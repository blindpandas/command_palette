# coding: utf-8

import sys
import os
import config

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "libs")))
import ujson
from fuzzywuzzy import process
sys.path.pop(0)

COMMANDS_FILE = "command_palette.json"


class CommandStore:
    def __init__(self):
        commands_json = os.path.abspath(os.path.join(config.getUserDefaultConfigPath(), COMMANDS_FILE))
        self.data = ujson.load(open(commands_json, "r"))

    def get_all_commands(self):
        return self.data["commands"]

    def filter_by(self, text):
        choices = self.get_all_commands()
        return [i for i, j in process.extractBests(text, choices, limit=1000, score_cutoff=50)]