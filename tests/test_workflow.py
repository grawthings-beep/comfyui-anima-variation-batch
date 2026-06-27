import json
import unittest
from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).parents[1]
    / "example_workflows"
    / "anima_variation_batch_workflow.json"
)
EASY_MULTIANGLE_WORKFLOW_PATH = (
    Path(__file__).parents[1]
    / "example_workflows"
    / "anima_easy_multiangle_batch_workflow.json"
)
ANIMA_EASY_MULTIANGLE_WORKFLOW_PATH = (
    Path(__file__).parents[1]
    / "example_workflows"
    / "ANIMA_EasyMultiAngle.json"
)
ANIMA_CONTROL_CANNY_WORKFLOW_PATH = (
    Path(__file__).parents[1]
    / "example_workflows"
    / "ANIMA_Control_Canny.json"
)


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
        cls.easy_multiangle_workflow = json.loads(
            EASY_MULTIANGLE_WORKFLOW_PATH.read_text(encoding="utf-8")
        )
        cls.anima_easy_multiangle_workflow = json.loads(
            ANIMA_EASY_MULTIANGLE_WORKFLOW_PATH.read_text(encoding="utf-8")
        )
        cls.anima_control_canny_workflow = json.loads(
            ANIMA_CONTROL_CANNY_WORKFLOW_PATH.read_text(encoding="utf-8")
        )

    def test_custom_node_is_present(self):
        node_types = {node["type"] for node in self.workflow["nodes"]}
        self.assertIn("AnimaFlexibleVariationBatchSampler", node_types)
        self.assertIn("AnimaVariationGroup", node_types)
        self.assertIn("AnimaSaveBatchZip", node_types)

    def test_node_orders_are_unique(self):
        orders = [node["order"] for node in self.workflow["nodes"]]
        self.assertEqual(len(orders), len(set(orders)))

    def test_example_has_angle_expression_pose_and_composition_groups(self):
        groups = [
            node
            for node in self.workflow["nodes"]
            if node["type"] == "AnimaVariationGroup"
        ]
        self.assertGreaterEqual(len(groups), 4)
        category_names = [node["widgets_values"][0] for node in groups]
        self.assertEqual(
            category_names[:4],
            ["Angle", "Expression", "Pose", "Composition"],
        )

    def test_links_reference_existing_nodes_and_sockets(self):
        self.assert_links_reference_existing_nodes_and_sockets(self.workflow)

    def test_easy_multiangle_links_reference_existing_nodes_and_sockets(self):
        self.assert_links_reference_existing_nodes_and_sockets(
            self.easy_multiangle_workflow
        )

    def test_control_canny_links_reference_existing_nodes_and_sockets(self):
        self.assert_links_reference_existing_nodes_and_sockets(
            self.anima_control_canny_workflow
        )

    def test_easy_multiangle_example_uses_preset_group_node(self):
        node_types = {node["type"] for node in self.easy_multiangle_workflow["nodes"]}
        self.assertIn("AnimaMultiAnglePresetGroup", node_types)
        self.assertNotIn("AnimaMultiAngle", node_types)
        self.assertNotIn("AnimaEasyMultiAngleGroup", node_types)
        self.assertNotIn("easy multiAngle", node_types)

        preset_group = next(
            node
            for node in self.easy_multiangle_workflow["nodes"]
            if node["type"] == "AnimaMultiAnglePresetGroup"
        )
        self.assertEqual(preset_group["widgets_values"][0], "Angle")
        self.assertEqual(len(preset_group["widgets_values"]), 21)
        self.assertGreaterEqual(sum(preset_group["widgets_values"][1:]), 4)

    def test_named_anima_easy_multiangle_workflow_is_self_contained(self):
        node_types = {
            node["type"] for node in self.anima_easy_multiangle_workflow["nodes"]
        }
        self.assertIn("AnimaMultiAnglePresetGroup", node_types)
        self.assertNotIn("AnimaMultiAngle", node_types)
        self.assertNotIn("AnimaEasyMultiAngleGroup", node_types)
        self.assertNotIn("easy multiAngle", node_types)
        self.assertNotIn("easy positive", node_types)
        self.assertNotIn("easy negative", node_types)
        self.assertNotIn("Power Lora Loader (rgthree)", node_types)

    def test_control_canny_workflow_uses_reference_latent_control(self):
        workflow = self.anima_control_canny_workflow
        node_types = {node["type"] for node in workflow["nodes"]}

        self.assertIn("LoadImage", node_types)
        self.assertIn("ImageScaleToTotalPixels", node_types)
        self.assertIn("Canny", node_types)
        self.assertIn("VAEEncode", node_types)
        self.assertIn("ModelSamplingAuraFlow", node_types)
        self.assertIn("AnimaFlexibleVariationBatchSampler", node_types)

        lora_names = [
            node["widgets_values"][0]
            for node in workflow["nodes"]
            if node["type"] == "LoraLoaderModelOnly"
        ]
        self.assertIn("qwen_image_union_diffsynth_lora.safetensors", lora_names)
        self.assertIn("anima-turbo-lora-v0.2.safetensors", lora_names)

        unet_loader = next(
            node for node in workflow["nodes"] if node["type"] == "UNETLoader"
        )
        self.assertEqual(
            unet_loader["widgets_values"][0],
            "waiANIMA_v10Base10.safetensors",
        )

        sampler = next(
            node
            for node in workflow["nodes"]
            if node["type"] == "AnimaFlexibleVariationBatchSampler"
        )
        sampler_input_links = {
            item["name"]: item["link"] for item in sampler["inputs"]
        }
        self.assertIsNotNone(sampler_input_links["latent_image"])
        self.assertIsNotNone(sampler_input_links["reference_latent"])

        links = {item[0]: item for item in workflow["links"]}
        latent_link = links[sampler_input_links["latent_image"]]
        reference_link = links[sampler_input_links["reference_latent"]]
        self.assertEqual(latent_link[1:3], reference_link[1:3])

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

    def test_example_uses_only_turbo_lora(self):
        lora_nodes = [
            node
            for node in self.workflow["nodes"]
            if node["type"] == "LoraLoaderModelOnly"
        ]
        self.assertEqual(len(lora_nodes), 1)
        self.assertIn("turbo", lora_nodes[0]["widgets_values"][0].lower())

    def test_prompt_report_is_connected_to_zip_saver(self):
        sampler = next(
            node
            for node in self.workflow["nodes"]
            if node["type"] == "AnimaFlexibleVariationBatchSampler"
        )
        saver = next(
            node
            for node in self.workflow["nodes"]
            if node["type"] == "AnimaSaveBatchZip"
        )
        report_links = sampler["outputs"][1]["links"]
        self.assertEqual(len(report_links), 1)
        link = next(
            item
            for item in self.workflow["links"]
            if item[0] == report_links[0]
        )
        self.assertEqual(link[3:5], [saver["id"], 1])
        self.assertIs(saver["widgets_values"][1], True)


if __name__ == "__main__":
    unittest.main()
