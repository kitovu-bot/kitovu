import pathlib
import typing


def test_connection_active(plugin) -> None:
    plugin.connect()
    assert plugin.is_connected


def test_connection_inactive(plugin) -> None:
    plugin.connect()
    plugin.disconnect()
    assert not plugin.is_connected


def test_local_digest(plugin, temppath):
    plugin.connect()
    local_digest = plugin.create_local_digest(temppath / "local_dir/test/example1.txt")
    assert local_digest == "1"


def test_local_digest_changed(plugin, temppath):
    plugin.connect()
    plugin.local_digests[temppath / "local_dir/test/example1.txt"] = "42"
    local_digest = plugin.create_local_digest(temppath / "local_dir/test/example1.txt")
    assert local_digest == "42"


def test_remote_digest(plugin):
    plugin.connect()
    remote_digest = plugin.create_remote_digest(pathlib.PurePath("remote_dir/test/example1.txt"))
    assert remote_digest == "1"


def test_remote_digest_changed(plugin):
    plugin.connect()
    plugin.remote_digests[pathlib.PurePath("remote_dir/test/example1.txt")] = "42"
    remote_digest = plugin.create_remote_digest(pathlib.PurePath("remote_dir/test/example1.txt"))
    assert remote_digest == "42"


def test_if_list_path_lists_correct_pathnames(plugin):
    pathnames: typing.Iterable[pathlib.PurePath] = [
        pathlib.PurePath("remote_dir/test/example1.txt"),
        pathlib.PurePath("remote_dir/test/example2.txt"),
        pathlib.PurePath("remote_dir/test/example3.txt"),
        pathlib.PurePath("remote_dir/test/example4.txt"),
    ]
    plugin.connect()
    all_paths = list(plugin.list_path(pathlib.PurePath('remote_dir/test')))
    assert all_paths == pathnames


def test_if_correct_file_retrieved(plugin, temppath: pathlib.Path):
    sample = temppath / 'testsample.txt'

    plugin.connect()
    with sample.open("wb") as f:
        plugin.retrieve_file(pathlib.PurePath("remote_dir/test/example1.txt"), f)

    text = sample.read_text('utf-8')
    assert text == str(pathlib.PurePath("remote_dir/test/example1.txt")) + "\n1"


def test_if_changed_digest_still_retrieves_correct_file(plugin, temppath: pathlib.Path):
    sample = temppath / 'testsample.txt'

    plugin.connect()
    plugin.remote_digests[pathlib.PurePath("remote_dir/test/example1.txt")] = "42"  # change remote digest

    with sample.open("wb") as f:
        plugin.retrieve_file(pathlib.PurePath("remote_dir/test/example1.txt"), f)

    text = sample.read_text('utf-8')
    assert text == str(pathlib.PurePath("remote_dir/test/example1.txt")) + "\n42"
