import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
WORKFLOW_DIR = ROOT / "example_workflows"
HIRES_ESRGAN_WORKFLOW_PATH = WORKFLOW_DIR / "anima_hiresfix_esrgan_2pass.json"
HIRES_LATENT_WORKFLOW_PATH = WORKFLOW_DIR / "anima_hiresfix_latent_2pass.json"


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hires_esrgan = cls.load(HIRES_ESRGAN_WORKFLOW_PATH)
        cls.hires_latent = cls.load(HIRES_LATENT_WORKFLOW_PATH)

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
            ],
        )

    def test_all_workflow_links_reference_existing_nodes_and_sockets(self):
        for workflow in (self.hires_esrgan, self.hires_latent):
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
