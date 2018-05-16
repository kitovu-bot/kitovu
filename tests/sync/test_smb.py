import io
import pathlib
import socket
import logging

import pytest
import attr
import keyring
from smb.SMBConnection import SMBConnection
from smb.smb_structs import OperationFailure, ProtocolError

from kitovu.sync import syncing
from kitovu import utils
from kitovu.sync.plugin import smb


@attr.s
class FakeStatResult:

    st_size: int = attr.ib()
    st_mtime: float = attr.ib()


@pytest.fixture(autouse=True)
def patch(monkeypatch):
    monkeypatch.setattr(smb, 'SMBConnection', SMBConnectionMock)
    monkeypatch.setattr('socket.gethostbyname', lambda _host: '123.123.123.123')
    monkeypatch.setattr('socket.gethostname', lambda: 'my-local-host')


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
        username: str = self.init_args['username']
        if username == 'invalid-user':
            return False
        elif username == 'invalid-user-2':
            # FIXME Can be removed once https://github.com/miketeo/pysmb/issues/108 is fixed
            raise ProtocolError("PySMB bug")

        if ip_address == "1.1.1.1":
            raise ConnectionRefusedError()
        self.connected_ip = ip_address
        self.connected_port = port
        assert self.is_connected()
        return True

    def close(self):
        assert self.is_connected()
        self.connected_ip = None
        self.connected_port = None

    def getAttributes(self, share, path):
        if path.endswith('missing'):
            raise OperationFailure('msg1', 'msg2')
        return self.AttributesMock(1024, 988824605.56)

    def listPath(self, share, path):
        if path.endswith('missing'):
            raise OperationFailure('msg1', 'msg2')
        if str(path).endswith('example_dir') or str(path).endswith('sub'):
            return [self.SharedFileMock('sub_file', False)]
        return [
            self.SharedFileMock('.', True),
            self.SharedFileMock('..', True),
            self.SharedFileMock('example_dir', True),
            self.SharedFileMock('example.txt', False),
            self.SharedFileMock('other_example.txt', False),
            self.SharedFileMock('sub', True),
            self.SharedFileMock('last_file', False),
        ]

    def retrieveFile(self, share, path, fileobj):
        if path.endswith('missing'):
            raise OperationFailure('msg1', 'msg2')
        fileobj.write(b'HELLO KITOVU')

    def is_connected(self):
        return self.connected_ip is not None and self.connected_port is not None


class TestConnect:

    @pytest.fixture
    def plugin(self):
        return smb.SmbPlugin()

    @pytest.fixture
    def info(self):
        """Get connection info (like we'd get it from a config) for tests."""
        keyring.set_password('kitovu-smb', 'myusername\nmyauthdomain\nexample.com', 'some_password')
        return {
            'domain': 'myauthdomain',
            'username': 'myusername',
            'hostname': 'example.com',
            'share': 'myshare',
        }

    @pytest.mark.parametrize('debug', [True, False])
    def test_debug_logging(self, plugin, info, debug):
        if debug:
            info['debug'] = True
        plugin.configure(info)
        assert logging.getLogger('SMB.SMBConnection').propagate == debug

    def test_connect_with_default_options(self, plugin, info):
        plugin.configure(info)
        plugin.connect()

        assert plugin._connection.init_args == {
            'username': 'myusername',
            'password': 'some_password',
            'domain': 'myauthdomain',
            'my_name': 'my-local-host',
            'remote_name': 'example.com',
            'use_ntlm_v2': False,
            'sign_options': SMBConnection.SIGN_WHEN_REQUIRED,
            'is_direct_tcp': True,
        }
        assert plugin._connection.connected_ip == '123.123.123.123'
        assert plugin._connection.connected_port == 445

    def test_connect_with_custom_options(self, plugin, info):
        info['use_ntlm_v2'] = True
        info['sign_options'] = 'when_supported'
        info['is_direct_tcp'] = False

        plugin.configure(info)
        plugin.connect()

        assert plugin._connection.init_args == {
            'username': 'myusername',
            'password': 'some_password',
            'domain': 'myauthdomain',
            'my_name': 'my-local-host',
            'remote_name': 'example.com',
            'use_ntlm_v2': True,
            'sign_options': SMBConnection.SIGN_WHEN_SUPPORTED,
            'is_direct_tcp': False,
        }
        assert plugin._connection.connected_ip == '123.123.123.123'
        assert plugin._connection.connected_port == 139

    def test_connect_with_hsr_config(self, plugin):
        keyring.set_password('kitovu-smb', 'myhsrusername\nHSR\nsvm-c213.hsr.ch', 'some_hsr_password')

        plugin.configure({'username': 'myhsrusername'})
        plugin.connect()

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

    def test_handles_an_inaccessible_server_correctly(self, plugin, info, monkeypatch):
        def raise_error(_host):
            raise socket.gaierror()
        monkeypatch.setattr('socket.gethostbyname', raise_error)

        plugin.configure(info)

        with pytest.raises(utils.PluginOperationError) as excinfo:
            plugin.connect()

        msg = "Could not find server example.com. Maybe you need to open a VPN connection or the server is not available."
        assert str(excinfo.value) == msg

    def test_handles_a_refused_connection(self, plugin, info, monkeypatch):
        monkeypatch.setattr('socket.gethostbyname', lambda _host: '1.1.1.1')

        plugin.configure(info)

        with pytest.raises(utils.PluginOperationError) as excinfo:
            plugin.connect()

        assert str(excinfo.value) == "Could not connect to 1.1.1.1:445"

    @pytest.mark.parametrize('username', ['invalid-user', 'invalid-user-2'])
    def test_handles_invalid_credentials_correctly(self, plugin, info, username):
        keyring.set_password('kitovu-smb', f'{username}\nmyauthdomain\nexample.com', 'some_password')

        info['username'] = username
        plugin.configure(info)

        with pytest.raises(utils.AuthenticationError) as excinfo:
            plugin.connect()

        assert str(excinfo.value) == "Authentication failed for 123.123.123.123:445"


