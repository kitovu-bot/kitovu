"""Logic related to actually syncing files."""

import appdirs
import pathlib
import typing

import stevedore
import stevedore.driver
import stevedore.exception

from kitovu import utils
from kitovu.sync import syncplugin
from kitovu.sync.settings import Settings, ConnectionSettings
from kitovu.sync.plugin import smb
from kitovu.sync import filecache


def _find_plugin(pluginname: str) -> syncplugin.AbstractSyncPlugin:
    """Find an appropriate sync plugin with the given settings."""
    builtin_plugins = {
        'smb': smb.SmbPlugin(),
    }
    if pluginname in builtin_plugins:
        return builtin_plugins[pluginname]

    try:
        manager = stevedore.driver.DriverManager(namespace='kitovu.sync.plugin',
                                                 name=pluginname, invoke_on_load=True)
    except stevedore.exception.NoMatches:
        raise utils.NoPluginError(f"The plugin {pluginname} was not found")

    plugin: syncplugin.AbstractSyncPlugin = manager.driver
    return plugin


def start_all(config_file: typing.Optional[pathlib.Path]) -> None:
    """Sync all files with the given configuration file."""
    settings = Settings.from_yaml_file(config_file)
    for _plugin_key, connection_settings in sorted(settings.connections.items()):
        start(connection_settings)


def start(connection_settings: ConnectionSettings) -> None:
    """Sync files with the given plugin and username."""
    plugin = _find_plugin(connection_settings.plugin_name)
    plugin.configure(connection_settings.connection)
    plugin.connect()
    cache: filecache.FileCache = filecache.FileCache(
        pathlib.Path(appdirs.user_data_dir('kitovu')) / 'filecache.json')
    cache.load()

    for subject in connection_settings.subjects:
        remote_dir = pathlib.PurePath(subject['remote-dir'])  # /Informatik/Fachbereich/EPJ/
        local_dir = pathlib.Path(subject['local-dir'])  # /home/leonie/HSR/EPJ/

        for remote_full_path in plugin.list_path(remote_dir):
            # each plugin should now yield all files recursively with list_path
            print(f'Downloading: {remote_full_path}')

            remote_digest = plugin.create_remote_digest(remote_full_path)
            print(f'Remote digest: {remote_digest}')

            # local_dir: /home/leonie/HSR/EPJ/
            # remote_full_path: /Informatik/Fachbereich/EPJ/Dokumente/Anleitung.pdf
            #   with relative_to: Dokumente/Anleitung.pdf
            # -> local_full_path: /home/leonie/HSR/EPJ/Dokumente/Anleitung.pdf
            local_full_path: pathlib.Path = local_dir / remote_full_path.relative_to(remote_dir)

            # When BOTH files changed, we currently override the local file, but this can and should
            # later be handled as a user decision. https://jira.keltec.ch/jira/browse/EPJ-78
            state_of_file: filecache.FileState = cache.discover_changes(local_full_path, remote_full_path, plugin)
            if state_of_file in [filecache.FileState.NO_CHANGES,
                                 filecache.FileState.LOCAL_CHANGED]:
                pass
            elif state_of_file in [filecache.FileState.REMOTE_CHANGED,
                                   filecache.FileState.NEW,
                                   filecache.FileState.BOTH_CHANGED]:
                local_full_path.parent.mkdir(parents=True, exist_ok=True)

                with local_full_path.open('wb') as fileobj:
                    plugin.retrieve_file(remote_full_path, fileobj)

                local_digest = plugin.create_local_digest(local_full_path)
                print(f'Local digest: {local_digest}')
                cache.modify(local_full_path, plugin, local_digest)
    cache.write()
    plugin.disconnect()
