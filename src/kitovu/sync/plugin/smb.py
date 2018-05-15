"""A plugin to sync data via SMB/CIFS (Windows fileshares)."""

import enum
import socket
import typing
import pathlib
import logging

import attr
from smb.SMBConnection import SMBConnection
from smb.base import SharedFile
from smb.smb_structs import OperationFailure, ProtocolError

from kitovu import utils
from kitovu.sync import syncplugin


logger: logging.Logger = logging.getLogger(__name__)


class _SignOptions(enum.IntEnum):

    """Enum for possible signing options from PySMB.

    See http://pysmb.readthedocs.io/en/latest/api/smb_SMBConnection.html?highlight=SIGN_NEVER#smb.SMBConnection.SMBConnection.__init__
    (the sign_options parameter).
    """

    never = SMBConnection.SIGN_NEVER
    when_supported = SMBConnection.SIGN_WHEN_SUPPORTED
    when_required = SMBConnection.SIGN_WHEN_REQUIRED


@attr.s
class _ConnectionInfo:

    username: str = attr.ib(None)
    password: str = attr.ib(None)
    hostname: str = attr.ib(None)
    share: str = attr.ib(None)
    domain: typing.Optional[str] = attr.ib(None)
    port: typing.Optional[int] = attr.ib(None)
    use_ntlm_v2: bool = attr.ib(None)
    sign_options: _SignOptions = attr.ib(None)
    is_direct_tcp: bool = attr.ib(None)


class SmbPlugin(syncplugin.AbstractSyncPlugin):

    NAME: str = "smb"

    def __init__(self) -> None:
        self._connection: SMBConnection = None
        self._info = _ConnectionInfo()
        self._attributes: typing.Dict[pathlib.PurePath, SharedFile] = {}

    def _password_identifier(self) -> str:
        """Get an unique identifier for the connection in self._info.

        The identifier is used to request/store passwords. Thus, it contains all
        information associated with a connection and a user account.

        A newline is used as a separator because it shouldn't cause any trouble
        in the password backend, but still should never be part of a
        username/domain/hostname.

        It does *not* contain the port, as it could be possible to access the
        same SMB server via different protocol versions that way, and that's
        probably more likely than having different SMB servers running on the
        same host.
        """
        domain: str = self._info.domain if self._info.domain else ''
        return '\n'.join([self._info.username, domain, self._info.hostname])

    def configure(self, info: typing.Dict[str, typing.Any]) -> None:
        self._info.use_ntlm_v2 = info.get('use_ntlm_v2', False)
        sign_options = info.get('sign_options', 'when_required')
        self._info.sign_options = _SignOptions[sign_options]
        self._info.is_direct_tcp = info.get('is_direct_tcp', True)

        self._info.username = info['username']
        self._info.domain = info.get('domain', 'HSR')

        self._info.share = info.get('share', 'skripte')
        self._info.hostname = info.get('hostname', 'svm-c213.hsr.ch')

        prompt = f'{self._info.username}@{self._info.hostname}'
        self._info.password = utils.get_password('smb', self._password_identifier(), prompt)

        default_port = 445 if self._info.is_direct_tcp else 139
        self._info.port = info.get('port', default_port)

        if not info.get('debug', False):
            # PySMB has too verbose logging, we don't want to see that.
            logging.getLogger('SMB.SMBConnection').propagate = False

        logger.debug(f'Configured: {self._info}')

    def connect(self) -> None:
        self._connection = SMBConnection(username=self._info.username,
                                         password=self._info.password,
                                         domain=self._info.domain,
                                         my_name=socket.gethostname(),
                                         remote_name=self._info.hostname,
                                         use_ntlm_v2=self._info.use_ntlm_v2,
                                         sign_options=self._info.sign_options,
                                         is_direct_tcp=self._info.is_direct_tcp)

        try:
            server_ip: str = socket.gethostbyname(self._info.hostname)
        except socket.gaierror:
            raise utils.PluginOperationError(
                f'Could not find server {self._info.hostname}. '
                'Maybe you need to open a VPN connection or the server is not available.')

        logger.debug(f'Connecting to {server_ip} ({self._info.hostname}) port {self._info.port}')

        try:
            success = self._connection.connect(server_ip, self._info.port)
        except (ConnectionRefusedError, socket.timeout):
            raise utils.PluginOperationError(f'Could not connect to {server_ip}:{self._info.port}')
        # FIXME Can be removed once https://github.com/miketeo/pysmb/issues/108 is fixed
        except ProtocolError:
            success = False

        if not success:
            raise utils.AuthenticationError(
                f'Authentication failed for {server_ip}:{self._info.port}')

    def disconnect(self) -> None:
        self._connection.close()

    def _create_digest(self, size: int, mtime: float) -> str:
        """Create a digest from a size and mtime.

        We can't get a hash from the server, so we use the last modified time
        (mtime) and file size as a substitute. Also see:
        https://en.wikipedia.org/wiki/St_mtime

        The mtime resolution can differ between client/server or on different
        file systems, so we truncate it to full seconds.
        """
        mtime = int(mtime)
        return f'{size}-{mtime}'

    def create_local_digest(self, path: pathlib.Path) -> str:
        info = path.lstat()
        return self._create_digest(size=info.st_size, mtime=info.st_mtime)

    def create_remote_digest(self, path: pathlib.PurePath) -> str:
        try:
            attributes = self._connection.getAttributes(self._info.share, str(path))
        except OperationFailure:
            raise utils.PluginOperationError(
                f'Could not find remote file {path} in share "{self._info.share}"')

        self._attributes[path] = attributes
        return self._create_digest(size=attributes.file_size,
                                   mtime=attributes.last_write_time)

    def list_path(self, path: pathlib.PurePath) -> typing.Iterable[pathlib.PurePath]:
        try:
            entries = self._connection.listPath(self._info.share, str(path))
        except OperationFailure:
            raise utils.PluginOperationError(f'Folder "{path}" not found')

        for entry in entries:
            if entry.isDirectory:
                if entry.filename not in [".", ".."]:
                    yield from self.list_path(pathlib.PurePath(path / entry.filename))
            else:
                yield pathlib.PurePath(path / entry.filename)

    def retrieve_file(self,
                      path: pathlib.PurePath,
                      fileobj: typing.IO[bytes]) -> typing.Optional[int]:
        logger.debug(f'Retrieving file {path}')
        try:
            self._connection.retrieveFile(self._info.share, str(path), fileobj)
        except OperationFailure:
            raise utils.PluginOperationError(
                f'Could not download {path} from share "{self._info.share}"')

        mtime: int = self._attributes[path].last_write_time
        return mtime

    def connection_schema(self) -> utils.JsonType:
        return {
            'type': 'object',
            'properties': {
                'hostname': {'type': 'string'},
                'port': {'type': 'number'},
                'share': {'type': 'string'},
                'domain': {'type': 'string'},
                'username': {'type': 'string'},
                'sign_options': {
                    'type': 'string',
                    'enum': ['never', 'when_supported', 'when_required'],
                },
                'use_ntlm_v2': {'type': 'boolean'},
                'is_direct_tcp': {'type': 'boolean'},
                'debug': {'type': 'boolean'},
            },
            'required': [
                'username',
            ],
            'additionalProperties': False,
        }
