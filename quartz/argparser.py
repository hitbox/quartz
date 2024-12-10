import argparse
import collections
import operator
import re

from . import commands
from . import const

def match_operator(pattern):
    regex = re.compile(pattern)
    return regex.match

filter_operators = {
    '==': operator.eq,
    '~=': match_operator,
}

def add_subcommand(name, func, subparsers):
    """
    Add a sub-command to subparsers.
    """
    subcmd = subparsers.add_parser(name, help=func.__doc__)
    subcmd.set_defaults(func=func)
    return subcmd

def dump_subcommand(args):
    """
    Dump scheduled tasks to files.
    """
    # This exists simply to namespace the dump commands.
    return args.func(args)

def filter_eval(arg):
    return eval("lambda task: " + arg)

def add_capture_subcommand(subparsers):
    # capture
    capture_command = add_subcommand(
        'capture',
        commands.capture_tasks,
        subparsers,
    )
    capture_command.add_argument(
        '--select',
        action = 'append',
        default = ['TaskName'],
        help = 'Keys to select from tasks.'
    )
    capture_command.add_argument(
        '--filter',
        action = 'append',
        type = filter_eval,
        help =
            'Add a filter expression. The expression is automatically'
            ' created as a lambda task: ...',
    )
    capture_command.add_argument(
        '--author',
        help = 'Select tasks authored by this user.',
    )

def add_dump_subcommand(subparsers):
    # dump namespace for subcommands
    dump_command = add_subcommand(
        'dump',
        dump_subcommand,
        subparsers,
    )
    dump_subparsers = dump_command.add_subparsers()

    # dump xml
    dump_xml_command = add_subcommand(
        'xml',
        commands.dump_xml,
        dump_subparsers,
    )
    dump_xml_command.add_argument(
        '-o',
        '--output',
        help = 'Filename to output to. Default to stdout.',
    )
    dump_xml_command.add_argument(
        '--replace-backslashes',
        default = '_',
        help = 'Replacement character for backslashes in filenames.',
    )

def add_ls_subcommand(subparsers):
    # ls (list_command)
    ls_command = add_subcommand(
        'ls',
        commands.list_command,
        subparsers,
    )
    ls_command.add_argument(
        'paths',
        nargs = '*',
        help = 'Paths to list. Supports wildcards.',
    )
    ls_command.add_argument(
        '--sort',
        action = 'store_true',
        help = 'Sort the names.',
    )

def add_lsconf_subcommand(subparsers):
    # lsconf (list_configured)
    lsconf_command = add_subcommand(
        'lsconf',
        commands.list_configured,
        subparsers,
    )
    lsconf_command.add_argument(
        'paths',
        nargs = '*',
        help = 'Paths to list. Supports wildcards.',
    )
    lsconf_command.add_argument(
        '--sort',
        action = 'store_true',
        help = 'Sort the names.',
    )
    lsconf_command.add_argument(
        '--check',
        action = 'store_true',
        help = 'Check that task exists in Scheduled Tasks.',
    )

def add_rm_subcommand(subparsers):
    # rm
    remove_command = add_subcommand(
        'rm',
        commands.remove,
        subparsers,
    )
    remove_command.add_argument(
        'name_or_wildcard',
        nargs = '+',
    )

def add_update_subcommand(subparsers):
    # update
    update_command = add_subcommand(
        'update',
        commands.update,
        subparsers,
    )
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

def argument_parser():
    """
    Return an argument parser for editing scheduled tasks from configuration.
    """
    parser = argparse.ArgumentParser(
        prog = const.APPNAME,
    )

    subparsers = parser.add_subparsers()

    add_capture_subcommand(subparsers)
    add_dump_subcommand(subparsers)
    add_ls_subcommand(subparsers)
    add_lsconf_subcommand(subparsers)
    add_rm_subcommand(subparsers)
    add_update_subcommand(subparsers)

    return parser
