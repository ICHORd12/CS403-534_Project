import unittest
from Phase1.src.tree_crdt.payload import MovePayload

# Given for demonstration purposes
# as you are already provided with the MovePayload class

class TestMovePayloadInitialization(unittest.TestCase):
  """Test MovePayload initialization and basic properties."""

  def test_initialization_with_valid_parameters(self):
    """Test MovePayload initializes correctly with valid parameters."""
    move = MovePayload(i=1, t=100, p=2, m={"key": "value"}, c=3)
    self.assertEqual(move.id, 1)
    self.assertEqual(move.timestamp, 100)
    self.assertEqual(move.parent, 2)
    self.assertEqual(move.metadata, {"key": "value"})
    self.assertEqual(move.child, 3)

  def test_initialization_with_none_parent(self):
    """Test MovePayload initializes with None parent."""
    move = MovePayload(i=1, t=50, p=None, m={}, c=2)
    self.assertEqual(move.id, 1)
    self.assertEqual(move.timestamp, 50)
    self.assertIsNone(move.parent)
    self.assertEqual(move.metadata, {})
    self.assertEqual(move.child, 2)

  def test_initialization_with_empty_metadata(self):
    """Test MovePayload initializes with empty metadata dict."""
    move = MovePayload(i=5, t=200, p=10, m={}, c=15)
    self.assertEqual(move.metadata, {})

  def test_initialization_with_complex_metadata(self):
    """Test MovePayload initializes with nested/complex metadata."""
    metadata = {"name": "test", "nested": {"key": "value"}, "list": [1, 2, 3]}
    move = MovePayload(i=1, t=100, p=2, m=metadata, c=3)
    self.assertEqual(move.metadata, metadata)
    self.assertEqual(move.metadata["nested"]["key"], "value")
    self.assertEqual(move.metadata["list"], [1, 2, 3])


class TestMovePayloadProperties(unittest.TestCase):
  """Test MovePayload property accessors."""

  def setUp(self):
    """Set up test fixtures."""
    self.move = MovePayload(i=42, t=999, p=7, m={"test": "data"}, c=99)

  def test_id_property(self):
    """Test id property returns correct value."""
    self.assertEqual(self.move.id, 42)

  def test_timestamp_property(self):
    """Test timestamp property returns correct value."""
    self.assertEqual(self.move.timestamp, 999)

  def test_parent_property(self):
    """Test parent property returns correct value."""
    self.assertEqual(self.move.parent, 7)

  def test_metadata_property(self):
    """Test metadata property returns correct value."""
    self.assertEqual(self.move.metadata, {"test": "data"})

  def test_child_property(self):
    """Test child property returns correct value."""
    self.assertEqual(self.move.child, 99)

  def test_metadata_property_returns_reference(self):
    """Test metadata property returns the exact metadata dict."""
    expected_metadata = {"x": 1, "y": 2}
    move = MovePayload(i=1, t=100, p=2, m=expected_metadata, c=3)
    self.assertIs(move.metadata, expected_metadata)


class TestMovePayloadCallable(unittest.TestCase):
  """Test MovePayload __call__ method."""

  def test_call_returns_tuple(self):
    """Test __call__ returns a tuple of (parent, metadata, child)."""
    move = MovePayload(i=1, t=100, p=5, m={"data": "test"}, c=10)
    result = move()
    self.assertIsInstance(result, tuple)
    self.assertEqual(len(result), 3)

  def test_call_returns_correct_values(self):
    """Test __call__ returns correct parent, metadata, and child."""
    metadata = {"key": "value"}
    move = MovePayload(i=1, t=100, p=3, m=metadata, c=7)
    parent, meta, child = move()
    self.assertEqual(parent, 3)
    self.assertEqual(meta, metadata)
    self.assertEqual(child, 7)

  def test_call_with_none_parent(self):
    """Test __call__ with None parent."""
    move = MovePayload(i=1, t=100, p=None, m={}, c=5)
    parent, meta, child = move()
    self.assertIsNone(parent)
    self.assertEqual(meta, {})
    self.assertEqual(child, 5)

  def test_call_with_empty_metadata(self):
    """Test __call__ with empty metadata."""
    move = MovePayload(i=1, t=100, p=2, m={}, c=3)
    parent, meta, child = move()
    self.assertEqual(parent, 2)
    self.assertEqual(meta, {})
    self.assertEqual(child, 3)

  def test_call_with_complex_metadata(self):
    """Test __call__ with complex metadata."""
    metadata = {"nested": {"deep": "value"}, "array": [1, 2, 3]}
    move = MovePayload(i=1, t=100, p=2, m=metadata, c=3)
    parent, meta, child = move()
    self.assertEqual(parent, 2)
    self.assertEqual(meta, metadata)
    self.assertEqual(meta["nested"]["deep"], "value")
    self.assertEqual(child, 3)


