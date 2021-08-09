# coding: utf-8

# Copyright (c) 2014-2019 Musharraf Omer
# This file is covered by the GNU General Public License.

"""
  Command Palette
  ~~~~~~~~~~~~~~~~~~~~~~

  The development of this addon is happening on GitHub <https://github.com/blindpandas/command_palette>
  Crafted by Musharraf Omer <info@blindpandas.com>.
"""

import wx
import globalPluginHandler
import scriptHandler
import gui
import speech
import controlTypes
import globalCommands


import addonHandler
addonHandler.initTranslation()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def terminate(self):
        """Terminates the add-on."""

    __gestures = {"kb:nvda+tab": "speakObject"}
