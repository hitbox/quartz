APPNAME = 'quartz'

CONFIGVAR = APPNAME.upper() + '_CONFIG'

scheduled_task_priorities = {
    'IDLE': 0,
    'BELOW_NORMAL': 1,
    'NORMAL': 2,
    'ABOVE_NORMAL': 3,
    'HIGH': 4,
    'REAL_TIME': 5,
}

multiple_instances_policies = {
    'IgnoreNew':
        'If a new instance of the task is triggered while another instance is'
        ' already running, the new trigger is ignored.',

    'Queue':
        'If a new instance of the task is triggered while another instance is'
        ' running, the new trigger is added to a queue, and the task runs the'
        ' new instance when the currently running instance finishes.',

    'Parallel':
        'Allows multiple instances of the task to run at the same time. This'
        ' means that if a new instance is triggered while another is still'
        ' running, both instances will execute concurrently.',

    'StopIfGoingOnBatteries':
        'Stops the task if it is running when the system switches to battery'
        ' power.',

    'DoNotStopIfGoingOnBatteries':
        'Allows the task to continue running even if the system switches to'
        ' battery power.',
}

trigger_types = {
    'CalendarTrigger':
        'Defines a task trigger based on specific dates and times, with'
        ' options for recurring schedules. It can be set to run daily,'
        ' weekly, or monthly on particular days. You can also specify a start'
        ' and end time (StartBoundary, EndBoundary), and include a Repetition'
        ' interval to repeat the task during the active period. This is used'
        ' for more flexible, complex schedules and is typically defined in'
        ' the XML schema for Windows Task Scheduler.',
    'TimeTrigger':
        'Triggers the task at a specific date and time (one-time execution).',
    'DailyTrigger':
        'Triggers the task at a specific time every day, with an optional'
        ' interval for multiple days.',
    'WeeklyTrigger':
        'Triggers the task on specific days of the week, with an optional'
        ' interval for weeks.',
    'MonthlyTrigger':
        'Triggers the task on specific days of the month or certain months of'
        ' the year.',
    'BootTrigger':
        'Triggers the task when the system starts (during boot).',
    'LogonTrigger':
        'Triggers the task when a specific user or any user logs on to the system.',
    'IdleTrigger':
        'Triggers the task when the system becomes idle.',
    'EventTrigger':
        'Triggers the task when a specific event occurs in the system or'
        ' application event log.',
    'StartupTrigger':
        'Trigger to run task on system startup.',
}

action_types = {
    'Exec':
        'Executes a program or script as part of the task\'s action.',
    'ComHandler':
        'Triggers a COM-based handler (using a registered COM object) as the'
        ' task\'s action.',
    'SendEmail':
        'Sends an email as part of the task\'s action (Deprecated in Task'
        ' Scheduler since Windows 8).',
    'ShowMessage':
        'Displays a message box as part of the task\'s action (Deprecated in'
        ' Task Scheduler since Windows 8).',
}

valid_permissions = {
    'F': 'Full',
    'R': 'Read',
    'M': 'Modify',
    'RX': 'Read & Execute',
    'W': 'Write',
}
