"""Logic related to actually syncing files."""

import pathlib

import stevedore
import stevedore.driver

from kitovu import utils
from kitovu.sync import syncplugin
from kitovu.sync.plugin import smb


def _find_plugin(pluginname: str) -> syncplugin.AbstractSyncPlugin:
    """Find an appropriate sync plugin with the given name."""
    builtin_plugins = {
        'smb': smb.SmbPlugin(),
    }
    if pluginname in builtin_plugins:
        return builtin_plugins[pluginname]

    try:
        manager = stevedore.driver.DriverManager(namespace='kitovu.sync.plug§in',
                                                 name=pluginname, invoke_on_load=True)
    except stevedore.exception.NoMatches:
        raise utils.NoPluginError(f"The plugin {pluginname} was not found")

    plugin: syncplugin.AbstractSyncPlugin = manager.driver
    return plugin


def start(pluginname: str, username: str) -> None:
    """Sync files with the given plugin and username."""
    plugin = _find_plugin(pluginname)
    plugin.configure({'username': username})
    plugin.connect()

    path = pathlib.Path('/Informatik/Fachbereich/Engineering-Projekt/EPJ/FS2018/')
    # in order to traverse the file system, Path class is needed instead of PurePath
    # where do I actually get the path names? how do I access the paths from the config file?

    files = plugin.list_path(path)
    print(f'Remote files: {files}')
    for item in plugin.list_path.rglob("*.*"):
        print(f'Downloading: {item}')

        digest = plugin.create_remote_digest(item)
        print(f'Remote digest: {digest}')

        output = pathlib.Path(item.name)

        with output.open('wb') as fileobj:
            plugin.retrieve_file(item, fileobj)

        digest = plugin.create_local_digest(output)
        print(f'Local digest: {digest}')

