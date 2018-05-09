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
from distutils import spawn
import subprocess
import os
import webbrowser

import click

from kitovu import utils
from kitovu.sync import syncing, settings


@click.group()
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
    """Synchronize with the given configuration file."""
    try:
        syncing.start_all(config)
    except utils.UsageError as ex:
        raise click.ClickException(str(ex))


@cli.command()
@click.option('--config', type=pathlib.Path, help="The configuration file to validate")
def validate(config: typing.Optional[pathlib.Path] = None) -> None:
    """Validates the specified configuration file."""
    try:
        syncing.validate_config(config)
    except utils.UsageError as ex:
        raise click.ClickException(str(ex))


@cli.command()
def docs() -> None:
    """Open the documentation in the browser."""
    # FIXME: make version aware
    webbrowser.open_new_tab('https://kitovu.readthedocs.io/en/latest')


DEFAULT_EDITORS = [
    'vim',
    'emacs',
    'nano',
    'editor',
    'notepad',
]


@cli.command()
@click.option('--config', type=pathlib.Path, help="The configuration file to edit")
@click.option('--editor', type=str, help="The command of the editor to use. "
              f"Default: $EDITOR or the first existing out of {', '.join(DEFAULT_EDITORS)}")
def edit(config: typing.Optional[pathlib.Path] = None, editor: typing.Optional[str] = None) -> None:
    """Edit the specified configuration file."""
    if editor is None and 'EDITOR' in os.environ:
        editor = os.environ['EDITOR']
    editor_path: str = _get_editor_path(editor)

    if config is None:
        config = settings.get_config_file_path()
    subprocess.call([editor_path, config])


def _get_editor_path(editor: typing.Optional[str]) -> str:
    if editor is not None:
        path = spawn.find_executable(editor)
        if path is None:
            raise click.ClickException(f"Could not find the editor {editor}")
        return path

    for default_editor in DEFAULT_EDITORS:
        path = spawn.find_executable(default_editor)
        if path is not None:
            return path

    raise click.ClickException('Could not find a valid editor')
