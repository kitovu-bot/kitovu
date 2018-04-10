"""Logic related to actually syncing files."""

import pathlib
import typing

import stevedore
import stevedore.driver
import jsonschema

from kitovu import utils
from kitovu.sync import syncplugin
from kitovu.sync.settings import Settings, PluginSettings
from kitovu.sync.plugin import smb


def _find_plugin(plugin_settings: PluginSettings) -> syncplugin.AbstractSyncPlugin:
    """Find an appropriate sync plugin with the given settings."""
    builtin_plugins = {
        'smb': smb.SmbPlugin(),
    }
    plugin_type = plugin_settings.plugin_type
    if plugin_type in builtin_plugins:
        plugin = builtin_plugins[plugin_type]
    else:
        try:
            manager = stevedore.driver.DriverManager(namespace='kitovu.sync.plugin',
                                                     name=plugin_type, invoke_on_load=True)
        except stevedore.exception.NoMatches:
            raise utils.NoPluginError(f"The plugin {plugin_type} was not found")

        plugin = manager.driver

    jsonschema.validate(plugin_settings.connection, plugin.connection_schema())

    return plugin


def start_all(config_file: pathlib.Path) -> None:
    """Sync all files with the given configuration file."""
    settings = Settings.from_yaml_file(config_file)
    for _plugin_key, plugin_settings in sorted(settings.plugins.items()):
        start(plugin_settings)


def start(plugin_settings: PluginSettings) -> None:
    """Sync files with the given plugin and username."""
    plugin = _find_plugin(plugin_settings)
    plugin.configure(plugin_settings.connection)
    plugin.connect()

    for sync in plugin_settings.syncs:
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


def config_error(config_file: pathlib.Path) -> typing.Union[str, None]:
    """Validates the given configuration file.

    Returns either an error message or None if it's valid."""
    try:
        settings = Settings.from_yaml_file(config_file)
        for _plugin_key, plugin_settings in sorted(settings.plugins.items()):
            _find_plugin(plugin_settings)
        return None
    except (jsonschema.exceptions.ValidationError, utils.UsageError) as error:
        return str(error)
