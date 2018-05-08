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

import click

from kitovu import utils
from kitovu.sync import syncing
from kitovu.gui import app as guiapp
from kitovu.sync import settings


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


@cli.command()
def fileinfo() -> None:
    """Show the paths to the configuration file and the FileCache."""
    print("The configuration file is located at: {}".format(settings.get_config_file_path()))
    print("\nThe FileCache is located at: {}".format(syncing.get_filecache_path()))
