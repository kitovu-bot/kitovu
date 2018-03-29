"""Logic related to actually syncing files."""

import pathlib

import stevedore
import stevedore.driver

from kitovu import utils
from kitovu.sync import syncplugin
from kitovu.sync.plugin import smb, moodle


def _find_plugin(pluginname: str) -> syncplugin.AbstractSyncPlugin:
    """Find an appropriate sync plugin with the given name."""
    builtin_plugins = {
        'smb': smb.SmbPlugin(),
        'moodle': moodle.MoodlePlugin(),
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


def start(pluginname: str, username: str, path: str) -> None:
    """Sync files with the given plugin, username and path."""
    plugin = _find_plugin(pluginname)
    plugin.configure({'username': username})
    plugin.connect()

    pure_path = pathlib.PurePath(path)

    files = list(plugin.list_path(pure_path))
    print('Remote files:')
    for filename in files:
        print(f'  {filename}')

    example_file = files[0]
    print(f'Downloading: {example_file}')
    digest = plugin.create_remote_digest(example_file)
    print(f'Remote digest: {digest}')

    output = pathlib.Path(example_file.name)

    with output.open('wb') as fileobj:
        plugin.retrieve_file(example_file, fileobj)

    digest = plugin.create_local_digest(output)
    print(f'Local digest: {digest}')
