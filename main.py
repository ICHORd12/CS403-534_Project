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

def listener_thread_func(
    replica_obj, 
    zmq_context, 
    shutdown_event, 
    replica_info, 
    num_replicas, 
    hosts, 
    all_replicas_done_event
):
    host, main_base, listener_base = replica_info
    my_id = replica_obj.id

    # 1. Setup SUB socket to listen to MOVE and DONE from all other replicas' main threads
    sub_socket = zmq_context.socket(zmq.SUB)
    for i in range(num_replicas):
        if i != my_id:
            sub_socket.connect(f"tcp://{hosts[i]}:{main_base + i}")
            
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, "MOVE")
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, "DONE")

    # 2. Setup PUB socket to send ACK back when a DONE is received
    pub_socket = zmq_context.socket(zmq.PUB)
    pub_socket.bind(replica_obj.listener_addr)

    poller = zmq.Poller()
    poller.register(sub_socket, zmq.POLLIN)

    done_replicas = set()

    while not shutdown_event.is_set():
        # Poll with timeout to periodically check the shutdown_event
        socks = dict(poller.poll(timeout=100))
        if sub_socket in socks:
            message = sub_socket.recv_string()
            topic, data_str = message.split(" ", 1)
            data = json.loads(data_str)

            if topic == "MOVE":
                op = MovePayload(data['i'], data['t'], data['p'], data['m'], data['c'])
                replica_obj.apply_remote_move(op)
                
            elif topic == "DONE":
                sender_id = data['i']
                sender_ts = data['t']
                
                # Update clock based on the DONE message's timestamp
                replica_obj.tick_clock(sender_ts)
                done_replicas.add(sender_id)

                # Broadcast ACK acknowledging we saw their DONE message
                ack_payload = {'i': my_id, 'ack_to': sender_id}
                pub_socket.send_string(f"ACK {json.dumps(ack_payload)}")

                # Check if we have received DONE from all OTHER replicas
                if len(done_replicas) == num_replicas - 1:
                    all_replicas_done_event.set()

def run_replica(
    run_id, 
    tree_config, 
    replica_id, 
    replica_info, 
    num_replicas, 
    hosts, 
    max_timestamp
) -> None:
    host, main_base, listener_base = replica_info

    # 1. Create the Replica object
    replica = Replica(replica_id, host, main_base, listener_base)

    # 2. Create the ZeroMQ context
    zmq_context = zmq.Context()

    # 3. Create and setup the ZeroMQ socket for publishing "MOVE" and "DONE"
    main_pub_socket = zmq_context.socket(zmq.PUB)
    main_pub_socket.bind(replica.main_addr)

    time.sleep(1) # Give the socket time to stabilize

    # 4. Create and setup the ZeroMQ socket for getting subscribed to "ACK"
    main_sub_socket = zmq_context.socket(zmq.SUB)
    for i in range(num_replicas):
        if i != replica_id:
            # Connect to other replicas' listener threads to receive their ACKs
            main_sub_socket.connect(f"tcp://{hosts[i]}:{listener_base + i}")
    main_sub_socket.setsockopt_string(zmq.SUBSCRIBE, "ACK")

    # 5. Create threading events
    shutdown_event = threading.Event()
    all_replicas_done_event = threading.Event()

    # 6. Create and start the listener thread
    listener_thread = threading.Thread(
        target=listener_thread_func,
        args=(replica, zmq_context, shutdown_event, replica_info, num_replicas, hosts, all_replicas_done_event)
    )
    listener_thread.start()

    time.sleep(3) # Wait for all replicas to bind their sockets

    counter = 0
    move_generator = get_move_generator(tree_config)

    if replica.id == 2:
        time.sleep(10)

    # 7. Main operational loop
    while True:
        # Check if we have reached the max timestamp
        if max_timestamp is not None and replica.current_timestamp() >= max_timestamp:
            break


        parent_id, child_id, tree_type = move_generator(counter)
        metadata = {
            "count": counter,
            "timestamp": 0,
            "config": tree_type,
            "replica": replica.id
        }

        # Apply locally and get the packaged payload
        op = replica.apply_local_move(parent_id, metadata, child_id)
        metadata["timestamp"] = op.timestamp
        # Broadcast the MOVE payload
        move_data = {
            'i': op.id, 't': op.timestamp, 'p': op.parent,
            'm': op.metadata, 'c': op.child
        }
        main_pub_socket.send_string(f"MOVE {json.dumps(move_data)}")

        counter += 1
        time.sleep(0.05) # Prevent overloading the network instantly

    # 8. Generate and broadcast the DONE message
    done_data = {'i': replica.id, 't': replica.current_timestamp()}
    done_msg = f"DONE {json.dumps(done_data)}"

    if num_replicas > 1:
        acked_replicas = set()
        poller = zmq.Poller()
        poller.register(main_sub_socket, zmq.POLLIN)

        while len(acked_replicas) < num_replicas - 1:
            # Periodically broadcast the DONE message
            main_pub_socket.send_string(done_msg)

            # Poll for ACKs (timeout allows us to loop and re-broadcast DONE if needed)
            socks = dict(poller.poll(timeout=500))
            if main_sub_socket in socks:
                # Read all available messages in the queue
                while True:
                    try:
                        msg = main_sub_socket.recv_string(flags=zmq.NOBLOCK)
                        topic, data_str = msg.split(" ", 1)
                        data = json.loads(data_str)
                        
                        # Only count the ACK if it is specifically addressed to us
                        if data['ack_to'] == replica.id:
                            acked_replicas.add(data['i'])
                    except zmq.Again:
                        break # No more messages in the queue

    # 9. Wait for the listener thread to catch up, then shut down
    all_replicas_done_event.wait(timeout=5.0) 
    shutdown_event.set()
    listener_thread.join()

    # NOTE: You are not allowed to modify the with block below
    with open(f"runs/{run_id.hex}_replica_{replica.id}.txt", "w") as final_file:
        final_file.write(f"[TREE STATE]\nReplica {replica.id}, tree structure: {tree_config}, maximum timestamp: {max_timestamp}\n")
        final_file.write(pprint.pformat(replica.tree()))

# -----------------------------------------
def main(
    num_replicas,
    tree_config,
    hosts,
    main_base,
    listener_base,
    max_timestamp = None,
) -> None:
    run_id: uuid.UUID = uuid.uuid4()
    os.makedirs("runs", exist_ok = True)

    processes = []
    
    # Create and start the replica processes locally
    for i in range(num_replicas):
        # NOTE: You should not create replica processes for remote replicas
        # We only start a local process if the host is localhost / 127.0.0.1
        if hosts[i] not in ["127.0.0.1", "localhost"]:
            continue

        replica_info = (hosts[i], main_base, listener_base)
        
        p = multiprocessing.Process(
            target=run_replica,
            name=f"Replica-{i}", # The test explicitly requires this name format!
            args=(run_id, tree_config, i, replica_info, num_replicas, hosts, max_timestamp)
        )
        processes.append(p)
        p.start()

    # Join the replica processes back to the main thread
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