import pathlib

from kitovu.sync.settings import Settings, ConnectionSettings


def test_load_a_sample_yaml_file():
    settings = Settings.from_yaml_file(pathlib.Path('./tests/assets/smb_example_config.yml'))

    expected_root_dir = pathlib.Path(f'{pathlib.Path.home()}/Documents/HSR/semester_06')
    expected_global_ignore = ['Thumbs.db', '.DS_Store']
    expected_connections = {
        'skripte-server': ConnectionSettings(
            plugin_name='smb',
            connection={
                'username': 'example_user',
            },
            subjects=[
                {
                    'name': 'Engineering-Projekt',
                    'ignore': ['SubDir', 'example.txt'],
                    'remote-dir': pathlib.PurePath('Informatik/Fachbereich/Engineering-Projekt/EPJ'),
                    'local-dir': pathlib.Path(f'{expected_root_dir}/Engineering-Projekt'),
                }
            ],
        ),
    }

    assert settings.root_dir == expected_root_dir
    assert settings.global_ignore == expected_global_ignore
    assert settings.connections == expected_connections

    assert settings == Settings(
        root_dir=expected_root_dir,
        global_ignore=expected_global_ignore,
        connections=expected_connections,
    )
