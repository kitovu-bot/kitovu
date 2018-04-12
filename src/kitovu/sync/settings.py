"""A collection of all settings wrappers and factories for the subject."""

import pathlib
import typing
import os.path

import yaml
import attr

from kitovu import utils


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

    @classmethod
    def from_yaml_file(cls, path: pathlib.Path) -> 'Settings':
        """Load the settings from the specified yaml file"""
        with path.open('r') as stream:
            return cls.from_yaml_stream(stream)

    @classmethod
    def from_yaml_stream(cls, stream: typing.IO) -> 'Settings':
        """Load the settings from the specified stream"""
        # FIXME handle OSError and UnicodeDecodeError
        data = yaml.load(stream)

        required_keys = ['root-dir', 'connections', 'subjects']
        missing_keys = [i for i in required_keys if i not in data.keys()]
        if missing_keys:
            raise utils.MissingSettingKeysError(missing_keys)
        root_dir = pathlib.Path(os.path.expanduser(data.pop('root-dir')))
        global_ignore = data.pop('global-ignore', [])

        connections = cls._get_connection_settings(
            raw_connections=data.pop('connections'),
            raw_subjects=data.pop('subjects'),
            root_dir=root_dir,
        )

        cls._ensure_empty(data)

        return Settings(
            root_dir=root_dir,
            global_ignore=global_ignore,
            connections=connections,
        )

    @classmethod
    def _get_connection_settings(cls, raw_connections: typing.List[SimpleDict],
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

        for subject in raw_subjects:
            name = subject.pop('name')
            for connection_usage in subject.pop('sources'):
                connection_usage['name'] = name
                connection_usage['local-dir'] = pathlib.Path(
                    connection_usage.get('local-dir', root_dir / name))
                connection_usage['remote-dir'] = pathlib.PurePath(connection_usage['remote-dir'])
                connections[connection_usage.pop('connection')].subjects.append(connection_usage)
            cls._ensure_empty(subject)

        return connections

    @classmethod
    def _ensure_empty(cls, data: SimpleDict) -> None:
        """Raise an error if the specified dictionary is not empty."""
        if data:
            raise utils.UnknownSettingKeysError(list(data.keys()))
