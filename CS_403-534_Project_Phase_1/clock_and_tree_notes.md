# Notes — Clock + Tree

`LamportClock` and `Tree` are done and tested. Files added to the repo:

- `src/tree_crdt/clock/lamport.py`
- `src/tree_crdt/tree/tree.py`

Nothing else was changed. 6/6 staff tests pass (`test_lamport.py`, `test_tree.py`).

---

## API contract

### `LamportClock`

```python
from tree_crdt.clock.lamport import LamportClock

clock = LamportClock(id=0)   # timestamp starts at 0

clock.id                     # int, read-only
clock.timestamp              # int, read-only
str(clock)                   # str of current timestamp

clock.update(None)           # local tick:  timestamp += 1
clock.update(r)              # merge rule:  timestamp = max(timestamp, r) + 1
```

Use `update(None)` for locally generated events. Use `update(r)` for any event
triggered by something received from another replica (remote MOVE, DONE).
Note: `update(0)` uses the merge rule, only literal `None` is a local tick.

### `Tree`

```python
from tree_crdt.tree import Tree, Node

tree = Tree()

tree[c]          # -> Node or None (never raises KeyError)
tree()           # -> set[Node], a snapshot
tree.move(node)  # -> None; silently ignores dupes and cycles, overwrites otherwise
str(tree)        # -> "{}" or "{(p, m, c), ...}"
```

`tree.move()` handles create, reparent, and metadata update in one call. It
returns `None` in all cases — it does **not** tell you whether the move was
applied or ignored.

---

## Two things to watch out for

1. **Reading the old parent.** `move()` doesn't return the old parent. If you
   need it for the op log, read it before calling `move()`:

   ```python
   existing = tree[op.child]
   old_p = existing.parent if existing is not None else None
   tree.move(Node(op.parent, op.metadata, op.child))
   ```

2. **`Node` has no `__repr__`.** `main.py` uses `pprint.pformat(replica.tree())`,
   which will render nodes as `<Node object at 0x...>`. We should agree on a
   fix when it comes up — easiest is adding `__repr__ = __str__` to `Node`.

---

## Other notes

- Tree is **not** thread-safe. Locking lives in `Replica`.
- `tree()` returns a snapshot set, but the Nodes inside are the real objects,
  not copies. Nodes are effectively immutable (private fields, no setters), so
  this is safe. If you need a full deep copy for a `Replica.tree` property,
  `copy.deepcopy(self._tree)` in the property is fine.
- Forward references (moving a node under a parent that doesn't exist yet) are
  allowed — cycle detection handles that case without issue.

---

## To verify locally

```bash
uv run python -m unittest tests.tree_crdt.clock.test_lamport tests.tree_crdt.tree.test_tree -v
```

Should show 6 OKs.