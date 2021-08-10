# coding: utf-8


import os
import webbrowser
import shellapi
from abc import ABC, abstractmethod
from dataclasses import dataclass
from logHandler import log
from .command_uri import CommandUri


class CommandError(Exception):
    """Represent failure to execute command."""



@dataclass
class CommandInterpreter(ABC):
    format = None
    registered_runners = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.registered_runners[cls.format] = cls

    def __init__(self, command, **extra_args):
        self.command = command
        self.extra_args = extra_args

    @abstractmethod
    def run(self):
        """Run this command."""



def run_command_by_uri(command_uri):
    try:
        command = CommandUri.from_uri_string(command_uri)
    except ValueError as e:
        raise CommandError("Could not parse command.") from e
    if not command.format in CommandInterpreter.registered_runners:
        raise CommandError("Command not found")
    interpreter_cls = CommandInterpreter.registered_runners[command.format]
    interpreter = interpreter_cls(
        command=command.path,
        **command.primary_args
    )
    interpreter.run()


class ShellCommandInterpreter(CommandInterpreter):
    format = "shell"

    def run(self):
        if self.command == "home":
            self.command = os.path.expanduser("~")
        cmd = f'"{self.command}"'
        shellapi.ShellExecute(None, "open", cmd, "", "", 1)


class UrlOpenCommand(CommandInterpreter):
    format = "url"

    def run(self):
        webbrowser.open_new(self.command)
