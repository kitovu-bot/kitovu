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

import click

from kitovu import utils
from kitovu.sync import syncing


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.argument('plugin')
@click.argument('username')
@click.argument('path')
def sync(plugin: str, username: str, path: str) -> None:
    """Synchronize with the given plugin, username and path."""
    try:
        syncing.start(plugin, username, path)
    except utils.UsageError as ex:
        raise click.ClickException(str(ex))
