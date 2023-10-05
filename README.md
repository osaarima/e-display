# e-display
Code to display weather information from a file in my raspberry pi e-ink display. There is a button listener to check how many times a certain button has been pressed for added functionality.

Needs Adafruit_SSD1680 and Adafruit_EPD to work.

display_prototype.py was the first working version and display_continuous.py has button presses enabled by making it run continuously.

drawWeather.py is used to plot weather data using matplotlib. This is used in the display.

checkInstance.sh is ran as a cronjob to see if the display_continuous.py is running or not, and if not, the program will be excecuted.
