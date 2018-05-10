"""A collection of all settings wrappers and factories for the subject."""

import pathlib
import typing
import os.path
import logging

import appdirs
import yaml
import attr

from kitovu import utils


logger: logging.Logger = logging.getLogger(__name__)
SimpleDict = typing.Dict[str, typing.Any]


@attr.s
class ConnectionSettings:
    """A class representing the settings of a single connection"""

    plugin_name: str = attr.ib()
    connection: SimpleDict = attr.ib()
    subjects: typing.List[SimpleDict] = attr.ib(default=attr.Factory(list))


@attr.s
class Settings:
    """A class representing the settings of all connections"""

    root_dir: pathlib.Path = attr.ib()
    global_ignore: typing.List[str] = attr.ib()
    connections: typing.Dict[str, ConnectionSettings] = attr.ib()

    SETTINGS_SCHEMA: utils.JsonSchemaType = {
        'type': 'object',
        'properties': {
            'root-dir': {'type': 'string'},
            'subjects': {
                'type': 'array',
                'items': {'type': 'object'},
            },
            'connections': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string'},
                        'plugin': {'type': 'string'},
                    },
                    'required': ['name', 'plugin'],
                },
            },
            'global-ignore': {'type': 'array', 'items': {'type': 'string'}},
        },
        'required': [
            'root-dir',
            'subjects',
            'connections',
        ],
        'additionalProperties': False,
    }

    @classmethod
    def from_yaml_file(cls, path: typing.Optional[pathlib.Path] = None,
                       validator: typing.Optional[utils.SchemaValidator] = None) -> 'Settings':
        """Load the settings from the specified yaml file"""
        if path is None:
            path = get_config_file_path()
        logger.debug(f"Loading from {path}")

        try:
            with path.open('r') as stream:
                return cls.from_yaml_stream(stream, validator)
        except FileNotFoundError as error:
            raise utils.UsageError(f'Could not find the file {error.filename}')

    @classmethod
    def from_yaml_stream(cls, stream: typing.IO,
                         validator: typing.Optional[utils.SchemaValidator] = None) -> 'Settings':
        """Load the settings from the specified stream"""
        if validator is None:
            validator = utils.SchemaValidator()

        # FIXME handle OSError and UnicodeDecodeError
        try:
            data = yaml.load(stream)
        except yaml.scanner.ScannerError as error:
            raise utils.UsageError(f"Invalid Configuration:\n{error}")

        validator.validate(data, cls.SETTINGS_SCHEMA)

        root_dir = pathlib.Path(os.path.expanduser(data.pop('root-dir')))
        global_ignore = data.pop('global-ignore', [])

        connections = cls._get_connection_settings(
            validator=validator,
            raw_connections=data.pop('connections'),
            raw_subjects=data.pop('subjects'),
            root_dir=root_dir,
        )

        return Settings(
            root_dir=root_dir,
            global_ignore=global_ignore,
            connections=connections,
        )

    @classmethod
    def _get_connection_settings(cls, validator: utils.SchemaValidator,
                                 raw_connections: typing.List[SimpleDict],
                                 raw_subjects: typing.List[SimpleDict],
                                 root_dir: pathlib.Path) -> typing.Dict[str, ConnectionSettings]:
        """Create the ConnectionSettings for the specified connections and subjects."""
        connections = {}

        for raw_connection in raw_connections:
            name = raw_connection.pop('name')
            connections[name] = ConnectionSettings(
                plugin_name=raw_connection.pop('plugin'),
                connection=raw_connection,
            )

        subject_schema: utils.JsonSchemaType = {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'sources': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'connection': {
                                    'type': 'string',
                                    'enum': [key for key in connections],
                                },
                                'local-dir': {'type': 'string'},
                                'remote-dir': {'type': 'string'},
                                'ignore': {
                                    'type': 'array',
                                    'items': {'type': 'string'},
                                },
                            },
                            'required': [
                                'connection',
                                'remote-dir',
                            ],
                            'additionalProperties': False,
                        },
                    },
                },
                'required': [
                    'name',
                    'sources',
                ],
                'additionalProperties': False,
            },
        }

        validator.validate(raw_subjects, subject_schema)

        for subject in raw_subjects:
            name = subject.pop('name')
            for connection_usage in subject.pop('sources'):
                connection_usage['name'] = name
                connection_usage['local-dir'] = pathlib.Path(
                    connection_usage.get('local-dir', root_dir / name))
                connection_usage['remote-dir'] = pathlib.PurePath(connection_usage['remote-dir'])
                connections[connection_usage.pop('connection')].subjects.append(connection_usage)

        return connections


def get_config_dir_path() -> pathlib.Path:
    return pathlib.Path(appdirs.user_config_dir('kitovu'))


def get_config_file_path() -> pathlib.Path:
    return get_config_dir_path() / 'kitovu.yaml'
