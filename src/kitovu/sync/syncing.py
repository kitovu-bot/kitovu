"""Logic related to actually syncing files."""

import pathlib

import stevedore
import stevedore.driver

from kitovu import utils
from kitovu.sync import syncplugin
from kitovu.sync.settings import YAMLSettingsFactory, PluginSettings
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


def start_all(config_file: pathlib.PurePath) -> None:
    """Sync all files with the given configuration file."""
    settings = YAMLSettingsFactory.from_file(config_file)
    for _plugin_key, plugin_settings in settings.plugins.items():
        start(plugin_settings)


def start(plugin_settings: PluginSettings) -> None:
    """Sync files with the given plugin and username."""
    plugin = _find_plugin(plugin_settings.plugin_type)
    plugin.configure(plugin_settings.connection)
    plugin.connect()

    for sync in plugin_settings.syncs:
        print(sync)
        remote_path = sync['remote-dir']
        local_path = sync['local-dir']

        files = list(plugin.list_path(remote_path))
        print(f'Remote files: {files}')

        example_file = files[0]
        print(f'Downloading: {example_file}')
        digest = plugin.create_remote_digest(example_file)
        print(f'Remote digest: {digest}')

        output = pathlib.Path(example_file.name)

        with output.open('wb') as fileobj:
            plugin.retrieve_file(local_path / example_file, fileobj)

        digest = plugin.create_local_digest(output)
        print(f'Local digest: {digest}')
