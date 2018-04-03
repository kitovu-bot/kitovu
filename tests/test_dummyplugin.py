import kitovu.utils
import pathlib
import pytest

from tests.helpers import dummyplugin


@pytest.fixture(autouse=True)
def plugin() -> dummyplugin.DummyPlugin:
    return dummyplugin.DummyPlugin()


def test_connection_active(plugin) -> None:
    plugin.connect()
    assert plugin.connection_state == True


def test_connection_inactive(plugin) -> None:
    plugin.connect()
    plugin.disconnect()
    assert plugin.connection_state == False


def test_local_digest(plugin):
    plugin.connect()
    local_digest = plugin.create_local_digest(pathlib.PurePath("example1.txt"))
    assert local_digest == "1"


def test_local_digest_changed(plugin):
    plugin.connect()
    plugin.paths[pathlib.PurePath("example1.txt")].local_digest = "42"
    local_digest = plugin.create_local_digest(pathlib.PurePath("example1.txt"))
    assert local_digest == "42"


def test_remote_digest(plugin):
    plugin.connect()
    remote_digest = plugin.create_remote_digest(pathlib.PurePath("example1.txt"))
    assert remote_digest == "1"


def test_local_digest_changed(plugin):
    plugin.connect()
    plugin.paths[pathlib.PurePath("example1.txt")].remote_digest = "42"
    remote_digest= plugin.create_remote_digest(pathlib.PurePath("example1.txt"))
    assert remote_digest == "42"



