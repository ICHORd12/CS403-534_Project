import unittest
from typing import cast

from Phase1.src.tree_crdt.replica import Replica
from Phase1.src.tree_crdt.payload import MovePayload
from Phase1.src.tree_crdt.tree import Node

class TestReplicaInitialization(unittest.TestCase):
  """Test suite for Replica initialization and properties"""

  def test_replica_initialization(self):
    """Test that a replica is initialized correctly"""
    replica = Replica(id=0, host="localhost", main_base=5555, listener_base=6666)
    clock_snapshot = replica.clock
    tree_snapshot = replica.tree
    log_entries = replica.log
    
    self.assertEqual(replica.id, 0)
    self.assertIsNotNone(clock_snapshot)
    self.assertEqual(clock_snapshot.timestamp, 0)
    self.assertIsNotNone(tree_snapshot)
    self.assertEqual(len(log_entries), 0)


class TestReplicaSimpleOperations(unittest.TestCase):
  """Test suite for simple in-order operations"""

  def setUp(self):
    """Set up a fresh replica for each test"""
    self.replica = Replica(id=0, host="localhost", main_base=5555, listener_base=6666)

  def test_apply_single_in_order_operation(self):
    """Test applying a single in-order operation"""
    payload = MovePayload(i=0, t=1, p=None, m={"name": "root"}, c=1)
    self.replica.apply_remote_move(payload)
    log_entries = self.replica.log
    
    # Check log was updated
    self.assertEqual(len(log_entries), 1)
    
    # Check tree was updated
    tree_snapshot = self.replica.tree
    nodes = tree_snapshot()
    self.assertEqual(len(nodes), 1)
    
    # Check log entry
    replica_id, timestamp, old_p, new_p, metadata, child = log_entries[0]
    self.assertEqual(replica_id, 0)
    self.assertEqual(timestamp, 1)
    self.assertIsNone(old_p)
    self.assertIsNone(new_p)
    self.assertEqual(metadata, {"name": "root"})
    self.assertEqual(child, 1)

class TestReplicaLocalMoveOperations(unittest.TestCase):
  """Test suite for local_move behavior"""

  def setUp(self):
    self.replica = Replica(id=7, host="localhost", main_base=5555, listener_base=6666)

  def test_local_move_advances_timestamp_monotonically(self):
    move1 = self.replica.apply_local_move(parent=None, metadata={"step": 1}, child=10)
    move2 = self.replica.apply_local_move(parent=10, metadata={"step": 2}, child=11)

    self.assertIsInstance(move1.timestamp, int)
    self.assertIsInstance(move2.timestamp, int)
    move1_timestamp = cast(int, move1.timestamp)
    move2_timestamp = cast(int, move2.timestamp)
    self.assertEqual(move2_timestamp, move1_timestamp + 1)


class TestReplicaOutOfOrderOperations(unittest.TestCase):
  """Test suite for out-of-order operations requiring undo/redo"""

  def setUp(self):
    """Set up a fresh replica for each test"""
    self.replica = Replica(id=0, host="localhost", main_base=5555, listener_base=6666)
  
  def test_undo_redo_preserves_tree_state(self):
    """Test that undo/redo preserves correct tree state"""
    # Build initial tree: 1 -> 2, 1 -> 3
    payload1 = MovePayload(i=0, t=1, p=None, m={}, c=1)
    payload2 = MovePayload(i=0, t=2, p=1, m={}, c=2)
    payload3 = MovePayload(i=0, t=3, p=1, m={}, c=3)
    
    self.replica.apply_remote_move(payload1)
    self.replica.apply_remote_move(payload2)
    self.replica.apply_remote_move(payload3)
    tree_snapshot = self.replica.tree

    baseline_state = {
      node.child: (node.parent, node.metadata)
      for node in tree_snapshot()
    }
    
    # Test with a clearly out-of-order scenario
    payload_insert = MovePayload(i=0, t=2, p=1, m={}, c=4)  # Another op with t=2

    self.replica.apply_remote_move(payload_insert)

    tree_snapshot = self.replica.tree
    nodes_after = tree_snapshot()
    self.assertEqual(len(nodes_after), 4)

    # Existing nodes should preserve parent and metadata after undo/redo.
    after_state = {
      node.child: (node.parent, node.metadata)
      for node in nodes_after
    }
    for child in [1, 2, 3]:
      self.assertIn(child, after_state)
      self.assertEqual(after_state[child], baseline_state[child])

    inserted_node = cast(Node, tree_snapshot[4])
    self.assertIsNotNone(inserted_node)
    self.assertEqual(inserted_node.parent, 1)

    # Log should remain in total order after inserting an out-of-order move.
    log_entries = self.replica.log
    ordered_keys = [(timestamp, replica_id) for replica_id, timestamp, _, _, _, _ in log_entries]
    self.assertEqual(ordered_keys, sorted(ordered_keys))

  def test_same_timestamp_orders_by_replica_id(self):
    """Test Lamport total-order tie-breaker by replica ID at same timestamp."""
    self.replica.apply_remote_move(MovePayload(i=2, t=5, p=None, m={"n": 2}, c=20))
    self.replica.apply_remote_move(MovePayload(i=1, t=5, p=None, m={"n": 1}, c=10))
    log_entries = self.replica.log

    observed_order = [(replica_id, timestamp) for replica_id, timestamp, _, _, _, _ in log_entries]
    self.assertEqual(observed_order, [(1, 5), (2, 5)])


