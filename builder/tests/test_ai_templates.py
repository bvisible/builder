"""
Tests for AI Templates Module
Tests for builder.ai.templates
"""

import unittest
from builder.ai.templates import (
    HEADER_TEMPLATES,
    FOOTER_TEMPLATES,
    SECTION_TEMPLATES,
    COMPONENT_TEMPLATES,
    get_header_template,
    get_footer_template,
    get_section_template,
    get_component_template,
    build_section_from_content,
)
from builder.ai.schemas.block_schema import (
    HeroContent,
    FeaturesContent,
    FeatureItem,
    CtaContent,
    StatsContent,
    StatItem,
)


class TestHeaderTemplates(unittest.TestCase):
    """Tests for header templates"""

    def test_templates_exist(self):
        """Test that header templates are defined"""
        self.assertIn("standard", HEADER_TEMPLATES)
        self.assertIsInstance(HEADER_TEMPLATES, dict)

    def test_get_header_template(self):
        """Test getting header template by name"""
        template = get_header_template("standard")
        self.assertIsNotNone(template)
        self.assertIn("blockId", template)
        self.assertEqual(template["element"], "header")


class TestFooterTemplates(unittest.TestCase):
    """Tests for footer templates"""

    def test_templates_exist(self):
        """Test that footer templates are defined"""
        self.assertIn("columns", FOOTER_TEMPLATES)
        self.assertIsInstance(FOOTER_TEMPLATES, dict)

    def test_get_footer_template(self):
        """Test getting footer template by name"""
        template = get_footer_template("columns")
        self.assertIsNotNone(template)
        self.assertIn("blockId", template)
        self.assertEqual(template["element"], "footer")


class TestSectionTemplates(unittest.TestCase):
    """Tests for section templates"""

    def test_common_sections_exist(self):
        """Test that common section templates exist"""
        expected_sections = [
            "hero_centered",
            "hero_split",
            "features_grid",
            "testimonials",
            "pricing",
            "cta",
            "faq",
            "stats",
        ]
        for section in expected_sections:
            self.assertIn(section, SECTION_TEMPLATES, f"Missing section: {section}")

    def test_section_structure(self):
        """Test that section templates have required structure"""
        for name, section in SECTION_TEMPLATES.items():
            self.assertIn("description", section, f"{name} missing description")
            self.assertIn("structure", section, f"{name} missing structure")
            structure = section["structure"]
            self.assertIn("blockId", structure, f"{name} structure missing blockId")
            self.assertIn("element", structure, f"{name} structure missing element")

    def test_get_section_template(self):
        """Test getting section template by type"""
        template = get_section_template("hero_centered")
        self.assertIsNotNone(template)
        self.assertIn("blockId", template)


class TestComponentTemplates(unittest.TestCase):
    """Tests for component templates"""

    def test_common_components_exist(self):
        """Test that common component templates exist"""
        expected = ["feature_card", "testimonial_card", "pricing_card", "stat_item", "faq_item"]
        for component in expected:
            self.assertIn(component, COMPONENT_TEMPLATES, f"Missing component: {component}")

    def test_get_component_template(self):
        """Test getting component template by type"""
        template = get_component_template("feature_card")
        self.assertIsNotNone(template)
        self.assertIn("blockId", template)


class TestBuildSectionFromContent(unittest.TestCase):
    """Tests for build_section_from_content function"""

    def test_build_hero_section(self):
        """Test building hero section from content"""
        content = HeroContent(
            headline="Test Headline",
            subheadline="Test subheadline text",
            primary_cta_text="Get Started",
            primary_cta_url="/start",
        )
        section = build_section_from_content("hero", content)
        self.assertIsNotNone(section)
        self.assertEqual(section["element"], "section")
        self.assertIn("children", section)

    def test_build_hero_with_badge(self):
        """Test hero section with badge"""
        content = HeroContent(
            badge="New Feature",
            headline="Test Headline",
            subheadline="Test subheadline",
        )
        section = build_section_from_content("hero_centered", content)
        self.assertIsNotNone(section)
        # Should have badge in the structure

    def test_build_features_section(self):
        """Test building features section from content"""
        content = FeaturesContent(
            section_title="Our Features",
            section_description="Check out what we offer",
            features=[
                FeatureItem(icon="🚀", title="Fast", description="Very fast performance"),
                FeatureItem(icon="🔒", title="Secure", description="Enterprise security"),
                FeatureItem(icon="💡", title="Smart", description="AI-powered insights"),
            ]
        )
        section = build_section_from_content("features", content)
        self.assertIsNotNone(section)
        self.assertEqual(section["element"], "section")

    def test_build_cta_section(self):
        """Test building CTA section from content"""
        content = CtaContent(
            headline="Ready to start?",
            description="Join thousands of happy customers",
            button_text="Sign Up Free",
            button_url="/signup",
        )
        section = build_section_from_content("cta", content)
        self.assertIsNotNone(section)

    def test_build_stats_section(self):
        """Test building stats section from content"""
        content = StatsContent(
            stats=[
                StatItem(number="10K+", label="Users"),
                StatItem(number="99%", label="Uptime"),
                StatItem(number="24/7", label="Support"),
            ]
        )
        section = build_section_from_content("stats", content)
        self.assertIsNotNone(section)

    def test_unknown_section_returns_none(self):
        """Test that unknown section type returns None"""
        section = build_section_from_content("unknown_type", None)
        self.assertIsNone(section)

    def test_section_has_valid_structure(self):
        """Test that built sections have valid Frappe Builder structure"""
        content = HeroContent(
            headline="Test",
            subheadline="Test sub",
        )
        section = build_section_from_content("hero", content)

        # Check required fields
        self.assertIn("blockId", section)
        self.assertIn("element", section)
        self.assertIn("baseStyles", section)

        # Check styles are camelCase
        for key in section.get("baseStyles", {}).keys():
            self.assertNotIn("-", key, f"Style key should be camelCase: {key}")


class TestTemplateIntegrity(unittest.TestCase):
    """Tests for template structural integrity"""

    def test_all_templates_have_block_ids(self):
        """Test that all templates have blockId"""
        for name, template in SECTION_TEMPLATES.items():
            structure = template.get("structure", {})
            self.assertIn("blockId", structure, f"{name} missing blockId")

    def test_all_templates_have_valid_elements(self):
        """Test that all templates use valid HTML elements"""
        valid_elements = {
            "div", "section", "article", "aside", "main", "header", "footer", "nav",
            "h1", "h2", "h3", "h4", "h5", "h6", "p", "span", "a", "button", "img",
            "ul", "ol", "li", "form", "input", "textarea"
        }
        for name, template in SECTION_TEMPLATES.items():
            structure = template.get("structure", {})
            element = structure.get("element")
            self.assertIn(element, valid_elements, f"{name} has invalid element: {element}")

    def test_children_are_lists(self):
        """Test that children fields are always lists"""
        def check_children(block, path=""):
            if "children" in block:
                self.assertIsInstance(
                    block["children"],
                    list,
                    f"children should be list at {path}"
                )
                for i, child in enumerate(block["children"]):
                    if isinstance(child, dict) and "slot" not in child:
                        check_children(child, f"{path}.children[{i}]")

        for name, template in SECTION_TEMPLATES.items():
            structure = template.get("structure", {})
            check_children(structure, name)


if __name__ == "__main__":
    unittest.main()
