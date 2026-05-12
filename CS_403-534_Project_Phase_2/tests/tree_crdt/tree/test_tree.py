import unittest
from typing import Any
from tree_crdt.tree import Node, Tree
from tree_crdt.clock import VectorClock


def tier(level: str):
    """Decorator to mark test tier (MVP/Advanced)."""
    def decorator(func):
        func.tier = level
        return func
    return decorator


class TreeTestMixin:
    """Shared helper methods for tree tests."""
    
    tree: Tree

    def _get_versions(self, child_id: int) -> set[Node]:
        """Get all versions (concurrent nodes) for a child ID."""
        return self.tree[child_id]

    def _get_single_node(self, child_id: int) -> Node:
        """Get the single node for a child ID, asserting exactly one version exists."""
        versions = self._get_versions(child_id)
        self.assertEqual(
            len(versions),
            1,
            f"Expected exactly 1 version for child {child_id}, got {len(versions)}",
        )
        return next(iter(versions))

    def assertEqual(self, first: Any, second: Any, msg: str | None = None) -> None:
        """Override assertion (satisfied by unittest.TestCase)."""
        ...

    def _child_ids_from_view(self, view):
        """Extract child IDs from Tree view in sorted order."""
        return [next(iter(bucket)).child if bucket else None for bucket in view]


# ============================================================================
# TIER 1: MVP CORE TESTS
# ============================================================================

class TestTreeCore(unittest.TestCase, TreeTestMixin):
    """
    TIER 1 (MVP): Basic tree operations and state management.
    """
    
    def setUp(self):
        self.tree = Tree()

    # =========== Initialization & Basic Operations ===========
    
    @tier("MVP")
    def test_tree_initialization(self):
        """TIER 1: Empty tree has no nodes."""
        self.assertEqual(self.tree(), [])
        self.assertEqual(self.tree(deleted=True), [])

    @tier("MVP")
    def test_add_single_node_vector(self):
        """TIER 1: Add single node with Vector Clock timestamp."""
        ts = {0: 1, 1: 0}
        result = self.tree.move(0, ts, None, {"id": 1, "status": "active"}, 1)
        self.assertIsNone(result)

        node = self._get_single_node(1)
        self.assertEqual(node.metadata["id"], 1)
        self.assertEqual(node.parent, None)

    @tier("MVP")
    def test_add_multiple_nodes(self):
        """TIER 1: Add multiple nodes in tree hierarchy."""
        self.tree.move(0, {0: 1, 1: 0}, None, {"id": 1, "status": "active"}, 1)
        self.tree.move(0, {0: 2, 1: 0}, 1, {"id": 2, "status": "active"}, 2)
        self.tree.move(0, {0: 3, 1: 0}, 1, {"id": 3, "status": "active"}, 3)

        self.assertEqual(len(self.tree()), 3)

    @tier("MVP")
    def test_move_returns_none(self):
        """TIER 1: Move operation always returns None (async CRDT)."""
        self.assertIsNone(self.tree.move(0, {0: 1, 1: 0}, None, {"status": "active"}, 1))

    # =========== Idempotency ===========
    
    @tier("MVP")
    def test_duplicate_move_is_idempotent(self):
        """TIER 1: Duplicate move with same timestamp is idempotent."""
        ts = {0: 1, 1: 0}
        self.tree.move(0, ts, None, {"x": 1, "status": "active"}, 1)
        self.tree.move(0, ts, None, {"x": 1, "status": "active"}, 1)

        self.assertEqual(len(self._get_versions(1)), 1)

    # =========== Status Handling ===========
    
    @tier("MVP")
    def test_deleted_version_in_deleted_view(self):
        """TIER 1: Deleted nodes appear in deleted view only."""
        self.tree.move(0, {0: 1, 1: 0}, None, {"status": "active"}, 1)
        self.tree.move(0, {0: 2, 1: 0}, None, {"status": "deleted"}, 1)

        active_view = self.tree()
        deleted_view = self.tree(deleted=True)

        self.assertEqual(len(active_view), 1)
        self.assertEqual(len(deleted_view), 1)


# ============================================================================
# TIER 1: CYCLE PREVENTION (MVP)
# ============================================================================

