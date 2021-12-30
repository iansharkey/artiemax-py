try:
  from queue import Queue
except ImportError:
  from Queue import Queue
from artiemax.socket_handler import SocketHandler
import time
import string
import random
import sys
import json
try:
  import urllib.request as request
except ImportError:
  import urllib2 as request

_sentinel = object()

class Artiemax:
  """
  Artie Max interface object.

  This class is based on the mirobot-py code, with some updates for Artie Max functions
  and changes to support chained methods.

  An example usage:
  >>> import artiemax
  >>> with artiemax.Artiemax() as artie:
  >>>   artie.inches().forward(4).left(45).beep(3)
  >>>

  Parameters
  ----------

  address: string
     Network address of the Artie Max robot; defaults to '192.168.4.1'
  debug: boolean
     Flag for outputting debug logs to standard output

  """
  def __init__(self, address = None, debug = False):
    # Initialisation for the id field
    self.nonce  = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(4))
    self.n      = 0
    self.debug = debug
    self.distance_scale = 1.

    # callbacks
    self.__on_error    = None
    self.__on_collide  = None
    self.__on_follow   = None

    if address is None:
      address = '192.168.4.1'
    self.connect(address)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    self.disconnect()
    
  def connect(self, address):
    # Set up the socket handling
    self.__send_q = Queue()
    self.recv_q = Queue()
    self.socket = SocketHandler(address, self.__send_q, self.recv_q, debug=self.debug, sentinel = _sentinel)
    self.socket.start()
    # get the version once connected
    self.version   = self.__send('version')

  def inches(self):
    self.distanceScale = 25.4
    return self

  def cm(self):
    self.distanceScale = 10.
    return self

  def mm(self):
    self.distanceScale = 1.
    return self
    
  def errorNotify(self, on_error):
    self.__on_error = on_error

  def collideNotify(self, on_collide):
    enabled = bool(on_collide)
    self.__on_collide = on_collide
    self.__send('collideNotify', ('false','true')[enabled])

  def followNotify(self, on_follow):
    enabled = bool(on_follow)
    self.__on_follow = on_follow
    self.__send('followNotify', ('false','true')[enabled])

  def ping(self):
    return self.__send('ping') or self

  def arc(self, distance, wangle):
    return self.__send('arc', [distance*self.distanceScale, wangle]) or self
  
  def uptime(self):
    return self.__send('uptime')

  def forward(self, distance):
    return self.__send('forward', distance*self.distanceScale) or self

  def back(self, distance):
    return self.__send('back',    distance*self.distanceScale) or self

  def left(self, degrees):
    return self.__send('left',    degrees) or self

  def right(self, degrees):
    return self.__send('right',   degrees) or self

  def penup(self):
    return self.__send('penup') or self

  def pendown(self, pen_num):
    return self.__send('pendown', pen_num) or self

  def beep(self, sound_num):
    return self.__send('beep', sound_num) or self

  def setLed(self, led_num, rgb):
    return self.__send('leds', [led_num, rgb]) or self

  def setAllLeds(self, rgb):
    return self.setLed(6, rgb)

  def colorState(self):
    return self.__send('colorState') 
  
  def findColour(self, rgb):
    return self.__send('findColour', rgb)
  
  def follow(self, enabled):
    enabled = bool(enabled)
    return self.__send('follow', enabled) or self
  
  def collideState(self):
    return self.__send('collideState')

  def followState(self):
    return self.__send('followState')

  def getVoltage(self):
    return self.__send('getVoltage')
  
  def disconnect(self):
    self.__send_q.put(_sentinel)

  def __send(self, cmd, arg = None, timeout = 5000):
    # Assemble the message
    msg = {'cmd': cmd}
    if (arg is not None):
      msg['arg'] = arg

    # Send the message and handle exceptions
    try:
      return self.__send_or_raise(msg, timeout)
    except Exception as x:
      if not self.__on_error:
        raise
      return self.__on_error(x, msg, timeout, self)

  def __send_or_raise(self, msg, timeout):
    msg_id = msg['id'] = self.generate_id()
    self.__send_q.put(msg)
    deadline = timeout + time.time()
    accepted = False
    while True:
      try:
        timeout = max(1, deadline - time.time())
        #import pdb; pdb.set_trace()
        incoming = self.recv_q.get(block = True, timeout = timeout)
      except KeyboardInterrupt as e:
        self.disconnect()
        raise e
      except: # .get raises "Empty"
        if (accepted):
          raise IOError("Mirobot timed out awaiting completion of %r" % (msg,))
        raise IOError("Mirobot timed out awaiting acceptance of %r" % (msg,))

      try:
        rx_id = incoming.get('id','???')
        if rx_id != msg_id:
          if (rx_id == 'collide'):
            self.__collide(incoming)
            continue
          if (rx_id == 'follow'):
            self.__follow(incoming)
            continue
          raise IOError("Received message ID (%s) does not match expected (%s)" % (rx_id, msg_id))
        rx_status = incoming.get('status','???')
        if rx_status == 'accepted':
          accepted = True
        elif rx_status == 'complete':
          return incoming.get('msg',None)
        elif rx_status == 'notify':
          pass
        else:
          raise IOError("Received message status (%s) unexpected" % (rx_status,))
      finally:
        self.recv_q.task_done()

  def __collide(self, msg):
    if self.__on_collide:
      left  = msg['msg'] in ('both','left')
      right = msg['msg'] in ('both','right')
      self.__on_collide(left, right, msg, self)

  def __follow(self, msg):
    if self.__on_follow:
      state  = int(msg['msg'])
      self.__on_follow(state, msg, self)

  def generate_id(self):
    self.n = (self.n + 1) % 0x10000
    return '%s%04x' % (self.nonce, self.n)
