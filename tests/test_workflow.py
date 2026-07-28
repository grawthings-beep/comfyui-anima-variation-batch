import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
WORKFLOW_DIR = ROOT / "example_workflows"
HIRES_ESRGAN_WORKFLOW_PATH = WORKFLOW_DIR / "anima_hiresfix_esrgan_2pass.json"
HIRES_LATENT_WORKFLOW_PATH = WORKFLOW_DIR / "anima_hiresfix_latent_2pass.json"
INPAINT_WORKFLOW_PATH = (
    WORKFLOW_DIR / "anima_two_character_inpaint_hiresfix.json"
)


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hires_esrgan = cls.load(HIRES_ESRGAN_WORKFLOW_PATH)
        cls.hires_latent = cls.load(HIRES_LATENT_WORKFLOW_PATH)
        cls.inpaint = cls.load(INPAINT_WORKFLOW_PATH)
        cls.workflows = (
            cls.hires_esrgan,
            cls.hires_latent,
            cls.inpaint,
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
                "anima_two_character_inpaint_hiresfix.json",
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
            self.inpaint,
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

    def test_inpaint_workflow_is_mask_editor_based_and_isolates_loras(self):
        nodes = {node["id"]: node for node in self.inpaint["nodes"]}
        node_types = [node["type"] for node in self.inpaint["nodes"]]

        self.assertEqual(node_types.count("AnimaCharacterLoRASelect"), 2)
        self.assertEqual(node_types.count("LoraLoaderModelOnly"), 3)
        self.assertEqual(node_types.count("KSampler"), 3)
        self.assertEqual(node_types.count("LoadImage"), 1)
        self.assertEqual(node_types.count("GrowMask"), 1)
        self.assertEqual(node_types.count("VAEEncodeForInpaint"), 1)
        self.assertEqual(node_types.count("ImageCompositeMasked"), 1)
        self.assertEqual(node_types.count("ImageScale"), 1)

        retired_types = {
            "AnimaCharacterPairPrompt",
            "AnimaTwoCharacterMasks",
            "AnimaTwoCharacterFreeMasks",
            "CreateHookLoraModelOnly",
            "ConditioningSetProperties",
            "ConditioningSetDefaultCombine",
        }
        self.assertTrue(set(node_types).isdisjoint(retired_types))

        turbo = nodes[5]
        selector_a = nodes[6]
        selector_b = nodes[7]
        loader_a = nodes[8]
        loader_b = nodes[9]
        base_sampler = nodes[14]
        inpaint_sampler = nodes[20]
        hires_sampler = nodes[27]

        self.assertEqual(selector_a["widgets_values"], ["Kotobuki Hisako", 0.8])
        self.assertEqual(
            selector_b["widgets_values"],
            ["Michinoku Komaro", 0.9],
        )
        self.assertEqual(nodes[13]["widgets_values"], [768, 1024, 1])
        self.assertIn("k0t0h1s4k0", nodes[10]["widgets_values"][0])
        self.assertIn("m1ch1n0kuk0m4r0", nodes[10]["widgets_values"][0])
        self.assertIn(
            "Redraw Character B inside the painted mask",
            nodes[11]["widgets_values"][0],
        )
        self.assertEqual(
            turbo["widgets_values"],
            ["anima-turbo-lora-v0.2.safetensors", 1.0],
        )
        self.assertEqual(
            base_sampler["widgets_values"][2:],
            [12, 1.5, "euler", "simple", 1.0],
        )
        self.assertEqual(
            inpaint_sampler["widgets_values"][2:],
            [12, 1.5, "euler", "simple", 0.82],
        )
        self.assertEqual(
            hires_sampler["widgets_values"][2:],
            [12, 1.5, "euler", "simple", 0.32],
        )
        self.assertEqual(
            nodes[25]["widgets_values"],
            ["lanczos", 1160, 1536, "disabled"],
        )
        self.assertEqual(nodes[16]["mode"], 0)
        self.assertEqual(nodes[29]["mode"], 2)

        sources = {
            (target_id, target_slot): (source_id, source_slot, link_type)
            for (
                _link_id,
                source_id,
                source_slot,
                target_id,
                target_slot,
                link_type,
            ) in self.inpaint["links"]
        }

        self.assertEqual(sources[(turbo["id"], 0)], (2, 0, "MODEL"))
        for loader, selector in ((loader_a, selector_a), (loader_b, selector_b)):
            self.assertEqual(sources[(loader["id"], 0)], (turbo["id"], 0, "MODEL"))
            self.assertEqual(
                sources[(loader["id"], 1)],
                (selector["id"], 0, "*"),
            )
            self.assertEqual(
                sources[(loader["id"], 2)],
                (selector["id"], 1, "FLOAT"),
            )

        self.assertEqual(sources[(base_sampler["id"], 0)], (loader_a["id"], 0, "MODEL"))
        self.assertEqual(
            sources[(inpaint_sampler["id"], 0)],
            (loader_b["id"], 0, "MODEL"),
        )
        self.assertEqual(
            sources[(hires_sampler["id"], 0)],
            (turbo["id"], 0, "MODEL"),
        )
        self.assertEqual(
            sources[(hires_sampler["id"], 1)],
            (10, 0, "CONDITIONING"),
        )

        self.assertEqual(sources[(18, 0)], (17, 1, "MASK"))
        self.assertEqual(sources[(19, 0)], (17, 0, "IMAGE"))
        self.assertEqual(sources[(19, 2)], (18, 0, "MASK"))
        self.assertEqual(sources[(22, 0)], (17, 0, "IMAGE"))
        self.assertEqual(sources[(22, 1)], (21, 0, "IMAGE"))
        self.assertEqual(sources[(22, 5)], (18, 0, "MASK"))

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
