import sys
import types
import android
import datetime, time
import json
import logging
from math import *

##########################################
# TODO
##########################################
"""
readSignalStrengths() to determine when to start sending messages!
readBatteryData() Test this for emergency text conditions
batteryGetHealth() Once not OK, send message!
batteryGetLevel() Once too low, emergency
batteryGetTemperature? (batteryStartMonitoring)
"""
##########################################
# GLOBALS
##########################################
DROID       = android.Android()
LOCATION    = None

ROUTE_COORD = [ # MUST BE IN ORDER OF NORTH -> SOUTH
  (52.222805,-7.530362)
]

##########################################
# FUNCTIONS - UTILITY
##########################################
def startUp():
  DROID.startLocating(5000) # period ms, dist
  DROID.startSensingTimed(1, 100)
  DROID.wakeLockAcquirePartial()
  DROID.batteryStartMonitoring()
  
def getLocation():
  global LOCATION
  location = {}
  event = DROID.eventWaitFor('location',10)
  # Get a location or get lastKNown
  loc = DROID.readLocation().result
  if loc == {}:
    loc = DROID.getLastKnownLocation().result        
    locType = "lastknown"
  # Iterate through it and get back some location data
  for locMethod in ["gps", "network"]:
    if (  isinstance(loc, dict) and
          locMethod in loc.keys() and 
          loc[locMethod] != None and 
          isinstance(loc[locMethod], dict) and 
          "longitude" in loc[locMethod].keys()):
      location = loc[locMethod]
      break
  LOCATION = location
  print location 

startUp()
while True:
  getLocation()
  time.sleep(3)