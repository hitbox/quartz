import fnmatch
import logging
import operator
import re
import subprocess
import sys

from . import const
from . import schtasks
from . import utils

class AuthorFilter:

    def __init__(self, author):
        self.author = author

    def __call__(self, task):
        return task.get('RegistrationInfo', {}).get('Author') == self.author


def get_filters_and_selects(args, with_config_module=False):
    """
    Return two lists of filters and selects. A filter is a callable that takes
    a task dict and returns whether to keep the task. A select is simply a key
    to extract from the task dict.
    """
    filters = []
    selects = []

    if with_config_module:
        config_module = utils.get_config_module(raise_=False)
        if config_module:
            # functions taking the task and returning bool
            filters.extend(getattr(config_module, 'CAPTURE_FILTERS', []))

    if args.filter:
        filters.extend(args.filter)

    if args.author:
        filters.append(AuthorFilter(args.author))

    if not filters:
        filters.append(lambda task: True)

    if args.select:
        selects.extend(args.select)

    if not selects:
        selects.append('TaskName')

    return (filters, selects)

def test_needs_xml(filters, selects):
    need_xml = False
    fake_task = dict(zip(schtasks.csv_fields, ''))
    for filter_ in filters:
        try:
            filter_(fake_task)
        except (KeyError, ValueError):
            need_xml = True
            break

    if not need_xml:
        for key in selects:
            if key not in schtasks.csv_fields:
                need_xml = True
                break

    return need_xml

def add_user_data(task, silent=True):
    # Try to add more friendly data about the user this task will run as.
    try:
        string_sid = task['Principals']['Principal']['UserId']
        task['Principals']['Principal']['UserData'] = utils.account_info(string_sid)
    except KeyError:
        if not silent:
            raise

def capture_tasks(args):
    """
    Get the current state of scheduled tasks and convert to Python.
    """
    from pprint import pprint
    logging.basicConfig()
    logger = logging.getLogger(const.APPNAME)
    filters, selects = get_filters_and_selects(args)
    unprefix = '{http://schemas.microsoft.com/windows/2004/02/mit/task}'
    for task in schtasks.get_tasks():
        task_xml = schtasks.get_xml(task['TaskName'])
        task.update(utils.xml_to_dict(task_xml, unprefix=unprefix))
        if all(condition(task) for condition in filters):
            pprint(task)

def capture_tasks(args):
    from pprint import pprint
    pprint(list(schtasks.get_tasks_xml()))

def remove(args):
    """
    Remove the configured scheduled tasks. Like `rm` for scheduled tasks.
    """
    regexes = list(map(shell_pattern_regex, args.name_or_wildcard))
    found_any = False
    for task_name in schtasks.get_tasks_list():
        if any(regex.match(task_name) for regex in regexes):
            found_any = True
            result = schtasks.delete(task_name)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
    if not found_any:
        print('No tasks found')

