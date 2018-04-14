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

    # FIXME hardcoded paths that will be replaced from entries in the config-file
    path = pathlib.PurePath('/Informatik/Fachbereich/Engineering-Projekt/EPJ/FS2018/')
    outputpath = pathlib.Path(".") / "kitovu-output-files"

    for item in plugin.list_path(path):

        # each plugin should now yield all files recursively with list_path
        print(f'Downloading: {item}')

        remote_digest = plugin.create_remote_digest(item)
        print(f'Remote digest: {remote_digest}')

        output = pathlib.Path(outputpath / item.relative_to(path))

        pathlib.Path(output.parent).mkdir(parents=True, exist_ok=True)

        with output.open('wb') as fileobj:
            plugin.retrieve_file(item, fileobj)

        local_digest = plugin.create_local_digest(output)
        print(f'Local digest: {local_digest}')
        # create File object, that writes output, remote_digest, local_digest to file
