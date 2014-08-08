'''
Create a simple GUI to display and save readings for the Radio Shack 
22-812 digital multimeter.

When the Start button is pressed, the data are written to the log file.
'''

import wx, re
from threading import Timer
from time import strftime, time
from rs22812 import RS22812
from sys import argv, stdout
from os.path import join, split
import wx.lib.agw.balloontip as BT

debug = False
font_factor = 1.75

# You can modify some features of the program here

settings = {
    "frame size horiz"      : 500,
    "frame size vert"       : 280,

    "time font size"        : 14,
    "reading font size"     : 40,

    "reading fg color"      : "black",
    "reading bg color"      : "#eeeeff",

    "time fg color"         : "black",
    "time bg color"         : "white",

    "log file"              : "readings.log",
    "default sample rate"   : "1",

    "tips" : {
        "Set" : '''You can use this button to change the sampling time
                   while the program is running.''',
        "Start" : '''Start and stop getting measurements from the meter.
            Make sure the meter is turned on and the serial cable is
            connected before pressing this button; otherwise, the program
            will hang.
            ''',
        "Textbox" : '''Enter a positive integer or floating point number to
            set the sampling rate.
            ''',
        "Reading" : '''Display of the meter's reading.  You may see additional
            text such as Auto (means autoranging is on), REL (readings are
            relative), or MAX/MIN (maximum and minimum readings are being
            captured).  The units are displayed after the number.  If ~ is
            included, it means an AC measurement.  0F means overflow and
            5hrt means "Short".
            ''',
        "Time stamp" : "Gives the time stamp of the last displayed reading.",

        "tip fg color" : "black",
        "tip bg color" : "#FFFED1",
        "start delay ms" : 1000,
    }
}

def D(s, no_eol=False):
    if debug:
        stdout.write(s)
        if not no_eol: stdout.write("\n")

def TipFormatter(tip, length=50):
    '''This function will format a string to fit into the specified number
    of spaces.  Multiple spaces will be replaced by one space character.
    The intent is to let you make nice looking dictionary entries for the
    tip texts using triple-quoted strings, but have them appear uniformly-
    wrapped on the screen.
    '''
    fields, s, line = re.sub("  +", " ", tip.replace("\n", "")).split(), "", ""
    for f in fields:
        if len(line) + len(f) < length:
            line += f + " "
        else:
            s += line + "\n"
            line = f + " "
    s += line 
    return s

