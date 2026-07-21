import tempfile
import unittest
from pathlib import Path
from unittest import mock

from install import MANAGER_INSTALL_ARGUMENTS
from scripts.install_anima_controls import (
    InstallError,
    discover_comfyui_root,
    download_artifact,
    find_hf_command,
    install_workflow,
    is_comfyui_root,
    verify_core_support,
)


class InstallAnimaControlsTests(unittest.TestCase):
    def make_root(self, directory):
        root = Path(directory) / "ComfyUI"
        (root / "models").mkdir(parents=True)
        (root / "custom_nodes").mkdir()
        return root

    def test_explicit_comfyui_root_is_discovered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_root(directory)
            self.assertTrue(is_comfyui_root(root))
            self.assertEqual(discover_comfyui_root(str(root)), root.resolve())

    def test_manager_hook_installs_required_patches_but_defers_preprocessors(self):
        self.assertIn("--skip-preprocessor-models", MANAGER_INSTALL_ARGUMENTS)
        self.assertNotIn("--skip-workflow", MANAGER_INSTALL_ARGUMENTS)

    def test_core_support_check_reports_missing_native_nodes(self):
        manifest = {
            "core": {
                "feature_commit": "a" * 40,
                "required_nodes": ["ModelPatchLoader", "AnimaLLLiteApply"],
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_root(directory)
            module = root / "comfy_extras" / "nodes_model_patch.py"
            module.parent.mkdir()
            module.write_text("class ModelPatchLoader:\n    pass\n", encoding="utf-8")
            with self.assertRaisesRegex(InstallError, "AnimaLLLiteApply"):
                verify_core_support(root, manifest)

            module.write_text(
                "class ModelPatchLoader:\n    pass\n"
                "class AnimaLLLiteApply:\n    pass\n",
                encoding="utf-8",
            )
            verify_core_support(root, manifest)

    def test_existing_download_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_root(directory)
            output = root / "models" / "model_patches" / "test.safetensors"
            output.parent.mkdir()
            output.write_bytes(b"valid")
            entry = {
                "id": "test",
                "repo_id": "owner/repo",
                "filename": "test.safetensors",
                "path": "models/model_patches/test.safetensors",
                "min_bytes": 5,
            }
            download_artifact(
                root,
                entry,
                "definitely-not-a-command",
                force=False,
                dry_run=False,
            )
            self.assertEqual(output.read_bytes(), b"valid")

    def test_hf_command_is_found_in_interpreter_scripts_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            scripts = Path(directory) / "Scripts"
            scripts.mkdir()
            command = scripts / "hf.exe"
            command.write_bytes(b"")
            with (
                mock.patch("shutil.which", return_value=None),
                mock.patch("sysconfig.get_path", return_value=str(scripts)),
            ):
                self.assertEqual(find_hf_command(), str(command))

    def test_workflow_is_copied_to_default_user_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_root(directory)
            source = Path(directory) / "workflow.json"
            source.write_text("{}\n", encoding="utf-8")
            destination = install_workflow(
                root,
                source,
                None,
                dry_run=False,
            )
            self.assertEqual(
                destination,
                root / "user" / "default" / "workflows" / "workflow.json",
            )
            self.assertEqual(destination.read_text(encoding="utf-8"), "{}\n")


if __name__ == "__main__":
    unittest.main()
