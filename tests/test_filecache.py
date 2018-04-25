import pytest
import pathlib
import json

from tests.helpers import dummyplugin
from kitovu.sync import filecache


@pytest.fixture
def plugin() -> dummyplugin.DummyPlugin:
    return dummyplugin.DummyPlugin()


@pytest.fixture
def cache(temppath) -> filecache.FileCache:
    return filecache.FileCache(temppath / "test_filecache.json")


class TestFile:

    def test_to_dict(self, temppath):
        file = filecache.File("this_is_a_digest", "dummyplugin")
        assert file.to_dict() == {"plugin": "dummyplugin", "digest": "this_is_a_digest"}


class TestLoadWrite:

    def test_write(self, temppath, cache, plugin):
        cache.modify(pathlib.Path(temppath) / "testfile1.txt", plugin, "digest1")
        cache.modify(pathlib.Path(temppath) / "testfile2.pdf", plugin, "digest2")
        cache.modify(pathlib.Path(temppath) / "testfile3.png", plugin, "digest3")
        cache.write()
        with cache._filename.open("r") as f:
            json_data = json.load(f)
        assert json_data == {str(temppath / "testfile1.txt"): {"digest": "digest1", "plugin": "dummyplugin"},
                             str(temppath / "testfile2.pdf"): {"digest": "digest2", "plugin": "dummyplugin"},
                             str(temppath / "testfile3.png"): {"digest": "digest3", "plugin": "dummyplugin"}}

    def test_load(self, temppath, cache, plugin):
        cache.modify(pathlib.Path(temppath) / "testfile1.txt", plugin, "digest1")
        cache.modify(pathlib.Path(temppath) / "testfile2.pdf", plugin, "digest2")
        cache.modify(pathlib.Path(temppath) / "testfile3.png", plugin, "digest3")
        cache.write()
        cache.load()
        assert cache._data == {pathlib.Path(temppath) / "testfile1.txt": filecache.File(cached_digest="digest1",
                                                                                        plugin_name="dummyplugin"),
                               pathlib.Path(temppath) / "testfile2.pdf": filecache.File(cached_digest="digest2",
                                                                                        plugin_name="dummyplugin"),
                               pathlib.Path(temppath) / "testfile3.png": filecache.File(cached_digest="digest3",
                                                                                        plugin_name="dummyplugin")}


class TestChange:

    def test_modify(self):
        pass

    def test_discover_changes(self):
        pass


class TestFileState:

    def test_file_is_new(self):
        pass

    def test_remote_file_changed(self):
        pass

    def test_file_not_changed(self):
        pass

    def test_local_file_changed(self):
        pass

    def test_remote_and_local_file_changed(self):
        pass
