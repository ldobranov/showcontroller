import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services import node_mode


class NodeModeTests(unittest.TestCase):
    def test_mode_file_round_trip(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            node_mode, "MODE_FILE", Path(directory, "node_mode.json")
        ):
            node_mode.save_node_mode("video")
            self.assertEqual(node_mode.load_node_mode(), "video")

    @patch.object(node_mode, "save_node_mode")
    @patch.object(node_mode, "start_node_runtime", return_value=(True, ""))
    @patch.object(node_mode, "stop_all_node_runtimes")
    @patch.object(node_mode, "get_node_runtime")
    def test_switch_stops_old_runtime_before_saving_new_mode(
        self, get_runtime, stop_all, start_runtime, save_mode
    ):
        runtime = {"mode": "video", "service": "video.service"}
        get_runtime.return_value = runtime
        self.assertEqual(node_mode.switch_node_mode("video"), (True, ""))
        stop_all.assert_called_once_with(enabled_only=False)
        start_runtime.assert_called_once_with(runtime)
        save_mode.assert_called_once_with("video")

    @patch.object(node_mode, "save_node_mode")
    @patch.object(node_mode, "start_node_runtime", return_value=(False, "failed"))
    @patch.object(node_mode, "stop_all_node_runtimes")
    @patch.object(node_mode, "get_node_runtime", return_value={"mode": "video"})
    def test_failed_start_does_not_save_mode(self, *_mocks):
        ok, error = node_mode.switch_node_mode("video")
        self.assertFalse(ok)
        self.assertEqual(error, "failed")
        node_mode.save_node_mode.assert_not_called()


if __name__ == "__main__":
    unittest.main()
