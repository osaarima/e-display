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
from urllib.request import urlopen
import re
from datetime import datetime
import drawWeather
import matplotlib.pyplot as plt

#The job of this class is to keep track of button presses and give signal
#when a decision of button presses has been made.
class ListenButtons:
    def __init__(self):
        self.time_at_press = None
        self.last_state1 = False
        self.last_state2 = False
        self.n1 = 0
        self.n2 = 0
        self.reset = False
        self.resetting_time = 2


    def set_resetting_time(self,new_time):
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
        #print(self.n1,self.n2)
        return False


#This function is used to create the Image object shown in the screen
class WeatherImageManipulations:
    def __init__(self,l_filename_weather,l_devIn,l_devOut,l_width,l_height):
        self.filename_weather=l_filename_weather
        self.deviceIn=l_devIn
        self.deviceOut=l_devOut
        self.width=l_width
        self.height=l_height
        self.show_in_out=1
        self.skip_lines=0
        self.show_days_graph=1
        self.boldSize=26
        self.bold_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", self.boldSize
        )
        self.smolSize=20
        self.smol_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", self.smolSize
        )

    def switch_in_out(self):
        if self.show_in_out==1:
            self.show_in_out=2
        else:
            self.show_in_out=1

    def set_skip_lines(self,new_skip):
        self.skip_lines=new_skip

    def create_weather_image(self, filename_pic, flip_pic=True, show_plot=True):
        #Define fonts

        if self.show_in_out==1:
            deviceNow=self.deviceOut
            printTitle = "Ulko"
        else:
            deviceNow=self.deviceIn
            printTitle = "Sisä"

        image = Image.new("RGB", (self.width, self.height), color=WHITE)
        draw = ImageDraw.Draw(image)

        meas_time = []
        temp = []
        humidi = []
        pressure = []
        xLab = []
        yLab = []
        #timing1 = time.perf_counter()
        try:
            (meas_time,temp,humidi,pressure,xLab,yLab,lines) = drawWeather.get_weather_data(self.filename_weather,
                                                               deviceNow, self.show_days_graph, self.skip_lines)
            #We start by not skipping lines, but after that
            #we know how many we need to skip in order to show
            #all of the data we need. This will speed up the
            #reading of the file significantly (~one magnitude)
            self.set_skip_lines(lines-self.show_days_graph*24*60/5) #Next iteration we want to minimize the reading of the file.
            leng = len(meas_time)
            if leng==0:
                print("No events to show")
                return None
            #We want to print the last values
            savedTime = str(meas_time[leng-1]).split('T')[1]
            savedHumi = humidi[leng-1]
            savedTemp = temp[leng-1]
        except OSError as err:
            print("File is in use (most likely), trying again in a couple of seconds. Message: ", err)
            time.sleep(5)
            return None
        #timing2 = time.perf_counter()
        #print("Reading took: ", timing2-timing1, "seconds")

        #Then comes the text
        printTime  = "{}".format(savedTime)
        if show_plot:
            printData  = "{} °C".format(savedTemp)
        else:
            printData  = "{} °C\n{} %".format(savedTemp, savedHumi)
        yCoord = 3
        draw.text((5,yCoord), printTitle, font=self.bold_font, fill=BLACK,)
        yCoord+=self.boldSize+3
        draw.text((5,yCoord), printTime, font=self.smol_font, fill=BLACK,)
        yCoord+=self.smolSize+6
        draw.text((5,yCoord), printData, font=self.bold_font, fill=BLACK,)

        #This only checks the box where said text will fit
        (bbLeft, bbTop, bbRight, bbBottom) = draw.textbbox((5,yCoord), printData, font=self.bold_font)

        if show_plot:
            plt_img=make_plot_image(meas_time,temp,bbRight,self.height-bbBottom)
            image.paste(plt_img, box=(5,bbBottom), mask=None)

        with Image.open(filename_pic).convert("RGB") as paste_img:
            #Can I get automatic contrast/brightness enhancement working?
            #enhance_color = ImageEnhance.Color(paste_img)
            #paste_img = enhance_color.enhance(0.0)
            #enhance_contrast = ImageEnhance.Contrast(paste_img)
            #paste_img = enhance_contrast.enhance(0.5)
            #enhance_brightness = ImageEnhance.Brightness(paste_img)
            #paste_img = enhance_brightness.enhance(0.95)

            resize_lim_h = self.height #90
            resize_lim_w = self.width-bbRight
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
                paste_l_pos = round((self.width+bbRight)/2 - paste_img.size[0]/2)
            else:
                paste_l_pos = self.width-paste_img.size[0]
            if paste_img.size[1]!=resize_lim_h:
                paste_t_pos = round(self.height/2 - paste_img.size[1]/2)
            else:
                paste_t_pos = self.height-paste_img.size[1]
            image.paste(paste_img, box=(paste_l_pos,paste_t_pos), mask=None)

        #draw.line((bbRight,0,bbRight,self.height), fill=BLACK,)
        #print(self.width-bbRight)

        return image

    #This function is used to create the Image object shown in the screen
    def create_sun_image(self,country_name, city_name):
        #Define fonts
        image = Image.new("RGB", (self.width, self.height), color=WHITE)
        draw = ImageDraw.Draw(image)

        (daylen, sunrise, sundown) = find_sun_info(country_name,city_name)
        daylen_split = daylen.split(':')

        #In case of nightless night or sunless day:
        if sunrise=="nightless":
            draw.text((5,3),"Tänään on yötön yö :o", font=self.smol_font, fill=BLACK)
            draw.ellipse((self.width/6.0, self.height/2.0, self.width-self.width/6.0, self.height+self.height/2.0), 
                          fill=None, outline=BLACK, width=3)
            draw.line((self.width/6.0, self.height-2, self.width-self.width/6.0, self.height-2),
                          fill=BLACK, width=3)
            return image
        if sunrise=="sunless":
            draw.text((5,3),"Tänään on kaamos :o", font=self.smol_font, fill=BLACK)
            draw.ellipse((self.width/6.0, self.height/2.0, self.width-self.width/6.0, self.height+self.height/2.0),
                          fill=BLACK, outline=BLACK, width=3)
            return image

        #In case of failure:
        if daylen_split[0]=="" or daylen_split[1]=="" or daylen_split[2]=="":
            draw.text((5,3),"Aurinkotietojen\nhakeminen\nepäonnistui\n:(", font=self.smol_font, fill=BLACK)
            return image

        daylen_hours=int(daylen_split[0])
        daylen_mins=int(daylen_split[1])
        daylen_secs=int(daylen_split[2])

        #Let's round the seconds up in case s>=30
        if daylen_secs>=30:
            daylen_mins+=1
            if daylen_mins==60:
                daylen_mins=0
                daylen_hours+=1
        daylenStr = "{}:{:02d}".format(daylen_hours,daylen_mins)

        printText1  = "Nousu"
        printText2  = "Kesto"
        printText3  = "Lasku"
        printTime1  = "{}".format(sunrise)
        printTime2  = "{}".format(daylenStr)
        printTime3  = "{}".format(sundown)
        
        #Drawing text and numbers so that they are aligned left, center, and right
        draw.text((5,3), printText1, font=self.smol_font, fill=BLACK,)
        (bbLeft, bbTop, bbRight, bbBottom) = draw.textbbox((0,0), printText2, font=self.smol_font)
        draw.text((self.width/2.0-bbRight/2.0,3), printText2, font=self.smol_font, fill=BLACK,)
        (bbLeft, bbTop, bbRight, bbBottom) = draw.textbbox((0,0), printText3, font=self.smol_font)
        draw.text((self.width-bbRight,3), printText3, font=self.smol_font, fill=BLACK,)

        draw.text((5,3+self.smolSize+5), printTime1, font=self.smol_font, fill=BLACK,)
        (bbLeft, bbTop, bbRight, bbBottom) = draw.textbbox((0,0), printTime2, font=self.smol_font)
        draw.text((self.width/2.0-bbRight/2.0,3+self.smolSize+5), printTime2, font=self.smol_font, fill=BLACK,)
        (bbLeft, bbTop, bbRight, bbBottom) = draw.textbbox((0,0), printTime3, font=self.smol_font)
        draw.text((self.width-bbRight,3+self.smolSize+5), printTime3, font=self.smol_font, fill=BLACK,)

        draw.ellipse((self.width/6.0, self.height/2.0, self.width-self.width/6.0, self.height+self.height/2.0),
                      fill=None, outline=BLACK, width=3)
        draw.line((self.width/6.0, self.height-2, self.width-self.width/6.0, self.height-2),
                   fill=BLACK, width=3)

        #Lets draw a pieslice showing visually the length of day. Black slice means no sun, white is daylight.
        day_in_minutes = 24*60
        sunrise_split = sunrise.split('.')
        sunrise_in_minutes = int(sunrise_split[0])*60 + int(sunrise_split[1])
        sundown_split = sundown.split('.')
        sundown_in_minutes = int(sundown_split[0])*60 + int(sundown_split[1])

        ratio_sunrise = sunrise_in_minutes/day_in_minutes
        ratio_sundown = sundown_in_minutes/day_in_minutes

        #Let's draw pieslice on top of the ellipse (needs to have same coordinates. Angles define the darkness.
        draw.pieslice((self.width/6.0, self.height/2.0, self.width-self.width/6.0, self.height+self.height/2.0),
                       -180+180*ratio_sundown, -180+180*ratio_sunrise,
                       fill=BLACK, outline=BLACK, width=3)

        return image



