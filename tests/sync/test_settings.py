import pathlib

from kitovu.sync.settings import YAMLSettingsFactory, Settings, PluginSettings


def test_load_a_sample_yaml_file():
    settings = YAMLSettingsFactory.from_file(pathlib.PurePath('./tests/assets/smb_example_config.yml'))

    expected_root_dir = pathlib.PurePath('~/Documents/HSR/semester_06')
    expected_global_ignore = ['Thumbs.db', '.DS_Store']
    expected_plugins = {
        'skripte-server': PluginSettings(
            plugin_type='smb',
            connection={
                'username': 'example_user',
            },
            syncs=[
                {
                    'name': 'Engineering-Projekt',
                    'ignored': ['SubDir', 'example.txt'],
                    'remote-dir': pathlib.PurePath('Informatik/Fachbereich/Engineering-Projekt/EPJ'),
                    'local-dir': pathlib.PurePath('~/Documents/HSR/semester_06/Engineering-Projekt'),
                }
            ],
        ),
    }

    assert settings.root_dir == expected_root_dir
    assert settings.global_ignore == expected_global_ignore
    assert settings.plugins == expected_plugins

    assert settings == Settings(
        root_dir=expected_root_dir,
        global_ignore=expected_global_ignore,
        plugins=expected_plugins,
    )