def update(args):
    """
    Update scheduled tsaks from configuration.
    """
    config_module = utils.get_config_module()

    logging.basicConfig()
    logger = logging.getLogger(const.APPNAME)

    jinja_env = utils.get_jinja_env()
    task_template = jinja_env.get_template('task.xml')

    validate_file_exists = args.validate_file_exists

    with utils.managed_tempfiles(delete=False) as tempfile_creator:
        # tempfile_creator accumulates the created temp files and deletes them
        # on context manager exit.

        admin_batch = None
        for task in config_module.QUARTZ_TASKS:
            # If given, filter tasks by name
            if args.tasks and task.name not in args.tasks:
                continue

            task.validate(file_exists=validate_file_exists)

            context = dict(
                task = task,
            )
            task_xml = task_template.render(**context)

            xml_file = tempfile_creator(
                prefix = task.name.split('\\')[-1] + '_',
                suffix = '.xml',
            )

            xml_file.write(task_xml.encode('utf-8'))
            xml_file.close()

            schtasks_create = schtasks.create_from_xml_command(
                task.name,
                xml_file.name,
                force = True,
            )
            if task.needs_admin():
                # Task requires admin, accumulate for elevated batch script.
                if admin_batch is None:
                    # Create admin batch file.
                    admin_batch = tempfile_creator(
                        encoding = 'utf-8',
                        mode = 'w',
                        prefix = 'schtasks_',
                        suffix = '.bat',
                    )
                    admin_batch.write('@echo off\n\n')
                # Add schtasks create command to batch file.
                lines = utils.batch_lines(schtasks_create, pause_debug=args.pause_debug)
                admin_batch.writelines(lines)
                # If present, add schtasks command to update run as user.
                if task.security_options:
                    # Note: `for_batch` puts quotes around some options, then
                    # we have to avoid escaping the quotes when creating the
                    # batch lines and just join them with spaces.
                    schtasks_run_as = schtasks.run_as_command(
                        task.name,
                        task.security_options.run_as_user,
                        task.security_options.run_as_password,
                        for_batch = True,
                    )
                    lines = utils.batch_lines(
                        schtasks_run_as,
                        # Avoid escaping quoting from `for_batch` option.
                        list2cmdline = ' '.join,
                        pause_debug = args.pause_debug,
                    )
                    admin_batch.writelines(lines)
            else:
                # Run commands as the user we already are.
                result = utils.run_with_logger(logger, schtasks_create)

                # Run as: if given, update the account to run under.
                if task.security_options:
                    schtasks_run_as = schtasks.run_as_command(
                        task.name,
                        task.security_options.run_as_user,
                        task.security_options.run_as_password,
                    )
                    result = utils.run_with_logger(logger, schtasks_run_as)
        if admin_batch:
            admin_batch.close()
            # Prompt for admin and execute batch file.
            run_admin_batch_command = [
                'PowerShell',
                #'-NoExit',
                '-Command', 'Start-Process', '-File', admin_batch.name, '-Wait',
                '-Verb', 'RunAs',
            ]
            result = utils.run_with_logger(
                logger,
                run_admin_batch_command,
                capture_with_pipe = False,
            )

def list_command(args):
    """
    List existing system scheduled tasks.
    """
    filters = [re.compile(fnmatch.translate(pattern)) for pattern in args.paths]
    if not filters:
        filters.append(re.compile(fnmatch.translate('*')))

    tasks = []
    for task_data in schtasks.get_tasks():
        if any(regex.match(task_data['TaskName']) for regex in filters):
            tasks.append(task_data)

    if args.sort:
        tasks = sorted(tasks, key=lambda task_data: task_data['TaskName'])

    for task_data in tasks:
        print(task_data['TaskName'])

by_name = operator.attrgetter('name')

def list_configured(args):
    """
    List scheduled tasks from configuration.
    """
    config_module = utils.get_config_module()

    logging.basicConfig()
    logger = logging.getLogger(const.APPNAME)

    tasks = config_module.QUARTZ_TASKS
    if args.sort:
        tasks = sorted(tasks, key=by_name)

    if not args.check:
        for task in tasks:
            print(task.name)
    else:
        missing = [task for task in tasks if not schtasks.exists(task.name)]
        if missing:
            if args.sort:
                missing = sorted(missing, key=by_name)
            print('Missing scheduled tasks')
            for task in missing:
                print(task.name)

def dump_xml(args):
    """
    Dump configured scheduled tasks to xml.
    """
    config_module = utils.get_config_module()

    logging.basicConfig()
    logger = logging.getLogger(const.APPNAME)

    output_arg = args.output

    if output_arg in (None, '-'):
        output_stream = sys.stdout
    else:
        output_stream = None

    for task in config_module.QUARTZ_TASKS:
        task_xml_string = schtasks.get_xml(task.name, as_string=True)

        if output_stream is not sys.stdout:
            output_filename = output_arg.format(task=task)
            if args.replace_backslashes:
                output_filename = output_filename.replace('\\', args.replace_backslashes)
            output_stream = open(output_filename, 'wb')

        try:
            output_stream.write(task_xml_string)
        finally:
            if output_stream is not sys.stdout:
                output_stream.close()
