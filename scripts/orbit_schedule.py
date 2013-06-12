import sys
import datetime, time
import json
import logging
import threading

#####################################
# GLOBALS
#####################################
STATE_DATA = {}
FUNC_STACK = {}
LOG = logging.getLogger("orbit")

#####################################
# FUNCTIONS
#####################################
def init():
  LOG.info("Initializing the Scheduler")

def shutDown():
  disableAllFunc()
  LOG.info("Shutting Down")

def enableFunc(funcName, function, interval, count=0):
  global FUNC_STACK

  # Cancel Thread if it already exists.
  if FUNC_STACK.get(funcName) and FUNC_STACK.get(funcName).get("THREAD"):
    FUNC_STACK[funcName]["THREAD"].cancel()
  
  # Dont worry about checking if a function is already enabled, as the thread would have died. Rather than updating the spec, just run a new thread.
  FUNC_STACK[funcName] = {
    "COUNT": count,
    "INTERVAL": interval,
    "FUNCTION": function,
    "THREAD": threading.Timer(
      interval,
      revive, [funcName]
    )
  }
  LOG.debug("Enabling New Thread:\n%s %s" % (funcName, FUNC_STACK[funcName]))
  FUNC_STACK[funcName]["THREAD"].start()

def disableFunc(funcName):
  global FUNC_STACK
  if funcName in FUNC_STACK.keys():
    thread = FUNC_STACK[funcName].get("THREAD")
    if thread: thread.cancel()
    del FUNC_STACK[funcName]

def disableAllFunc():
  global FUNC_STACK
  for funcName in FUNC_STACK:
    thread = FUNC_STACK[funcName].get("THREAD")
    if thread: thread.cancel()
  FUNC_STACK = {}

#------------------------------------
# THREAD FOR TICKING AND CHECKING EVENTS
# Calls itself again
#------------------------------------
def revive(funcName):
  global FUNC_STACK
  FUNC_STACK[funcName]["FUNCTION"]()
  funcSpec = FUNC_STACK.get(funcName, None)
  if funcSpec:
    count = funcSpec["COUNT"]
    func = funcSpec["FUNCTION"]
    if count != 1:
      FUNC_STACK[funcName]["COUNT"] = count - 1
      funcSpec["THREAD"].cancel() # Kill off this thread just in case..
      enableFunc(funcName, func, funcSpec["INTERVAL"]) # REVIVE!
#------------------------------------