import unittest
from unittest.mock import MagicMock, patch

from services import updater


class UpdaterTests(unittest.TestCase):
    @patch.object(updater, "set_last_update_status")
    @patch.object(updater, "start_safe_update")
    @patch.object(updater, "open", create=True)
    @patch.object(updater.os, "makedirs")
    @patch.object(updater, "run_git")
    def test_safe_update_is_started_only_after_fast_forward_check(
        self, run_git, _makedirs, open_mock, start_update, _set_status
    ):
        open_mock.return_value = MagicMock()
        start_update.return_value = MagicMock(returncode=0)
        run_git.side_effect = [
            (0, "", ""),
            (0, "b" * 40, ""),
            (0, "a" * 40, ""),
            (0, "", ""),
        ]
        ok, _ = updater.install_update()
        self.assertTrue(ok)
        start_update.assert_called_once_with("b" * 40)

    @patch.object(updater, "set_last_update_status")
    @patch.object(updater, "start_safe_update")
    @patch.object(updater, "run_git")
    def test_divergent_update_is_rejected(self, run_git, start_update, _set_status):
        run_git.side_effect = [
            (0, "", ""),
            (0, "b" * 40, ""),
            (0, "a" * 40, ""),
            (1, "", "diverged"),
        ]
        ok, message = updater.install_update()
        self.assertFalse(ok)
        self.assertIn("not a safe fast-forward", message)
        start_update.assert_not_called()


if __name__ == "__main__":
    unittest.main()
