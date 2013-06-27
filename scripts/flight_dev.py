import sys
import types
import time
import traceback
import logging
import signal
import sys
import math
# Orbit Imports
import fhorbit

##########################################
# MAIN
##########################################       
def MAIN_LOOP():
  fhorbit.orbit_lib.speak("Loading")
  fhorbit.setup_custom_logger("orbit")
  fhorbit.LOG = logging.getLogger("orbit")
  fhorbit.orbit_lib.speak("Starting")
  fhorbit.LOGLEVEL = logging.DEBUG
  
  # Ininite loop for state driven work
  while fhorbit.RUNNING:
    try:
      fhorbit.execute_flight()
      fhorbit.switch_flight()
      time.sleep(.01)
    except:
      time.sleep(1)
      fhorbit.LOG.error(traceback.print_exc())
      
if __name__ == '__main__':
  fhorbit.orbit_lib.arduinoController.FAKE = True
  fhorbit.orbit_lib.startUp()
  MAIN_LOOP()
  fhorbit.orbit_lib.shutDown()
    