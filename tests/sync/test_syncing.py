import pytest
import typing
import pathlib

import stevedore

from kitovu import utils
from kitovu.sync import syncing
from kitovu.sync.plugin import smb
from kitovu.sync.settings import PluginSettings
from kitovu.sync.syncplugin import AbstractSyncPlugin


class FakePlugin(AbstractSyncPlugin):
    connection_schema = {}

    def configure(self, info: typing.Dict[str, typing.Any]) -> None:
        raise NotImplementedError

    def connect(self) -> None:
        raise NotImplementedError

    def disconnect(self) -> None:
        raise NotImplementedError

    def create_local_digest(self, path: pathlib.Path) -> str:
        raise NotImplementedError

    def create_remote_digest(self, path: pathlib.PurePath) -> str:
        raise NotImplementedError

    def list_path(self, path: pathlib.PurePath) -> typing.Iterable[pathlib.PurePath]:
        raise NotImplementedError

    def retrieve_file(self, path: pathlib.PurePath, fileobj: typing.IO[bytes]) -> None:
        raise NotImplementedError


class TestFindPlugin:

    def test_find_plugin_builtin(self):
        plugin = syncing._find_plugin(self._get_settings('smb', connection={'username': 'test'}))
        assert isinstance(plugin, smb.SmbPlugin)

    def test_find_plugin_missing_external(self, mocker):
        mocker.patch('stevedore.driver.DriverManager', autospec=True,
                     side_effect=stevedore.exception.NoMatches)

        with pytest.raises(utils.NoPluginError, match='The plugin doesnotexist was not found'):
            syncing._find_plugin(self._get_settings('doesnotexist'))

    def test_find_plugin_external(self, mocker):
        fake_plugin_obj = FakePlugin()
        manager = mocker.patch('stevedore.driver.DriverManager', autospec=True)
        instance = manager(namespace='kitovu.sync.plugin', name='test',
                           invoke_on_load=True)
        instance.driver = fake_plugin_obj

        plugin = syncing._find_plugin(self._get_settings('test'))
        assert plugin is fake_plugin_obj

    def _get_settings(self, plugin_type, connection={}, syncs=[]):
        return PluginSettings(
            plugin_type=plugin_type,
            connection=connection,
            syncs=syncs,
        )
