import importlib
import logging
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from collections import defaultdict
from contextlib import contextmanager
from operator import itemgetter
from pprint import pprint

import jinja2

from . import const

def basename_without_extension(path):
    """
    The basename of a path without the file extension.
    """
    return os.path.splitext(os.path.basename(path))[0]

def batch_lines(command, list2cmdline=None, pause_debug=False):
    """
    Stringify `command` and add errorlevel check for batch file lines. Intended
    use with .writelines.
    """
    if list2cmdline is None:
        list2cmdline = subprocess.list2cmdline
    lines = []
    if pause_debug:
        lines.append('pause\n')
    lines.append(list2cmdline(command) + '\n')
    if pause_debug:
        lines.append('pause\n')
    lines.extend([
        # Exit with error for each command
        'if %errorlevel% neq 0 (\n',
        '    exit /b %errorlevel%\n',
        ')\n',
        '\n',
    ])
    return lines

def get_config_module():
    """
    Get the run configuration from environment variable.
    """
    config_path = os.environ[const.CONFIGVAR]
    config_module = importlib.import_module(config_path)
    return config_module

def get_jinja_env():
    """
    Return the jinja environment.
    """
    jinja_env = jinja2.Environment(
        autoescape = jinja2.select_autoescape(),
        loader = jinja2.FileSystemLoader('templates'),
    )
    return jinja_env

@contextmanager
def managed_tempfiles(class_=tempfile.NamedTemporaryFile, **base_kwargs):
    # XXX
    # - Make delete kwarg off limits?
    temp_files = []
    try:
        def tempfile_creator(**kwargs):
            if base_kwargs is not None:
                for key, val in base_kwargs.items():
                    kwargs.setdefault(key, val)
            file = class_(**kwargs)
            temp_files.append(file)
            return file
        yield tempfile_creator
    finally:
        for file in temp_files:
            file.close()
            try:
                os.remove(file.name)
            except OSError:
                pass

def set_file_permissions(file_path, user, permission_level):
    """
    Sets permissions on a file for a specified user using icacls.

    Parameters:
    - file_path (str): The path of the file to set permissions on.
    - user (str): The user (in "domain\\username" or "username" format) to grant permissions to.
    - permission_level (str): The permission level to grant (e.g., 'F' for Full, 'R' for Read).

    Raises:
    - FileNotFoundError: If the specified file does not exist.
    - ValueError: If the permission level is invalid.
    - RuntimeError: If the icacls command fails.
    """
    # Validate the file exists
    if not os.path.isfile(file_path):
        raise FileNotFoundError("File does not exist")

    if permission_level not in const.valid_permissions:
        raise ValueError("Invalid permission level")

    # Run the icacls command to set permissions
    grant_option = f"{user}:{permission_level}"
    result = subprocess.run(
        ["icacls", file_path, "/grant", grant_option],
        capture_output = True,
        check = True,
        text = True,
    )
    return result

def shell_pattern_regex(pattern):
    """
    Compile filename pattern into regex.
    """
    return re.compile(fnmatch.translate(pattern))

def run_with_logger(logger, command, capture_with_pipe=True):
    """
    Context manager to run a subprocess command and log if exited with error.
    """
    kwargs = dict(check=True)
    if capture_with_pipe:
        kwargs['stdout'] = subprocess.PIPE
        kwargs['stderr'] = subprocess.PIPE
    try:
        result = subprocess.run(command, **kwargs)
    except subprocess.CalledProcessError as e:
        logger.exception('An exception occurred.')
        if e.stdout:
            logger.error('stdout: %s', e.stdout)
        if e.stderr:
            logger.error('stderr: %s', e.stderr)
        raise
    else:
        return result
