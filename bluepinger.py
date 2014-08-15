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
# or use another db with the -db option

# Note: Requires sqlite3 and python bluez
# Requires root because of GPIO
# I usually run this as sudo nohup ./bluepinger.py &

import time
import sqlite3
import bluetooth
import pygame
import multiprocessing
import argparse

try:
    # Try to use GPIO
    import RPi.GPIO as GPIO
except RuntimeError:
    print "Error: You need to run this as root"
    quit()

# Parse arguements
parser = argparse.ArgumentParser(description='Play sound when door is opened')

# Make a mutually exclusive group so conflicting options can't be used
group = parser.add_mutually_exclusive_group()
group.add_argument("-v", "--verbose", help="Verbose mode",
action="store_true")
group.add_argument("-vv", "--veryverbose", help="Very verbose mode",
action="store_true")
group.add_argument("-q", "--quiet", help="Quiet mode, only show errors",
action="store_true")

parser.add_argument("-db", "--database",
help="Database file. Default is macs.db", default="macs.db")

parser.add_argument("-sp", "--switchpin",
help="Reed switch pin. Default is 14", type=int, default=14)

parser.add_argument("-lp", "--ledpin",
help="Led pin. Default is 15", type=int, default=15)

parser.add_argument("-t", "--timeout",
help="Bluetooth connection timout in seconds. Default is 4", type=int,
default=4)

parser.add_argument("-st", "--starttime",
help="Hour of day when sound is allowed. Default is 8", type=int,
default=8)

parser.add_argument("-et", "--endtime",
help="Hour of day when sound stops. Default is 22 (10:00 PM)", type=int,
default=22)

args = parser.parse_args()
if args.verbose:
    print "Verbose mode"
if args.veryverbose:
    # Very verbose mode includes verbose mode
    args.verbose = True
    print "Very verbose mode"
#if args.quiet:
    #print "Quiet mode"
if args.database != "macs.db":
    print "Database file is:", args.database
if args.switchpin != 14:
    print "Input pin is", args.switchpin
if args.ledpin != 15:
    print "LED pin is", args.ledpin
if args.timeout != 4:
    print "Bluetooth connection timeout is", args.timeout

# connect to the database
# Allow multiple threads to access the db
conn = sqlite3.connect(args.database, check_same_thread=False)


# Use BCM GPIO numbering
GPIO.setmode(GPIO.BCM)
# Disable GPIO warnings
GPIO.setwarnings(False)
# Status LED is in pin 15
# Or whatever pin is made with -lp option
GPIO.setup(args.ledpin, GPIO.OUT)
# Set pin 14 as GPIO input
# Or whatever pin is made with -sp option
GPIO.setup(args.switchpin, GPIO.IN)

#log = open('track1.txt', 'w')  # open a text file for logging
#print log  # print what the log file is
#log.write('Time,IP,Ping\n')  # write to log

# initalize pygame mixer for audio
pygame.mixer.init()

# Set up shared status variable
gstatus = multiprocessing.Value('i', 0)


# Function for door detection thread
def door_callback(channel):
    if args.quiet is False:
        print '\033[1;32m Object Detected \033[00m'
    time.sleep(0.1)  # Hack to fix not playing until door is closed
    try:
        # Play the song
        timecheck()
    except sqlite3.OperationalError:
        # The database is in use
        print "\033[91m Error Excepted: DB in use \033[00m"
        # Try again after a second
        time.sleep(1)
        timecheck()
    #except:
        # Some other error
        # Wait 10 seconds then start over
        #print "Error"
        #time.sleep(10)


# Function for playing music
def playsong():
    c = conn.cursor()
    c.execute("SELECT * FROM gone")
    rows = c.fetchall()
    countrow = len(rows)  # Counts the number of rows
    if args.verbose:
        print "Number of Rows:", countrow
    search = 1  # 1 is the last marker
    query = "SELECT * FROM gone WHERE last=? ORDER BY {0}".format('Last')
    c.execute(query, (search,))
    for row in c:
        #print row
        if args.quiet is False:
            print 'Last person was:', row[4]
            print 'MP3 file is:', row[3]
        # Remove their last person tag
        keyid = row[0]
        c.execute("UPDATE gone SET Last = 0 WHERE key = %d" % keyid)
        conn.commit()  # commit changes to the db
        if args.veryverbose:
            print "Total number of rows updated :", conn.total_changes

        pygame.mixer.music.load(row[3])  # load the file for the person
        pygame.mixer.music.play()  # play the loaded file

        # Check to see if the song is playing and let it play
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(0)
        if args.quiet is False:
            print "Sound played! \n"


