#===============================================================================
# wipy_hd44780.py: Wipy class for interfacing with HD44780-compatible LCD
#                  controllers.
#
# Author: Andrew T. Canaday
#
# License: The MIT License (Term follow)
#
# MIT License
#
# Copyright (c) 2016 Andrew Canaday
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
#===============================================================================
import time
from machine import Pin

__version__ = 'v0.0.1'

class HD44780(object):
    """
    Simple bit-banging controller class for HD44780-based LCD displays for the
    wipy microcontroller.
    """

    # HD44780 pin labels:
    LCD_DATA_PINS = (
            'D7',
            'D6',
            'D5',
            'D4',
            'D3',
            'D2',
            'D1',
            'D0',
            )

    # Total DDRAM
    DDRAM_TOTAL  = 80

    # Line addresses:
    DDRAM0_START = 0x00
    DDRAM0_END   = 0x27
    DDRAM1_START = 0x40
    DDRAM1_END   = 0x67

    # Message type constants:
    MSG_TYPE_CMD  = 0
    MSG_TYPE_DATA = 1

    # Interface operation mode constants:
    MODE_UNKNOWN  = 0
    MODE_8BIT     = 8
    MODE_4BIT     = 4

    # Font codes
    FONT_5x8  = 0
    FONT_5x10 = 1

    def __init__(
            self,
            host_pins = None,
            clk='GP0',
            rs='GP4',
            rw=None,
            width=16,
            height=2,
            font=FONT_5x8,
            ):
        """
        Initialize the HD44780 driver.

        Params:
         - host_pins:   a list of pin NAMES used to send data to the HD44780
         - clk:         The NAME of the to use for the clock/enable bit/pin
         - rs:          The NAME of the pin to use to set the message type bit/pin
         - rw:          The NAME of the pin to use to set the RW bit/pin
                        (NOTE: RW functionality not yet implemented!)
         - width:  The width of the display, in characters
         - height: The height of the display, in characters
         - font:        Display font

        Defaults:
         - ['GP8', 'GP30', 'GP31', 'GP3']
         - 'GP0'
         - 'GP4'
         - None
         - 16
         - 2
         - FONT_5x8

        NOTES:
           Addressing is based off the information found here: http://web.alfredstate.edu/weimandn/lcd/lcd_addressing/lcd_addressing_index.html.
           For "Type 1" 16x1 screens, set width=8, height=2
        """

        if host_pins is None:
            # Default to 4-bit mode:
            host_pins = (
            'GP8',  # HD44780 d7
            'GP30', # HD44780 d6
            'GP31', # HD44780 d5
            'GP3',  # HD44780 d4
            )

        # Initialize pins:
        self._rs_pin = Pin(rs, Pin.OUT)
        self._clk_pin = Pin(clk, Pin.OUT)
        self._data_pins = [Pin(x, Pin.OUT) for x in host_pins]

        # Accounting:
        self._ch_idx = 0
        self._width = width
        self._height = height
        self._line_addr = self._init_line_addrs(width,height)
        self._no_pins = len(self._data_pins)
        self._mode = self.MODE_UNKNOWN
        self._last_cmd_complete = 0

        # RW pin is optional:
        if rw is not None:
            self._rw_pin = Pin(rw, Pin.OUT)
        else:
            self._rw_pin = None

        # Rest to 8-bit mode (starting point for all HD44780 configurations):
        self.set_8bit_mode()

        # Set mode based on number of pins:
        if self._no_pins == 8:
            self.set_8bit_mode()
        elif self._no_pins == 4:
            self.set_4bit_mode()
        else:
            raise Exception("Number of pins must be 4 or 8!")

        # Return cursor to home:
        self.clear()

        # Indicate to the hardware whether we are using a one or
        # multi-line display (also, default to 5x8 font):
        if self._height == 1:
            self.set_function(0,0)
        else:
            self.set_function(1,0)
        return

    @property
    def mode(self):
        """
        Return the current hardware operating mode.

        Returns one of self.MODE_8BIT or self.MODE_4BIT
        """
        if self._no_pins == 8:
            return self.MODE_8BIT
        elif self._no_pins == 4:
            return self.MODE_4BIT
        else:
            return self.MODE_UNKNOWN

    @property
    def width(self):
        """Return the physical display width (in characters)"""
        return self._width

    @property
    def height(self):
        """Return the physical display height (in characters)"""
        return self._height

    @property
    def host_pins(self):
        """
        Return a list of host pins used for data transfer.
        """
        return [x.id() for x in self._data_pins]

    def clear(self):
        """
        Clear the display and return the cursor to home.
        """
        return self._send([0,0,0,0,0,0,0,1], self.MSG_TYPE_CMD)

    def home(self):
        """
        Return the cursor/screen/shift to home.
        """
        return self._send([0,0,0,0,0,0,1,0], self.MSG_TYPE_CMD)

    def shift(self, s_c, r_l):
        """
        Instruct the HD44780 to perform a display shift.

        Params:
         - s_c: 0 = shift cursor; 1 = shift screen
         - r_l: 1 = shift right; 0 = shift left
        """
        return self._send([0,0,0,1,s_c,r_l,0,0], self.MSG_TYPE_CMD)

    def write(self, buf):
        """
        Write a stream of character data to the HD44780 display.

        NOTE: Presently resets to home position!!!
        """
        self.home()
        self._ch_idx = 0 # Reset character counter

        for ch in buf:
            line_pos = self._ch_idx % self._width

            # If we've reached the beginning of a line:
            if line_pos == 0:
                line_no = self._ch_idx // self._width
                self.set_ddram(self._line_addr[line_no])

            # Send actual data:
            data = [int(x) for x in list('{0:08b}'.format(ord(ch)))]
            self._send(data, self.MSG_TYPE_DATA)
            self._ch_idx = (self._ch_idx + 1) % (self._width * self._height)
        return

    def set_8bit_mode(self):
        """
        Safely transition HD44780 controller to 8-bit mode.
        """
        for i in range(3):
            self._send([0,0,1,1], self.MSG_TYPE_CMD)
        self._mode = self.MODE_8BIT
        return

    def set_4bit_mode(self):
        """
        Safely transition HD44780 controller to 4-bit mode.
        """
        if self._mode != self.MODE_8BIT:
            self.set_8bit_mode()
        self._send([0,0,1,0], self.MSG_TYPE_CMD)
        return

    def set_display_opts(self, d, c, b):
        """
        Set display options. Use 1 for ON and 0 for OFF.

        Params:
         - d: Display ON/OFF bit
         - c: Cursor ON/OFF bit
         - b: Blink ON/OFF bit
        """
        return self._send([0,0,0,0,1,d,c,b], self.MSG_TYPE_CMD)

    def set_entry_mode(self, i_d, s):
        """
        Set HD44780 "Entry Mode". This is used to control automatic
        cursor/screen shifting after data transmission.

        Params:
         - i_d: 1 = increment; 0 = decrement
         - s: 0 = move cursor only; 1 = shift display
        """
        return self._send([0,0,0,0,0,1,i_d,s], self.MSG_TYPE_CMD)

    def set_function(self, n, f):
        """
        Set number of display lines, and font.

        Params:
         - n: 0 = ONE line display; 1 = TWO line display
         - f: 0 = 5x8 font; 1 = 5x10 font
        """
        # Function set - data length:
        dl_bit = int(self._no_pins == 8)
        return self._send([0,0,1,dl_bit,n,f,1,1], self.MSG_TYPE_CMD)

    def set_ddram(self, addr):
        """
        Set the DDRAM address to the argument given.
        """
        addr = (addr & 0xff) | 0x80
        data = [(addr >> n & 1) for n in range(7,-1,-1)]
        return self._send(data, self.MSG_TYPE_CMD)

    def set_cgram(self, addr):
        """
        Set the CGRAM address to the argument given.
        """
        addr = (addr & 0x7f) | 0x40
        data = [(addr >> n & 1) for n in range(7,-1,-1)]
        return self._send(data, self.MSG_TYPE_CMD)

    def _send(self, bit_data, msg_type, delay_us=1530):
        """
        Send the bit data in increments of the number of active pins.
        Param:
         - bit_data: An array of binary data as ints
         - delay_us: Delay until the HD44780 can process another command after
                     this one has been successfully relayed.
        """

        # Wait (if necessary) until HD44780 is ready for next command:
        # self._wait_for_completion(delay_us)

        # Set the RS pin according to the message type we're sending:
        self._rs_pin.value(int(msg_type == self.MSG_TYPE_DATA))

        payload_len = len(bit_data)
        # Send the data as appropriately sized "nibbles":
        for i in range(0,payload_len,self._no_pins):
            for b in range(0,self._no_pins):
                self._data_pins[b].value(bit_data[i+b])

            # Pins are set; toggle the clock/enable pin:
            self._clk_pin.value(1)
            time.sleep_us(delay_us) # <-- hack: Wait MAX amount of time.
                                    # TODO: use _wait_for_completion or RW bit
            self._clk_pin.value(0)
        return

    def _init_line_addrs(self, w, h):
        """
        Set the "beginning of line" addresses for each line available on the
        physical display (this is used to automatically jump to the beginning
        of the next line when we've run over the width boundary for the current
        one).
        """
        # For 16x1:
        if h == 1:
            return (self.DDRAM0_START)
        # For 16x2, 20x2, 40x2
        elif h == 2:
            return (self.DDRAM0_START, self.DDRAM1_START)
        # For 20x4
        elif h == 4:
            return (self.DDRAM0_START,
                    self.DDRAM1_START,
                    self.DDRAM0_START + 0x14,
                    self.DDRAM1_START + 0x14,
                    )
        else:
            raise Exception("No DDRAM -> pixel mapping for this ratio!")
        return

    def _wait_for_completion(self, delay_us):
        """
        Used by _send to wait until the previous data has been processed before
        sending any additional data packets.
        """
        now = time.ticks_us()

        if now < self._last_cmd_complete:
            remain_us = (self._last_cmd_complete - now) + 1
            if self._rw_pin is None:
                # If enough time hasn't elapsed, we'll wait until the maximum
                # execution time has elapsed:
                time.sleep_us( remain_us )
            else:
                # TODO: leverage RW pin to wait on completion, if available.
                # For now, we do the same as if we had no RW pin:
                time.sleep_us( remain_us )

        # Update last timestamp and proceed:
        self._last_cmd_complete = now + delay_us
        return

# EOF

