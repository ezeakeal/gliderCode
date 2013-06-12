import sys
import types
import android
import datetime, time
import json
import logging
from math import *

import orbit_arduinoController as arduinoController
import orbit_schedule as schedule
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
PHONEHOME   = "0833457414"
STATE       = "OK"
LOG         = logging.getLogger('orbit')
LOCATION    = None
ORIENTATION = [{'yaw':0, 'pitch':0, 'roll':0}, {'yaw':0, 'pitch':0, 'roll':0}, {'yaw':0, 'pitch':0, 'roll':0}] # Some initial headings

ROUTE_COORD = [ # MUST BE IN ORDER OF NORTH -> SOUTH
  (52.254197,-7.181244)
]
WING_PARAM = {
  "LEFT": {"CENTER": 60, "MIN": 40, "MAX": 80}, # Center is IDEALLY midway between MIN and MAX
  "RIGHT": {"CENTER": 120, "MIN": 140, "MAX": 100}
}
DEST_COORD = ROUTE_COORD[0]
##########################################
# FUNCTIONS - UTILITY
##########################################
def startUp():
  DROID.startLocating(5000) # period ms, dist
  DROID.startSensingTimed(1, 100)
  DROID.wakeLockAcquirePartial()
  DROID.batteryStartMonitoring()
  speak("Starting Controller")
  arduinoController.init()
  getLocation()
  schedule.enableFunc("getLocation", getLocation, 10)
  schedule.enableFunc("sendTextData", sendTextData, 60)
  
def shutDown():
  LOG.info("Shutting Down")
  schedule.shutDown()
  DROID.stopSensing()
  DROID.stopLocating()  
  DROID.batteryStopMonitoring()
  DROID.wakeLockRelease()

def alert(msg):
  title = 'fh-orbit warning'
  text = str(msg)
  DROID.dialogCreateAlert(title, text)
  DROID.dialogSetPositiveButtonText('Continue')
  DROID.dialogShow()
  
def setState(newState):
  """Sets the global state which is used for various updates"""
  global STATE
  STATE = newState
  
def speak(text):
  LOG.info("Speaking %s" % text)
  DROID.ttsSpeak("%s" % text)

def logLocation(location, orientation):
  logStr = "%s %s %s %s %s %s %s" % (
    datetime.datetime.now(),
    location['longitude'], location['latitude'], location['altitude'], 
    degrees(orientation[0]), degrees(orientation[1]), degrees(orientation[2])
  )
  LOG.info(logStr)

##########################################
# FUNCTIONS - GET - DROID
##########################################
def getBatteryStatus():
  bathealth = DROID.batteryGetHealth().result
  batlevel = DROID.batteryGetLevel().result
  battemp = DROID.batteryGetTemperature().result
  return {
    "health":bathealth, 
    "level":batlevel, 
    "temp":battemp
  }

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
    if (locMethod in loc.keys()) and (loc[locMethod] != None) and (isinstance(loc[locMethod], dict)) and ("longitude" in loc[locMethod].keys()):
      location = loc[locMethod]
      break
  LOG.info("Setting Location: %s" % location)
  LOCATION = location 

def updateOrientation():
  global ORIENTATION
  orien     = DROID.sensorsReadOrientation().result
  if isinstance(orien, list) and len(orien) >= 2:
    ORIENTATION[0] = ORIENTATION[1]
    ORIENTATION[1] = ORIENTATION[2]
    ORIENTATION[2] = {'yaw':orien[0], 'pitch':orien[1], 'roll':orien[2]}

def getOrientation():
  updateOrientation()
  orientation = {'yaw':0, 'pitch':0, 'roll':0}
  for k in orientation.keys():
    for orientationRecord in ORIENTATION:
      orientation[k] = orientation[k] + orientationRecord[k]
    orientation[k] = orientation[k] / len(ORIENTATION)
  LOG.debug("ORIENTATION AVG: %s" % orientation)
  LOG.debug("ORIENTATION RAW: %s" % ORIENTATION[2])
  return orientation

def updateDestination():
  global DEST_COORD
  for coord in ROUTE_COORD:
    if coord[1] < LOCATION['longitude']:
      if (DEST_COORD != coord):
        LOG.info("Updating Co-ord: ")
        LOG.info(coord)
      DEST_COORD = coord
      break