class TestTreeCycleDetection(unittest.TestCase, TreeTestMixin):
    """
    TIER 1 (MVP): Cycle detection and prevention.
    """
    
    def setUp(self):
        self.tree = Tree()

    @tier("MVP")
    def test_self_parent_rejected(self):
        """TIER 1: Node cannot be its own parent."""
        ts = {0: 1, 1: 0}
        self.tree.move(0, ts, 1, {}, 1)
        self.assertEqual(len(self._get_versions(1)), 0)

    @tier("MVP")
    def test_direct_cycle_prevented(self):
        """TIER 1: Direct cycle is prevented (A→B, B→A rejected)."""
        self.tree.move(0, {0: 1, 1: 0}, None, {}, 1)
        self.tree.move(0, {0: 2, 1: 0}, 1, {}, 2)
        self.tree.move(0, {0: 3, 1: 0}, 2, {}, 1)  # would create cycle

        node1 = self._get_single_node(1)
        self.assertIsNone(node1.parent)

    @tier("MVP")
    def test_indirect_cycle_prevented(self):
        """TIER 1: Indirect cycle is prevented (A→B→C→A rejected)."""
        self.tree.move(0, {0: 1, 1: 0}, None, {}, 1)
        self.tree.move(0, {0: 2, 1: 0}, 1, {}, 2)
        self.tree.move(0, {0: 3, 1: 0}, 2, {}, 3)
        self.tree.move(0, {0: 4, 1: 0}, 3, {}, 1)  # cycle attempt

        node1 = self._get_single_node(1)
        self.assertIsNone(node1.parent)

    @tier("MVP")
    def test_deep_cycle_prevention(self):
        """TIER 1: Deep cycles in long chains are prevented."""
        for i in range(1, 6):
            self.tree.move(0, {0: i, 1: 0}, i - 1 if i > 1 else None, {}, i)

        self.tree.move(0, {0: 6, 1: 0}, 5, {}, 1)  # attempt cycle

        node1 = self._get_single_node(1)
        self.assertIsNone(node1.parent)


# ============================================================================
# TIER 1: VECTOR CLOCK SEMANTICS (MVP - Phase 2 core)
# ============================================================================

class TestTreeVectorSemantics(unittest.TestCase, TreeTestMixin):
    """
    TIER 1 (MVP): Vector Clock semantics for Phase 2.
    """
    
    def setUp(self):
        self.tree = Tree()

    def ts(self, a: int, b: int) -> dict[int, int]:
        """Helper: create 2-replica vector timestamp {0: a, 1: b}."""
        return {0: a, 1: b}

    # =========== Causal Ordering ===========
    
    @tier("MVP")
    def test_causal_update_replaces_earlier(self):
        """TIER 1: Later causal timestamp replaces earlier version."""
        self.tree.move(0, self.ts(1, 0), None, {"version": 1, "status": "active"}, 1)
        self.tree.move(0, self.ts(2, 0), None, {"version": 2, "status": "active"}, 1)

        versions = self._get_versions(1)
        self.assertEqual(len(versions), 1)

        node = next(iter(versions))
        self.assertEqual(node.metadata["version"], 2)

    @tier("MVP")
    def test_dominated_timestamp_ignored(self):
        """TIER 1: Earlier dominated timestamp is ignored (causality)."""
        self.tree.move(0, self.ts(2, 0), None, {"version": 2, "status": "active"}, 1)
        self.tree.move(0, self.ts(1, 0), None, {"version": 1, "status": "active"}, 1)

        versions = self._get_versions(1)
        self.assertEqual(len(versions), 1)

        node = next(iter(versions))
        self.assertEqual(node.metadata["version"], 2)

    # =========== Concurrent Updates (Move-Wins) ===========
    
    @tier("MVP")
    def test_concurrent_updates_keep_both_versions(self):
        """TIER 1: Concurrent updates from different replicas keep both versions."""
        self.tree.move(0, self.ts(1, 0), None, {"version": 1, "status": "active"}, 1)
        self.tree.move(1, self.ts(0, 1), None, {"version": 2, "status": "active"}, 1)

        versions = self._get_versions(1)
        self.assertEqual(len(versions), 2)

        values = {node.metadata["version"] for node in versions}
        self.assertEqual(values, {1, 2})

    @tier("MVP")
    def test_concurrent_active_beats_deleted(self):
        """TIER 1: Concurrent active beats concurrent deleted (move-wins)."""
        self.tree.move(0, self.ts(1, 0), None, {"status": "active"}, 1)
        self.tree.move(1, self.ts(0, 1), None, {"status": "deleted"}, 1)

        versions = self._get_versions(1)
        self.assertEqual(len(versions), 1)

        node = next(iter(versions))
        self.assertEqual(node.status, "active")

    @tier("MVP")
    def test_happens_before_removes_old_version(self):
        """TIER 1: Happens-before relationship removes old version."""
        ts1 = {0: 1, 1: 0, 2: 0}
        ts2 = {0: 2, 1: 1, 2: 0}  # ts1 happens-before ts2
        
        self.tree.move(0, ts1, None, {"version": 1}, 1)
        self.tree.move(1, ts2, None, {"version": 2}, 1)
        
        versions = self._get_versions(1)
        self.assertEqual(len(versions), 1)
        
        node = next(iter(versions))
        self.assertEqual(node.metadata["version"], 2)


