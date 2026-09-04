#//// Neoffice - added file (no upstream equivalent). Covers builder/ai/**, the
#//// Neoffice AI site-generation subsystem (first commit 71e8284d, 2026-02-03);
#//// frappe/builder upstream ships neither the module nor these tests.
"""
Tests for AI Schemas Module
Tests for builder.ai.schemas

Only the schemas that still exist are covered: FrappeStyles / FrappeBlock
(block_schema) and DesignBrief with its TypographyScale / SectionHeights
(design_brief). The page-structure, section-content, header and footer
schemas were removed by the February 2026 refactor ("creative AI generation
with full freedom") and their tests went with them (CI, 2026-09-03).
"""

import unittest
from pydantic import ValidationError
from builder.ai.schemas.block_schema import (
    FrappeBlock,
    FrappeStyles,
)
from builder.ai.schemas.design_brief import (
    DesignBrief,
    TypographyScale,
    SectionHeights,
)

class TestFrappeStyles(unittest.TestCase):
    """Tests for FrappeStyles schema"""

    def test_basic_styles(self):
        """Test basic style properties"""
        styles = FrappeStyles(
            display="flex",
            padding="20px",
            backgroundColor="#fff",
        )
        self.assertEqual(styles.display, "flex")
        self.assertEqual(styles.padding, "20px")

    def test_to_dict_excludes_none(self):
        """Test that to_dict excludes None values"""
        styles = FrappeStyles(display="flex", padding=None)
        result = styles.to_dict()
        self.assertIn("display", result)
        self.assertNotIn("padding", result)

    def test_extra_properties_allowed(self):
        """Test that extra CSS properties are allowed"""
        styles = FrappeStyles(
            display="flex",
            customProperty="value",  # Extra property
        )
        result = styles.to_dict()
        self.assertIn("customProperty", result)


class TestFrappeBlock(unittest.TestCase):
    """Tests for FrappeBlock schema"""

    def test_minimal_block(self):
        """Test creating a minimal block"""
        block = FrappeBlock(element="div")
        self.assertEqual(block.element, "div")
        self.assertIsNotNone(block.blockId)

    def test_block_with_styles(self):
        """A block carries its styles as plain camelCase dicts."""
        # Changed: baseStyles / mobileStyles were typed FrappeStyles until 95d9df5f
        # ("creative AI generation with full freedom"), which retyped them to
        # Optional[dict] so the model can never reject a CSS property the AI
        # invents. FrappeStyles survives as the documented vocabulary (see
        # TestFrappeStyles), not as a gate on what a block may carry.
        block = FrappeBlock(
            blockId="test-block",
            element="section",
            baseStyles={"padding": "20px"},
            mobileStyles={"padding": "10px"},
        )
        self.assertEqual(block.blockId, "test-block")
        self.assertEqual(block.baseStyles["padding"], "20px")
        self.assertEqual(block.mobileStyles["padding"], "10px")

    def test_block_styles_reject_a_model(self):
        """A FrappeStyles instance is not a style dict and is refused."""
        # Pins the dict contract above: the failure mode this replaces was a
        # FrappeStyles passed where a dict is expected, which pydantic rejects.
        with self.assertRaises(ValidationError):
            FrappeBlock(element="section", baseStyles=FrappeStyles(padding="20px"))

    def test_block_with_children(self):
        """Test block with nested children"""
        child = FrappeBlock(blockId="child", element="div")
        parent = FrappeBlock(
            blockId="parent",
            element="section",
            children=[child],
        )
        self.assertEqual(len(parent.children), 1)
        self.assertEqual(parent.children[0].blockId, "child")

    def test_to_dict(self):
        """Test to_dict conversion"""
        block = FrappeBlock(
            blockId="test",
            element="div",
            innerHTML="Hello",
            baseStyles={"color": "red"},  # dict, not FrappeStyles - see test_block_with_styles
        )
        result = block.to_dict()
        self.assertEqual(result["blockId"], "test")
        self.assertEqual(result["element"], "div")
        self.assertEqual(result["innerHTML"], "Hello")
        self.assertEqual(result["baseStyles"]["color"], "red")

    def test_block_id_auto_generation(self):
        """Test that blockId is auto-generated if not provided"""
        block = FrappeBlock(element="div")
        self.assertTrue(block.blockId.startswith("block-"))


class TestTypographyScale(unittest.TestCase):
    """Tests for TypographyScale schema"""

    def test_default_values(self):
        """Test default typography values"""
        typo = TypographyScale()
        self.assertEqual(typo.h1_size, "48px")
        self.assertEqual(typo.h1_size_mobile, "32px")
        self.assertEqual(typo.h1_weight, "700")
        self.assertEqual(typo.body_size, "16px")
        self.assertEqual(typo.body_line_height, "1.6")

    def test_custom_values(self):
        """Test custom typography values"""
        typo = TypographyScale(
            h1_size="56px",
            h1_weight="900",
            body_size="18px",
        )
        self.assertEqual(typo.h1_size, "56px")
        self.assertEqual(typo.h1_weight, "900")
        self.assertEqual(typo.body_size, "18px")


class TestSectionHeights(unittest.TestCase):
    """Tests for SectionHeights schema"""

    def test_default_values(self):
        """Test default section height values"""
        # Changed: hero heights defaulted to "90vh" / "70vh" until ec1758f0
        # ("enable hero minHeight"), which made them Optional and None -
        # "Suggested section heights - AI has freedom to adapt". Unset now means
        # "no opinion", which is what lets the AI size its own hero; a brief that
        # does carry a height still wins (see TestHeroHeightFromBrief in
        # test_ai_generation).
        heights = SectionHeights()
        self.assertIsNone(heights.hero_min_height)
        self.assertIsNone(heights.hero_min_height_mobile)
        self.assertEqual(heights.standard_min_height, "auto")

    def test_custom_values(self):
        """Test custom section height values"""
        heights = SectionHeights(
            hero_min_height="100vh",
            hero_min_height_mobile="80vh",
        )
        self.assertEqual(heights.hero_min_height, "100vh")
        self.assertEqual(heights.hero_min_height_mobile, "80vh")


