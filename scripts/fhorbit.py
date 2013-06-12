import sys
import types
import time
import traceback
import logging
import signal
import sys
import math
# Orbit Imports
import orbit_lib

##########################################
# TODO
##########################################

##########################################
# GLOBALS
##########################################
LOGLEVEL          = logging.WARN
LOG               = None
RUNNING           = True
DESIRED_PITCH     = 0.05
RELEASED          = False

STATE_ORDER = {
  "HEALTH_CHECK"  : {"execute":"execute_health_check", "switch":"switch_health_check"},
  "ASCENT"        : {"execute":"execute_ascent", "switch":"switch_ascent"},                   
  "RELEASE"       : {"execute":"execute_release", "switch":"switch_release"},                
  "FLIGHT"        : {"execute":"execute_flight", "switch":"switch_flight"},                    
  "PARACHUTE"     : {"execute":"execute_parachute", "switch":"switch_parachute"},
  "RECOVER"       : {"execute":"execute_recovery", "switch":"switch_recovery"}
}
CURRENT_STATE = "FLIGHT"

PERSIST_DATA = {}
##########################################
# FUNCTIONS - UTIL
##########################################
def setup_custom_logger(name):
  formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
  handler = logging.StreamHandler()
  handler.setFormatter(formatter)
  logger = logging.getLogger(name)
  logger.setLevel(LOGLEVEL)
  logger.addHandler(handler)
  return logger

def signal_handler(signal, frame):
  global RUNNING
  RUNNING = False

def getDesiredRoll(rad_delta):
  tanSigma = 2
  tanScale = math.tan(rad_delta/2)/tanSigma # tan cycles twice over 2pi, so scale rad_delta appropriately
  if tanScale > 1:
    tanScale = 1 
  elif tanScale < -1:
    tanScale = -1
  maxAbsRange = math.pi/3 # Maximum absolute roll angle
  return maxAbsRange * tanScale

##########################################
# FUNCTIONS - STATE
##########################################

def scheduleRelease():
  global CURRENT_STATE
  CURRENT_STATE = "RELEASE"

#-----------------------------------
#         Health Check
#-----------------------------------
def execute_health_check():
  time.sleep(5)
  
def switch_health_check():
  global CURRENT_STATE
  location = orbit_lib.getLocation()
  orientation = orbit_lib.getOrientation()
  battStatus = orbit_lib.getBatteryStatus()
  if (location['provider'] != 'gps'):
    LOG.error("Network Provider not sufficient: %s" % location['provider'])  
    return
  if (battStatus['level'] < 85):
    LOG.error("Battery too low: %s" % battStatus['level'])  
    return
  LOG.info("Health Check Passed")
  orbit_lib.speak("Health Check Complete")
  orbit_lib.sendTextData("Health Good")
  orbit_lib.speak("Beginning Ascent")
  CURRENT_STATE = "ASCENT"
    
#-----------------------------------
#         Ascent
#-----------------------------------
def execute_ascent():
  LOG.info("ASCENDING!")
  time.sleep(60)

def switch_ascent():
  global CURRENT_STATE
  time.sleep(60)
  battLevel = DROID.batteryGetLevel().result
  battTempt = DROID.batteryGetTemperature().result
  location  = orbit_lib.getLocation()
  if location['altitude'] > 15000 and PERSIST_DATA.get('15000') == None:
    PERSIST_DATA['15000'] = time.time()
  if location['altitude'] > 17000 and PERSIST_DATA.get('17000') == None:
    PERSIST_DATA['17000'] = time.time()
  if PERSIST_DATA.get('17000') and PERSIST_DATA.get('15000'):
    diff = int(PERSIST_DATA['17000'] - PERSIST_DATA['15000'])
    schedule.enableFunc("scheduleRelease", scheduleRelease, diff)
  if battLevel < 50:
    LOG.warn("BATTERY LOW! %s" % battLevel)
    orbit_lib.sendTextData("Battery Low. Releasing.")
    CURRENT_STATE = "RELEASE"
  if battTempt < -200:
    LOG.warn("TEMPERATURE LOW! %s" % battTempt)
    orbit_lib.sendTextData("Temp Low. Releasing.")
    CURRENT_STATE = "RELEASE"
  
  if STATE['ascent_complete']:
    LOG.info("Ascent Complete")
    
