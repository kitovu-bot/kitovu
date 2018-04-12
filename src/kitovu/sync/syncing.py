"""Logic related to actually syncing files."""

import pathlib
import typing

import stevedore
import stevedore.driver
import jsonschema

from kitovu import utils
from kitovu.sync import syncplugin
from kitovu.sync.settings import Settings, ConnectionSettings
from kitovu.sync.plugin import smb


def _find_plugin(plugin_settings: ConnectionSettings) -> syncplugin.AbstractSyncPlugin:
    """Find an appropriate sync plugin with the given settings."""
    builtin_plugins = {
        'smb': smb.SmbPlugin(),
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

    jsonschema.validate(plugin_settings.connection, plugin.connection_schema())

    return plugin


def start_all(config_file: pathlib.Path) -> None:
    """Sync all files with the given configuration file."""
    settings = Settings.from_yaml_file(config_file)
    for _plugin_key, connection_settings in sorted(settings.connections.items()):
        start(connection_settings)


def start(connection_settings: ConnectionSettings) -> None:
    """Sync files with the given plugin and username."""
    plugin = _find_plugin(connection_settings)
    plugin.configure(connection_settings.connection)
    plugin.connect()

    for subject in connection_settings.subjects:
        remote_path = subject['remote-dir']
        local_path = subject['local-dir']

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

    plugin.disconnect()


def config_error(config_file: pathlib.Path) -> typing.Union[str, None]:
    """Validates the given configuration file.

    Returns either an error message or None if it's valid."""
    try:
        settings = Settings.from_yaml_file(config_file)
        for _connection_key, connection_settings in sorted(settings.connections.items()):
            _find_plugin(connection_settings)
        return None
    except (jsonschema.exceptions.ValidationError, utils.UsageError) as error:
        return str(error)
