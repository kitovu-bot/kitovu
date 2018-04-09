import os
import pathlib
import typing

import pytest

from helpers import dummyplugin


@pytest.fixture(autouse=True)
def plugin() -> dummyplugin.DummyPlugin:
    return dummyplugin.DummyPlugin()


def test_connection_active(plugin) -> None:
    plugin.connect()
    assert plugin.connection_state


def test_connection_inactive(plugin) -> None:
    plugin.connect()
    plugin.disconnect()
    assert not plugin.connection_state


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


def test_remote_digest_changed(plugin):
    plugin.connect()
    plugin.paths[pathlib.PurePath("example1.txt")].remote_digest = "42"
    remote_digest = plugin.create_remote_digest(pathlib.PurePath("example1.txt"))
    assert remote_digest == "42"


def test_if_list_path_lists_correct_pathnames(plugin):
    pathnames: typing.Iterable[pathlib.PurePath] = [pathlib.PurePath("example1.txt"),
                                                    pathlib.PurePath("example2.txt"),
                                                    pathlib.PurePath("example3.txt"),
                                                    pathlib.PurePath("example4.txt")]
    plugin.connect()
    all_paths = list(plugin.list_path(plugin.paths))
    assert all_paths == pathnames


def test_if_correct_file_retrieved(plugin):
    filename = "testsample.txt"
    if os.path.exists(filename):
        os.remove(filename)
    plugin.connect()
    f = open(filename, "w")
    with f:
        plugin.retrieve_file(pathlib.PurePath("example1.txt"), f)
    f = open(filename, "r")
    with f:
        assert f.read() == "example1.txt\n1"


def test_if_changed_digest_still_retrieves_correct_file(plugin):
    filename = "testsample.txt"
    if os.path.exists(filename):
        os.remove(filename)
    plugin.connect()
    plugin.paths[pathlib.PurePath("example1.txt")].remote_digest = "42"  # change remote digest
    f = open(filename, "w")
    with f:
        plugin.retrieve_file(pathlib.PurePath("example1.txt"), f)
    f = open(filename, "r")
    with f:
        assert f.read() == "example1.txt\n42"