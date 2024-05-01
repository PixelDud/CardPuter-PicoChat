# CardPuter-PicoChat
A [PicoChat](https://github.com/PixelDud/PicoChat-Server) client for the M5Stack CardPuter, written in MicroPython for use with [MicroHydra](https://github.com/echo-lalia/Cardputer-MicroHydra).

To use, simply place the `PicoChat` folder into the `apps/` folder on the SD card you use with MicroHydra.
The settings must be manually edited (for the time being), so make sure to set your username in the `settings.json` file! The default server address is active, so feel free to leave it as is, or go ahead and host your own server!

You send messages by typing them out on the keyboard, typing freezes when the light goes green (fetching the chat log). When a message exceeds 30 characters it will wrap, on the display but the whole thing will still be sent! Enter sends your message, ESC clears the message, so you can start over!

`base64.py` is sourced from [here](https://github.com/micropython/micropython-lib/blob/master/python-stdlib/base64/base64.py) and licensed under [this](https://www.python.org/download/releases/3.3.5/license/) license.
