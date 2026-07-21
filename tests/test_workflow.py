import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
WORKFLOW_DIR = ROOT / "example_workflows"
HIRES_ESRGAN_WORKFLOW_PATH = WORKFLOW_DIR / "anima_hiresfix_esrgan_2pass.json"
POSE_DEPTH_WORKFLOW_PATH = WORKFLOW_DIR / "anima_hiresfix_esrgan_pose_depth.json"
HIRES_LATENT_WORKFLOW_PATH = WORKFLOW_DIR / "anima_hiresfix_latent_2pass.json"


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hires_esrgan = cls.load(HIRES_ESRGAN_WORKFLOW_PATH)
        cls.pose_depth = cls.load(POSE_DEPTH_WORKFLOW_PATH)
        cls.hires_latent = cls.load(HIRES_LATENT_WORKFLOW_PATH)
        cls.workflows = (
            cls.hires_esrgan,
            cls.pose_depth,
            cls.hires_latent,
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
                "anima_hiresfix_esrgan_pose_depth.json",
                "anima_hiresfix_latent_2pass.json",
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

    def test_pose_depth_workflow_uses_native_lllite_in_first_pass(self):
        nodes = {node["id"]: node for node in self.pose_depth["nodes"]}
        node_types = [node["type"] for node in self.pose_depth["nodes"]]
        self.assertEqual(node_types.count("ModelPatchLoader"), 2)
        self.assertEqual(node_types.count("AnimaLLLiteApply"), 2)
        self.assertIn("DWPreprocessor", node_types)
        self.assertIn("DepthAnythingV2Preprocessor", node_types)

        self.assertEqual(
            nodes[20]["widgets_values"],
            ["anima-lllite-pose-1.safetensors"],
        )
        self.assertEqual(
            nodes[24]["widgets_values"],
            ["anima-lllite-depth-1.safetensors"],
        )
        self.assertEqual(nodes[21]["widgets_values"], [1.0, 0.0, 0.8])
        self.assertEqual(nodes[25]["widgets_values"], [0.65, 0.0, 0.7])

        sources = {
            (target_id, target_slot): (source_id, source_slot, link_type)
            for (
                _link_id,
                source_id,
                source_slot,
                target_id,
                target_slot,
                link_type,
            ) in self.pose_depth["links"]
        }
        self.assertEqual(sources[(21, 0)], (1, 0, "MODEL"))
        self.assertEqual(sources[(21, 1)], (20, 0, "MODEL_PATCH"))
        self.assertEqual(sources[(21, 2)], (19, 0, "IMAGE"))
        self.assertEqual(sources[(25, 0)], (21, 0, "MODEL"))
        self.assertEqual(sources[(25, 1)], (24, 0, "MODEL_PATCH"))
        self.assertEqual(sources[(25, 2)], (23, 0, "IMAGE"))
        self.assertEqual(sources[(7, 0)], (25, 0, "MODEL"))
        self.assertEqual(sources[(14, 0)], (1, 0, "MODEL"))

    def test_pose_depth_workflow_embeds_download_metadata(self):
        nodes = {node["id"]: node for node in self.pose_depth["nodes"]}
        pose_model = nodes[20]["properties"]["models"][0]
        depth_model = nodes[24]["properties"]["models"][0]
        self.assertEqual(pose_model["directory"], "model_patches")
        self.assertEqual(depth_model["directory"], "model_patches")
        self.assertTrue(pose_model["url"].endswith("anima-lllite-pose-1.safetensors"))
        self.assertTrue(depth_model["url"].endswith("anima-lllite-depth-1.safetensors"))

    def test_esrgan_workflows_embed_animesharp_download_metadata(self):
        for workflow in (self.hires_esrgan, self.pose_depth):
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
            self.assertLess(nodes[source_id]["order"], nodes[target_id]["order"])


if __name__ == "__main__":
    unittest.main()
