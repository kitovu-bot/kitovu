"""A collection of all settings wrappers and factories for the sync."""

import pathlib
import typing
import os.path

import yaml
import attr
import jsonschema

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

    root_dir: pathlib.Path = attr.ib()
    global_ignore: typing.List[str] = attr.ib()
    plugins: typing.Dict[str, PluginSettings] = attr.ib()

    settings_schema: typing.Dict[str, typing.Any] = {
        'type': 'object',
        'properties': {
            'root-dir': {'type': 'string'},
            'syncs': {
                'type': 'array',
                'items': {'type': 'object'},
            },
            'plugins': {
                'type': 'array',
                'items': {'type': 'object'},
            },
            'global-ignore': {'type': 'array'},
        },
        'required': [
            'root-dir',
            'syncs',
            'plugins',
        ],
        'additionalProperties': False,
    }

    @classmethod
    def from_yaml_file(cls, path: pathlib.Path) -> 'Settings':
        """Load the settings from the specified yaml file"""
        try:
            with path.open('r') as stream:
                return cls.from_yaml_stream(stream)
        except FileNotFoundError as error:
            raise utils.UsageError(f'Could not find the file {error.filename}')

        return cls.from_yaml_stream(stream)

    @classmethod
    def from_yaml_stream(cls, stream: typing.IO) -> 'Settings':
        """Load the settings from the specified stream"""
        # FIXME handle OSError and UnicodeDecodeError
        data = yaml.load(stream)

        jsonschema.validate(data, cls.settings_schema)

        root_dir = pathlib.Path(os.path.expanduser(data.pop('root-dir')))
        global_ignore = data.pop('global-ignore', [])

        plugins = cls._get_plugin_settings(
            raw_plugins=data.pop('plugins'),
            raw_syncs=data.pop('syncs'),
            root_dir=root_dir,
        )

        return Settings(
            root_dir=root_dir,
            global_ignore=global_ignore,
            plugins=plugins,
        )

    @classmethod
    def _get_plugin_settings(cls, raw_plugins: typing.List[SimpleDict],
                             raw_syncs: typing.List[SimpleDict],
                             root_dir: pathlib.Path) -> typing.Dict[str, PluginSettings]:
        """Create the PluginSettings for the specified plugins and syncs."""
        plugins = {}

        for raw_plugin in raw_plugins:
            name = raw_plugin.pop('name')
            plugins[name] = PluginSettings(
                plugin_type=raw_plugin.pop('type'),
                connection=raw_plugin,
            )

        sync_schema: typing.Dict[str, typing.Any] = {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'plugins': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'plugin': {
                                    'type': 'string',
                                    'enum': [key for key in plugins],
                                },
                                'local-dir': {'type': 'string'},
                                'remote-dir': {'type': 'string'},
                                'ignore': {
                                    'type': 'array',
                                    'items': {'type': 'string'},
                                },
                            },
                            'required': [
                                'plugin',
                                'remote-dir',
                            ],
                            'additionalProperties': False,
                        },
                    },
                },
                'required': [
                    'name',
                    'plugins',
                ],
                'additionalProperties': False,
            },
        }

        jsonschema.validate(raw_syncs, sync_schema)

        for sync in raw_syncs:
            name = sync.pop('name')
            for plugin_usage in sync.pop('plugins'):
                plugin_usage['name'] = name
                plugin_usage['local-dir'] = pathlib.Path(
                    plugin_usage.get('local-dir', root_dir / name))
                plugin_usage['remote-dir'] = pathlib.PurePath(plugin_usage['remote-dir'])
                plugins[plugin_usage.pop('plugin')].syncs.append(plugin_usage)

        return plugins
