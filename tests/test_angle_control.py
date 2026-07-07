import unittest

from angle_control import (
    build_angle_prompt,
    build_full_prompt,
    describe_yaw,
    render_angle_guide,
)


class AngleControlTests(unittest.TestCase):
    def test_yaw_descriptions_cover_full_turn(self):
        self.assertEqual(describe_yaw(0), "front view")
        self.assertEqual(describe_yaw(45), "front-right three-quarter view")
        self.assertEqual(describe_yaw(90), "right profile view")
        self.assertEqual(describe_yaw(180), "back view")
        self.assertEqual(describe_yaw(270), "left profile view")
        self.assertEqual(describe_yaw(360), "front view")

    def test_angle_prompt_includes_exact_yaw(self):
        prompt = build_angle_prompt(137, 32, 5.5)
        self.assertIn("back-right three-quarter view", prompt)
        self.assertIn("high-angle view", prompt)
        self.assertIn("camera yaw 137 degrees", prompt)
        self.assertIn("OpenPose control reference", prompt)

    def test_full_prompt_can_skip_angle_terms(self):
        self.assertEqual(
            build_full_prompt("masterpiece, 1girl", 90, 0, 5, False),
            "masterpiece, 1girl",
        )

    def test_rendered_guide_has_expected_shape_and_range(self):
        image = render_angle_guide(320, 512, 45, 10, 0, 5, line_thickness=4)
        self.assertEqual(image.size, (320, 512))
        self.assertEqual(image.mode, "RGB")
        self.assertGreater(sum(image.tobytes()), 0)
        colors = image.getcolors(maxcolors=1000000)
        self.assertIsNotNone(colors)
        self.assertTrue(any(color[0] != color[1] for _count, color in colors))

    def test_yaw_changes_rendered_control_image(self):
        front = render_angle_guide(320, 512, 0, 0, 0, 5, line_thickness=4)
        side = render_angle_guide(320, 512, 90, 0, 0, 5, line_thickness=4)
        diff = sum(abs(a - b) for a, b in zip(front.tobytes(), side.tobytes()))
        self.assertGreater(diff, 100)


if __name__ == "__main__":
    unittest.main()
