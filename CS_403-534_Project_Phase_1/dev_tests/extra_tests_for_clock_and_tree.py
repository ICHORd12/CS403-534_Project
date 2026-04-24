"""
Run from the project root:
    uv run python -m unittest dev_tests.extra_tests_for_clock_and_tree -v
or if the venv is activated:
    python -m unittest dev_tests.extra_tests_for_clock_and_tree -v
"""
import unittest

from tree_crdt.clock import Clock
from tree_crdt.clock.lamport import LamportClock
from tree_crdt.tree import Node, Tree


# ==========================================================================
# LamportClock -- scenarios the given test_lamport.py does not cover
# ==========================================================================

class TestLamportClockInitialization(unittest.TestCase):
  def test_starts_at_zero(self):
    self.assertEqual(LamportClock(id=1).timestamp, 0)

  def test_id_is_stored(self):
    self.assertEqual(LamportClock(id=42).id, 42)

  def test_id_zero_is_valid(self):
    # Replica IDs in this project start at 0.
    self.assertEqual(LamportClock(id=0).id, 0)

  def test_instantiates_cleanly(self):
    # If a Clock abstract method weren't implemented, Python would
    # raise TypeError on construction.
    LamportClock(id=1)  # must not raise

  def test_is_a_Clock_subclass(self):
    self.assertIsInstance(LamportClock(id=1), Clock)


class TestLamportClockLocalTick(unittest.TestCase):
  """update(None) is how Replica.apply_local_move ticks the clock."""

  def test_local_tick_increments_by_one(self):
    c = LamportClock(id=1)
    c.update(None)
    self.assertEqual(c.timestamp, 1)

  def test_multiple_local_ticks(self):
    c = LamportClock(id=1)
    for expected in range(1, 11):
      c.update(None)
      self.assertEqual(c.timestamp, expected)


class TestLamportClockRemoteUpdate(unittest.TestCase):
  """update(r) for integer r uses the Lamport merge rule."""

  def test_update_with_larger_received(self):
    c = LamportClock(id=1)
    c.update(10)
    self.assertEqual(c.timestamp, 11)  # max(0, 10) + 1

  def test_update_with_smaller_received(self):
    c = LamportClock(id=1)
    for _ in range(3): c.update(None)  # ts = 3
    c.update(1)
    self.assertEqual(c.timestamp, 4)  # max(3, 1) + 1

  def test_update_with_equal_received(self):
    c = LamportClock(id=1)
    for _ in range(3): c.update(None)  # ts = 3
    c.update(3)
    self.assertEqual(c.timestamp, 4)  # max(3, 3) + 1

  def test_update_with_zero_is_not_local_tick(self):
    """
    Regression guard: received 0 must use the merge rule, not be confused
    with update(None). Both happen to give +1 from ts=0, but diverge later.
    """
    c = LamportClock(id=1)
    c.update(None)   # ts = 1
    c.update(None)   # ts = 2
    c.update(0)      # merge: max(2, 0) + 1 = 3  (NOT 3 via local, still 3)
    self.assertEqual(c.timestamp, 3)


class TestLamportClockMixedEvents(unittest.TestCase):
  def test_interleaved_local_and_remote(self):
    c = LamportClock(id=1)
    c.update(None)   # 1
    c.update(5)      # max(1,5)+1 = 6
    c.update(None)   # 7
    c.update(3)      # max(7,3)+1 = 8
    c.update(None)   # 9
    self.assertEqual(c.timestamp, 9)


class TestLamportClockStr(unittest.TestCase):
  def test_str_of_initial(self):
    self.assertEqual(str(LamportClock(id=1)), "0")

  def test_str_after_ticks(self):
    c = LamportClock(id=1)
    for _ in range(3): c.update(None)
    self.assertEqual(str(c), "3")


# ==========================================================================
# Tree -- scenarios the given test_tree.py does not cover
# ==========================================================================

class TestTreeGetItem(unittest.TestCase):
  def test_missing_key_returns_None(self):
    # Spec: __getitem__ returns None for missing keys (not KeyError).
    t = Tree()
    self.assertIsNone(t[999])

  def test_returns_same_node_after_insert(self):
    t = Tree()
    t.move(Node(p=None, m={"k": "v"}, c=1))
    self.assertIsNotNone(t[1])
    self.assertEqual(t[1].parent, None)
    self.assertEqual(t[1].metadata, {"k": "v"})


class TestTreeDuplicateEdgeIgnored(unittest.TestCase):
  """
  Figure 1's 'Move 7 0 m_2 2' case: re-applying the same (p, m, c) edge
  is a no-op.
  """
  def test_exact_duplicate_is_noop(self):
    t = Tree()
    t.move(Node(p=None, m={"v": "a"}, c=0))
    t.move(Node(p=0, m={"v": "b"}, c=1))

    snapshot_before = t()
    t.move(Node(p=0, m={"v": "b"}, c=1))  # exact duplicate
    snapshot_after = t()

    self.assertEqual(snapshot_before, snapshot_after)


