#! /usr/bin/env python

#bdoorcheck.py for doorsound
#Copyright (C) 2014  Paul Schow

#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; either version 2
#of the License, or (at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# doorcheck.py looks for the door opening by reading a reed switch
# it need to be run as sudo for GPIO access
# I usually run this as:
# sudo nohup python doorcheck.py &

import sqlite3
import pygame
import time
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
# Disable GPIO warnings
GPIO.setwarnings(False)
# Set pin 14 as GPIO input
GPIO.setup(14, GPIO.IN)

# connect to the database
# gone.db is for wifi
# macs.db is for bluetooth
conn = sqlite3.connect('macs.db')
# the cursor is c
c = conn.cursor()

# initalize pygame mixer for audio
pygame.mixer.init()


# Function for playing music
def playsong():
    search = 1  # 1 is the last marker
    query = "SELECT * FROM gone WHERE last=? ORDER BY {0}".format('Last')
    c.execute(query, (search,))
    for row in c:
        #print row
        print 'Last person was:', row[4]
        print 'MP3 file is:', row[3]
        # Remove their last person tag
        keyid = row[0]
        c.execute("UPDATE gone SET Last = 0 WHERE key = %d" % keyid)
        conn.commit()  # commit changes to the db

        pygame.mixer.music.load(row[3])  # load the file for the person
        pygame.mixer.music.play()  # play the loaded file

        # Check to see if the song is playing and let it play
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(0)
        print "Sound played! \n"


def timecheck():
    # Get the current hour
    # 24 hour format
    hour = time.localtime()[3]
    print "Hour is", hour
    if 8 < hour < 22:
        playsong()
    else:
        print "It's too late"


# Main Loop
while True:
    # Wait for the rising edge
    # AKA detect when something gets too close
    print "Waiting for sensor event"
    GPIO.wait_for_edge(14, GPIO.RISING)
    print '\033[1;32m Object Detected \033[00m'
    time.sleep(0.1)  # Hack to fix not playing until door is closed
    try:
        # Play the song
        timecheck()
    except sqlite3.OperationalError:
        # The database is in use
        print "\033[91m Error Excepted \033[00m"
        # Try again after a second
        time.sleep(1)
        timecheck()
    except:
        # Some other error
        # Wait 10 seconds then start over
        print "Error"
        time.sleep(10)


GPIO.cleanup()
