import pathlib

import pytest

from kitovu import utils
from kitovu.sync.settings import Settings, ConnectionSettings


def test_load_a_sample_yaml_file():
    settings = Settings.from_yaml_file(pathlib.Path('./tests/assets/smb_example_config.yml'))

    expected_root_dir = pathlib.Path.home() / 'Documents/HSR/semester_06'
    expected_connections = {
        'skripte-server': ConnectionSettings(
            plugin_name='smb',
            connection={
                'username': 'example_user',
            },
            subjects=[
                {
                    'name': 'Engineering-Projekt',
                    'ignore': ['Thumbs.db', '.DS_Store', 'SubDir', 'example.txt'],
                    'remote-dir': pathlib.PurePath('Informatik/Fachbereich/Engineering-Projekt/EPJ'),
                    'local-dir': pathlib.Path(f'{expected_root_dir}/Engineering-Projekt'),
                }
            ],
        ),
    }

    assert settings.root_dir == expected_root_dir
    assert settings.connections == expected_connections

    assert settings == Settings(
        root_dir=expected_root_dir,
        connections=expected_connections,
    )


def test_invalid_yaml_files(temppath: pathlib.Path):
    config_yml = temppath / 'config.yml'
    config_yml.write_text(f"""
    root-dir: ./asdf
    connections:
      - name: mytest-plugin
         plugin: smb
       username: myuser
    subjects:
      - name: sync-1
        sources:
          - connection: mytest-plugin
            remote-dir: Some/Test/Dir1
          - connection: another-plugin
            remote-dir: Another/Test/Dir1
    """, encoding='utf-8')

    with pytest.raises(utils.UsageError) as excinfo:
        Settings.from_yaml_file(config_yml)
    assert str(excinfo.value) == f"""Failed to load configuration:
mapping values are not allowed here
  in "{config_yml}", line 5, column 16"""
