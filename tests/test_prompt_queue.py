import importlib.util
import sys
import unittest
from pathlib import Path

from prompt_queue import BATCH_RANGES, MAX_SEED, AnimaPromptQueue, split_scenes


class PromptQueueTests(unittest.TestCase):
    def test_package_registers_prompt_queue_node(self):
        root = Path(__file__).parents[1]
        module_name = "anima_variation_batch_registration_test"
        spec = importlib.util.spec_from_file_location(
            module_name,
            root / "__init__.py",
            submodule_search_locations=[str(root)],
        )
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
            registered = module.NODE_CLASS_MAPPINGS["AnimaPromptQueue"]
            self.assertEqual(registered.__name__, "AnimaPromptQueue")
            self.assertIn("AnimaSaveQueueZip", module.NODE_CLASS_MAPPINGS)
            self.assertEqual(module.WEB_DIRECTORY, "./web")
        finally:
            sys.modules.pop(module_name, None)
            sys.modules.pop(f"{module_name}.prompt_queue", None)
            sys.modules.pop(f"{module_name}.zip_output", None)
            sys.modules.pop(f"{module_name}.batch_archive", None)

    def test_splits_whitespace_only_blank_lines_and_preserves_prompt_lines(self):
        text = "scene one\ncontinued\r\n\t\r\nscene two\n\n\nscene three"
        self.assertEqual(
            split_scenes(text),
            ["scene one\ncontinued", "scene two", "scene three"],
        )

    def test_expands_selected_scenes_with_aligned_seeds_and_prefixes(self):
        result = AnimaPromptQueue().expand(
            "scene one\n\nscene two\n\nscene three\n\nscene four",
            batch_range="51-100",
            start_in_range=2,
            scene_limit=2,
            base_seed=100,
            filename_prefix="Anima/test",
        )
        self.assertEqual(result[0], ["scene two", "scene three"])
        self.assertEqual(result[1], [202, 204])
        self.assertEqual(result[2], [203, 205])
        self.assertEqual(
            result[3],
            ["Anima/test/scene_052", "Anima/test/scene_053"],
        )
        self.assertEqual(
            result[4],
            ["anima_batches/test_051-100", "anima_batches/test_051-100"],
        )

    def test_seed_values_wrap_at_comfyui_maximum(self):
        result = AnimaPromptQueue().expand(
            "scene one\n\nscene two",
            batch_range="1-50",
            start_in_range=1,
            scene_limit=2,
            base_seed=MAX_SEED,
            filename_prefix="",
        )
        self.assertEqual(result[1], [MAX_SEED, 1])
        self.assertEqual(result[2], [0, 2])
        self.assertEqual(result[3][0], "Anima_latent_queue/scene_001")

    def test_empty_input_and_out_of_range_start_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            AnimaPromptQueue().expand(" \n\n ", "1-50", 1, 50, 0, "output")
        with self.assertRaisesRegex(ValueError, "only 1 scenes"):
            AnimaPromptQueue().expand("scene one", "1-50", 2, 50, 0, "output")

    def test_range_selector_numbers_separate_fifty_prompt_pastes(self):
        scenes = "\n\n".join(f"prompt {index}" for index in range(1, 51))
        result = AnimaPromptQueue().expand(
            scenes,
            batch_range="251-300",
            start_in_range=1,
            scene_limit=50,
            base_seed=0,
            filename_prefix="Anima_latent_queue",
        )
        self.assertEqual(len(result[0]), 50)
        self.assertEqual(result[3][0], "Anima_latent_queue/scene_251")
        self.assertEqual(result[3][-1], "Anima_latent_queue/scene_300")
        self.assertEqual(
            result[4][0],
            "anima_batches/Anima_latent_queue_251-300",
        )

    def test_range_end_caps_a_resumed_batch(self):
        scenes = "\n\n".join(f"prompt {index}" for index in range(1, 51))
        result = AnimaPromptQueue().expand(
            scenes,
            batch_range="101-150",
            start_in_range=41,
            scene_limit=50,
            base_seed=0,
            filename_prefix="output",
        )
        self.assertEqual(len(result[0]), 10)
        self.assertEqual(result[3][0], "output/scene_141")
        self.assertEqual(result[3][-1], "output/scene_150")

    def test_node_outputs_are_lists_and_scene_limit_is_capped_at_fifty(self):
        self.assertEqual(
            AnimaPromptQueue.OUTPUT_IS_LIST,
            (True, True, True, True, True),
        )
        self.assertEqual(BATCH_RANGES[0], "1-50")
        self.assertEqual(BATCH_RANGES[-1], "251-300")
        scene_limit = AnimaPromptQueue.INPUT_TYPES()["required"]["scene_limit"]
        self.assertEqual(scene_limit[1]["default"], 50)
        self.assertEqual(scene_limit[1]["max"], 50)


if __name__ == "__main__":
    unittest.main()
