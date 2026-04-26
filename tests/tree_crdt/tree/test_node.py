import unittest

from tree_crdt.tree import Node

# Given for demonstration purposes
# as you are already provided with the Node class

class TestNode(unittest.TestCase):
  """Test suite for Node class"""
  
  def setUp(self):
    """Set up test nodes."""
    self.node1 = Node(p=None, m={"key": "value"}, c=1)
    self.node2 = Node(p=1, m={"key": "value"}, c=2)
    self.node3 = Node(p=1, m={"key": "value"}, c=2)
    self.node4 = Node(p=1, m={"different": "metadata"}, c=2)

  # TEST 1: Node initialization
  def test_node_initialization(self):
    node = Node(p=5, m={"test": "data"}, c=10)
    self.assertEqual(node(), (5, {"test": "data"}, 10))

  # TEST 2: Node with None parent
  def test_node_with_none_parent(self):
    node = Node(p=None, m={}, c=1)
    p, m, c = node()
    self.assertIsNone(p)
    self.assertEqual(m, {})
    self.assertEqual(c, 1)

  # TEST 3: Node call returns correct tuple
  def test_node_call_returns_tuple(self):
    result = self.node1()
    self.assertIsInstance(result, tuple)
    self.assertEqual(len(result), 3)
    self.assertEqual(result, (None, {"key": "value"}, 1))

  # TEST 4: Node string representation
  def test_node_str(self):
    expected = "Node(p=None,m={'key': 'value'},c=1)"
    actual = str(self.node1)
    self.assertEqual(actual, expected)

  # TEST 5: Nodes with same attributes are equal
  def test_node_equality_same_attributes(self):
    self.assertEqual(self.node2, self.node3)

  # TEST 6: Nodes with different metadata are not equal
  def test_node_equality_different_metadata(self):
    self.assertNotEqual(self.node2, self.node4)

  # TEST 7: Nodes with different parents are not equal
  def test_node_equality_different_parents(self):
    node_a = Node(p=1, m={"key": "value"}, c=2)
    node_b = Node(p=2, m={"key": "value"}, c=2)
    self.assertNotEqual(node_a, node_b)

  # TEST 8: Nodes with different child ids are not equal
  def test_node_equality_different_child_ids(self):
    node_a = Node(p=1, m={"key": "value"}, c=2)
    node_b = Node(p=1, m={"key": "value"}, c=3)
    self.assertNotEqual(node_a, node_b)

  # TEST 9: Node inequality operator
  def test_node_inequality(self):
    self.assertTrue(self.node2 != self.node4)

  # TEST 10: Empty metadata dictionary
  def test_node_empty_metadata(self):
    node = Node(p=5, m={}, c=10)
    _, m, _ = node()
    self.assertEqual(m, {})

  # TEST 11: Complex metadata
  def test_node_complex_metadata(self):
    metadata = {"nested": {"level": 2}, "list": [1, 2, 3], "string": "value"}
    node = Node(p=1, m=metadata, c=2)
    _, m, _ = node()
    self.assertEqual(m, metadata)

  # TEST 12: Node with large child id
  def test_node_large_child_id(self):
    node = Node(p=1, m={}, c=999999)
    _, _, c = node()
    self.assertEqual(c, 999999)

  # TEST 13: Node equality is reflexive
  def test_node_equality_reflexive(self):
    self.assertEqual(self.node1, self.node1)

  # TEST 14: Node equality with same values
  def test_node_equality_same_values(self):
    node_copy = Node(p=None, m={"key": "value"}, c=1)
    self.assertEqual(self.node1, node_copy)


if __name__ == '__main__':
  unittest.main()