class TestDesignBrief(unittest.TestCase):
    """Tests for DesignBrief schema"""

    def test_default_brief(self):
        """Test creating a default design brief"""
        brief = DesignBrief()
        self.assertEqual(brief.site_tone, "professional")
        self.assertEqual(brief.heading_font, "Inter")
        self.assertEqual(brief.body_font, "Inter")
        self.assertIsNotNone(brief.typography)
        self.assertIsNotNone(brief.section_heights)
        self.assertIsNotNone(brief.section_paddings)

    def test_custom_fonts(self):
        """Test brief with custom fonts"""
        brief = DesignBrief(
            heading_font="Poppins",
            body_font="Roboto",
        )
        self.assertEqual(brief.heading_font, "Poppins")
        self.assertEqual(brief.body_font, "Roboto")

    def test_custom_typography(self):
        """Test brief with custom typography scale"""
        typo = TypographyScale(h1_size="56px", h1_weight="800")
        brief = DesignBrief(typography=typo)
        self.assertEqual(brief.typography.h1_size, "56px")
        self.assertEqual(brief.typography.h1_weight, "800")

    def test_custom_section_heights(self):
        """Test brief with custom section heights"""
        heights = SectionHeights(hero_min_height="95vh")
        brief = DesignBrief(section_heights=heights)
        self.assertEqual(brief.section_heights.hero_min_height, "95vh")

    def test_section_paddings_dict(self):
        """Test section paddings dictionary"""
        brief = DesignBrief(
            section_paddings={
                "hero": "120px 24px",
                "standard": "100px 24px",
                "compact": "80px 24px",
                "cta": "60px 24px",
            }
        )
        self.assertEqual(brief.section_paddings["hero"], "120px 24px")
        self.assertEqual(brief.section_paddings["cta"], "60px 24px")

    def test_to_prompt_section_contains_typography(self):
        """Test that to_prompt_section includes typography info"""
        brief = DesignBrief(
            heading_font="Poppins",
            typography=TypographyScale(h1_size="52px"),
        )
        prompt = brief.to_prompt_section()
        self.assertIn("52px", prompt)
        self.assertIn("Poppins", prompt)
        # Changed: the headings read "### TYPOGRAPHY (MANDATORY - USE THESE EXACT
        # VALUES)" and "### FONTS (MANDATORY ...)" until ec1758f0 turned the brief
        # from a set of mandates into guidelines. Sizes became suggestions; the
        # font pair stayed binding, because two pages set in different typefaces
        # do not read as one site.
        self.assertIn("### Typography suggestions", prompt)
        self.assertIn("### Fonts (CONTRACT", prompt)

    def test_to_prompt_section_suggests_a_hero_height_range_not_the_brief_value(self):
        """The prompt recommends a hero height range; the brief's own value is not asked of the AI."""
        # Changed: the prompt used to interpolate the brief under "### SECTION
        # HEIGHTS (MANDATORY)". ec1758f0 ("enable hero minHeight") replaced that
        # table with a fixed 70vh-90vh recommendation and, per its own message,
        # removed "contradictory instructions about minHeight" - the LLM was being
        # ordered to use an exact height that the code then overwrote anyway.
        # The brief's value did not stop mattering, it moved out of the prompt and
        # into code: page_generator._fix_block_styles writes
        # brief.section_heights.hero_min_height onto any hero block that came back
        # without one. assertNotIn pins that split so a re-interpolation is caught.
        brief = DesignBrief(
            section_heights=SectionHeights(hero_min_height="95vh"),
        )
        prompt = brief.to_prompt_section()
        self.assertIn("### Section Heights", prompt)
        self.assertIn('use minHeight "70vh" to "90vh"', prompt)
        self.assertNotIn("95vh", prompt)

    def test_to_prompt_section_contains_paddings(self):
        """The brief's own paddings reach the prompt."""
        # Changed: the heading read "### SECTION PADDINGS BY TYPE" until ec1758f0
        # retitled it "### Section Paddings (suggestions)" and dropped the compact
        # and cta rows (the AI paces its own sections now). Asserting the values
        # rather than the bare words "Hero" / "Standard", which matched anywhere.
        brief = DesignBrief(section_paddings={"hero": "120px 24px", "standard": "90px 24px"})
        prompt = brief.to_prompt_section()
        self.assertIn("### Section Paddings", prompt)
        self.assertIn("| Hero | ~120px 24px |", prompt)
        self.assertIn("| Standard | ~90px 24px |", prompt)

    def test_get_border_radius(self):
        """Test border radius getter"""
        brief = DesignBrief(border_radius_style="rounded")
        self.assertEqual(brief.get_border_radius(), "12px")

        brief2 = DesignBrief(border_radius_style="none")
        self.assertEqual(brief2.get_border_radius(), "0")

        brief3 = DesignBrief(border_radius_style="pill")
        self.assertEqual(brief3.get_border_radius(), "9999px")

    def test_to_dict(self):
        """Test to_dict conversion"""
        brief = DesignBrief(heading_font="Montserrat")
        result = brief.to_dict()
        self.assertEqual(result["heading_font"], "Montserrat")
        self.assertIn("typography", result)
        self.assertIn("section_heights", result)


if __name__ == "__main__":
    unittest.main()
