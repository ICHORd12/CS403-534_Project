class MovePayload:
  def __init__(self, i, t, p, m, c):
    self.__i = i
    self.__t = t
    self.__p = p
    self.__m = m
    self.__c = c

  @property
  def id(self):
    return self.__i
  
  @property
  def timestamp(self):
    return self.__t
  
  @property
  def parent(self):
    return self.__p
  
  @property
  def metadata(self):
    return self.__m
  
  @property
  def child(self):
    return self.__c

  def __call__(self):
    return self.__p, self.__m, self.__c
  
  def __str__(self):
    return f"{self.__i},({self.__t},{self.__p},{self.__m},{self.__c})"
  