"""Logic related to actually syncing files."""

import pathlib

from kitovu.sync import syncplugin, smb


def start(url: str) -> None:
    """Sync files from the given URL."""
    # FIXME actually dispatch to the right plugin
    plugin = smb.SmbPlugin()
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
