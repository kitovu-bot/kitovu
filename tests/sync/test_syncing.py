import pytest
import typing
import pathlib
import py.path

import stevedore

from kitovu import utils
from kitovu.sync import syncing
from kitovu.sync.plugin import smb
from kitovu.sync.settings import PluginSettings
from kitovu.sync.syncplugin import AbstractSyncPlugin


class FakePlugin(AbstractSyncPlugin):
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

    def connection_schema(self) -> typing.Dict[str, typing.Any]:
        return {
            'type': 'object',
            'properties': {
                'some-required-prop': {'type': 'string'},
                'some-optional-prop': {'type': 'string'},
            },
            'required': ['some-required-prop'],
            'allowAdditional': False,
        }


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

        plugin = syncing._find_plugin(self._get_settings('test', connection={'some-required-prop': 'test'}))
        assert plugin is fake_plugin_obj

    def _get_settings(self, plugin_type, connection={}, syncs=[]):
        return PluginSettings(
            plugin_type=plugin_type,
            connection=connection,
            syncs=syncs,
        )


class TestConfigError:
    def test_valid_configuration(self, tmpdir: py.path.local):
        file_name = pathlib.Path(tmpdir / 'config.yml')
        with file_name.open('w') as f:
            f.write("""
            root-dir: ./asdf
            plugins:
              - name: mytest-plugin
                type: smb
                username: myuser
              - name: another-plugin
                type: smb
                username: otheruser
            syncs:
              - name: sync-1
                plugins:
                  - plugin: mytest-plugin
                    remote-dir: Some/Test/Dir1
                  - plugin: another-plugin
                    remote-dir: Another/Test/Dir1
              - name: sync-2
                plugins:
                  - plugin: mytest-plugin
                    remote-dir: Some/Test/Dir2
                  - plugin: another-plugin
                    remote-dir: Another/Test/Dir2
            """)
        assert syncing.config_error(file_name) is None

    def test_configuration_without_a_file(self, tmpdir: py.path.local):
        file_name = pathlib.Path(tmpdir / 'config.yml')
        assert syncing.config_error(file_name) == f'Could not find the file {file_name}'

    def test_configuration_with_an_empty_file(self, tmpdir: py.path.local):
        file_name = pathlib.Path(tmpdir / 'config.yml')
        with file_name.open('w') as f:
            f.write("")
        assert syncing.config_error(file_name).startswith("None is not of type 'object'\n")

    def test_configuration_with_missing_root_dir(self, tmpdir: py.path.local):
        file_name = pathlib.Path(tmpdir / 'config.yml')
        with file_name.open('w') as f:
            f.write("""
            plugins: []
            syncs: []
            """)
        assert syncing.config_error(file_name).startswith("'root-dir' is a required property\n")

    def test_configuration_with_missing_syncs(self, tmpdir: py.path.local):
        file_name = pathlib.Path(tmpdir / 'config.yml')
        with file_name.open('w') as f:
            f.write("""
            root-dir: some-dir
            plugins: []
            """)
        assert syncing.config_error(file_name).startswith("'syncs' is a required property\n")

    def test_configuration_with_missing_plugins(self, tmpdir: py.path.local):
        file_name = pathlib.Path(tmpdir / 'config.yml')
        with file_name.open('w') as f:
            f.write("""
            root-dir: some-dir
            syncs: []
            """)
        assert syncing.config_error(file_name).startswith("'plugins' is a required property\n")

    def test_configuration_with_invalid_syncs(self, tmpdir: py.path.local):
        file_name = pathlib.Path(tmpdir / 'config.yml')
        with file_name.open('w') as f:
            f.write("""
            root-dir: ./asdf
            plugins:
              - name: mytest-plugin
                type: smb
                username: myuser
            syncs:
              - name: sync-1
                plugins:
                  - remote-dir: Some/Test/Dir2
            """)
        assert syncing.config_error(file_name).startswith("'plugin' is a required property\n")

    def test_configuration_with_invalid_plugins(self, mocker, tmpdir: py.path.local):
        fake_plugin_obj = FakePlugin()
        manager = mocker.patch('stevedore.driver.DriverManager', autospec=True)
        instance = manager(namespace='kitovu.sync.plugin', name='test',
                           invoke_on_load=True)
        instance.driver = fake_plugin_obj

        file_name = pathlib.Path(tmpdir / 'config.yml')
        with file_name.open('w') as f:
            f.write("""
            root-dir: ./asdf
            plugins:
              - name: mytest-plugin
                type: test
            syncs:
              - name: sync-1
                plugins:
                  - plugin: mytest-plugin
                    remote-dir: Some/Test/Dir
            """)
        assert syncing.config_error(file_name).startswith("'some-required-prop' is a required property\n")
