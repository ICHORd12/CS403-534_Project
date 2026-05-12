from .node import Node
from ..clock.vector import VectorClock

class Tree:
  """The tree data structure underlying the Tree CRDT.

  In Phase 2, each child ID is associated with a set of versions of that
  node, rather than a single triple as in Phase 1. Each version is a
  Node carrying the (i, t, p, m, c) quintuple from the operation that
  produced it. Under a Lamport clock that set will contain at most one
  element, so the Phase 1 behaviour is recovered as a degenerate
  special case.

  The choice of how to STORE this association internally is yours,
  exactly as in Phase 1: a dictionary mapping IDs to sets, a list of
  Node objects you index on demand, or any other container is
  acceptable, as long as the methods below behave according to their
  contracts. Note that the EXTERNAL return types of __call__ and
  __getitem__ ARE constrained (they are part of the test-facing API);
  see the Phase 2 PDF, Section "The Tree Class", for the full contract.
  """

  def __init__(self):
    """Construct an empty tree."""
    self.__nodes = {}

  def __call__(self, deleted=False):
    """Return the current tree state as a list of frozensets, sorted by child ID.

    If `deleted` is False (default), versions whose status is "deleted"
    are filtered out of each frozenset. If `deleted` is True, they are
    included. frozenset is used (rather than set) because the caller may
    need the result to be hashable.
    """
    result = []
    for c_id in sorted(self.__nodes.keys()):
        versions = self.__nodes[c_id]
        if not deleted:
            filtered = frozenset(v for v in versions if v.metadata.get("status", "active") != "deleted")
        else:
            filtered = frozenset(versions)
            
        result.append(filtered)
    return result

  def __getitem__(self, key):
    """Return the set of versions associated with `key`, or the empty set if unknown.

    The return type is a set[Node]; if you store versions internally in
    a different container, convert on the fly here.
    """
    return self.__nodes.get(key, set())

  def __iter__(self):
    """Iterate over the child IDs known to the tree."""
    return iter(self.__nodes.keys())

  def _is_orphaned(self, start_version: Node) -> bool:
    if start_version.parent is None:
        return False 
        
    stack = [start_version.parent]
    visited = set()
    
    while stack:
        curr_id = stack.pop()
        if curr_id is None:
            return False 
            
        if curr_id in visited:
            continue
        visited.add(curr_id)
        
        versions = self.__nodes.get(curr_id, set())
        if not versions:
            continue 
            
        if all(v.metadata.get("status", "active") == "deleted" for v in versions):
            continue
            
        for v in versions:
            if v.metadata.get("status", "active") != "deleted":
                stack.append(v.parent)
                
    return True 

  def get_active(self, key):
    """Return the subset of `[key]` consisting of versions that are alive.

    A version is alive iff it is not a tombstone (status != "deleted")
    AND it is not orphaned. A version is orphaned if it has no path to
    the root through ancestors whose multi-value sets contain at least
    one alive version. See the PDF section "Orphaned Nodes" for details.
    """
    versions = self.__nodes.get(key, set())
    active_subset = set()
    for v in versions:
        if v.metadata.get("status", "active") != "deleted" and not self._is_orphaned(v):
            active_subset.add(v)
    return active_subset

  def _causes_cycle(self, parent_id, child_id) -> bool:
    if parent_id == child_id:
        return True
    if parent_id is None:
        return False
        
    stack = [parent_id]
    visited = set()
    
    while stack:
        curr = stack.pop()
        if curr == child_id:
            return True
        if curr in visited or curr is None:
            continue
        visited.add(curr)
        
        versions = self.__nodes.get(curr, set())
        for v in versions:
            if v.parent is not None:
                stack.append(v.parent)
    return False

  def move(self, replica_id, timestamp, parent, metadata, child):
    """Apply the Move operation (i, t, p, m, c) to the tree.

    The required behaviour is:

      1. Reject the operation if it would create a cycle (child == parent,
         or `parent` is currently a descendant of `child` through any
         version in any multi-value set on the path; use a DFS).

      2. Otherwise, build the candidate Node and resolve it pairwise
         against every existing version in the multi-value set for `child`:

         - Vector (both timestamps are dict): pairwise compare with
           VectorClock.timestamp_le / timestamp_lt / timestamp_concurrent; the
           older version is removed, the newer-existing version causes
           the candidate to be discarded, and concurrent versions trigger
           Move-Wins (see PDF Section "Multi-Value Tree State and the
           Move-Wins Concurrency Semantics"):

             * incoming Delete vs. existing alive  --> discard candidate
             * incoming alive  vs. existing Delete --> remove existing

      3. Remove the marked-for-removal versions, add the candidate
         (unless discarded), write the updated multi-value set back.
    """
    if self._causes_cycle(parent, child):
        return
        
    cand = Node(i=replica_id, t=timestamp, p=parent, m=metadata, c=child)
    
    if child not in self.__nodes:
        self.__nodes[child] = set()
        
    if isinstance(timestamp, int):
        self.__nodes[child] = {cand}
        return
        
    existing_versions = self.__nodes[child]
    to_remove = set()
    discard_cand = False
    
    cand_deleted = (cand.metadata.get("status", "active") == "deleted")
    
    for v in existing_versions:
        if VectorClock.timestamp_lt(v.timestamp, cand.timestamp):
            to_remove.add(v)
        elif VectorClock.timestamp_le(cand.timestamp, v.timestamp):
            discard_cand = True
        elif VectorClock.timestamp_concurrent(v.timestamp, cand.timestamp):
            
            v_deleted = (v.metadata.get("status", "active") == "deleted")
            
            if cand_deleted and not v_deleted:
                discard_cand = True
            elif not cand_deleted and v_deleted:
                to_remove.add(v)
            else:
                pass
                
    for v in to_remove:
        existing_versions.remove(v)
        
    if not discard_cand:
        existing_versions.add(cand)
        
    if not self.__nodes[child]:
        del self.__nodes[child]

  def __str__(self):
    if not self.__nodes:
        return "Empty Tree"
    res = []
    for k in sorted(self.__nodes.keys()):
        versions = sorted(list(self.__nodes[k]), key=lambda x: str(x))
        res.append(f"{k}: {versions}")
    return "Tree(" + ", ".join(res) + ")"

  def __repr__(self):
    return self.__str__()