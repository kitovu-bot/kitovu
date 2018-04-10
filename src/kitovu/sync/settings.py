"""A collection of all settings wrappers and factories for the sync."""

import pathlib
import typing

import yaml
import attr

from kitovu import utils


SimpleDict = typing.Dict[str, typing.Any]


@attr.s
class PluginSettings:
    """A class representing the settings of a single plugin"""

    plugin_type: str = attr.ib()
    connection: SimpleDict = attr.ib()
    syncs: typing.List[SimpleDict] = attr.ib(default=attr.Factory(list))


@attr.s
class Settings:
    """A class representing the settings of all plugins"""

    root_dir: pathlib.PurePath = attr.ib()
    global_ignore: typing.List[str] = attr.ib()
    plugins: typing.Dict[str, PluginSettings] = attr.ib()

    @classmethod
    def from_yaml_file(cls, path: pathlib.Path) -> 'Settings':
        """Load the settings from the specified yaml file"""
        with path.open('r') as stream:
            return cls.from_yaml_stream(stream)

    @classmethod
    def from_yaml_stream(cls, stream: typing.TextIO) -> 'Settings':
        """Load the settings from the specified stream"""
        # FIXME handle OSError and UnicodeDecodeError
        data = yaml.load(stream)

        required_keys = ['root-dir', 'syncs', 'plugins']
        missing_keys = [i for i in required_keys if i not in data.keys()]
        if missing_keys:
            raise utils.MissingSettingKeysError(missing_keys)
        root_dir = pathlib.PurePath(data.pop('root-dir'))
        global_ignore = data.pop('global-ignore', [])

        plugins = cls._get_plugins(
            raw_plugins=data.pop('plugins'),
            raw_syncs=data.pop('syncs'),
            root_dir=root_dir,
        )

        cls._ensure_empty(data)

        return Settings(
            root_dir=root_dir,
            global_ignore=global_ignore,
            plugins=plugins,
        )

    @classmethod
    def _get_plugins(cls, raw_plugins: typing.List[SimpleDict],
                     raw_syncs: typing.List[SimpleDict],
                     root_dir: pathlib.PurePath) -> typing.Dict[str, PluginSettings]:
        """Create the PluginSettings for the specified plugins and syncs."""
        plugins = {}

        for raw_plugin in raw_plugins:
            name = raw_plugin.pop('name')
            print(name)
            plugins[name] = PluginSettings(
                plugin_type=raw_plugin.pop('type'),
                connection=raw_plugin,
            )

        for sync in raw_syncs:
            name = sync.pop('name')
            for plugin_usage in sync.pop('plugins'):
                plugin_usage['name'] = name
                plugin_usage['local-dir'] = pathlib.PurePath(
                    plugin_usage.get('local-dir', root_dir / name))
                plugin_usage['remote-dir'] = pathlib.PurePath(plugin_usage['remote-dir'])
                plugins[plugin_usage.pop('plugin')].syncs.append(plugin_usage)
            cls._ensure_empty(sync)

        return plugins

    @classmethod
    def _ensure_empty(cls, data: SimpleDict) -> None:
        """Raise an error if the specified dictionary is not empty."""
        if data:
            raise utils.UnknownSettingKeysError(list(data.keys()))
