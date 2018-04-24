import pytest
import typing
import pathlib
import py.path

import stevedore

from kitovu import utils
from kitovu.sync import syncing
from kitovu.sync.plugin import smb
from kitovu.sync.settings import ConnectionSettings
from kitovu.sync.syncplugin import AbstractSyncPlugin
from helpers import dummyplugin


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
            'additionalProperties': False,
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

        settings = self._get_settings('test', connection={'some-required-prop': 'test'})
        plugin = syncing._find_plugin(settings)
        assert plugin is fake_plugin_obj

    def _get_settings(self, plugin_name, connection={}, subjects=[]):
        return ConnectionSettings(
            plugin_name=plugin_name,
            connection=connection,
            subjects=subjects,
        )


class TestSyncAll:
    @pytest.fixture(autouse=True)
    def include_dummy_plugin(self, mocker):
        manager = mocker.patch('stevedore.driver.DriverManager', autospec=True)
        instance = manager(namespace='kitovu.sync.plugin', name='dummy',
                           invoke_on_load=True)
        instance.driver = dummyplugin.DummyPlugin(remote_digests={
            pathlib.PurePath('Some/Test/Dir1/group1-file1.txt'): '11',
            pathlib.PurePath('Some/Test/Dir1/group1-file2.txt'): '12',
            pathlib.PurePath('Some/Test/Dir1/group1-file3.txt'): '13',
            pathlib.PurePath('Another/Test/Dir1/group2-file1.txt'): '21',
            pathlib.PurePath('Another/Test/Dir1/group2-file2.txt'): '22',
            pathlib.PurePath('Some/Test/Dir2/group3-file1.txt'): '31',
            pathlib.PurePath('Some/Test/Dir2/group3-file2.txt'): '32',
            pathlib.PurePath('Another/Test/Dir2/group4-file1.txt'): '41',
            pathlib.PurePath('Another/Test/Dir2/group4-file2.txt'): '42',
        })

    def test_complex_sync_all(self, tmpdir: py.path.local):
        file_name = pathlib.Path(tmpdir / 'config.yml')
        with file_name.open('w') as f:
            f.write(f"""
            root-dir: {tmpdir}/syncs
            connections:
              - name: mytest-plugin
                plugin: dummy
              - name: another-plugin
                plugin: dummy
            subjects:
              - name: sync-1
                sources:
                  - connection: mytest-plugin
                    remote-dir: Some/Test/Dir1
                  - connection: another-plugin
                    remote-dir: Another/Test/Dir1
              - name: sync-2
                sources:
                  - connection: mytest-plugin
                    remote-dir: Some/Test/Dir2
                  - connection: another-plugin
                    remote-dir: Another/Test/Dir2
            """)
        syncing.start_all(file_name)

        assert sorted(pathlib.Path(tmpdir).glob("syncs/**/*")) == [
            pathlib.Path(f'{tmpdir}/syncs/sync-1'),
            pathlib.Path(f'{tmpdir}/syncs/sync-1/group1-file1.txt'),
            pathlib.Path(f'{tmpdir}/syncs/sync-1/group1-file2.txt'),
            pathlib.Path(f'{tmpdir}/syncs/sync-1/group1-file3.txt'),
            pathlib.Path(f'{tmpdir}/syncs/sync-1/group2-file1.txt'),
            pathlib.Path(f'{tmpdir}/syncs/sync-1/group2-file2.txt'),
            pathlib.Path(f'{tmpdir}/syncs/sync-2'),
            pathlib.Path(f'{tmpdir}/syncs/sync-2/group3-file1.txt'),
            pathlib.Path(f'{tmpdir}/syncs/sync-2/group3-file2.txt'),
            pathlib.Path(f'{tmpdir}/syncs/sync-2/group4-file1.txt'),
            pathlib.Path(f'{tmpdir}/syncs/sync-2/group4-file2.txt'),
        ]


