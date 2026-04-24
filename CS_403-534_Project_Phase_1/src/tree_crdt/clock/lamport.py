from . import Clock

class LamportClock(Clock):
  # TODO: Implement this class by inheriting from Clock
  def __init__(self, id):
    # The ID of the replica that owns this clock
    self.__id = id
    # Lamport timestamps start at 0
    self.__timestamp = 0

  @property
  def id(self):
    return self.__id

  @property
  def timestamp(self):
    return self.__timestamp

  def update(self, received):
    if received is None:
      self.__timestamp += 1
    else:
      self.__timestamp = max(self.__timestamp, received) + 1

  def __str__(self):
    return str(self.__timestamp)

    