# ============================================================================
# TIER 1: REPARENTING & VIEW BEHAVIOR (MVP)
# ============================================================================

class TestTreeReparenting(unittest.TestCase, TreeTestMixin):
    """
    TIER 1 (MVP): Valid reparenting and tree view operations.
    """
    
    def setUp(self):
        self.tree = Tree()

    @tier("MVP")
    def test_valid_reparenting(self):
        """TIER 1: Valid reparent: move child to different parent."""
        self.tree.move(0, {0: 1, 1: 0}, None, {}, 1)
        self.tree.move(0, {0: 2, 1: 0}, None, {}, 2)
        self.tree.move(0, {0: 3, 1: 0}, 1, {}, 3)
        self.tree.move(0, {0: 4, 1: 0}, 2, {}, 3)  # reparent 3 to 2

        node3 = self._get_single_node(3)
        self.assertEqual(node3.parent, 2)

    @tier("MVP")
    def test_tree_view_sorted_by_child_id(self):
        """TIER 1: Tree view is sorted by child ID."""
        self.tree.move(0, {0: 1, 1: 0}, None, {"status": "active"}, 3)
        self.tree.move(0, {0: 1, 1: 1}, None, {"status": "active"}, 1)
        self.tree.move(0, {0: 1, 1: 2}, None, {"status": "active"}, 2)

        view = self.tree()
        self.assertEqual(self._child_ids_from_view(view), [1, 2, 3])


# ============================================================================
# TIER 2: ADVANCED TESTS (Vector Clock edge cases & conflict resolution)
# ============================================================================

class TestTreeAdvanced(unittest.TestCase, TreeTestMixin):
    """
    TIER 2 (Advanced): Edge cases and advanced conflict resolution.
    """
    
    def setUp(self):
        self.tree = Tree()

    @tier("Advanced")
    def test_concurrent_versions_multiple_replicas(self):
        """TIER 2: Operations from 3+ replicas create concurrent versions."""
        self.tree.move(0, {0: 1, 1: 0, 2: 0}, None, {"status": "active", "r": 0}, 1)
        self.tree.move(1, {0: 0, 1: 1, 2: 0}, None, {"status": "active", "r": 1}, 1)
        self.tree.move(2, {0: 0, 1: 0, 2: 1}, None, {"status": "active", "r": 2}, 1)
        
        versions = self.tree[1]
        self.assertEqual(len(versions), 3)
        
        replica_ids = {v.replica_id for v in versions}
        self.assertEqual(replica_ids, {0, 1, 2})

    @tier("Advanced")
    def test_causal_chain_convergence(self):
        """TIER 2: Causal chain R0→R1→R2 converges correctly."""
        self.tree.move(0, {0: 1, 1: 0, 2: 0}, None, {"name": "root", "status": "active"}, 1)
        self.tree.move(1, {0: 1, 1: 1, 2: 0}, 1, {"name": "child", "status": "active"}, 2)
        self.tree.move(2, {0: 1, 1: 1, 2: 1}, 2, {"name": "grandchild", "status": "active"}, 3)
        
        self.assertEqual(len(self.tree()), 3)
        
        node2 = next(iter(self.tree[2]))
        node3 = next(iter(self.tree[3]))
        self.assertEqual(node2.parent, 1)
        self.assertEqual(node3.parent, 2)

    @tier("Advanced")
    def test_concurrent_same_child_different_parents(self):
        """TIER 2: Concurrent moves of same child to different parents."""
        ts1 = {0: 1, 1: 0}
        ts2 = {0: 0, 1: 1}
        
        self.tree.move(0, ts1, None, {"status": "active"}, 1)
        self.tree.move(1, ts2, 99, {"status": "active"}, 1)  # move to different parent
        
        versions = self.tree[1]
        self.assertEqual(len(versions), 2)
        
        parents = {v.parent for v in versions}
        self.assertEqual(parents, {None, 99})

    @tier("Advanced")
    def test_vector_clock_timestamp_concurrency_detection(self):
        """TIER 2: VectorClock.timestamp_concurrent detects incomparable timestamps."""
        ts1 = {0: 1, 1: 0, 2: 0}
        ts2 = {0: 0, 1: 1, 2: 0}
        ts3 = {0: 2, 1: 0, 2: 0}
        
        # ts1 and ts2 are concurrent
        self.assertTrue(VectorClock.timestamp_concurrent(ts1, ts2))
        
        # ts1 and ts3 are not concurrent
        self.assertFalse(VectorClock.timestamp_concurrent(ts1, ts3))
        
        # ts2 and ts3 are concurrent
        self.assertTrue(VectorClock.timestamp_concurrent(ts2, ts3))


if __name__ == '__main__':
    unittest.main()
