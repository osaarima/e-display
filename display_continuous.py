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
from os import walk
from os import path
from numpy import random

boldSize=26
bold_font = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", boldSize
)
smolSize=20
smol_font = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", smolSize
)

#This function is used to create the Image object shown in the screen
def create_weather_image(width, height, show_in_out, filename):
    image = Image.new("RGB", (width, height), color=WHITE)
    #print(display.width, display.height) #250 122
    draw = ImageDraw.Draw(image)

    #timing1 = time.perf_counter()
    try:
        with open("/home/piirakka/weather.csv", 'r', encoding="utf-8") as fil:
            #raise OSError(1, "testing the exception")
            if show_in_out==1:
                humi_ind = 2
                temp_ind = 3
            elif show_in_out==2:
                humi_ind = 6
                temp_ind = 7
            for num,line in enumerate(fil):
                if num==0:
                    continue
                splitted = line.split(',')
                #date = splitted[0]
                savedTime = splitted[1]
                savedHumi = splitted[humi_ind]
                savedTemp = splitted[temp_ind]
    except OSError as err:
        print("File is in use (most likely), trying again in a couple of seconds. Message: ", err)
        time.sleep(5)
        return None

    #timing2 = time.perf_counter()
    #print("Reading took: ", timing2-timing1, "seconds")
    if show_in_out==1:
        printTitle = "Sää ulkona"
    elif show_in_out==2:
        printTitle = "Sää sisällä"
    printTime  = "{}".format(savedTime)
    printData  = "{} °C\n{} %".format(savedTemp, savedHumi)
    yCoord = 3
    draw.text((5,yCoord), printTitle, font=bold_font, fill=BLACK,)
    yCoord+=boldSize+3
    draw.text((5,yCoord), printTime, font=smol_font, fill=BLACK,)
    yCoord+=smolSize+6
    draw.text((5,yCoord), printData, font=bold_font, fill=BLACK,)
    #draw.line((0,image.size[1],image.size[0],0), fill=BLACK,)
    with Image.open(filename).convert("RGB") as paste_img:
        resize_lim = 90
        if paste_img.size[1]>resize_lim:
            #print(int(paste_img.size[0]*resize_lim/paste_img.size[1]))
            paste_img=paste_img.resize((int(paste_img.size[0]*resize_lim/paste_img.size[1]), resize_lim),resample=Image.NEAREST, reducing_gap=3.0)
        if "yuuka" in filename:
            paste_img=paste_img.transpose(method=Image.FLIP_LEFT_RIGHT)
        #Lets place the image we have at the lower right corner.
        image.paste(paste_img, box=(image.size[0]-paste_img.size[0],image.size[1]-paste_img.size[1]), mask=None)

    return image

if __name__ == "__main__":
    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
    ecs = digitalio.DigitalInOut(board.CE0)
    dc = digitalio.DigitalInOut(board.D22)
    rst = digitalio.DigitalInOut(board.D27)
    busy = digitalio.DigitalInOut(board.D17)
    up_button = digitalio.DigitalInOut(board.D6)
    up_button.switch_to_input()
    down_button = digitalio.DigitalInOut(board.D5)
    down_button.switch_to_input()

    # Initialize the Display
    display = Adafruit_SSD1680(     # Newer eInk Bonnet
        122, 250, spi, cs_pin=ecs, dc_pin=dc, sramcs_pin=None, rst_pin=rst, busy_pin=busy,
    )

    display.rotation = 1

    filenames = []
    totalPics = 0
    defPic = 0
    #Find all black and whit (bw) pics in the picture folder and list them.
    #"yuuka" picture is the default one.
    for (dirpath, dirnames, fnames) in walk("/home/piirakka/e-display/pics/"):
        for fname in fnames:
            if "bw" in fname:
                filenames.append(path.join(dirpath,fname))
                if "yuuka" in fname:
                    defPic=totalPics
                totalPics+=1

    weather_refresh = None
    #i=0

    down_button_pressed = False
    show_in_out = 1
    show_this_pic = defPic
    while True:
        # only query the weather every 5 minutes (and on first run)
        if (not weather_refresh) or (time.monotonic() - weather_refresh) > 300:
            weather_refresh = time.monotonic()
            image = create_weather_image(display.width,
                                         display.height,
                                         show_in_out,
                                         filenames[show_this_pic])
            #If image was not successfully made, lets try another time in a new loop
            if not image:
                weather_refresh = None
                continue
            display.fill(Adafruit_EPD.WHITE)
            display.image(image)
            display.display()

        #If button 1 is pressed, we want to change to change between
        #indoor and outdoor information.
        if not up_button.value:
            if show_in_out==1:
                show_in_out = 2
            else:
                show_in_out = 1
            #After pushing button we want a refresh
            weather_refresh = None

        #If button 2 is pressed, we want to change the pic randomly,
        #but not to the same one as previously.
        if not down_button.value:
            while True:
                ranPic = random.randint(0,totalPics)
                if ranPic!=show_this_pic:
                    break
            show_this_pic=ranPic
            #After pushing button we want a refresh
            weather_refresh = None

        #In order to not overburden cpu
        time.sleep(0.1)
        #print("test",i,"button1:",up_button.value,"button2:",down_button.value)
        #i+=1

