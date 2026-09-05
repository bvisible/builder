# //// Neoffice - added file (no upstream equivalent). Covers builder/ai/**, the
# //// Neoffice AI site-generation subsystem (first commit 71e8284d, 2026-02-03);
# //// frappe/builder upstream ships neither the module nor these tests.
"""
Tests for AI Validators Module
Tests for builder.ai.validators.BlockValidator

Rewritten 2026-09-04. The previous suite was written against a reject-and-report
validator: it read validator.errors / .warnings, called get_report(), passed
strict=True, and expected warnings for kebab-case styles, an <img> without alt,
an <a> without href and lorem ipsum. None of that survives 95d9df5f ("creative
AI generation with full freedom" - "Simplified block validation (no auto-fix)"),
which turned BlockValidator into an auto-repairer: it FIXES what an LLM gets
wrong instead of rejecting a whole generation over it. AutoFixer and the
validate_block / auto_fix_block helpers were deleted outright. Every one of
those 14 tests could only ImportError or AttributeError against the current
code (CI, 2026-09-03), so they are replaced here by tests of what the validator
actually guarantees today: the legacy bool API, the repair path, and the three
mechanical safety-net rules.
"""

import unittest

from builder.ai.validators import BlockValidator


class TestBlockValidatorLegacyValidate(unittest.TestCase):
    """validate() / validate_blocks() - the bool API kept for backward compat."""

    def setUp(self):
        self.validator = BlockValidator()

    def test_valid_block(self):
        block = {
            "blockId": "test-block",
            "element": "div",
            "baseStyles": {"padding": "20px", "backgroundColor": "#fff"},
        }
        self.assertTrue(self.validator.validate(block))

    def test_missing_block_id(self):
        self.assertFalse(self.validator.validate({"element": "div"}))

    def test_missing_element(self):
        self.assertFalse(self.validator.validate({"blockId": "b1"}))

    def test_invalid_element(self):
        self.assertFalse(self.validator.validate({"blockId": "b1", "element": "marquee"}))

    def test_svg_elements_are_valid(self):
        # The LLM writes inline SVG icons; those tags are in VALID_ELEMENTS.
        self.assertTrue(self.validator.validate({"blockId": "i1", "element": "svg"}))

    def test_an_invalid_child_fails_the_parent(self):
        block = {
            "blockId": "parent",
            "element": "section",
            "children": [{"blockId": "child", "element": "marquee"}],
        }
        self.assertFalse(self.validator.validate(block))

    def test_validate_blocks_rejects_an_empty_list(self):
        self.assertFalse(self.validator.validate_blocks([]))

    def test_duplicate_block_ids_are_not_a_validation_error(self):
        """Duplicate ids are repaired, not rejected."""
        # Changed: the old suite asserted validate() returned False here. Under a
        # validator that auto-repairs, refusing the whole page over a repeated id
        # would throw away a good generation - so the duplicate is renamed instead
        # (see test_duplicate_block_ids_are_made_unique).
        block = {
            "blockId": "same",
            "element": "div",
            "children": [{"blockId": "same", "element": "div"}],
        }
        self.assertTrue(self.validator.validate(block))


class TestBlockValidatorRepair(unittest.TestCase):
    """repair_block() / validate_and_repair() - the path generation actually uses."""

    def setUp(self):
        self.validator = BlockValidator()

    def test_missing_block_id_is_generated(self):
        block = self.validator.repair_block({"element": "section"})
        self.assertTrue(block["blockId"].startswith("section-auto-"))

    def test_missing_element_defaults_to_div(self):
        block = self.validator.repair_block({"blockId": "b1"})
        self.assertEqual(block["element"], "div")

    def test_invalid_element_becomes_div(self):
        block = self.validator.repair_block({"blockId": "b1", "element": "marquee"})
        self.assertEqual(block["element"], "div")

    def test_children_that_are_not_a_list_are_dropped(self):
        block = self.validator.repair_block(
            {"blockId": "b1", "element": "div", "children": "oops"}
        )
        self.assertEqual(block["children"], [])

    def test_children_are_repaired_recursively(self):
        block = self.validator.repair_block(
            {"blockId": "parent", "element": "section", "children": [{"element": "marquee"}]}
        )
        child = block["children"][0]
        self.assertEqual(child["element"], "div")
        self.assertIn("blockId", child)

    def test_repair_block_refuses_a_non_dict(self):
        self.assertIsNone(self.validator.repair_block("not a block"))

    def test_duplicate_block_ids_are_made_unique(self):
        blocks = self.validator.validate_and_repair(
            [
                {"blockId": "same", "element": "div"},
                {"blockId": "same", "element": "div"},
            ]
        )
        self.assertEqual(len(blocks), 2)
        self.assertNotEqual(blocks[0]["blockId"], blocks[1]["blockId"])
        self.assertTrue(blocks[1]["blockId"].startswith("same-"))

    def test_non_list_input_returns_empty(self):
        self.assertEqual(self.validator.validate_and_repair({"blockId": "b1"}), [])

    def test_empty_input_returns_empty(self):
        self.assertEqual(self.validator.validate_and_repair([]), [])


