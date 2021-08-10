# coding: utf-8

# Copyright (c) 2021 Musharraf Omer and Blind Pandas Team
# This file is covered by the GNU General Public License.

"""
  Command Palette
  ~~~~~~~~~~~~~~~~~~~~~~

  The development of this addon is happening on GitHub <https://github.com/blindpandas/command_palette>
  Crafted by Musharraf Omer <info@blindpandas.com>.
"""

import globalPluginHandler
from scriptHandler import script
from .command_palette_dialog import CommandPaletteDialog



# import addonHandler
# addonHandler.initTranslation()




class GlobalPlugin(globalPluginHandler.GlobalPlugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command_palette_dialog = CommandPaletteDialog()

    def terminate(self):
        """Terminates the add-on."""

    @script(
        description=_("Launch the command palette"),
        category="TOOLS",
        gesture="kb:nvda+shift+p",
    )
    def script_launch_command_palette(self, gesture):
        self.command_palette_dialog.popup_command_palette()