#-----------------------------------
#         Release
#-----------------------------------
def execute_release():
  global RELEASED
  LOG.info("RELEASING!")
  orbit_lib.speak("Releasing in")
  time.sleep(3)
  for t in [5,4,3,2,1]:
    if t > 1: orbit_lib.speak(t)
    time.sleep(1)
  orbit_lib.releaseChord()
  RELEASED = True

def switch_release():
  global CURRENT_STATE
  orbit_lib.speak("Performing Flight")
  CURRENT_STATE = "FLIGHT"
  
#-----------------------------------
#         Guided Flight
#-----------------------------------
def execute_flight():
  desired_heading = orbit_lib.getDesiredHeading()
  LOG.debug("Nav Heading: %s " % desired_heading)
  orientation = orbit_lib.getOrientation()
  LOG.debug("Current Heading: %s " % orientation['yaw'])
  headingDelta = desired_heading - orientation['yaw']
  
  LOG.debug("Current Roll: %s" % orientation['roll'])
  desired_roll = getDesiredRoll(headingDelta)
  LOG.debug("Desired Roll: %s" % (desired_roll)) 
  deltaRoll = desired_roll - orientation['roll'] # required change in current roll
  LOG.debug("Delta Roll: %s" % (deltaRoll)) 

  LOG.debug("Current Pitch: %s" % orientation['pitch'])
  LOG.debug("Desired Pitch: %s" % (DESIRED_PITCH)) 
  deltaPitch = DESIRED_PITCH - orientation['pitch']
  orbit_lib.wing_turnDelta(deltaRoll, deltaPitch)
  
def switch_flight():
  global CURRENT_STATE

#-----------------------------------
#         PARACHUTE
#-----------------------------------
def execute_parachute():
  orbit_lib.speak("Releasing parachute!")
  location = orbit_lib.getLocation()
  orientation = orbit_lib.getOrientation()
  orbit_lib.broadcastLocation()
  orbit_lib.releaseParachute()

def switch_recovery():
  global CURRENT_STATE
  LOG.info("Attempting Recovery")
  if RELEASED:
    CURRENT_STATE = "PARACHUTE"
  else:
    CURRENT_STATE = "RELEASE"


#-----------------------------------
#         EMERGENCY
#-----------------------------------
def execute_recovery():
  orbit_lib.speak("Recovery!")
  LOG.critical("Attempting Recovery")
  location = orbit_lib.getLocation()
  orientation = orbit_lib.getOrientation()
  orbit_lib.broadcastLocation()

def switch_recovery():
  global CURRENT_STATE
  LOG.info("Attempting Recovery")
  if RELEASED:
    CURRENT_STATE = "PARACHUTE"
  else:
    CURRENT_STATE = "RELEASE"


##########################################
# MAIN
##########################################       
def MAIN_LOOP():
  global LOG
  self = sys.modules[__name__]
  setup_custom_logger("orbit")
  LOG = logging.getLogger("orbit")
  signal.signal(signal.SIGINT, signal_handler)
  orbit_lib.speak("Initialized")
  
  # Ininite loop for state driven work
  while RUNNING:
    try:
      LOG.debug("Current State: %s" % CURRENT_STATE)
      stateData = STATE_ORDER[CURRENT_STATE]
      funcExec = getattr(self, stateData['execute'])
      eResponse = funcExec()
      funcSwitch = getattr(self, stateData['switch'])
      sResponse = funcSwitch()
      time.sleep(.1)
    except:
      LOG.error(traceback.print_exc())
      orbit_lib.setState("RECOVER")

if __name__ == '__main__':
  orbit_lib.startUp()
  MAIN_LOOP()
  orbit_lib.shutDown()
    