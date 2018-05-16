"""Logic related to actually syncing files."""

import os
import pathlib
import typing
import logging

import stevedore
import stevedore.driver
import stevedore.exception

from kitovu import utils
from kitovu.sync import filecache
from kitovu.sync.syncplugin import AbstractSyncPlugin
from kitovu.sync.settings import Settings, ConnectionSettings
from kitovu.sync.plugin import smb, moodle


logger: logging.Logger = logging.getLogger(__name__)


def _load_plugin(plugin_settings: ConnectionSettings,
                 validator: typing.Optional[utils.SchemaValidator] = None) -> AbstractSyncPlugin:
    if validator is None:
        validator = utils.SchemaValidator()

    builtin_plugins = {
        'smb': smb.SmbPlugin(),
        'moodle': moodle.MoodlePlugin(),
    }
    plugin_name = plugin_settings.plugin_name
    if plugin_name in builtin_plugins:
        plugin = builtin_plugins[plugin_name]
    else:
        try:
            manager = stevedore.driver.DriverManager(namespace='kitovu.sync.plugin',
                                                     name=plugin_name, invoke_on_load=True)
        except stevedore.exception.NoMatches:
            raise utils.NoPluginError(f"The plugin {plugin_name} was not found")

        plugin = manager.driver

    validator.validate(plugin_settings.connection, plugin.connection_schema())

    return plugin


def start_all(config_file: typing.Optional[pathlib.Path]) -> None:
    settings = Settings.from_yaml_file(config_file)
    for connection_name, connection_settings in sorted(settings.connections.items()):
        _start(connection_name, connection_settings)


def _start(connection_name: str, connection_settings: ConnectionSettings) -> None:
    logger.info(f'Syncing connection {connection_name}')

    plugin = _load_plugin(connection_settings)

    try:
        plugin.configure(connection_settings.connection)
        plugin.connect()
    except utils.PluginOperationError as ex:
        logger.error(f'Error from {plugin.NAME} plugin: {ex}, skipping this plugin')
        return

    filecache_path: pathlib.Path = filecache.get_path()
    cache: filecache.FileCache = filecache.FileCache(filecache_path)
    cache.load()

    for subject in connection_settings.subjects:
        try:
            _sync_subject(subject, plugin, cache)
        except utils.PluginOperationError as ex:
            logger.error(f'Error from {plugin.NAME} plugin: {ex}, skipping this subject')
            continue

    logger.info('')
    cache.write()
    plugin.disconnect()


def _sync_subject(subject: utils.JsonType,
                  plugin: AbstractSyncPlugin,
                  cache: filecache.FileCache) -> None:
    logger.info(f'Syncing subject {subject["name"]}')

    remote_dir = pathlib.PurePath(subject['remote-dir'])  # /Informatik/Fachbereich/EPJ/
    local_dir = pathlib.Path(subject['local-dir'])  # /home/leonie/HSR/EPJ/

    ignore: typing.List[str] = subject['ignore']

    for remote_full_path in plugin.list_path(remote_dir):
        if remote_full_path.name in ignore:
            logger.debug(f'Ignoring file {remote_full_path}')
            continue
        try:
            _sync_path(remote_full_path, local_dir, remote_dir, plugin, cache)
        except utils.PluginOperationError as ex:
            logger.error(f'Error from {plugin.NAME} plugin: {ex}, skipping this file')
            continue


def _sync_path(remote_full_path: pathlib.PurePath,
               local_dir: pathlib.Path,
               remote_dir: pathlib.PurePath,
               plugin: AbstractSyncPlugin,
               cache: filecache.FileCache) -> None:
    # each plugin should now yield all files recursively with list_path
    logger.debug(f'Checking: {remote_full_path}')

    remote_digest = plugin.create_remote_digest(remote_full_path)
    logger.debug(f'Remote digest: {remote_digest}')

    # local_dir: /home/leonie/HSR/EPJ/
    # remote_full_path: /Informatik/Fachbereich/EPJ/Dokumente/Anleitung.pdf
    #   with relative_to: Dokumente/Anleitung.pdf
    # -> local_full_path: /home/leonie/HSR/EPJ/Dokumente/Anleitung.pdf
    filename: pathlib.PurePath = utils.sanitize_filename(remote_full_path.relative_to(remote_dir))
    local_full_path: pathlib.Path = local_dir / filename

    # When both files changed, we currently override the local file, but this can and should
    # later be handled as a user decision. https://jira.keltec.ch/jira/browse/EPJ-78
    state_of_file: filecache.FileState = cache.discover_changes(
        local_full_path=local_full_path, remote_full_path=remote_full_path, plugin=plugin)
    if state_of_file in [filecache.FileState.NO_CHANGES,
                         filecache.FileState.LOCAL_CHANGED]:
        logger.debug("No remote changes.")
    elif state_of_file in [filecache.FileState.REMOTE_CHANGED,
                           filecache.FileState.NEW,
                           filecache.FileState.BOTH_CHANGED]:
        logger.info(f"Downloading {remote_full_path}")
        local_full_path.parent.mkdir(parents=True, exist_ok=True)

        with local_full_path.open('wb') as fileobj:
            mtime: typing.Optional[int] = plugin.retrieve_file(remote_full_path, fileobj)

        if mtime is not None:
            os.utime(local_full_path, (local_full_path.stat().st_atime, mtime))

        local_digest = plugin.create_local_digest(local_full_path)
        logger.debug(f"Local digest: {local_digest}")

        assert remote_digest == local_digest, local_full_path
        cache.modify(local_full_path, plugin, local_digest)
    else:
        raise AssertionError(f"Unhandled state {state_of_file} for {local_full_path}")


def validate_config(config_file: typing.Optional[pathlib.Path]) -> None:
    """Validate the given configuration file.

    Raise an UsageError if the configuration is not valid.
    """
    settings = Settings.from_yaml_file(config_file)
    validator = utils.SchemaValidator(abort=False)
    for _connection_key, connection_settings in sorted(settings.connections.items()):
        _load_plugin(connection_settings, validator)
    if not validator.is_valid:
        validator.raise_error()
