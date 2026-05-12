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
  current_nodes = [node_id for node_id in tree if node_id >= 0]
  
  current_nodes.sort()
  
  if not current_nodes or (counter < 2) or (random.random() < 0.1):
    child_id = (replica.id * 1000) + counter + 50
    return None, child_id, "random_root"
  
  if random.random() < 0.2:
    child_to_delete = random.choice(current_nodes)
    return None, child_to_delete, "random_delete"
  
  child_id = random.choice(current_nodes)
  potential_parents = [None] + current_nodes
  potential_parents.sort(key=lambda x: -1 if x is None else x)
  parent_id = random.choice(potential_parents)
  
  return parent_id, child_id, "random_move"

def get_move_generator(config_name):
  """Get the appropriate move generator function based on configuration name"""
  generators = {
    "hierarchical": generate_hierarchical_move,
    "wide": generate_wide_tree_move,
    "chain": generate_deep_chain_move
  }
  return generators.get(config_name, generate_hierarchical_move)

# -----------------------------------------

def listener_thread_func(replica_obj, zmq_context, shutdown_event, replica_info, num_replicas, hosts, all_replicas_done_event):
  host, main_base, listener_base = replica_info
  
  sub_socket = zmq_context.socket(zmq.SUB)
  sub_socket.setsockopt(zmq.LINGER, 0) 
  for i, h in enumerate(hosts):
    if i != replica_obj.id:
      sub_socket.connect(f"tcp://{h}:{main_base + i}")
  sub_socket.setsockopt_string(zmq.SUBSCRIBE, "MOVE")
  
  rep_socket = zmq_context.socket(zmq.REP)
  rep_socket.setsockopt(zmq.LINGER, 0)
  rep_socket.bind(replica_obj.listener_addr)
  
  poller = zmq.Poller()
  poller.register(sub_socket, zmq.POLLIN)
  poller.register(rep_socket, zmq.POLLIN)
  
  dones_received = set()
  
  if num_replicas <= 1:
      all_replicas_done_event.set()

  while not shutdown_event.is_set():
    socks = dict(poller.poll(timeout=100)) 
      
    if sub_socket in socks:
      topic, msg_bytes = sub_socket.recv_multipart()
      msg = json.loads(msg_bytes.decode('utf-8'))
          
      vector_timestamp = {int(k): v for k, v in msg['timestamp'].items()}
          
      op = MovePayload(
        msg['sender_id'],
        vector_timestamp,
        msg['parent'],
        msg['metadata'],
        msg['child']
      )
      
      if "last_ts" in op.metadata:
        peer_ts = {int(k): v for k, v in op.metadata["last_ts"].items()}
        replica_obj.record_last_timestamp(op.id, peer_ts)
        
      replica_obj.apply_remote_move(op)
          
    if rep_socket in socks:
      msg_bytes = rep_socket.recv()
      msg = json.loads(msg_bytes.decode('utf-8'))
          
      if msg.get("type") == "DONE":
        sender_id = msg["sender_id"]
        if "timestamp" in msg:
            ts = {int(k): v for k, v in msg["timestamp"].items()}
            replica_obj.tick_clock(ts)
            
        dones_received.add(sender_id)
        
        if len(dones_received) >= num_replicas - 1:
            all_replicas_done_event.set()
            
        rep_socket.send(json.dumps({"type": "ACK", "sender_id": replica_obj.id}).encode('utf-8'))
                  
  sub_socket.close()
  rep_socket.close()

