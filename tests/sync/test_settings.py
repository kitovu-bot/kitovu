import os
import re
import pathlib

import pytest

from kitovu import utils
from kitovu.sync import settings
from kitovu.sync.settings import Settings, ConnectionSettings


@pytest.fixture
def default_config(monkeypatch, temppath):
    monkeypatch.setattr(settings.appdirs, 'user_config_dir', lambda _name: str(temppath))
    return temppath / 'kitovu.yaml'


def test_creating_default_config(default_config, monkeypatch):
    monkeypatch.setattr(settings.subprocess, 'call', lambda args: None)
    assert not default_config.exists()
    spawner = settings.EditorSpawner()
    spawner.edit()
    assert default_config.exists()


def test_load_unreadable_file(temppath):
    settings = temppath / 'kitovu.yaml'
    settings.touch()
    settings.chmod(0)
    if os.access(settings, os.R_OK):
        pytest.skip("Failed to make file unreadable")  # pragma: no cover

    with pytest.raises(utils.UsageError):
        Settings.from_yaml_file(settings)


def test_load_a_sample_yaml_file(assets_dir):
    settings = Settings.from_yaml_file(assets_dir / "smb_example_config.yml")

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


def test_load_default_location(default_config):
    with pytest.raises(utils.UsageError,
                       match=re.escape(f'Could not find the file {default_config}')):
        Settings.from_yaml_file()


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
