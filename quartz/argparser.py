import argparse

from . import commands
from . import const

def add_subcommand(name, func, subparsers):
    subcmd = subparsers.add_parser(name, help=func.__doc__)
    subcmd.set_defaults(func=func)
    return subcmd

def argument_parser():
    """
    Return an argument parser for editing scheduled tasks from configuration.
    """
    parser = argparse.ArgumentParser(
        prog = const.APPNAME,
    )

    subparsers = parser.add_subparsers()

    add_subcommand('capture', commands.capture_tasks, subparsers)

    ls_command = add_subcommand('ls', commands.list_configured, subparsers)
    ls_command.add_argument(
        '--sort',
        action = 'store_true',
        help = 'Sort the names.',
    )

    update_command = add_subcommand('update', commands.update, subparsers)
    update_command.add_argument(
        '--tasks',
        nargs = '+',
        help = 'Update only these tasks.',
    )
    update_command.add_argument(
        '--validate-file-exists',
        action = 'store_true',
        help = 'During validation, validate that paths to files exist.',
    )
    update_command.add_argument(
        '--pause-debug',
        action = 'store_true',
        help =
            'Pause after each command in admin batch script. No effect if'
            ' admin is not required.',
    )

    remove_command = add_subcommand('rm', commands.remove, subparsers)
    remove_command.add_argument(
        'name_or_wildcard',
        nargs = '+',
    )

    add_subcommand('rmconf', commands.remove_configured, subparsers)

    return parser
