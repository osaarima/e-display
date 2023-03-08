#!/usr/bin/env python3

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
import argparse

#The job of this class is to keep track of button presses and give signal
#when a decision of button presses has been made.
class ListenButton:
    def __init__(self):
        self.time_at_press = None
        self.last_state1 = False
        self.last_state2 = False
        self.n1 = 0
        self.n2 = 0
        self.reset = False
        self.resetting_time = 2

    def set_resetting_time(new_time):
        self.resetting_time=2
        return

    #Return true if buttons were pressed and a decision of press has been made.
    #Return false if no buttons pressed, or the listening time of button presses
    #has not yet ended.
    def check_button_state(self,button1,button2):
        #We want to do reset only in the next loop as otherwise we lose the
        #number of presses.
        if self.reset:
            self.n1=0
            self.n2=0
            self.time_at_press = None
            self.reset=False
        #up_button.value gives False if pressed
        button1_was_pressed = not button1
        button2_was_pressed = not button2
        if button1_was_pressed or button2_was_pressed:
            #We do not want a long press to count as multiple presses
            if self.last_state1!=button1_was_pressed and button1_was_pressed:
                self.time_at_press = time.monotonic()
                self.n1+=1
            if self.last_state2!=button2_was_pressed and button2_was_pressed:
                self.time_at_press = time.monotonic()
                self.n2+=1
        self.last_state1 = button1_was_pressed
        self.last_state2 = button2_was_pressed
        if self.time_at_press and time.monotonic()-self.time_at_press > self.resetting_time:
            self.reset=True
            return True
        print(self.n1,self.n2)
        return False


#This function is used to create the Image object shown in the screen
def create_weather_image(filename_weather,width, height, show_in_out, filename_pic, flip_pic=True):
    #Define fonts
    boldSize=26
    bold_font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", boldSize
    )
    smolSize=20
    smol_font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", smolSize
    )

    image = Image.new("RGB", (width, height), color=WHITE)
    #print(display.width, display.height) #250 122
    draw = ImageDraw.Draw(image)

    #timing1 = time.perf_counter()
    try:
        with open(filename_weather, 'r', encoding="utf-8") as fil:
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

    #Then comes the text
    if show_in_out==1:
        printTitle = "Ulko"
    elif show_in_out==2:
        printTitle = "Sisä"
    printTime  = "{}".format(savedTime)
    printData  = "{} °C\n{} %".format(savedTemp, savedHumi)
    yCoord = 3
    draw.text((5,yCoord), printTitle, font=bold_font, fill=BLACK,)
    yCoord+=boldSize+3
    draw.text((5,yCoord), printTime, font=smol_font, fill=BLACK,)
    yCoord+=smolSize+6
    draw.text((5,yCoord), printData, font=bold_font, fill=BLACK,)

    #This only checks the box where said text will fit
    (bbLeft, bbTop, bbRight, bbBottom) = draw.textbbox((5,yCoord), printData, font=bold_font)

    with Image.open(filename_pic).convert("RGB") as paste_img:
        #Can I get automatic contrast/brightness enhancement working?
        #enhance_color = ImageEnhance.Color(paste_img)
        #paste_img = enhance_color.enhance(0.0)
        #enhance_contrast = ImageEnhance.Contrast(paste_img)
        #paste_img = enhance_contrast.enhance(0.5)
        #enhance_brightness = ImageEnhance.Brightness(paste_img)
        #paste_img = enhance_brightness.enhance(0.95)

        resize_lim_h = height #90
        resize_lim_w = width-bbRight
        resize_x1 = paste_img.size[0]
        resize_y1 = paste_img.size[1]
        resize_x2 = paste_img.size[0]
        resize_y2 = paste_img.size[1]
        #Test which restriction (x or y) is creating the smaller image and scale with that
        if resize_y1>resize_lim_h:
            resize_x1 = round(paste_img.size[0]*resize_lim_h/paste_img.size[1])
            resize_y1 = resize_lim_h
        if resize_x2>resize_lim_w:
            resize_x2 = resize_lim_w
            resize_y2 = round(paste_img.size[1]*resize_lim_w/paste_img.size[0])
        if resize_y1<resize_y2:
            paste_img=paste_img.resize((resize_x1, resize_y1),resample=Image.LANCZOS, reducing_gap=3.0)
        else:
            paste_img=paste_img.resize((resize_x2, resize_y2),resample=Image.LANCZOS, reducing_gap=3.0)

        if flip_pic:
            paste_img=paste_img.transpose(method=Image.FLIP_LEFT_RIGHT)

        #If the image has space, let's center it in the available space.
        #Otherwise it will be tightly fitted into the space.
        if paste_img.size[0]!=resize_lim_w:
            paste_l_pos = round((width+bbRight)/2 - paste_img.size[0]/2)
        else:
            paste_l_pos = width-paste_img.size[0]
        if paste_img.size[1]!=resize_lim_h:
            paste_t_pos = round(height/2 - paste_img.size[1]/2)
        else:
            paste_t_pos = height-paste_img.size[1]
        image.paste(paste_img, box=(paste_l_pos,paste_t_pos), mask=None)

    #draw.line((bbRight,0,bbRight,height), fill=BLACK,)
    #print(width-bbRight)

    return image