class TestWithConnectedPlugin:

    @pytest.fixture
    def plugin(self):
        plugin = smb.SmbPlugin()
        keyring.set_password('kitovu-smb', 'myusername\nHSR\nsvm-c213.hsr.ch', 'some_password')
        plugin.configure({'username': 'myusername'})
        plugin.connect()
        return plugin

    def test_disconnect(self, plugin):
        assert plugin._connection.is_connected()
        plugin.disconnect()
        assert not plugin._connection.is_connected()

    def test_create_local_digest(self, plugin, monkeypatch, temppath):
        testfile = temppath / 'foo.txt'
        text = 'hello kitovu'
        testfile.write_text(text)

        mtime = 13371337.4242
        monkeypatch.setattr(pathlib.Path, 'lstat', lambda _self:
                            FakeStatResult(st_size=len(text), st_mtime=mtime))

        plugin.create_local_digest(testfile)

        assert plugin.create_local_digest(testfile) == f'{len(text)}-13371337'

    def test_create_remote_digest(self, plugin):
        assert plugin.create_remote_digest(pathlib.PurePath('/test')) == '1024-988824605'

    def test_create_remote_digest_with_an_error(self, plugin):
        path = pathlib.PurePath('/test/missing')
        with pytest.raises(utils.PluginOperationError) as excinfo:
            plugin.create_remote_digest(path)

        assert str(excinfo.value) == f'Could not find remote file {path} in share "skripte"'

    def test_list_path(self, plugin):
        paths = list(plugin.list_path(pathlib.PurePath('/some/test/dir')))
        assert paths == [
            pathlib.PurePath('/some/test/dir/example_dir/sub_file'),
            pathlib.PurePath('/some/test/dir/example.txt'),
            pathlib.PurePath('/some/test/dir/other_example.txt'),
            pathlib.PurePath('/some/test/dir/sub/sub_file'),
            pathlib.PurePath('/some/test/dir/last_file'),
        ]

    def test_list_path_with_an_error(self, plugin):
        path = pathlib.PurePath('/test/missing')
        with pytest.raises(utils.PluginOperationError) as excinfo:
            list(plugin.list_path(path))

        assert str(excinfo.value) == f'Folder "{path}" not found'

    def test_retrieve_file(self, plugin):
        fileobj = io.BytesIO()
        path = pathlib.PurePath('foo.txt')
        plugin.create_remote_digest(path)

        mtime = 988824605.56
        assert plugin.retrieve_file(path, fileobj) == mtime
        assert fileobj.getvalue() == b"HELLO KITOVU"

    def test_retrieve_file_error(self, plugin):
        with pytest.raises(utils.PluginOperationError):
            plugin.retrieve_file(pathlib.PurePath('foo.missing'), io.BytesIO())


class TestValidations:

    def test_configuration_with_the_minimum_required_fields(self, mocker, temppath: pathlib.Path):
        config_yml = temppath / 'config.yml'
        config_yml.write_text("""
        root-dir: ./asdf
        connections:
          - name: mytest-plugin
            plugin: smb
            username: myuser
        subjects:
          - name: test-subject
            sources:
              - connection: mytest-plugin
                remote-dir: /test/dir
        """, encoding='utf-8')

        syncing.validate_config(config_yml)

    def test_configuration_with_the_all_available_fields(self, mocker, temppath: pathlib.Path):
        config_yml = temppath / 'config.yml'
        config_yml.write_text("""
        root-dir: ./asdf
        connections:
          - name: mytest-plugin
            plugin: smb
            hostname: example.com
            port: 1234
            share: my-share
            domain: my-domain
            username: myuser
            sign_options: never
            use_ntlm_v2: true
            is_direct_tcp: false
        subjects:
          - name: test-subject
            sources:
              - connection: mytest-plugin
                remote-dir: /test/dir
        """, encoding='utf-8')

        syncing.validate_config(config_yml)

    def test_configuration_with_unexpected_fields(self, mocker, temppath: pathlib.Path):
        config_yml = temppath / 'config.yml'
        config_yml.write_text("""
        root-dir: ./asdf
        connections:
          - name: mytest-plugin
            plugin: smb
            host: example.com
            sign_options: some-other-value
        subjects:
          - name: test-subject
            sources:
              - connection: mytest-plugin
                remote-dir: /test/dir
        """, encoding='utf-8')

        assert self._get_config_errors(config_yml) == [
            "'some-other-value' is not one of ['never', 'when_supported', 'when_required']",
            "'username' is a required property",
            "Additional properties are not allowed ('host' was unexpected)",
        ]

    def _get_config_errors(self, config_yml):
        with pytest.raises(utils.InvalidSettingsError) as excinfo:
            syncing.validate_config(config_yml)
        return [error.message for error in excinfo.value.errors]
