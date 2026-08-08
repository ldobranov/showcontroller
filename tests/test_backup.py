import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from services import backup


class Upload:
    def __init__(self, content, filename="backup.zip"):
        self.content = content
        self.filename = filename

    def save(self, path):
        Path(path).write_bytes(self.content)


def make_zip(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, value in files.items():
            archive.writestr(name, value)
    return output.getvalue()


class BackupTests(unittest.TestCase):
    def test_restore_accepts_known_json_files(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            backup, "BASE_DIR", Path(directory)
        ):
            content = make_zip({
                str(backup.BACKUP_FILES[0]): json.dumps({"name": "test"}),
                str(backup.BACKUP_FILES[3]): json.dumps({"mode": "video"}),
            })
            backup.restore_config_file(Upload(content))
            restored = json.loads(Path(directory, "config.json").read_text())
            self.assertEqual(restored["name"], "test")

    def test_restore_rejects_unknown_archive_members(self):
        content = make_zip({"../../etc/passwd": "not allowed"})
        with self.assertRaisesRegex(ValueError, "Unexpected file"):
            backup.restore_config_file(Upload(content))

    def test_restore_rejects_invalid_json_before_writing(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            backup, "BASE_DIR", Path(directory)
        ):
            content = make_zip({"config.json": "[1, 2, 3]"})
            with self.assertRaisesRegex(ValueError, "JSON object"):
                backup.restore_config_file(Upload(content))
            self.assertFalse(Path(directory, "config.json").exists())


if __name__ == "__main__":
    unittest.main()
