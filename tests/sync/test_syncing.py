import pathlib

import appdirs
import stevedore
import pytest

from kitovu import utils
from kitovu.sync import syncing
from kitovu.sync.plugin import smb
from kitovu.sync.settings import ConnectionSettings
from helpers import dummyplugin


@pytest.fixture(autouse=True)
def patch(monkeypatch, temppath):
    monkeypatch.setattr(appdirs, "user_data_dir", lambda _path: str(temppath))


@pytest.fixture
def dummy_plugin(temppath):
    return dummyplugin.DummyPlugin(temppath=temppath, connection_schema={
        'type': 'object',
        'properties': {
            'some-required-prop': {'type': 'string'},
            'some-optional-prop': {'type': 'string'},
        },
        'required': ['some-required-prop'],
        'additionalProperties': False,
    })


@pytest.fixture
def patch_dummy_plugin(dummy_plugin, mocker):
    manager = mocker.patch('stevedore.driver.DriverManager', autospec=True)
    instance = manager(namespace='kitovu.sync.plugin', name='test',
                       invoke_on_load=True)
    instance.driver = dummy_plugin


class TestFindPlugin:

    def test_load_plugin_builtin(self):
        plugin = syncing._load_plugin(self._get_settings('smb', connection={'username': 'test'}))
        assert isinstance(plugin, smb.SmbPlugin)

    def test_load_plugin_missing_external(self, mocker):
        mocker.patch('stevedore.driver.DriverManager', autospec=True,
                     side_effect=stevedore.exception.NoMatches)

        with pytest.raises(utils.NoPluginError, match='The plugin doesnotexist was not found'):
            syncing._load_plugin(self._get_settings('doesnotexist'))

    def test_load_plugin_external(self, mocker, dummy_plugin):
        manager = mocker.patch('stevedore.driver.DriverManager', autospec=True)
        instance = manager(namespace='kitovu.sync.plugin', name='test',
                           invoke_on_load=True)
        instance.driver = dummy_plugin

        settings = self._get_settings('test', connection={'some-required-prop': 'test'})
        plugin = syncing._load_plugin(settings)
        assert plugin is dummy_plugin

    def _get_settings(self, plugin_name, connection={}, subjects=[]):
        return ConnectionSettings(
            plugin_name=plugin_name,
            connection=connection,
            subjects=subjects,
        )


class TestSyncAll:

    @pytest.fixture(autouse=True)
    def configured_dummy_plugin(self, mocker, temppath):
        manager = mocker.patch('stevedore.driver.DriverManager', autospec=True)
        instance = manager(namespace='kitovu.sync.plugin', name='dummy',
                           invoke_on_load=True)
        instance.driver = dummyplugin.DummyPlugin(temppath, remote_digests={
            pathlib.PurePath('Some/Test/Dir1/group1-file1.txt'): '11',
            pathlib.PurePath('Some/Test/Dir1/group1-file2.txt'): '12',
            pathlib.PurePath('Some/Test/Dir1/group1-file3.txt'): '13',
            pathlib.PurePath('Another/Test/Dir1/group2-file1.txt'): '21',
            pathlib.PurePath('Another/Test/Dir1/group2-file2.txt'): '22',
            pathlib.PurePath('Some/Test/Dir2/group3-file1.txt'): '31',
            pathlib.PurePath('Some/Test/Dir2/group3-file2.txt'): '32',
            pathlib.PurePath('Another/Test/Dir2/group4-file1.txt'): '41',
            pathlib.PurePath('Another/Test/Dir2/group4-file2.txt'): '42',
        }, local_digests={
            temppath / 'syncs/sync-1/group1-file1.txt': '11',
        })
        return instance.driver

    @pytest.mark.parametrize('mtime', [None, 13371337])
    def test_complex_sync_all(self, mtime, temppath: pathlib.Path, configured_dummy_plugin):
        configured_dummy_plugin.mtime = mtime

        group1_file1 = temppath / 'syncs/sync-1/group1-file1.txt'
        group1_file1.parent.mkdir(parents=True)
        group1_file1.touch()

        group1_file2 = temppath / 'syncs/sync-1/group1-file2.txt'

        config_yml = temppath / 'config.yml'
        config_yml.write_text(f"""
        root-dir: {temppath}/syncs
        global-ignore:
            - group3-file1.txt
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
        """, encoding='utf-8')
        syncing.start_all(config_yml)

        assert sorted(pathlib.Path(temppath).glob("syncs/**/*")) == [
            temppath / 'syncs/sync-1',
            group1_file1,
            group1_file2,
            temppath / 'syncs/sync-1/group1-file3.txt',
            temppath / 'syncs/sync-1/group2-file1.txt',
            temppath / 'syncs/sync-1/group2-file2.txt',
            temppath / 'syncs/sync-2',
            temppath / 'syncs/sync-2/group3-file2.txt',
            temppath / 'syncs/sync-2/group4-file1.txt',
            temppath / 'syncs/sync-2/group4-file2.txt',
        ]

        if mtime is not None:
            assert int(group1_file1.stat().st_mtime) != mtime  # no remote changes
            assert int(group1_file2.stat().st_mtime) == mtime