def run_replica(run_id, tree_config, replica_id, replica_info, num_replicas, hosts, max_timestamp):
  host, main_base, listener_base = replica_info
  replica = Replica(replica_id, host, main_base, listener_base, num_replicas)

  zmq_context = zmq.Context()

  pub_socket = zmq_context.socket(zmq.PUB)
  pub_socket.setsockopt(zmq.LINGER, 0) 
  pub_socket.bind(replica.main_addr)

  time.sleep(1)

  shutdown_event = threading.Event()
  all_replicas_done_event = threading.Event()
  
  listener = threading.Thread(target=listener_thread_func, args=(
    replica, zmq_context, shutdown_event, replica_info, num_replicas, hosts, all_replicas_done_event
  ))
  listener.start()

  time.sleep(3)

  counter: int = 0
  move_generator = get_move_generator(tree_config)

  while True:
    current_timestamp = replica.current_timestamp()
    
    is_at_max = False
    is_phase2 = False
    
    if max_timestamp is not None:
      phase2_limit = 2 * max_timestamp
      is_at_max = (counter >= phase2_limit)
      is_phase2 = (counter >= max_timestamp)

    if is_at_max:
      break
    
    if is_phase2 and max_timestamp is not None:
      others_ready = True
      local_vclock = current_timestamp if isinstance(current_timestamp, dict) else None
        
      for other_id in range(num_replicas):
        if other_id == replica.id:
          continue
            
        peer_ts_entry = replica.get_peer_timestamp(other_id)
        vclock_entry = local_vclock.get(other_id, 0) if local_vclock else 0
            
        last_val = 0
        if peer_ts_entry is not None:
          last_val = peer_ts_entry if isinstance(peer_ts_entry, int) else peer_ts_entry.get(other_id, 0)
            
        if max(last_val, vclock_entry) < max_timestamp:
          others_ready = False
          break
                
      if not others_ready:
        time.sleep(0.5)
        continue

    if is_phase2:
      parent_id, child_id, tree_type = generate_random_move_delete(replica, counter)
    else:
      parent_id, child_id, tree_type = move_generator(counter)
    
    m = {
        "status": "deleted" if tree_type == "random_delete" else "active",
        "last_ts": replica.current_timestamp()
    }
      
    op = replica.apply_local_move(parent_id, m, child_id)
      
    msg = {
        "sender_id": op.id,
        "timestamp": op.timestamp,
        "parent": op.parent,
        "metadata": op.metadata,
        "child": op.child
    }
    pub_socket.send_multipart([b"MOVE", json.dumps(msg).encode('utf-8')])
    
    counter += 1
    time.sleep(random.uniform(0.01, 0.05))

  if num_replicas > 1:
    received_acks = set()
    failed_to_send_acks = set()
    req_sockets_info = [(i, h) for i, h in enumerate(hosts) if i != replica_id]
            
    while True:
      for i, h in req_sockets_info:
        if i in received_acks:
            continue
            
        req = zmq_context.socket(zmq.REQ)
        req.setsockopt(zmq.LINGER, 0) 
        req.setsockopt(zmq.RCVTIMEO, 1000) 
        req.connect(f"tcp://{h}:{listener_base + i}")
        try:
          done_msg = {
              "type": "DONE", 
              "sender_id": replica_id, 
              "timestamp": replica.current_timestamp()
          }
          req.send(json.dumps(done_msg).encode('utf-8'))
          ack_bytes = req.recv()
          ack = json.loads(ack_bytes.decode('utf-8'))
          if ack.get("type") == "ACK":
            received_acks.add(i)
            if i in failed_to_send_acks:
                failed_to_send_acks.remove(i)
        except zmq.error.Again:
          failed_to_send_acks.add(i)
        finally:
          req.close()
          
   
      all_acked = (received_acks | failed_to_send_acks | {replica_id}) == set(range(num_replicas))
      if all_replicas_done_event.is_set() and all_acked:
          break
      time.sleep(0.1) 

  shutdown_event.set()
  listener.join()
  pub_socket.close()
  zmq_context.term()

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
  run_id = uuid.uuid4()
  
  if not os.path.exists("runs"):
    os.makedirs("runs")
    
  processes = []
  
  for i in range(num_replicas):
    if hosts[i] in ["127.0.0.1", "localhost"]:
      replica_info = (hosts[i], main_base, listener_base)
      p = multiprocessing.Process(target=run_replica, args=(
        run_id, tree_config, i, replica_info, num_replicas, hosts, max_timestamp
      ))
      processes.append(p)
      p.start()
      
  for p in processes:
    p.join()

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