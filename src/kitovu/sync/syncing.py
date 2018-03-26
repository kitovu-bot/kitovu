"""Logic related to actually syncing files."""

import pathlib
import urllib.parse

import stevedore
import stevedore.driver

from kitovu import utils
from kitovu.sync import syncplugin
from kitovu.sync.plugin import smb


def _find_plugin(url: str) -> syncplugin.AbstractSyncPlugin:
    """Find an appropriate sync plugin for the given URL.

    The URL's scheme (e.g. smb://) is equal to the plugin name.
    """
    builtin_plugins = {
        'smb': smb.SmbPlugin(),
    }
    scheme: str = urllib.parse.urlparse(url).scheme
    if scheme in builtin_plugins:
        return builtin_plugins[scheme]

    try:
        manager = stevedore.driver.DriverManager(namespace='kitovu.sync.plugin',
                                                 name=scheme, invoke_on_load=True)
    except stevedore.exception.NoMatches:
        raise utils.NoPluginError(f"No plugin found for {scheme}:// URL.")

    plugin: syncplugin.AbstractSyncPlugin = manager.driver
    return plugin


def start(url: str) -> None:
    """Sync files from the given URL."""
    plugin = _find_plugin(url)
    plugin.connect(url, options={})

    path = pathlib.PurePath('/Informatik/Fachbereich/Engineering-Projekt/EPJ/FS2018/')

    files = list(plugin.list_path(path))
    print(f'Remote files: {files}')

    example_file = files[0]
    print(f'Downloading: {example_file}')
    digest = plugin.create_remote_digest(example_file)
    print(f'Remote digest: {digest}')

    output = pathlib.Path(example_file.name)

    with output.open('wb') as fileobj:
        plugin.retrieve_file(example_file, fileobj)

    digest = plugin.create_local_digest(output)
    print(f'Local digest: {digest}')
