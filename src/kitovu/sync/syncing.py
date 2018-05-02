"""Logic related to actually syncing files."""

import os
import pathlib
import typing

import appdirs
import stevedore
import stevedore.driver
import stevedore.exception

from kitovu import utils
from kitovu.sync import filecache
from kitovu.sync.syncplugin import AbstractSyncPlugin
from kitovu.sync.settings import Settings, ConnectionSettings
from kitovu.sync.plugin import smb, moodle


def _load_plugin(plugin_settings: ConnectionSettings,
                 reporter: utils.AbstractReporter,
                 validator: typing.Optional[utils.SchemaValidator] = None) -> AbstractSyncPlugin:
    """Find and load an appropriate sync plugin with the given settings."""
    if validator is None:
        validator = utils.SchemaValidator()

    builtin_plugins = {
        'smb': smb.SmbPlugin(reporter),
        'moodle': moodle.MoodlePlugin(reporter),
    }
    plugin_name = plugin_settings.plugin_name
    if plugin_name in builtin_plugins:
        plugin = builtin_plugins[plugin_name]
    else:
        try:
            manager = stevedore.driver.DriverManager(namespace='kitovu.sync.plugin',
                                                     name=plugin_name, invoke_on_load=True,
                                                     invoke_args=(reporter,))
        except stevedore.exception.NoMatches:
            raise utils.NoPluginError(f"The plugin {plugin_name} was not found")

        plugin = manager.driver

    validator.validate(plugin_settings.connection, plugin.connection_schema())

    return plugin


def start_all(config_file: typing.Optional[pathlib.Path], reporter: utils.AbstractReporter) -> None:
    """Sync all files with the given configuration file."""
    settings = Settings.from_yaml_file(config_file)
    for _plugin_key, connection_settings in sorted(settings.connections.items()):
        start(connection_settings, reporter)


def start(connection_settings: ConnectionSettings, reporter: utils.AbstractReporter) -> None:
    """Sync files with the given plugin and username."""
    plugin = _load_plugin(connection_settings, reporter)
    plugin.configure(connection_settings.connection)
    plugin.connect()

    filecache_path: pathlib.Path = pathlib.Path(appdirs.user_data_dir('kitovu')) / 'filecache.json'
    cache: filecache.FileCache = filecache.FileCache(filecache_path)
    cache.load()

    for subject in connection_settings.subjects:
        remote_dir = pathlib.PurePath(subject['remote-dir'])  # /Informatik/Fachbereich/EPJ/
        local_dir = pathlib.Path(subject['local-dir'])  # /home/leonie/HSR/EPJ/

        for remote_full_path in plugin.list_path(remote_dir):
            # each plugin should now yield all files recursively with list_path
            print(f'Checking: {remote_full_path}')

            remote_digest = plugin.create_remote_digest(remote_full_path)
            print(f'Remote digest: {remote_digest}')

            # local_dir: /home/leonie/HSR/EPJ/
            # remote_full_path: /Informatik/Fachbereich/EPJ/Dokumente/Anleitung.pdf
            #   with relative_to: Dokumente/Anleitung.pdf
            # -> local_full_path: /home/leonie/HSR/EPJ/Dokumente/Anleitung.pdf
            local_full_path: pathlib.Path = local_dir / remote_full_path.relative_to(remote_dir)

            # When both files changed, we currently override the local file, but this can and should
            # later be handled as a user decision. https://jira.keltec.ch/jira/browse/EPJ-78
            state_of_file: filecache.FileState = cache.discover_changes(
                local_full_path=local_full_path, remote_full_path=remote_full_path, plugin=plugin)
            if state_of_file in [filecache.FileState.NO_CHANGES,
                                 filecache.FileState.LOCAL_CHANGED]:
                print("No remote changes.")
            elif state_of_file in [filecache.FileState.REMOTE_CHANGED,
                                   filecache.FileState.NEW,
                                   filecache.FileState.BOTH_CHANGED]:
                print("Downloading...")
                local_full_path.parent.mkdir(parents=True, exist_ok=True)

                with local_full_path.open('wb') as fileobj:
                    mtime: typing.Optional[int] = plugin.retrieve_file(remote_full_path, fileobj)

                if mtime is not None:
                    os.utime(local_full_path, (local_full_path.stat().st_atime, mtime))

                local_digest = plugin.create_local_digest(local_full_path)
                print(f'Local digest: {local_digest}')

                assert remote_digest == local_digest, local_full_path
                cache.modify(local_full_path, plugin, local_digest)
    cache.write()
    plugin.disconnect()


def validate_config(config_file: typing.Optional[pathlib.Path],
                    reporter: utils.AbstractReporter) -> None:
    """Validates the given configuration file.

    Raises an UsageError if the configuration is not valid.
    """
    settings = Settings.from_yaml_file(config_file)
    validator = utils.SchemaValidator(abort=False)
    for _connection_key, connection_settings in sorted(settings.connections.items()):
        _load_plugin(connection_settings, reporter, validator)
    if not validator.is_valid:
        validator.raise_error()
