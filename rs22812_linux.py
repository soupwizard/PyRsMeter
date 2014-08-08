'''
A python interface for the Radio Shack 22-812 digital multimeter.  You will
also need to download and install the PySerial module (see
http://pyserial.sourceforge.net/).  This Radio Shack multimeter has a
serial port that lets you get the readings the instrument makes.

Modern computers usually do not come with a serial port anymore.  You
can buy a USB to serial adapter for $15 or so that will give you a serial
port.  Sabrent is one brand name, but there are many others.  The device
plugs into a USB port and terminates in a 9 pin RS-232 connector (mine is
a male connector).  For Windows, you install a driver by running an
executable and you should then have a working serial port at COM3.  No
computer reboot is necessary.

This routine was written based on the information in the article
http://www.kronosrobotics.com/Projects/CYW_RSMeter.pdf (update 22 Jun
2014:  this website is defunct).  Note the numbering of bits in Table
1 in the article is opposite of the typical convention: bit 7 is
actually what most folks would call bit 0.  Here is the table with the
bit numbering as I would prefer:

                               Bit
Byte    7       6       5       4       3       2       1       0
0       ---------------------- Mode -----------------------------
1       Hz      Ohms    K       M       F       A       V       m
2       u       n       dBm     s       %       hFE     REL     MIN
3       4D      4C      4G      4B      DP3     4E      4F      4A
4       3D      3C      3G      3B      DP2     3E      3F      3A
5       2D      2C      2G      2B      DP1     2E      2F      2A
6       1D      1C      1G      1B      MAX     1E      1F      1A
7       Beep    Diode   Bat     Hold    -       ~       RS232   Auto
8       -------------------- Checksum ---------------------------

The segment lettering is

    |--A--|
    |     |
    F     B
    |     |
    |--G--|
    |     |
    E     C
    |     |
    |--D--|

The mode is given by the following table:

    0    DC V
    1    AC V
    2    DC uA
    3    DC mA
    4    DC A
    5    AC uA
    6    AC mA
    7    AC A
    8    OHM
    9    CAP
    10   HZ
    11   NET HZ
    12   AMP HZ
    13   DUTY
    14   NET DUTY
    15   AMP DUTY
    16   WIDTH
    17   NET WIDTH
    18   AMP WIDTH
    19   DIODE
    20   CONT
    21   HFE
    22   LOGIC
    23   DBM
    24   EF
    25   TEMP

Note:  I don't know what "NET HZ" etc. mean, as I didn't see these come
up during my testing.  Perhaps they are available with later instruments; I
bought mine 7-8 years ago.

The interface works at 4800 baud, 8 bits, no parity and 1 stop bit.  Once
you have made the connection, your program needs to raise DTR (data terminal
ready) and the meter will start sending data.  Note you have to press the
SELECT and RANGE buttons on the meter simultaneously to enable the RS-232
interface.

The meter uses a 9 V battery and the manual states that the battery will
last for about 100 hours.  It is probably less than this when the serial
interface is being used.

But for $70, this lets an experimenter log measurement data unattended.

The meter has a 9 pin female D connector for the serial port connection.

----------------------------------------------------------------------
Copyright (C) 2009, 2014 Don Peterson
Contact:  gmail.com@someonesdad1
  
                  The Wide Open License (WOL)
  
Permission to use, copy, modify, distribute and sell this software and
its documentation for any purpose is hereby granted without fee,
provided that the above copyright notice and this license appear in
all copies.  THIS SOFTWARE IS PROVIDED "AS IS" WITHOUT EXPRESS OR
IMPLIED WARRANTY OF ANY KIND. See
http://www.dspguru.com/wide-open-license for more information.
'''

import serial
from time import sleep

ignore_RS232_modifier = True

