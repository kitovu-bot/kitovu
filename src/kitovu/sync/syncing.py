"""Logic related to actually syncing files."""

import pathlib
import typing

import stevedore
import stevedore.driver
import attr
import yaml

from kitovu import utils
from kitovu.sync import syncplugin
from kitovu.sync.plugin import smb


def _find_plugin(pluginname: str) -> syncplugin.AbstractSyncPlugin:
    """Find an appropriate sync plugin with the given name."""
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


def start(pluginname: str, username: str) -> None:
    """Sync files with the given plugin and username."""
    plugin = _find_plugin(pluginname)
    plugin.configure({'username': username})
    plugin.connect()

    path = pathlib.PurePath('/Informatik/Fachbereich/Engineering-Projekt/EPJ/FS2018/')

    files = list(plugin.list_path(path))
    print(f'Remote files: {files}')

    example_file = files[0]
    print(f'Downloading: {example_file}')
    digest = plugin.create_remote_digest(example_file)
    print(f'Remote digest: {digest}')

    output = pathlib.Path(example_file.name)

    with output.open('wb') as fileobj:
        plugin.retrieve_file(example_file, fileobj)

    digest = plugin.create_local_digest(output)
    print(f'Local digest: {digest}')


SyncType = typing.Dict[str, typing.Any]
SyncListType = typing.List[SyncType]


@attr.s
class PluginSettings:
    """A class representing the settings of a signle plugin"""

    plugin_type: str = attr.ib()
    connection: typing.Dict[str, typing.Any] = attr.ib()
    syncs: SyncListType = attr.ib(default=[])


@attr.s
class Settings:
    """A class representing the settings of a all plugins"""

    root_dir: pathlib.PurePath = attr.ib()
    global_ignore: typing.List[str] = attr.ib()
    plugins: typing.Dict[str, PluginSettings] = attr.ib()


class SettingsFactory:
    """A factory to create settings objects from files or strings.

    It cannot be done in the Settings class itself because mypy does
    not know the Settings type inside of the class.
    """

    @classmethod
    def from_yaml_file(cls, path: pathlib.PurePath) -> Settings:
        """Load the settings from the specified yaml file"""

        stream = open(path, 'r')
        return cls.from_yaml(stream)

    @classmethod
    def from_yaml(cls, stream: typing.TextIO) -> Settings:
        """Load the settings from the specified stream"""

        data = yaml.load(stream)

        required_keys = ['root-dir', 'syncs', 'plugins']
        missing_keys = [i for i in required_keys if i not in data.keys()]
        if missing_keys:
            raise utils.MissingSettingKeysError(missing_keys)
        root_dir = pathlib.PurePath(data.pop('root-dir'))
        global_ignore = data.pop('global-ignore', [])

        plugins = {}
        for raw_plugin in data.pop('plugins'):
            plugin = PluginSettings(
                plugin_type=raw_plugin.pop('type'),
                connection=raw_plugin,
            )
            plugins[raw_plugin.pop('name')] = plugin

        for sync in data.pop('syncs'):
            name = sync.pop('name')
            for sub_plugin in sync.pop('plugins'):
                sub_plugin['name'] = name
                plugins[sub_plugin.pop('plugin')].syncs.append(sub_plugin)
            if sync:
                raise utils.UnknownSettingKeysError(sync.keys())

        if data:
            raise utils.UnknownSettingKeysError(data.keys())

        return Settings(
            root_dir=root_dir,
            global_ignore=global_ignore,
            plugins=plugins,
        )
