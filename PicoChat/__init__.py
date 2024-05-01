import os, requests, network, random, time, neopixel, json
from machine import SPI, Pin, freq, SDCard
from lib import st7789fbuf, smartkeyboard, mhconfig
from . import base64 as b64

freq(240000000)
ledPin = Pin(21)
led = neopixel.NeoPixel(ledPin, 1, bpp=3)

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

RGB = st7789fbuf.color565
CONFIG = mhconfig.Config()
KB = smartkeyboard.KeyBoard(config=CONFIG)

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

def connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        led.fill((10,0,0)); led.write()
        tft.fill(RGB(23,17,26))
        tft.text("Connecting to network...", 24, 63, RGB(255,255,255))
        tft.show()
        print('Connecting to network...')
        wlan.connect(CONFIG["wifi_ssid"], CONFIG["wifi_pass"])
        while not wlan.isconnected():
            pass
        led.fill((0,0,0)); led.write()
    print('network config:', wlan.ifconfig())

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

def get_messages():
    led.fill((0,10,0)); led.write()
    tft.fill_rect(0, 0, 240, 120, RGB(23,17,26))
    validator = random.uniform(0, 1)
    http_req = requests.get(('https://' + str(server) + '/' + str(validator) + '/%2bget'), headers={})
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
        tft.text(line, 0, 120-8*(15-(len(printlog)-l)), RGB(255,255,255))
        l += 1

    tft.show()
    led.fill((0,0,0)); led.write()

def send_message(message):
    led.fill((0,0,10)); led.write()
    content = str(b64.b32encode(bytes(str("<" + username + "> " + message + "\n"), "utf-8")).decode("ascii"))
    validator = random.uniform(0, 1)
    requests.get(('https://' + str(server) + '/' + str(validator) + '/' + str(content)), headers={})
    led.fill((0,0,0)); led.write()
    get_messages()

current_value = ''
tft.fill(RGB(23,17,26))
tft.text("Welcome to PicoChat!", 40, 63, RGB(255,255,255))
tft.show()
time.sleep(2)
SETTINGS = fetch_settings()
server = SETTINGS['server']
username = SETTINGS['username']
connect()
get_messages()

timer = 120;

keys = KB.get_new_keys()

while True:
    keys = KB.get_new_keys()
    if keys:
        for key in keys:
            if key == "ENT":
                send_message(current_value)
                current_value = ''
            elif key == "BSPC":
                current_value = current_value[0:-1]
            elif key == "SPC":
                current_value = current_value + ' '
            elif key == "DEL":
                editor.del_line()
            elif key == "ESC":
                current_value = ''
            elif len(key) == 1:
                current_value += key

    tft.fill_rect(0, 120, 240, 135, RGB(62,55,92))
    tft.text(current_value[-25:], 8, 124, RGB(178, 188, 194))
    tft.show()

    timer -= 1
    if timer <= 0:
        connect()
        get_messages()
        timer = 120