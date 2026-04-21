# NOTE: You can add new imports if you need
import json
import multiprocessing
import os
import pprint
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
#  replica_obj, # The Replica object
#  zmq_context, # The ZeroMQ context for the sockets
#  shutdown_event, # The system shutdown event for the replica
#  replica_info, # Replica info: (host, main_base, listener_base)
#  num_replicas, # Number of replicas in the system
#  hosts, # The list of hosts in the system
#  all_replicas_done_event # The event that all replicas have reached the maximum timestamp
# )
# The function should not return any value
# See the PDF for a detailed description of the function

def run_replica( # NOTE: All the parameters are set here; do not modify them
  run_id, # The random UUID for the running session of the system
  tree_config, # Retrieved from .env
  replica_id, # The ID of the replica
  replica_info, # Replica info: (host, main_base, listener_base)
  num_replicas, # Number of replicas in the system
  hosts, # The list of hosts in the system
  max_timestamp, # The specified maximum timestamp
) -> None:
  # TODO: Create the Replica object

  # TODO: Create the ZeroMQ context for the sockets
  # TODO: Create and setup the ZeroMQ socket for publishing to "MOVE" and "DONE"

  # Give the socket time to stabilize before other replicas connect
  time.sleep(1)

  # TODO: Create and setup the ZeroMQ socket for getting subscribed to "ACK"

  # TODO: Create the listener thread with the arguments in the signature, and start it
    # For non-existent parameters, you should create such parameters first as described

  # Wait for all replicas to bind their sockets
  time.sleep(3)

  # A counter you can use for metadata purposes
  counter: int = 0
  
  # The tree configuration and the associated generator are retrieved
  move_generator = get_move_generator(tree_config)

  # Continue until the maximum timestamp is reached (if it is not set, run indefinitely)
  while True:
    # TODO: Generate, apply, and broadcast MOVE operations
      # Generation: parent_id, child_id, tree_type = move_generator(counter)

      # Example metadata structure which you can see in sample_runs
      # (You are free to use any dictionary structure you want):
      # {
      #   "count": counter,
      #   "config": tree_type,
      #   "replica": replica.id
      # }
    
    break

  # TODO: Generate the DONE message

  if num_replicas > 1:
    while True:

      # TODO: Broadcast the DONE message periodically

      # TODO: Poll the socket subscribed to "ACK", and receive the message if exists
      # TODO: You should be keeping track of the 

      # Continue until ACKs are received from all replicas

      break
  
  # TODO: Join the listener thread

  # NOTE: You are not allowed to modify the with block below
  with open(f"runs/{run_id.hex}_replica_{replica.id}.txt", "w") as final_file:
    final_file.write(f"[TREE STATE]\nReplica {replica.id}, tree structure: {tree_config}, maximum timestamp: {max_timestamp}\n")
    final_file.write(pprint.pformat(replica.tree()))

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

  # TODO: Create and start the replica processes
  # NOTE: You should not create replica processes for remote replicas if you use any

  # TODO: Join the replica processes

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