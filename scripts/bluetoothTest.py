import android
import bluetooth

TARGET = None
SOCK   = None
droid  = android.Android()

def init(target="00:13:03:14:16:68"):
  global SOCK
  global TARGET
  SOCK    = None
  TARGET  = target
  sConnect()
  

def disconnect():
  if SOCK:
    try: 
      SOCK.close()
    except: 
      print "Closing SOCK failed"
    

def sConnect():
  global SOCK
  port = 1
  print "Creating Socket"
  SOCK = bluetooth.BluetoothSocket( bluetooth.RFCOMM )
  print "Connecting Socket %s %s" % (TARGET, port)
  SOCK.connect((TARGET, port))


def send(cStr):
  print "SENDING: %s" % cStr
  try:
    SOCK.sendall("%s;" % cStr)
  except Exception, e:
    print "Bluetooth Communication Failed!"
    print e
    disconnect()
    sConnect()

init()
while True:
  message = droid.dialogGetInput('TTS', 'Send String:').result
  send(message)

