from .node import Node

class Tree:
    def __init__(self):
        # We use a dictionary mapping child_id -> Node. 
        # This makes looking up nodes instantaneous.
        self.__nodes = {}

    def __call__(self):
        # The instructions say: "Returns the current state of the tree 
        # according to the set representation described before."
        # Remember, node() calls the __call__ method in node.py which returns (p, m, c)
        return set(self.__nodes.values())

    def __getitem__(self, key):
        # Overrides the [] operator. If the node doesn't exist, it returns None.
        return self.__nodes.get(key, None)

    def move(self, new_node: Node):
        """
        Applies a move operation. Creates the node if it's new, 
        updates the parent if it exists, and ignores cycles.
        """
        curr_parent = new_node.parent
        child_id = new_node.child
        
        # CYCLE DETECTION: Walk up the new parent's ancestry line.
        # If we ever bump into our own child_id, it's a cycle!
        while curr_parent is not None:
            if curr_parent == child_id:
                # Cycle detected! The instructions say "simply ignore such operations"
                return 
            
            # Move one step up the family tree
            if curr_parent in self.__nodes:
                curr_parent = self.__nodes[curr_parent].parent
            else:
                # If the parent isn't in the tree yet, we can't check further up.
                break
        
        # If we survived the cycle check, apply the move!
        # This handles both creating new nodes and overwriting old ones.
        self.__nodes[child_id] = new_node

    def __str__(self):
        # Returns a clean string representation of the tree's current state
        if not self.__nodes:
            return "Empty Tree"
        
        sorted_nodes = sorted([str(node) for node in self.__nodes.values()])
        return "{\n  " + ",\n  ".join(sorted_nodes) + "\n}"