class RS22812(object):
    '''Provides an interface object to the Radio Shack 22-812 digital
    multimeter.  You must provide the constructor with the port number
    or device.
    '''
    def __init__(self, port):
        self.port = port
        baudrate = 4800
        self.sp = serial.Serial(port, baudrate, timeout=0)

    def __del__(self):
        if self.sp:
            self.sp.close()

    def get_packet(self):
        '''This routine follows the logic of the algorithm given on page 2
        of the article
        http://www.kronosrobotics.com/Projects/CYW_RSMeter.pdf.  The
        procedure is:
            Purge the port
            Wait 100 ms
            Set DTR true
            Get 9 bytes
            Set DTR false
            Wait 100 ms
            Purge the port
        However, we continue to loop until we do get a good packet.
        '''
        sleep_time = 0.3  # seconds
        good_packet = False
        while not good_packet:
            self.sp.flushInput()
            sleep(sleep_time)
            self.sp.setDTR(level=True)
            packet = self.sp.read(9)
            if len(packet) != 9:
                self.sp.setDTR(level=False)
                sleep(sleep_time)
                continue
            # I have no idea why the article adds this number in for the
            # checksum, but it seems to work.
            constant = 57
            checksum = (sum([ord(c) for c in packet[:-1]]) + constant) & 255
            if checksum != ord(packet[8]):
                self.sp.setDTR(level=False)
                sleep(sleep_time)
                continue
            good_packet = True
            self.sp.setDTR(level=False)
            sleep(sleep_time)
            self.sp.flushInput()
        return packet

    def interpret_digit(self, byte):
        '''This routine interprets the coded seven segment display digit.
        '''
        code = { 215 : "0", 80 : "1", 181 : "2", 241 : "3", 114 : "4", 
            227 : "5", 231 : "6", 81 : "7", 247 : "8", 243 : "9", 39 : "F", 
            55 : "P", 167 : "E", 135 : "C", 134 : "L", 118 : "H", 6 : "I",
            102 : "h", 36 : "r", 166 : "t", 100 : "n", 32 : "-", 0 : " "}
        if byte in code:
            return code[byte]
        else:
            return "?"

    def GetModifiers(self, bytes):
        '''Various modes show additional annunciators, such as "MAX", 
        "MIN", etc.  Return those set as a tuple of strings.  We ignore
        the RS-232 annunciator unless you really want it.
        '''
        s = []
        if bytes[2] & (1 << 1):  s += ["REL"]
        if bytes[2] & (1 << 0):  s += ["MIN"]
        if bytes[6] & (1 << 3):  s += ["MAX"]
        if bytes[7] & (1 << 7):  s += ["Beep"]
        if bytes[7] & (1 << 6):  s += ["Diode"]
        if bytes[7] & (1 << 5):  s += ["Bat"]
        if bytes[7] & (1 << 4):  s += ["Hold"]
        if not ignore_RS232_modifier:
            if bytes[7] & (1 << 1):  s += ["RS232"]
        if bytes[7] & (1 << 0):  s += ["Auto"]
        return tuple(s)

    def GetUnits(self, bytes):
        '''Return a string representing the units of the measurement.
        '''
        prefix = ""
        if   bytes[1] & (1 << 5):  prefix = "k"
        elif bytes[1] & (1 << 4):  prefix = "M"
        elif bytes[1] & (1 << 0):  prefix = "m"
        elif bytes[2] & (1 << 7):  prefix = "u"
        elif bytes[2] & (1 << 6):  prefix = "n"
        unit = ""
        if   bytes[1] & (1 << 7):  unit = "Hz"
        elif bytes[1] & (1 << 6):  unit = "ohm"
        elif bytes[1] & (1 << 3):  unit = "F"
        elif bytes[1] & (1 << 2):  unit = "A"
        elif bytes[1] & (1 << 1):  unit = "V"
        elif bytes[2] & (1 << 5):  unit = "dBm"
        elif bytes[2] & (1 << 4):  unit = "s"
        elif bytes[2] & (1 << 3):  unit = "%"
        elif bytes[2] & (1 << 2):  unit = "hFE"
        # Append "~" to V, A, or dBm if it is an AC measurement
        if unit in ("V", "A", "dBm"):
            if bytes[7] & (1 << 2):  unit += "~"
        if unit:
            return prefix + unit
        return ""

    def InterpretReading(self, string):
        '''We return a tuple of strings:  
            (
                Numerical reading with units
                Mode
                Modifiers
            )
        '''
        if string == None:
            return None
        bytes = [ord(i) for i in string]
        # Byte 0:  mode
        modes = ("DC V", "AC V", "DC uA", "DC mA", "DC A", "AC uA", 
            "AC mA", "AC A", "ohm", "CAP", "Hz", "NET Hz", "AMP Hz",
            "Duty", "Net Duty", "Amp Duty", "Width", "Net Width", "Amp"
            "Width", "Diode", "Cont", "hFE", "Logic", "dBm", "EF", "Temp")
        mode = modes[bytes[0]]
        digits = [0, 0, 0, 0]
        n = 4
        for di, by in zip((3, 4, 5, 6), (3, 2, 1, 0)):
            # Mask out the decimal point
            byte = bytes[di] & (~8)
            digits[by] = self.interpret_digit(byte)
        # Get decimal point.  If dp = 1, 2, or 3, this locates the decimal
        # point after the first, second, or third digit, respectively.  If
        # dp = 0, there is no decimal point.
        dp = 0
        if bytes[3] & (1 << 3):
            dp = 3
        elif bytes[4] & (1 << 3):
            dp = 2
        elif bytes[5] & (1 << 3):
            dp = 1
        # Get sign
        sign = ""
        if bytes[7] & (1 << 3):  sign = "-"
        # Get units
        units = self.GetUnits(bytes)
        # Construct number
        if dp: digits.insert(dp, ".")
        number = (''.join(digits)).strip() 
        # Strip leading zeros
        while number and number[0] == "0":
            number = number[1:]
        if not number:
            number = "0"
        if number[0] == "." or number[0] == "F" or number[0] == "P":
            number = "0" + number
        if number == "0.0F": number = ".0F"  # Diode open case
        # Make the reading
        reading = sign + number + " " + units
        return reading, mode, self.GetModifiers(bytes)

    def DumpPacket(self, packet):
        s = ""
        for i in xrange(len(packet)):
            s += "%3d " % ord(packet[i]) 
        return s

    def GetReading(self):
        # Return a string representing a reading.  If we could not get a 
        # reading, return None.
        packet = self.get_packet()
        if 0:  # Turn on to see individual bytes
            print self.DumpPacket(packet)
        return self.InterpretReading(packet)

