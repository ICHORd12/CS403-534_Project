from copy import deepcopy

from . import VectorClock


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
    # TODO: store the replica id and initialise the dict {0: 0, 1: 0, ..., max_id-1: 0}
    raise NotImplementedError("TODO: implement VectorClock.__init__")

  @property
  def id(self) -> int:
    """Return the ID of the replica that owns this clock."""
    # TODO
    raise NotImplementedError("TODO: implement VectorClock.id")

  @property
  def timestamp(self) -> dict[int, int]:
    """Return a DEEP COPY of the current vector timestamp."""
    # TODO: deepcopy is required; do not return the internal dict directly
    raise NotImplementedError("TODO: implement VectorClock.timestamp")

  def update(self, received: dict[int, int] | None) -> None:
    """Update the clock.

    If `received` is None, this is a local event: increment self[self.id] by 1.
    If `received` is a dict, this is a remote event: take component-wise max
    with `received`, then increment self[self.id] by 1.
    """
    # TODO
    raise NotImplementedError("TODO: implement VectorClock.update")

  def __str__(self) -> str:
    # TODO
    raise NotImplementedError("TODO: implement VectorClock.__str__")

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
    # TODO: Implement the <= comparison for both Lamport (int) and
    #       vector (dict[int, int]) timestamps.
    raise NotImplementedError("TODO: implement VectorClock.timestamp_le")

  @staticmethod
  def timestamp_lt(lhs, rhs):
    """Return True iff lhs < rhs under the appropriate clock order."""
    # TODO: Implement the strict < comparison.
    raise NotImplementedError("TODO: implement VectorClock.timestamp_lt")

  @staticmethod
  def timestamp_eq(lhs, rhs):
    """Return True iff lhs == rhs."""
    # TODO: Implement equality for both clock types.
    raise NotImplementedError("TODO: implement VectorClock.timestamp_eq")

  @staticmethod
  def timestamp_concurrent(lhs, rhs):
    """Return True iff lhs and rhs are concurrent (||) under the partial order."""
    # TODO: For vector timestamps, two timestamps are concurrent iff
    #       neither is <= the other. For Lamport, this is identically False.
    raise NotImplementedError("TODO: implement VectorClock.timestamp_concurrent")
