import csv
import io
import subprocess
import xml.etree.ElementTree as ET

from lxml import etree

# The fields output by schtasks for CSV.
csv_fields = [
    'TaskName',
    'Next Run Time',
    'Status',
]

schtasks_schema = None

class SchemaValidationError(Exception):
    pass

def ensure_schtasks_schema():
    global schtasks_schema
    if schtasks_schema is None:
        schtasks_schema = etree.XMLSchema(file='quartz/task_scheduler.xsd')
        #with open('quartz/task_scheduler.xsd') as schema_file:
        #    schtasks_schema = etree.XMLSchema(file=schema_file)
    return schtasks_schema

def create_from_xml_command(task_name, xml_path, force=False):
    """
    Return command list to create scheduled task from xml file.
    """
    command = ['schtasks', '/create', '/tn', task_name]
    if force:
        command.append('/f')
    # Note: other code expects the path at the end, specifically setting the
    # file permissions to allow another user to access them.
    command.extend(['/xml', xml_path])
    return command

def delete(task_name, confirm=False):
    """
    Delete a scheduled task by name.
    """
    command = ['schtasks', '/delete', '/tn', task_name]
    if not confirm:
        command.append('/f')
    result = subprocess.run(
        command,
        check = True,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
    )
    return result

def exists(task_name):
    try:
        subprocess.run(
            ['schtasks', '/query', '/tn', task_name],
            check = True,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
        )
    except subprocess.CalledProcessError:
        return False
    else:
        return True

def task_create_from_xml(task_name, xml_path, force=False):
    command = create_from_xml_command(task_name, xml_path, force)
    result = subprocess.run(
        command,
        check = True,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
    )
    return result

def get_tasks(verbose=False):
    """
    Get a list of data about scheduled tasks.
    """
    # This is probably the fastest way to get a list of names.
    # XXX
    # - CSV format does not have the schedule data.
    # - Probably other data too.
    # /v gives more fields but produces duplicate headers
    command = ['schtasks', '/query', '/fo', 'CSV']
    if verbose:
        command.append('/v')
    result = subprocess.run(
        command,
        capture_output = True,
        check = True,
        text = True,
    )
    csv_data = io.StringIO(result.stdout)
    reader = csv.reader(csv_data)
    header = next(reader)
    tasks = []
    for row in reader:
        if row == header:
            continue
        tasks.append(dict(zip(header, row)))
    return tasks

def get_tasks_list(verbose=False):
    command = ['schtasks', '/query', '/fo', 'LIST']
    if verbose:
        command.append('/v')
    result = subprocess.run(command, capture_output=True, text=True)
    tasks = []
    lines = result.stdout.splitlines()
    for line in lines:
        if line.startswith('TaskName:'):
            task_name = line.split(':', 1)[1].strip()
            tasks.append(task_name)
    return tasks

def get_tasks_folders(verbose=False):
    command = ['schtasks', '/query', '/fo', 'LIST']
    if verbose:
        command.append('/v')
    result = subprocess.run(command, capture_output=True, text=True)

    lines = result.stdout.splitlines()
    tasks = defaultdict(list)

    for line in lines:
        if line.startswith('TaskName:'):
            task_path = line.split(':', 1)[1].strip()
            folder_path, task_name = task_path.rsplit('\\', 1)
            if folder_path == '':
                # consistent folder keys
                folder_path = '\\'
            tasks[folder_path].append(task_name)

    return dict(tasks)

def get_tasks_xml():
    # XXX
    # - schtasks.exe does not give proper xml for a complete dump of all tasks.
    # - but does for specific tasks.
    command = ['schtasks', '/query', '/xml']
    result = subprocess.run(
        command,
        capture_output = True,
        check = True,
        text = True,
    )
    root = ET.fromstring(result.stdout)
    for task_node in root.findall('task'):
        yield task_node

def run_as_command(task_name, user, password, for_batch=False):
    """
    Return the command to update user to run scheduled task as.
    """
    if for_batch:
        # Escape percent for batch files.
        password = password.replace('%', '%%')
        password = f'"{password}"'
    command = [
        'schtasks', '/change',
        '/tn', task_name,
        '/ru', user,
        '/rp', password,
    ]
    return command

def schtasks_get_data(task_name):
    """
    Nearly complete task data as xml object. Data is not complete because
    schtasks does not dump everything.
    """
    command = ['schtasks', '/query', '/xml', '/tn', task_name]
    result = subprocess.run(
        command,
        capture_output = True,
        check = True,
        text = True,
    )
    root = ET.fromstring(result.stdout)
    return root

def schtasks_list_tasks():
    folders = set()
    tasks = get_tasks()
    for task in tasks:
        task_name = task['TaskName']
        if task_name.startswith('\\Microsoft'):
            continue
        task_path_parts = [part for part in task_name.split('\\') if part]
        if len(task_path_parts) > 1:
            folder_parts = task_path_parts[:-1]
            task_name_part = task_path_parts[-1]
            folders.add('\\'.join(folder_parts))

def task_run_as(task_name, user, password):
    command = run_as_command(task_name, user, password)
    result = subprocess.run(
        command,
        check = True,
        stderr = subprocess.PIPE,
        stdout = subprocess.PIPE,
    )
    return result

def get_xml(task_name, as_string=False):
    command = ['schtasks', '/query', '/xml', '/tn', task_name]
    result = subprocess.run(
        command,
        capture_output = True,
        check = True,
    )
    if as_string:
        return result.stdout
    else:
        # the xml doc says utf-16 but it's really utf-8
        xml_parser = etree.XMLParser(encoding='utf-8')
        root = etree.fromstring(result.stdout, xml_parser)
        return root

def raise_for_validation(root):
    schema = ensure_schtasks_schema()
    if not schema.validate(root):
        error_messages = []
        for error in schema.error_log:
            error_messages.append(
                f'Error in {error.line}, {error.column}: {error.message}')
        raise SchemaValidationError(
            'Schema validation failed\n' + '\n'.join(error_messages))
