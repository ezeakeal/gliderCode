import sys
import datetime, time
import math
import logging
import bluetooth

##########################################
# TODO
##########################################

##########################################
# GLOBALS
##########################################
SERVOTICK = 0.05
SOCK      = None
TARGET    = None
LOG       = logging.getLogger('orbit')

##########################################
# FUNCTIONS
##########################################
# Initialize the serial connection - then use some commands I saw somewhere once
def init(target="00:13:03:14:16:68"):
  global SOCK
  global TARGET
  SOCK    = None
  TARGET  = target
  sConnect()
  LOG.debug("Initialized Flight Controller")
  
def disconnect():
  if SOCK:
    try: 
      SOCK.close()
    except: 
      LOG.info("Closing SOCK failed")
    
def sConnect():
  global SOCK
  disconnect()
  try:
    LOG.debug("Creating Socket")
    server_sock = bluetooth.BluetoothSocket( bluetooth.RFCOMM )
    SOCK = bluetooth.BluetoothSocket( bluetooth.RFCOMM )
    LOG.info("Connecting Socket %s %s" % (TARGET, 1))
    SOCK.connect((TARGET, 1))
  except Exception, e:
    LOG.critical(e)
    print e
    LOG.critical("Reconnecting in 3 seconds")
    time.sleep(3)
    sConnect()


def send(cStr):
  LOG.debug("SENDING: %s" % cStr)
  try:
    SOCK.sendall("%s;" % cStr)
    dat =  SOCK.recv(1024)
  except Exception, e:
    LOG.critical("Bluetooth Communication Failed!")
    LOG.critical(e)
    sConnect()
    
def setWing(angleLeft, angleRight):
  LOG.debug("Setting Wing Angle")
  send("W:%s:%s" % (angleLeft, angleRight))
  time.sleep(SERVOTICK) # sleep a bit

def release():
  LOG.debug("Releasing")
  send("D:")
  time.sleep(SERVOTICK) # sleep a bit
    
def releaseChute():
  LOG.debug("Releasing Parachute")
  send("P:")
  time.sleep(SERVOTICK) # sleep a bit
    
def sendRadio(rString):
  LOG.debug("Sending Radio Packet: %s" % rString)
  send("R:%s" % rString)
  
def stop():
  SOCK.close()
  LOG.info("Closing Module")
