"""Logic related to actually syncing files."""

import pathlib

import stevedore
import stevedore.driver

from kitovu import utils
from kitovu.sync import syncplugin
from kitovu.sync.settings import Settings, PluginSettings
from kitovu.sync.plugin import smb


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


def start_all(config_file: pathlib.Path) -> None:
    """Sync all files with the given configuration file."""
    settings = Settings.from_yaml_file(config_file)
    for _plugin_key, plugin_settings in sorted(settings.plugins.items()):
        start(plugin_settings)


def start(plugin_settings: PluginSettings) -> None:
    """Sync files with the given plugin and username."""
    plugin = _find_plugin(plugin_settings.plugin_type)
    plugin.configure(plugin_settings.connection)
    plugin.connect()

    for sync in plugin_settings.syncs:
        remote_path = sync['remote-dir']
        local_path = sync['local-dir']

        for item in plugin.list_path(remote_path):
            # each plugin should now yield all files recursively with list_path
            print(f'Downloading: {item}')

            digest = plugin.create_remote_digest(item)
            print(f'Remote digest: {digest}')

            output = pathlib.Path(local_path / item.relative_to(remote_path))

            pathlib.Path(output.parent).mkdir(parents=True, exist_ok=True)

            with output.open('wb') as fileobj:
                plugin.retrieve_file(item, fileobj)

            digest = plugin.create_local_digest(output)
            print(f'Local digest: {digest}')
