import sys
import time
import traceback
import logging
import signal
import math
# Orbit Imports
import orbit_lib
import orbit_schedule as schedule

##########################################
# TODO
##########################################

##########################################
# GLOBALS
##########################################
LOGLEVEL = logging.WARN
LOG = None
RUNNING = True
DESIRED_PITCH = 0.10  # angle in radians to point downward
RELEASED = False
# PARACHUTE_HEIGHT = 1500
# RELEASE_HEIGHT   = 25000
# STABLIZE_HEIGHT  = 2000
PARACHUTE_HEIGHT = -65
RELEASE_HEIGHT = -80
STABLIZE_HEIGHT = -76

STATE_ORDER = {
    "HEALTH_CHECK": {"execute": "execute_health_check", "switch": "switch_health_check"},
    "ASCENT": {"execute": "execute_ascent", "switch": "switch_ascent"},
    "RELEASE": {"execute": "execute_release", "switch": "switch_release"},
    "FLIGHT": {"execute": "execute_flight", "switch": "switch_flight"},
    "PARACHUTE": {"execute": "execute_parachute", "switch": "switch_parachute"},
    "SLEEP": {"execute": "execute_sleep", "switch": "switch_sleep"},
    "RECOVER": {"execute": "execute_recovery", "switch": "switch_recovery"}
}
CURRENT_STATE = "FLIGHT"

ASCENT_TIMES = {}
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
    rollScale = 0.6
    if orbit_lib.LOCATION < STABLIZE_HEIGHT:
        return 0
    tanScale = math.tan(-rad_delta/2)*rollScale  # tan cycles twice over 2pi, so scale rad_delta appropriately
    if tanScale > 1:
        tanScale = 1
    elif tanScale < -1:
        tanScale = -1
    maxAbsRange = math.pi/6  # Maximum absolute roll angle
    return maxAbsRange * tanScale

##########################################
# FUNCTIONS - STATE
##########################################


def scheduleRelease():
    global CURRENT_STATE
    CURRENT_STATE = "RELEASE"


#-----------------------------------
#         HEALTH_CHECK
#-----------------------------------
def execute_health_check():
    time.sleep(5)


def switch_health_check():
    global CURRENT_STATE
    location = orbit_lib.LOCATION
    battStatus = orbit_lib.getBatteryStatus()
    if (location['provider'] != 'gps'):
        LOG.error("Network Provider not sufficient: %s" % location['provider'])
        return
    if (battStatus['level'] < 30):
        LOG.error("Battery too low: %s" % battStatus['level'])
        return
    LOG.info("Health Check Passed")
    orbit_lib.speak("Health Check Complete")
    orbit_lib.sendTextData("Health Good")
    orbit_lib.speak("Beginning Ascent")
    CURRENT_STATE = "ASCENT"


#-----------------------------------
#         ASCENT
#-----------------------------------
def execute_ascent():
    LOG.info("ASCENDING!")
    time.sleep(15)


def switch_ascent():
    global CURRENT_STATE
    batteryStatus = orbit_lib.getBatteryStatus()
    location = orbit_lib.LOCATION

    # Works out an interval for Switching state
    if location['altitude'] > 15000 and ASCENT_TIMES.get('15000') is None:
        ASCENT_TIMES['15000'] = time.time()
    if location['altitude'] > 17000 and ASCENT_TIMES.get('17000') is None:
        ASCENT_TIMES['17000'] = time.time()

    if ASCENT_TIMES.get('17000') and ASCENT_TIMES.get('15000'):
        diff = int(ASCENT_TIMES['17000'] - ASCENT_TIMES['15000'])
        schedule.enableFunc("scheduleRelease", scheduleRelease, diff)

    if batteryStatus['level'] < 50:
        LOG.warn("BATTERY LOW! %s" % batteryStatus['level'])
        orbit_lib.sendTextData("Battery Low. Releasing.")
        CURRENT_STATE = "RELEASE"
    if batteryStatus['temp'] < -200:
        LOG.warn("TEMPERATURE LOW! %s" % batteryStatus['temp'])
        orbit_lib.sendTextData("Temp Low. Releasing.")
        CURRENT_STATE = "RELEASE"

    if location['altitude'] > RELEASE_HEIGHT:
        orbit_lib.sendTextData("Releasing at %s" % location['altitude'])
        CURRENT_STATE = "RELEASE"


