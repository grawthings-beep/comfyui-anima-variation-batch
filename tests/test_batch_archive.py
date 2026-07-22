import importlib.util
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from batch_archive import write_archive
from zip_output import AnimaSaveQueueZip, first, safe_stem


class BatchArchiveTests(unittest.TestCase):
    def test_archive_contains_numbered_images_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "queue.zip"
            write_archive(
                path,
                [
                    ("scene_001.png", b"png one"),
                    ("scene_002.png", b"png two"),
                ],
                manifest=lambda: "001\tscene_001.png\n002\tscene_002.png",
            )
            with zipfile.ZipFile(path) as archive:
                self.assertEqual(
                    archive.namelist(),
                    ["scene_001.png", "scene_002.png", "manifest.txt"],
                )
                self.assertEqual(archive.read("scene_002.png"), b"png two")

    def test_failed_archive_does_not_publish_partial_file(self):
        def broken_entries():
            yield "scene_001.png", b"first"
            raise RuntimeError("broken")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "queue.zip"
            with self.assertRaisesRegex(RuntimeError, "broken"):
                write_archive(path, broken_entries())
            self.assertFalse(path.exists())
            self.assertFalse(path.with_suffix(".zip.tmp").exists())

    def test_zip_node_receives_all_mapped_images_in_one_call(self):
        self.assertTrue(AnimaSaveQueueZip.INPUT_IS_LIST)
        self.assertTrue(AnimaSaveQueueZip.OUTPUT_NODE)
        self.assertEqual(first([True]), True)
        self.assertEqual(safe_stem("folder/scene 001", 1), "scene_001")

    @unittest.skipUnless(
        importlib.util.find_spec("numpy") and importlib.util.find_spec("PIL"),
        "optional image libraries are unavailable",
    )
    def test_zip_node_encodes_images_without_individual_output_files(self):
        import numpy as np

        class FakeImage:
            def __init__(self, value):
                self.array = np.full((4, 5, 3), value, dtype=np.float32)
                self.shape = self.array.shape

            def cpu(self):
                return self

            def numpy(self):
                return self.array

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            folder_paths = types.ModuleType("folder_paths")
            folder_paths.get_output_directory = lambda: str(output)
            folder_paths.get_save_image_path = lambda *_args: (
                str(output / "anima_batches"),
                "Anima_latent_queue",
                1,
                "anima_batches",
                "Anima_latent_queue",
            )
            comfy = types.ModuleType("comfy")
            comfy.__path__ = []
            cli_args = types.ModuleType("comfy.cli_args")
            cli_args.args = types.SimpleNamespace(disable_metadata=False)

            with mock.patch.dict(
                sys.modules,
                {
                    "folder_paths": folder_paths,
                    "comfy": comfy,
                    "comfy.cli_args": cli_args,
                },
            ):
                result = AnimaSaveQueueZip().save_zip(
                    images=[[FakeImage(0.25)], [FakeImage(0.75)]],
                    file_stems=["queue/scene_001", "queue/scene_002"],
                    archive_name=["anima_batches/Anima_latent_queue"],
                    auto_download=[True],
                    prompt=[{"node": "prompt"}],
                    extra_pnginfo=[{"workflow": {"test": True}}],
                )

            archive_path = (
                output / "anima_batches" / "Anima_latent_queue_00001.zip"
            )
            self.assertTrue(archive_path.is_file())
            self.assertEqual(list(output.rglob("*.png")), [])
            with zipfile.ZipFile(archive_path) as archive:
                self.assertEqual(
                    archive.namelist(),
                    ["scene_001.png", "scene_002.png", "manifest.txt"],
                )
            archive_ui = result["ui"]["zip"][0]
            self.assertEqual(archive_ui["count"], 2)
            self.assertTrue(archive_ui["auto_download"])


if __name__ == "__main__":
    unittest.main()