# Function to make sure music isn't being played too late or early
def timecheck():
    hour = time.localtime()[3]
    # Get the current hour
    # 24 hour format
    if args.verbose:
        print "Hour is", hour
    if args.starttime < hour < args.endtime:
        playsong()
    else:
        if args.quiet is False:
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
    if args.verbose:
        print "Connecting..."
    p = multiprocessing.Process(target=newping, name="ping", args=(mac,))
    p.start()
    p.join(args.timeout)  # Timeout after seconds
    if p.is_alive():
        if args.verbose:
            print "Connection Timed Out"
        # Terminate connection
        gstatus.value = 0
        p.terminate()
        p.join()


# function for marking someone as gone in the db
def db_gone(keyid, prestatus):
    if prestatus == 0:
        # Already marked as gone
        # Do nothing
        return
    else:
        # They where here before
        # Mark them as gone
        # Also mark them as not being last
        c.execute("UPDATE gone SET Last = 0 WHERE key = %d" % keyid)
        c.execute("UPDATE gone SET Status = 0 WHERE key = %d" % keyid)
        conn.commit()  # commit changes to the db
        # Turn the LED
        if args.verbose:
            print "LED OFF"
        GPIO.output(15, GPIO. LOW)
        if args.veryverbose:
            print "Total number of rows updated :", conn.total_changes


def db_here(keyid, prestatus):
    if prestatus == 0:
        # They just showed up!
        if args.quiet is False:
            print '\033[1;32m Person Arrived \033[00m'
        # Set everyone else to not last
        c.execute("UPDATE gone SET Last = 0 WHERE key != %d" % keyid)
        # Set them as the last person
        c.execute("UPDATE gone SET Last = 1 WHERE key = %d" % keyid)
        # Turn on LED
        time.sleep(1)  # Hack to keep people from opening the door too fast
        if args.verbose:
            print "LED %d ON" % (15)
        GPIO.output(15, GPIO. HIGH)
        conn.commit()  # commit changes to the db
        if args.veryverbose:
            print "Total number of rows updated :", conn.total_changes
    else:
        if args.quiet is False:
            print "They were already here"
        # Turn off the LED
        if args.verbose:
            print "LED OFF"
        GPIO.output(15, GPIO. LOW)

    #c.execute("SELECT * FROM gone")
    c.execute("UPDATE gone SET Status = 1 WHERE key = %d" % keyid)
    conn.commit()  # commit changes to the db
    if args.veryverbose:
        print "Total number of rows updated :", conn.total_changes


# This starts the door thread
GPIO.add_event_detect(14, GPIO.RISING, callback=door_callback)

#Main loop
while True:
    c = conn.cursor()
    c.execute("SELECT * FROM gone")
    rows = c.fetchall()
    countrow = len(rows)  # Counts the number of rows
    if args.verbose:
        print "Number of Rows:", countrow
    for row in rows:
        if args.verbose:
            print "MAC = %s" % row[5]
            print "Name = %s" % row[4]
        pingtimer(row[5])  # ping the MAC, get status
        if gstatus.value == 1:
            #print "They're here!"
            if args.quiet is False:
                print "\033[94m %s is Here \033[00m" % row[4]
            # Send the row to db_here
            db_here(row[0], row[2])
            if args.quiet is False:
                print " "  # Print blank line
        else:
            if args.quiet is False:
                print "\033[91m %s is Not Here \033[00m" % row[4]
                print " "  # Print blank line
            # Send the row to db_gone
            db_gone(row[0], row[2])
    if args.quiet is False:
        print "\033[33m Done \033[00m \n"