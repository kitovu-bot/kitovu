import pytest
import pathlib
import py.path
import glob

import stevedore

from kitovu import utils
from kitovu.sync import syncing
from kitovu.sync.plugin import smb
from helpers import dummyplugin


class TestFindPlugin:

    def test_find_plugin_builtin(self):
        plugin = syncing._find_plugin('smb')
        assert isinstance(plugin, smb.SmbPlugin)

    def test_find_plugin_missing_external(self, mocker):
        mocker.patch('stevedore.driver.DriverManager', autospec=True,
                     side_effect=stevedore.exception.NoMatches)

        with pytest.raises(utils.NoPluginError, match='The plugin doesnotexist was not found'):
            syncing._find_plugin('doesnotexist')

    def test_find_plugin_external(self, mocker):
        fake_plugin_obj = object()
        manager = mocker.patch('stevedore.driver.DriverManager', autospec=True)
        instance = manager(namespace='kitovu.sync.plugin', name='test',
                           invoke_on_load=True)
        instance.driver = fake_plugin_obj

        plugin = syncing._find_plugin('test')
        assert plugin is fake_plugin_obj


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
            root-dir: {tmpdir}
            plugins:
              - name: mytest-plugin
                type: dummy
              - name: another-plugin
                type: dummy
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
        syncing.start_all(file_name)

        assert sorted(glob.glob(f"{tmpdir}/**/*")) == [
            f'{tmpdir}/sync-1/group1-file1.txt',
            f'{tmpdir}/sync-1/group1-file2.txt',
            f'{tmpdir}/sync-1/group1-file3.txt',
            f'{tmpdir}/sync-1/group2-file1.txt',
            f'{tmpdir}/sync-1/group2-file2.txt',
            f'{tmpdir}/sync-2/group3-file1.txt',
            f'{tmpdir}/sync-2/group3-file2.txt',
            f'{tmpdir}/sync-2/group4-file1.txt',
            f'{tmpdir}/sync-2/group4-file2.txt',
        ]
