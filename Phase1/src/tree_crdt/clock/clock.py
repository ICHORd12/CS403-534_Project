from abc import ABC, abstractmethod

class Clock(ABC):
  @property
  @abstractmethod
  def id(self): ...

  @property
  @abstractmethod
  def timestamp(self): ...

  @abstractmethod
  def update(self, received): ...

  @abstractmethod
  def __str__(self): ...