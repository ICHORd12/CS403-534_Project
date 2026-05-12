import threading
import copy
from functools import cmp_to_key

from .clock import Clock, VectorClock
from .payload import MovePayload
from .tree import Tree, Node

Node.__repr__ = Node.__str__
MovePayload.__repr__ = lambda self: f"MovePayload(id={self.id}, timestamp={self.timestamp}, parent={self.parent}, metadata={self.metadata}, child={self.child})"

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
    self.__id = id
    self.__clock = VectorClock(id, num_replicas)
    self.__tree = Tree()          
    self.__snapshot = Tree()      
    self.__op_log = []            
    self.__last_timestamps = {}   
    self.__zmq_main_addr = f"tcp://{host}:{main_base + id}"
    self.__zmq_listener_addr = f"tcp://{host}:{listener_base + id}"
    self.__lock = threading.RLock()

  # ---------------------------------------------------------------------
  # Properties
  # ---------------------------------------------------------------------

  @property
  def id(self) -> int:
    return self.__id

  @property
  def clock(self) -> Clock:
    with self.__lock:
        return copy.deepcopy(self.__clock)

  @property
  def tree(self) -> Tree:
    with self.__lock:
        return copy.deepcopy(self.__tree)

  @property
  def log(self) -> list:
    with self.__lock:
        return copy.deepcopy(self.__op_log)

  @property
  def main_addr(self) -> str:
    return self.__zmq_main_addr

  @property
  def listener_addr(self) -> str:
    return self.__zmq_listener_addr

  # ---------------------------------------------------------------------
  # Additional Methods Required for Testing
  # ---------------------------------------------------------------------

  def record_last_timestamp(self, peer_id: int, timestamp: dict):
    with self.__lock:
        self.__last_timestamps[peer_id] = copy.deepcopy(timestamp)

  def get_peer_timestamp(self, peer_id: int) -> dict:
    with self.__lock:
        return copy.deepcopy(self.__last_timestamps.get(
            peer_id, {i: 0 for i in range(len(self.__clock.timestamp))}
        ))

  def tree_snapshot(self):
    with self.__lock:
        return self.__snapshot()

  # ---------------------------------------------------------------------
  # Core API
  # ---------------------------------------------------------------------

  def current_timestamp(self) -> dict[int, int]:
    """Return the current internal timestamp (used to stamp outgoing moves)."""
    with self.__lock:
        return self.__clock.timestamp

  def tick_clock(self, received: dict[int, int] | None = None) -> dict[int, int]:
    """Tick the local clock, optionally taking the max with `received`."""
    with self.__lock:
        self.__clock.update(received)
        return self.current_timestamp()

  def apply_local_move(self, parent: int | None, metadata: dict, child: int) -> MovePayload:
    """Apply a locally generated Move operation.
    
    Tick the clock, construct the MovePayload, pass to __apply_move,
    and return the payload so it can be broadcast.
    """
    with self.__lock:
        self.tick_clock()
        op = MovePayload(self.id, self.current_timestamp(), parent, metadata, child)
        self.__apply_move(op)
        return op

  def apply_remote_move(self, op: MovePayload):
    """Apply a Move operation received from a peer.
    
    Tick the clock with the remote timestamp, then pass to __apply_move.
    """
    with self.__lock:
        self.tick_clock(op.timestamp)
        self.__apply_move(op)

  def __apply_move(self, op: MovePayload):
    """Core resolution logic.

    Insert the operation into the log. In Phase 2, this MUST maintain
    a strict total order on the log to guarantee convergence.

    Because concurrent Move operations may arrive out of causal order
    (or even in order but require conflict resolution that retroactively
    changes the `applied` flag of a past operation), the simplest strategy
    is the Log-Insertion-Rollback-Redo sequence:

      1. Insert into the log and re-sort.
      2. Undo: reset the active tree to the causally stable SNAPSHOT.
      3. Redo: replay the entire log forward, recalculating Move-Wins.
      4. Try to compact the log if the causal stability threshold has advanced.
    """
    with self.__lock:
        self.__do_operation(op)
        self.__undo_operations(None)
        self.__redo_operations(None)
        self.__compact_log()

  # ---------------------------------------------------------------------
  # Log compaction
  # ---------------------------------------------------------------------

  def __compact_log(self):
    """Compute the causal-stability threshold and compact the log.

    Every time the local clock ticks (via local or remote event),
    we may have learned that all peers have passed a certain timestamp.
    That minimum is the causal-stability threshold.

    For each log entry whose timestamp is strictly less than the
    threshold, fold its effect (if applied=True) into the snapshot tree
    and drop it from the active log.
    """
    with self.__lock:
        if not self.__op_log:
            return

        num_reps = len(self.__clock.timestamp)
        threshold_vector = {}
        
        for k in range(num_reps):
            min_k = self.__clock.timestamp.get(k, 0)
            for peer_id in range(num_reps):
                if peer_id == self.id:
                    continue
                peer_ts = self.__last_timestamps.get(peer_id, {})
                min_k = min(min_k, peer_ts.get(k, 0))
            threshold_vector[k] = min_k
        
        new_log = []
        for op_tuple in self.__op_log:
            r_id, r_t, old_p, r_p, r_m, r_c = op_tuple
            
            if r_t[r_id] < threshold_vector.get(r_id, 0):
                self.__snapshot.move(r_id, r_t, r_p, r_m, r_c)
            else:
                new_log.append(op_tuple)
                
        self.__op_log = new_log

  # ---------------------------------------------------------------------
  # Internal: undo / do / redo helpers
  # ---------------------------------------------------------------------

  def __undo_operations(self, ops):
    """Rebuild the tree without the given log entries.

    A reasonable implementation is to restore from the snapshot and
    redo every other log entry whose applied=True.
    """
    with self.__lock:
        self.__tree = copy.deepcopy(self.__snapshot)

  def __do_operation(self, op, *args, **kwargs):
    """Insert `op` into the log and (if applied=True) apply it to the tree."""
    with self.__lock:
        last_ts = op.metadata.pop("last_ts", None)
        op.metadata["applied"] = True
        if last_ts is not None:
            op.metadata["last_ts"] = last_ts
        
        curr_versions = self.__tree[op.child]
        old_p = list(curr_versions)[0].parent if curr_versions else None
        
        log_entry = (op.id, op.timestamp, old_p, op.parent, op.metadata, op.child)
        self.__op_log.append(log_entry)
        
        def compare_ops(a, b):
            if VectorClock.timestamp_lt(a[1], b[1]): return -1
            if VectorClock.timestamp_lt(b[1], a[1]): return 1
            if a[0] < b[0]: return -1
            if a[0] > b[0]: return 1
            return 0
            
        self.__op_log.sort(key=cmp_to_key(compare_ops))

  def __redo_operations(self, ops):
    """Re-apply each entry in `ops` (whose applied=True) to the tree."""
    with self.__lock:
        for log_entry in self.__op_log:
            r_id, r_t, old_p, r_p, r_m, r_c = log_entry
            self.__tree.move(r_id, r_t, r_p, r_m, r_c)

  # ---------------------------------------------------------------------
  # String representations
  # ---------------------------------------------------------------------

  def __str__(self):
    with self.__lock:
        return f"Replica(id={self.__id}, clock={self.__clock})"

  def __repr__(self):
    return self.__str__()