class TestTreeCycleVariants(unittest.TestCase):
  def test_self_loop_rejected(self):
    """p == c is the most basic cycle."""
    t = Tree()
    t.move(Node(p=None, m={}, c=1))
    t.move(Node(p=1, m={}, c=1))
    self.assertIsNone(t[1].parent)

  def test_deep_chain_cycle_rejected(self):
    """4-level chain: 0 -> 1 -> 2 -> 3, try to put 0 under 3."""
    t = Tree()
    for c in range(4):
      p = None if c == 0 else c - 1
      t.move(Node(p=p, m={}, c=c))
    # Would create cycle 3 -> 0 -> 1 -> 2 -> 3
    t.move(Node(p=3, m={}, c=0))
    self.assertIsNone(t[0].parent)
    self.assertEqual(len(t()), 4)

  def test_valid_reparent_is_not_a_cycle(self):
    """0 -> 1 -> 2; move 2 directly under 0 (legal flattening)."""
    t = Tree()
    t.move(Node(p=None, m={}, c=0))
    t.move(Node(p=0, m={}, c=1))
    t.move(Node(p=1, m={}, c=2))
    t.move(Node(p=0, m={}, c=2))
    self.assertEqual(t[2].parent, 0)


class TestTreeForwardReference(unittest.TestCase):
  """
  Spec does not forbid moving a node under a parent that doesn't exist
  yet (a later move may create the parent). Cycle detection must
  terminate cleanly when the parent chain hits a missing ID.
  """
  def test_parent_not_yet_in_tree(self):
    t = Tree()
    t.move(Node(p=99, m={}, c=1))
    self.assertEqual(t[1].parent, 99)
    self.assertIsNone(t[99])


class TestTreeSnapshotIsolation(unittest.TestCase):
  def test_call_returns_snapshot_not_live_view(self):
    t = Tree()
    t.move(Node(p=None, m={}, c=1))
    snap = t()
    t.move(Node(p=None, m={}, c=2))
    self.assertEqual(len(snap), 1, "earlier snapshot should not see later inserts")
    self.assertEqual(len(t()), 2)


class TestTreeMetadataUpdate(unittest.TestCase):
  """Figure 1's 'Move 8 0 m'_2 2' case: overwrite metadata, same p and c."""
  def test_metadata_only_update(self):
    t = Tree()
    t.move(Node(p=None, m={"v": 1}, c=1))
    t.move(Node(p=None, m={"v": 2}, c=1))
    self.assertEqual(len(t()), 1, "metadata update must not duplicate the node")
    self.assertEqual(t[1].metadata, {"v": 2})


class TestTreeStr(unittest.TestCase):
  def test_empty_tree_str(self):
    self.assertEqual(str(Tree()), "{}")

  def test_populated_tree_str_is_non_trivial(self):
    # We don't pin the exact format, just that it mentions both nodes.
    t = Tree()
    t.move(Node(p=None, m={"x": 1}, c=0))
    t.move(Node(p=0, m={}, c=1))
    s = str(t)
    self.assertIn("None", s)
    self.assertIn("0", s)
    self.assertIn("1", s)


class TestTreeFigure1Sequence(unittest.TestCase):
  """
  Replay the full sequence from PDF Figure 1 and check the final state.
  This is the headline end-to-end scenario for Tree.
  """
  def test_figure1_full_sequence(self):
    t = Tree()
    m0 = {"label": "m0"}
    m1 = {"label": "m1"}
    m2 = {"label": "m2"}
    m2_prime = {"label": "m2_prime"}
    m3 = {"label": "m3"}

    # Move 1 None m_0 0
    t.move(Node(p=None, m=m0, c=0))
    # Move 2 0 m_1 1
    t.move(Node(p=0, m=m1, c=1))
    # Move 3 0 m_2 2
    t.move(Node(p=0, m=m2, c=2))

    # Move 4 2 m_0 0  -- IGNORED (cycle)
    t.move(Node(p=2, m=m0, c=0))
    self.assertIsNone(t[0].parent, "0 must still be root after ignored move")

    # Move 5 1 m_3 3  -- creates 3 under 1
    t.move(Node(p=1, m=m3, c=3))
    self.assertEqual(t[3].parent, 1)

    # Move 6 2 m_3 3  -- reparent 3 under 2
    t.move(Node(p=2, m=m3, c=3))
    self.assertEqual(t[3].parent, 2)

    # Move 7 0 m_2 2  -- IGNORED (exact duplicate)
    snap_before = t()
    t.move(Node(p=0, m=m2, c=2))
    self.assertEqual(t(), snap_before, "duplicate move must leave tree unchanged")

    # Move 8 0 m'_2 2 -- metadata update
    t.move(Node(p=0, m=m2_prime, c=2))
    self.assertEqual(t[2].metadata, m2_prime)

    # Final tree has exactly 4 nodes: 0, 1, 2, 3.
    self.assertEqual(len(t()), 4)
    self.assertEqual({t[c].child for c in range(4)}, {0, 1, 2, 3})


if __name__ == "__main__":
  unittest.main()