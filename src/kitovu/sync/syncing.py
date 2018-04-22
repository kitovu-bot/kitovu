"""Logic related to actually syncing files."""

import pathlib
import typing

import stevedore
import stevedore.driver

from kitovu import utils
from kitovu.sync import syncplugin
from kitovu.sync.settings import Settings, ConnectionSettings
from kitovu.sync.plugin import smb
from kitovu.sync import kitovu_filecache


def _find_plugin(pluginname: str) -> syncplugin.AbstractSyncPlugin:
    """Find an appropriate sync plugin with the given settings."""
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

def start_all(config_file: typing.Optional[pathlib.Path]) -> None:
    """Sync all files with the given configuration file."""
    settings = Settings.from_yaml_file(config_file)
    for _plugin_key, connection_settings in sorted(settings.connections.items()):
        start(connection_settings)

# synchronisation process: define here filename of FileCache / write with appdirs to disk


def start(connection_settings: ConnectionSettings) -> None:
    """Sync files with the given plugin and username."""
    plugin = _find_plugin(connection_settings.plugin_name)
    plugin.configure(connection_settings.connection)
    plugin.connect()
    filecache: kitovu_filecache.FileCache = kitovu_filecache.FileCache(pathlib.PurePath("filecache.json"))
    # FIXME add path from settings instead of filecache.json
    filecache.load()

    # special filecache cases which FIXME here
    # 1. remote deleted (triggers exception), local exists => REMOTE*
    # 2. remote deleted (triggers exception), local exists AND changed (local_digest and cached_digest differ) => BOTH*

    for subject in connection_settings.subjects:
        remote_path = subject['remote-dir']
        local_path = subject['local-dir']

        for item in plugin.list_path(remote_path):
            # each plugin should now yield all files recursively with list_path
            print(f'Downloading: {item}')

            remote_digest = plugin.create_remote_digest(item)
            print(f'Remote digest: {remote_digest}')

            # test if file remotely: case 1 and 2 are special
                # 1. remote deleted (triggers exception), local exists => REMOTE*
                # 2. remote deleted (triggers exception), local exists AND changed (local_digest and cached_digest differ) => BOTH*


            # if file doesn't exist: case 3 (normal case)
            if not pathlib.Path(local_path / item.relative_to(remote_path)).exists():
                output = pathlib.Path(local_path / item.relative_to(remote_path))
                pathlib.Path(output.parent).mkdir(parents=True, exist_ok=True)

                with output.open('wb') as fileobj:
                    plugin.retrieve_file(item, fileobj)

                local_digest = plugin.create_local_digest(output)
                print(f'Local digest: {local_digest}')
                filecache.update(local_digest, output, plugin)
                # Fixme case 4. remote B, local A => remote_digest and local digest differ, but local digest and cached digest same => REMOTE, download
            else: # file exists already
                state_of_file: int = filecache.discover_changes(output, plugin)
                if state_of_file == kitovu_filecache.Filestate.NONE:
                    pass
                elif state_of_file == kitovu_filecache.Filestate.REMOTE:

                elif state_of_file == kitovu_filecache.Filestate.LOCAL:
                    filecache.update(local_digest, output, plugin)
                elif state_of_file == kitovu_filecache.Filestate.BOTH: # override



    plugin.disconnect()
