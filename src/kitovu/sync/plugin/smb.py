"""Plugin to synchronize SMB Windows fileshares."""

import enum
import socket
import typing
import pathlib

import attr
from smb.SMBConnection import SMBConnection

from kitovu import utils
from kitovu.sync import syncplugin


class _SignOptions(enum.IntEnum):

    """Enum for possible signing options from PySMB."""

    never = SMBConnection.SIGN_NEVER
    when_supported = SMBConnection.SIGN_WHEN_SUPPORTED
    when_required = SMBConnection.SIGN_WHEN_REQUIRED


@attr.s
class _ConnectionInfo:

    """Connection information we got from the config."""

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

    """A plugin to sync data via SMB/CIFS (Windows fileshares)."""

    def __init__(self) -> None:
        self._connection: SMBConnection = None
        self._info = _ConnectionInfo()

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

        self._info.password = utils.get_password('smb', self._password_identifier())

        default_port = 445 if self._info.is_direct_tcp else 139
        self._info.port = info.get('port', default_port)

    def connect(self) -> None:
        self._connection = SMBConnection(username=self._info.username,
                                         password=self._info.password,
                                         domain=self._info.domain,
                                         my_name=socket.gethostname(),
                                         remote_name=self._info.hostname,
                                         use_ntlm_v2=self._info.use_ntlm_v2,
                                         sign_options=self._info.sign_options,
                                         is_direct_tcp=self._info.is_direct_tcp)

        # FIXME: Handle OSError (not in HSR net)
        server_ip: str = socket.gethostbyname(self._info.hostname)
        # FIXME: Handle smb.smb_structs.ProtocolError (wrong password)
        success = self._connection.connect(server_ip, self._info.port)
        if not success:
            raise OSError(f'Connection failed to {server_ip}:{self._info.port}')

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
        attributes = self._connection.getAttributes(self._info.share, str(path))
        return self._create_digest(size=attributes.file_size,
                                   mtime=attributes.last_write_time)

    def list_path(self, path: pathlib.PurePath) -> typing.Iterable[pathlib.PurePath]:
        for entry in self._connection.listPath(self._info.share, str(path)):
            if not entry.isDirectory:
                yield pathlib.PurePath(path / entry.filename)

    def retrieve_file(self, path: pathlib.PurePath, fileobj: typing.IO[bytes]) -> None:
        self._connection.retrieveFile(self._info.share, str(path), fileobj)