class TestConfigError:
    def test_valid_configuration(self, tmpdir: py.path.local):
        file_name = pathlib.Path(tmpdir / 'config.yml')
        with file_name.open('w') as f:
            f.write("""
            root-dir: ./asdf
            connections:
              - name: mytest-plugin
                plugin: smb
                username: myuser
              - name: another-plugin
                plugin: smb
                username: otheruser
            subjects:
              - name: sync-1
                sources:
                  - connection: mytest-plugin
                    remote-dir: Some/Test/Dir1
                  - connection: another-plugin
                    remote-dir: Another/Test/Dir1
              - name: sync-2
                sources:
                  - connection: mytest-plugin
                    remote-dir: Some/Test/Dir2
                  - connection: another-plugin
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
        assert self._get_config_errors(file_name) == ["None is not of type 'object'"]

    def test_configuration_with_missing_root_dir(self, tmpdir: py.path.local):
        file_name = pathlib.Path(tmpdir / 'config.yml')
        with file_name.open('w') as f:
            f.write("""
            connections: []
            subjects: []
            """)
        assert self._get_config_errors(file_name) == ["'root-dir' is a required property"]

    def test_configuration_with_missing_subjects(self, tmpdir: py.path.local):
        file_name = pathlib.Path(tmpdir / 'config.yml')
        with file_name.open('w') as f:
            f.write("""
            root-dir: some-dir
            connections: []
            """)
        assert self._get_config_errors(file_name) == ["'subjects' is a required property"]

    def test_configuration_with_missing_connections(self, tmpdir: py.path.local):
        file_name = pathlib.Path(tmpdir / 'config.yml')
        with file_name.open('w') as f:
            f.write("""
            root-dir: some-dir
            subjects: []
            """)
        assert self._get_config_errors(file_name) == ["'connections' is a required property"]

    def test_configuration_with_invalid_subjects(self, tmpdir: py.path.local):
        file_name = pathlib.Path(tmpdir / 'config.yml')
        with file_name.open('w') as f:
            f.write("""
            root-dir: ./asdf
            connections:
              - name: mytest-plugin
                plugin: smb
                username: myuser
            subjects:
              - name: sync-1
                unexpected_prop: asdf
                sources:
                  - remote-dir: Some/Test/Dir2
            """)
        assert self._get_config_errors(file_name) == [
            "'connection' is a required property",
            "Additional properties are not allowed ('unexpected_prop' was unexpected)",
        ]

    def test_configuration_with_invalid_connections(self, mocker, tmpdir: py.path.local):
        fake_plugin_obj = FakePlugin()
        manager = mocker.patch('stevedore.driver.DriverManager', autospec=True)
        instance = manager(namespace='kitovu.sync.plugin', name='test',
                           invoke_on_load=True)
        instance.driver = fake_plugin_obj

        file_name = pathlib.Path(tmpdir / 'config.yml')
        with file_name.open('w') as f:
            f.write("""
            root-dir: ./asdf
            connections:
              - name: mytest-plugin
                plugin: test
              - name: other-plugin
                plugin: smb
            subjects:
              - name: sync-1
                sources:
                  - connection: mytest-plugin
                    remote-dir: Some/Test/Dir
            """)
        assert self._get_config_errors(file_name) == [
            "'some-required-prop' is a required property",
            "'username' is a required property",
        ]

    def test_configuration_with_an_empty_connection(self, mocker, tmpdir: py.path.local):
        file_name = pathlib.Path(tmpdir / 'config.yml')
        with file_name.open('w') as f:
            f.write("""
            root-dir: ./asdf
            connections:
              - {}
              - plugin: test
            subjects:
              - name: sync-1
                sources:
                  - connection: mytest-plugin
                    remote-dir: Some/Test/Dir
            """)
        assert self._get_config_errors(file_name) == [
            "'name' is a required property",
            "'plugin' is a required property",
            "'name' is a required property",
        ]

    def test_configuration_with_an_empty_subject(self, mocker, tmpdir: py.path.local):
        file_name = pathlib.Path(tmpdir / 'config.yml')
        with file_name.open('w') as f:
            f.write("""
            root-dir: ./asdf
            connections:
              - name: mytest-plugin
                plugin: smb
                username: myuser
            subjects:
              - {}
              - name: mytest
            """)
        assert self._get_config_errors(file_name) == [
            "'name' is a required property",
            "'sources' is a required property",
            "'sources' is a required property",
        ]

    def _get_config_errors(self, file_name):
        lines = syncing.config_error(file_name).split('\n')
        return [line for line in lines if line and not line.startswith('\t')]