#Finds and returns the length of day, sunrise, and sundown for a given city
#either from the timeanddate.com wep page or by argument. If there is a nightless
#night, returns ("nightless","nightless","nightless"), or if there is a sunless
#day, returns ("sunless","sunless","sunless"). In case of failure returns ("","","")
def find_sun_info(country_name, city_name, pre_year=-1, pre_month=-1, pre_date=-1):
    if pre_year==-1 and pre_month==-1 and pre_date==-1:
        currTime = str(datetime.now().date()).split('-')
        strYear = currTime[0]
        intMonth = int(currTime[1])
        intDate  = int(currTime[2])
    else:
        strYear = str(pre_year)
        intMonth = pre_month
        intDate = pre_date
    url = "https://www.timeanddate.com/sun/{}/{}?month={}&year={}".format(country_name,city_name,str(intMonth),strYear)
    try:
        with urlopen(url) as page:
            html_bytes = page.read()
            html = html_bytes.decode("utf-8")
            date_pattern = "data-day={}.*?data-day={}".format(intDate,intDate+1)
            date_result = re.findall(date_pattern, html, re.IGNORECASE)[0]

            #Let's first check if there is sun up or down at all.
            nightless_night_pattern = "Up all day"
            match_results = re.findall(nightless_night_pattern, date_result, re.IGNORECASE)
            if len(match_results)>0:
                return ("nightless","nightless","nightless")
            sunless_day_pattern = "Down all day"
            match_results = re.findall(sunless_day_pattern, date_result, re.IGNORECASE)
            if len(match_results)>0:
                return ("sunless","sunless","sunless")

            time_pattern = "<td class=\"c tr sep-l\".*?>.*?</td.*?>"
            match_results = re.findall(time_pattern, date_result, re.IGNORECASE)
            length_of_day = re.sub("<.*?>", "", match_results[0]) #Remove < ... >
            length_of_day = re.sub("\s*?", "", length_of_day) #Remove whitespace

            time_pattern = "<td class=\"c sep\".*?>.*?</td.*?>"
            match_results = re.findall(time_pattern, date_result, re.IGNORECASE)
            sunrise = re.sub("span.*?span", "", match_results[0]) #Remove extra info
            sunrise = re.sub("<.*?>", "", sunrise)
            sunrise = re.sub("\s*?", "", sunrise)

            time_pattern = "<td class=\"sep c\".*?>.*?</td.*?>"
            match_results = re.findall(time_pattern, date_result, re.IGNORECASE)
            sundown = re.sub("span.*?span", "", match_results[0])
            sundown = re.sub("<.*?>", "", sundown)
            sundown = re.sub("\s*?", "", sundown)

            #The timeanddate.com will return only '-' in case sundown
            #happens exactly at midnight.
            if sundown=='-':
                sundown='00.00'

            return (length_of_day, sunrise, sundown)
    except OSError as er:
        print("Error:",er,url)
        return ("","","")

