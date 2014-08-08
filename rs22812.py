
# TODO handle ctrl-c in main
# TODO rename bytes variable to something else, bytes is a builtin type in python 3
# TODO string in digits: 
#   if number_str == "0.0F": number_str = ".0F"  # Diode open case
# TODO when changing ranges, meter can send digits "----" which causes parse error

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

    MODE_DC_V           =  0=
    MODE_AC_V           =  1=
    MODE_DC_uA          =  2= (caused by dial set to uA/A)
    MODE_DC_mA          =  3= (caused by dial set to mA/A)
    MODE_DC_A           =  4
    MODE_AC_uA          =  5= (caused by dial set to uA/A, then press Select)
    MODE_AC_mA          =  6= (caused by dial set to um/A, then press Select)
    MODE_AC_A           =  7
    MODE_OHM            =  8=
    MODE_CAP            =  9=
    MODE_HZ             = 10= this is dial setting, check indicators to get scale
    MODE_NET_HZ         = 11= (caused by dial set to V, press Hz/Duty/Width)
    MODE_AMP_HZ         = 12= (caused by dial set to A, press Hz/Duty/Width)
    MODE_DUTY           = 13= (caused by dial set to Hz, press Hz/Duty/Width)
    MODE_NET_DUTY       = 14= (caused by dial set to V, press Hz/Duty/Width)
    MODE_AMP_DUTY       = 15= (caused by dial set to A, press Hz/Duty/Width)
    MODE_WIDTH          = 16= (caused by dial set to Hz, press Hz/Duty/Width)
    MODE_NET_WIDTH      = 17= (caused by dial set to V, press Hz/Duty/Width)
    MODE_AMP_WIDTH      = 18= (caused by dial set to A, press Hz/Duty/Width)
    MODE_DIODE          = 19=
    MODE_CONTINUITY     = 20=
    MODE_HFE            = 21=
    MODE_LOGIC          = 22=
    MODE_DBM            = 23=
    MODE_EF             = 24
    MODE_TEMPERATURE    = 25=

Notes:
- Dial on uA/A, pressing range changes between uA, mA.  Need to check indicators to 
  see if we need to switch modes also