class MyFrame(wx.Frame):
    def __init__(self, parent, id):
        wx.Frame.__init__(self, parent, id, "meter.py", 
            size=(settings["frame size horiz"], settings["frame size vert"]))
        self.interval = 0
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour("white")
        self.status_bar = self.CreateStatusBar()
        self.add_sizer()
        self.tips_button()
        self.time_stamp()
        self.reading()
        self.start_button()
        self.sampling()
        self.time_stuff()
        self.events()
        self.log_file()
        self.tips()
        self.log.write("\nProgram started " + self.CurrentTime() + "\n")
        self.meter = None  # Start off with no meter object
        self.OnTips(None)

    def log_file(self):
        # Open log file
        head, tail = split(argv[0])
        self.log = open(join(head, settings["log file"]), "a")

    def tips(self):
        # Set up our tips
        font_title = wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD)
        font_text  = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL)
        shape = BT.BT_ROUNDED
        style = BT.BT_LEAVE
        self.tips = {}
        dict = settings["tips"]
        self.tips["Start"] = [BT.BalloonTip(topicon=None, 
            toptitle="Start button", 
            message=TipFormatter(dict["Start"]),
            shape=shape, tipstyle=style),
            self.start]
        self.tips["Set"] = [BT.BalloonTip(topicon=None, 
            toptitle="Set button", 
            message=TipFormatter(dict["Set"]),
            shape=shape, tipstyle=style),
            self.set]
        self.tips["Textbox"] = [BT.BalloonTip(topicon=None, 
            toptitle="Sampling interval", 
            message=TipFormatter(dict["Textbox"]),
            shape=shape, tipstyle=style),
            self.rate]
        self.tips["Reading"] = [BT.BalloonTip(topicon=None, 
            toptitle="Reading", 
            message=TipFormatter(dict["Reading"]),
            shape=shape, tipstyle=style),
            self.reading]
        self.tips["Time stamp"] = [BT.BalloonTip(topicon=None, 
            toptitle="Time stamp", 
            message=TipFormatter(dict["Time stamp"]),
            shape=shape, tipstyle=style),
            self.timestamp]

        for name in self.tips:
            self.tips[name][0].SetBalloonColour(dict["tip bg color"])
            self.tips[name][0].SetMessageColour(dict["tip fg color"])
            self.tips[name][0].SetStartDelay(dict["start delay ms"])
            self.tips[name][0].SetTitleFont(font_title)
            self.tips[name][0].SetMessageFont(font_text)
            self.tips[name][0].SetTarget(self.tips[name][1])

    def add_sizer(self):
        # Add a vertical sizer
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

    def sampling(self):
        # Text box for sampling interval
        ratetext = wx.StaticText(self.panel, -1, "Sample rate", style=wx.ALIGN_CENTER)
        self.rate = wx.TextCtrl(self.panel, -1, 
            settings["default sample rate"], size=(50, 20))
        # Choice box for units
        units = wx.StaticText(self.panel, -1, "units", style=wx.ALIGN_CENTER)
        self.unit_choices = ["seconds", "minutes", "hours"]
        self.units = wx.ListBox(self.panel, -1, (20, 20), (80, 50), 
            self.unit_choices, wx.LB_SINGLE)
        self.units.SetSelection(0)
        choice_sizer = wx.BoxSizer(wx.HORIZONTAL)
        choice_sizer.Add(ratetext, 0, wx.EXPAND)
        choice_sizer.Add((5, 1))
        choice_sizer.Add(self.rate, 0, wx.FIXED_MINSIZE)
        choice_sizer.Add((10, 1))
        choice_sizer.Add(units, 0, wx.EXPAND)
        choice_sizer.Add((5, 1))
        choice_sizer.Add(self.units,   0, wx.FIXED_MINSIZE)
        choice_sizer.Add((5, 1))
        self.set = wx.Button(self.panel, -1, "Set")
        choice_sizer.Add(self.set, 0, wx.ALIGN_TOP)
        self.Bind(wx.EVT_BUTTON, self.OnSet, self.set)
        self.sizer.Add(choice_sizer, 0, wx.ALIGN_CENTER)

    def time_stamp(self):
        # Static text control for the time stamp
        self.timestamp = wx.StaticText(self.panel, -1, "", 
            size = (settings["frame size horiz"],
                    settings["time font size"]*font_factor),
            style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE)
        self.timestamp.SetBackgroundColour(settings["time bg color"])
        self.timestamp.SetForegroundColour(settings["time fg color"])
        self.timestamp.SetFont(wx.Font(settings["time font size"],
            wx.DEFAULT, wx.NORMAL, wx.BOLD))
        self.sizer.Add(self.timestamp, 0, wx.EXPAND)

    def reading(self):
        # Static text control for the reading
        self.reading = wx.StaticText(self.panel, -1, "0.0 V", 
            size = (settings["frame size horiz"],
                    settings["reading font size"]*font_factor),
            style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE)
        self.reading.SetBackgroundColour(settings["reading bg color"])
        self.reading.SetForegroundColour(settings["reading fg color"])
        self.reading.SetFont(wx.Font(settings["reading font size"],
            wx.DEFAULT, wx.NORMAL, wx.BOLD))
        self.sizer.Add(self.reading, 0, wx.EXPAND)
        self.sizer.Add((1, 5))

    def tips_button(self):
        self.tips_button = wx.ToggleButton(self.panel, -1, "Tips",
            style=wx.BU_EXACTFIT)
        self.tips_button.SetValue(False)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.OnTips, self.tips_button)
        self.sizer.Add(self.tips_button, 0, wx.FIXED_MINSIZE|wx.ALIGN_LEFT)

    def start_button(self):
        # Start/stop button
        self.start = wx.ToggleButton(self.panel, -1, "Start")
        self.Bind(wx.EVT_TOGGLEBUTTON, self.OnStart, self.start)
        self.sizer.Add(self.start, 0, wx.FIXED_MINSIZE|wx.ALIGN_CENTER_HORIZONTAL)
        # Spacing between button and data entry
        self.sizer.Add((10, 20))

    def events(self):
        # Hook up needed events
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def time_stuff(self):
        # We'll have a timer update the status bar with the current time
        self.sbtimer = Timer(1, self.UpdateStatusBar)
        self.sbtimer.start()
        self.last_time = time()

    def UpdateStatusBar(self):
        self.status_bar.SetStatusText(self.CurrentTime())
        # Reset the timer
        self.sbtimer = Timer(1, self.UpdateStatusBar)
        self.sbtimer.start()
        
    def CurrentTime(self):
        return strftime("%d%b%Y-%H:%M:%S")

    def GetReading(self):
        if not self.interval:
            self.OnSet(None)
        if self.running:
            if not self.meter:
                self.meter = RS22812()
            reading_tuple = self.meter.GetReading()
            reading_string = self.CurrentTime() + " [%d] " % self.count + \
                str(reading_tuple)
            self.count += 1
            self.log.write("    " + reading_string + "\n")
            D("Reading = " + reading_string)
            # Update display
            self.timestamp.SetLabel(self.CurrentTime())
            reading, mode, modifiers = reading_tuple
            s = reading + " " + ''.join(modifiers)
            self.reading.SetLabel(s)
            # Set up timer to take another reading
            self.reading_timer = Timer(self.interval, self.GetReading)
            self.reading_timer.start()
            D("Timer set to take another reading in %g s" % self.interval)

    def OnStart(self, event):
        if self.start.GetValue():
            # Was a start command
            D("Start button pressed")
            self.start.SetLabel("Stop")
            self.log.write("  Start button pressed %s\n" % self.CurrentTime())
            self.count = 1
            self.running = True
            self.GetReading()
        else:
            # Was a stop command
            self.reading_timer.cancel()
            self.running = False
            if self.meter:
                del self.meter  # Forces serial port to close
            self.meter = None
            D("Stop button pressed")
            self.log.write("  Stop button pressed %s\n" % self.CurrentTime())
            self.start.SetLabel("Start")

    def OnTips(self, event):
        if self.tips_button.GetValue():
            self.tips["Start"][0].EnableTip(True)
        else:
            self.tips["Start"][0].EnableTip(False)

    def OnSet(self, event):
        # Set our sampling interval
        try:
            self.interval = float(self.rate.GetValue())
            if self.interval <= 0:
                raise Exception()
        except:
            wx.MessageBox("'%s' is an improper sample rate" %
                self.rate.GetLabel())
            return
        # Get units
        units = self.unit_choices[self.units.GetSelection()]
        if units == "minutes": self.interval *= 60
        elif units == "hours": self.interval *= 3600
        s = "Set button pressed = %g s" % self.interval
        if event:
            D(s)
        else:
            D("Simulating " + s)
        self.log.write("  New sampling interval %g s %s\n" % (
            self.interval, self.CurrentTime()))

    def OnClose(self, event):
        D("Program shutting down")
        try: self.sbtimer.cancel()
        except: pass
        try: self.reading_timer.cancel()
        except: pass
        self.log.write("  Program ended %s\n" % self.CurrentTime())
        self.Destroy()

if __name__ == "__main__":
    app = wx.PySimpleApp()
    frame = MyFrame(parent=None, id=-1)
    frame.Show()
    app.MainLoop()


