# //// Neoffice — added file (no upstream equivalent): tests of the page generator's layout sanitiser.
# //// builder/ai/** = the Neoffice AI site generator; frappe/builder ships no such module. First commit
# //// 2c44cd3e 2026-02-01.
"""
Tests for AI Site Generation
Tests for builder.ai.generators.page_generator

The webshop header/footer template tests, the header-schema defaults and the
HeaderGenerator navigation tests were removed: 95d9df5f ("creative AI
generation with full freedom", 2026-02-03) deleted ai/templates/webshop_*.py,
ai/schemas/header_schema.py and ai/generators/header_generator.py along with
the whole rigid template system. Header and footer are now managed by Website
Header Footer Config, and the AI writes sections itself. Those 20 tests could
only ever ImportError against the current code (CI, 2026-09-03).
"""

import unittest


class TestLayoutSanitizer(unittest.TestCase):
    """Tests for _sanitize_layout_styles — strips flex-only props when the
    block is display:grid, and grid-only props when the block is display:flex.
    """

    def _run(self, blocks):
        # Instantiate the generator without __init__ to avoid provider /
        # database setup — we only need the method under test.
        from builder.ai.generators.page_generator import PageGenerator
        gen = PageGenerator.__new__(PageGenerator)
        return gen._sanitize_layout_styles(blocks)

    def test_flex_block_drops_grid_props(self):
        blocks = [{
            "blockId": "b1",
            "element": "section",
            "baseStyles": {
                "display": "flex",
                "flexDirection": "row",
                "gap": "24px",
                "gridTemplateColumns": "repeat(4, 1fr)",
                "gridAutoRows": "200px",
            },
        }]
        out = self._run(blocks)[0]["baseStyles"]
        self.assertEqual(out["display"], "flex")
        self.assertEqual(out["flexDirection"], "row")
        self.assertEqual(out["gap"], "24px")
        self.assertNotIn("gridTemplateColumns", out)
        self.assertNotIn("gridAutoRows", out)

    def test_grid_block_drops_flex_props(self):
        blocks = [{
            "blockId": "b1",
            "element": "section",
            "baseStyles": {
                "display": "grid",
                "gridTemplateColumns": "repeat(3, 1fr)",
                "gap": "20px",
                "flexDirection": "row",
                "flexWrap": "wrap",
            },
        }]
        out = self._run(blocks)[0]["baseStyles"]
        self.assertEqual(out["display"], "grid")
        self.assertEqual(out["gridTemplateColumns"], "repeat(3, 1fr)")
        self.assertNotIn("flexDirection", out)
        self.assertNotIn("flexWrap", out)

    def test_mobile_styles_cleaned_using_base_display(self):
        # mobileStyles has no display but inherits display: flex from base.
        # The orphan gridTemplateColumns must be stripped.
        blocks = [{
            "blockId": "b1",
            "element": "div",
            "baseStyles": {"display": "flex", "flexDirection": "row"},
            "mobileStyles": {"gridTemplateColumns": "1fr"},
        }]
        out = self._run(blocks)[0]
        self.assertNotIn("gridTemplateColumns", out["mobileStyles"])

    def test_children_are_walked(self):
        blocks = [{
            "blockId": "parent",
            "element": "section",
            "baseStyles": {"display": "block"},
            "children": [{
                "blockId": "child",
                "element": "div",
                "baseStyles": {
                    "display": "grid",
                    "gridTemplateColumns": "1fr 1fr",
                    "flexWrap": "wrap",
                },
            }],
        }]
        out = self._run(blocks)[0]["children"][0]["baseStyles"]
        self.assertEqual(out["gridTemplateColumns"], "1fr 1fr")
        self.assertNotIn("flexWrap", out)

    def test_no_display_means_no_stripping(self):
        blocks = [{
            "blockId": "b1",
            "element": "p",
            "baseStyles": {"padding": "20px"},
        }]
        out = self._run(blocks)[0]["baseStyles"]
        self.assertEqual(out, {"padding": "20px"})


class TestHeroHeightFromBrief(unittest.TestCase):
    """The brief's hero height reaches the page through the code, not the prompt.

    ec1758f0 ("enable hero minHeight") stopped interpolating
    DesignBrief.section_heights into to_prompt_section and left the value to be
    applied here instead. These tests hold that half of the split; the other
    half is asserted in test_ai_schemas
    (test_to_prompt_section_suggests_a_hero_height_range_not_the_brief_value).
    """

    def _fix(self, block, brief):
        # Instantiate the generator without __init__ to avoid provider /
        # database setup - we only need the method under test.
        from builder.ai.generators.page_generator import PageGenerator

        gen = PageGenerator.__new__(PageGenerator)
        gen._fix_block_styles(block, brief)
        return block

    def _brief(self):
        from builder.ai.schemas.design_brief import DesignBrief, SectionHeights

        return DesignBrief(
            section_heights=SectionHeights(
                hero_min_height="95vh", hero_min_height_mobile="75vh"
            )
        )

    def test_hero_block_without_height_gets_the_brief_height(self):
        block = self._fix({"blockId": "hero-1", "element": "section"}, self._brief())
        self.assertEqual(block["baseStyles"]["minHeight"], "95vh")
        self.assertEqual(block["mobileStyles"]["minHeight"], "75vh")

    def test_height_chosen_by_the_ai_is_kept(self):
        block = self._fix(
            {
                "blockId": "hero-1",
                "element": "section",
                "baseStyles": {"minHeight": "60vh"},
            },
            self._brief(),
        )
        self.assertEqual(block["baseStyles"]["minHeight"], "60vh")

    def test_non_hero_block_is_left_alone(self):
        block = self._fix({"blockId": "features-1", "element": "section"}, self._brief())
        self.assertNotIn("minHeight", block.get("baseStyles", {}))


if __name__ == "__main__":
    unittest.main()
