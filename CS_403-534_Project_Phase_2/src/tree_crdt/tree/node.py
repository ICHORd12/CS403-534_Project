from copy import deepcopy

class Node:
  def __init__(self, i, t, p, m, c):
    self.__i = i
    self.__t = t
    self.__p = p
    self.__m = m
    self.__c = c

  @property
  def replica_id(self):
    return self.__i

  @property
  def timestamp(self):
    return deepcopy(self.__t)

  @property
  def parent(self):
    return self.__p

  @property
  def metadata(self):
    return self.__m

  @property
  def child(self):
    return self.__c
  
  # Returns whether the node is "active" or "deleted"
  @property
  def status(self):
    return self.__m["status"]

  def __call__(self):
    return (self.__i, deepcopy(self.__t), self.__p, self.__m, self.__c)

  def __str__(self):
    return f"Node(i={str(self.__i)},t={str(self.__t)},p={str(self.__p)},m={str(self.__m)},c={str(self.__c)})"

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return False
    
    # Defined in order to be able to handle nested structures
    self_m = tuple(sorted(self.__m.items()))
    other_m = tuple(sorted(other.__m.items()))

    return (
      self.__i == other.__i
      and self.__t == other.__t
      and self.__p == other.__p
      and self_m == other_m
      and self.__c == other.__c
    )

  def __hash__(self):
    def _make_hashable(obj):
      if isinstance(obj, dict):
        return tuple(sorted((k, _make_hashable(v)) for k, v in obj.items()))
      if isinstance(obj, (list, tuple)):
        return tuple(_make_hashable(item) for item in obj)
      return obj

    timestamp = _make_hashable(self.__t)
    metadata = _make_hashable(self.__m)
    return hash((self.__i, timestamp, self.__p, metadata, self.__c))