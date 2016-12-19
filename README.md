wipy-hd44780
============

Quick-hack controller code for HD44780-based LCD's. Tossed this together to
control a couple of boards I got recently. This library _should_ work for 16x1,
16x2, 20x2, 40x2, and 20x4 LCD screens driven by Hitachi HD44780-compatible
controllers.

The code uses a relatively naive bit-banging approach with software-based delays
and - at present - no utilization of the R/W pin. If you'd like to clean it up
or optimize for real-world usage, feel free to fork and submit a pull request
(develop branch is best!).

License
-------
This library is licensed under the MIT license. See **LICENSE** for details.


Usage
=====
(**NOTE:** _For complete API docs, see the source code._)

```Python
from hd44780 import HD44780

# Default setup:
# By default, this will initialize the LCD controller for 4-bit mode; use pins
# 08,30,31,03 for D7-D4, pin 00 for CLK/E, and pin 04 for RS; RW is unset; the
# default display size is assumed to be *16x2*, with a 5x8 font:
lcd = HD44780()             # (See constructor for pin/size args!)
lcd.set_display_opts(1,1,1) # Turn it on!
lcd.set_entry_mode(1,0)     # Automatically increment cursor on write
lcd.write("Hello, world!")

# Custom pins setup:
# Setting all the parameters, specifically (values chosen at random for
# illustration purposes):
lcd2 = HD44780(
	host_pins=['GP2', 'GP1', 'GP23', 'GP24'],
	clk='GP11',
	rs='GP12',
	width=20,
	height=4
	font=HD44780.FONT_5x10
	)
lcd.set_display_opts(1,1,1) # Turn it on!
lcd.set_entry_mode(1,0)     # Automatically increment cursor on write
lcd.write("Hello, other world!")
```

Notes
-----
 - At present, there is a parameter for the RW pin, but it is _not used_
 - The default pin layout is based _only on which pins I had free at the time!_
 - _If you have a "type 1" 16x1 board_, you should tell the driver that your
   display size is *8x2*. See the resources section for why this works.


Resources
=========

 - [Donald Weimand's Home Page](http://web.alfredstate.edu/weimandn/) - Honestly, the best resource I've found
   for LCD programming related information. Comprehensive yet easy to digest!
 - [Hitachi HD44780 on Wikipedia](https://en.wikipedia.org/wiki/Hitachi_HD44780_LCD_controller) - Good overview
