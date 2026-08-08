import json
import unittest
from pathlib import Path

from services import modules


ROOT = Path(__file__).resolve().parents[1]


class ProjectSmokeTests(unittest.TestCase):
    def test_default_config_is_valid_object(self):
        data = json.loads((ROOT / "config.default.json").read_text(encoding="utf-8"))
        self.assertIsInstance(data, dict)
        self.assertIn("web", data)

    def test_version_matches_default_config(self):
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        config = json.loads((ROOT / "config.default.json").read_text(encoding="utf-8"))
        self.assertEqual(config.get("version"), version)

    def test_module_manifests_load_with_unique_keys(self):
        available = modules.get_available_modules()
        keys = [item["key"] for item in available]
        self.assertGreater(len(keys), 0)
        self.assertEqual(len(keys), len(set(keys)))
        for item in available:
            self.assertTrue(callable(item["register"]))

    def test_manifest_menu_templates_exist(self):
        for item in modules.get_available_modules():
            for menu in item.get("menu", []):
                template = menu.get("template")
                if template:
                    self.assertTrue(
                        (ROOT / "templates" / template).is_file(),
                        f"Missing template: {template}",
                    )

    def test_required_systemd_units_exist(self):
        for name in (
            "showcontroller-web.service",
            "showcontroller-gpio.service",
            "showcontroller-video-node.service",
        ):
            self.assertTrue((ROOT / "systemd" / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
