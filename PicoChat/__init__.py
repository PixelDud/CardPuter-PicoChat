import os
import requests
import network
import random
import time
import json
import uasyncio as asyncio
from machine import SPI, Pin, freq, SDCard
from lib import st7789fbuf, smartkeyboard, mhconfig
from . import base64 as b64

with open("config.json", "r") as conf:
    config = json.loads(conf.read())
    ui_color = config["ui_color"]
    bg_color = config["bg_color"]

freq(240000000)

# Sets up the display
tft = st7789fbuf.ST7789(
    SPI(1, baudrate=40000000, sck=Pin(36), mosi=Pin(35), miso=None),
    135,
    240,
    reset=Pin(33, Pin.OUT),
    cs=Pin(37, Pin.OUT),
    dc=Pin(34, Pin.OUT),
    backlight=Pin(38, Pin.OUT),
    rotation=1,
    color_order=st7789fbuf.BGR
)

async def timer_handler():
    global timer
    while True:
        await asyncio.sleep(1)
        timer -= 1
        if timer <= 0:
            connect()
            get_messages()
            timer = 120
            

# Gets username and server URL
def fetch_settings():
    try:
        sd = SDCard(slot=2, sck=Pin(40), miso=Pin(39), mosi=Pin(14), cs=Pin(12))
        os.mount(sd, '/sd')
    except OSError:
        print("Could not mount SDCard!")

    picochat_dir = []
    if "sd" in os.listdir("/"):
        picochat_dir = "/sd/apps/PicoChat"
    
    f = open(picochat_dir + "/settings.json")
    data = json.load(f)
    f.close()
    return data

# Initialize global variables
RGB = st7789fbuf.color565
CONFIG = mhconfig.Config()
SETTINGS = fetch_settings()
SERVER = SETTINGS['server']
USER = SETTINGS['username']
cursor_text_pos = 0
cursor_screen_pos = 4

# To connect to the network
def connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        tft.fill(bg_color)
        tft.text("Connecting to network...", 24, 63, ui_color)
        tft.show()
        print('Connecting to network...')
        wlan.connect(CONFIG["wifi_ssid"], CONFIG["wifi_pass"])
        while not wlan.isconnected():
            pass
    print('network config:', wlan.ifconfig())

# For handling long messages
def wrap(text):
    words = str(text).split(' ')
    lines = []
    current_string = ""
    for word in words:
        if len(current_string) + len(word) + 1 < 30:
            current_string += word + " "
        else:
            lines.append(current_string)
            current_string = word + " "
    lines.append(current_string)
    return lines

# Gets chatlog from server, decodes, and displays it
def get_messages():
    tft.fill_rect(0, 0, 240, 120, bg_color)
    validator = random.uniform(0, 1)
    http_req = requests.get(('https://' + str(SERVER) + '/' + str(validator) + '/%2bget'), headers={})
    rawlog = http_req.content.decode("ascii")
    splitlog = rawlog.split('-')

    splitlog = splitlog[-15:]

    chatlog = []
    m = 0
    while m < len(splitlog):
        chatlog.append(str(b64.b32decode(splitlog[m]).decode("ascii"))[:-1])
        m += 1
    chatlog.pop()

    l = 1

    printlog = []

    i = 0
    while i < len(chatlog):
        if len(chatlog[len(chatlog)-1-i]) <= 30:
            printlog.append(chatlog[len(chatlog)-1-i])
        else:
            lines = wrap(chatlog[len(chatlog)-1-i])
            for z in range(len(lines)):
                printlog.append(lines[len(lines)-1-z])
        i += 1

    printlog = printlog[:15]

    for line in printlog:
        tft.text(line, 0, 120-8*(15-(len(printlog)-l)), ui_color)
        l += 1

    tft.show()

# Sends given message
def send_message(message):
    content = str(b64.b32encode(bytes(str("<" + USER + "> " + message + "\n"), "utf-8")).decode("ascii"))
    validator = random.uniform(0, 1)
    requests.get(('https://' + str(SERVER) + '/' + str(validator) + '/' + str(content)), headers={})
    get_messages()

# Moves cursor in set direction
def move_cursor(spaces, message):
    global cursor_text_pos
    global cursor_screen_pos
    if spaces == 1:
        if cursor_text_pos < len(message):
            cursor_text_pos += 1
            if cursor_screen_pos < 204:
                cursor_screen_pos += 8
    elif spaces == -1:
        if cursor_text_pos > 0:
            cursor_text_pos -= 1
            if cursor_screen_pos > 4 and not cursor_text_pos >= 25:
                cursor_screen_pos -= 8

# Moves cursor to beginning of message
def cursor_home():
    global cursor_text_pos
    global cursor_screen_pos
    cursor_text_pos = 0
    cursor_screen_pos = 4

# Moves cursor to end of message
def cursor_end(message):
    global cursor_text_pos
    global cursor_screen_pos
    cursor_text_pos = len(message)
    cursor_screen_pos = (len(message[-25:]) * 8) + 4

# Main function
async def main():
    # Setup variables
    KB = smartkeyboard.KeyBoard(config=CONFIG)
    keys = KB.get_new_keys()

    current_value = ''

    cursor_visible = True

    timer = 120

    # Initialize PicoChat
    tft.fill(bg_color)
    tft.text("Welcome to PicoChat!", 40, 63, ui_color)
    tft.show()
    time.sleep(1)
    connect()
    get_messages()
    asyncio.create_task(timer_handler())
    # Main Loop
    while True:
        # Keyboard handling
        keys = KB.get_new_keys()
        if keys:
            for key in keys:
                # Handle cursor movement
                if key == "UP":
                    cursor_end(current_value)
                elif key == "DOWN":
                    cursor_home()
                elif key == "LEFT":
                    move_cursor(-1, current_value)
                elif key == "RIGHT":
                    move_cursor(1, current_value)
                # Handle message editing
                elif key == "BSPC":
                    if cursor_text_pos != 0:
                        current_value = current_value[:(cursor_text_pos-1)] + current_value[cursor_text_pos:]
                        move_cursor(-1, current_value)
                elif key == "SPC":
                    current_value = current_value[:cursor_text_pos] + ' ' + current_value[cursor_text_pos:]
                    move_cursor(1, current_value)
                elif key == "ESC":
                    current_value = ''
                    cursor_home()
                elif len(key) == 1:
                    current_value = current_value[:cursor_text_pos] + key + current_value[cursor_text_pos:]
                    move_cursor(1, current_value)
                # Send message only when Enter is pressed
                elif key == "ENT":
                    if current_value:
                        send_message(current_value)
                        current_value = ''
                        cursor_home()

        # Displays message being edited
        tft.fill_rect(0, 120, 240, 135, RGB(62,55,92))
        if cursor_text_pos < 25:
            tft.text(current_value[-25:], 8, 124, RGB(178, 188, 194))
        else:
            tft.text(current_value[(cursor_text_pos-25):cursor_text_pos], 8, 124, RGB(178, 188, 194))

        if cursor_visible:
            tft.text("|", cursor_screen_pos, 124, RGB(120, 132, 171))

        tft.show()


        # For blinking the cursor
        if timer % 30 == 0:
            cursor_visible = not cursor_visible

# Calls main function
asyncio.run(main())

