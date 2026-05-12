import unittest

from Phase1.src.tree_crdt.tree import Node, Tree

class TestTree(unittest.TestCase):
  """Test suite for Tree class"""
  
  def setUp(self):
    """Set up a fresh Tree instance for each test."""
    self.tree = Tree()

  # TEST: Tree initialization is empty
  def test_tree_initialization(self):
    nodes = self.tree()
    self.assertIsInstance(nodes, set)
    self.assertEqual(len(nodes), 0)

  # TEST: Add a single node to tree
  def test_add_single_node(self):
    node = Node(p=None, m={"id": 1}, c=1)
    result = self.tree.move(node)
    
    # move() should return None
    self.assertIsNone(result)
    
    # Node should be in tree
    nodes = self.tree()
    self.assertIn(node, nodes)
    self.assertEqual(len(nodes), 1)

  # TEST: Replacing a node with different metadata
  def test_replace_node_different_metadata(self):
    node1 = Node(p=None, m={"version": 1}, c=1)
    node2 = Node(p=None, m={"version": 2}, c=1)
    
    self.tree.move(node1)
    self.tree.move(node2)
    
    nodes = self.tree()
    self.assertEqual(len(nodes), 1)
    self.assertIn(node2, nodes)
    self.assertNotIn(node1, nodes)

  # TEST: Moving node to different parent (reparenting)
  def test_move_node_to_sibling_parent(self):
    # Initial tree: 1 -> (2, 3)
    node1 = Node(p=None, m={}, c=1)
    node2 = Node(p=1, m={}, c=2)
    node3 = Node(p=1, m={}, c=3)
    
    self.tree.move(node1)
    self.tree.move(node2)
    self.tree.move(node3)
    
    # Move node2 to be a child of node3
    node2_moved = Node(p=3, m={}, c=2)
    self.tree.move(node2_moved)
    
    result_nodes = self.tree()
    self.assertIn(node2_moved, result_nodes)
    self.assertNotIn(node2, result_nodes)

  # TEST: Cannot create a cycle (child cannot be ancestor of parent)
  def test_prevent_cycle_direct(self):
    # Create a parent-child relationship: 1 -> 2
    node1 = Node(p=None, m={}, c=1)
    node2 = Node(p=1, m={}, c=2)
    
    self.tree.move(node1)
    self.tree.move(node2)
    
    # Try to make the child the parent of the original parent (creates cycle)
    node1_modified = Node(p=2, m={}, c=1)
    self.tree.move(node1_modified)
    
    # node1_modified should not be added because it would create a cycle
    nodes = self.tree()
    # Original node1 should still be there
    self.assertIn(node1, nodes)
    # Modified node should not be there
    self.assertNotIn(node1_modified, nodes)

if __name__ == '__main__':
  unittest.main()
