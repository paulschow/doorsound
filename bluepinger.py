#!/usr/bin/env python

#bluepinger.py for doorsound
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

# Modified from doorpinger.py
# This one uses bluetooth instead of wifi

# You have to pair the devices and add them to macs.db

# Note: Requires sqlite3 and python bluez

import time
import sqlite3
import subprocess
import re
import bluetooth
import pygame
import multiprocessing
import RPi.GPIO as GPIO


# connect to the database
# Allow multiple threads to access the db
conn = sqlite3.connect('macs.db', check_same_thread=False)
# the cursor is c
c = conn.cursor()

# Use BCM GPIO numbering
GPIO.setmode(GPIO.BCM)
# Disable GPIO warnings
GPIO.setwarnings(False)
# Status LED is in pin 15
GPIO.setup(15, GPIO.OUT)
# Set pin 14 as GPIO input
GPIO.setup(14, GPIO.IN)

#log = open('track1.txt', 'w')  # open a text file for logging
#print log  # print what the log file is
#log.write('Time,IP,Ping\n')  # write to log

# initalize pygame mixer for audio
pygame.mixer.init()

# Set up shared status variable
gstatus = multiprocessing.Value('i', 0)

c.execute("SELECT * FROM gone")
rows = c.fetchall()
countrow = len(rows)  # Counts the number of rows
print "Number of Rows:", countrow


# Function for door detection thread
def door_callback(channel):
    print "Event detected"
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
    #except:
        # Some other error
        # Wait 10 seconds then start over
        #print "Error"
        #time.sleep(10)


# This starts the door thread
GPIO.add_event_detect(14, GPIO.RISING, callback=door_callback)


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


# Function to make sure music isn't being played too late or early
def timecheck():
    hour = time.localtime()[3]
    # Get the current hour
    # 24 hour format
    print "Hour is", hour
    if 8 < hour < 22:
        playsong()
    else:
        print "It's too late"


def newping(btaddr):
# Adapted from
# https://github.com/jeffbryner/bluetoothscreenlock
# Basically just tries to connect to the device
# And reports if it is there or not
    btsocket = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    #print("searching for device..."), btaddr
    try:
        btsocket.connect((btaddr, 3))
        if btsocket.send("hey"):
            #print("Device Found")
            gstatus.value = 1
            return 1
            btsocket.close()
    except bluetooth.btcommon.BluetoothError:
        print("Bluetooth Error. Is device paired?")
        # Whatever, they're still there
        # Probably
        gstatus.value = 1
        return 0


def pingtimer(mac):
# This is a pretty awful use of multiprocessing to time the pings
# But it works pretty well
# Maybe later I will use pools or something
    print "Connecting..."
    p = multiprocessing.Process(target=newping, name="ping", args=(mac,))
    p.start()
    p.join(4)  # Timeout after seconds
    #print result
    if p.is_alive():
        print "Connection Timed Out"
        # Terminate foo
        gstatus.value = 0
        p.terminate()
        p.join()


def l2ping(phonemac):
# Old Bluetooth ping command
# Uses l2ping linux command
# Returns a 0 if mac is gone
# Returns a 1 if mac is here
# This takes ~5 seconds per device, there's a better way
    p = subprocess.Popen(["sudo", "l2ping", "-t 1", "-c 1", phonemac],
    stdout=subprocess.PIPE)
    # run the l2ping (bluetooth ping) command for phonemac
    # with timeout 1 second
    # and count 1 (a single ping)
    (ping, err) = p.communicate()
    return regping(ping)


def regping(ping):
# URL that generated this code:
# http://txt2re.com
# Uses regular expressions to look through l2ping result
# This is pretty awful, but it works

    txt = str(ping)

    re1 = '.*?'     # Non-greedy match on filler
    re2 = '( 1 received)'     # Command Seperated Values 1

    rg = re.compile(re1 + re2, re.IGNORECASE | re.DOTALL)
    m = rg.search(txt)
    if m:
        csv1 = m.group(1)
        #print "(" + csv1 + ")" + "\n"
    try:
        if csv1 == " 1 received":
            print "Ping received"
            return 1
        else:
            print "How did you even get this error"
            return 0
    except NameError:
        print "No Ping received"
        return 0


# function for marking someone as gone in the db
def db_gone(keyid, prestatus):
    if prestatus == 0:
        # Already marked as gone
        # Do nothing
        return
    else:
        # They where here before
        # Mark them as gone
        #print "key = %d" % keyid
        #c.execute("SELECT * FROM gone")
        # Also mark them as not being last
        c.execute("UPDATE gone SET Last = 0 WHERE key = %d" % keyid)
        c.execute("UPDATE gone SET Status = 0 WHERE key = %d" % keyid)
        conn.commit()  # commit changes to the db
        # Turn the LED
        print "LED OFF"
        GPIO.output(15, GPIO. LOW)
        #print "Total number of rows updated :", conn.total_changes


def db_here(keyid, prestatus):
    #print "key = %d" % keyid
    #print "Previous Status is  = %d" % prestatus
    if prestatus == 0:
        # They just showed up!
        print '\033[1;32m Person Arrived \033[00m'
        # Set everyone else to not last
        c.execute("UPDATE gone SET Last = 0 WHERE key != %d" % keyid)
        # Set them as the last person
        c.execute("UPDATE gone SET Last = 1 WHERE key = %d" % keyid)
        # Turn on LED
        time.sleep(1)  # Hack to keep people from opening the door too fast
        print "LED %d ON" % (15)
        GPIO.output(15, GPIO. HIGH)
        conn.commit()  # commit changes to the db
    else:
        print "They were already here"
        # Turn the LED
        print "LED OFF"
        GPIO.output(15, GPIO. LOW)

    #c.execute("SELECT * FROM gone")
    c.execute("UPDATE gone SET Status = 1 WHERE key = %d" % keyid)
    conn.commit()  # commit changes to the db
    #print "Total number of rows updated :", conn.total_changes


#Main loop
while True:
    for row in rows:
        #print "MAC = %s" % row[5]
        #print "Name = %s" % row[4]
        #status = l2ping(row[5])  # ping the MAC, get status
        #status = newping(row[5])  # ping the MAC, get status
        pingtimer(row[5])  # ping the MAC, get status
        if gstatus.value == 1:
            #print "They're here!"
            print "\033[94m %s is Here \033[00m" % row[4]
            # Send the row to db_here
            db_here(row[0], row[2])
            print " "
            #print "Total number of rows updated :", conn.total_changes
        else:
            #print "Not Here"
            # Send the row to db_gone
            print "\033[91m %s is Not Here \033[00m" % row[4]
            print " "
            db_gone(row[0], row[2])
    print "\033[33m Done \033[00m \n"
