# coding: utf-8

import importlib
import os
import webbrowser
import baseObject
import shellapi
import api
import config
import keyboardHandler
import scriptHandler
import globalCommands
import vision
from abc import ABC, abstractmethod
from contextlib import contextmanager
from functools import partial
from copy import deepcopy
from dataclasses import dataclass
from urllib import parse
from logHandler import log


USER_COMMANDS_JSON_HEADER = (
    "[\n"
    "  {\n"
    '    "category": "app",\n'
    '    "label": "Open Calculator",\n'
    '    "command_info": "calc.exe"\n'
    "  }\n"
    "\n"
    "]"
)


@contextmanager
def cwd():
    old_cwd = os.getcwd()
    try:
        home_dir = os.path.expanduser("~")
        os.chdir(home_dir)
        yield
    finally:
        os.chdir(old_cwd)


class CommandError(Exception):
    """Represent failure to execute command."""


class ChangeCommand(Exception):
    """Change the old command to the new command."""

    def __init__(self, old_command, new_command):
        self.old_command = old_command
        self.new_command = new_command


@dataclass
class CommandInterpreter(ABC):
    __slots__ = [
        "label",
        "command_info",
        "args",
    ]
    category = None
    registered_categories = {}
    __requires_text_arg__ = False
    __text_entry_label__ = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.registered_categories[cls.category] = cls

    def __init__(self, command_info, args=None, label=None):
        self.label = label
        self.command_info = command_info
        self.args = args or {}

    def __hash__(self):
        return hash((self.category, self.label, self.command_info))

    def __repr__(self):
        return f"CommandInterpreter (category='{self.category}', command_info='{self.command_info}', args={self.args})"

    @classmethod
    def create(cls, category, command_info, args=None, label=None):
        command_cls = cls.registered_categories[category]
        return command_cls(command_info, args, label)

    @property
    def requires_text_arg(self):
        return self.__requires_text_arg__ or self.args.get("requires_text_arg")

    @property
    def text_entry_label(self):
        if self.requires_text_arg:
            return self.__text_entry_label__ or self.args.get("text_entry_label")

    def create_copy(self, command_info=None, args=None, label=None):
        clone = deepcopy(self)
        clone.command_info = command_info or self.command_info
        clone.args.update(args or {})
        clone.label = label or self.label
        return clone

    @abstractmethod
    def run(self):
        """Run this command."""


def run_command(command):
    try:
        command.run()
    except ChangeCommand as e:
        run_command(e.new_command)


class ShellExecuteCommandInterpreter(CommandInterpreter):
    category = "app"

    def run(self):
        cmd = f'"{self.command_info}"'
        with cwd():
            shellapi.ShellExecute(None, "open", cmd, "", "", 1)


class UrlOpenCommand(CommandInterpreter):
    category = "web.page"

    def run(self):
        webbrowser.open_new(self.command_info)


class PythonFuncionCommand(CommandInterpreter):
    category = "python"

    def run(self):
        module, func = self.command_info.split(":")
        module = importlib.import_module(module)
        module.func(self)


class SearchWebCommand(CommandInterpreter):
    category = "web.search"
    __requires_text_arg__ = True
    __text_entry_label__ = _("Search term")

    def run(self):
        if self.args.get("search_as_suffix", False):
            quoted = parse.quote_plus(self.args["text"])
            full_search_url = f"{self.command_info.strip('/')}/{quoted}"
        else:
            query = parse.urlencode({self.args["query"]: self.args["text"]})
            full_search_url = f"{self.command_info.strip('?')}?{query}"
        raise ChangeCommand(
            old_command=self, new_command=UrlOpenCommand(full_search_url)
        )


class SpecialCommand(CommandInterpreter):
    category = "special"

    def run(self):
        func = getattr(self, f"run_{self.command_info}", None)
        if func is None:
            raise CommandError(f"Unknown special command: {self.command}")
        func()

    def run_home(self):
        home_dir = os.path.normpath(os.path.expanduser("~"))
        raise ChangeCommand(
            old_command=self, new_command=ShellExecuteCommandInterpreter(home_dir)
        )

    def run_open_user_commands_json(self):
        from .command_store import USER_COMMANDS_JSON

        if not os.path.isfile(USER_COMMANDS_JSON):
            with open(USER_COMMANDS_JSON, "w", encoding="utf-8") as newfile:
                newfile.write(USER_COMMANDS_JSON_HEADER)
        raise ChangeCommand(
            old_command=self,
            new_command=ShellExecuteCommandInterpreter(USER_COMMANDS_JSON),
        )

    def run_open_scratchpad_directory(self):
        scratchpad_directory = config.getScratchpadDir()
        raise ChangeCommand(
            old_command=self,
            new_command=ShellExecuteCommandInterpreter(scratchpad_directory),
        )


class NVDAGestureCommand(CommandInterpreter):
    category = "nvda"

    def run(self):
        script_func = self.findScript(
            module=self.command_info.moduleName,
            cls=self.command_info.cls,
            scriptName=self.command_info.scriptName,
        )
        if script_func is None:
            func = getattr(
                self.command_info.cls, f"script_{self.command_info.scriptName}"
            )
            script_func = partial(func, None)
        first_kb_gesture = tuple(
            filter(lambda g: g.startswith("kb:"), self.command_info.gestures)
        )
        if first_kb_gesture:
            gesture = keyboardHandler.KeyboardInputGesture.fromName(
                first_kb_gesture[0][3:]
            )
            scriptHandler.queueScript(script_func, gesture)
        else:
            script_func(None)

    def findScript(self, module, cls, scriptName):
        focus = api.getFocusObject()
        if not focus:
            return None
        if scriptName.startswith("kb:"):
            # Emulate a key press.
            return scriptHandler._makeKbEmulateScript(scriptName)
        # Global plugin level.
        if cls == "GlobalPlugin":
            for plugin in globalPluginHandler.runningPlugins:
                if module == plugin.__module__:
                    func = getattr(plugin, "script_%s" % scriptName, None)
                    if func:
                        return func
        # App module level.
        app = focus.appModule
        if app and cls == "AppModule" and module == app.__module__:
            func = getattr(app, "script_%s" % scriptName, None)
            if func:
                return func
        # Vision enhancement provider level
        for provider in vision.handler.getActiveProviderInstances():
            if isinstance(provider, baseObject.ScriptableObject):
                if cls == "VisionEnhancementProvider" and module == provider.__module__:
                    func = getattr(app, "script_%s" % scriptName, None)
                    if func:
                        return func
        # Tree interceptor level.
        treeInterceptor = focus.treeInterceptor
        if treeInterceptor and treeInterceptor.isReady:
            func = getattr(treeInterceptor, "script_%s" % scriptName, None)
            if func:
                return func
        # NVDAObject level.
        func = getattr(focus, "script_%s" % scriptName, None)
        if func:
            return func
        for obj in reversed(api.getFocusAncestors()):
            func = getattr(obj, "script_%s" % scriptName, None)
            if func and getattr(func, "canPropagate", False):
                return func
        # Global commands.
        func = getattr(globalCommands.commands, "script_%s" % scriptName, None)
        if func:
            return func
        return None
