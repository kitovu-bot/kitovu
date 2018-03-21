"""Plugin to synchronize SMB Windows fileshares."""

import enum
import urllib.parse
import socket
import typing
import pathlib

import attr
from smb.SMBConnection import SMBConnection

from kitovu import config, utils
from kitovu.sync import syncplugin


@attr.s
class _LoginInfo:

    """SMB login info we can extract from an URL."""

    username: str = attr.ib(None)
    hostname: str = attr.ib(None)
    share: str = attr.ib(None)
    domain: typing.Optional[str] = attr.ib(None)
    port: typing.Optional[int] = attr.ib(None)


class _SignOptions(enum.IntEnum):

    """Enum for possible signing options from PySMB."""

    never = SMBConnection.SIGN_NEVER
    when_supported = SMBConnection.SIGN_WHEN_SUPPORTED
    when_required = SMBConnection.SIGN_WHEN_REQUIRED


def _parse_url(url: str) -> _LoginInfo:
    """Get a _LoginInfo class for the given URL.

    For the exact syntax of such an URL, see:
    http://ubiqx.org/cifs/Appendix-D.html
    https://www.iana.org/assignments/uri-schemes/prov/smb

    With an invalid URL, this will raise ValueError.
    """
    parsed: urllib.parse.ParseResult = urllib.parse.urlparse(url)
    username: str = parsed.username
    hostname: str
    share: str
    domain: typing.Optional[str]
    port: int

    if parsed.scheme == 'smb' and parsed.hostname == 'hsr.ch':
        # smb://user@hsr.ch shorthand URL
        # FIXME Make sure no share/domain/... is in the URL
        hostname = 'svm-c213.hsr.ch'
        share = 'skripte'
        domain = 'HSR'
        port = 445
    else:
        if ';' in username:
            username, domain = username.split(';')
        else:
            domain = None
        hostname = parsed.hostname
        share = parsed.path.lstrip('/')
        port = parsed.port

    return _LoginInfo(username=username, hostname=hostname, share=share,
                      domain=domain, port=port)


class SmbPlugin(syncplugin.AbstractSyncPlugin):

    """A plugin to sync data via SMB/CIFS (Windows fileshares)."""

    def __init__(self) -> None:
        self._connection: SMBConnection = None
        self._login_info = _LoginInfo()

    def connect(self, url: str, options: typing.Dict[str, typing.Any]) -> None:
        # FIXME custom exception for errors
        info: _LoginInfo = _parse_url(url)
        self._login_info = info
        password = config.get_password(url)

        use_ntlm_v2: bool = options.get('use_ntlm_v2', False)
        sign_options: str = options.get('sign_options', 'when_required')
        is_direct_tcp: bool = options.get('is_direct_tcp', True)

        self._connection = SMBConnection(
            username=info.username, password=password, domain=info.domain,
            my_name=socket.gethostname(), remote_name=info.hostname,
            use_ntlm_v2=use_ntlm_v2, sign_options=_SignOptions[sign_options],
            is_direct_tcp=is_direct_tcp)

        # FIXME: Handle OSError (not in HSR net)
        server_ip: str = socket.gethostbyname(info.hostname)
        port: typing.Optional[int] = info.port

        if port is None:
            # Default SMB/CIFS ports
            port = 445 if is_direct_tcp else 139

        # FIXME: Handle smb.smb_structs.ProtocolError (wrong password)
        success = self._connection.connect(server_ip, port)
        if not success:
            raise OSError("Connection failed")

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
        attributes = self._connection.getAttributes(self._login_info.share,
                                                    str(path))
        return self._create_digest(size=attributes.file_size,
                                   mtime=attributes.last_write_time)

    def list_path(self, path: pathlib.PurePath) -> typing.Iterable[pathlib.PurePath]:
        for entry in self._connection.listPath(self._login_info.share,
                                               str(path)):
            if not entry.isDirectory:
                yield pathlib.PurePath(path / entry.filename)

    def retrieve_file(self, path: pathlib.PurePath, fileobj: typing.IO[str]) -> None:
        self._connection.retrieveFile(self._login_info.share, str(path), fileobj)
