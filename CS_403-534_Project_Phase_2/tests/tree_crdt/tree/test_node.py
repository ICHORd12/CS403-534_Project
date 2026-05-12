import unittest

from tree_crdt.tree import Node


class TestNode(unittest.TestCase):
  """Test suite for Node class"""

  def setUp(self):
    """Set up test nodes."""
    # All metadata dicts must include "status" for the status property
    self.node1 = Node(i=0, t=1, p=None, m={"key": "value", "status": "active"}, c=1)
    self.node2 = Node(i=1, t=2, p=1,    m={"key": "value", "status": "active"}, c=2)
    self.node3 = Node(i=1, t=2, p=1,    m={"key": "value", "status": "active"}, c=2)
    self.node4 = Node(i=1, t=2, p=1,    m={"different": "metadata", "status": "active"}, c=2)

  # TEST 1: Node initialization
  def test_node_initialization(self):
    node = Node(i=0, t=5, p=5, m={"test": "data", "status": "active"}, c=10)
    self.assertEqual(node(), (0, 5, 5, {"test": "data", "status": "active"}, 10))

  # TEST 2: Node with None parent
  def test_node_with_none_parent(self):
    node = Node(i=0, t=1, p=None, m={"status": "active"}, c=1)
    _, _, p, _, c = node()
    self.assertIsNone(p)
    self.assertEqual(c, 1)

  # TEST 3: Node call returns correct tuple
  def test_node_call_returns_tuple(self):
    result = self.node1()
    self.assertIsInstance(result, tuple)
    self.assertEqual(len(result), 5)
    self.assertEqual(result, (0, 1, None, {"key": "value", "status": "active"}, 1))

  # TEST 4: Node string representation (__str__ uses str(), no quotes around strings)
  def test_node_str(self):
    expected = "Node(i=0,t=1,p=None,m={'key': 'value', 'status': 'active'},c=1)"
    self.assertEqual(str(self.node1), expected)

  # TEST 5: Node repr representation (__repr__ uses !r, so strings are quoted)
  def test_node_repr(self):
    expected = "Node(i=0,t=1,p=None,m={'key': 'value', 'status': 'active'},c=1)"
    self.assertEqual(repr(self.node1), expected)

  # TEST 6: Nodes with same attributes are equal
  def test_node_equality_same_attributes(self):
    self.assertEqual(self.node2, self.node3)

  # TEST 7: Nodes with different metadata are not equal
  def test_node_equality_different_metadata(self):
    self.assertNotEqual(self.node2, self.node4)

  # TEST 8: Nodes with different parents are not equal
  def test_node_equality_different_parents(self):
    node_a = Node(i=1, t=1, p=1, m={"key": "value", "status": "active"}, c=2)
    node_b = Node(i=1, t=1, p=2, m={"key": "value", "status": "active"}, c=2)
    self.assertNotEqual(node_a, node_b)

  # TEST 9: Nodes with different child ids are not equal
  def test_node_equality_different_child_ids(self):
    node_a = Node(i=1, t=1, p=1, m={"key": "value", "status": "active"}, c=2)
    node_b = Node(i=1, t=1, p=1, m={"key": "value", "status": "active"}, c=3)
    self.assertNotEqual(node_a, node_b)

  # TEST 10: Node inequality operator
  def test_node_inequality(self):
    self.assertTrue(self.node2 != self.node4)

  # TEST 11: Empty metadata (still needs "status")
  def test_node_empty_metadata(self):
    node = Node(i=1, t=1, p=5, m={"status": "active"}, c=10)
    _, _, _, m, _ = node()
    self.assertEqual(m, {"status": "active"})

  # TEST 12: Complex metadata
  def test_node_complex_metadata(self):
    metadata = {"nested": {"level": 2}, "list": [1, 2, 3], "string": "value", "status": "active"}
    node = Node(i=1, t=1, p=1, m=metadata, c=2)
    _, _, _, m, _ = node()
    self.assertEqual(m, metadata)

  # TEST 13: Node with large child id
  def test_node_large_child_id(self):
    node = Node(i=1, t=1, p=1, m={"status": "active"}, c=999999)
    _, _, _, _, c = node()
    self.assertEqual(c, 999999)

  # TEST 14: Node equality is reflexive
  def test_node_equality_reflexive(self):
    self.assertEqual(self.node1, self.node1)

  # TEST 15: Node equality with same values
  def test_node_equality_same_values(self):
    node_copy = Node(i=0, t=1, p=None, m={"key": "value", "status": "active"}, c=1)
    self.assertEqual(self.node1, node_copy)

  # TEST 16: Node equality with non-Node returns False
  def test_node_equality_non_node(self):
    self.assertNotEqual(self.node1, "not a node")
    self.assertNotEqual(self.node1, None)

  # TEST 17: status property returns correct value
  def test_node_status_active(self):
    node = Node(i=0, t=1, p=None, m={"status": "active"}, c=1)
    self.assertEqual(node.status, "active")

  def test_node_status_deleted(self):
    node = Node(i=0, t=1, p=None, m={"status": "deleted"}, c=1)
    self.assertEqual(node.status, "deleted")

  # TEST 18: Node is hashable (required for use in frozenset)
  def test_node_hashable(self):
    self.assertIsInstance(hash(self.node1), int)

  def test_node_equal_nodes_same_hash(self):
    node_copy = Node(i=0, t=1, p=None, m={"key": "value", "status": "active"}, c=1)
    self.assertEqual(hash(self.node1), hash(node_copy))

  def test_node_in_frozenset(self):
    s = frozenset([self.node2, self.node3])  # node2 == node3, so only one entry
    self.assertEqual(len(s), 1)

  # TEST 19: Vector clock timestamp (dict)
  def test_node_vector_clock_timestamp(self):
    ts = {0: 1, 1: 0, 2: 0}
    node = Node(i=0, t=ts, p=None, m={"status": "active"}, c=1)
    self.assertEqual(node.timestamp, ts)

  def test_node_vector_clock_equality(self):
    ts = {0: 1, 1: 0, 2: 0}
    node_a = Node(i=0, t=ts, p=None, m={"status": "active"}, c=1)
    node_b = Node(i=0, t=ts, p=None, m={"status": "active"}, c=1)
    self.assertEqual(node_a, node_b)

  def test_node_vector_clock_different_timestamps_not_equal(self):
    node_a = Node(i=0, t={0: 1, 1: 0, 2: 0}, p=None, m={"status": "active"}, c=1)
    node_b = Node(i=0, t={0: 2, 1: 0, 2: 0}, p=None, m={"status": "active"}, c=1)
    self.assertNotEqual(node_a, node_b)


if __name__ == "__main__":
  unittest.main()