class TestReplicaLogManagement(unittest.TestCase):
  """Test suite for operation log management"""

  def setUp(self):
    """Set up a fresh replica for each test"""
    self.replica = Replica(id=0, host="localhost", main_base=5555, listener_base=6666)

  def test_operation_log_records_old_parent(self):
    """Test that operation log records the old parent when node exists"""
    # Add initial node
    self.replica.apply_remote_move(MovePayload(i=0, t=1, p=None, m={}, c=1))
    
    # Move node to different parent
    self.replica.apply_remote_move(MovePayload(i=0, t=2, p=2, m={}, c=1))
    log_entries = self.replica.log
    
    # Second log entry should record old parent as None
    _, _, old_p, new_p, _, _ = log_entries[1]
    self.assertIsNone(old_p)
    self.assertEqual(new_p, 2)


class TestReplicaStringRepresentations(unittest.TestCase):
  """Test suite for string representations"""

  def test_replica_str(self):
    """Test replica string representation"""
    replica = Replica(id=3, host="localhost", main_base=5555, listener_base=6666)
    str_repr = str(replica)
    
    self.assertIsInstance(str_repr, str)
    self.assertIn("ID: 3", str_repr)
    self.assertIn("Timestamp: 0", str_repr)


class TestReplicaEdgeCases(unittest.TestCase):
  """Test suite for edge cases and boundary conditions"""

  def setUp(self):
    """Set up a fresh replica for each test"""
    self.replica = Replica(id=0, host="localhost", main_base=5555, listener_base=6666)

  def test_operation_replacing_existing_node(self):
    """Test operation that replaces an existing node"""
    # Add node
    self.replica.apply_remote_move(MovePayload(i=0, t=1, p=None, m={"v": 1}, c=1))
    
    # Replace with new metadata
    self.replica.apply_remote_move(MovePayload(i=0, t=2, p=None, m={"v": 2}, c=1))
    log_entries = self.replica.log
    
    # Should have 2 log entries
    self.assertEqual(len(log_entries), 2)
    
    # But tree should still have 1 node with new metadata
    tree_snapshot = self.replica.tree
    nodes = tree_snapshot()
    self.assertEqual(len(nodes), 1)
    node = cast(Node, tree_snapshot[1])
    self.assertEqual(node.metadata, {"v": 2})


class TestReplicaIntegration(unittest.TestCase):
  """Integration tests for complex scenarios"""

  def test_interleaved_operations_from_multiple_replicas(self):
    """Test interleaved operations from multiple replicas"""
    replica = Replica(id=0, host="localhost", main_base=5555, listener_base=6666)
    
    # Replica 0 at t=1,3,5
    replica.apply_remote_move(MovePayload(i=0, t=1, p=None, m={}, c=1))
    replica.apply_remote_move(MovePayload(i=0, t=3, p=1, m={}, c=3))
    replica.apply_remote_move(MovePayload(i=0, t=5, p=3, m={}, c=5))
    
    # Replica 1 at t=2,4
    replica.apply_remote_move(MovePayload(i=1, t=2, p=1, m={}, c=2))
    replica.apply_remote_move(MovePayload(i=1, t=4, p=2, m={}, c=4))
    log_entries = replica.log
    
    # Log should have all operations ordered
    self.assertEqual(len(log_entries), 5)
    timestamps = [t for _, t, _, _, _, _ in log_entries]
    self.assertEqual(timestamps, [1, 2, 3, 4, 5])

if __name__ == '__main__':
  unittest.main()
