import abc
import datetime
import os

from . import const
from . import validate

class Base(abc.ABC):
    """
    Base for all scheduled task objects.
    """

    def to_dict(self):
        """
        Return dict of all non-private, non-callable attributes.
        """
        data = {}
        for key, val in self.__dict__.items():
            if key.startswith('_') or callable(val):
                continue

            if hasattr(val, 'to_dict'):
                val = val.to_dict()

            data[key] = val

        return data

    @abc.abstractmethod
    def validate(self, **kwargs):
        """
        Validate the values of this instance's attributes.
        """

    @abc.abstractmethod
    def needs_admin(self):
        return False


class Task(Base):

    def __init__(
        self,
        name,
        author = None,
        description = None,
        actions = None,
        triggers = None,
        settings = None,
        registration_date = None,
        security_options = None,
    ):
        """
        :param name:
            The task's name, including it's path in the folder structure.
        :param author:
            String of the task's author.
        :param description:
            Self explanatory. Free text field.
        :param actions:
            List of Action objects.
        :param triggers:
            List of Trigger objects.
        :param settings:
            A Settings object. Defaults to the defaults of the Settings class.
        :param registration_date:
            The created date.
        :param security_options:
            A SecurityOptions object. Defaults to that object's defaults.
        """
        self.name = name
        self.author = author
        self.description = description
        if actions is None:
            actions = []
        self.actions = actions
        if triggers is None:
            triggers = []
        self.triggers = triggers
        if settings is None:
            settings = Settings()
        self.settings = settings
        if security_options is None:
            security_options = SecurityOptions()
        self.security_options = security_options

    @property
    def uri(self):
        """
        Helpful for examining the XML output. The name, itself, seems to be
        most important.
        """
        return self.name

    @property
    def registration_date_or_now(self):
        if self.registration_date is None:
            return datetime.datetime.now()
        return self.registration_date

    def validate(self, **kwargs):
        for action in self.actions:
            action.validate(**kwargs)

        for trigger in self.triggers:
            trigger.validate(**kwargs)

        self.settings.validate(**kwargs)
        self.security_options.validate(**kwargs)

    def needs_admin(self):
        if any(action.needs_admin() for action in self.actions):
            return True

        if any(trigger.needs_admin() for trigger in self.triggers):
            return True


class Action(Base):
    """
    An action to do when a scheduled task is triggered.
    """

    windows_venv_pythonw_args = ['venv', 'Scripts', 'pythonw.exe']

    def __init__(
        self,
        type_,
        command,
        arguments,
        working_directory,
    ):
        """
        :param type_:
            Action type, usually Exec.
        :param command:
            String command or program to run.
        :param arguments:
            String arguments to give the command.
        :param working_directory:
            String path of working directory.
        """
        self.type_ = type_
        self.command = command
        self.arguments = arguments
        self.working_directory = working_directory

    @classmethod
    def from_exec_pythonw(cls, working_directory, arguments):
        """
        Instance from common pattern of running pythonw in a working directory
        and giving it arguments.
        """
        pythonw_path = os.path.join(working_directory, *cls.windows_venv_pythonw_args)
        instance = cls(
            type_ = 'Exec',
            command = pythonw_path,
            arguments = arguments,
            working_directory = working_directory,
        )
        return instance

    def validate(self, **kwargs):
        if self.type_ not in const.action_types:
            raise ValueError('Invalid action type.')
        # TODO
        # - a way to test the command without actually running it?
        if kwargs.get('file_exists') and not os.path.exists(self.working_directory):
            raise ValueError('Working directory does not exist.')

    def needs_admin(self):
        return False


class IdleSettings(Base):

    def __init__(
        self,
        stop_on_idle_end = True,
        restart_on_idle = False,
    ):
        self.stop_on_idle_end = stop_on_idle_end
        self.restart_on_idle = restart_on_idle

    def validate(self, **kwargs):
        # TODO
        # - Validate True/False?
        pass

    def needs_admin(self):
        return False


class Settings(Base):
    """
    Scheduled task settings.
    """

    def __init__(
        self,
        multiple_instances_policy = None,
        disallow_start_if_on_batteries = False,
        stop_if_going_on_batteries = False,
        allow_hard_terminate = True,
        start_when_available = True,
        run_only_if_network_available = False,
        idle_settings = None,
        allow_start_on_demand = True,
        enabled = True,
        hidden = False,
        run_only_if_idle = False,
        wake_to_run = False,
        execution_time_limit = None,
        priority = None,
    ):
        """
        :param multiple_instances_policy:
            One of multiple_instances_policies.
        :param disallow_start_if_on_batteries:
        :param stop_if_going_on_batteries:
        :param allow_hard_terminate:
        :param start_when_available:
        :param run_only_if_network_available:
        :param idle_settings:
        :param allow_start_on_demand:
        :param enabled:
        :param hidden:
        :param run_only_if_idle:
        :param wake_to_run:
        :param execution_time_limit:
            TODO:
                Document and validate these values.
            PT0S - No time limit.
        :param priority:
        """
        if multiple_instances_policy is None:
            multiple_instances_policy = 'IgnoreNew'
        self.multiple_instances_policy = multiple_instances_policy
        self.disallow_start_if_on_batteries = disallow_start_if_on_batteries
        self.stop_if_going_on_batteries = stop_if_going_on_batteries
        self.allow_hard_terminate = allow_hard_terminate
        self.start_when_available = start_when_available
        self.run_only_if_network_available = run_only_if_network_available
        if idle_settings is None:
            idle_settings = IdleSettings()
        self.idle_settings = idle_settings
        self.allow_start_on_demand = allow_start_on_demand
        self.enabled = enabled
        self.hidden = hidden
        self.run_only_if_idle = run_only_if_idle
        self.wake_to_run = wake_to_run
        self.execution_time_limit = execution_time_limit
        if priority is None:
            priority = 'NORMAL'
        self.priority = const.scheduled_task_priorities[priority]

    def validate(self, **kwargs):
        if self.multiple_instances_policy not in const.multiple_instances_policies:
            raise ValueError('Invalid multiple_instances_policy value.')
        self.idle_settings.validate(**kwargs)
        if self.priority not in const.scheduled_task_priorities.values():
            raise ValueError('Invalid priority value.')

    def needs_admin(self):
        return False