def getDesiredHeading():
  updateDestination()
  x1, y1 = LOCATION['latitude'], LOCATION['longitude']
  x2, y2 = DEST_COORD[0], DEST_COORD[1]
  lon1, lat1, lon2, lat2 = map(radians, [y1, x1, y2, x2])
  dlon = lon2 - lon1
  dlat = lat2 - lat1
  dLon = lon2 - lon1
  y = sin(dLon) * cos(lat2)
  x = cos(lat1) * sin(lat2) \
      - sin(lat1) * cos(lat2) * cos(dLon)
  rads = atan2(y, x)
  LOG.debug("X1 %s Y2 %s" % (x1, y1))
  LOG.debug("X2 %s Y2 %s" % (x2, y2))
  LOG.debug("ANG %s" % (rads))
  return rads

def sendTextData(msg=""):
  try:
    orient = getOrientation()
    orient = "%02d %02d %02d" % (degrees(orient['yaw']), degrees(orient['pitch']), degrees(orient['roll']))
    loc = "%s %s %s" % (LOCATION['latitude'], LOCATION['longitude'], LOCATION['altitude'])
    dest = "%s %s" % (DEST_COORD[0], DEST_COORD[1])
    battData = getBatteryStatus()
    textMsg = "%s::T:(%s)\nO:(%s)\nL(%s)\nD(%s)\nB(%s)\nC(%s)" % (msg, time.time(), orient, loc, dest, battData['level'], battData['temp'])
    LOG.debug("Sending message to (%s) : %s" % (PHONEHOME, textMsg))
    DROID.smsSend(PHONEHOME,textMsg)
  except:
    pass

##########################################
# FUNCTIONS - SET - DROID
##########################################
def setWingAngle(leftAngle, rightAngle):
  LOG.debug("Setting: %02d %02d" % (leftAngle, rightAngle))
  arduinoController.setWing(leftAngle, rightAngle)

def releaseChord():
  arduinoController.release()

def releaseParachute():
  arduinoController.releaseChute()

def wing_turnDelta(rollDelta, pitchDelta):
  # rollDelta and pitchDelta are both Radian deltas
  maxAbsPitchRange = pi/2
  if pitchDelta > maxAbsPitchRange:
    pitchDelta = maxAbsPitchRange
  elif pitchDelta < (maxAbsPitchRange * -1):
    pitchDelta = (maxAbsPitchRange * -1)
  pitchDeltaAngle = -sin(pitchDelta)

  initLeftCenter   = WING_PARAM['LEFT']['CENTER']
  initRightCenter  = WING_PARAM['RIGHT']['CENTER']
  leftPitchOffset  = pitchDeltaAngle*(initLeftCenter - WING_PARAM['LEFT']['MIN'])
  rightPitchOffset = pitchDeltaAngle*(initRightCenter - WING_PARAM['RIGHT']['MIN'])
  LOG.debug("Adjusting Wing Center %s %s" % (leftPitchOffset, rightPitchOffset))
  leftCenter       = initLeftCenter + leftPitchOffset
  rightCenter      = initRightCenter + rightPitchOffset

  LOG.debug("RollDelta %s (ANG %s) PitchDelta %s (ANG %s)" % (rollDelta, rollDelta, pitchDelta, pitchDeltaAngle))
  if rollDelta > 0:
    leftWingOffset  = -rollDelta*(leftCenter - WING_PARAM['LEFT']['MIN'])
    rightWingOffset = -rollDelta*(rightCenter - WING_PARAM['RIGHT']['MAX'])
  else:
    leftWingOffset  = rollDelta*(leftCenter - WING_PARAM['LEFT']['MAX'])
    rightWingOffset = rollDelta*(rightCenter - WING_PARAM['RIGHT']['MIN'])

  leftWingAngle = leftCenter + leftWingOffset
  rightWingAngle = rightCenter + rightWingOffset

  LOG.debug("Adjusting Wing Angles %s %s" % (leftWingOffset, -rightWingOffset))
  setWingAngle(leftWingAngle, rightWingAngle)