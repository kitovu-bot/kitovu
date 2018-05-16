"""A collection of all settings wrappers and factories for the subject."""

import pathlib
import typing
import os.path
import logging
import subprocess
from distutils import spawn

import appdirs
import yaml
import attr

from kitovu import utils


logger: logging.Logger = logging.getLogger(__name__)
SimpleDict = typing.Dict[str, typing.Any]


def get_config_file_path() -> pathlib.Path:
    return pathlib.Path(appdirs.user_config_dir('kitovu')) / 'kitovu.yaml'


class EditorSpawner:

    DEFAULT_EDITORS = [
        'vim',
        'emacs',
        'nano',
        'editor',
        'notepad',
    ]
    DEFAULT_EDITORS_STR = ', '.join(DEFAULT_EDITORS)

    def edit(self,
             config: typing.Optional[pathlib.Path] = None,
             editor: typing.Optional[str] = None) -> None:
        if editor is None and 'EDITOR' in os.environ:
            editor = os.environ['EDITOR']
        editor_path: str = self._get_editor_path(editor)

        if config is None:
            config = get_config_file_path()
            config.parent.mkdir(exist_ok=True)
            config.touch(exist_ok=True)
        elif not config.exists():
            raise utils.UsageError(f"Could not find the configuration file {config}")

        subprocess.call([editor_path, config])

    def _get_editor_path(self, editor: typing.Optional[str]) -> str:
        if editor is not None:
            path = spawn.find_executable(editor)
            if path is None:
                raise utils.UsageError(f"Could not find the editor {editor}")
            return path

        for default_editor in self.DEFAULT_EDITORS:
            path = spawn.find_executable(default_editor)
            if path is not None:
                return path

        raise utils.UsageError('Could not find a valid editor')


@attr.s
class ConnectionSettings:
    """The settings of a single connection."""

    plugin_name: str = attr.ib()
    connection: SimpleDict = attr.ib()
    subjects: typing.List[SimpleDict] = attr.ib(default=attr.Factory(list))


@attr.s
class Settings:
    """The settings of all connections."""

    root_dir: pathlib.Path = attr.ib()
    connections: typing.Dict[str, ConnectionSettings] = attr.ib()

    SETTINGS_SCHEMA: utils.JsonType = {
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
    def from_yaml_file(cls, path: typing.Optional[pathlib.Path] = None) -> 'Settings':
        if path is None:
            path = get_config_file_path()
        logger.debug(f"Loading from {path}")

        try:
            with path.open('r') as stream:
                return cls.from_yaml_stream(stream)
        except FileNotFoundError as error:
            raise utils.UsageError(f'Could not find the file {error.filename}')
        except OSError as error:
            raise utils.UsageError(f'Failed to open config file: {error}')

    @classmethod
    def from_yaml_stream(cls, stream: typing.IO) -> 'Settings':
        validator = utils.SchemaValidator()

        try:
            data = yaml.load(stream)
        except (yaml.YAMLError, OSError, UnicodeDecodeError) as error:
            raise utils.UsageError(f"Failed to load configuration:\n{error}")

        validator.validate(data, cls.SETTINGS_SCHEMA)

        root_dir = pathlib.Path(os.path.expanduser(data.pop('root-dir')))
        global_ignore = data.pop('global-ignore', [])

        connections = cls._get_connection_settings(
            validator=validator,
            raw_connections=data.pop('connections'),
            raw_subjects=data.pop('subjects'),
            global_ignore=global_ignore,
            root_dir=root_dir,
        )

        return Settings(
            root_dir=root_dir,
            connections=connections,
        )

    @staticmethod
    def _get_connection_settings(validator: utils.SchemaValidator,
                                 raw_connections: typing.List[SimpleDict],
                                 raw_subjects: typing.List[SimpleDict],
                                 global_ignore: typing.List[str],
                                 root_dir: pathlib.Path) -> typing.Dict[str, ConnectionSettings]:
        """Create the ConnectionSettings for the specified connections and subjects."""
        connections = {}

        for raw_connection in raw_connections:
            name = raw_connection.pop('name')
            connections[name] = ConnectionSettings(
                plugin_name=raw_connection.pop('plugin'),
                connection=raw_connection,
            )

        subject_schema: utils.JsonType = {
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
                connection_usage['ignore'] = global_ignore + connection_usage.get('ignore', [])
                connections[connection_usage.pop('connection')].subjects.append(connection_usage)

        return connections
