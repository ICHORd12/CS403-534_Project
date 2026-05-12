import threading

from .clock import Clock, VectorClock
from .payload import MovePayload
from .tree import Tree, Node


class Replica:
  """A replica in the Tree CRDT system.

  In Phase 2, the Replica gains:

    - A `num_replicas` constructor argument that
      switches the replica's clock from LamportClock to VectorClock.
    - A peer-progress map (peer_id -> last seen timestamp) used to compute
      the causal-stability threshold for log compaction.
    - A second Tree instance, the SNAPSHOT, holding the cumulative effect
      of log entries that are already known to be causally stable.
    - A new resolution path inside __apply_move (the Move-Wins case)
      that may flip the "applied" flag of a past log entry and rebuild
      the tree from the snapshot.

  The Replica object is shared between the main and listener threads of
  its process; access must remain thread-safe (e.g. via threading.RLock).

  See the Phase 2 PDF, Section "The Replica Class", for the full contract.
  """

  def __init__(self, id, host, main_base, listener_base, num_replicas):
    """Construct a replica.
    The clock is a VectorClock(id, num_replicas).
    """
    # TODO: store id, choose clock type based on num_replicas, construct
    #       Tree (active) and Tree (snapshot), op_log, lock, last_timestamps,
    #       and the two ZeroMQ addresses.
    raise NotImplementedError("TODO: implement Replica.__init__")

  # ---------------------------------------------------------------------
  # Public read-only accessors
  # ---------------------------------------------------------------------

  @property
  def id(self):
    """Return the replica ID."""
    raise NotImplementedError("TODO: implement Replica.id")

  @property
  def clock(self):
    """Return a deep copy of the clock."""
    raise NotImplementedError("TODO: implement Replica.clock")

  @property
  def tree(self):
    """Return a deep copy of the active tree."""
    raise NotImplementedError("TODO: implement Replica.tree")
  
  @property
  def tree_snapshot(self):
    """Return a deep copy of the tree snapshot."""
    raise NotImplementedError("TODO: implement Replica.tree")

  @property
  def log(self):
    """Return a deep copy of the operation log."""
    raise NotImplementedError("TODO: implement Replica.log")

  @property
  def last_timestamps(self):
    """Return a deep copy of the per-peer most-recent-timestamp map."""
    raise NotImplementedError("TODO: implement Replica.last_timestamps")

  @property
  def main_addr(self):
    """Return the ZeroMQ bind address for the main thread."""
    raise NotImplementedError("TODO: implement Replica.main_addr")

  @property
  def listener_addr(self):
    """Return the ZeroMQ bind address for the listener thread."""
    raise NotImplementedError("TODO: implement Replica.listener_addr")

  # ---------------------------------------------------------------------
  # Clock helpers
  # ---------------------------------------------------------------------

  def current_timestamp(self):
    """Return the current value of the clock's timestamp."""
    raise NotImplementedError("TODO: implement Replica.current_timestamp")

  def tick_clock(self, received):
    """Advance the clock by calling clock.update(received), thread-safely.

    Pass `received=None` for a local event, or the received timestamp for
    a remote event. Returns the new timestamp.
    """
    raise NotImplementedError("TODO: implement Replica.tick_clock")

  # ---------------------------------------------------------------------
  # Peer-progress bookkeeping (Phase 2)
  # ---------------------------------------------------------------------

  def record_last_timestamp(self, replica_id, last_timestamp):
    """Record that peer `replica_id` was most recently seen at `last_timestamp`.

    Called by the listener-side of the receive path whenever a peer
    advertises its progress (see PDF Section "Tracking Peer Progress").
    """
    raise NotImplementedError("TODO: implement Replica.record_last_timestamp")

  def get_peer_timestamp(self, peer_id):
    """Return the most recent timestamp recorded for peer `peer_id`.

    Contract:
      - If `peer_id` has been registered via `record_last_timestamp`,
        return the recorded value (deep-copy-safe: the caller must not
        be able to mutate internal state through the returned value).
      - If `peer_id` is unknown, return the identity element of the
        clock's order: all-zeros vectorn(with the same key set as the local clock) 
        for a vector-clock replica.
      - The method is read-only and must be thread-safe.
    """
    raise NotImplementedError("TODO: implement Replica.get_peer_timestamp")

  # ---------------------------------------------------------------------
  # Public apply paths
  # ---------------------------------------------------------------------

  def apply_local_move(self, parent, metadata, child):
    """Generate a local Move operation, apply it, and return the payload.

    The metadata dict MUST contain "status": "active" or "deleted".
    The library will set "applied" inside __apply_move.
    """
    # TODO: tick the clock locally, build the MovePayload, and call
    #       __apply_move(payload). Return the payload so the caller can
    #       broadcast it over the wire.
    raise NotImplementedError("TODO: implement Replica.apply_local_move")

  def apply_remote_move(self, op):
    """Apply a Move operation received from a peer."""
    # TODO: tick the clock with op.timestamp, then call __apply_move(op).
    raise NotImplementedError("TODO: implement Replica.apply_remote_move")

  # ---------------------------------------------------------------------
  # Internal: ordering, conflict detection, apply, undo/do/redo
  # ---------------------------------------------------------------------
  #
  # The structure below is the recommended decomposition; you may rename,
  # reorganise, or merge methods as you see fit. The PDF describes the
  # required SEMANTICS of each step.

  def __is_in_order(self, op):
    """Return True iff `op` can be appended to the log without disturbing it.

    Vector : op is in order iff op does NOT strictly happen-before the
             last log entry. (Concurrent ops are in order; they become
             multi-value peers.)
    """
    raise NotImplementedError("TODO: implement Replica.__is_in_order")

  def __get_concurrent_conflicts(self, op):
    """Return log entries that conflict with `op` (vector clock case).

    Two ops conflict iff their timestamps are concurrent AND they target
    the same child ID. Used to drive the Move-Wins path of __apply_move.
    """
    raise NotImplementedError("TODO: implement Replica.__get_concurrent_conflicts")

  def __find_insertion_point(self, op):
    """Return the index in op_log at which `op` should be inserted.

    Vector : insert before the first entry whose timestamp is >= op.timestamp
             under the partial order; concurrent entries are skipped past
             so that they remain peers rather than being undone/redone.
    """
    raise NotImplementedError("TODO: implement Replica.__find_insertion_point")

  def __apply_move(self, op):
    """The central apply method.

    Required behaviour (see PDF Section "The __apply_move(op) method"):

      1. If using vector clocks, detect log conflicts. For each conflict:
           - incoming Delete vs. existing alive   --> mark op as
             "applied": False, append to log, RETURN (no checkpointing).
           - incoming alive  vs. existing Delete  --> flip the existing
             entry's "applied" flag to False; remember to rebuild.

      2. If no flag was flipped AND op is in order: append + apply to tree.

      3. Else, run the appropriate recovery sequence:
           - undo-do-redo (Phase 1, but skipping entries with applied=False),
             OR
           - log-insertion-rollback-redo: insert op, restore tree from
             snapshot, redo all entries currently in the log whose
             applied=True.

      4. End by attempting log compaction (call __compact_log).
    """
    raise NotImplementedError("TODO: implement Replica.__apply_move")

  # ---------------------------------------------------------------------
  # Internal: checkpointing (Phase 2)
  # ---------------------------------------------------------------------

  def __min_timestamp(self):
    """Return the causal-stability threshold (min over peer timestamps)."""
    raise NotImplementedError("TODO: implement Replica.__min_timestamp")

  def __compact_log(self):
    """Compact the operation log up to the causal-stability threshold.

    For each log entry whose timestamp is strictly less than the
    threshold, fold its effect (if applied=True) into the snapshot tree
    and drop it from the active log.
    """
    raise NotImplementedError("TODO: implement Replica.__compact_log")

  # ---------------------------------------------------------------------
  # Internal: undo / do / redo helpers
  # ---------------------------------------------------------------------

  def __undo_operations(self, ops):
    """Rebuild the tree without the given log entries.

    A reasonable implementation is to restore from the snapshot and
    redo every other log entry whose applied=True.
    """
    raise NotImplementedError("TODO: implement Replica.__undo_operations")

  def __do_operation(self, op, *args, **kwargs):
    """Insert `op` into the log and (if applied=True) apply it to the tree."""
    raise NotImplementedError("TODO: implement Replica.__do_operation")

  def __redo_operations(self, ops):
    """Re-apply each entry in `ops` (whose applied=True) to the tree."""
    raise NotImplementedError("TODO: implement Replica.__redo_operations")

  # ---------------------------------------------------------------------
  # String representations
  # ---------------------------------------------------------------------

  def __str__(self):
    raise NotImplementedError("TODO: implement Replica.__str__")

  def __repr__(self):
    raise NotImplementedError("TODO: implement Replica.__repr__")
