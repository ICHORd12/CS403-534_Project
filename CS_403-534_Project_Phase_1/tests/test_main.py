import unittest
import uuid
from unittest.mock import MagicMock, patch

import main

# This class is shown for demonstration purposes
# as you are already provided with the helper functions in main.py
class TestMainHelpers(unittest.TestCase):
  def test_parse_hosts_filters_invalid_values(self) -> None:
    hosts = main.parse_hosts("127.0.0.1,invalid,10.0.0.2,256.0.0.1")
    self.assertEqual(hosts, ["127.0.0.1", "10.0.0.2"])


class TestMainProcessOrchestration(unittest.TestCase):
  @patch("main.multiprocessing.Process")
  def test_main_starts_and_joins_all_processes(self, process_cls: MagicMock) -> None:
    first = MagicMock()
    first.is_alive.return_value = False
    process_cls.return_value = first

    hosts = ["127.0.0.1", "127.0.0.2"]
    main.main(
      num_replicas=2,
      tree_config="hierarchical",
      hosts=hosts,
      main_base=5000,
      listener_base=6000,
    )

    self.assertEqual(process_cls.call_count, 1)
    first.start.assert_called_once()
    first.join.assert_called_once_with()

  @patch("main.multiprocessing.Process")
  def test_main_builds_processes_with_expected_targets_and_args(self, process_cls: MagicMock) -> None:
    first = MagicMock()
    process_cls.return_value = first

    hosts = ["127.0.0.1", "127.0.0.2"]
    main.main(
      num_replicas=2,
      tree_config="hierarchical",
      hosts=hosts,
      main_base=5000,
      listener_base=6000,
    )

    self.assertEqual(process_cls.call_count, 1)

    first_call = process_cls.call_args_list[0]
    kwargs = first_call.kwargs
    self.assertIs(kwargs["target"], main.run_replica)
    self.assertEqual(kwargs["name"], "Replica-0")

    args = kwargs["args"]
    self.assertEqual(len(args), 7)
    self.assertIsInstance(args[0], uuid.UUID)
    self.assertEqual(args[1], "hierarchical")
    self.assertEqual(args[2], 0)
    self.assertEqual(args[3], (hosts[0], 5000, 6000))
    self.assertEqual(args[4], 2)
    self.assertEqual(args[5], hosts)
    self.assertIsNone(args[6])

if __name__ == "__main__":
  unittest.main()
