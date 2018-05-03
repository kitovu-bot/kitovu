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
import platform
from distutils import spawn
import subprocess
import os

import click

from kitovu import utils
from kitovu.sync import syncing
from kitovu.gui import app as guiapp


class CliReporter(utils.AbstractReporter):
    """A reporter for printing to the console."""

    def warn(self, message: str) -> None:
        print(message, file=sys.stderr)


@click.group()
def cli() -> None:
    pass


@cli.command()
def gui() -> None:
    """Start the kitovu GUI."""
    sys.exit(guiapp.run())


@cli.command()
@click.option('--config', type=pathlib.Path, help="The configuration file to use")
def sync(config: typing.Optional[pathlib.Path] = None) -> None:
    """Synchronize with the given configuration file."""
    try:
        syncing.start_all(config, CliReporter())
    except utils.UsageError as ex:
        raise click.ClickException(str(ex))


@cli.command()
@click.option('--config', type=pathlib.Path, help="The configuration file to validate")
def validate(config: typing.Optional[pathlib.Path] = None) -> None:
    """Validates the specified configuration file."""
    try:
        syncing.validate_config(config, CliReporter())
    except utils.UsageError as ex:
        raise click.ClickException(str(ex))


AVAILABLE_EDITORS = [
    'vim',
    'emacs',
    'nano',
    'editor',
    'notepad',
]


@cli.command()
@click.option('--config', type=pathlib.Path, help="The configuration file to edit")
@click.option('--editor', type=str, help=f"The command of the editor to use. Default: $EDITOR or the first existing out of {', '.join(AVAILABLE_EDITORS)}")
def edit(config: typing.Optional[pathlib.Path] = None, editor: typing.Optional[str] = None) -> None:
    """Edit the specified configuration file."""
    if editor is None and 'EDITOR' in os.environ:
        editor = os.environ['EDITOR']
    editor_path: typing.Optional[str] = _get_editor_path(editor)

    if editor_path is None:
        if editor is None:
            print('Could not find a valid editor')
        else:
            print(f"Could not find the editor {editor}")
        sys.exit(1)

    subprocess.call([editor_path, config])


def _get_editor_path(editor: typing.Optional[str]) -> typing.Optional[str]:
    if editor is not None:
        return spawn.find_executable(editor)

    for e in AVAILABLE_EDITORS:
        path = spawn.find_executable(e)
        if path is not None:
            return path

    return None
