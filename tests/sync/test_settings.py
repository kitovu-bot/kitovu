import pathlib

from kitovu.sync import syncing


def test_load_a_sample_yaml_file():
    settings = syncing.SettingsFactory.from_yaml_file(pathlib.PurePath('./tests/assets/smb_example_config.yml'))

    expected_root_dir = pathlib.PurePath('~/Documents/HSR/semester_06')
    expected_global_ignore = ['Thumbs.db', '.DS_Store']
    expected_plugins = {
        'skripte-server': syncing.PluginSettings(
            plugin_type='smb',
            connection={
                'user': 'example_user',
            },
            syncs=[
                {
                    'name': 'Engineering-Projekt',
                    'ignored': ['SubDir', 'example.txt'],
                    'remote-dir': 'Informatik/Fachbereich/Engineering-Projekt/EPJ',
                }
            ],
        ),
    }

    assert settings.root_dir == expected_root_dir
    assert settings.global_ignore == expected_global_ignore
    assert settings.plugins == expected_plugins

    assert settings == syncing.Settings(
        root_dir=expected_root_dir,
        global_ignore=expected_global_ignore,
        plugins=expected_plugins,
    )
