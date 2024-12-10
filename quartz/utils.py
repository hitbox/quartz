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
import win32security

from lxml import etree

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

def get_config_module(raise_=True):
    """
    Get the run configuration from environment variable.
    """
    try:
        config_path = os.environ[const.CONFIGVAR]
    except KeyError:
        if raise_:
            raise
    else:
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

def xml_to_dict(element, unprefix=None):
    """
    Recursively converts an XML element into a dictionary.
    """
    # If the element has no children, return its text content
    if not list(element):
        return element.text.strip() if element.text else None

    # If the element has children, recursively process them
    result = {}
    for child in element:
        # Handle duplicate tags by storing as a list
        child_tag = child.tag
        if unprefix:
            child_tag = child_tag[len(unprefix):]
        child_dict = xml_to_dict(child, unprefix=unprefix)

        if child_tag in result:
            if not isinstance(result[child_tag], list):
                result[child_tag] = [result[child_tag]]
            result[child_tag].append(child_dict)
        else:
            result[child_tag] = child_dict

    # Include attributes in the dictionary
    if element.attrib:
        result["@attributes"] = element.attrib

    return result

def validate_xml_with_schema(schema_path, xml_path):
    """
    Validates the XML file against the provided schema.
    """
    with open(schema_path, "rb") as schema_fh:
        schema_doc = etree.XML(schema_fh.read())
        schema = etree.XMLSchema(schema_doc)

    with open(xml_path, "rb") as xml_fh:
        xml_doc = etree.parse(xml_fh)

    if schema.validate(xml_doc):
        print("XML is valid.")
    else:
        print("XML is invalid.")
        print(schema.error_log)
        return None

    return xml_doc

def remove_defaults(xml_doc, schema_path):
    """
    Removes elements with default values from the XML document.
    """
    with open(schema_path, "rb") as schema_fh:
        schema_doc = etree.XML(schema_fh.read())

    ns = {"xs": "http://www.w3.org/2001/XMLSchema"}
    schema_tree = etree.ElementTree(schema_doc)

    defaults = {}
    # Extract default values from the schema
    for element in schema_tree.xpath("//xs:element[@default]", namespaces=ns):
        tag = element.attrib["name"]
        default_value = element.attrib["default"]
        defaults[tag] = default_value

    # Remove elements in the XML that match default values
    root = xml_doc.getroot()
    for element in root.xpath(".//*"):
        if element.tag in defaults and element.text == defaults[element.tag]:
            parent = element.getparent()
            parent.remove(element)

    return xml_doc

account_type_map = {
    1: 'User',
    2: 'Group',
    3: 'Domain',
    4: 'Alias',
    5: 'Computer',
}

def account_info(string_sid):
    """
    Return dict of account info for a SID.
    """
    sid = win32security.ConvertStringSidToSid(string_sid)
    name, domain, type_ = win32security.LookupAccountSid(None, sid)
    account_type = account_type_map.get(type_, 'Unknown')
    return {'name': name, 'domain': domain, 'type': account_type}

def get_user_sid(username):
    """
    Return SID from username.
    """
    command = f'wmic useraccount where name="{username}" get sid'
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    _, sid = result.stdout.split()
    return sid
