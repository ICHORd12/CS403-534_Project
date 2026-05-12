import unittest

from tree_crdt.clock import VectorClock


class TestVectorClock(unittest.TestCase):
	"""Test suite for VectorClock implementation.
	
	Covers: initialization, update operations, comparison operations,
	string representations, immutability, and multi-node scenarios.
	"""

	def setUp(self):
		"""Set up a fresh VectorClock instance for each test."""
		self.clock_node = VectorClock(id=1, max_id=3)

	# =========================================================================
	# Initialization Tests
	# =========================================================================

	def test_initial_state(self):
		"""Test 1: Verify initial state of VectorClock."""
		self.assertEqual(self.clock_node.id, 1)
		self.assertEqual(self.clock_node.timestamp, {0: 0, 1: 0, 2: 0})

	# =========================================================================
	# Local Update Tests
	# =========================================================================

	def test_update_local(self):
		"""Test 2: Local event increments only the local component."""
		self.clock_node.update(None)
		self.assertEqual(self.clock_node.timestamp, {0: 0, 1: 1, 2: 0})

		self.clock_node.update(None)
		self.assertEqual(self.clock_node.timestamp, {0: 0, 1: 2, 2: 0})

	# =========================================================================
	# Receive Update Tests
	# =========================================================================

	def test_update_receive(self):
		"""Test 3: Receive event takes component-wise max and increments local."""
		# Current timestamp is {0: 0, 1: 0, 2: 0}, receive a larger vector.
		self.clock_node.update({0: 5, 1: 1, 2: 3})
		# max({0,0,0}, {5,1,3}) then local increment at id=1.
		self.assertEqual(self.clock_node.timestamp, {0: 5, 1: 2, 2: 3})

		# Current timestamp is {0: 5, 1: 2, 2: 3}, receive mixed values.
		self.clock_node.update({0: 4, 1: 7, 2: 3})
		# Component-wise max gives {0: 5, 1: 7, 2: 3}, then local increment.
		self.assertEqual(self.clock_node.timestamp, {0: 5, 1: 8, 2: 3})

	# =========================================================================
	# String Representation Tests
	# =========================================================================

	def test_string_repr_str(self):
		"""Test 4: String representation format."""
		self.clock_node.update(None)
		self.assertEqual(str(self.clock_node), "{0: 0, 1: 1, 2: 0}")

	# =========================================================================
	# Multi-Node Scenario Tests
	# =========================================================================

	def test_multiple_nodes(self):
		"""Test 5: Multiple nodes exchanging timestamps."""
		node_a = VectorClock(id=0, max_id=3)
		node_b = VectorClock(id=1, max_id=3)

		# Node A local event.
		node_a.update(None)  # A: {0: 1, 1: 0, 2: 0}

		# Node B receives from A.
		node_b.update(node_a.timestamp)  # B: {0: 1, 1: 1, 2: 0}
		self.assertEqual(node_b.timestamp, {0: 1, 1: 1, 2: 0})

		# Node A receives from B.
		node_a.update(node_b.timestamp)  # A: {0: 2, 1: 1, 2: 0}
		self.assertEqual(node_a.timestamp, {0: 2, 1: 1, 2: 0})

	def test_concurrent_events_detection(self):
		"""Test: Vector clocks can detect concurrent events."""
		node_a = VectorClock(id=0, max_id=3)
		node_b = VectorClock(id=1, max_id=3)

		# Both nodes do local events independently
		node_a.update(None)  # A: {0: 1, 1: 0, 2: 0}
		node_b.update(None)  # B: {0: 0, 1: 1, 2: 0}

		# Neither timestamp is less than the other (concurrent)
		ts_a = node_a.timestamp
		ts_b = node_b.timestamp
		
		# A is not < B (because A[0]=1 > B[0]=0)
		self.assertFalse(VectorClock.timestamp_lt(ts_a, ts_b))
		# B is not < A (because B[1]=1 > A[1]=0)
		self.assertFalse(VectorClock.timestamp_lt(ts_b, ts_a))
		# A is not == B
		self.assertFalse(VectorClock.timestamp_eq(ts_a, ts_b))

	# =========================================================================
	# Immutability and Safety Tests
	# =========================================================================

	def test_timestamp_property_returns_copy(self):
		"""Test 6: Timestamp accessor returns a copy."""
		observed = self.clock_node.timestamp
		observed[1] = 99

		self.assertEqual(self.clock_node.timestamp, {0: 0, 1: 0, 2: 0})

	# =========================================================================
	# Comparison Operation Tests
	# =========================================================================

	def test_timestamp_less_than(self):
		"""Test: timestamp_lt for vector clocks."""
		ts1 = {0: 1, 1: 2, 2: 3}
		ts2 = {0: 2, 1: 3, 2: 4}
		ts3 = {0: 1, 1: 2, 2: 3}
		
		self.assertTrue(VectorClock.timestamp_lt(ts1, ts2))
		self.assertFalse(VectorClock.timestamp_lt(ts2, ts1))
		self.assertFalse(VectorClock.timestamp_lt(ts1, ts3))
		self.assertFalse(VectorClock.timestamp_lt(ts3, ts1))

	def test_timestamp_less_than_or_equal(self):
		"""Test: timestamp_le for vector clocks."""
		ts1 = {0: 1, 1: 2, 2: 3}
		ts2 = {0: 2, 1: 3, 2: 4}
		ts3 = {0: 1, 1: 2, 2: 3}
		
		self.assertTrue(VectorClock.timestamp_le(ts1, ts2))
		self.assertFalse(VectorClock.timestamp_le(ts2, ts1))
		self.assertTrue(VectorClock.timestamp_le(ts1, ts3))
		self.assertTrue(VectorClock.timestamp_le(ts3, ts1))

	def test_timestamp_equal(self):
		"""Test: timestamp_eq for vector clocks."""
		ts1 = {0: 1, 1: 2, 2: 3}
		ts2 = {0: 1, 1: 2, 2: 3}
		ts3 = {0: 1, 1: 2, 2: 4}
		
		self.assertTrue(VectorClock.timestamp_eq(ts1, ts2))
		self.assertFalse(VectorClock.timestamp_eq(ts1, ts3))

	def test_timestamp_comparison_different_keys(self):
		"""Test: Timestamp comparison with different keys returns False."""
		ts1 = {0: 1, 1: 2}
		ts2 = {0: 1, 1: 2, 2: 3}
		
		self.assertFalse(VectorClock.timestamp_eq(ts1, ts2))
		self.assertFalse(VectorClock.timestamp_le(ts1, ts2))
		self.assertFalse(VectorClock.timestamp_lt(ts1, ts2))

	# =========================================================================
	# Edge Case Tests
	# =========================================================================

	def test_idempotent_receive(self):
		"""Test: Receiving same timestamp twice shows expected behavior."""
		self.clock_node.update(None)  # {0: 0, 1: 1, 2: 0}
		
		# Receive a larger timestamp - takes max then increments local
		self.clock_node.update({0: 5, 1: 5, 2: 5})  # max({0:0,1:1,2:0}, {0:5,1:5,2:5}) + inc(1) = {0: 5, 1: 6, 2: 5}
		self.clock_node.update({0: 5, 1: 5, 2: 5})  # max({0:5,1:6,2:5}, {0:5,1:5,2:5}) + inc(1) = {0: 5, 1: 7, 2: 5}
		
		# Non-local components stay at the max value (5)
		self.assertEqual(self.clock_node.timestamp[0], 5)
		self.assertEqual(self.clock_node.timestamp[2], 5)
		# Local component increments each time (1 -> 6 -> 7)
		self.assertEqual(self.clock_node.timestamp[1], 7)


if __name__ == '__main__':
	unittest.main()
