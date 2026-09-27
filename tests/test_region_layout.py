import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from region_layout import DEFAULT_LAYOUT, AnimaRegionLayout, AnimaRegionalCharacter, normalize_layout, rasterize_layout


class RegionLayoutTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is needed to compare browser masks")
    def test_browser_preview_matches_backend_masks(self):
        script = """
        import { preset, transform, weightAt, OWNERS } from './web/region_geometry.js';
        const cases = [];
        for (const name of ['3 columns', '4 rows', '2 x 2']) {
            let layout = transform(preset(name), 'r1', 'move', 0.03, 0.04);
            layout.overlap = 0.07; layout.feather = 0.11;
            layout.regions[1].owner = 'A';
            layout.regions[2].enabled = false;
            for (const [width, height] of [[64, 96], [96, 64]]) {
                const samples = [];
                for (let y = 0; y < height; y += 3) for (let x = 0; x < width; x += 3) {
                    const values = OWNERS.map(owner => Math.max(0, ...layout.regions
                        .filter(r => r.owner === owner)
                        .map(r => weightAt(r, layout, x + 0.5, y + 0.5, width, height))));
                    samples.push({x, y, values});
                }
                cases.push({layout, width, height, samples});
            }
        }
        console.log(JSON.stringify(cases));
        """
        result = subprocess.run(
            [shutil.which("node"), "--input-type=module", "-e", script],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=True,
        )
        for case in json.loads(result.stdout):
            masks = rasterize_layout(case["layout"], case["width"], case["height"])
            expected = np.array([sample["values"] for sample in case["samples"]])
            actual = np.array([masks[:, sample["y"], sample["x"]] for sample in case["samples"]])
            np.testing.assert_allclose(actual, expected, atol=2e-6)

    def test_two_columns_cover_without_gap_and_unused_slots_are_zero(self):
        masks = rasterize_layout(DEFAULT_LAYOUT, 128, 192)
        self.assertEqual(masks.shape, (4, 192, 128))
        self.assertEqual(masks.dtype, np.float32)
        np.testing.assert_allclose(masks.sum(axis=0), 1, atol=1e-6)
        self.assertEqual(masks[0, 0, 0], 1)
        self.assertEqual(masks[1, -1, -1], 1)
        self.assertFalse(masks[2:].any())

    def test_rows_columns_and_grid_at_different_aspect_ratios(self):
        for cols, rows in ((3, 1), (1, 3), (4, 1), (1, 4), (2, 2)):
            layout = {"version": 1, "regions": [
                {"id": str(i), "owner": "ABCD"[i], "x": (i % cols)/cols, "y": (i//cols)/rows, "w": 1/cols, "h": 1/rows}
                for i in range(cols*rows)
            ]}
            for width, height in ((128, 192), (192, 128), (128, 128)):
                masks = rasterize_layout(layout, width, height)
                np.testing.assert_allclose(masks.sum(axis=0), 1, atol=2e-6)
                for i, r in enumerate(layout["regions"]):
                    x, y = int((r["x"]+r["w"]/2)*width), int((r["y"]+r["h"]/2)*height)
                    self.assertEqual(masks[i, y, x], 1)

    def test_same_owner_union_and_disabled_regions(self):
        layout = normalize_layout(DEFAULT_LAYOUT)
        layout["regions"][1]["owner"] = "A"
        layout["regions"].append(dict(layout["regions"][0], id="r3"))
        masks = rasterize_layout(layout, 128, 128)
        self.assertLessEqual(masks.max(), 1)
        self.assertFalse(masks[1:].any())
        layout["regions"][0]["enabled"] = False
        layout["regions"][2]["enabled"] = False
        self.assertEqual(rasterize_layout(layout, 128, 128)[0, 64, 1], 0)

    def test_empty_layout_and_uncovered_background(self):
        self.assertFalse(rasterize_layout({"version": 1, "regions": []}, 64, 64).any())
        layout = normalize_layout(DEFAULT_LAYOUT)
        layout["regions"] = [dict(layout["regions"][0], x=.25, y=.25, w=.5, h=.5)]
        masks = rasterize_layout(layout, 128, 128)
        self.assertEqual(masks[0, 0, 0], 0)
        self.assertEqual(masks[0, 64, 64], 1)

    def test_validation_clamps_bounds_and_rejects_bad_data(self):
        layout = normalize_layout(DEFAULT_LAYOUT)
        layout["regions"][0].update(x=2, w=3, y=-5, h=3)
        region = normalize_layout(layout)["regions"][0]
        self.assertAlmostEqual(region["x"] + region["w"], 1)
        self.assertEqual((region["y"], region["h"]), (0, 1))
        for value in ("{", "[]", {"version": 2}, {"version": 1, "regions": [None]}, {"version": 1, "regions": [{}]}):
            with self.assertRaises(ValueError): normalize_layout(value)
        for key, value in (("x", float("nan")), ("w", True), ("enabled", "false"), ("owner", "")):
            bad = normalize_layout(DEFAULT_LAYOUT); bad["regions"][0][key] = value
            with self.assertRaises(ValueError): normalize_layout(bad)
        for dims in ((65, 128), (0, 64), (8192, 64)):
            with self.assertRaises(ValueError): rasterize_layout(DEFAULT_LAYOUT, *dims)

    def test_serialization_and_node_outputs(self):
        layout = normalize_layout(DEFAULT_LAYOUT)
        self.assertEqual(layout, normalize_layout(json.dumps(layout)))
        with patch.dict(sys.modules, {"torch": SimpleNamespace(from_numpy=lambda x: x)}):
            outputs = AnimaRegionLayout().create(64, 128, json.dumps(layout))
        self.assertEqual(outputs[-2:], (64, 128))
        self.assertEqual(outputs[0].shape, (1, 128, 64))


class RegionalCharacterTests(unittest.TestCase):
    def call(self, node, mask, **kwargs):
        settings = dict(clip="clip", mask=mask, shared_positive="scene", shared_negative="bad",
                        lora_name="a.safetensors", strength=.8, positive="identity", negative="outfit")
        settings.update(kwargs)
        return node.condition(**settings)

    def test_unused_character_does_not_import_or_load_models(self):
        node = AnimaRegionalCharacter(); node._hook_loader = object()
        with patch.dict(sys.modules, {"nodes": None, "comfy_extras.nodes_hooks": None}):
            self.assertEqual(self.call(node, np.zeros((1,64,64)), lora_name="missing.safetensors"), ([], []))
        self.assertIsNone(node._hook_loader)
        self.assertTrue(node.VALIDATE_INPUTS("missing.safetensors"))

    def test_active_character_uses_matching_pair_mask_and_model_only_hook(self):
        encoder, loader, properties = Mock(), Mock(), Mock()
        encoder.encode.side_effect = [("pos",), ("neg",)]
        loader.create_hook.return_value = ("hook",)
        properties.set_properties.return_value = ("pair_pos", "pair_neg")
        modules = {"nodes": SimpleNamespace(CLIPTextEncode=lambda: encoder),
                   "folder_paths": SimpleNamespace(get_full_path=lambda *_: "model"),
                   "comfy_extras.nodes_hooks": SimpleNamespace(CreateHookLora=lambda: loader, PairConditioningSetProperties=lambda: properties)}
        mask = np.ones((1,64,64))
        with patch.dict(sys.modules, modules):
            self.assertEqual(self.call(AnimaRegionalCharacter(), mask), ("pair_pos", "pair_neg"))
        loader.create_hook.assert_called_once_with("a.safetensors", .8, 0.0)
        self.assertEqual(encoder.encode.call_args_list[0].args, ("clip", "scene\n\nidentity"))
        self.assertEqual(encoder.encode.call_args_list[1].args, ("clip", "bad, outfit"))
        self.assertIs(properties.set_properties.call_args.kwargs["mask"], mask)
        self.assertEqual(properties.set_properties.call_args.kwargs["hooks"], "hook")
        self.assertEqual(properties.set_properties.call_args.kwargs["set_cond_area"], "default")

    def test_prompt_only_slot_and_active_missing_file(self):
        encoder = Mock(); encoder.encode.return_value = ([],)
        hook = Mock(); props = Mock(); props.set_properties.return_value = ([], [])
        modules = {"nodes": SimpleNamespace(CLIPTextEncode=lambda: encoder),
                   "folder_paths": SimpleNamespace(get_full_path=lambda *_: None),
                   "comfy_extras.nodes_hooks": SimpleNamespace(CreateHookLora=hook, PairConditioningSetProperties=lambda: props)}
        with patch.dict(sys.modules, modules):
            self.call(AnimaRegionalCharacter(), np.ones((1,64,64)), lora_name="(none)")
            self.call(AnimaRegionalCharacter(), np.ones((1,64,64)), strength=0)
            hook.assert_not_called()
            with self.assertRaisesRegex(ValueError, "Active regional LoRA"):
                self.call(AnimaRegionalCharacter(), np.ones((1,64,64)))