class TestBlockValidatorMechanicalRules(unittest.TestCase):
    """The three safety nets behind the prompts: prompts steer, these guarantee."""

    def setUp(self):
        self.validator = BlockValidator()

    # R1 - a root flex section with no direction and wide children stacks
    def test_root_flex_without_direction_is_forced_to_column(self):
        block = {
            "blockId": "root",
            "element": "section",
            "baseStyles": {"display": "flex"},
            "children": [
                {"blockId": "a", "element": "section"},
                {"blockId": "b", "element": "section"},
            ],
        }
        out = self.validator.validate_and_repair([block])[0]
        self.assertEqual(out["baseStyles"]["flexDirection"], "column")

    def test_root_flex_with_an_explicit_direction_is_left_alone(self):
        block = {
            "blockId": "root",
            "element": "section",
            "baseStyles": {"display": "flex", "flexDirection": "row"},
            "children": [
                {"blockId": "a", "element": "section"},
                {"blockId": "b", "element": "section"},
            ],
        }
        out = self.validator.validate_and_repair([block])[0]
        self.assertEqual(out["baseStyles"]["flexDirection"], "row")

    def test_narrow_children_side_by_side_are_left_alone(self):
        block = {
            "blockId": "root",
            "element": "section",
            "baseStyles": {"display": "flex"},
            "children": [
                {"blockId": "a", "element": "div", "baseStyles": {"width": "33%"}},
                {"blockId": "b", "element": "div", "baseStyles": {"width": "33%"}},
            ],
        }
        out = self.validator.validate_and_repair([block])[0]
        self.assertNotIn("flexDirection", out["baseStyles"])

    # R2 - oversized absolute display text goes behind the copy, faded
    def test_ghost_text_is_pushed_behind_and_faded(self):
        block = {
            "blockId": "root",
            "element": "section",
            "children": [
                {
                    "blockId": "ghost",
                    "element": "span",
                    "innerHTML": "DESIGN",
                    "baseStyles": {"position": "absolute", "fontSize": "180px"},
                }
            ],
        }
        ghost = self.validator.validate_and_repair([block])[0]["children"][0]
        self.assertEqual(ghost["baseStyles"]["opacity"], "0.08")
        self.assertEqual(ghost["baseStyles"]["zIndex"], "-1")
        self.assertEqual(ghost["baseStyles"]["pointerEvents"], "none")

    def test_rem_font_sizes_count_as_huge(self):
        block = {
            "blockId": "ghost",
            "element": "span",
            "innerHTML": "DESIGN",
            "baseStyles": {"position": "absolute", "fontSize": "12rem"},
        }
        out = self.validator.validate_and_repair([block])[0]
        self.assertEqual(out["baseStyles"]["opacity"], "0.08")

    def test_ordinary_absolute_text_is_left_alone(self):
        block = {
            "blockId": "badge",
            "element": "span",
            "innerHTML": "New",
            "baseStyles": {"position": "absolute", "fontSize": "14px"},
        }
        out = self.validator.validate_and_repair([block])[0]
        self.assertNotIn("opacity", out["baseStyles"])
        self.assertNotIn("zIndex", out["baseStyles"])

    # R3 - placehold.co prints its ?text= across the image
    def test_large_placeholder_loses_its_text(self):
        block = {
            "blockId": "img",
            "element": "img",
            "attributes": {"src": "https://placehold.co/1200x600/eeeeee/333333?text=Our+Team"},
        }
        out = self.validator.validate_and_repair([block])[0]
        src = out["attributes"]["src"]
        self.assertNotIn("text=", src)
        # and the printed dimensions are hidden by painting them in the bg color
        self.assertEqual(src, "https://placehold.co/1200x600/eeeeee/eeeeee")

    def test_avatar_sized_placeholder_keeps_its_initials(self):
        url = "https://placehold.co/80x80/eeeeee/333333?text=JD"
        block = {"blockId": "img", "element": "img", "attributes": {"src": url}}
        out = self.validator.validate_and_repair([block])[0]
        self.assertEqual(out["attributes"]["src"], url)


if __name__ == "__main__":
    unittest.main()
