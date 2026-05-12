import unittest
from typing import cast
from unittest.mock import MagicMock, patch

import main
from tree_crdt import Replica
from tree_crdt.clock import VectorClock


class TestMainCore(unittest.TestCase):
    """TIER 1: Core helper functions and move generation."""

    def test_validate_ip_accepts_valid_ipv4(self) -> None:
        """Validate that valid IPv4 addresses are accepted."""
        self.assertTrue(main.validate_ip("127.0.0.1"))
        self.assertTrue(main.validate_ip("192.168.1.10"))
        self.assertTrue(main.validate_ip("255.255.255.255"))

    def test_validate_ip_rejects_invalid_ipv4(self) -> None:
        """Validate that invalid IPv4 addresses are rejected."""
        self.assertFalse(main.validate_ip(""))
        self.assertFalse(main.validate_ip("localhost"))
        self.assertFalse(main.validate_ip("300.1.1.1"))

    def test_hierarchical_move_generator(self) -> None:
        """Test hierarchical tree move generation."""
        self.assertEqual(main.generate_hierarchical_move(0), (None, 0, "root"))
        self.assertEqual(main.generate_hierarchical_move(1), (0, 1, "child"))
        self.assertEqual(main.generate_hierarchical_move(4), (1, 14, "grandchild"))

    def test_wide_move_generator(self) -> None:
        """Test wide tree move generation."""
        self.assertEqual(main.generate_wide_tree_move(3), (0, 3, "wide_child"))

    def test_chain_move_generator(self) -> None:
        """Test chain (deep) tree move generation."""
        self.assertEqual(main.generate_deep_chain_move(0), (None, 0, "chain_node"))
        self.assertEqual(main.generate_deep_chain_move(5), (4, 5, "chain_node"))

    def test_parse_hosts_filters_invalid_values(self) -> None:
        """Test that host parsing correctly filters invalid IPs."""
        hosts = main.parse_hosts("127.0.0.1,invalid,10.0.0.2,256.0.0.1")
        self.assertEqual(hosts, ["127.0.0.1", "10.0.0.2"])

    def test_main_starts_and_joins_processes(self) -> None:
        """Test that main orchestration starts and joins processes."""
        with patch("main.multiprocessing.Process") as process_cls:
            first = MagicMock()
            first.is_alive.return_value = False
            process_cls.return_value = first

            hosts = ["127.0.0.1", "127.0.0.2"]
            main.main(
                num_replicas=2,
                tree_config="hierarchical",
                hosts=hosts,
                main_base=5000,
                listener_base=6000,
            )

            self.assertEqual(process_cls.call_count, 1)
            first.start.assert_called_once()
            first.join.assert_called_once_with()


class TestMainVectorClockBasics(unittest.TestCase):
    """TIER 1: Vector Clock basics and configuration."""

    def test_replica_created_with_vector_clock(self):
        """Test that replicas are created with vector clocks when configured."""
        replica = Replica(id=0, host="127.0.0.1", main_base=5000, listener_base=6000, num_replicas=3)
        
        self.assertIsInstance(replica.clock, VectorClock)
        self.assertEqual(replica.clock.timestamp, {0: 0, 1: 0, 2: 0})

    def test_vector_clock_timestamp_format(self):
        """Test that vector clock timestamps have correct format."""
        replica = Replica(id=1, host="127.0.0.1", main_base=5000, listener_base=6000, num_replicas=3)
        
        move = replica.apply_local_move(None, {"name": "test", "status": "active"}, 1)
        
        timestamp = cast(dict[int, int], move.timestamp)
        self.assertEqual(timestamp.keys(), {0, 1, 2})
        self.assertEqual(timestamp[1], 1)  # Local component incremented


class TestMainRandomMoveGenerator(unittest.TestCase):
    """TIER 2: Advanced random move/delete generation."""

    def setUp(self):
        self.replica = Replica(1, "127.0.0.1", 5000, 6000, 1)

    @patch('main.random.random')
    def test_random_move_delete_empty_tree_creates_root(self, mock_random):
        """Test that random generator creates root on empty tree."""
        mock_random.return_value = 0.5
        parent, child, tree_type = main.generate_random_move_delete(self.replica, 0)
        self.assertIsNone(parent)
        self.assertEqual(child, 1050)  # replica 1 * 1000 + counter 0 + 50
        self.assertEqual(tree_type, "random_root")

    @patch('main.random.random')
    @patch('main.random.choice')
    def test_random_move_delete_moves_current_node(self, mock_choice, mock_random):
        """Test that random generator can move existing nodes."""
        self.replica.apply_local_move(None, {"status": "active"}, 1)
        self.replica.apply_local_move(1, {"status": "active"}, 2)
        mock_random.return_value = 0.5  # Above delete threshold
        mock_choice.side_effect = [2, 1]  # Child to move: 2, new parent: 1

        parent, child, tree_type = main.generate_random_move_delete(self.replica, 5)
        
        self.assertEqual(parent, 1)
        self.assertEqual(child, 2)
        self.assertEqual(tree_type, "random_move")


class TestMainPhase2VectorClock(unittest.TestCase):
    """TIER 2: Phase 2 operations with vector clocks."""

    def setUp(self):
        self.replica = Replica(id=0, host="127.0.0.1", main_base=5000, listener_base=6000, num_replicas=3)

    def test_phase2_move_has_vector_timestamp(self):
        """Test that Phase 2 moves contain vector clock timestamps."""
        with patch('main.random.random', return_value=0.5):
            parent, child, tree_type = main.generate_random_move_delete(self.replica, 0)
            
            self.replica.apply_local_move(parent, {"phase": 2, "type": tree_type}, child)
            
            log_entries = self.replica.log
            self.assertEqual(len(log_entries), 1)
            
            _, timestamp, _, _, metadata, _ = log_entries[-1]
            timestamp = cast(dict[int, int], timestamp)
            self.assertEqual(timestamp[0], 1)


class TestMainVectorClockIntegration(unittest.TestCase):
    """TIER 2: Integration tests for vector clocks."""

    def test_full_workflow_with_vector_clocks(self):
        """Test complete workflow with vector clocks across multiple replicas."""
        num_replicas = 3
        replicas = [
            Replica(id=i, host="127.0.0.1", main_base=5000, listener_base=6000, num_replicas=num_replicas)
            for i in range(num_replicas)
        ]
        
        # Each replica generates moves
        for i, replica in enumerate(replicas):
            for j in range(5):
                parent, child, tree_type = main.generate_hierarchical_move(j)
        
        # Exchange moves between replicas
        for source_replica in replicas:
            for target_replica in replicas:
                if source_replica.id != target_replica.id:
                    for _, ts, _, _, metadata, child in source_replica.log:
                        op = main.MovePayload(source_replica.id, ts, None, metadata, child)
                        target_replica.apply_remote_move(op)
        
        # All replicas should converge to same state
        canonical = replicas[0].tree()
        for replica in replicas[1:]:
            self.assertEqual(replica.tree(), canonical)


if __name__ == '__main__':
    unittest.main()