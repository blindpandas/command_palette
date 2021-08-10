# coding: utf-8

import tones
import wx
import queueHandler
import gui
import ui
from gui import guiHelper
from . command_store import CommandStore


def runScriptModalDialog(dialog, callback=None):
    """Run a modal dialog from a script.
    This will not block the caller,
    but will instead call C{callback} (if provided) with the result from the dialog.
    The dialog will be destroyed once the callback has returned.
    @param dialog: The dialog to show.
    @type dialog: C{wx.Dialog}
    @param callback: The optional callable to call with the result from the dialog.
    @type callback: callable
    """
    mainFrame = gui.mainFrame
    def run():
        mainFrame.prePopup()
        res = dialog.ShowModal()
        mainFrame.postPopup()
        if callback:
            callback(res)
    wx.CallAfter(run)



class CommandPaletteDialog(wx.Dialog):

    def __init__(self):
        super().__init__(
            parent=None,
            title=_("Command Palette"),
        )
        self.store = CommandStore()
        mainSizer=wx.BoxSizer(wx.VERTICAL)
        sHelper = guiHelper.BoxSizerHelper( self, wx.VERTICAL)
        self.commandEntry = sHelper.addLabeledControl (_("Enter command"), wx.TextCtrl)
        self.commandList = sHelper.addLabeledControl (_("Commands"), wx.ListBox, size=(-1, 250))
        mainSizer.Add(sHelper.sizer, border=10, flag=wx.ALL|wx.EXPAND)
        mainSizer.Fit(self)
        self.SetSizer(mainSizer)
        sHelper.addDialogDismissButtons(wx.CLOSE)
        self.CenterOnScreen()
        self.Bind(wx.EVT_BUTTON, self.onClose, id=wx.ID_CLOSE)
        self.Bind(wx.EVT_SHOW, self.onShow, self)
        self.commandEntry.Bind(wx.EVT_KEY_UP, self.onCommandEntryKeyUP, self.commandEntry)
        self.commandEntry.Bind(wx.EVT_TEXT, self.onCommandEntryText, self.commandEntry)
        self.commandList.Bind(wx.EVT_SET_FOCUS, self.onCommandListSetFocus, self.commandList)
        self.commandList.Bind(wx.EVT_KEY_UP, self.onCommandListKeyUp, self.commandList)
        self._last_selected_item = -2

    def popup_command_palette(self):
        if not self.IsShown():
            runScriptModalDialog(self)
            self.commandEntry.SetFocus()

    def onShow(self, event):
        self.populate_command_list(self.store.get_all_commands())

    def onClose(self, event):
        """Hides the dialog."""
        self.Hide()
        self.commandEntry.Clear()
        self.commandList.Clear()
        event.Skip(True)

    def onCommandEntryKeyUP(self, event):
        keycode = event.KeyCode
        if keycode == wx.WXK_DOWN:
            self.commandList.SetFocus()

    def onCommandEntryText(self, event):
        current_text = self.commandEntry.GetLineText(0)
        if not current_text.strip():
            suggestions = self.store.get_all_commands()
        else:
            suggestions = self.store.filter_by(current_text)
        self.populate_command_list(suggestions)
        num_suggestions = len(suggestions)
        if num_suggestions == 1:
            queueHandler.queueFunction(queueHandler.eventQueue, ui.message, f"{num_suggestions} command found")
        else:
            queueHandler.queueFunction(queueHandler.eventQueue, ui.message, f"{num_suggestions} commands found")

    def onCommandListSetFocus(self, event):
        self.select_command(0)

    def onCommandListKeyUp(self, event):
        selected_item = self.commandList.GetSelection()
        if (
            event.GetKeyCode() in (wx.WXK_UP, wx.WXK_DOWN)
            and self._last_selected_item == selected_item
            and selected_item in (0, self.commandList.GetCount() - 1)
        ):
            self.commandEntry.SetFocus()
        else:
            self._last_selected_item = selected_item
        event.Skip()

    def select_command(self, idx):
        command_list = self.commandList
        command_list.SetFocus()
        if idx >= command_list.GetCount():
            return
        command_list.EnsureVisible(idx)
        command_list.Select(idx)

    def populate_command_list(self, commands):
        self.commandList.Clear()
        for cmd in commands:
            self.commandList.Append(cmd)