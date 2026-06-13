import unittest

from variation import (
    add_variation_group,
    build_group_variations,
    build_variations,
    join_prompt,
    parse_lines,
    parse_options,
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
        self.assertEqual(len({item.selections for item in first}), 8)
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

    def test_flexible_count_cannot_exceed_combinations(self):
        groups = add_variation_group(None, "Angle", "from above, from below")
        with self.assertRaisesRegex(ValueError, "only 2"):
            build_group_variations("base", groups, 3, 0)


if __name__ == "__main__":
    unittest.main()
