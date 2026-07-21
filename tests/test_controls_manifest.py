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

    def test_core_and_preprocessor_dependencies_are_pinned(self):
        core = self.manifest["core"]
        self.assertEqual(
            core["required_nodes"],
            ["ModelPatchLoader", "AnimaLLLiteApply"],
        )
        self.assertRegex(core["feature_commit"], r"^[0-9a-f]{40}$")
        self.assertRegex(
            self.manifest["controlnet_aux"]["commit"],
            r"^[0-9a-f]{40}$",
        )

    def test_artifact_ids_and_paths_are_unique(self):
        entries = (
            self.manifest["model_patches"]
            + self.manifest["preprocessor_models"]
        )
        for key in ("id", "path"):
            values = [entry[key] for entry in entries]
            self.assertEqual(len(values), len(set(values)), key)

    def test_model_patches_install_under_model_patches(self):
        for entry in self.manifest["model_patches"]:
            self.assertTrue(entry["path"].startswith("models/model_patches/"))
            self.assertTrue(entry["path"].endswith(".safetensors"))

    def test_preprocessors_install_under_controlnet_aux_cache(self):
        prefix = "custom_nodes/comfyui_controlnet_aux/ckpts/"
        for entry in self.manifest["preprocessor_models"]:
            self.assertTrue(entry["path"].startswith(prefix))

    def test_all_download_entries_are_complete(self):
        entries = (
            self.manifest["model_patches"]
            + self.manifest["preprocessor_models"]
        )
        for entry in entries:
            with self.subTest(entry=entry["id"]):
                self.assertIn("/", entry["repo_id"])
                self.assertTrue(entry["filename"])
                self.assertGreater(entry["min_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