#Make a plot from given data to width,height space in pixels
def make_plot_image(x_plot,y_plot,width,height):
    px = 1/plt.rcParams['figure.dpi'] #one pixel in inches
    fig, ax = plt.subplots(1,1,figsize=(width*px,height*px))
    plot_color="white"
    ax.set_xlabel("",color=plot_color)
    ax.set_ylabel("",color=plot_color)
    #ax.set_facecolor(plot_color)
    ax.tick_params(labelcolor=plot_color)
    ax.tick_params(axis='x', colors=plot_color)
    ax.tick_params(axis='y', colors=plot_color)
    ax.spines['top'].set_color(plot_color)
    ax.spines['bottom'].set_color(plot_color)
    ax.spines['left'].set_color(plot_color)
    ax.spines['right'].set_color(plot_color)

    #print(fig.canvas.get_width_height())

    ax.plot(x_plot,y_plot,color="black")

    posVal=False
    negVal=False
    for iT in y_plot:
        if iT<0:
            negVal=True
        else:
            posVal=True
        
    if posVal and negVal:
        ax.axhline(y=0, color="black", linestyle='--')

    fig.canvas.draw()
    plt_img = Image.frombytes("RGB", fig.canvas.get_width_height(), fig.canvas.tostring_rgb())
    plt_img.save("test.png")
    return plt_img


