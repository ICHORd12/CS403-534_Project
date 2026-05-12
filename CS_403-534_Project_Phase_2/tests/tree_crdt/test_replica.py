import unittest
from typing import Any, cast

from tree_crdt.clock import VectorClock
from tree_crdt.payload import MovePayload
from tree_crdt.replica import Replica


def tier(level: str):
    """Decorator to mark test tier (MVP/Advanced)."""
    def decorator(func):
        func.tier = level
        return func
    return decorator


class ReplicaTestMixin:
    """Shared helpers for replica tests."""

    replica: Replica

    def _new_replica(self, num_replicas: int | None = None) -> Replica:
        return Replica(id=0, host="localhost", main_base=5555, listener_base=6666, num_replicas=num_replicas)

    def _remote_timestamp(self, num_replicas: int | None, t: int, sender: int = 0) -> int | dict[int, int]:
        if num_replicas is None:
            return t
        return {i: (t if i == sender else 0) for i in range(num_replicas)}


class TestReplicaCore(unittest.TestCase, ReplicaTestMixin):
    """TIER 1: Replica initialization and basic properties."""

    @tier("MVP")
    def test_replica_initialization_vector(self):
        replica = self._new_replica(num_replicas=3)
        self.assertIsInstance(replica.clock, VectorClock)
        self.assertEqual(replica.clock.timestamp, {0: 0, 1: 0, 2: 0})

    @tier("MVP")
    def test_replica_properties(self):
        replica = Replica(id=1, host="127.0.0.1", main_base=5000, listener_base=6000, num_replicas=3)
        self.assertEqual(replica.main_addr, "tcp://127.0.0.1:5001")
        self.assertEqual(replica.listener_addr, "tcp://127.0.0.1:6001")

    @tier("MVP")
    def test_replica_tree_initialization_vector(self):
        replica = self._new_replica(num_replicas=3)
        self.assertEqual(len(replica.tree()), 0)

    @tier("MVP")
    def test_replica_log_initialization(self):
        replica = self._new_replica(num_replicas=3)
        self.assertEqual(replica.log, [])

    @tier("MVP")
    def test_replica_clock_initialization_vector(self):
        replica = self._new_replica(num_replicas=6)
        self.assertEqual(replica.clock.timestamp, {i: 0 for i in range(6)})


class TestReplicaBasicOperations(unittest.TestCase, ReplicaTestMixin):
    """TIER 1: Basic in-order operations and local moves."""

    def setUp(self) -> None:
        self.replica = self._new_replica(num_replicas=3)

    @tier("MVP")
    def test_apply_single_in_order_operation_vector(self):
        ts = self._remote_timestamp(3, 1)
        self.replica.apply_remote_move(MovePayload(i=0, t=ts, p=None, m={"name": "root", "status": "active"}, c=1))
        self.assertEqual(len(self.replica.log), 1)
        self.assertEqual(len(self.replica.tree()), 1)

    @tier("MVP")
    def test_apply_multiple_in_order_operations_vector(self):
        for t, child, parent in [(1, 1, None), (2, 2, 1), (3, 3, 1)]:
            self.replica.apply_remote_move(MovePayload(i=0, t=self._remote_timestamp(3, t), p=parent, m={"status": "active"}, c=child))
        self.assertEqual(len(self.replica.log), 3)
        self.assertEqual(len(self.replica.tree()), 3)

    @tier("MVP")
    def test_operation_updates_node_in_tree_vector(self):
        ts = self._remote_timestamp(3, 1)
        self.replica.apply_remote_move(MovePayload(i=0, t=ts, p=None, m={"value": 42, "status": "active"}, c=1))
        node = next(iter(self.replica.tree[1]))
        self.assertEqual(node.child, 1)
        self.assertEqual(node.metadata, {"applied": True, "value": 42, "status": "active"})

    @tier("MVP")
    def test_local_move_returns_payload_for_local_replica_vector(self):
        payload = self.replica.apply_local_move(parent=None, metadata={"name": "root", "status": "active"}, child=1)
        self.assertEqual(payload.id, self.replica.id)
        self.assertIsNone(payload.parent)
        self.assertEqual(payload.child, 1)

    @tier("MVP")
    def test_local_move_updates_tree_and_log_vector(self):
        self.replica.apply_local_move(parent=None, metadata={"name": "root", "status": "active"}, child=100)
        self.replica.apply_local_move(parent=100, metadata={"name": "child", "status": "active"}, child=101)

        self.assertEqual(len(self.replica.log), 2)
        self.assertEqual(len(self.replica.tree()), 2)
        child_node = next(iter(self.replica.tree[101]))
        self.assertEqual(child_node.parent, 100)

    @tier("MVP")
    def test_local_move_increments_vector_clock(self):
        initial = cast(dict[int, int], self.replica.clock.timestamp).copy()
        self.replica.apply_local_move(None, {"name": "test", "status": "active"}, 1)
        new_ts = cast(dict[int, int], self.replica.clock.timestamp)
        self.assertEqual(new_ts[0], initial[0] + 1)
        self.assertEqual(new_ts[1], initial[1])
        self.assertEqual(new_ts[2], initial[2])


