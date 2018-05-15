"""
Module that contains the command line app.

Why does this file exist, and why not put this in __main__?

  You might be tempted to import things from __main__ later, but that will cause
  problems: the code will get executed twice:

  - When you run `python -mkitovu` python will execute
    ``__main__.py`` as a script. That means there won't be any
    ``kitovu.__main__`` in ``sys.modules``.
  - When you import __main__ it will get executed again (as a module) because
    there's no ``kitovu.__main__`` in ``sys.modules``.

  Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration
"""

import pathlib
import typing
import sys
import logging
import webbrowser

import click

from kitovu import utils
from kitovu.sync import syncing, settings, filecache


@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.option('--loglevel',
              type=click.Choice(['debug', 'info', 'warning', 'error', 'critical']),
              default='info')
def cli(loglevel: str) -> None:
    level: int = getattr(logging, loglevel.upper())
    if level == logging.DEBUG:
        logformat = '%(asctime)s [%(levelname)5s] %(name)25s %(message)s'
    else:
        logformat = '%(message)s'

    logging.basicConfig(level=level, format=logformat)


@cli.command()
def gui() -> None:
    """Start the kitovu GUI."""
    from kitovu.gui import app as guiapp
    sys.exit(guiapp.run())


@cli.command()
@click.option('--config', type=pathlib.Path, help="The configuration file to use")
def sync(config: typing.Optional[pathlib.Path] = None) -> None:
    """Synchronize new files."""
    try:
        syncing.start_all(config)
    except utils.UsageError as ex:
        raise click.ClickException(str(ex))


@cli.command()
@click.option('--config', type=pathlib.Path, help="The configuration file to validate")
def validate(config: typing.Optional[pathlib.Path] = None) -> None:
    """Validate the configuration file."""
    try:
        syncing.validate_config(config)
    except utils.UsageError as ex:
        raise click.ClickException(str(ex))


@cli.command()
def fileinfo() -> None:
    """Show the paths to files kitovu uses."""
    print("The configuration file is located at: {}".format(settings.get_config_file_path()))
    print("The file cache is located at: {}".format(filecache.get_path()))


@cli.command()
def docs() -> None:
    """Open the documentation in the browser."""
    # FIXME: Load version-aware documentation once we have a first versioned release.
    webbrowser.open_new_tab('https://kitovu.readthedocs.io/en/latest')


@cli.command()
@click.option('--config', type=pathlib.Path, help="The configuration file to edit")
@click.option('--editor', type=str, help="The command of the editor to use. "
              f"Default: $EDITOR or the first existing out of "
              f"{settings.EditorSpawner.DEFAULT_EDITORS_STR}")
def edit(config: typing.Optional[pathlib.Path] = None, editor: typing.Optional[str] = None) -> None:
    """Edit the configuration file."""
    spawner = settings.EditorSpawner()
    try:
        spawner.edit(config, editor)
    except utils.UsageError as ex:
        raise click.ClickException(str(ex))