def sakarin_villapaitapeli_mini(display,up_but,down_but):
    with Image.open("pics/sakari/peli1.png").convert("RGB") as skr_img:
        show_image(display,skr_img)
    gamestate=0
    try:
        while True:
            if gamestate==0:
                if not up_but.value or not down_but.value:
                    with Image.open("pics/sakari/peli2.png").convert("RGB") as skr_img:
                        show_image(display,skr_img)
                    gamestate=1
            if gamestate==1:
                if not up_but.value:
                    with Image.open("pics/sakari/peli3-voitit.png").convert("RGB") as skr_img:
                        show_image(display,skr_img)
                    time.sleep(0.5)
                    with Image.open("pics/sakari/peli3-voitit2.png").convert("RGB") as skr_img:
                        show_image(display,skr_img)
                    gamestate=11
                if not down_but.value:
                    with Image.open("pics/sakari/peli3-havisit.png").convert("RGB") as skr_img:
                        show_image(display,skr_img)
                    time.sleep(0.5)
                    with Image.open("pics/sakari/peli3-havisit2.png").convert("RGB") as skr_img:
                        show_image(display,skr_img)
                    gamestate=11
            if gamestate==11:
                if not up_but.value:
                    with Image.open("pics/sakari/peli1.png").convert("RGB") as skr_img:
                        show_image(display,skr_img)
                    gamestate=0
                if not down_but.value:
                    return

            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting program...")
    return

def select_random_not_this(max_plus_one, not_this_one):
    while True:
        ranPic = random.randint(0,max_plus_one)
        if ranPic!=not_this_one:
            break
    return ranPic

def show_image(display,image):
    if not image:
        print("Error: No image produced which should be shown, exiting...")
        exit()
    display.fill(Adafruit_EPD.WHITE)
    display.image(image)
    display.display()
    return

if __name__ == "__main__":
    #make_plot_image([1,2,3,4],[1,2,3,4])
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

    #print(find_sun_info("finland","sodankyla",2023,5,24))

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
        #Nice to have the files in alphabetical order
        fnames = sorted(fnames)
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
    override_randomizer = False
    down_button_pressed = False
    image_manip = WeatherImageManipulations(args.weatherfile,
                  "e6:89:18:c1:32:1f", "fc:41:f4:c5:0c:08",
                  display.width, display.height)
    listener = ListenButtons()
    listener.set_resetting_time(1)
    show_plot=False
    try:
        while True:
            # only query the weather every 5 minutes (and on first run)
            if (not weather_refresh) or (time.monotonic() - weather_refresh) > 300:
                if randomize_every_update and not override_randomizer:
                    show_this_pic = select_random_not_this(totalPics,show_this_pic)
                weather_refresh = time.monotonic()
                image = image_manip.create_weather_image(filenames[show_this_pic],
                                                        "yuuka" in filenames[show_this_pic],
                                                        show_plot)
                #If image was not successfully made, lets try another time in a new loop
                show_image(display,image)

            if args.onetime:
                break

            show_plot=False
            override_randomizer = False
            if listener.check_button_state(up_button.value,down_button.value):
                if listener.n1>0 and listener.n2==0:
                    if listener.n1==3:
                        image = image_manip.create_sun_image("finland","jyvaskyla")
                        show_image(display,image)
                    elif listener.n1==2:
                        show_plot=True
                        weather_refresh=None
                    else:
                        image_manip.switch_in_out()
                        weather_refresh=None
                #We can decide the wanted pic by the number of presses
                if listener.n2>0 and listener.n1==0:
                    show_this_pic = (listener.n2-1)%totalPics
                    override_randomizer = True
                    weather_refresh=None
                
                if listener.n1==3 and listener.n2==3:
                    sakarin_villapaitapeli_mini(display,up_button,down_button)
                    weather_refresh=None

            #In order to not overburden cpu
            time.sleep(0.05)
            #print("test",i,"button1:",up_button.value,"button2:",down_button.value)
            #i+=1
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting program...")

