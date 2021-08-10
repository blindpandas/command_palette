# coding: utf-8

import sys
import os
import config
from collections import OrderedDict


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "libs")))
import ujson
from fuzzywuzzy import process
from .command_uri import CommandUri
from .command_interpreter import run_command_by_uri
sys.path.pop(0)

COMMANDS_FILE = "command_palette.json"


class CommandStore:
    def __init__(self):
        commands_json = os.path.abspath(os.path.join(config.getUserDefaultConfigPath(), COMMANDS_FILE))
        self.data = ujson.load(open(commands_json, "r"))
        self.ids_to_labels = OrderedDict([(cmd["id"], cmd["label"]) for cmd in self.data])
        self.ids_to_uris = {cmd["id"]: cmd["uri"] for cmd in self.data}

    def get_all_commands(self):
        return self.ids_to_labels

    def filter_by(self, text):
        choices = self.get_all_commands()
        return OrderedDict([
            (k, i)
            for i, j, k
            in process.extractBests(text, choices, limit=1000, score_cutoff=50)
        ])

    def run_command_by_id(self, command_id):
        command_uri = self.ids_to_uris[command_id]
        run_command_by_uri(command_uri)
