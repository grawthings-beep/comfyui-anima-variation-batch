import itertools
import json
import unittest
from pathlib import Path

from region_layout import AnimaRegionLayout, AnimaRegionalCharacter, normalize_layout


class HooksWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = json.loads((Path(__file__).parents[1] / "example_workflows/anima_two_character_hooks_hiresfix.json").read_text())
        cls.nodes = {n["id"]: n for n in cls.workflow["nodes"]}
        cls.sources = {(target, slot): (source, output) for _, source, output, target, slot, _ in cls.workflow["links"]}

    def source(self, node, name):
        slot = next(i for i, item in enumerate(self.nodes[node]["inputs"]) if item["name"] == name)
        return self.sources.get((node, slot))

    def test_four_characters_share_one_live_layout(self):
        self.assertEqual(self.nodes[6]["type"], "AnimaRegionLayout")
        layout = normalize_layout(self.nodes[6]["widgets_values"][2])
        self.assertEqual([r["owner"] for r in layout["regions"]], ["A", "B"])
        for i, node in enumerate((10, 30, 40, 41)):
            self.assertEqual(self.nodes[node]["type"], "AnimaRegionalCharacter")
            self.assertEqual(self.source(node, "mask"), (6, i))
            self.assertEqual(self.source(node, "clip"), (2, 0))
            self.assertEqual(self.source(node, "shared_positive"), (4, 0))
            self.assertEqual(self.source(node, "shared_negative"), (5, 0))
        for node in (40, 41):
            self.assertEqual(self.nodes[node]["widgets_values"], ["(none)", .8, "", ""])
        self.assertIn("Bikini Cinderella", self.nodes[10]["widgets_values"][0])
        self.assertIn("White Cinderella", self.nodes[30]["widgets_values"][0])
        self.assertIn("bikinicinderella", self.nodes[10]["widgets_values"][2])
        self.assertIn("whitecinderella", self.nodes[30]["widgets_values"][2])

    def test_dimensions_are_connected_not_duplicated(self):
        self.assertEqual(self.nodes[6]["widgets_values"][:2], [1152, 1536])
        self.assertEqual(self.source(7, "width"), (6, 4))
        self.assertEqual(self.source(7, "height"), (6, 5))
        self.assertEqual([o["type"] for o in self.nodes[6]["outputs"]], list(AnimaRegionLayout.RETURN_TYPES))

    def test_all_pairs_and_shared_fallback_reach_both_passes(self):
        for node, first, second in ((52, 10, 30), (58, 40, 41), (59, 52, 58)):
            for name, expected in {"positive_A": (first, 0), "negative_A": (first, 1), "positive_B": (second, 0), "negative_B": (second, 1)}.items():
                self.assertEqual(self.source(node, name), expected)
        self.assertEqual(self.source(53, "positive"), (59, 0))
        self.assertEqual(self.source(53, "negative"), (59, 1))
        self.assertEqual(self.source(53, "positive_DEFAULT"), (50, 0))
        self.assertEqual(self.source(53, "negative_DEFAULT"), (51, 0))
        self.assertIsNone(self.source(53, "hooks"))
        for sampler in (54, 61):
            self.assertEqual(self.source(sampler, "positive"), (53, 0))
            self.assertEqual(self.source(sampler, "negative"), (53, 1))
            self.assertEqual(self.source(sampler, "model"), (9, 0))

    def test_preferred_texture_profile_and_latent_path_are_preserved(self):
        self.assertEqual(self.source(8, "model"), (1, 0))
        self.assertEqual(self.source(9, "model"), (8, 0))
        self.assertEqual(self.nodes[8]["widgets_values"], ["anima-turbo-lora-v0.2.safetensors", .65])
        self.assertEqual(self.nodes[9]["widgets_values"], ["anima/Skin Texture Detail.safetensors", .4])
        self.assertEqual(self.nodes[54]["widgets_values"][2:], [18, 1, "res_multistep", "sgm_uniform", 1])
        self.assertEqual(self.nodes[61]["widgets_values"][2:], [8, 1, "res_multistep", "sgm_uniform", .55])
        self.assertEqual(self.nodes[57]["widgets_values"], ["bislerp", 1.5])
        self.assertEqual(self.source(57, "samples"), (54, 0))
        self.assertEqual(self.source(61, "latent_image"), (57, 0))
        self.assertEqual(self.source(54, "latent_image"), (7, 0))
        self.assertEqual(self.source(63, "images"), (62, 0))
        for node in (8, 9, 56, 63):
            self.assertEqual(self.nodes[node]["mode"], 0)
        types = [n["type"] for n in self.nodes.values()]
        self.assertEqual(types.count("KSampler"), 2)
        for kind in ("SolidMask", "FeatherMask", "MaskComposite", "LoadImage", "UpscaleModelLoader", "VAEEncode"):
            self.assertNotIn(kind, types)

    def test_node_rectangles_and_titles_do_not_overlap(self):
        for a, b in itertools.combinations(self.nodes.values(), 2):
            x, y = a["pos"]; w, h = a["size"]
            xx, yy = b["pos"]; ww, hh = b["size"]
            self.assertTrue(x + w <= xx or xx + ww <= x or y + h <= yy - 30 or yy + hh <= y - 30, (a["id"], b["id"]))

    def test_all_link_types_match(self):
        self.assertEqual(len(self.nodes), len(self.workflow["nodes"]))
        for _, a, out, b, inp, kind in self.workflow["links"]:
            self.assertEqual(self.nodes[a]["outputs"][out]["type"], kind)
            self.assertEqual(self.nodes[b]["inputs"][inp]["type"], kind)
        for node in (10, 30, 40, 41):
            self.assertEqual([o["type"] for o in self.nodes[node]["outputs"]], list(AnimaRegionalCharacter.RETURN_TYPES))
