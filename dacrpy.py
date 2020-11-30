#!/usr/bin/env python

import time
from colorsys import hsv_to_rgb
from PIL import ImageFont, Image, ImageDraw, ImageStat
import os
import os.path
from os import path
import ST7789 as ST7789
from socketIO_client import SocketIO, LoggingNamespace
import requests
from io import BytesIO
from numpy import mean
import sys
import logging
import signal
import RPi.GPIO as GPIO
import commands 

# Startup Script
print("Pirate Display | Startup")
print("------------------------")
print(" ")
global waitingforshutdown
global isScreenOn 
waitingforshutdown = 0
  
# get the path of the script
script_path = os.path.dirname(os.path.abspath(__file__))
# set script path as current directory
os.chdir(script_path)

# Services
# airplay_emulation 

def on_connect():
    print('connected')

def on_disconnect():
    print('disconnected')
    img = Image.new('RGBA', (240, 240), color=(0, 0, 0, 25))
    img = Image.open('/volumio/app/plugins/miscellanea/albumart/default.jpg')
    img = img.resize((WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img, 'RGBA')
    draw.text((10, 200), 'shuting down ...', font=font_m, fill=(255, 255, 255))
    disp.display(img)

# Get the background image and decorate it with hostname and IP Address 
def getBackgroundImage():
    temp_background = Image.open(script_path + '/images/blank.png').resize((240,240))
    txt_col = (255, 255, 255)
    draw = ImageDraw.Draw(temp_background, 'RGBA')
    width,height= draw.textsize(hostname, font=font_l)
    draw.text(((240-width)/2, 115),hostname,font=font_l, fill=txt_col)
    width,height= draw.textsize(ipaddress, font=font_l)
    draw.text(((240-width)/2, 145), ipaddress , font=font_l, fill=txt_col) 
    return temp_background
    
def on_push_state(*args):
    img = Image.new('RGBA', (240, 240), color=(0, 0, 0, 25))
    global status
    global service
    global ipaddress
    global tracktype 
    global isScreenOn 
    
    if 'status' in args[0]:
        status = args[0]['status'].encode('ascii', 'ignore')
    else:
        status = 'unknown'
   
    if 'service' in args[0]:
        service = args[0]['service'].encode('ascii', 'ignore')
    else:
        service = 'unknown'
    if 'uri' in args[0]:
        print 'URI ' + args[0]['uri'] 
    
    if 'trackType' in args[0]:
        tracktype = args[0]['trackType'] 
        print 'Tract Type ' + tracktype
    else:
        tracktype = "unknown"
        
    volume = args[0]['volume']
    print ("Volume: {}".format(volume))
    
    canseek = 0 
    if 'duration' in args[0]:
        duration = args[0]['duration']  # seconds
        if duration != 0:
            if 'seek' in args[0]:
                seek = args[0]['seek']  # time elapsed seconds
                if isinstance(seek, int):
                    if seek != 0:
                        canseek = 1
    print("Can Seek: {}".format(canseek)) 
    
    # Load albumcover or radio cover
    albumart = args[0]['albumart'].encode('ascii', 'ignore')
    getart = 0
    if len(albumart) == 0:  # to catch a empty field on start
        img = getBackgroundImage()
        print('Album Art Length Zero - using default Service: ' + service)
        
        #albumart = 'http://localhost:3000/albumart'
    elif 'http' not in albumart:
        if albumart == '/albumart':
            img = getBackgroundImage()
            print('Album Art /albumart - using default Service: ' + service)
        else:
            albumart = 'http://localhost:3000'+args[0]['albumart']
            response = requests.get(albumart)
            img = Image.open(BytesIO(response.content))
            img = img.resize((WIDTH, HEIGHT))
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            print('Album Art: '+albumart + ' Service: ' + service)
    else:     
        print('Album Art: '+albumart + ' Service: ' + service)
        response = requests.get(albumart)
        img = Image.open(BytesIO(response.content))
        img = img.resize((WIDTH, HEIGHT))
        if img.mode != "RGBA":
            img = img.convert("RGBA")

    # Light / Dark Symbols an bars, depending on background
    im_stat = ImageStat.Stat(img)
    im_mean = im_stat.mean
    mn = mean(im_mean)

    txt_col = (255, 255, 255)
    bar_bgcol = (200, 200, 200)
    bar_col = (255, 255, 255)
    dark = False
    if mn > 175:
        txt_col = (55, 55, 55)
        dark = True
        bar_bgcol = (255, 255, 255)
        bar_col = (100, 100, 100)
    if mn < 80:
        txt_col = (200, 200, 200)

    # paste button symbol overlay in light/dark mode
    if service != "airplay_emulation":
        if status == 'play':
            if dark is False:
                img.paste(pause_icons, (0, 0), pause_icons)
            else:
                img.paste(pause_icons_dark, (0, 0), pause_icons_dark)
        else:
            if dark is False:
                img.paste(play_icons, (0, 0), play_icons)
            else:
                img.paste(play_icons_dark, (0, 0), play_icons_dark)
    
    # Set Icon on top right hand corner based on source
    shownames = 0
    if tracktype == "airplay":
        img.paste(airplay_overlay, (0, 0), airplay_overlay)
        shownames = 1
    elif service == "mpd":
        img.paste(mpd_overlay, (0, 0), mpd_overlay)
        shownames = 1
    elif service == "webradio":
        img.paste(webradio_overlay, (0, 0), webradio_overlay)
        shownames = 0
    elif service == "spop":
        img.paste(spotify_overlay, (0, 0), spotify_overlay)
        shownames = 1
    elif service == "volspotconnect2":
        img.paste(spotify_overlay, (0, 0), spotify_overlay)
        shownames = 1
    elif tracktype == "tidal":
        img.paste(tidal_overlay, (0, 0), tidal_overlay)
        shownames = 1
    elif tracktype == "qobuz":
        img.paste(qobuz_overlay, (0, 0), qobuz_overlay)
        shownames = 1
    elif tracktype == "bt":
        img.paste(bluetooth_overlay, (0, 0), bluetooth_overlay)
        shownames = 0
    else:
        img.paste(bluetooth_overlay, (0, 0), bluetooth_overlay)
        shownames = 0
    
        
    draw = ImageDraw.Draw(img, 'RGBA')

    top = 7
    if 'artist' in args[0]:
        x1 = 20
        w1, y1 = draw.textsize(args[0]['artist'], font_m)
        x1 = x1-20
        if x1 < (WIDTH - w1 - 20):
            x1 = 0
        if w1 <= WIDTH:
            x1 = (WIDTH - w1)//2
        if shownames == 1:
            draw.text((x1, top), args[0]['artist'], font=font_m, fill=txt_col)
    top = 35

    if 'album' in args[0]:
        if args[0]['album'] is not None:
            x2 = 20
            w2, y2 = draw.textsize(args[0]['album'], font_s)
            x2 = x2-20
            if x2 < (WIDTH - w2 - 20):
                x2 = 0
            if w2 <= WIDTH:
                x2 = (WIDTH - w2)//2
            if shownames == 1:
                draw.text((x2, top), args[0]['album'], font=font_s, fill=txt_col)

    if 'title' in args[0]:
        # Does the title fit on one line
        
        x3 = 20
        w3, y3 = draw.textsize(args[0]['title'], font_l)
        x3 = x3-20
        if x3 < (WIDTH - w3 - 20):
            x3 = 0
        if w3 <= WIDTH:
            x3 = (WIDTH - w3)//2
        if shownames == 1:
            draw.text((x3, 105), args[0]['title'], font=font_l, fill=txt_col)  # fill by mean

    # volume bar
    # Not prsent for airplay_emulation
    if service != "airplay_emulation":
        vol_x = int((float(args[0]['volume'])/100)*(WIDTH - 33))
        draw.rectangle((5, 184, WIDTH-34, 184+8), bar_bgcol)  # background
        draw.rectangle((5, 184, vol_x, 184+8), bar_col)
        volumeText = "Volume: {}".format(args[0]['volume'])
        x2 = 0
        w2, y2 = draw.textsize(volumeText, font_s)
        if w2 <= WIDTH:
            x2 = (WIDTH - w2)//2
        draw.text((x2, 154), volumeText, font=font_s, fill=txt_col)

    # time bar
    if canseek == 1:
        el_time = int(float(args[0]['seek'])/1000)
        du_time = int(float(args[0]['duration']))
        dur_x = int((float(el_time)/float(du_time))*(WIDTH-10))
        draw.rectangle((5, 222, WIDTH-5, 222 + 12), bar_bgcol)  # background
        draw.rectangle((5, 222, dur_x, 222 + 12), bar_col)

    # Draw the image on the display hardware
    disp.display(img)

socketIO = SocketIO('localhost', 3000)
socketIO.on('connect', on_connect)

# Create ST7789 LCD display class.
disp = ST7789.ST7789(
    rotation=90,  # Needed to display the right way up on Pirate Audio
    port=0,       # SPI port
    cs=1,         # SPI port Chip-select channel
    dc=9,         # BCM pin used for data/command
    backlight=13,
    spi_speed_hz=80 * 1000 * 1000
)

# Initialize display.
disp.begin()

WIDTH = 240
HEIGHT = 240
waitingforshutdown = 0
font_s = ImageFont.truetype(script_path + '/fonts/Roboto-Medium.ttf', 20)
font_m = ImageFont.truetype(script_path + '/fonts/Roboto-Medium.ttf', 24)
font_l = ImageFont.truetype(script_path + '/fonts/Roboto-Medium.ttf', 30)

play_icons = Image.open('images/controls-play.png').resize((240, 240))
play_icons_dark = Image.open('images/controls-play-dark.png').resize((240, 240))
pause_icons = Image.open('images/controls-pause.png').resize((240, 240))
pause_icons_dark = Image.open('images/controls-pause-dark.png').resize((240, 240))
airplay_overlay = Image.open('images/airplay_overlay.png').convert("RGBA")
mpd_overlay = Image.open('images/mpd_overlay.png').convert("RGBA")
webradio_overlay = Image.open('images/webradio_overlay.png').convert("RGBA")
spotify_overlay = Image.open('images/spotify_overlay.png').convert("RGBA")
tidal_overlay = Image.open('images/tidal_overlay.png').convert("RGBA")
bluetooth_overlay =  Image.open('images/bluetooth_overlay.png').convert("RGBA")
qobuz_overlay =  Image.open('images/qobuz_overlay.png').convert("RGBA")

# Setup Background Image 
ipaddress = commands.getoutput('hostname -I')
hostname = commands.getoutput('hostname')
print("Ip Address: " + ipaddress)
print("Hostname: " + hostname)
waitingforshutdown = 0 
default_background = getBackgroundImage()
disp.display(default_background)

GPIO.setmode(GPIO.BCM)
dark = Image.open('images/controls-pause-dark.png').resize((240, 240))

BUTTONS = [5, 6, 16, 24] 
LABELS = ['A', 'B', 'X', 'Y']
# Set up RPi.GPIO with the "BCM" numbering scheme
# Buttons connect to ground when pressed, so we should set them up
# with a "PULL UP", which weakly pulls the input signal to 3.3V.
GPIO.setup(BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def shutDownPi():
    command = "/usr/bin/sudo /sbin/shutdown now"
    import subprocess
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output = process.communicate()[0]
    print output
    
def rebootPi():
    command = "/usr/bin/sudo /sbin/shutdown -r now"
    import subprocess
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output = process.communicate()[0]
    print output
    
def handle_button(pin):
    global waitingforshutdown
    global isScreenOn 
    label = LABELS[BUTTONS.index(pin)]
    print("Button press detected on pin: {} label: {}".format(pin, label))
    print("Status: {} Service {}".format(status, service))

    if isScreenOn == 0:
        #Pressed a button and screen is off, turn it on
        setScreenOn()
        pass 
        
    if pin == 5: # 'A' 
        if waitingforshutdown == 1:
            rebootPi()
        if (status == 'play') and (service == 'webradio'):
            print('pause')
            socketIO.emit('pause')
        elif (status == 'play'):
            print('pause')
            socketIO.emit('pause')
        else:
            print('play')
            socketIO.emit('play')
            
    if pin == 6:   # 'B'
        if waitingforshutdown == 1:
            setScreenOff()
        waitingforshutdown = 0
        print('volDown')
        socketIO.emit('volume', '-')
        
    if pin == 16: # 'X'
        print('Shutdown')
        if waitingforshutdown == 1: # Pressing it for the second time 
            shutitDown()
            shutDownPi()
        else:
            img = Image.new('RGB', (240, 240), color=(0, 0, 0))
            system_menu =  Image.open('images/system_menu.png').convert("RGBA")
            img.paste(system_menu, (0, 0), system_menu)
            #draw.rectangle((0, 0, 240, 240), (0, 0, 0))
            #txt_col = (255, 255, 255)
            #StatusText = 'Shutdown ?'
            #width,height= draw.textsize(StatusText, font=font_l)
            #draw.text(((240-width)/2, 20),StatusText,font=font_l, fill=txt_col)
            #StatusText = 'Press Again to Shutdown'
            #width,height= draw.textsize(StatusText, font=font_s)
            #draw.text(((240-width)/2, 80),StatusText,font=font_s, fill=txt_col)
            #StatusText = 'or other button to resume'
            #width,height= draw.textsize(StatusText, font=font_s)
            #draw.text(((240-width)/2, 110),StatusText,font=font_s, fill=txt_col)
            disp.display(img)
            waitingforshutdown = 1
    if pin == 24: # 'Y'
        waitingforshutdown = 0
        print('volUp')
        socketIO.emit('volume', '+')

def main():
    while True:
        print ('Entering Main Loop')
        for pin in BUTTONS:
            GPIO.add_event_detect(pin, GPIO.FALLING, handle_button, bouncetime=100)
        setScreenOn()
        disp.set_backlight(True)
        disp.display(default_background)
        # Bind Socket 
        socketIO.on('pushState', on_push_state)
        # Get initial state
        socketIO.emit('getState', '', on_push_state)
        socketIO.wait()
        time.sleep(0.01)

def shutitDown():
    print('Shutting Down.....')
    img = Image.new('RGB', (240, 240), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 240, 240), (0, 0, 0))
    StatusText = 'Shutdown Display'
    width,height= draw.textsize(StatusText, font=font_l)
    txt_col = (255, 255, 255)
    draw.text(((240-width)/2, 20),StatusText,font=font_l, fill=txt_col)
    disp.display(img)

def setScreenOn():
    global isScreenOn 
    disp.set_backlight(True)
    isScreenOn = 1

def setScreenOff():
    global isScreenOn 
    disp.set_backlight(False)
    isScreenOn = 0
    

if __name__ == '__main__':
        try:
            main()
        except KeyboardInterrupt, Exception:
            shutitDown()
            #disp.set_backlight(False)
            pass