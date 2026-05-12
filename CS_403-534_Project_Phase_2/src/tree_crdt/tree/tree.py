from .node import Node


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
    # TODO: initialise an empty container for the per-child set of versions.
    #       The container type (dict, list, etc.) is up to you.
    raise NotImplementedError("TODO: implement Tree.__init__")

  def __call__(self, deleted):
    """Return the current tree state as a list of frozensets, sorted by child ID.

    If `deleted` is False (default), versions whose status is "deleted"
    are filtered out of each frozenset. If `deleted` is True, they are
    included. frozenset is used (rather than set) because the caller may
    need the result to be hashable.
    """
    # TODO
    raise NotImplementedError("TODO: implement Tree.__call__")

  def __getitem__(self, key):
    """Return the set of versions associated with `key`, or the empty set if unknown.

    The return type is a set[Node]; if you store versions internally in
    a different container, convert on the fly here.
    """
    # TODO
    raise NotImplementedError("TODO: implement Tree.__getitem__")

  def __iter__(self):
    """Iterate over the child IDs known to the tree."""
    # TODO
    raise NotImplementedError("TODO: implement Tree.__iter__")

  def get_active(self, key):
    """Return the subset of `[key]` consisting of versions that are alive.

    A version is alive iff it is not a tombstone (status != "deleted")
    AND it is not orphaned. A version is orphaned if it has no path to
    the root through ancestors whose multi-value sets contain at least
    one alive version. See the PDF section "Orphaned Nodes" for details.
    """
    # TODO: filter out tombstones AND orphans (e.g. via BFS/DFS up to root)
    raise NotImplementedError("TODO: implement Tree.get_active")

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
    # TODO
    raise NotImplementedError("TODO: implement Tree.move")

  def __str__(self):
    # TODO
    raise NotImplementedError("TODO: implement Tree.__str__")

  def __repr__(self):
    # TODO
    raise NotImplementedError("TODO: implement Tree.__repr__")
