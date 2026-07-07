import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
WORKFLOW_DIR = ROOT / "example_workflows"
HIRES_ESRGAN_WORKFLOW_PATH = WORKFLOW_DIR / "anima_hiresfix_esrgan_2pass.json"
HIRES_LATENT_WORKFLOW_PATH = WORKFLOW_DIR / "anima_hiresfix_latent_2pass.json"
ANGLE_360_WORKFLOW_PATH = WORKFLOW_DIR / "ANIMA_360_Angle_Control.json"


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hires_esrgan = cls.load(HIRES_ESRGAN_WORKFLOW_PATH)
        cls.hires_latent = cls.load(HIRES_LATENT_WORKFLOW_PATH)
        cls.angle_360 = cls.load(ANGLE_360_WORKFLOW_PATH)

    @staticmethod
    def load(path):
        return json.loads(path.read_text(encoding="utf-8"))

    def test_only_supported_example_workflows_remain(self):
        workflow_names = sorted(path.name for path in WORKFLOW_DIR.glob("*.json"))
        self.assertEqual(
            workflow_names,
            [
                "ANIMA_360_Angle_Control.json",
                "anima_hiresfix_esrgan_2pass.json",
                "anima_hiresfix_latent_2pass.json",
            ],
        )

    def test_all_workflow_links_reference_existing_nodes_and_sockets(self):
        for workflow in (self.hires_esrgan, self.hires_latent, self.angle_360):
            with self.subTest(workflow=workflow.get("id")):
                self.assert_links_reference_existing_nodes_and_sockets(workflow)

    def test_360_workflow_uses_custom_angle_control_and_reference_latent(self):
        node_types = {node["type"] for node in self.angle_360["nodes"]}
        self.assertIn("Anima360AngleControl", node_types)
        self.assertIn("AnimaApplyReferenceLatent", node_types)
        self.assertIn("LoraLoaderModelOnly", node_types)
        self.assertIn("KSampler", node_types)

        lora_names = [
            node["widgets_values"][0]
            for node in self.angle_360["nodes"]
            if node["type"] == "LoraLoaderModelOnly"
        ]
        self.assertEqual(lora_names, ["qwen_image_union_diffsynth_lora.safetensors"])

        angle_node = next(
            node for node in self.angle_360["nodes"] if node["type"] == "Anima360AngleControl"
        )
        self.assertEqual(angle_node["widgets_values"][1:5], [832, 1216, 45, 0])

        apply_node = next(
            node for node in self.angle_360["nodes"] if node["type"] == "AnimaApplyReferenceLatent"
        )
        apply_inputs = {item["name"]: item["link"] for item in apply_node["inputs"]}
        self.assertIsNotNone(apply_inputs["reference_latent"])

        links = {item[0]: item for item in self.angle_360["links"]}
        reference_source = links[apply_inputs["reference_latent"]][1]
        vae_encode = next(
            node for node in self.angle_360["nodes"] if node["type"] == "VAEEncode"
        )
        self.assertEqual(reference_source, vae_encode["id"])

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
        for workflow in (self.hires_esrgan, self.hires_latent):
            node_types = {node["type"] for node in workflow["nodes"]}
            self.assertTrue(node_types.isdisjoint(removed_nodes))

    def assert_links_reference_existing_nodes_and_sockets(self, workflow):
        nodes = {node["id"]: node for node in workflow["nodes"]}
        link_ids = set()

        for link_id, source_id, source_slot, target_id, target_slot, _type in (
            workflow["links"]
        ):
            self.assertNotIn(link_id, link_ids)
            link_ids.add(link_id)
            self.assertIn(source_id, nodes)
            self.assertIn(target_id, nodes)
            self.assertLess(source_slot, len(nodes[source_id]["outputs"]))
            self.assertLess(target_slot, len(nodes[target_id]["inputs"]))


if __name__ == "__main__":
    unittest.main()
