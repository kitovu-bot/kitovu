"""Storage and parsing of kitovu's configuration."""

import typing
import urllib.parse

import keyring


def get_password(url: str) -> str:
    """Get the password for the given URL via keyring."""
    # FIXME Handle password being None
    # FIXME Make sure there's an username
    assert urllib.parse.urlparse(url).username is not None
    password: typing.Optional[str] = keyring.get_password('kitovu', url)
    assert password is not None
    return password
