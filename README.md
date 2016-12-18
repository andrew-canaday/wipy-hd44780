wipy-hd44780
============

Quick-hack controller code for HD44780-based LCD's. Tossed this together to
control a couple of boards I got recently. This library _should_ work for 16x1,
16x2, 20x2, 40x2, and 20x4 LCD screens driven by Hitachi HD44780-compatible
controllers.

The code uses a relatively naive bit-banging approach. If you'd like to clean it
up or optimize for real-world usage, feel free to fork and submit a pull request
(to the develop branch!)

License
-------
This library is licensed under the MIT license. See **LICENSE** for details.

Example
-------

```Python
from hd44780 import HD44780
# By default, this will initialize the LCD controller for 4-bit mode,
# one a 16x2 display, and a 5x8 font:
lcd = HD44780()         # (See constructor for pin/size args!)
lcd.set_entry_mode(1,0) # Automatically increment cursor on write
lcd.write("Hello, world!")
```

