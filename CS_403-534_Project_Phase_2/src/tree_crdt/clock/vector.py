from copy import deepcopy

from . import Clock


class VectorClock(Clock):
  """Vector logical clock for a replica.

  See the Phase 2 PDF, section "The VectorClock Class", for the
  required contracts. Briefly:

    - The internal timestamp is a dict[int, int] of size `max_id`, with
      every component initialised to 0.
    - On a local event (`update(None)`), increment the component for
      this replica's id by 1.
    - On a remote event (`update(received)`), take the component-wise
      maximum of self and `received`, then perform the same self-tick.
    - The `timestamp` property MUST return a deep copy of the internal
      dict; vector timestamps are mutable and aliasing is a frequent
      source of bugs.
  """

  def __init__(self, id: int, max_id: int) -> None:
    """Initialise the clock for replica `id` in a system of `max_id` replicas."""
    super().__init__()
    self._id = id
    self._timestamp = {i: 0 for i in range(max_id)}

  @property
  def id(self) -> int:
    """Return the ID of the replica that owns this clock."""
    return self._id

  @property
  def timestamp(self) -> dict[int, int]:
    """Return a DEEP COPY of the current vector timestamp."""
    return deepcopy(self._timestamp)

  def update(self, received: dict[int, int] | None) -> None:
    """Update the clock.

    If `received` is None, this is a local event: increment self[self.id] by 1.
    If `received` is a dict, this is a remote event: take component-wise max
    with `received`, then increment self[self.id] by 1.
    """
    if received is not None:
        for k in self._timestamp.keys():
            if k in received:
                self._timestamp[k] = max(self._timestamp[k], received[k])
    
    self._timestamp[self._id] = self._timestamp.get(self._id, 0) + 1

  def __str__(self) -> str:
    return str(self._timestamp)

  # ---------------------------------------------------------------------
  # Static comparison helpers (Phase 2)
  # ---------------------------------------------------------------------
  # The four helpers below provide a single comparison API that works for
  # both Lamport timestamps (int) and vector timestamps (dict[int, int]).
  # They are required by Replica and Tree in Phase 2; see the Phase 2 PDF,
  # section "Static Comparison Helpers".
  #
  # Contracts:
  #   - timestamp_le        : returns True iff lhs <=    rhs
  #   - timestamp_lt        : returns True iff lhs <     rhs
  #   - timestamp_eq        : returns True iff lhs ==    rhs
  #   - timestamp_concurrent: returns True iff lhs || rhs (vector-only;
  #                            for Lamport, this is identically False)
  # Mismatched operand types should be treated as incomparable.

  @staticmethod
  def timestamp_le(lhs, rhs):
    """Return True iff lhs <= rhs under the appropriate clock order."""
    if type(lhs) != type(rhs):
        return False
        
    if isinstance(lhs, int):
        return lhs <= rhs
    elif isinstance(lhs, dict):
        if lhs.keys() != rhs.keys():
            return False
        return all(lhs[k] <= rhs[k] for k in lhs.keys())
    
    return False

  @staticmethod
  def timestamp_lt(lhs, rhs):
    """Return True iff lhs < rhs under the appropriate clock order."""
    if type(lhs) != type(rhs):
        return False
        
    if isinstance(lhs, int):
        return lhs < rhs
    elif isinstance(lhs, dict):
        return VectorClock.timestamp_le(lhs, rhs) and not VectorClock.timestamp_eq(lhs, rhs)
        
    return False

  @staticmethod
  def timestamp_eq(lhs, rhs):
    """Return True iff lhs == rhs."""
    if type(lhs) != type(rhs):
        return False
        
    if isinstance(lhs, int) or isinstance(lhs, dict):
        return lhs == rhs
        
    return False

  @staticmethod
  def timestamp_concurrent(lhs, rhs):
    """Return True iff lhs and rhs are concurrent (||) under the partial order."""
    if type(lhs) != type(rhs):
        return False
        
    if isinstance(lhs, int):
        return False
    elif isinstance(lhs, dict):
        if lhs.keys() != rhs.keys():
            return False
        return not VectorClock.timestamp_le(lhs, rhs) and not VectorClock.timestamp_le(rhs, lhs)
        
    return False