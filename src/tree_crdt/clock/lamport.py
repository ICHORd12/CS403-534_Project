from .clock import Clock

class LamportClock(Clock):
    def __init__(self, id: int):
        self.__id = id
        self.__timestamp = 0

    @property
    def id(self) -> int:
        return self.__id

    @property
    def timestamp(self) -> int:
        return self.__timestamp

    def update(self, received: int | None = None) -> None:
        """
        Updates the clock. 
        If received is None, it's a local event.
        If received is an int, it's a remote event from another replica.
        """
        if received is None:
            # Local update: just add 1
            self.__timestamp += 1
        else:
            # Remote update: pick the highest timestamp, then add 1
            self.__timestamp = max(self.__timestamp, received) + 1

    def __str__(self) -> str:
        return str(self.__timestamp)