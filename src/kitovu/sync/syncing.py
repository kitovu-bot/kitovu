"""Logic related to actually syncing files."""

import pathlib

from kitovu.sync import syncplugin, smb


def start(url: str):
    """Sync files from the given URL."""
    syncplugin.init()
    smb.init()

    hooks = syncplugin.manager.hook
    hooks.connect(url=url, options={})

    path = pathlib.PurePath('/Informatik/Fachbereich/Engineering-Projekt/EPJ/FS2018/')
    # FIXME how to handle pluggy's multicall with various plugins?
    files = list(hooks.list_path(path=path)[0])
    print(f'Remote files: {files}')

    example_file = files[0]
    print(f'Downloading: {example_file}')
    digest = hooks.create_remote_digest(path=example_file)[0]
    print(f'Remote digest: {digest}')

    output = pathlib.Path(example_file.name)

    with output.open('wb') as fileobj:
        hooks.retrieve_file(path=example_file, fileobj=fileobj)

    digest = hooks.create_local_digest(path=output)[0]
    print(f'Local digest: {digest}')
