import json
import tempfile
import unittest
from pathlib import Path

from scripts.download_loras import cleanup_legacy_paths, parse_hf_resolve_url, select_loras


MANIFEST_PATH = (
    Path(__file__).parents[1]
    / "config"
    / "anima-loras.json"
)


class LoraManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = json.loads(
            MANIFEST_PATH.read_text(encoding="utf-8")
        )["loras"]

    def test_ids_urls_and_paths_are_unique(self):
        for key in ("id", "url", "path"):
            values = [entry[key] for entry in self.entries]
            self.assertEqual(len(values), len(set(values)), key)

    def test_all_files_install_under_anima_lora_directory(self):
        self.assertTrue(
            all(
                entry["path"].startswith("models/loras/anima/")
                and entry["path"].endswith(".safetensors")
                for entry in self.entries
            )
        )

    def test_lora_filenames_start_with_readable_labels(self):
        for entry in self.entries:
            filename = Path(entry["path"]).name
            self.assertFalse(filename.startswith("anima_"), entry["id"])
            self.assertFalse(filename.endswith("_anima.safetensors"), entry["id"])
            for legacy_path in entry.get("legacy_paths", []):
                self.assertTrue(legacy_path.startswith("models/loras/anima/"))
                self.assertNotEqual(legacy_path, entry["path"])

    def test_recent_loras_are_present(self):
        by_id = {entry["id"]: entry for entry in self.entries}
        self.assertEqual(by_id["eris"]["trigger"], "3r1s")
        self.assertEqual(by_id["label"]["trigger"], "l4bel")
        self.assertEqual(by_id["arkrangerblack"]["trigger"], "4rkblack")
        self.assertEqual(by_id["laplace"]["trigger"], "l4place")
        self.assertEqual(by_id["marciana"]["trigger"], "m4rciana")
        self.assertEqual(by_id["marciana-3"]["trigger"], "m4rciana")
        self.assertEqual(by_id["maxwell"]["trigger"], "m4xwell")
        self.assertEqual(by_id["moran"]["trigger"], "m0ran")
        self.assertEqual(by_id["snowwhite"]["trigger"], "sn0white")
        self.assertEqual(by_id["swimsuit-elegg"]["trigger"], "swimsuitelegg")
        self.assertEqual(by_id["swimsuit-rapi"]["trigger"], "swimsuitrapi")
        self.assertEqual(by_id["white-cinderella"]["trigger"], "whitecinderella")
        self.assertEqual(by_id["anis"]["trigger"], "an1s")
        self.assertEqual(by_id["littlemermaid"]["trigger"], "l1m3rma1d")
        self.assertEqual(by_id["bikini-cinderella"]["trigger"], "bikinicinderella")
        self.assertEqual(by_id["anisstar3"]["trigger"], "an1sstar3")
        self.assertEqual(by_id["pixel-came"]["trigger"], "CAME")
        self.assertEqual(
            by_id["eris"]["url"],
            "https://huggingface.co/uwgm/nikke-loras/resolve/main/"
            "anima_eris.safetensors",
        )
        self.assertEqual(
            by_id["moran"]["url"],
            "https://huggingface.co/uwgm/nikke-loras/resolve/main/"
            "anima_moran%20(1).safetensors",
        )
        self.assertEqual(
            by_id["moran"]["path"],
            "models/loras/anima/Moran - Anima v1.safetensors",
        )
        self.assertEqual(
            by_id["laplace"]["url"],
            "https://huggingface.co/uwgm/nikke-loras/resolve/main/"
            "anima_laplace.safetensors",
        )
        self.assertEqual(
            by_id["maxwell"]["url"],
            "https://huggingface.co/uwgm/nikke-loras/resolve/main/"
            "anima_maxwell.safetensors",
        )
        self.assertEqual(
            by_id["swimsuit-elegg"]["url"],
            "https://huggingface.co/uwgm/nikke-loras/resolve/main/"
            "anima_swimsuit_elegg.safetensors",
        )
        self.assertEqual(
            by_id["swimsuit-rapi"]["url"],
            "https://huggingface.co/uwgm/nikke-loras/resolve/main/"
            "anima_swimsuitrapi.safetensors",
        )
        self.assertEqual(
            by_id["white-cinderella"]["url"],
            "https://huggingface.co/uwgm/nikke-loras/resolve/main/"
            "anima_whitecinderella.safetensors",
        )
        self.assertEqual(
            by_id["anis"]["url"],
            "https://huggingface.co/uwgm/nikke-loras/resolve/main/"
            "anima_anis.safetensors",
        )
        self.assertEqual(
            by_id["marciana"]["url"],
            "https://huggingface.co/uwgm/nikke-loras/resolve/main/"
            "anima_marciana.safetensors",
        )
        self.assertEqual(
            by_id["marciana-3"]["url"],
            "https://huggingface.co/uwgm/nikke-loras/resolve/main/"
            "anima_marciana%20(3).safetensors",
        )
        self.assertEqual(
            by_id["snowwhite"]["url"],
            "https://huggingface.co/uwgm/nikke-loras/resolve/main/"
            "anima_snowwhite%20(1).safetensors",
        )
        self.assertEqual(
            by_id["snowwhite"]["path"],
            "models/loras/anima/Snow White - Anima v1.safetensors",
        )
        self.assertEqual(
            by_id["littlemermaid"]["url"],
            "https://huggingface.co/uwgm/nikke-loras/resolve/main/"
            "anima_littlemermaid.safetensors",
        )
        self.assertEqual(
            by_id["bikini-cinderella"]["url"],
            "https://huggingface.co/uwgm/nikke-loras/resolve/main/"
            "anima_bikinicinderella.safetensors",
        )
        self.assertEqual(
            by_id["anisstar3"]["url"],
            "https://huggingface.co/uwgm/nikke-loras/resolve/main/"
            "anima_anisstar3.safetensors",
        )

    def test_selection_accepts_multiple_ids(self):
        selected = select_loras(self.entries, ["label", "arkrangerblack"])
        self.assertEqual(
            [entry["id"] for entry in selected],
            ["label", "arkrangerblack"],
        )

    def test_legacy_paths_are_removed_only_after_replacement_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            current = root / "models" / "loras" / "anima" / "Rapi - Anima.safetensors"
            legacy = root / "models" / "loras" / "anima" / "anima_rapi.safetensors"
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(b"old")
            entry = {
                "id": "rapi",
                "legacy_paths": ["models/loras/anima/anima_rapi.safetensors"],
            }

            cleanup_legacy_paths(entry, root, current)
            self.assertTrue(legacy.exists())

            current.write_bytes(b"new")
            cleanup_legacy_paths(entry, root, current)
            self.assertFalse(legacy.exists())

    def test_hugging_face_urls_can_be_passed_to_hf_download(self):
        entry = next(item for item in self.entries if item["id"] == "anisstar")
        self.assertEqual(
            parse_hf_resolve_url(entry["url"]),
            (
                "uwgm/nikke-loras",
                "anima_anisstar (2).safetensors",
            ),
        )
        entry = next(item for item in self.entries if item["id"] == "marciana-3")
        self.assertEqual(
            parse_hf_resolve_url(entry["url"]),
            (
                "uwgm/nikke-loras",
                "anima_marciana (3).safetensors",
            ),
        )
        entry = next(item for item in self.entries if item["id"] == "moran")
        self.assertEqual(
            parse_hf_resolve_url(entry["url"]),
            (
                "uwgm/nikke-loras",
                "anima_moran (1).safetensors",
            ),
        )
        entry = next(item for item in self.entries if item["id"] == "snowwhite")
        self.assertEqual(
            parse_hf_resolve_url(entry["url"]),
            (
                "uwgm/nikke-loras",
                "anima_snowwhite (1).safetensors",
            ),
        )


if __name__ == "__main__":
    unittest.main()