if __name__ == "__main__":
    # Immediately start taking readings and printing to stdout.  There
    # are two optional parameters on the command line.  Use the -h or --help
    # flags for more information.
    from time import strftime, sleep
    from optparse import OptionParser
    def TimeNow():
        return strftime("%d%b%Y-%H:%M:%S")

    #process command-line arguments
    parser = OptionParser(
        usage = "%prog [options]",
        description = "rs22812 - A python interface for the " +
                      "Radio Shack 22-812 digital multimeter."
    )
    parser.add_option("-p", "--port",
        dest = "port",
        help = "port device string: examples:  " +
               "Unix-like: /dev/ttyS0, " +
               "Windows: COM1 [defaults to one of these values]"
    )
    parser.add_option("-i", "--interval",
        dest = "interval",
        type = "int",
        default = 1,
        help = "interval in seconds between readings [default: %default]"
    )
    (options, args) = parser.parse_args()
    port = options.port
    interval = options.interval
    if (port == None):
        # attempt to supply something intelligent for os for a default
        import os
        if os.name == 'nt':
            port = 'COM1'
        else:
            port = '/dev/ttyS0'
        print "rs22812 main:  no port option specified:  port set to", port
        
    rs = RS22812(port)

    count = 0
    while True:
        count += 1
        r = rs.GetReading()
        print TimeNow() + " [%d]" % count, r
        sleep(interval)
