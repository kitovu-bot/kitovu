import pytest
import pathlib
import py.path

import stevedore

from kitovu import utils
from kitovu.sync import syncing
from kitovu.sync.plugin import smb
from kitovu.sync.settings import ConnectionSettings
from helpers import dummyplugin, reporter


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


class TestFindPlugin:

    def test_load_plugin_builtin(self):
        plugin = syncing._load_plugin(self._get_settings('smb', connection={'username': 'test'}), reporter.TestReporter())
        assert isinstance(plugin, smb.SmbPlugin)

    def test_load_plugin_missing_external(self, mocker):
        mocker.patch('stevedore.driver.DriverManager', autospec=True,
                     side_effect=stevedore.exception.NoMatches)

        with pytest.raises(utils.NoPluginError, match='The plugin doesnotexist was not found'):
            syncing._load_plugin(self._get_settings('doesnotexist'), reporter.TestReporter())

    def test_load_plugin_external(self, mocker, dummy_plugin):
        manager = mocker.patch('stevedore.driver.DriverManager', autospec=True)
        instance = manager(namespace='kitovu.sync.plugin', name='test',
                           invoke_on_load=True)
        instance.driver = dummy_plugin

        settings = self._get_settings('test', connection={'some-required-prop': 'test'})
        plugin = syncing._load_plugin(settings, reporter.TestReporter())
        assert plugin is dummy_plugin

    def _get_settings(self, plugin_name, connection={}, subjects=[]):
        return ConnectionSettings(
            plugin_name=plugin_name,
            connection=connection,
            subjects=subjects,
        )


class TestSyncAll:

    @pytest.fixture(autouse=True)
    def include_dummy_plugin(self, mocker, temppath):
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
        })

    def test_complex_sync_all(self, tmpdir: py.path.local):
        config_yml = tmpdir / 'config.yml'
        config_yml.write_text("""
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
        """, encoding='utf-8')
        syncing.start_all(config_yml, reporter.TestReporter())

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
        config_yml = tmpdir / 'config.yml'
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

        syncing.validate_config(config_yml, reporter.TestReporter())

    def test_configuration_without_a_file(self, tmpdir: py.path.local):
        config_yml = tmpdir / 'config.yml'

        with pytest.raises(utils.UsageError) as excinfo:
            syncing.validate_config(pathlib.Path(config_yml), reporter.TestReporter())
        assert str(excinfo.value) == f'Could not find the file {config_yml}'

    def test_configuration_with_an_empty_file(self, tmpdir: py.path.local):
        config_yml = tmpdir / 'config.yml'
        config_yml.ensure()
        assert self._get_config_errors(config_yml) == ["None is not of type 'object'"]

    def test_configuration_with_missing_root_dir(self, tmpdir: py.path.local):
        config_yml = tmpdir / 'config.yml'
        config_yml.write_text("""
        connections: []
        subjects: []
        """, encoding='utf-8')
        assert self._get_config_errors(config_yml) == ["'root-dir' is a required property"]

    def test_configuration_with_missing_subjects(self, tmpdir: py.path.local):
        config_yml = tmpdir / 'config.yml'
        config_yml.write_text("""
        root-dir: some-dir
        connections: []
        """, encoding='utf-8')
        assert self._get_config_errors(config_yml) == ["'subjects' is a required property"]

    def test_configuration_with_missing_connections(self, tmpdir: py.path.local):
        config_yml = tmpdir / 'config.yml'
        config_yml.write_text("""
        root-dir: some-dir
        subjects: []
        """, encoding='utf-8')
        assert self._get_config_errors(config_yml) == ["'connections' is a required property"]

    def test_configuration_with_invalid_subjects(self, tmpdir: py.path.local):
        config_yml = tmpdir / 'config.yml'
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

    def test_configuration_with_invalid_connections(self, mocker, tmpdir: py.path.local, dummy_plugin):
        manager = mocker.patch('stevedore.driver.DriverManager', autospec=True)
        instance = manager(namespace='kitovu.sync.plugin', name='test',
                           invoke_on_load=True)
        instance.driver = dummy_plugin

        config_yml = tmpdir / 'config.yml'
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

    def test_configuration_with_an_empty_connection(self, mocker, tmpdir: py.path.local):
        config_yml = tmpdir / 'config.yml'
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

    def test_configuration_with_an_empty_subject(self, mocker, tmpdir: py.path.local):
        config_yml = tmpdir / 'config.yml'
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
            syncing.validate_config(config_yml, reporter.TestReporter())
        return [error.message for error in excinfo.value.errors]
