import unittest

from Phase1.src.tree_crdt.clock.lamport import LamportClock

class TestLamportClock(unittest.TestCase):
  """Test suite for LamportClock"""
  
  def setUp(self):
    """Set up a fresh LamportClock instance for each test."""
    self.clock_node = LamportClock(id=1)

  # TEST: Update (receive event) takes max and increments
  def test_update_receive(self):
    # Current timestamp is 0, receive 5
    self.clock_node.update(5)
    # max(0, 5) + 1 = 6
    self.assertEqual(self.clock_node.timestamp, 6)
    
    # Current timestamp is 6, receive 3
    self.clock_node.update(3)
    # max(6, 3) + 1 = 7
    self.assertEqual(self.clock_node.timestamp, 7)

if __name__ == '__main__':
  unittest.main()
