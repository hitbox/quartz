import logging
import subprocess

from . import const
from . import schtasks
from . import utils

def capture_tasks(args):
    """
    Get the current state of scheduled tasks and convert to Python.
    """
    config_module = utils.get_config_module()

    logging.basicConfig()
    logger = logging.getLogger(const.APPNAME)

    filters = getattr(config_module, 'CAPTURE_FILTERS', [])
    if not filters:
        filters.append(lambda task: True)

    for task in schtasks.get_tasks():
        if any(condition(task) for condition in filters):
            #pprint(task)
            task_name = task['TaskName']
            print(task_name)
            #print(task_name.split('\\'))

def remove(args):
    """
    Remove the configured scheduled tasks. Like `rm` for scheduled tasks.
    """
    regexes = list(map(shell_pattern_regex, args.name_or_wildcard))
    found_any = False
    for task_name in schtasks.get_tasks_list():
        if not task_name.startswith('\\Microsoft'):
            print(task_name)
        if any(regex.match(task_name) for regex in regexes):
            found_any = True
            result = schtasks.delete(task_name)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
    if not found_any:
        print('No tasks found')

def remove_configured(args):
    """
    Remove scheduled tasks named from configuration.
    """
    config_module = utils.get_config_module()

    logging.basicConfig()
    logger = logging.getLogger(const.APPNAME)

    for task in config_module.QUARTZ_TASKS:
        if not schtasks.exists(task.name):
            continue
        try:
            schtasks.delete(task.name)
        except subprocess.CalledProcessError as e:
            logger.exception('An exception occurred.')
            if e.stdout:
                logger.error('stdout: %s', e.stdout)
            if e.stderr:
                logger.error('stderr: %s', e.stderr)
            raise

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

def list_configured(args):
    """
    List scheduled tasks from configuration.
    """
    config_module = utils.get_config_module()

    logging.basicConfig()
    logger = logging.getLogger(const.APPNAME)

    tasks = config_module.QUARTZ_TASKS
    if args.sort:
        tasks = sorted(tasks, key=lambda task: task.name)

    for task in tasks:
        print(task.name)
