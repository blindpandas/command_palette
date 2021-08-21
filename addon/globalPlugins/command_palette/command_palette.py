# coding: utf-8

import tones
import operator
import wx
import queueHandler
import gui
import ui
from contextlib import contextmanager
from gui import guiHelper
from logHandler import log
from .command_store import CommandStore
from . import command_interpreter
from .immutable_listview import ImmutableObjectListView, ColumnDefn


LISTVIEW_COLUMNS = (
    ColumnDefn(
        title=_("Command"),
        alignment="left",
        width=100,
        string_converter=operator.attrgetter("label"),
    ),
)


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
        super().__init__(parent=None, title=_("Command Palette"), size=(-1, 500))
        self.store = CommandStore()
        self.entryLabelText = _("Enter Command")
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sHelper = guiHelper.BoxSizerHelper(self, wx.VERTICAL)
        self.entryLabel = wx.StaticText(self, -1, self.entryLabelText)
        self.commandEntry = wx.TextCtrl(
            self, -1, size=(400, -1), style=wx.TE_PROCESS_ENTER
        )
        listLabel = wx.StaticText(self, -1, _("Commands"))
        self.commandList = ImmutableObjectListView(
            self, columns=LISTVIEW_COLUMNS, id=wx.ID_ANY, size=(400, 500)
        )
        guiHelper.associateElements(listLabel, self.commandList)
        entrySizer = wx.BoxSizer(wx.VERTICAL)
        entrySizer.Add(self.entryLabel, wx.ALL | wx.EXPAND)
        entrySizer.Add(self.commandEntry, wx.ALL | wx.EXPAND)
        sHelper.addItem(entrySizer, flag=wx.ALL | wx.EXPAND)
        sHelper.addItem(listLabel, flag=wx.ALL | wx.EXPAND)
        sHelper.addItem(self.commandList, flag=wx.ALL | wx.EXPAND)
        mainSizer.Add(sHelper.sizer, border=10, flag=wx.ALL | wx.EXPAND)
        mainSizer.Fit(self)
        self.SetSizer(mainSizer)
        self.CenterOnScreen()
        # Customizations
        self.commandEntry.SetHint(self.entryLabelText)
        self.commandList.UnsetToolTip()
        # Events
        self.Bind(wx.EVT_SHOW, self.onShow, self)
        # Bind Ctrl events
        self.commandEntry.Bind(
            wx.EVT_KEY_UP, self.onCommandEntryKeyUP, self.commandEntry
        )
        self.commandEntry.Bind(wx.EVT_TEXT, self.onCommandEntryText, self.commandEntry)
        self.commandEntry.Bind(
            wx.EVT_TEXT_ENTER, self.onCommandEntryTextEnter, self.commandEntry
        )
        self.commandEntry.Bind(wx.EVT_CHAR, self.onCommandEntryChar, self.commandEntry)
        self.commandList.Bind(
            wx.EVT_SET_FOCUS, self.onCommandListSetFocus, self.commandList
        )
        self.commandList.Bind(wx.EVT_KEY_UP, self.onCommandListKeyUp, self.commandList)
        self.commandList.Bind(wx.EVT_CHAR, self.onCommandListChar, self.commandList)
        # Assign  variables
        self._last_selected_item = -2
        self.__arg_entry_mode_active = False
        self.__current_command = None

    def popup_command_palette(self):
        if not self.IsShown():
            runScriptModalDialog(self)
            self.commandList.SetFocus()

    def enable_arg_entry_mode(self, entry_label_text):
        self.__arg_entry_mode_active = True
        self.entryLabel.SetLabelText(entry_label_text)
        self.commandEntry.SetHint(entry_label_text)
        self.commandEntry.Clear()
        self.commandList.Enable(False)
        self.commandList.set_objects(())
        self.commandEntry.SetFocus()

    def disable_arg_entry_mode(self):
        self.entryLabel.SetLabelText(self.entryLabelText)
        self.commandEntry.SetHint(self.entryLabelText)
        self.commandEntry.Clear()
        self.commandList.Enable(True)
        self.__arg_entry_mode_active = False
        self.__current_command = None

    def onShow(self, event):
        if event.IsShown():
            self.populate_command_list(self.store.get_commands())
        else:
            self.onHide()

    def onHide(self):
        wx.CallAfter(self.disable_arg_entry_mode)
        wx.CallAfter(self.commandEntry.Clear)
        wx.CallAfter(self.commandList.set_objects, ())

    def onCommandEntryKeyUP(self, event):
        if self.__arg_entry_mode_active:
            return
        keycode = event.KeyCode
        if keycode == wx.WXK_DOWN:
            self.commandList.SetFocus()

    def onCommandEntryText(self, event):
        if self.__arg_entry_mode_active:
            event.Skip()
            return
        current_text = self.commandEntry.GetLineText(0)
        if not current_text.strip():
            suggestions = self.store.get_commands()
        else:
            suggestions = self.store.filter_by(current_text)
        self.populate_command_list(suggestions)
        if self.IsShown() and not suggestions:
            queueHandler.queueFunction(
                queueHandler.eventQueue, ui.message, _("No commands")
            )

    def onCommandEntryTextEnter(self, event):
        if not self.__arg_entry_mode_active:
            if not self.commandEntry.IsEmpty() and wx.KeyboardState().ControlDown():
                self.run_shell_command(self.commandEntry.GetValue())
                return
            elif self.commandList.IsEmpty():
                return wx.Bell()
            self.activate_command(self.commandList.get_object(0))
        else:
            if self.commandEntry.IsEmpty():
                return wx.Bell()
            command_copy = self.__current_command.create_copy(
                args={"text": self.commandEntry.GetValue()}
            )
            self.disable_arg_entry_mode()
            self.run_command(command_copy)

    def onCommandEntryChar(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Hide()
            return
        event.Skip()

    def onCommandListSetFocus(self, event):
        self.commandList.set_focused_item(0)

    def onCommandListKeyUp(self, event):
        keycode = event.GetKeyCode()
        selected_item = self.commandList.get_selected()
        if keycode in {wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER}:
            if event.ControlDown():
                if not self.commandEntry.IsEmpty():
                    self.run_shell_command(self.commandEntry.GetValue())
                else:
                    wx.Bell()
                return
            elif selected_item is not None:
                self.activate_command(selected_item)
            return
        if (
            keycode in (wx.WXK_UP, wx.WXK_DOWN)
            and self._last_selected_item == selected_item
            and selected_item in (0, self.commandList.get_count() - 1)
        ):
            self.commandEntry.SetFocus()
        else:
            self._last_selected_item = selected_item
        event.Skip()

    def onCommandListChar(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Hide()
            return
        elif event.KeyCode in {wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER}:
            # Already handled
            return
        elif event.GetKeyCode() == wx.WXK_CONTROL_A:
            self.commandEntry.SetFocus()
            self.commandEntry.SelectAll()
            return
        elif event.GetKeyCode() == wx.WXK_CONTROL_Y:
            self.commandEntry.Redo()
            return
        elif event.GetKeyCode() == wx.WXK_CONTROL_Z:
            self.commandEntry.Undo()
            return
        elif event.KeyCode == 8:
            if not self.commandEntry.IsEmpty():
                self.commandEntry.SetValue(self.commandEntry.Value[:-1])
                self.commandList.set_focused_item(0)
            return
        unicode_char = event.GetUnicodeKey()
        if unicode_char == wx.WXK_NONE:
            event.Skip()
            return
        self.commandEntry.AppendText(chr(unicode_char))
        self.commandList.set_focused_item(0)

    def populate_command_list(self, commands):
        self.commandList.set_objects(commands)

    def activate_command(self, command):
        if command.requires_text_arg:
            self.__current_command = command
            self.enable_arg_entry_mode(command.text_entry_label)
        else:
            self.run_command(command)

    def run_command(self, command):
        wx.CallAfter(self.Hide)
        command_interpreter.run_command(command)

    def run_shell_command(self, command_string, user_error=True):
        try:
            self.run_command(
                command_interpreter.ShellExecuteCommandInterpreter(
                    command_info=command_string
                )
            )
        except OSError:
            if user_error:
                gui.messageBox(
                    _(
                        "Cannot find '{cmd}'. Make sure you typed the name correctly, and then try again"
                    ).format(cmd=command_string),
                    command_string,
                    style=wx.OK | wx.ICON_ERROR,
                )
