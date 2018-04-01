import pytest

import stevedore

from kitovu import utils
from kitovu.sync import syncing
from kitovu.sync.plugin import smb


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