class SecurityOptions(Base):
    """
    A scheduled task meta object that does not exists in the XML. This is
    implemented outside the normal importing methods. Primarily it is options
    for running a task as a different user.
    """

    def __init__(
        self,
        run_as_user,
        run_as_password,
    ):
        """
        :param run_as_user:
            String name of user account to run as.
        :param run_as_password:
            String of password for run_as_user.
        """
        self.run_as_user = run_as_user
        self.run_as_password = run_as_password

    def validate(self, **kwargs):
        # TODO
        pass

    def needs_admin(self):
        return False


class Repetition(Base):
    """
    Repetition for a trigger.
    """

    def __init__(
        self,
        interval,
        duration,
        stop_at_duration_end,
    ):
        """
        :param interval:
            String like "PT5M", which means a "Period of Time every five
            minutes." An ISO 8601 duration.
        :param duration:
            String for how long this repetition is in effect. For example,
            "P1D" for "a period of one day."
        :param stop_at_duration_end:
            True/false, forcibly stop the task after it's duration.
        """
        self.interval = interval
        self.duration = duration
        self.stop_at_duration_end = stop_at_duration_end

    def validate(self):
        if not validate.iso8601_duration(self.interval):
            raise ValueError('Invalid interval value.')
        if not validate.iso8601_duration(self.duration):
            raise ValueError('Invalid duration value.')

    def needs_admin(self):
        return False


class Trigger(Base):
    """
    Event to trigger a scheduled task.
    """

    def __init__(
        self,
        type_,
        repetition = None,
        start_boundary = None,
        enabled = False,
        schedule_by_day = None,
    ):
        """
        :param type_:
            One of trigger_types.
        :param repetition:
        :param start_boundary:
        :param enabled:
        :param schedule_by_day:
        """
        self.type_ = type_
        self.repetition = repetition
        self.start_boundary = start_boundary
        self.enabled = enabled
        self.schedule_by_day = schedule_by_day

    def validate(self, **kwargs):
        if self.type_ not in const.trigger_types:
            raise ValueError('Invalid trigger type.')

    def needs_admin(self):
        return False


class LogonTrigger(Trigger):

    def __init__(
        self,
        user_id,
        **kwargs
    ):
        type_ = 'LogonTrigger'
        super().__init__(type_, **kwargs)
        self.user_id = user_id


class EveryMinutes(Trigger):
    """
    Trigger every n minutes every day.
    """

    def __init__(
        self,
        start_boundary_date,
        interval_minutes,
        start_boundary_offset_minutes = 0,
        **kwargs
    ):
        type_ = 'CalendarTrigger'
        repetition = Repetition(
            interval = f'PT{interval_minutes}M',
            duration = 'P1D',
            stop_at_duration_end = False,
        )
        start_boundary_dt = datetime.datetime.combine(
            start_boundary_date,
            datetime.time(minute=start_boundary_offset_minutes)
        )
        start_boundary = start_boundary_dt.isoformat(timespec='seconds')
        schedule_by_day = {
            'days_interval': '1',
        }
        args = (type_, repetition, start_boundary)
        super().__init__(*args, schedule_by_day=schedule_by_day, **kwargs)


class OnceDaily(Trigger):

    def __init__(
        self,
        time,
        start_boundary_date = None,
        **kwargs
    ):
        """
        :param time:
            A datetime.time.
        :param start_boundary_date:
            A datetime.date.
        """
        if start_boundary_date is None:
            start_boundary_date = datetime.date.today()
        type_ = 'CalendarTrigger'
        start_boundary_dt = datetime.datetime.combine(
            start_boundary_date,
            time,
        )
        start_boundary = start_boundary_dt.isoformat(timespec='seconds')
        schedule_by_day = kwargs.setdefault('schedule_by_day', {})
        schedule_by_day.setdefault('days_interval', 1)
        super().__init__(type_, start_boundary=start_boundary, **kwargs)


class BootTrigger(Trigger):

    def __init__(
        self,
        **kwargs
    ):
        type_ = 'BootTrigger'
        super().__init__(type_, **kwargs)

    def needs_admin(self):
        # As near as I can tell, the existence of a boot trigger requires admin
        # to create the task.
        return True
