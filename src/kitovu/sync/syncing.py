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
        manager = stevedore.driver.DriverManager(namespace='kitovu.sync.plugin',
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

    path = pathlib.PurePath('/Informatik/Fachbereich/Engineering-Projekt/EPJ/FS2018/')

    files = list(plugin.list_path(path))
    print(f'Remote files: {files}')

    for x in files:
        file = files[x]
        print(f'Downloading: {file}')

        # FIXME: insert our nice Progress bar

        digest = plugin.create_remote_digest(file)
        print(f'Remote digest: {digest}')

        output = pathlib.Path(file.name)

        with output.open('wb') as fileobj:
            plugin.retrieve_file(file, fileobj)

        digest = plugin.create_local_digest(output)
        print(f'Local digest: {digest}')
