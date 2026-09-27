import itertools
import json
import unittest
from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).parents[1]
    / "example_workflows/anima_two_character_hooks_hiresfix.json"
)


class HooksWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
        cls.nodes = {node["id"]: node for node in cls.workflow["nodes"]}
        cls.sources = {
            (target, slot): (source, output)
            for _, source, output, target, slot, _ in cls.workflow["links"]
        }

    def source(self, node_id, name):
        inputs = self.nodes[node_id]["inputs"]
        slot = next(i for i, item in enumerate(inputs) if item["name"] == name)
        return self.sources.get((node_id, slot))

    def test_core_only_and_two_joint_samplers(self):
        types = [node["type"] for node in self.nodes.values()]
        self.assertEqual(types.count("CreateHookLora"), 2)
        self.assertEqual(types.count("PairConditioningSetProperties"), 2)
        self.assertEqual(types.count("KSampler"), 2)
        self.assertEqual(types.count("MaskToImage"), 2)
        self.assertEqual(types.count("PreviewImage"), 3)
        self.assertNotIn("LoadImage", types)
        self.assertNotIn("SetClipHooks", types)
        self.assertNotIn("UpscaleModelLoader", types)
        self.assertNotIn("ImageUpscaleWithModel", types)
        self.assertNotIn("ImageScale", types)
        self.assertNotIn("VAEEncode", types)
        self.assertFalse(any("Keyframe" in kind for kind in types))
        for node in self.nodes.values():
            self.assertEqual(node["properties"]["cnr_id"], "comfy-core")

    def test_character_lora_dropdowns_are_visible_and_independent(self):
        for node_id, filename in (
            (10, "Bikini Cinderella - Anima.safetensors"),
            (30, "White Cinderella - Anima.safetensors"),
        ):
            node = self.nodes[node_id]
            self.assertEqual(node["widgets_values"], [f"anima/{filename}", 0.8, 0.0])
            self.assertEqual([item["name"] for item in node["inputs"]], ["prev_hooks"])
            self.assertIsNone(self.source(node_id, "prev_hooks"))
        loaders = [node for node in self.nodes.values() if node["type"] == "LoraLoaderModelOnly"]
        self.assertEqual([node["id"] for node in loaders], [8, 9])
        for loader in loaders:
            self.assertEqual(loader["mode"], 0)
        self.assertEqual(loaders[0]["widgets_values"], ["anima-turbo-lora-v0.2.safetensors", 0.65])
        self.assertEqual(loaders[1]["widgets_values"], ["anima/Skin Texture Detail.safetensors", 0.4])

    def test_shared_prompts_reach_both_characters_and_uncovered_background(self):
        for branch in (10, 30):
            self.assertEqual(self.source(branch + 1, "string_a"), (4, 0))
            self.assertEqual(self.source(branch + 2, "string_a"), (5, 0))
            self.assertEqual(self.source(branch + 3, "text"), (branch + 1, 0))
            self.assertEqual(self.source(branch + 4, "text"), (branch + 2, 0))
            self.assertTrue(self.nodes[branch + 1]["widgets_values"][1])
            self.assertTrue(self.nodes[branch + 2]["widgets_values"][1])
        self.assertEqual(self.source(50, "text"), (4, 0))
        self.assertEqual(self.source(51, "text"), (5, 0))
        self.assertIn("bikinicinderella", self.nodes[11]["widgets_values"][1])
        self.assertNotIn("whitecinderella", self.nodes[11]["widgets_values"][1])
        self.assertIn("whitecinderella", self.nodes[31]["widgets_values"][1])
        self.assertNotIn("bikinicinderella", self.nodes[31]["widgets_values"][1])

    def test_same_hook_and_mask_are_attached_to_both_conditioning_sides(self):
        for branch in (10, 30):
            pair = branch + 9
            self.assertEqual(self.source(pair, "positive_NEW"), (branch + 3, 0))
            self.assertEqual(self.source(pair, "negative_NEW"), (branch + 4, 0))
            self.assertEqual(self.source(pair, "hooks"), (branch, 0))
            self.assertEqual(self.source(pair, "mask"), (branch + 7, 0))
            self.assertEqual(self.nodes[pair]["widgets_values"], [1.0, "default"])
            self.assertIsNone(self.source(pair, "timesteps"))
        for name, expected in {
            "positive_A": (19, 0), "negative_A": (19, 1),
            "positive_B": (39, 0), "negative_B": (39, 1),
        }.items():
            self.assertEqual(self.source(52, name), expected)
        for name, expected in {
            "positive": (52, 0), "negative": (52, 1),
            "positive_DEFAULT": (50, 0), "negative_DEFAULT": (51, 0),
        }.items():
            self.assertEqual(self.source(53, name), expected)
        self.assertIsNone(self.source(53, "hooks"))

    def test_both_passes_keep_regional_conditions_and_no_global_character_lora(self):
        self.assertEqual(self.source(8, "model"), (1, 0))
        self.assertEqual(self.source(9, "model"), (8, 0))
        for sampler in (54, 61):
            self.assertEqual(self.source(sampler, "model"), (9, 0))
            self.assertEqual(self.source(sampler, "positive"), (53, 0))
            self.assertEqual(self.source(sampler, "negative"), (53, 1))
            self.assertEqual(self.nodes[sampler]["widgets_values"][1], "fixed")
            self.assertEqual(self.nodes[sampler]["widgets_values"][3], 1.0)
        self.assertEqual(self.source(54, "latent_image"), (7, 0))
        self.assertEqual(self.source(61, "latent_image"), (57, 0))
        self.assertEqual(self.nodes[54]["widgets_values"][-1], 1.0)
        self.assertEqual(self.nodes[61]["widgets_values"][-1], 0.55)

    def test_sampler_profile_matches_supplied_single_character_workflow(self):
        self.assertEqual(
            self.nodes[54]["widgets_values"][2:],
            [18, 1.0, "res_multistep", "sgm_uniform", 1.0],
        )
        self.assertEqual(
            self.nodes[61]["widgets_values"][2:],
            [8, 1.0, "res_multistep", "sgm_uniform", 0.55],
        )
        self.assertEqual(self.nodes[7]["widgets_values"], [1152, 1536, 1])
        self.assertEqual(self.nodes[57]["widgets_values"], ["bislerp", 1.5])
        width, height, _ = self.nodes[7]["widgets_values"]
        self.assertEqual((width * 1.5, height * 1.5), (1728, 2304))

    def test_prompt_style_is_not_forced_by_the_regional_template(self):
        prompt = self.nodes[4]["widgets_values"][0]
        self.assertNotIn("anime illustration", prompt)
        self.assertNotIn("detailed anime shading", prompt)
        self.assertEqual(
            self.nodes[5]["widgets_values"][0],
            "worst quality, low quality, early, old, score_1, score_2, score_3, "
            "cartoon, graphic, painting, crayon, graphite, abstract, glitch, "
            "deformed, mutated, ugly, disfigured, long body, bad anatomy, bad "
            "hands, missing fingers, extra fingers, extra digits, fewer digits, "
            "cropped, very displeasing, artist name, blurry, jpeg artifacts, "
            "lowres, censor",
        )

    def test_hires_chain_and_visible_results(self):
        for target, input_name, expected in (
            (55, "samples", (54, 0)), (55, "vae", (3, 0)),
            (56, "images", (55, 0)), (57, "samples", (54, 0)),
            (62, "samples", (61, 0)), (62, "vae", (3, 0)),
            (63, "images", (62, 0)),
        ):
            self.assertEqual(self.source(target, input_name), expected)
        self.assertEqual(self.nodes[57]["type"], "LatentUpscaleBy")
        for output in (18, 38, 56, 63):
            self.assertEqual(self.nodes[output]["mode"], 0)

    def test_masks_have_correct_preview_and_no_horizontal_gap(self):
        self.assertEqual(self.nodes[6]["widgets_values"], [0, 1152, 1536])
        for branch in (10, 30):
            self.assertEqual(self.source(branch + 6, "mask"), (branch + 5, 0))
            self.assertEqual(self.source(branch + 7, "source"), (branch + 6, 0))
            self.assertEqual(self.source(branch + 7, "destination"), (6, 0))
            self.assertEqual(self.source(branch + 10, "mask"), (branch + 7, 0))
            self.assertEqual(self.source(branch + 8, "images"), (branch + 10, 0))
        a = self.mask_row(10)
        b = self.mask_row(30)
        self.assertEqual((a[0], b[0]), (1.0, 0.0))
        self.assertEqual((a[-1], b[-1]), (0.0, 1.0))
        self.assertTrue(all(left + right >= 1.0 for left, right in zip(a, b)))
        self.assertEqual(sum(left > 0 and right > 0 for left, right in zip(a, b)), 48)
        self.assertAlmostEqual(a[576], 0.5)
        self.assertAlmostEqual(b[575], 0.5)

    def mask_row(self, branch):
        value, width, height = self.nodes[branch + 5]["widgets_values"]
        x, y, operation = self.nodes[branch + 7]["widgets_values"]
        left, top, right, bottom = self.nodes[branch + 6]["widgets_values"]
        self.assertEqual((y, height, top, bottom, operation), (0, 1536, 0, 0, "add"))
        source = [value] * width
        for i in range(left):
            source[i] *= (i + 1) / left
        for i in range(right):
            source[-i - 1] *= (i + 1) / right
        row = [0.0] * 1152
        row[x:x + width] = source
        return row

    def test_link_types_backreferences_and_node_ids(self):
        self.assertEqual(len(self.nodes), len(self.workflow["nodes"]))
        self.assertEqual(self.workflow["last_node_id"], max(self.nodes))
        self.assertEqual(self.workflow["last_link_id"], len(self.workflow["links"]))
        link_ids = {link[0] for link in self.workflow["links"]}
        for node in self.nodes.values():
            for item in node["inputs"]:
                if item["link"] is not None:
                    self.assertIn(item["link"], link_ids)
            for output in node["outputs"]:
                self.assertTrue(set(output["links"]) <= link_ids)
        for _, source, source_slot, target, target_slot, kind in self.workflow["links"]:
            self.assertEqual(self.nodes[source]["outputs"][source_slot]["type"], kind)
            self.assertEqual(self.nodes[target]["inputs"][target_slot]["type"], kind)

    def test_node_rectangles_and_titles_do_not_overlap(self):
        for first, second in itertools.combinations(self.nodes.values(), 2):
            x1, y1 = first["pos"]
            w1, h1 = first["size"]
            x2, y2 = second["pos"]
            w2, h2 = second["size"]
            separated = (
                x1 + w1 <= x2 or x2 + w2 <= x1
                or y1 + h1 <= y2 - 30 or y2 + h2 <= y1 - 30
            )
            self.assertTrue(separated, f"Overlapping nodes: {first['id']}, {second['id']}")


if __name__ == "__main__":
    unittest.main()