class TestReplicaVectorSemantics(unittest.TestCase, ReplicaTestMixin):
    """TIER 1: Vector clock peer tracking and ordering."""

    def setUp(self) -> None:
        self.replica = self._new_replica(num_replicas=3)

    @tier("MVP")
    def test_get_peer_timestamp_initial_vector(self):
        self.assertEqual(self.replica.get_peer_timestamp(1), {0: 0, 1: 0, 2: 0})

    @tier("MVP")
    def test_get_peer_timestamp_recorded(self):
        ts = {0: 1, 1: 5, 2: 0}
        self.replica.record_last_timestamp(1, ts)
        self.assertEqual(self.replica.get_peer_timestamp(1), ts)

    @tier("MVP")
    def test_get_peer_timestamp_immutable(self):
        ts = {0: 1, 1: 5, 2: 0}
        self.replica.record_last_timestamp(1, ts)
        observed = cast(dict[int, int], self.replica.get_peer_timestamp(1))
        observed[1] = 999
        self.assertEqual(self.replica.get_peer_timestamp(1), ts)

    @tier("MVP")
    def test_operation_log_records_operation_vector(self):
        ts = self._remote_timestamp(3, 10, sender=2)
        payload = MovePayload(i=2, t=ts, p=5, m={"key": "value", "status": "active"}, c=20)
        self.replica.apply_remote_move(payload)

        replica_id, timestamp, old_p, new_p, metadata, child = self.replica.log[0]
        self.assertEqual(replica_id, 2)
        self.assertEqual(timestamp, ts)
        self.assertIsNone(old_p)
        self.assertEqual(new_p, 5)
        self.assertEqual(metadata, {"applied": True, "key": "value", "status": "active"})
        self.assertEqual(child, 20)

    @tier("MVP")
    def test_out_of_order_vector_clock_reinsertion(self):
        op2 = MovePayload(i=0, t={0: 2, 1: 0, 2: 0}, p=None, m={"name": "op2"}, c=1)
        op1 = MovePayload(i=0, t={0: 1, 1: 0, 2: 0}, p=None, m={"name": "op1"}, c=1)
        self.replica.apply_remote_move(op2)
        self.replica.apply_remote_move(op1)
        timestamps = [ts for _, ts, _, _, _, _ in self.replica.log]
        self.assertEqual(timestamps, [{0: 1, 1: 0, 2: 0}, {0: 2, 1: 0, 2: 0}])

    @tier("MVP")
    def test_concurrent_vector_clock_operations(self):
        op1 = MovePayload(i=0, t={0: 1, 1: 0, 2: 0}, p=None, m={"name": "op1", "status": "deleted"}, c=1)
        op2 = MovePayload(i=1, t={0: 0, 1: 1, 2: 0}, p=None, m={"name": "op2", "status": "deleted"}, c=1)
        self.replica.apply_remote_move(op1)
        self.replica.apply_remote_move(op2)
        self.assertEqual(len(self.replica.log), 2)
        self.assertEqual(len(self.replica.tree[1]), 2)


