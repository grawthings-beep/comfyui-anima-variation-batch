import unittest

from inpaint_lora_select import (
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


if __name__ == "__main__":
    unittest.main()