def select_random_not_this(max_plus_one, not_this_one):
    while True:
        ranPic = random.randint(0,max_plus_one)
        if ranPic!=not_this_one:
            break
    return ranPic

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="This displays the weather information measured by readRuuvi.py in an Raspberry pi e-ink display. The display is updated every five minutes starting from the time the program is first run. The first button changes between inside and outside weather information, and the second button refreshes the screen, starting the five minute timer from the beginning.",
                                     epilog="Created by OS")
    parser.add_argument("--rand",
                        "-r",
                        help="Randomize the picture shown every refresh",
                        action="store_true",
                        default=False)
    parser.add_argument("--defpic",
                        "-d",
                        help="Give some part of the default picture name. Needs to be black and white and 'bw' included in the filename.",
                        type=str,
                        nargs='?',
                        default="yuuka")
    parser.add_argument("--picfolder",
                        "-f",
                        help="The full path to the folder where the 'bw' labeled black and white pictures are located.",
                        type=str,
                        nargs='?',
                        default="/home/piirakka/e-display/pics/bw/")
    parser.add_argument("--weatherfile",
                        "-w",
                        help="The full path to the file generated by readRuuvi.py, which has the weather information.",
                        type=str,
                        nargs='?',
                        default="/home/piirakka/weather.csv")
    parser.add_argument("--onetime",
                        "-o",
                        help="Run the refresh only one time. Mainly used for testing",
                        action="store_true",
                        default=False)
    args = parser.parse_args()

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
    for (dirpath, dirnames, fnames) in walk(args.picfolder):
        for fname in fnames:
            if "bw" in fname:
                filenames.append(path.join(dirpath,fname))
                if args.defpic in fname:
                    defPic=totalPics
                totalPics+=1

    if len(filenames)==0:
        print("No files found for pic, terminating")
        exit()

    weather_refresh = None
    #i=0

    show_in_out = 1
    if args.rand:
        #If pic is choosen randomly every time, we would like to
        #see the default picture also happen sometime when the
        #program is ran the first time.
        show_this_pic = -1
    else:
        show_this_pic = defPic
    randomize_every_update = args.rand
    down_button_pressed = False
    listener = ListenButton()
    try:
        while True:
            # only query the weather every 5 minutes (and on first run)
            if (not weather_refresh) or (time.monotonic() - weather_refresh) > 300:
                if randomize_every_update:
                    show_this_pic = select_random_not_this(totalPics,show_this_pic)
                weather_refresh = time.monotonic()
                image = create_weather_image(args.weatherfile,
                                             display.width,
                                             display.height,
                                             show_in_out,
                                             filenames[show_this_pic],
                                             "yuuka" in filenames[show_this_pic])
                #If image was not successfully made, lets try another time in a new loop
                if not image:
                    weather_refresh = None
                    continue
                display.fill(Adafruit_EPD.WHITE)
                display.image(image)
                display.display()

            if listener.check_button_state(up_button.value,down_button.value):
                if listener.n1>0:
                    if show_in_out==1:
                        show_in_out = 2
                    else:
                        show_in_out = 1
                    weather_refresh=None
                if listener.n2>0:
                    weather_refresh=None

            #In order to not overburden cpu
            time.sleep(0.05)
            #print("test",i,"button1:",up_button.value,"button2:",down_button.value)
            #i+=1
            if args.onetime:
                break
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting program...")

