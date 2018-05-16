import pytest
import pathlib
import json

from kitovu.sync import filecache
from kitovu.sync.plugin.smb import SmbPlugin


@pytest.fixture
def cache(temppath) -> filecache.FileCache:
    return filecache.FileCache(temppath / "test_filecache.json")


class TestFile:

    def test_to_dict(self, temppath):
        file = filecache.File("this_is_a_digest", "dummyplugin")
        assert file.to_dict() == {"plugin": "dummyplugin", "digest": "this_is_a_digest"}


class TestLoadWrite:

    def test_write(self, temppath, cache, plugin):
        cache.modify(temppath / "testfile1.txt", plugin, "digest1")
        cache.modify(temppath / "testfile2.pdf", plugin, "digest2")
        cache.modify(temppath / "testfile3.png", plugin, "digest3")
        cache.write()
        with cache._filename.open("r") as f:
            json_data = json.load(f)
        assert json_data == {str(temppath / "testfile1.txt"): {"digest": "digest1", "plugin": "dummyplugin"},
                             str(temppath / "testfile2.pdf"): {"digest": "digest2", "plugin": "dummyplugin"},
                             str(temppath / "testfile3.png"): {"digest": "digest3", "plugin": "dummyplugin"}}

    def test_load(self, temppath, cache, plugin):
        cache.modify(temppath / "testfile4.txt", plugin, "digest4")
        cache.modify(temppath / "testfile5.pdf", plugin, "digest5")
        cache.modify(temppath / "testfile6.png", plugin, "digest6")
        cache.write()
        cache.load()
        assert cache._data == {temppath / "testfile4.txt": filecache.File(cached_digest="digest4",
                                                                          plugin_name="dummyplugin"),
                               temppath / "testfile5.pdf": filecache.File(cached_digest="digest5",
                                                                          plugin_name="dummyplugin"),
                               temppath / "testfile6.png": filecache.File(cached_digest="digest6",
                                                                          plugin_name="dummyplugin")}

    def test_filecache_not_found(self, temppath, cache, plugin):
        cache.load()
        assert not cache._data


class TestChange:

    def test_modify(self, temppath, plugin, cache):
        cache.modify(temppath / "testfile1.txt", plugin, "digest1")
        testfile = filecache.File(cached_digest="digest1", plugin_name="dummyplugin")
        assert cache._data[temppath / "testfile1.txt"] == testfile

    def test_not_matching_pluginname(self, temppath, plugin, cache):
        local = temppath / "local_dir/test/example1.txt"
        local.parent.mkdir(parents=True)
        local.touch()
        remote = pathlib.PurePath("remote_dir/test/example1.txt")

        cache.modify(local, plugin, plugin.remote_digests[remote])

        wrongplugin = SmbPlugin()
        with pytest.raises(AssertionError):
            cache.discover_changes(local, remote, wrongplugin)


class TestFileState:

    def test_file_is_new(self, temppath, plugin, cache):
        local = temppath / "testfile1.txt"
        remote = pathlib.PurePath(temppath) / "testfile1.txt"
        assert cache.discover_changes(local, remote, plugin) == filecache.FileState.NEW

    @pytest.mark.parametrize('local_changed, remote_changed, expected', [
        (True, True, filecache.FileState.BOTH_CHANGED),
        (True, False, filecache.FileState.LOCAL_CHANGED),
        (False, True, filecache.FileState.REMOTE_CHANGED),
        (False, False, filecache.FileState.NO_CHANGES),
    ])
    def test_files_changed(self, temppath, plugin, cache, local_changed, remote_changed, expected):
        plugin.connect()
        local = temppath / "local_dir/test/example4.txt"
        local.parent.mkdir(parents=True)
        local.touch()
        remote = pathlib.PurePath("remote_dir/test/example4.txt")

        cache.modify(local, plugin, plugin.remote_digests[remote])

        if local_changed:
            plugin.local_digests[local] = "abc"
        if remote_changed:
            plugin.remote_digests[remote] = "def"

        assert cache.discover_changes(local, remote, plugin) == expected

    def test_outdated_cache_and_same_digest(self, temppath, plugin, cache):
        plugin.connect()
        local = temppath / "local_dir/test/example4.txt"
        local.parent.mkdir(parents=True)
        local.touch()
        remote = pathlib.PurePath("remote_dir/test/example4.txt")

        cache.modify(local, plugin, plugin.remote_digests[remote])

        plugin.local_digests[local] = "new-digest"
        plugin.remote_digests[remote] = "new-digest"

        assert cache._data[local].cached_digest != "new-digest"
        assert cache.discover_changes(local, remote, plugin) == filecache.FileState.NO_CHANGES
        assert cache._data[local].cached_digest == "new-digest"

    def test_outdated_cache_and_different_digest(self, temppath, plugin, cache):
        plugin.connect()
        local = temppath / "local_dir/test/example4.txt"
        local.parent.mkdir(parents=True)
        local.touch()
        remote = pathlib.PurePath("remote_dir/test/example4.txt")

        cache.modify(local, plugin, plugin.remote_digests[remote])

        plugin.local_digests[local] = "other-digest"
        plugin.remote_digests[remote] = "new-digest"

        assert cache._data[local].cached_digest != "new-digest"
        assert cache.discover_changes(local, remote, plugin) == filecache.FileState.BOTH_CHANGED
        assert cache._data[local].cached_digest != "new-digest"

    def test_outdated_cache_new_file(self, temppath, plugin, cache):
        plugin.connect()
        local = temppath / "local_dir/test/example4.txt"
        local.parent.mkdir(parents=True)
        local.touch()

        remote = pathlib.PurePath("remote_dir/test/example4.txt")
        plugin.remote_digests[remote] = "new-digest"

        assert local not in cache._data
        assert cache.discover_changes(local, remote, plugin) == filecache.FileState.BOTH_CHANGED
        assert cache._data[local].cached_digest is None