#-----------------------------------
#         RELEASE
#-----------------------------------
def execute_release():
    global RELEASED
    LOG.info("RELEASING!")
    orbit_lib.speak("Releasing in")
    time.sleep(3)
    for t in [3, 2, 1]:
        orbit_lib.speak(t)
        time.sleep(1)
    orbit_lib.releaseChord()
    RELEASED = True


def switch_release():
    global CURRENT_STATE
    orbit_lib.speak("Performing Flight")
    CURRENT_STATE = "FLIGHT"


#-----------------------------------
#         FLIGHT
#-----------------------------------
def execute_flight():
    orbit_lib.updateOrientation()
    desired_heading = orbit_lib.getDesiredHeading()
    LOG.debug("Nav Heading: %s " % desired_heading)
    orientation = orbit_lib.ORIENTATION
    LOG.debug("Current Heading: %s " % orientation['yaw'])
    if (desired_heading - orientation['yaw'])**2 < (orientation['yaw'] - desired_heading)**2:
        headingDelta = desired_heading - orientation['yaw']
    else:
        headingDelta = orientation['yaw'] - desired_heading

    LOG.debug("Current Roll: %s" % orientation['roll'])
    desired_roll = getDesiredRoll(headingDelta)
    LOG.debug("Desired Roll: %s" % (desired_roll))
    deltaRoll = desired_roll - orientation['roll']  # required change in current roll
    LOG.debug("Delta Roll: %s" % (deltaRoll))

    LOG.debug("Current Pitch: %s" % orientation['pitch'])
    LOG.debug("Desired Pitch: %s" % (DESIRED_PITCH))

    LOG.info("H[%1.4f -> %1.4f] R[%1.4f -> %1.4f]" % (orientation['yaw'], desired_heading, orientation['roll'], desired_roll))
    deltaPitch = DESIRED_PITCH - orientation['pitch']
    orbit_lib.wing_turnDelta(deltaRoll, deltaPitch)


def switch_flight():
    global CURRENT_STATE
    location = orbit_lib.LOCATION
    if location['altitude'] < PARACHUTE_HEIGHT:
        CURRENT_STATE = "PARACHUTE"


#-----------------------------------
#         PARACHUTE
#-----------------------------------
def execute_parachute():
    orbit_lib.speak("Releasing parachute!")
    orbit_lib.sendTextData("Parachute!")
    orbit_lib.releaseParachute()


def switch_parachute():
    global CURRENT_STATE
    LOG.info("Sleeping..")
    CURRENT_STATE = "SLEEP"


#-----------------------------------
#         SLEEP
#-----------------------------------
def execute_sleep():
    time.sleep(60)


def switch_sleep():
    pass  # Yup..


#-----------------------------------
#         EMERGENCY
#-----------------------------------
def execute_recovery():
    orbit_lib.speak("Recovery!")
    LOG.critical("Attempting Recovery")
    orbit_lib.sendTextData("Recovery!")


def switch_recovery():
    global CURRENT_STATE
    LOG.info("Attempting Recovery")
    if RELEASED:
        CURRENT_STATE = "PARACHUTE"


##########################################
# MAIN
##########################################
def MAIN_LOOP():
    global LOG
    global CURRENT_STATE
    orbit_lib.speak("Loading")
    self = sys.modules[__name__]
    setup_custom_logger("orbit")
    LOG = logging.getLogger("orbit")
    signal.signal(signal.SIGINT, signal_handler)
    orbit_lib.speak("Starting")

    # Ininite loop for state driven work
    while RUNNING:
        try:
            LOG.debug("Current State: %s" % CURRENT_STATE)
            stateData = STATE_ORDER[CURRENT_STATE]
            funcExec = getattr(self, stateData['execute'])
            funcSwitch = getattr(self, stateData['switch'])
            funcExec()
            funcSwitch()
            time.sleep(.01)
        except:
            time.sleep(1)
            LOG.error(traceback.print_exc())
            CURRENT_STATE = "RECOVER"

if __name__ == '__main__':
    orbit_lib.startUp()
    MAIN_LOOP()
    orbit_lib.shutDown()
