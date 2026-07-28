import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
WORKFLOW_DIR = ROOT / "example_workflows"
HIRES_ESRGAN_WORKFLOW_PATH = WORKFLOW_DIR / "anima_hiresfix_esrgan_2pass.json"
HIRES_LATENT_WORKFLOW_PATH = WORKFLOW_DIR / "anima_hiresfix_latent_2pass.json"
TWO_CHARACTER_WORKFLOW_PATH = (
    WORKFLOW_DIR / "anima_two_character_regional_hiresfix.json"
)


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hires_esrgan = cls.load(HIRES_ESRGAN_WORKFLOW_PATH)
        cls.hires_latent = cls.load(HIRES_LATENT_WORKFLOW_PATH)
        cls.two_character = cls.load(TWO_CHARACTER_WORKFLOW_PATH)
        cls.workflows = (
            cls.hires_esrgan,
            cls.hires_latent,
            cls.two_character,
        )

    @staticmethod
    def load(path):
        return json.loads(path.read_text(encoding="utf-8"))

    def test_only_supported_example_workflows_remain(self):
        workflow_names = sorted(path.name for path in WORKFLOW_DIR.glob("*.json"))
        self.assertEqual(
            workflow_names,
            [
                "anima_hiresfix_esrgan_2pass.json",
                "anima_hiresfix_latent_2pass.json",
                "anima_two_character_regional_hiresfix.json",
            ],
        )

    def test_all_workflow_links_reference_existing_nodes_and_sockets(self):
        for workflow in self.workflows:
            with self.subTest(workflow=workflow.get("id")):
                self.assert_links_reference_existing_nodes_and_sockets(workflow)

    def test_hires_workflows_do_not_use_removed_custom_nodes(self):
        removed_nodes = {
            "AnimaVariationGroup",
            "AnimaMultiAngle",
            "AnimaMultiAnglePresetGroup",
            "AnimaEasyMultiAngleGroup",
            "AnimaVariationBatchSampler",
            "AnimaFlexibleVariationBatchSampler",
            "AnimaSaveBatchZip",
        }
        for workflow in self.workflows:
            node_types = {node["type"] for node in workflow["nodes"]}
            self.assertTrue(node_types.isdisjoint(removed_nodes))

    def test_esrgan_workflows_embed_animesharp_download_metadata(self):
        for workflow in (
            self.hires_esrgan,
            self.two_character,
        ):
            with self.subTest(workflow=workflow.get("id")):
                loader = next(
                    node
                    for node in workflow["nodes"]
                    if node["type"] == "UpscaleModelLoader"
                )
                model = loader["properties"]["models"][0]
                self.assertEqual(model["name"], "4x-AnimeSharp.pth")
                self.assertEqual(model["directory"], "upscale_models")
                self.assertEqual(
                    model["url"],
                    "https://huggingface.co/Kim2091/AnimeSharp/resolve/"
                    "main/4x-AnimeSharp.pth",
                )

    def test_latent_workflow_queues_blank_line_scenes_without_esrgan(self):
        nodes = {node["id"]: node for node in self.hires_latent["nodes"]}
        node_types = {node["type"] for node in self.hires_latent["nodes"]}
        self.assertIn("AnimaPromptQueue", node_types)
        self.assertIn("AnimaPoseLoRASelect", node_types)
        self.assertIn("AnimaSaveQueueZip", node_types)
        self.assertIn("LatentUpscaleBy", node_types)
        self.assertNotIn("UpscaleModelLoader", node_types)
        self.assertNotIn("SaveImage", node_types)

        queue = nodes[15]
        self.assertEqual(queue["widgets_values"][1:4], ["1-500", 1, 500])
        self.assertIn("\n\n", queue["widgets_values"][0])

        sources = {
            (target_id, target_slot): (source_id, source_slot, link_type)
            for (
                _link_id,
                source_id,
                source_slot,
                target_id,
                target_slot,
                link_type,
            ) in self.hires_latent["links"]
        }
        self.assertEqual(sources[(4, 1)], (15, 0, "STRING"))
        self.assertEqual(sources[(7, 4)], (15, 1, "INT"))
        self.assertEqual(sources[(11, 4)], (15, 2, "INT"))
        self.assertEqual(sources[(13, 1)], (15, 3, "STRING"))
        self.assertEqual(sources[(13, 2)], (15, 4, "STRING"))

        for node_id, input_name in (
            (4, "text"),
            (7, "seed"),
            (11, "seed"),
        ):
            converted_input = nodes[node_id]["inputs"][-1]
            self.assertEqual(converted_input["name"], input_name)
            self.assertEqual(converted_input["widget"]["name"], input_name)

        zip_saver = nodes[13]
        self.assertEqual(
            [item["name"] for item in zip_saver["inputs"]],
            ["images", "file_stems", "archive_name"],
        )
        self.assertNotIn("widget", zip_saver["inputs"][1])
        self.assertNotIn("widget", zip_saver["inputs"][2])
        self.assertEqual(zip_saver["widgets_values"], [True])

    def test_latent_workflow_applies_selected_pose_lora_to_both_passes(self):
        nodes = {node["id"]: node for node in self.hires_latent["nodes"]}
        selectors = [
            node for node in self.hires_latent["nodes"]
            if node["type"] == "AnimaPoseLoRASelect"
        ]
        loaders = [
            node for node in self.hires_latent["nodes"]
            if node["type"] == "LoraLoaderModelOnly"
        ]
        self.assertEqual(len(selectors), 1)
        self.assertEqual(len(loaders), 2)

        selector = selectors[0]
        first_loader = next(node for node in loaders if "1st pass" in node["title"])
        second_loader = next(node for node in loaders if "2nd pass" in node["title"])
        self.assertTrue(selector["widgets_values"][0].startswith("anima_pose/"))
        self.assertEqual(selector["widgets_values"][1:], [0.8, 0.8])

        sources = {
            (target_id, target_slot): (source_id, source_slot, link_type)
            for (
                _link_id,
                source_id,
                source_slot,
                target_id,
                target_slot,
                link_type,
            ) in self.hires_latent["links"]
        }
        self.assertEqual(sources[(first_loader["id"], 0)], (1, 0, "MODEL"))
        self.assertEqual(sources[(second_loader["id"], 0)], (1, 0, "MODEL"))
        self.assertEqual(sources[(first_loader["id"], 1)], (selector["id"], 0, "*"))
        self.assertEqual(sources[(second_loader["id"], 1)], (selector["id"], 0, "*"))
        self.assertEqual(sources[(first_loader["id"], 2)], (selector["id"], 1, "FLOAT"))
        self.assertEqual(sources[(second_loader["id"], 2)], (selector["id"], 2, "FLOAT"))
        self.assertEqual(sources[(7, 0)], (first_loader["id"], 0, "MODEL"))
        self.assertEqual(sources[(11, 0)], (second_loader["id"], 0, "MODEL"))

    def test_two_character_workflow_separates_prompts_loras_and_masks(self):
        nodes = {node["id"]: node for node in self.two_character["nodes"]}
        node_types = [node["type"] for node in self.two_character["nodes"]]

        self.assertEqual(node_types.count("AnimaCharacterPairPrompt"), 1)
        self.assertEqual(node_types.count("AnimaTwoCharacterFreeMasks"), 1)
        self.assertNotIn("AnimaTwoCharacterMasks", node_types)
        self.assertEqual(node_types.count("CreateHookLoraModelOnly"), 2)
        self.assertEqual(node_types.count("ConditioningSetProperties"), 2)
        self.assertEqual(node_types.count("ConditioningCombine"), 1)
        self.assertEqual(node_types.count("ConditioningSetDefaultCombine"), 1)
        self.assertEqual(node_types.count("KSampler"), 2)
        self.assertNotIn("LoraLoaderModelOnly", node_types)
        self.assertNotIn("VAEEncodeForInpaint", node_types)

        selector = nodes[4]
        masks = nodes[5]
        hook_a = nodes[9]
        hook_b = nodes[10]
        regional_a = nodes[11]
        regional_b = nodes[12]
        shared_prompt = nodes[27]
        default_combine = nodes[28]
        first_sampler = nodes[16]
        second_sampler = nodes[23]

        self.assertIn("trigger:", selector["widgets_values"][1])
        self.assertIn("trigger:", selector["widgets_values"][4])
        self.assertEqual(
            masks["widgets_values"],
            [832, 1216, 26, 50, 48, 96, 74, 50, 48, 96, 6],
        )
        self.assertEqual(regional_a["widgets_values"], [1, "default"])
        self.assertEqual(regional_b["widgets_values"], [1, "default"])
        self.assertEqual(first_sampler["widgets_values"][-1], 1)
        self.assertEqual(second_sampler["widgets_values"][-1], 0.38)
        self.assertEqual(nodes[1]["widgets_values"][0], "waiANIMA_v10Base10.safetensors")

        sources = {
            (target_id, target_slot): (source_id, source_slot, link_type)
            for (
                _link_id,
                source_id,
                source_slot,
                target_id,
                target_slot,
                link_type,
            ) in self.two_character["links"]
        }
        self.assertEqual(sources[(4, 0)], (5, 3, "STRING"))
        self.assertEqual(sources[(4, 1)], (5, 4, "STRING"))
        self.assertEqual(sources[(6, 1)], (4, 0, "STRING"))
        self.assertEqual(sources[(7, 1)], (4, 1, "STRING"))
        self.assertEqual(sources[(hook_a["id"], 0)], (4, 2, "*"))
        self.assertEqual(sources[(hook_a["id"], 1)], (4, 3, "FLOAT"))
        self.assertEqual(sources[(hook_b["id"], 0)], (4, 4, "*"))
        self.assertEqual(sources[(hook_b["id"], 1)], (4, 5, "FLOAT"))
        self.assertEqual(sources[(regional_a["id"], 0)], (6, 0, "CONDITIONING"))
        self.assertEqual(sources[(regional_a["id"], 1)], (5, 0, "MASK"))
        self.assertEqual(sources[(regional_a["id"], 2)], (9, 0, "HOOKS"))
        self.assertEqual(sources[(regional_b["id"], 0)], (7, 0, "CONDITIONING"))
        self.assertEqual(sources[(regional_b["id"], 1)], (5, 1, "MASK"))
        self.assertEqual(sources[(regional_b["id"], 2)], (10, 0, "HOOKS"))
        self.assertEqual(sources[(13, 0)], (11, 0, "CONDITIONING"))
        self.assertEqual(sources[(13, 1)], (12, 0, "CONDITIONING"))
        self.assertEqual(sources[(shared_prompt["id"], 0)], (2, 0, "CLIP"))
        self.assertEqual(sources[(shared_prompt["id"], 1)], (4, 6, "STRING"))
        self.assertEqual(
            sources[(default_combine["id"], 0)],
            (13, 0, "CONDITIONING"),
        )
        self.assertEqual(
            sources[(default_combine["id"], 1)],
            (27, 0, "CONDITIONING"),
        )

        for sampler_id in (first_sampler["id"], second_sampler["id"]):
            self.assertEqual(sources[(sampler_id, 0)], (1, 0, "MODEL"))
            self.assertEqual(sources[(sampler_id, 1)], (28, 0, "CONDITIONING"))
            self.assertEqual(sources[(sampler_id, 2)], (8, 0, "CONDITIONING"))

    def assert_links_reference_existing_nodes_and_sockets(self, workflow):
        nodes = {node["id"]: node for node in workflow["nodes"]}
        link_ids = set()
        orders = [node["order"] for node in workflow["nodes"]]
        self.assertEqual(len(orders), len(set(orders)))

        for link_id, source_id, source_slot, target_id, target_slot, _type in (
            workflow["links"]
        ):
            self.assertNotIn(link_id, link_ids)
            link_ids.add(link_id)
            self.assertIn(source_id, nodes)
            self.assertIn(target_id, nodes)
            self.assertLess(source_slot, len(nodes[source_id]["outputs"]))
            self.assertLess(target_slot, len(nodes[target_id]["inputs"]))
            self.assertIn(link_id, nodes[source_id]["outputs"][source_slot]["links"])
            self.assertEqual(
                nodes[target_id]["inputs"][target_slot]["link"],
                link_id,
            )
            self.assertLess(nodes[source_id]["order"], nodes[target_id]["order"])


if __name__ == "__main__":
    unittest.main()
