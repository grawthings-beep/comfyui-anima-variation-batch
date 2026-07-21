import runpy
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from install import MANAGER_INSTALL_ARGUMENTS
from scripts.install_anima_controls import (
    discover_comfyui_root,
    download_artifact,
    find_hf_command,
    install_workflow,
    is_comfyui_root,
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

    def test_manager_hook_installs_required_models_but_defers_preprocessors(self):
        self.assertIn("--skip-preprocessor-models", MANAGER_INSTALL_ARGUMENTS)
        self.assertNotIn("--skip-controlnet-aux", MANAGER_INSTALL_ARGUMENTS)
        self.assertNotIn("--skip-anima-node", MANAGER_INSTALL_ARGUMENTS)
        self.assertNotIn("--skip-workflow", MANAGER_INSTALL_ARGUMENTS)

    def test_prestartup_targets_its_own_comfyui_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_root(directory)
            repository = root / "custom_nodes" / "ComfyUI-AnimaVariationBatch"
            repository.mkdir()
            script = repository / "prestartup_script.py"
            shutil.copy2(
                Path(__file__).parents[1] / "prestartup_script.py",
                script,
            )

            with mock.patch(
                "scripts.install_anima_controls.main"
            ) as install_controls:
                runpy.run_path(str(script))

            install_controls.assert_called_once_with(
                ["--root", str(root), "--skip-preprocessor-models"]
            )

    def test_existing_download_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_root(directory)
            output = root / "models" / "controlnet" / "test.safetensors"
            output.parent.mkdir()
            output.write_bytes(b"valid")
            entry = {
                "id": "test",
                "repo_id": "owner/repo",
                "filename": "test.safetensors",
                "path": "models/controlnet/test.safetensors",
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
