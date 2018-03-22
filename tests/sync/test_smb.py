from unittest import mock
import pytest

import keyring
from smb.SMBConnection import SMBConnection

from kitovu.sync.plugin import smb


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
    def __init__(self, **kwargs):
        self.init_args = kwargs
        self.connected_ip = None
        self.connected_port = None

    def connect(self, ip_address, port):
        self.connected_ip = ip_address
        self.connected_port = port
        return True

    def is_connected(self):
        return self.connected_ip is not None and self.connected_port is not None

    def disconnect(self):
        self._ensure_connected()
        self.connected_ip = None
        self.connected_port = None

    def _ensure_connected(self):
        if not self.is_connected():
            raise Exception('Not connected!')


@mock.patch('kitovu.sync.plugin.smb.SMBConnection', new=SMBConnectionMock)
@mock.patch('socket.gethostbyname', mock.MagicMock(return_value='123.123.123.123'))
@mock.patch('socket.gethostname', mock.MagicMock(return_value='my-local-host'))
class TestConnect():
    def test_connect_with_default_options(self):
        url = 'smb://myauthdomain;myusername@myserver.test/some/path'
        keyring.set_password('kitovu', url, 'some_password')
        plugin = smb.SmbPlugin()
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

    def test_connect_with_custom_options(self):
        url = 'smb://myauthdomain;myusername@myserver.test/some/path'
        keyring.set_password('kitovu', url, 'some_password')
        plugin = smb.SmbPlugin()
        plugin.connect(url, {
            'use_ntlm_v2': True, 'sign_options': 'when_supported', 'is_direct_tcp': False
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

    def test_connect_with_hsr_url(self):
        url = 'smb://myhsrusername@hsr.ch/some/path'
        keyring.set_password('kitovu', url, 'some_hsr_password')
        plugin = smb.SmbPlugin()
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
