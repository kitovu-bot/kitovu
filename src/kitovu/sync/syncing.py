"""Logic related to actually syncing files."""

import pathlib
import typing

import stevedore
import stevedore.driver

from kitovu import utils
from kitovu.sync import syncplugin
from kitovu.sync.settings import Settings, ConnectionSettings
from kitovu.sync.plugin import smb, moodle


def _find_plugin(pluginname: str) -> syncplugin.AbstractSyncPlugin:
    """Find an appropriate sync plugin with the given settings."""
    builtin_plugins = {
        'smb': smb.SmbPlugin(),
        'moodle': moodle.MoodlePlugin(),
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

    for subject in connection_settings.subjects:
        remote_path = subject['remote-dir']
        local_path = subject['local-dir']

        for item in plugin.list_path(remote_path):
            # each plugin should now yield all files recursively with list_path
            print(f'Downloading: {item}')

            remote_digest = plugin.create_remote_digest(item)
            print(f'Remote digest: {remote_digest}')

            output = pathlib.Path(local_path / item.relative_to(remote_path))

            pathlib.Path(output.parent).mkdir(parents=True, exist_ok=True)

            with output.open('wb') as fileobj:
                plugin.retrieve_file(item, fileobj)

            local_digest = plugin.create_local_digest(output)
            print(f'Local digest: {local_digest}')

            assert remote_digest == local_digest

    plugin.disconnect()
