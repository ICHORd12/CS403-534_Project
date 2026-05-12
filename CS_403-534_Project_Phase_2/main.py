# NOTE: You can add new imports if you need
import json
import multiprocessing
import os
import pprint
import random
import re
import threading
import time
import uuid
import zmq

from dotenv import load_dotenv

from tree_crdt import Replica
from tree_crdt.payload import MovePayload

# -----------------------------------------

# Helper functions:
def validate_ip(ip):
  pattern = r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$'
  return re.match(pattern, ip) is not None

def parse_hosts(host_str):
  return [host for host in host_str.split(",") if validate_ip(host)]

# -----------------------------------------

# Pub-Sub topics:
#   "MOVE"

# -----------------------------------------

# Configuration generators:

def generate_hierarchical_move(counter):
  """Config 1: Hierarchical tree (Root -> Children -> Grandchildren)"""
  if counter == 0:
    parent_id = None
    child_id = 0
    tree_type = "root"
  elif counter <= 3:
    parent_id = 0
    child_id = counter
    tree_type = "child"
  else:
    parent_id = ((counter - 4) % 3) + 1
    child_id = counter + 10
    tree_type = "grandchild"
  
  return parent_id, child_id, tree_type

def generate_wide_tree_move(counter):
  """Config 2: Wide tree with many siblings (one root with many children)"""
  parent_id = None if counter == 0 else 0
  child_id = counter
  tree_type = "root" if counter == 0 else "wide_child"
  
  return parent_id, child_id, tree_type

def generate_deep_chain_move(counter):
  """Config 3: Deep chain - linear parent-child relationships"""
  parent_id = counter - 1 if counter > 0 else None
  child_id = counter
  tree_type = "chain_node"
  
  return parent_id, child_id, tree_type

def generate_random_move_delete(replica, counter):
  """Generates random moves and deletes based on the current tree state"""
  tree = replica.tree
  # Extract current node IDs from the tree via its iterator
  # Filter out the special value -1 if it somehow polluted the keys,
  # and ensure we have unique node IDs.
  current_nodes = [node_id for node_id in tree if node_id >= 0]
  
  # 1. Root creation if no nodes exist or occasionally to add new roots
  # Use replica-specific namespace (replica.id * 1000) for new nodes in Phase 2
  # to avoid collision with Phase 1 static IDs (0-49)
  if not current_nodes or (counter < 2) or (random.random() < 0.1):
    child_id = (replica.id * 1000) + counter + 50
    return None, child_id, "random_root"
  
  # 2. Random Delete (mark as deleted)
  # Roughly 20% chance to delete a node instead of moving
  if random.random() < 0.2:
    child_to_delete = random.choice(current_nodes)
    # Moving to a special parent/status can signify delete if the tree logic supports it,
    # or just use the metadata.
    return None, child_to_delete, "random_delete"
  
  # 3. Random Move
  child_id = random.choice(current_nodes)
  # Try to find a valid parent (any node including None, but avoiding cycles is handled by Tree.move)
  potential_parents = [None] + current_nodes
  parent_id = random.choice(potential_parents)
  
  return parent_id, child_id, "random_move"

def get_move_generator(config_name):
  """Get the appropriate move generator function based on configuration name"""
  generators = {
    "hierarchical": generate_hierarchical_move,
    "wide": generate_wide_tree_move,
    "chain": generate_deep_chain_move
  }
  return generators.get(config_name, generate_hierarchical_move)  # Default to hierarchical

# -----------------------------------------

# TODO: Create the function for the listener thread of the replica here
# Signature:
# (
#  replica_obj,            # The Replica object
#  zmq_context,            # The ZeroMQ context for the sockets
#  shutdown_event,         # The system shutdown event for the replica
#  replica_info,           # Replica info: (host, main_base, listener_base)
#  num_replicas,           # Number of replicas in the system
#  hosts,                  # The list of hosts in the system
#  all_replicas_done_event # The event that all replicas have reached the maximum timestamp
# )
# The function should not return any value.
#
# Behaviour summary (see the Phase 2 PDF for the full description --
# in particular the section "The termination protocol: from PUB-SUB
# to REQ-REP", which explains why DONE/ACK are no longer Pub/Sub
# topics):
#
#   - Sockets owned by this thread:
#       * MOVE-SUB (PUB-SUB), connected to every peer's MOVE-PUB
#         socket; subscribed to the "MOVE" topic.
#       * DONE-REP (REQ-REP), bound to the replica's listener
#         address, used to receive DONE requests from peers and reply
#         with the literal string "ACK".
#
#   - On a "MOVE" message via MOVE-SUB:
#       Extract sender_id, timestamp, parent, metadata, child; record
#       any peer-progress information piggybacked on the message
#       (your design choice -- see PDF Section "Peer-progress
#       mechanism") via replica_obj.record_last_timestamp(...);
#       construct a MovePayload and call
#       replica_obj.apply_remote_move(...).
#
#   - On a DONE request via DONE-REP:
#       Tick the clock with the sender's timestamp, mark the sender
#       as having signalled DONE, send back the literal string "ACK"
#       on the same socket. Set all_replicas_done_event once you have
#       seen DONE from every peer. Use a timeout on recv() so a
#       crashed peer cannot deadlock you.
#
#   - Exit when shutdown_event is set.