class TestReplicaAdvanced(unittest.TestCase, ReplicaTestMixin):
    """TIER 2: Advanced vector-clock and compaction scenarios."""

    def setUp(self) -> None:
        self.replica = self._new_replica(num_replicas=3)

    @tier("Advanced")
    def test_operation_log_records_old_parent_vector(self):
        self.replica.apply_remote_move(MovePayload(i=0, t=self._remote_timestamp(3, 1), p=None, m={"status": "active"}, c=1))
        self.replica.apply_remote_move(MovePayload(i=0, t=self._remote_timestamp(3, 2), p=2, m={"status": "active"}, c=1))
        _, _, old_p, new_p, _, _ = self.replica.log[1]
        self.assertIsNone(old_p)
        self.assertEqual(new_p, 2)

    @tier("Advanced")
    def test_operation_log_persists_metadata_vector(self):
        m1 = {"version": 1, "author": "replica_0", "status": "active"}
        m2 = {"version": 2, "author": "replica_1", "status": "active"}
        self.replica.apply_remote_move(MovePayload(i=0, t=self._remote_timestamp(3, 1), p=None, m=m1, c=1))
        self.replica.apply_remote_move(MovePayload(i=0, t=self._remote_timestamp(3, 2), p=1, m=m2, c=2))

        _, _, _, _, log_m1, _ = self.replica.log[0]
        _, _, _, _, log_m2, _ = self.replica.log[1]
        strip = lambda m: {k: v for k, v in m.items() if k != "applied"}
        self.assertEqual(strip(log_m1), strip(m1))
        self.assertEqual(strip(log_m2), strip(m2))

    @tier("Advanced")
    def test_log_compaction_with_vector_clocks(self):
        self.replica.apply_local_move(None, {"name": "op1", "status": "active"}, 1)
        self.replica.apply_local_move(1, {"name": "op2", "status": "active"}, 2)
        self.replica.apply_local_move(2, {"name": "op3", "status": "active"}, 3)

        self.replica.record_last_timestamp(1, {0: 2, 1: 0, 2: 0})
        self.replica.record_last_timestamp(2, {0: 2, 1: 0, 2: 0})
        cast(Any, self.replica)._Replica__compact_log()

        self.assertGreater(len(self.replica.log), 0)

    @tier("Advanced")
    def test_tree_snapshot_updated_on_compaction(self):
        self.replica.apply_local_move(None, {"name": "test", "status": "active"}, 1)
        self.replica.record_last_timestamp(1, {0: 2, 1: 0, 2: 0})
        self.replica.record_last_timestamp(2, {0: 2, 1: 0, 2: 0})
        self.replica.apply_local_move(None, {"name": "trigger", "status": "active"}, 2)

        self.assertEqual(len(self.replica.tree_snapshot()), 1)

    @tier("Advanced")
    def test_concurrent_delete_vs_active(self):
        op_active = MovePayload(i=0, t={0: 1, 1: 0, 2: 0}, p=None, m={"status": "active"}, c=1)
        op_delete = MovePayload(i=1, t={0: 0, 1: 1, 2: 0}, p=None, m={"status": "deleted"}, c=1)

        self.replica.apply_remote_move(op_active)
        self.replica.apply_remote_move(op_delete)

        active_versions = [v for v in self.replica.tree[1] if v.metadata.get("status") == "active"]
        self.assertEqual(len(active_versions), 1)


if __name__ == "__main__":
    unittest.main()