class TestMovePayloadStringRepresentations(unittest.TestCase):
  """Test MovePayload string representations."""

  def test_str_format(self):
    """Test __str__ returns formatted string."""
    move = MovePayload(i=1, t=10, p=2, m={"x": 1}, c=3)
    str_repr = str(move)
    # Format: "i,(t,p,m,m)" with duplicate metadata in original implementation
    self.assertIn("1", str_repr)
    self.assertIn("10", str_repr)
    self.assertIn("2", str_repr)

  def test_str_with_none_parent(self):
    """Test __str__ with None parent."""
    move = MovePayload(i=5, t=50, p=None, m={}, c=10)
    str_repr = str(move)
    self.assertIn("5", str_repr)
    self.assertIn("50", str_repr)
    self.assertIn("None", str_repr)

class TestMovePayloadEdgeCases(unittest.TestCase):
  """Test MovePayload edge cases and boundary conditions."""

  def test_zero_values(self):
    """Test MovePayload with zero values."""
    move = MovePayload(i=0, t=0, p=0, m={}, c=0)
    self.assertEqual(move.id, 0)
    self.assertEqual(move.timestamp, 0)
    self.assertEqual(move.parent, 0)
    self.assertEqual(move.child, 0)

  def test_negative_values(self):
    """Test MovePayload with negative values."""
    move = MovePayload(i=-1, t=-100, p=-5, m={}, c=-10)
    self.assertEqual(move.id, -1)
    self.assertEqual(move.timestamp, -100)
    self.assertEqual(move.parent, -5)
    self.assertEqual(move.child, -10)

  def test_large_values(self):
    """Test MovePayload with large values."""
    large_int = 10**18
    move = MovePayload(i=large_int, t=large_int, p=large_int, m={}, c=large_int)
    self.assertEqual(move.id, large_int)
    self.assertEqual(move.timestamp, large_int)
    self.assertEqual(move.parent, large_int)
    self.assertEqual(move.child, large_int)

  def test_metadata_with_special_characters(self):
    """Test metadata with special characters and Unicode."""
    metadata: dict[str, str] = {"emoji": "🚀", "special": "@#$%", "unicode": "日本語"}
    move = MovePayload(i=1, t=100, p=2, m=metadata, c=3)
    self.assertEqual(move.metadata["emoji"], "🚀")
    self.assertEqual(move.metadata["special"], "@#$%")
    self.assertEqual(move.metadata["unicode"], "日本語")

  def test_metadata_with_nested_empty_dicts(self):
    """Test metadata with nested empty dictionaries."""
    metadata: dict = {"outer": {"inner": {}}}
    move = MovePayload(i=1, t=100, p=2, m=metadata, c=3)
    self.assertEqual(move.metadata["outer"]["inner"], {})

  def test_metadata_modification_after_creation(self):
    """Test that modifying original metadata affects move's metadata."""
    metadata = {"key": "value"}
    move = MovePayload(i=1, t=100, p=2, m=metadata, c=3)
    metadata["key"] = "modified"
    self.assertEqual(move.metadata["key"], "modified")

  def test_multiple_instances_independence(self):
    """Test that multiple instances don't share state."""
    move1 = MovePayload(i=1, t=100, p=2, m={"data": "move1"}, c=3)
    move2 = MovePayload(i=4, t=200, p=5, m={"data": "move2"}, c=6)
    
    self.assertEqual(move1.id, 1)
    self.assertEqual(move2.id, 4)
    self.assertEqual(move1.metadata["data"], "move1")
    self.assertEqual(move2.metadata["data"], "move2")


class TestMovePayloadIntegration(unittest.TestCase):
  """Integration tests for MovePayload."""

  def test_create_and_unpack(self):
    """Test creating and unpacking a MovePayload in one operation."""
    move = MovePayload(i=1, t=100, p=2, m={"test": "data"}, c=3)
    parent, metadata, child = move()
    
    self.assertEqual(parent, move.parent)
    self.assertEqual(metadata, move.metadata)
    self.assertEqual(child, move.child)

  def test_move_lifecycle(self):
    """Test typical lifecycle of MovePayload usage."""
    # Create a move
    move = MovePayload(i=10, t=500, p=20, m={"status": "active"}, c=30)
    
    # Verify all properties
    self.assertEqual(move.id, 10)
    self.assertEqual(move.timestamp, 500)
    self.assertEqual(move.parent, 20)
    self.assertEqual(move.metadata, {"status": "active"})
    self.assertEqual(move.child, 30)
    
    # Unpack
    p, m, c = move()
    self.assertEqual((p, m, c), (20, {"status": "active"}, 30))

  def test_sequence_of_moves(self):
    """Test creating a sequence of related moves."""
    moves = [
      MovePayload(i=1, t=10, p=None, m={}, c=2),
      MovePayload(i=2, t=20, p=1, m={"level": 1}, c=3),
      MovePayload(i=3, t=30, p=2, m={"level": 2}, c=4),
    ]
    
    # Verify sequence integrity
    self.assertEqual(moves[0].child, moves[1].id)
    self.assertEqual(moves[1].parent, moves[0].id)
    self.assertEqual(moves[1].child, moves[2].id)
    self.assertEqual(moves[2].parent, moves[1].id)


if __name__ == "__main__":
  unittest.main()
