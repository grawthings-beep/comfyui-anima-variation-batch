import json
import unittest
from pathlib import Path


MANIFEST_PATH = (
    Path(__file__).parents[1]
    / "config"
    / "anima-controls.json"
)


class ControlsManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_node_dependencies_are_pinned(self):
        for key in ("anima_lllite_node", "controlnet_aux"):
            dependency = self.manifest[key]
            self.assertRegex(dependency["commit"], r"^[0-9a-f]{40}$")
            self.assertTrue(dependency["repository"].startswith("https://github.com/"))
            self.assertTrue(dependency["path"].startswith("custom_nodes/"))

    def test_artifact_ids_and_paths_are_unique(self):
        entries = (
            self.manifest["lllite_models"]
            + self.manifest["upscale_models"]
            + self.manifest["preprocessor_models"]
        )
        for key in ("id", "path"):
            values = [entry[key] for entry in entries]
            self.assertEqual(len(values), len(set(values)), key)

    def test_lllite_models_install_under_controlnet(self):
        for entry in self.manifest["lllite_models"]:
            self.assertTrue(entry["path"].startswith("models/controlnet/"))
            self.assertTrue(entry["path"].endswith(".safetensors"))

    def test_preprocessors_install_under_controlnet_aux_cache(self):
        prefix = "custom_nodes/comfyui_controlnet_aux/ckpts/"
        for entry in self.manifest["preprocessor_models"]:
            self.assertTrue(entry["path"].startswith(prefix))

    def test_upscaler_installs_under_upscale_models(self):
        self.assertEqual(len(self.manifest["upscale_models"]), 1)
        entry = self.manifest["upscale_models"][0]
        self.assertEqual(entry["repo_id"], "Kim2091/AnimeSharp")
        self.assertEqual(
            entry["path"],
            "models/upscale_models/4x-AnimeSharp.pth",
        )

    def test_all_download_entries_are_complete(self):
        entries = (
            self.manifest["lllite_models"]
            + self.manifest["upscale_models"]
            + self.manifest["preprocessor_models"]
        )
        for entry in entries:
            with self.subTest(entry=entry["id"]):
                self.assertIn("/", entry["repo_id"])
                self.assertTrue(entry["filename"])
                self.assertGreater(entry["min_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
