"""Logic related to actually syncing files."""

import pathlib
import typing

import stevedore
import stevedore.driver

from kitovu import utils
from kitovu.sync.syncplugin import AbstractSyncPlugin
from kitovu.sync.settings import Settings, ConnectionSettings
from kitovu.sync.plugin import smb


def _find_plugin(plugin_settings: ConnectionSettings,
                 validator: typing.Optional[utils.SchemaValidator] = None) -> AbstractSyncPlugin:
    """Find an appropriate sync plugin with the given settings."""
    if validator is None:
        validator = utils.SchemaValidator()

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

    validator.validate(plugin_settings.connection, plugin.connection_schema())

    return plugin


def start_all(config_file: typing.Optional[pathlib.Path]) -> None:
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


def validate_config(config_file: typing.Optional[pathlib.Path]) -> None:
    """Validates the given configuration file.

    Raises an UsageError if the configuration is not valid."""
    settings = Settings.from_yaml_file(config_file)
    validator = utils.SchemaValidator(abort=False)
    for _connection_key, connection_settings in sorted(settings.connections.items()):
        _find_plugin(connection_settings, validator)
    if not validator.is_valid:
        validator.raise_error()
