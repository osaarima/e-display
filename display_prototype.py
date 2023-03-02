# Code by me, but the original template and ideas from Adafruit Industries:
# SPDX-FileCopyrightText: 2020 Melissa LeBlanc-Williams for Adafruit Industries
# SPDX-License-Identifier: MIT

# RGB Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0) # value over 120 is considered white

import time
import digitalio
import busio
import board
from adafruit_epd.ssd1680 import Adafruit_SSD1680
from adafruit_epd.epd import Adafruit_EPD
from PIL import Image, ImageDraw, ImageFont

boldSize=26
bold_font = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", boldSize
)
smolSize=20
smol_font = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", smolSize
)

spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
ecs = digitalio.DigitalInOut(board.CE0)
dc = digitalio.DigitalInOut(board.D22)
rst = digitalio.DigitalInOut(board.D27)
busy = digitalio.DigitalInOut(board.D17)

# Initialize the Display
display = Adafruit_SSD1680(     # Newer eInk Bonnet
    122, 250, spi, cs_pin=ecs, dc_pin=dc, sramcs_pin=None, rst_pin=rst, busy_pin=busy,
)

display.rotation = 1

display.fill(Adafruit_EPD.WHITE)
image = Image.new("RGB", (display.width, display.height), color=WHITE)
#print(display.width, display.height) #250 122
draw = ImageDraw.Draw(image)

with open("/home/piirakka/weather.csv", 'r', encoding="utf-8") as fil:
    for num,line in enumerate(fil):
        if num==0:
            continue
        splitted = line.split(',')
        date = splitted[0]
        time = splitted[1]
        humi = splitted[2]
        temp = splitted[3]

printTitle = "Sää ulkona"
printTime  = "{}".format(time)
printData  = "{} °C\n{} %".format(temp, humi)
yCoord = 3
draw.text((5,yCoord), printTitle, font=bold_font, fill=BLACK,)
yCoord+=boldSize+3
draw.text((5,yCoord), printTime, font=smol_font, fill=BLACK,)
yCoord+=smolSize+6
draw.text((5,yCoord), printData, font=bold_font, fill=BLACK,)
#draw.line((0,image.size[1],image.size[0],0), fill=BLACK,)
filename = "/home/piirakka/e-display/yuuka_bw.png"
with Image.open(filename).convert("RGB") as paste_img:
    resize_lim = 90
    if paste_img.size[1]>resize_lim:
        #print(int(paste_img.size[0]*resize_lim/paste_img.size[1]))
        paste_img=paste_img.resize((int(paste_img.size[0]*resize_lim/paste_img.size[1]), resize_lim),resample=Image.NEAREST, reducing_gap=3.0)
    if "yuuka" in filename:
        paste_img=paste_img.transpose(method=Image.FLIP_LEFT_RIGHT)
    #Lets place the image we have at the lower right corner.
    image.paste(paste_img, box=(image.size[0]-paste_img.size[0],image.size[1]-paste_img.size[1]), mask=None)
display.image(image)
display.display()
