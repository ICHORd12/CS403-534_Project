# CS 403/534 Course Project: Phase 1

The package for the course project of CS 403/534 (Distributed Systems) based on the paper by [Kleppmann et al.](https://doi.org/10.1109/TPDS.2021.3118603) on a Tree CRDT with a Move operation, implemented as a library named ```tree_crdt``` in the directory [src/tree_crdt](src/tree_crdt/), with the corresponding tests in the [tests](tests) directory and a main program in [```main.py```](main.py).

## Package Contents

- **The directory [```src/tree_crdt```](src/tree_crdt/) :** The base directory for the library, ```tree-crdt```, which you are going to implement as part of Phase 1 for the Tree CRDT.

  - **The directory [```clock```](src/tree_crdt/clock/):** The ```clock``` subpackage of the ```tree-crdt``` library.

    - **The file [```clock.py```](src/tree_crdt/clock/clock.py):** The file where you are provided with the ```Clock``` <u>abstract class</u> of the ```clock``` subpackage.

    - **The file [```lamport.py```](src/tree_crdt/clock/lamport.py):** The file where you are going to implement the ```LamportClock``` class for the ```clock``` subpackage.

  - **The directory [```payload```](src/tree_crdt/payload/):** The ```payload``` subpackage of the ```tree-crdt``` library.

    - **The file [```move.py```](src/tree_crdt/payload/move.py):** The file where you are provided with the ```MovePayload``` class of the ```payload``` subpackage.

  - **The directory [```tree```](src/tree_crdt/tree/):** The ```tree``` subpackage of the ```tree-crdt``` library.

    - **The file [```node.py```](src/tree_crdt/tree/node.py):** The file where you are provided with the ```Node``` class of the ```tree``` subpackage.

    - **The file [```tree.py```](src/tree_crdt/tree/tree.py):** The file where you are going to implement the ```Tree``` class for the ```tree``` subpackage.

  - **The file [```replica.py```](src/tree_crdt/replica.py):** The file where you are going to implement the ```Replica``` class for the ```tree-crdt``` library.

- **The file [```main.py```](main.py):** The main program for Phase 1; partially implemented, you are going to complete this program so that you can use the ```tree-crdt``` library you developed and the replicas you created with this library.

- **The directory [```sample_runs```](sample_runs/):** Some example runs of the library with different configurations in order to guide you on what you can expect when you run a correct implementation.

  - The files in this directory have the following naming convention: ```sample<sample-run-id>_replica_<replica-id>.txt```

  - **Note:** The numbers of nodes in the final state of the tree may differ between different executions of the system with the same configuration; **this situation does not imply any issue with your implementations**.

- **The file [```.env.example```](.env.example):** Use this file as the basis for your ```.env``` file to configure the project.

- **The directory [```tests```](tests/) :** The base directory for the tests we provide you with, so that you can check the functional correctness of your implementation. **Please note that you are not allowed to modify any of the contents of this directory.**

  - **The file [```test_main.py```](tests/test_main.py):** The tests for [```main.py```](main.py).

  - **The directory [```tree_crdt```](tests/tree_crdt/):** The tests for the [```tree-crdt```](src/tree_crdt/) library.

    - **The directory [```clock```](tests/tree_crdt/clock/):** The tests for the [```clock```](src/tree_crdt/clock/) subpackage of the ```tree-crdt``` library.

      - **The file [```test_lamport.py```](tests/tree_crdt/clock/test_lamport.py):** The tests for [```lamport.py```](src/tree_crdt/clock/lamport.py).

    - **The directory [```payload```](tests/tree_crdt/payload/):** The tests for the [```payload```](src/tree_crdt/payload/)  subpackage of the ```tree-crdt``` library.

      - **The file [```test_move.py```](tests/tree_crdt/payload/test_move.py):** The tests for [```move.py```](src/tree_crdt/payload/move.py).

    - **The directory [```tree```](tests/tree_crdt/tree/):** The tests for the [```tree```](src/tree_crdt/tree/)  subpackage of the ```tree-crdt``` library.

      - **The file [```test_node.py```](tests/tree_crdt/tree/test_node.py):** The tests for [```node.py```](src/tree_crdt/tree/node.py).

      - **The file [```test_tree.py```](tests/tree_crdt/tree/test_tree.py):** The tests for [```tree.py```](src/tree_crdt/tree/tree.py).
    
    - **The file [```test_replica.py```](tests/tree_crdt/test_replica.py):** The tests for [```replica.py```](src/tree_crdt/replica.py).

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

### How to configure the environment variables before running the project?
Create a ```.env``` file in your root directory in a similar structure to the provided [```.env.example```](.env.example) file, with the following fields set:

- ```HOSTS```: Comma-separated IP addresses for each replica, which are going to be ordered in the range ${0,1,2,...,i}$ if you specified $i$ comma-separated IP addresses.

  - For the replicas you plan to run on your machine locally, assign **127.0.0.1** as the IP address.

  - For the replicas that are going to be run remotely (with respect to your machine), assign the IP address(es) you need.

- ```MAIN_BASE```: The base port number for the MOVE-PUB and ACK-SUB sockets (main thread) of the replicas. (See [```replica.py```](src/tree_crdt/replica.py) and [```main.py```](main.py))

- ```LISTENER_BASE```: The base port number for the MOVE-SUB and ACK-PUB sockets (listener thread) of the replicas. (See [```replica.py```](src/tree_crdt/replica.py) and [```main.py```](main.py))

- ```MAX_TIMESTAMP```: The maximum Lamport timestamp at which a replica will generate a MOVE operation. (See [```main.py```](main.py))
  - If you do not set this field, the replicas will run indefinitely until you shut down the replicas manually.

- ```TREE_CONFIG```: The structure requested for the tree. Should be set to ```hierarchical```, ```wide```, or ```chain```. (See [```main.py```](main.py))
  - ```hierarchical```: Generates a tree with a root node, three children, and their grandchildren as the program runs.

  - ```wide```: Generates a tree such that there is a root node and all the new nodes are generated to be children of the root node.

  - ```chain```: Generates a tree where each new node is the child of the last generated node, creating a chain-like structure.

### How to run the project?

If you did not modify the contents of the project, you can directly run the main program:

```bash
uv run main.py # Runs main.py on the environment's Python interpreter
```

If you had modifications, however, you will first need to reinstall the package:

```bash
uv pip install -e . # Installs (or reinstalls) tree-crdt in development mode
```

- After reinstalling the package, you can run the script ```main.py``` as described above.

- After you complete running ```main.py```, either due to the maximum timestamp or by suspending manually, you are going to see files in the ```runs``` directory with the name format ```<run-id>_replica_<replica-id>.txt```, where ```<run-id>``` is the random UUID generated for your particular run; you can check the final versions of the tree on your replicas from that file.

### How to run the unit tests provided in the project?

You can run the unit tests through the following command:

```bash
uv run python -m unittest discover -s tests -t . -v
```

### What are the required packages for the ```tree-crdt``` library?

- ```pyzmq```: Required for using ZeroMQ sockets in Python.

- ```python-dotenv```: Required for the ability to get the environment variables from the .env files in Python.