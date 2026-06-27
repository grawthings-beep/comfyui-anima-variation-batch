import unittest

from variation import (
    MULTI_ANGLE_PRESETS,
    add_variation_group,
    add_variation_group_options,
    build_group_variations,
    build_variations,
    clean_angle_prompt,
    clean_angle_prompts,
    easy_multi_angle_prompts,
    join_prompt,
    parse_lines,
    parse_options,
    parse_easy_multi_angle_params,
    selected_multi_angle_presets,
)


SHOTS = """\
close-up portrait
upper body shot
cowboy shot
full body shot
"""

EXPRESSIONS = """\
gentle smile
laughing
surprised expression
embarrassed expression
"""


class VariationTests(unittest.TestCase):
    def test_parse_lines_removes_comments_blanks_and_duplicates(self):
        value = "one\n\n# ignored\n two \none\n"
        self.assertEqual(parse_lines(value), ["one", "two"])

    def test_join_prompt_normalizes_commas(self):
        self.assertEqual(
            join_prompt("masterpiece,", ", close-up", " smile "),
            "masterpiece, close-up, smile",
        )

    def test_parse_options_accepts_commas_newlines_comments_and_duplicates(self):
        value = "from above, from side,\n# note\nfrom below, From Side"
        self.assertEqual(
            parse_options(value),
            ["from above", "from side", "from below"],
        )

    def test_preparsed_options_preserve_commas_inside_angle_prompt(self):
        groups = add_variation_group_options(
            None,
            "Angle",
            [
                "front view, eye level, medium shot",
                "right side view, high angle, close-up",
            ],
        )

        self.assertEqual(len(groups[0].options), 2)
        self.assertEqual(
            groups[0].options[0],
            "front view, eye level, medium shot",
        )

    def test_clean_angle_prompt_strips_metadata_and_qwen_trigger(self):
        self.assertEqual(
            clean_angle_prompt(
                "<sks> front view, eye level, medium shot "
                "(horizontal: 0, vertical: 0, zoom: 5.0)"
            ),
            "front view, eye level, medium shot",
        )

    def test_clean_angle_prompts_accepts_json_string_list(self):
        self.assertEqual(
            clean_angle_prompts(
                '["front view (horizontal: 0)", "front view (horizontal: 0)", '
                '"left side view (horizontal: 270)"]'
            ),
            ["front view", "left side view"],
        )

    def test_easy_multi_angle_params_create_anima_friendly_prompts(self):
        prompts = easy_multi_angle_prompts(
            '[{"rotate":145,"vertical":36,"zoom":0,'
            '"add_angle_prompt":true}]'
        )

        self.assertEqual(
            prompts,
            ["back-right view, high angle, extreme wide shot"],
        )

    def test_easy_multi_angle_params_are_clamped(self):
        self.assertEqual(
            parse_easy_multi_angle_params(
                '[{"rotate":999,"vertical":-999,"zoom":99,'
                '"add_angle_prompt":false}]'
            ),
            [
                {
                    "rotate": 360,
                    "vertical": -90,
                    "zoom": 10.0,
                    "add_angle_prompt": False,
                }
            ],
        )

    def test_multi_angle_presets_expose_twenty_toggle_options(self):
        keys = [preset["key"] for preset in MULTI_ANGLE_PRESETS]
        self.assertEqual(len(keys), 20)
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn("front", keys)
        self.assertIn("front_left_high", keys)

    def test_selected_multi_angle_presets_use_enabled_toggles_only(self):
        params = selected_multi_angle_presets(
            {
                "front": True,
                "front_high": False,
                "right_low": True,
            }
        )

        self.assertEqual(
            params,
            [
                {
                    "rotate": 0,
                    "vertical": 0,
                    "zoom": 5,
                    "add_angle_prompt": True,
                },
                {
                    "rotate": 90,
                    "vertical": -25,
                    "zoom": 5,
                    "add_angle_prompt": True,
                },
            ],
        )

    def test_selected_multi_angle_presets_require_one_toggle(self):
        with self.assertRaisesRegex(ValueError, "select at least one"):
            selected_multi_angle_presets({})

    def test_four_variations_are_deterministic_and_unique(self):
        first = build_variations(
            "masterpiece, 1girl",
            SHOTS,
            EXPRESSIONS,
            4,
            12345,
        )
        second = build_variations(
            "masterpiece, 1girl",
            SHOTS,
            EXPRESSIONS,
            4,
            12345,
        )

        self.assertEqual(first, second)
        self.assertEqual(len(first), 4)
        self.assertEqual(len({(item.shot, item.expression) for item in first}), 4)
        self.assertEqual(len({item.seed for item in first}), 4)

    def test_count_cannot_exceed_combinations(self):
        with self.assertRaisesRegex(ValueError, "only 1"):
            build_variations("base", "shot", "face", 2, 0)

    def test_flexible_groups_pick_one_option_from_every_category(self):
        groups = add_variation_group(
            None,
            "Angle",
            "from above, from side, from below",
        )
        groups = add_variation_group(
            groups,
            "Expression",
            "smile, angry, surprised",
        )
        groups = add_variation_group(
            groups,
            "Pose",
            "standing, sitting, looking back",
        )

        first = build_group_variations("masterpiece, 1girl", groups, 8, 123)
        second = build_group_variations("masterpiece, 1girl", groups, 8, 123)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 8)
        self.assertEqual(len({item.seed for item in first}), 8)
        self.assertTrue(
            all(
                [name for name, _value in item.selections]
                == ["Angle", "Expression", "Pose"]
                for item in first
            )
        )
        self.assertTrue(
            all(
                all(value in item.prompt for _name, value in item.selections)
                for item in first
            )
        )

    def test_each_category_exhausts_its_options_before_repeating(self):
        groups = add_variation_group(
            None,
            "Angle",
            "from above, from side, from below",
        )
        groups = add_variation_group(
            groups,
            "Expression",
            "smile, angry",
        )

        variations = build_group_variations("base", groups, 8, 44)
        angles = [item.selections[0][1] for item in variations]
        expressions = [item.selections[1][1] for item in variations]

        self.assertEqual(
            set(angles[:3]),
            {"from above", "from side", "from below"},
        )
        self.assertEqual(
            set(angles[3:6]),
            {"from above", "from side", "from below"},
        )
        self.assertEqual(len(set(angles[6:])), 2)
        self.assertNotEqual(angles[2], angles[3])
        self.assertNotEqual(angles[5], angles[6])
        for start in range(0, 8, 2):
            self.assertEqual(set(expressions[start:start + 2]), {"smile", "angry"})
        for boundary in (2, 4, 6):
            self.assertNotEqual(expressions[boundary - 1], expressions[boundary])

    def test_single_option_can_repeat_after_it_is_exhausted(self):
        groups = add_variation_group(None, "Angle", "eye level")
        variations = build_group_variations("base", groups, 4, 5)
        self.assertEqual(
            [item.selections[0][1] for item in variations],
            ["eye level"] * 4,
        )

    def test_flexible_groups_can_be_extended_without_a_fixed_limit(self):
        groups = None
        for index in range(80):
            groups = add_variation_group(
                groups,
                f"Category {index}",
                f"option {index}a, option {index}b",
            )

        variations = build_group_variations("base", groups, 4, 1)
        self.assertEqual(len(variations[0].selections), 80)

    def test_duplicate_category_name_is_rejected(self):
        groups = add_variation_group(None, "Angle", "from above")
        with self.assertRaisesRegex(ValueError, "duplicate variation category"):
            add_variation_group(groups, "angle", "from below")

    def test_flexible_count_can_exceed_total_combinations(self):
        groups = add_variation_group(None, "Angle", "from above, from below")
        variations = build_group_variations("base", groups, 5, 0)
        angles = [item.selections[0][1] for item in variations]
        self.assertEqual(set(angles[:2]), {"from above", "from below"})
        self.assertEqual(set(angles[2:4]), {"from above", "from below"})


if __name__ == "__main__":
    unittest.main()