def run_replica( # NOTE: All the parameters are set here; do not modify them
  run_id,        # The random UUID for the running session of the system
  tree_config,   # Retrieved from .env
  replica_id,    # The ID of the replica
  replica_info,  # Replica info: (host, main_base, listener_base)
  num_replicas,  # Number of replicas in the system
  hosts,         # The list of hosts in the system
  max_timestamp, # The specified maximum timestamp
) -> None:
  # TODO: Create the Replica object.
  #       Phase 2: pass num_replicas as the last argument so the replica
  #       uses a vector clock.

  # TODO: Create the ZeroMQ context for the sockets.

  # TODO: Create and set up the MOVE-PUB socket (PUB-SUB), bound to the
  #       replica's main address. Used to broadcast MOVE operations.

  # Give the socket time to stabilize before other replicas connect
  time.sleep(1)

  # TODO: Create and set up one DONE-REQ socket (REQ-REP) PER PEER,
  #       each connected to that peer's listener address. Used to
  #       send DONE messages and block on the matching "ACK" reply.
  #       Set a recv() timeout (e.g. 5 seconds) on every DONE-REQ
  #       socket so a crashed peer cannot deadlock you.

  # TODO: Create the listener thread with the arguments in the signature
  #       above, and start it. (For non-existent parameters, you should
  #       create such parameters first as described in the PDF.)

  # Wait for all replicas to bind their sockets
  time.sleep(3)

  # A counter kept for controlling the operation generators
  counter: int = 0

  # The tree configuration and the associated generator are retrieved
  move_generator = get_move_generator(tree_config)

  # Continue until the maximum timestamp is reached (if it is not set, run indefinitely)
  while True:
    # Generate MOVE operations
    # Phase separation (use counter, not logical clock, to avoid distributed barriers):
    current_timestamp: int | dict[int, int] = replica.current_timestamp()
    
    is_at_max = False
    is_phase2 = False
    
    if max_timestamp is not None:
      phase2_limit = 2 * max_timestamp
        
      is_at_max = (counter >= phase2_limit)
      is_phase2 = (counter >= max_timestamp)

    if is_at_max:
      break
    
    # Wait for other replicas to catch up before starting Phase 2
    if is_phase2 and max_timestamp is not None:
      # Check if we have received a timestamp from everyone that is at least at Phase 1 limit.
      # We check the local clock's own component for other replicas as well.
      others_ready = True
      local_vclock = current_timestamp if isinstance(current_timestamp, dict) else None
        
      for other_id in range(num_replicas):
        if other_id == replica.id:
          continue
            
        # Use either the last recorded timestamp from the peer or our own view of their component
        peer_ts_entry = replica.get_peer_timestamp(other_id)
        vclock_entry = local_vclock.get(other_id, 0) if local_vclock else 0
            
        last_val = 0
        if peer_ts_entry is not None:
          last_val = peer_ts_entry if isinstance(peer_ts_entry, int) else peer_ts_entry.get(other_id, 0)
            
        # The peer must have reached max_timestamp in our view (either via direct metadata or vclock)
        if max(last_val, vclock_entry) < max_timestamp:
          others_ready = False
          break
                
      if not others_ready:
        time.sleep(0.5)
        continue

    # Select generator based on phase
    if is_phase2:
      # Phase 2: Random moves and deletes independent of the original configuration
      parent_id, child_id, tree_type = generate_random_move_delete(replica, counter)
    else:
      # Phase 1: Initial tree construction based on the original configuration
      parent_id, child_id, tree_type = move_generator(counter)
    
    # TODO: Apply the move locally and broadcast it
    #
    # Example metadata structure (you are free to use any structure
    # you want, but the "status" key is REQUIRED in Phase 2):
    #   {
    #     "count":   counter,
    #     "config":  tree_type,
    #     "replica": replica.id,
    #     "status":  "active",   # or "deleted"
    #     # Optional: piggyback your most recent timestamp here so
    #     # peers can compute the causal-stability threshold (PDF
    #     # Section "Peer-progress mechanism"). Other mechanisms
    #     # (e.g. a separate periodic broadcast) are also acceptable.
    #   }
    #
    # Broadcast via MOVE-PUB socket:
    #   move_pub_socket.send_json({
    #     "sender_id": replica.id,
    #     "timestamp": move_payload.timestamp,
    #     "parent": move_payload.parent,
    #     "metadata": move_payload.metadata,
    #     "child": move_payload.child,
    #     # Optionally piggyback peer-progress information
    #   })
    #
    # Increment counter for next iteration
    counter += 1

  # TODO: Generate the DONE message (a JSON object containing at
  #       least the sender's id and timestamp).

  if num_replicas > 1:
    # Termination barrier (PDF Section "The termination protocol: from
    # PUB-SUB to REQ-REP"). You need to track:
    #   - received_acks         : peer IDs from which an "ACK" has
    #                             been received
    #   - failed_to_send_acks   : peer IDs whose DONE-REQ recv() timed
    #                             out at least once
    # The exit condition is:
    #   all_replicas_done_event is set
    #   AND  received_acks
    #        ∪ failed_to_send_acks
    #        ∪ {replica_obj.id}
    #        == set(range(num_replicas))
    while True:

      # TODO: For each peer not yet in received_acks, send the DONE
      #       message on the corresponding DONE-REQ socket and try to
      #       recv() the "ACK" reply within the timeout.
      #         - On success: add the peer to received_acks and
      #           remove it from failed_to_send_acks.
      #         - On zmq.Again (timeout): add the peer to
      #           failed_to_send_acks. Note that a REQ socket is
      #           stuck in the "waiting for response" state after a
      #           timeout; you must close and recreate it before the
      #           next attempt, or the next send() will raise.

      # TODO: Check the exit condition above; break out when it is
      #       satisfied.

      break

  # TODO: Join the listener thread.

  # NOTE: You are not allowed to modify the with block below
  with open(f"runs/{run_id.hex}_replica_{replica.id}.txt", "w") as final_file:
    final_file.write(f"[TREE STATE]\nReplica {replica.id}, tree structure: {tree_config}, maximum timestamp: {max_timestamp}\n")
    final_file.write(pprint.pformat(replica.tree(deleted = True)))

