from .node import Node

class Tree:
  # TODO: Implement this class
  def __init__(self):
    # child_id -> Node. Empty container at construction time
    self.__nodes: dict = {}
 
  def __call__(self):
    # Snapshot the current tree state as a set of Node objects: T = { (p, m, c), (p', m', c'), ... }
    return set(self.__nodes.values())
 
  def __getitem__(self, key):
    # Look up a node by its child ID. Returns None if the node is absent
    return self.__nodes.get(key)
 
  def move(self, new_node):
    """
    Three outcomes:
    1. Exact duplicate edge already in the tree -> ignore
    2. Applying this move would create a cycle -> ignore
    3. Otherwise -> overwrite the entry for this child ID with the new node
    """
    c = new_node.child
    existing = self.__nodes.get(c)
 
    # Case 1: the tree already contains exactly this edge (p, m, c)
    if existing is not None and existing == new_node:
      return None
 
    # Case 2: would this move create a cycle?
    if self.__would_create_cycle(new_node):
      return None
 
    # Case 3: apply (create, reparent, and metadata update)
    self.__nodes[c] = new_node
    return None
 
  def __would_create_cycle(self, new_node) -> bool:
    # A move (p, m, c) creates a cycle iff, in the current tree, c is an ancestor of p (or p == c, the self-loop case)
    p = new_node.parent
    c = new_node.child
 
    # Attaching to None means becoming a root -- never a cycle
    if p is None:
      return False
 
    # A node cannot be its own parent
    if p == c:
      return True
 
    # Walk up from p via existing parent pointers
    current = p
    while current is not None:
      if current == c:
        return True
      parent_node = self.__nodes.get(current)
      # If the parent chain points to an ID we don't know about yet, there can't be a cycle involving c from this path
      if parent_node is None:
        return False
      current = parent_node.parent
 
    return False
 
  def __str__(self):
    # String representation: {(None, m_0, 0), (0, m_1, 1), (0, m_2, 2)}
    # The empty tree is rendered as '{}'
    if not self.__nodes:
      return "{}"
    
    # Sort by child ID for readable representation
    parts = []
    for c in sorted(self.__nodes.keys()):
      node = self.__nodes[c]
      parts.append(f"({node.parent}, {node.metadata}, {node.child})")
    return "{" + ", ".join(parts) + "}"