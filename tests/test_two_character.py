import unittest

from two_character import (
    AnimaCharacterPairPrompt,
    character_entries,
    character_options,
    resolve_character,
    soft_region_bounds,
)


class TwoCharacterTests(unittest.TestCase):
    def test_character_options_are_readable_and_resolve_to_lora_paths(self):
        options = character_options()
        self.assertGreaterEqual(len(options), 2)
        self.assertTrue(all("trigger:" in option for option in options))
        self.assertFalse(any("Style" in option for option in options))
        self.assertFalse(any("Pixel AnimaB" in option for option in options))

        rapi = next(
            entry for entry in character_entries() if entry["id"] == "rapi"
        )
        self.assertEqual(resolve_character(rapi["label"]), rapi)
        self.assertEqual(
            rapi["lora_name"],
            "anima/Rapi - Anima.safetensors",
        )

    def test_pair_prompt_injects_triggers_and_keeps_positions_distinct(self):
        entries = {entry["id"]: entry for entry in character_entries()}
        output = AnimaCharacterPairPrompt().build(
            "masterpiece, best quality, 2girls in a shared scene",
            entries["rapi"]["label"],
            "red jacket and a calm expression",
            0.75,
            entries["anis"]["label"],
            "warm smile and a distinct outfit",
            0.85,
        )

        self.assertIn(
            "masterpiece, best quality, 2girls in a shared scene",
            output[0],
        )
        self.assertIn("r4pi", output[0])
        self.assertIn("left side", output[0])
        self.assertIn("Character B", output[0])
        self.assertIn("an1s", output[1])
        self.assertIn("right side", output[1])
        self.assertIn("Character A", output[1])
        self.assertEqual(output[2], entries["rapi"]["lora_name"])
        self.assertEqual(output[3], 0.75)
        self.assertEqual(output[4], entries["anis"]["lora_name"])
        self.assertEqual(output[5], 0.85)

    def test_soft_region_bounds_include_feather_outside_hard_region(self):
        self.assertEqual(
            soft_region_bounds(26, 48, 6),
            (-4.0, 2.0, 50.0, 56.0),
        )
        self.assertEqual(
            soft_region_bounds(74, 48, 6),
            (44.0, 50.0, 98.0, 104.0),
        )


if __name__ == "__main__":
    unittest.main()