# -----------------------------------------
def main( # NOTE: All the parameters are set here; do not modify them
  num_replicas,
  tree_config,
  hosts,
  main_base,
  listener_base,
  max_timestamp = None,
) -> None:
  # A run ID is generated as a random UUID for the current run of the system
  run_id: uuid.UUID = uuid.uuid4()

  # The directory to write final tree state is created beforehand
  os.makedirs("runs", exist_ok = True)

  # TODO: Create and start the replica processes.
  # NOTE: You should not create replica processes for remote replicas if you use any.

  # TODO: Join the replica processes.

# -----------------------------------------

if __name__ == "__main__":
  load_dotenv()

  if os.getenv("HOSTS") is None:
    exit(os.EX_USAGE)

  hosts: list[str] = parse_hosts(str(os.getenv("HOSTS")))
  num_replicas: int = len(hosts)

  try:
    if os.getenv("MAIN_BASE") is None:
      exit(os.EX_USAGE)

    main_base: int = int(str(os.getenv("MAIN_BASE")))
  except ValueError as err:
    print(err)
    exit(os.EX_USAGE)

  try:
    if os.getenv("LISTENER_BASE") is None:
      exit(os.EX_USAGE)

    listener_base: int = int(str(os.getenv("LISTENER_BASE")))
  except ValueError as err:
    print(err)
    exit(os.EX_USAGE)

  try:
    if os.getenv("MAX_TIMESTAMP") is None:
      exit(os.EX_USAGE)

    max_timestamp: int = int(str(os.getenv("MAX_TIMESTAMP")))

    if max_timestamp < 0:
      print("MAX_TIMESTAMP must be a non-negative integer")
      exit(os.EX_USAGE)

  except ValueError as err:
    print(err)
    exit(os.EX_USAGE)

  try:
    if os.getenv("TREE_CONFIG") is None:
      exit(os.EX_USAGE)

    tree_config: str = str(os.getenv("TREE_CONFIG"))

    if (tree_config != "hierarchical") and (tree_config != "wide") and tree_config != "chain":
      print("TREE_CONFIG must be \"hierarchical\", \"wide\", or \"chain\"")
      exit(os.EX_USAGE)

  except ValueError as err:
    print(err)
    exit(os.EX_USAGE)

  main(num_replicas, tree_config, hosts, main_base, listener_base, max_timestamp)
