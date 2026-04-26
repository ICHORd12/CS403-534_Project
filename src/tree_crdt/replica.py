import threading
import copy
from .clock import LamportClock
from .tree import Tree, Node
from .payload import MovePayload

class Replica:
    def __init__(self, id: int, host: str, main_base: int, listener_base: int):
        self.__id = id
        self.__clock = LamportClock(id)
        self.__tree = Tree()
        # Log stores: (replica_id, t, old_p, p, m, c)
        self.__op_log = [] 
        self.__zmq_main_addr = f"tcp://{host}:{main_base + id}"
        self.__zmq_listener_addr = f"tcp://{host}:{listener_base + id}"
        
        # RLock prevents deadlock when methods call other methods inside this class
        self.__lock = threading.RLock()

    @property
    def id(self) -> int:
        return self.__id

    @property
    def clock(self) -> LamportClock:
        with self.__lock:
            return copy.deepcopy(self.__clock)

    @property
    def tree(self) -> Tree:
        with self.__lock:
            return copy.deepcopy(self.__tree)

    @property
    def log(self) -> list:
        with self.__lock:
            return copy.deepcopy(self.__op_log)

    @property
    def main_addr(self) -> str:
        return self.__zmq_main_addr

    @property
    def listener_addr(self) -> str:
        return self.__zmq_listener_addr

    def current_timestamp(self) -> int:
        with self.__lock:
            return self.__clock.timestamp

    def tick_clock(self, received: int | None = None) -> int:
        with self.__lock:
            self.__clock.update(received)
            return self.__clock.timestamp

    def __apply_move(self, op: MovePayload):
        """
        The core Undo-Do-Redo logic for CRDTs.
        Ensures all replicas end up with the exact same tree state, 
        even if messages arrive completely out of order.
        """
        with self.__lock:
            op_tuple = (op.timestamp, op.id)
            popped_ops = []

            # 1. UNDO: Pop operations that happened "after" this new one
            while self.__op_log:
                last_op = self.__op_log[-1]
                # last_op is: (replica_id, t, old_p, p, m, c)
                last_op_tuple = (last_op[1], last_op[0]) 

                if last_op_tuple > op_tuple:
                    # The last operation is NOT a predecessor. We must undo it.
                    r_id, r_t, r_old_p, r_p, r_m, r_c = self.__op_log.pop()
                    popped_ops.append(last_op)
                    
                    # Revert the tree move by pointing the child back to old_p
                    undo_node = Node(p=r_old_p, m=r_m, c=r_c)
                    self.__tree.move(undo_node)
                else:
                    # The last operation is a predecessor. Stop undoing.
                    break

            # 2. DO: Apply the new operation
            # Find what the parent was *before* we apply this move, to save in the log
            current_node = self.__tree[op.child]
            old_p = current_node.parent if current_node else None
            
            new_node = Node(p=op.parent, m=op.metadata, c=op.child)
            self.__tree.move(new_node)
            
            # Save to log: (replica_id, t, old_p, p, m, c)
            self.__op_log.append((op.id, op.timestamp, old_p, op.parent, op.metadata, op.child))

            # 3. REDO: Re-apply the popped operations in chronological order
            # popped_ops was built newest-to-oldest, so we reverse it to redo
            for redo_op in reversed(popped_ops):
                r_id, r_t, _, r_p, r_m, r_c = redo_op
                
                # Check what the parent is NOW before re-applying
                curr_node = self.__tree[r_c]
                new_old_p = curr_node.parent if curr_node else None
                
                redo_node = Node(p=r_p, m=r_m, c=r_c)
                self.__tree.move(redo_node)
                
                # Add back to log with the updated old_p
                self.__op_log.append((r_id, r_t, new_old_p, r_p, r_m, r_c))

    def apply_local_move(self, parent: int | None, metadata: dict, child: int) -> MovePayload:
        with self.__lock:
            # 1. Update clock for local action
            self.tick_clock()
            
            # 2. Create the payload
            op = MovePayload(self.id, self.current_timestamp(), parent, metadata, child)
            
            # 3. Apply the move
            self.__apply_move(op)
            
            return op

    def apply_remote_move(self, op: MovePayload):
        with self.__lock:
            # 1. Sync the Lamport clock with the incoming remote timestamp
            self.tick_clock(op.timestamp)
            
            # 2. Apply the move
            self.__apply_move(op)

    def __str__(self) -> str:
        return f"ID: {self.id}, Timestamp: {self.current_timestamp()}"