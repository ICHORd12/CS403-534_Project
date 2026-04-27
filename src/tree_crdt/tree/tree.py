from .node import Node

class Tree:
    def __init__(self):
        # We use a dictionary mapping child_id -> Node. 
        self.__nodes = {}

    def __call__(self):
        return set(self.__nodes.values()) # (p, m, c) tuples are stored in the Node objects.

    def __getitem__(self, key):
        # Overrides the [] operator. If the node doesn't exist, it returns None.
        return self.__nodes.get(key, None)

    def move(self, new_node: Node):
        # Applies a move operation. Creates the node if it's new, 
        # updates the parent if it exists, and ignores cycles.
        
        curr_parent = new_node.parent
        child_id = new_node.child
        
        
        # If we ever bump into our own child_id, it's a cycle
        while curr_parent is not None:
            if curr_parent == child_id:
                # Cycle ignore the move 
                return 
            
            # Move one step up the family tree
            if curr_parent in self.__nodes:
                curr_parent = self.__nodes[curr_parent].parent
            else:
                # If the parent isn't in the tree yet, we can't check further up.
                break
        
        # If no cycle apply the move
        self.__nodes[child_id] = new_node

    def __str__(self):
        # Returns a string representation of the tree's current state
        if not self.__nodes:
            return "Empty Tree"
        
        # Sort the nodes by their string representation for consistent ordering
        sorted_nodes = sorted([str(node) for node in self.__nodes.values()])
        return "{\n  " + ",\n  ".join(sorted_nodes) + "\n}"