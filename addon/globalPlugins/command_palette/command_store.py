# coding: utf-8

import sys
import os
import operator
import config
import inputCore
import gui
from collections import OrderedDict
from logHandler import log
from .command_interpreter import CommandInterpreter, NVDAGestureCommand


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "libs")))
import ujson
from fuzzywuzzy import process

sys.path.pop(0)


BUILTIN_COMMANDS_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "builtin_commands.json")
)
USER_COMMANDS_JSON = os.path.normpath(
    os.path.join(os.path.expanduser("~"), "command_palette.json")
)


class CommandStore:
    """Retrieves and parses commands stored as strings."""

    def __init__(self):
        with open(BUILTIN_COMMANDS_FILE, "r") as file:
            data = ujson.load(file)
        if os.path.isfile(USER_COMMANDS_JSON):
            with open(USER_COMMANDS_JSON, "r") as file:
                try:
                    user_commands = ujson.load(file)
                    data.extend(user_commands)
                except:
                    log.exception(
                        f"Failed to load commands from user commands file: '{USER_COMMANDS_JSON}'"
                    )
        nvda_commands = inputCore.manager.getAllGestureMappings(
            obj=gui.mainFrame.prevFocus, ancestors=gui.mainFrame.prevFocusAncestors
        )
        self.commands = [
            CommandInterpreter.create(
                category=item["category"],
                label=item["label"],
                command_info=item["command_info"],
                args=item.get("args", {}),
            )
            for idx, item in enumerate(data)
        ]
        self.commands.extend(
            NVDAGestureCommand(command_info=info, label=f"{cat}: {label}")
            for (cat, cmd_list) in sorted(nvda_commands.items())
            for (label, info) in sorted(cmd_list.items())
        )
        self.search_choices = {cmd: cmd.label for cmd in self.get_commands()}

    def get_commands(self):
        return self.commands

    def filter_by(self, text):
        results = sorted(
            [
                (j, k)
                for i, j, k in process.extractBests(
                    text, self.search_choices, limit=1000, score_cutoff=50
                )
            ],
            key=operator.itemgetter(0),
            reverse=True,
        )
        return [k for (i, k) in results]