- How to get to MODE_DC_A, MODE_AC_A? maybe need actual power to measure
- How to get MODE_EF?



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

    #####################################################################
    # Constants, for code readiblity and use by external users of class
    #####################################################################
    
    # Constants for dial setting (function rotary switch on meter)
    DIAL_DC_V           =  0   
    DIAL_AC_V           =  1 
    DIAL_DC_uA          =  2 
    DIAL_DC_mA          =  3 
    DIAL_DC_A           =  4 
    DIAL_AC_uA          =  5 
    DIAL_AC_mA          =  6 
    DIAL_AC_A           =  7 
    DIAL_OHM            =  8 
    DIAL_CAP            =  9 
    DIAL_HZ             = 10
    DIAL_NET_HZ         = 11
    DIAL_AMP_HZ         = 12
    DIAL_DUTY           = 13
    DIAL_NET_DUTY       = 14
    DIAL_AMP_DUTY       = 15
    DIAL_WIDTH          = 16
    DIAL_NET_WIDTH      = 17
    DIAL_AMP_WIDTH      = 18
    DIAL_DIODE          = 19
    DIAL_CONTINUITY     = 20
    DIAL_HFE            = 21
    DIAL_LOGIC          = 22
    DIAL_DBM            = 23
    DIAL_EF             = 24
    DIAL_TEMPERATURE    = 25

    UNITS_HERTZ              = "Hz"
    UNITS_OHMS               = "Ohm"
    UNITS_FARADS             = "F"
    UNITS_AMPS               = "A"
    UNITS_VOLTS              = "V"
    UNITS_GAIN               = "hFE"
    UNITS_PERCENT            = "%"
    UNITS_SECONDS            = "S"
    UNITS_DECIBEL_MILLIWATTS = "dBm"
 
    UNITS_SCALE_NANO        = "n"
    UNITS_SCALE_MICRO       = "u"
    UNITS_SCALE_MILLI       = "m"
    UNITS_SCALE_KILO        = "k"
    UNITS_SCALE_MEGA        = "M"
    UNITS_SCALE_CELCIUS     = "C"
    UNITS_SCALE_FAHRENHEIT  = "F"



    # Lookup table for meter dial labels.  TODO: L10N
    dial_label = ("DC V", "AC V", "DC uA", "DC mA", "DC A", "AC uA", 
                  "AC mA", "AC A", "ohm", "CAP", "Hz", "NET Hz", "AMP Hz",
                  "Duty", "Net Duty", "Amp Duty", "Width", "Net Width", "Amp"
                  "Width", "Diode", "Cont", "hFE", "Logic", "dBm", "EF", "Temp")


    #####################################################################
    # Readings from meter lcd screen, function dial, & buttons
    #####################################################################
    
    dial             = None  # state of function rotary dial

    # LCD Reading
    digits_raw       = None  # for debugging purposes, keep digits list
    digits           = None  # contents of four 7-segment digits on LCD
    significant_decimals = 0 # number of significant decimal places
    decimal_location = None  # number of decimal places in LCD digits
    sign             = None  # sign of reading: -1 = negative, 1 = positive
     
    # LCD Indicators (extra symbols on display set by button presses, etc)

    # indicators along top of LCD screen
    indicator_battery       = None  # True = weak battery indicator is on, False = off
    indicator_autorange     = None  # True = auto-ranging, False = manual ranging
    indicator_rs232         = None  # True = RS232 mode on, False = RS232 mode off
    indicator_relative      = None  # True = relative measurement mode on, False = off    
    indicator_continuity    = None  # True = in continuity check mode, False = off
    indicator_diode         = None  # True = in diode check mode, False = off

    # indicators vertically along left side of LCD screen
    indicator_hold          = None  # True = hold indicator on, False = hold indicator off
    indicator_ac            = None  # True = reading is from AC, False = reading is from DC
    indicator_max           = None  # True = max indicator is on, False = off
    indicator_min           = None  # True = min indicator is on, False = off

    # indicators vertically along right side of LCD screen
    # The following indicators are used to set the units:
    #    %, S, V, A, F, Hz, ohm, dbm, hfe
    # The following indicators are used to set the units prefix:
    #    n, m, u, K, M 
    # units (from indicators)
    units_scale = None  
    units       = None

    #####################################################################
    # Interpreted state of meter
    #####################################################################

    # Logic probe
    # indicates "Lo" if voltage is less than 1.0V
    # indicates "Hi" if voltage is greater than 2.0V
    # gives measured volts if 1.0V <= reading <= 2.0V
    # note: manual says not to exceed 5v on input
    logic_probe_high  = None  # False if Low, True if High, None if between Low and High
    logic_probe_volts = None  # Float containing measured volts, None if is Low or High

    # Continuity
    continuity = None  # True = closed circuit, False = open circuit


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
        sleep_time = 1  # seconds
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
            if not self.valid_checksum(packet):
                self.sp.setDTR(level=False)
                sleep(sleep_time)
                continue
            good_packet = True
            self.sp.setDTR(level=False)
            sleep(sleep_time)
            self.sp.flushInput()
        return packet

    def valid_checksum(self, packet):
        # I have no idea why the article adds constant 57 to the  
        # checksum, but it seems to work.
        constant = 57
        checksum_calculated = (sum([ord(c) for c in packet[:-1]]) + constant) & 255
        checksum_received   = ord(packet[8])
        if checksum_calculated != checksum_received:
            print "ERROR, checksum failed. Expected %d, got %d" % (checksum_calculated, checksum_received)
            return False
        else:
            return True

    def interpret_digit(self, byte):
        '''This routine interprets the coded seven segment display digit.
        '''
        code = { 215 : "0",  80 : "1", 181 : "2", 241 : "3", 
                 114 : "4", 227 : "5", 231 : "6",  81 : "7", 
                 247 : "8", 243 : "9",  39 : "F",  55 : "P", 
                 167 : "E", 135 : "C", 134 : "L", 118 : "H", 
                   6 : "I", 102 : "h",  36 : "r", 166 : "t", 
                 100 : "n",  32 : "-",   0 : " "}
        if byte in code:
            return code[byte]
        else:
            return "?"

    def digits_to_number(self, digits, decimal_location, sign):
        '''
        Convert a list of char digits to a floating point number
        - Assumes that digits list is exactly 4 char in size
        - Decimal_location indicates location of decimal 
          point from the left side.
        - Sign is -1 (for a negative number) or +1 (for positive)
        '''
        #print "+++", digits, decimal_location, sign
        if decimal_location: 
            digits.insert(decimal_location, ".")
        digits_str = ''.join(digits)
        #print "+++", digits_str
        try:
            digits = float(digits_str)
        except ValueError:
            print "ERROR converting digits to float.", \
                  "digits:", digits, \
                  ", decimal_location:", decimal_location
            digits = 0.0
        digits = digits * sign
        #print "+++ returning", digits 
        return digits

    def parse_response(self, response_str):
        '''
        Pull status of indicators on LCD
        Indicators are  additional annunciators, such as "MAX", 
        "MIN", "ohm", "Hold", etc.
        '''

        '''
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
        '''

        if response_str == None:
            print "ERROR: response string was empty"
            return

        response = [ord(i) for i in response_str]

        #####################
        ### response byte 0 
        #####################

        # function rotary dial setting 
        self.dial = response[0]

        #####################
        ### response byte 1 
        #####################
        
        # response byte 1, bits 1,2,3,6,7 are part of units
        # response byte 1, bits 0,4,5 are part of units scale

        #####################
        ### response byte 2
        #####################

        if response[2] & (1 << 0):
            self.indicator_min = True
        else:
            self.indicator_min = False

        if response[2] & (1 << 1):
            self.indicator_relative = True
        else:
            self.indicator_relative = False

        # response byte 2, bits 2-5 are part of units
        # response byte 2, bits 6-7 are part of units scale

        #####################
        ### response byte 3
        #####################

        # response byte 3, bits 0-2, 4-7 are part of LCD digit display
        # response byte 3, bit 3 is part of decimal location

        #####################
        ### response byte 4 
        #####################

        # response byte 4, bits 0-2, 4-7 are part of LCD digit display
        # response byte 4, bit 3 is part of decimal location

        #####################
        ### response byte 5 
        #####################

        # response byte 4, bits 0-2, 4-7 are part of LCD digit display
        # response byte 5, bit 3 is part of decimal location

        #####################
        ### response byte 6
        #####################

        if response[6] & (1 << 3):
            self.indicator_max = True
        else:
            self.indicator_max = False

        #####################
        ### response byte 7
        #####################

        if response[7] & (1 << 0):
            self.indicator_autorange = True
        else:
            self.indicator_autorange = False

        if response[7] & (1 << 1):
            self.indicator_rs232 = True
        else:
            self.indicator_rs232 = False

        if response[7] & (1 << 2):
            self.indicator_ac = True
        else: 
            self.indicator_ac = False

        if response[7] & (1 << 3):  
            self.sign = -1
        else:
            self.sign = 1

        if response[7] & (1 << 4):
            self.indicator_hold = True
        else:
            self.indicator_hold = False

        if response[7] & (1 << 5):
            self.indicator_battery = True
        else:
            self.indicator_battery = False

        if response[7] & (1 << 6):
            self.indicator_diode = True
        else:
            self.indicator_diode = False

        if response[7] & (1 << 7):
            self.indicator_continuity = True
        else:
            self.indicator_continuity = False


        #####################
        ### response byte 8
        #####################

        # checksum is validated while reading from device

        #######################
        ### LCD Digit Display 
        #######################
        digits = [0, 0, 0, 0]
        n = 4
        for di, by in zip((3, 4, 5, 6), (3, 2, 1, 0)):
            # Mask out the decimal point
            byte = response[di] & (~8)
            digits[by] = self.interpret_digit(byte)
        self.digits_raw = list(digits)

        ######################
        ### Decimal Location
        ######################
        # Get decimal point.  If dp = 1, 2, or 3, this locates the decimal
        # point after the first, second, or third digit, respectively.  If
        # dp = 0, there is no decimal point.
        dp = 0
        if response[3] & (1 << 3):
            dp = 3
        elif response[4] & (1 << 3):
            dp = 2
        elif response[5] & (1 << 3):
            dp = 1
        decimal_location = dp
        self.decimal_location = dp

        ### Decimal places: since digits is always 4 chars, we
        ### can figure out how many decimal places are significant
        if decimal_location == 0:
            self.significant_decimals = 0
        else:
            self.significant_decimals = 4 - decimal_location

        #####################
        ### Units
        #####################
        units = ""
        if   response[1] & (1 << 1):  units = self.UNITS_VOLTS
        elif response[1] & (1 << 2):  units = self.UNITS_AMPS 
        elif response[1] & (1 << 3):  units = self.UNITS_FARADS
        elif response[1] & (1 << 6):  units = self.UNITS_OHMS
        elif response[1] & (1 << 7):  units = self.UNITS_HERTZ
        elif response[2] & (1 << 2):  units = self.UNITS_GAIN
        elif response[2] & (1 << 3):  units = self.UNITS_PERCENT
        elif response[2] & (1 << 4):  units = self.UNITS_SECONDS
        elif response[2] & (1 << 5):  units = self.UNITS_DECIBEL_MILLIWATTS
        self.units = units
    
        #####################
        ### Units Scale 
        #####################
        scale = ""
        if   response[1] & (1 << 0): scale = self.UNITS_SCALE_MILLI
        elif response[1] & (1 << 4): scale = self.UNITS_SCALE_MEGA
        elif response[1] & (1 << 5): scale = self.UNITS_SCALE_KILO 
        elif response[2] & (1 << 6): scale = self.UNITS_SCALE_NANO
        elif response[2] & (1 << 7): scale = self.UNITS_SCALE_MICRO
        self.units_scale = scale

        ######################################
        ### Interpret what LCD reading means
        ######################################
        
        digits_str = ''.join(digits)

        self.input_overrange = False 

        if digits_str == " 0F ":
            # " 0F " = input value too high
            self.input_overrange = True
            self.digits = 0.0 
        elif self.dial == self.DIAL_LOGIC:
            self.logic_probe_high  = None
            if digits_str == " L0 ":
                self.logic_probe_high  = False
            elif digits_str == " HI ":
                self.logic_probe_high  = True 
            else:
                # value is between low and high, get voltage
                self.digits = self.digits_to_number(digits, decimal_location, self.sign)
        elif self.dial == self.DIAL_CONTINUITY:
            self.continuity = None  # True = closed circuit, False = open circuit
            if digits_str == "0Pen":
                # "0Pen" = continuity open
                self.continuity = False
            elif digits_str == "5hrt":
                # "5hrt" = continuity shorted (closed)
                self.continuity  = True 
        elif self.dial == self.DIAL_TEMPERATURE:
            # temp has sign, and digits in format of "NN.N{C|F}"
            if digits[3] == "C":
                self.units_scale = self.UNITS_SCALE_CELCIUS
            elif digits[3] == "F":
                self.units_scale = self.UNITS_SCALE_FAHRENHEIT
            else:
                print "ERROR: temperature digits does not end in C or F.", \
                      "digits:", digits
            self.digits = self.digits_to_number(digits[:3] + ['0'], decimal_location, self.sign)
        else:
            # in all other cases, digits contains a number
            self.digits = self.digits_to_number(digits, decimal_location, self.sign)
            


    def DumpPacket(self, packet):
        s = ""
        for i in xrange(len(packet)):
            s += "%3d " % ord(packet[i]) 
        return s

    #def GetReading(self):
    #    # Return a string representing a reading.  If we could not get a 
    #    # reading, return None.
    #    packet = self.get_packet()
    #    if 0:  # Turn on to see individual bytes
    #        print self.DumpPacket(packet)
    #    reading, dial, modifiers = self.InterpretReading(packet)
    #    if 1:
    #        print "Reading: %s, Dial: %s, Modifiers: %s" % (reading, dial, modifiers)
    #    return self.InterpretReading(packet)


    def interpret_reading(self):
        extra = ''
        if self.indicator_ac:
            extra = extra + "AC"
        else:
            extra = extra + "DC"

        if self.indicator_relative:
            extra = extra + " Relative"

        if self.indicator_hold:
            extra = extra + ", Hold"
    
        if self.input_overrange:
            digits_str = "OverRange"
        elif self.logic_probe_high == True:
            digits_str = "HIGH"
        elif self.logic_probe_high == False:
            digits_str = "LOW"
        else:
            # all other cases, including self.logic_probe_high == None
            format_str = "%%.%df" % self.significant_decimals
            digits_str = format_str % self.digits

        reading = "%s %s%s %s" % (digits_str, self.units_scale, self.units, extra)
        return reading
 
    def debug(self):
        print "*******************************************************"
        print "*** Display Readings ***"
        print "************************"
        now_str = strftime("%Y-%m-%d %H:%M:%S") 
        print now_str
        print "function dial    : %s (%d)" % (self.dial_label[self.dial], self.dial) 
        print "digits           :", self.digits_raw
        print "decimal location :", self.decimal_location
        print "decimal signfict :",  self.significant_decimals
        print "units            :", self.units_scale + self.units
        print "INDICATORS"
        print "  AC                :", self.indicator_ac
        print "  Autorange         :", self.indicator_autorange  
        print "  Hold              :", self.indicator_hold       
        print "  RS232             :", self.indicator_rs232      
        print "  Relative          :", self.indicator_relative        
        print "  Continuity Mode   :", self.indicator_continuity 
        print "  Diode Mode        :", self.indicator_diode      
        print "  Min Reading       :", self.indicator_min        
        print "  Max Reading       :", self.indicator_max        
        print "  Low Battery       :", self.indicator_battery    
        print "*******************************************************"



###
### MAIN
###

def main(port, interval):
    # Immediately start taking readings and printing to stdout.

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
        packet = rs.get_packet()
        now_str = strftime("%Y-%m-%d %H:%M:%S") 
        #r = rs.GetReading()
        #print now_str + " [%d]" % count, r
        rs.parse_response(packet)
        rs.debug()
        reading = rs.interpret_reading()
        print now_str, reading
        sleep(interval)

if __name__ == "__main__":

    from time import strftime, sleep
    from optparse import OptionParser

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

    main(port, interval)
