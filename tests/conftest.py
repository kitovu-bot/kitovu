import keyring
import pathlib
import pytest

from helpers.in_memory_keyring import InMemoryKeyring
from tests.helpers import dummyplugin


@pytest.fixture(autouse=True)
def init_keyring():
    ring = InMemoryKeyring()
    keyring.set_keyring(ring)
    yield
    ring.clear()


@pytest.fixture
def temppath(tmpdir):
    return pathlib.Path(tmpdir)


@pytest.fixture
def plugin(temppath) -> dummyplugin.DummyPlugin:
    return dummyplugin.DummyPlugin(temppath)
