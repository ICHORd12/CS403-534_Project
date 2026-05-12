# CS 403/534 Project — Phase 2

The repository for the project of CS 403/534 based on the paper by [Kleppmann et al.](https://doi.org/10.1109/TPDS.2021.3118603) on a Tree CRDT, implemented as a library named ```tree_crdt``` in the directory [src/tree_crdt](src/tree_crdt/), with a starter test suite in the [tests](tests/) directory and a main program in [```main.py```](main.py).

This is the **Phase 2** starter package. It assumes you have a working Phase 1 implementation as a starting point: many classes/files (e.g. ```Tree```, ```Replica```, ```main.py```) were complete in Phase 1 and have now been gutted again so that you can extend them.

## What changes in Phase 2?

A short summary; please read [```CS_403-534_Project_Phase_2.pdf```](CS_403-534_Project_Phase_2.pdf) for the full specification.

- **A new operation, ```Delete```.** Alongside ```Move```, you now also support ```Delete```, represented as a ```Move``` whose ```metadata["status"]``` is ```"deleted"``` (acting as a tombstone for the target node).

- **A new clock type, ```VectorClock```.** Replicas can be configured to use a vector clock instead of a Lamport clock by passing ```num_replicas``` to the ```Replica``` constructor; under the partial order of vector clocks, two operations may be **concurrent**.

- **The ```Tree``` is no longer single-value.** Each node identifier $c$ is now associated with a **set of versions** of that node, rather than a single triple. Conceptually the data structure generalises from a tree into a directed acyclic graph (DAG) of versions; the user-facing ``active tree'' is a filtered subgraph. The internal storage you choose (dict-of-sets, list, etc.) is up to you.

- **Move-Wins concurrency semantics.** When a ```Move``` and a ```Delete``` target the same child concurrently, the ```Move``` wins; the ```Delete``` is recorded but not applied.

- **Checkpointing.** You implement log compaction driven by causal stability: peers communicate their progress (mechanism is your design choice), and entries below the resulting threshold are folded into a tree snapshot and dropped from the active log.

- **A new termination protocol.** ```DONE```/```ACK``` move from PUB-SUB to a per-peer Request-Reply (REQ-REP) channel, to avoid a Two-Generals-shaped livelock that exists in the Phase 1 protocol. ```MOVE``` itself remains PUB-SUB.

- **Forward and backward compatibility.** Backward compatibility with Phase 1 is a **report-only** discussion (no implementation required). Forward compatibility toward an unknown Phase 3 is **report + implementation** — you should keep the design extensible for at least two precautions you will defend in your report.

## Package Contents

- **The directory [```src/tree_crdt```](src/tree_crdt/) :** The base directory for the library, ```tree-crdt```, which you are going to extend as part of Phase 2 for the Tree CRDT.

  - **The directory [```clock```](src/tree_crdt/clock/):** The ```clock``` subpackage of the ```tree-crdt``` library.

    - **The file [```clock.py```](src/tree_crdt/clock/clock.py):** The file where you are provided with the ```Clock``` <u>abstract class</u>.

    - **The file [```vector.py```](src/tree_crdt/clock/vector.py):** **(New in Phase 2)** The file where you implement the ```VectorClock``` class. Its constructor takes ```max_id``` (the size of the replica set) as a second argument, and the timestamp is stored as a ```dict[int, int]```. You also need to implement four <u>static</u> comparison helpers (```timestamp_le```, ```timestamp_lt```, ```timestamp_eq```, ```timestamp_concurrent```) on this class.

  - **The directory [```payload```](src/tree_crdt/payload/):** The ```payload``` subpackage.

    - **The file [```move.py```](src/tree_crdt/payload/move.py):** The file where you are provided with the ```MovePayload``` class.

  - **The directory [```tree```](src/tree_crdt/tree/):** The ```tree``` subpackage.

    - **The file [```node.py```](src/tree_crdt/tree/node.py):** The file where you are provided with the ```Node``` class. **Phase 2:** ```Node``` now represents a quintuple ```(i, t, p, m, c)``` rather than the triple ```(p, m, c)``` of Phase 1, where ```i``` is the producing replica id and ```t``` is the producing timestamp.

    - **The file [```tree.py```](src/tree_crdt/tree/tree.py):** The file where you implement the ```Tree``` class. **Phase 2:** ```Tree``` associates each node id with a *set of versions* and supports the new ```get_active(key)``` accessor (which filters out tombstones and orphans). ```move``` now takes ```(i, t, p, m, c)```. The internal storage is your choice.

  - **The file [```replica.py```](src/tree_crdt/replica.py):** The file where you implement the ```Replica``` class. **Phase 2:** the constructor takes a new ```num_replicas``` argument (so that the replica can use a vector clock), and the class gains ```record_last_timestamp``` / ```get_peer_timestamp``` for peer-progress bookkeeping. The internal apply path supports Move-Wins resolution and log compaction.

- **The file [```main.py```](main.py):** The main program for Phase 2; partially implemented, you are going to complete it. Note that the **termination protocol changed from PUB-SUB to REQ-REP** — see the spec PDF for details.

- **The directory [```sample_runs```](sample_runs/):** Some example runs of the library with different configurations in order to guide you on what you can expect when you run a correct implementation. This contains Phase 2 sample outputs (with vector-clock timestamps and tombstoned nodes).

  - The files in this directory have the following naming convention: ```sample<sample-run-id>_replica_<replica-id>.txt```

  - **Note:** The numbers of nodes in the final state of the tree may differ between different executions of the system with the same configuration; **this situation does not imply any issue with your implementations**.

- **The file [```.env.example```](.env.example):** Use this file as the basis for your ```.env``` file to configure the project.

- **The directory [```tests```](tests/):** A small subset of unit tests provided to help you smoke-test the helper classes you must implement. **Please note that you are not allowed to modify any of the contents of this directory.** Coverage in this starter package is intentionally narrow; passing these tests does **not** prove your implementation is correct overall — you are responsible for verifying the broader behaviour (Move-Wins resolution, undo/do/redo, checkpointing, convergence under concurrency, thread safety) yourself, ideally with your own additional tests.

  - **The directory [```tree_crdt```](tests/tree_crdt/):** The tests for the [```tree-crdt```](src/tree_crdt/) library.

    - **The directory [```clock```](tests/tree_crdt/clock/):** The tests for the [```clock```](src/tree_crdt/clock/) subpackage.

      - **The file [```test_vector.py```](tests/tree_crdt/clock/test_vector.py):** Smoke tests for [```vector.py```](src/tree_crdt/clock/vector.py) and the static comparison helpers in that file.

    - **The directory [```payload```](tests/tree_crdt/payload/):** The tests for the [```payload```](src/tree_crdt/payload/) subpackage.

      - **The file [```test_move.py```](tests/tree_crdt/payload/test_move.py):** Smoke tests for [```move.py```](src/tree_crdt/payload/move.py).

    - **The directory [```tree```](tests/tree_crdt/tree/):** The tests for the [```tree```](src/tree_crdt/tree/) subpackage.

      - **The file [```test_node.py```](tests/tree_crdt/tree/test_node.py):** Smoke tests for [```node.py```](src/tree_crdt/tree/node.py).

      - **The file [```test_tree.py```](tests/tree_crdt/tree/test_tree.py):** Smoke tests for [```tree.py```](src/tree_crdt/tree/tree.py).
    
    - **The file [```test_replica.py```](tests/tree_crdt/test_replica.py):** Smoke tests for [```replica.py```](src/tree_crdt/replica.py).
  
  - **The file [```test_main.py```](tests/test_main.py):** Smoke tests for [```main.py```](main.py).

- **The file [```CS_403-534_Project_Phase_2.pdf```](CS_403-534_Project_Phase_2.pdf):** **(New in Phase 2)** The full project specification for Phase 2, written as a delta on top of the Phase 1 PDF. Please read both before starting.

- **The file [```pyproject.toml```](pyproject.toml):** Normally, you should not need to deal with this file; if you think that you ever need to do so, you can reach out the course staff.

- **The files named ```__init__.py```:** You do not need to deal with these files as these are already set for you.

- **The file [```py.typed```](src/tree_crdt/py.typed):** You do not need to deal with this file.

## Setting up the project

### How to set up the project workflow?

- Install ```uv``` on your machine for handling the (isolated) Python environment for the project and managing dependencies: [Installation | uv](https://docs.astral.sh/uv/getting-started/installation)

- Run the following command to create the Python environment for the project:
  ```bash
  uv venv
  ```

- After creating the environment, activate it on your terminal:
  ```bash
  source .venv/bin/activate
  ```

- Once you activated the environment, install the dependencies:
  ```bash
  uv sync
  ```

  - ```uv``` will retrieve the dependencies from ```pyproject.toml``` and install on the virtual environment.

- You can check the installed packages using the following command:
  ```bash
  uv pip list
  ```

  - **Note:** You are going to see that the library for the project, ```tree-crdt```, is also among the installed packages; it is utilized as if it is an ordinary package in ```main.py```.

## How to configure the environment variables before running the project?

Create a ```.env``` file in your root directory in a similar structure to the provided [```.env.example```](.env.example) file, with the following fields set:

- ```HOSTS```: Comma-separated IP addresses for each replica, which are going to be ordered in the range ${0,1,2,...,i}$ if you specified $i$ comma-separated IP addresses.

  - For the replicas you plan to run on your machine locally, assign **127.0.0.1** as the IP address.

  - For the replicas that are going to be run remotely (with respect to your machine), assign the IP address(es) you need.

- ```MAIN_BASE```: The base port number for the **MOVE-PUB** sockets (and the per-peer **DONE-REQ** sockets used by the new REQ-REP termination protocol) on the main thread of the replicas. (See [```replica.py```](src/tree_crdt/replica.py) and [```main.py```](main.py).)

- ```LISTENER_BASE```: The base port number for the **MOVE-SUB** sockets and the **DONE-REP** socket of the listener thread of the replicas. (See [```replica.py```](src/tree_crdt/replica.py) and [```main.py```](main.py).)

- ```MAX_TIMESTAMP```: The maximum logical-clock timestamp at which a replica will stop generating ```MOVE``` operations. Under a vector clock you should compare the local component of the vector against this value. (See [```main.py```](main.py).)
  - If you do not set this field, the replicas will run indefinitely until you shut down the replicas manually.

- ```TREE_CONFIG```: The structure requested for the tree. Should be set to ```hierarchical```, ```wide```, or ```chain```. (See [```main.py```](main.py).)
  - ```hierarchical```: Generates a tree with a root node, three children, and their grandchildren as the program runs.
  - ```wide```: Generates a tree such that there is a root node and all the new nodes are generated to be children of the root node.
  - ```chain```: Generates a tree where each new node is the child of the last generated node, creating a chain-like structure.

## How to run the project?

If you did not modify the contents of the project, you can directly run the main program:

```bash
uv run main.py # Runs main.py on the environment's Python interpreter
```

If you had modifications, however, you will first need to reinstall the package:

```bash
uv pip install -e . # Installs (or reinstalls) tree-crdt in development mode
```

- After reinstalling the package, you can run the script ```main.py``` as described above.

- After you complete running ```main.py```, either due to the maximum timestamp or by suspending manually, you are going to see files in the ```runs``` directory with the following name format: ```<run-id>_replica_<replica-id>.txt```; you can check the final versions of the tree on your replicas from that file.

## How to run the unit tests provided in the project?

You can run the unit tests, which reside in the directory ```tests/```, through the following command:

```bash
uv run python -m unittest discover -s tests -t . -v
```

## What are the required packages for the ```tree-crdt``` library?

- ```pyzmq```: Required for using ZeroMQ sockets in Python.

- ```python-dotenv```: Required for the ability to get the environment variables from the .env files in Python.