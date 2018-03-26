import pathlib

import pytest
import attr
import keyring
from smb.SMBConnection import SMBConnection

from kitovu.sync.plugin import smb


@pytest.fixture(autouse=True)
def patch(monkeypatch):
    monkeypatch.setattr(smb, 'SMBConnection', SMBConnectionMock)
    monkeypatch.setattr('socket.gethostbyname', lambda _host: '123.123.123.123')
    monkeypatch.setattr('socket.gethostname', lambda: 'my-local-host')


@pytest.mark.parametrize('url, expected', [
    # @hsr.ch shorthand
    ('smb://testuser@hsr.ch', smb._LoginInfo(
        username='testuser', hostname='svm-c213.hsr.ch', share='skripte',
        domain='HSR', port=445)),
    # Other SMB server
    ('smb://user@example.com/share', smb._LoginInfo(
        username='user', hostname='example.com', share='share',
        domain=None, port=None)),
    # Other server with domain
    ('smb://domain;user@example.com/share', smb._LoginInfo(
        username='user', hostname='example.com', share='share',
        domain='domain', port=None)),
])
def test_parse_url(url: str, expected: smb._LoginInfo):
    assert smb._parse_url(url) == expected


class SMBConnectionMock:

    @attr.s
    class AttributesMock:

        file_size = attr.ib()
        last_write_time = attr.ib()

    @attr.s
    class SharedFileMock:

        filename = attr.ib()
        isDirectory = attr.ib()

    def __init__(self, **kwargs):
        self.init_args = kwargs
        self.connected_ip = None
        self.connected_port = None

    def connect(self, ip_address, port):
        self.connected_ip = ip_address
        self.connected_port = port
        assert self.is_connected()
        return True

    def close(self):
        assert self.is_connected()
        self.connected_ip = None
        self.connected_port = None

    def getAttributes(self, share, path):
        return self.AttributesMock(1024, 988824605.56)

    def listPath(self, share, path):
        return [
            self.SharedFileMock('example_dir', True),
            self.SharedFileMock('example.txt', False),
            self.SharedFileMock('other_example.txt', False),
            self.SharedFileMock('sub', True),
            self.SharedFileMock('last_file', False),
        ]

    def is_connected(self):
        return self.connected_ip is not None and self.connected_port is not None


class TestConnect:

    @pytest.fixture
    def plugin(self):
        return smb.SmbPlugin()

    def test_connect_with_default_options(self, plugin):
        url = 'smb://myauthdomain;myusername@myserver.test/some/path'
        keyring.set_password('kitovu', url, 'some_password')
        plugin.connect(url, {})
        assert plugin._connection.init_args == {
            'username': 'myusername',
            'password': 'some_password',
            'domain': 'myauthdomain',
            'my_name': 'my-local-host',
            'remote_name': 'myserver.test',
            'use_ntlm_v2': False,
            'sign_options': SMBConnection.SIGN_WHEN_REQUIRED,
            'is_direct_tcp': True,
        }
        assert plugin._connection.connected_ip == '123.123.123.123'
        assert plugin._connection.connected_port == 445

    def test_connect_with_custom_options(self, plugin):
        url = 'smb://myauthdomain;myusername@myserver.test/some/path'
        keyring.set_password('kitovu', url, 'some_password')
        plugin.connect(url, {
            'use_ntlm_v2': True,
            'sign_options': 'when_supported',
            'is_direct_tcp': False,
        })
        assert plugin._connection.init_args == {
            'username': 'myusername',
            'password': 'some_password',
            'domain': 'myauthdomain',
            'my_name': 'my-local-host',
            'remote_name': 'myserver.test',
            'use_ntlm_v2': True,
            'sign_options': SMBConnection.SIGN_WHEN_SUPPORTED,
            'is_direct_tcp': False,
        }
        assert plugin._connection.connected_ip == '123.123.123.123'
        assert plugin._connection.connected_port == 139

    def test_connect_with_hsr_url(self, plugin):
        url = 'smb://myhsrusername@hsr.ch/some/path'
        keyring.set_password('kitovu', url, 'some_hsr_password')
        plugin.connect(url, {})
        assert plugin._connection.init_args == {
            'username': 'myhsrusername',
            'password': 'some_hsr_password',
            'domain': 'HSR',
            'my_name': 'my-local-host',
            'remote_name': 'svm-c213.hsr.ch',
            'use_ntlm_v2': False,
            'sign_options': SMBConnection.SIGN_WHEN_REQUIRED,
            'is_direct_tcp': True,
        }
        assert plugin._connection.connected_ip == '123.123.123.123'
        assert plugin._connection.connected_port == 445


class TestWithConnectedPlugin:

    @pytest.fixture
    def plugin(self):
        plugin = smb.SmbPlugin()
        url = 'smb://myauthdomain;myusername@myserver.test/some/path'
        keyring.set_password('kitovu', url, 'some_password')
        plugin.connect(url, {})
        return plugin

    def test_disconnect(self, plugin):
        assert plugin._connection.is_connected()
        plugin.disconnect()
        assert not plugin._connection.is_connected()

    def test_create_remote_digest(self, plugin):
        assert plugin.create_remote_digest(pathlib.PurePath('/test')) == '1024-988824605'

    def test_list_path(self, plugin):
        paths = list(plugin.list_path(pathlib.PurePath('/some/test/dir')))
        assert paths == [
            pathlib.PurePath('/some/test/dir/example.txt'),
            pathlib.PurePath('/some/test/dir/other_example.txt'),
            pathlib.PurePath('/some/test/dir/last_file'),
        ]
