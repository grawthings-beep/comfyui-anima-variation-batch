import unittest
from types import ModuleType
from unittest import mock

from inpaint_lora_select import (
    AnimaCharacterLoRALoader,
    AnimaCharacterLoRASelect,
    character_options,
    resolve_character,
)


class InpaintLoRASelectTests(unittest.TestCase):
    def test_character_options_use_short_readable_names(self):
        options = character_options()
        self.assertIn("Kotobuki Hisako", options)
        self.assertIn("Michinoku Komaro", options)
        self.assertNotIn(
            "Kotobuki Hisako Anima LoRA (trigger: kotobukihisako)",
            options,
        )

    def test_selector_returns_manifest_lora_path_without_editing_prompt(self):
        selector = AnimaCharacterLoRASelect()
        self.assertEqual(
            selector.select("Kotobuki Hisako", 0.85),
            ("anima/Kotobuki Hisako - Anima.safetensors", 0.85),
        )
        self.assertEqual(
            selector.select("Michinoku Komaro", 0.9),
            ("anima/Michinoku Komaro - Anima.safetensors", 0.9),
        )

    def test_selector_accepts_manifest_id(self):
        entry = resolve_character("michinoku-komaro")
        self.assertEqual(entry["label"], "Michinoku Komaro")

    def test_combined_loader_has_visible_character_dropdown(self):
        required = AnimaCharacterLoRALoader.INPUT_TYPES()["required"]
        self.assertEqual(required["model"], ("MODEL",))
        self.assertIn("Anis", required["character"][0])
        self.assertIn("Michinoku Komaro", required["character"][0])
        self.assertEqual(required["strength"][0], "FLOAT")

    def test_combined_loader_resolves_character_before_core_load(self):
        calls = []

        class FakeCoreLoader:
            def load_lora_model_only(self, model, lora_name, strength):
                calls.append((model, lora_name, strength))
                return ("loaded-model",)

        fake_nodes = ModuleType("nodes")
        fake_nodes.LoraLoaderModelOnly = FakeCoreLoader
        loader = AnimaCharacterLoRALoader()
        with mock.patch.dict("sys.modules", {"nodes": fake_nodes}):
            result = loader.load_character_lora("base-model", "Anis", 0.75)

        self.assertEqual(result, ("loaded-model",))
        self.assertEqual(
            calls,
            [("base-model", "anima/Anis - Anima.safetensors", 0.75)],
        )


if __name__ == "__main__":
    unittest.main()
