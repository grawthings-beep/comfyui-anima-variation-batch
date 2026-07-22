import importlib.util
import sys
import unittest
from pathlib import Path

from nodes import MAX_SEED, AnimaPromptQueue, split_scenes


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
        finally:
            sys.modules.pop(module_name, None)
            sys.modules.pop(f"{module_name}.nodes", None)

    def test_splits_whitespace_only_blank_lines_and_preserves_prompt_lines(self):
        text = "scene one\ncontinued\r\n\t\r\nscene two\n\n\nscene three"
        self.assertEqual(
            split_scenes(text),
            ["scene one\ncontinued", "scene two", "scene three"],
        )

    def test_expands_selected_scenes_with_aligned_seeds_and_prefixes(self):
        result = AnimaPromptQueue().expand(
            "scene one\n\nscene two\n\nscene three\n\nscene four",
            start_scene=2,
            scene_limit=2,
            base_seed=100,
            filename_prefix="Anima/test",
        )
        self.assertEqual(result[0], ["scene two", "scene three"])
        self.assertEqual(result[1], [102, 104])
        self.assertEqual(result[2], [103, 105])
        self.assertEqual(
            result[3],
            ["Anima/test/scene_002", "Anima/test/scene_003"],
        )

    def test_seed_values_wrap_at_comfyui_maximum(self):
        result = AnimaPromptQueue().expand(
            "scene one\n\nscene two",
            start_scene=1,
            scene_limit=2,
            base_seed=MAX_SEED,
            filename_prefix="",
        )
        self.assertEqual(result[1], [MAX_SEED, 1])
        self.assertEqual(result[2], [0, 2])
        self.assertEqual(result[3][0], "Anima_latent_queue/scene_001")

    def test_empty_input_and_out_of_range_start_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            AnimaPromptQueue().expand(" \n\n ", 1, 50, 0, "output")
        with self.assertRaisesRegex(ValueError, "only 1 scenes"):
            AnimaPromptQueue().expand("scene one", 2, 50, 0, "output")

    def test_node_outputs_are_lists_and_scene_limit_is_capped_at_fifty(self):
        self.assertEqual(AnimaPromptQueue.OUTPUT_IS_LIST, (True, True, True, True))
        scene_limit = AnimaPromptQueue.INPUT_TYPES()["required"]["scene_limit"]
        self.assertEqual(scene_limit[1]["default"], 50)
        self.assertEqual(scene_limit[1]["max"], 50)


if __name__ == "__main__":
    unittest.main()