class TestErrorHandling:

    @pytest.fixture
    def connection_settings(self, patch_dummy_plugin):
        return ConnectionSettings(
            plugin_name='dummy',
            connection={'some-required-prop': 'foo'},
            subjects=[{
                'name': 'subject1',
                'remote-dir': 'remote_dir/test',
                'local-dir': 'local_dir/test',
                'ignore': [],
            }],
        )

    def test_connection_error(self, dummy_plugin, connection_settings, caplog):
        dummy_plugin.error_connect = True
        syncing._start('connection', connection_settings)

        expected = 'Error from dummyplugin plugin: Could not connect, skipping this plugin'
        record = caplog.records[-1]
        assert record.message == expected

    def test_list_path_error(self, dummy_plugin, connection_settings, caplog):
        dummy_plugin.error_list_path = True
        syncing._start('connection', connection_settings)

        expected = 'Error from dummyplugin plugin: Could not list path, skipping this subject'
        record = caplog.records[-1]
        assert record.message == expected

    def test_create_remote_digest_error(self, dummy_plugin, connection_settings, caplog):
        dummy_plugin.error_create_remote_digest = True
        syncing._start('connection', connection_settings)

        expected = 'Error from dummyplugin plugin: Could not create remote digest, skipping this file'
        record = caplog.records[-1]
        assert record.message == expected


class TestConfigError:

    def test_valid_configuration(self, temppath: pathlib.Path):
        config_yml = temppath / 'config.yml'
        config_yml.write_text(f"""
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
        """, encoding='utf-8')

        syncing.validate_config(config_yml)

    def test_configuration_without_a_file(self, temppath: pathlib.Path):
        config_yml = temppath / 'config.yml'

        with pytest.raises(utils.UsageError) as excinfo:
            syncing.validate_config(pathlib.Path(config_yml))
        assert str(excinfo.value) == f'Could not find the file {config_yml}'

    def test_configuration_with_an_empty_file(self, temppath: pathlib.Path):
        config_yml = temppath / 'config.yml'
        config_yml.touch()
        assert self._get_config_errors(config_yml) == ["None is not of type 'object'"]

    def test_configuration_with_missing_root_dir(self, temppath: pathlib.Path):
        config_yml = temppath / 'config.yml'
        config_yml.write_text("""
        connections: []
        subjects: []
        """, encoding='utf-8')
        assert self._get_config_errors(config_yml) == ["'root-dir' is a required property"]

    def test_configuration_with_missing_subjects(self, temppath: pathlib.Path):
        config_yml = temppath / 'config.yml'
        config_yml.write_text("""
        root-dir: some-dir
        connections: []
        """, encoding='utf-8')
        assert self._get_config_errors(config_yml) == ["'subjects' is a required property"]

    def test_configuration_with_missing_connections(self, temppath: pathlib.Path):
        config_yml = temppath / 'config.yml'
        config_yml.write_text("""
        root-dir: some-dir
        subjects: []
        """, encoding='utf-8')
        assert self._get_config_errors(config_yml) == ["'connections' is a required property"]

    def test_configuration_with_invalid_subjects(self, temppath: pathlib.Path):
        config_yml = temppath / 'config.yml'
        config_yml.write_text("""
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
        """, encoding='utf-8')
        assert self._get_config_errors(config_yml) == [
            "'connection' is a required property",
            "Additional properties are not allowed ('unexpected_prop' was unexpected)",
        ]

    def test_configuration_with_invalid_connections(self, temppath: pathlib.Path, patch_dummy_plugin):
        config_yml = temppath / 'config.yml'
        config_yml.write_text("""
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
        """, encoding='utf-8')
        assert self._get_config_errors(config_yml) == [
            "'some-required-prop' is a required property",
            "'username' is a required property",
        ]

    def test_configuration_with_an_empty_connection(self, mocker, temppath: pathlib.Path):
        config_yml = temppath / 'config.yml'
        config_yml.write_text("""
        root-dir: ./asdf
        connections:
          - {}
          - plugin: test
        subjects:
          - name: sync-1
            sources:
              - connection: mytest-plugin
                remote-dir: Some/Test/Dir
        """, encoding='utf-8')
        assert self._get_config_errors(config_yml) == [
            "'name' is a required property",
            "'plugin' is a required property",
            "'name' is a required property",
        ]

    def test_configuration_with_an_empty_subject(self, mocker, temppath: pathlib.Path):
        config_yml = temppath / 'config.yml'
        config_yml.write_text("""
        root-dir: ./asdf
        connections:
          - name: mytest-plugin
            plugin: smb
            username: myuser
        subjects:
          - {}
          - name: mytest
        """, encoding='utf-8')
        assert self._get_config_errors(config_yml) == [
            "'name' is a required property",
            "'sources' is a required property",
            "'sources' is a required property",
        ]

    def _get_config_errors(self, config_yml):
        with pytest.raises(utils.InvalidSettingsError) as excinfo:
            syncing.validate_config(config_yml)
        return [error.message for error in excinfo.value.errors]
