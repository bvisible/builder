"""
Tests for AI Schemas Module
Tests for builder.ai.schemas
"""

import unittest
from pydantic import ValidationError
from builder.ai.schemas.block_schema import (
    FrappeBlock,
    FrappeStyles,
    PageStructure,
    SectionInfo,
    HeroContent,
    FeaturesContent,
    FeatureItem,
    TestimonialsContent,
    TestimonialItem,
    PricingContent,
    PricingTier,
    PricingFeature,
    CtaContent,
    StatsContent,
    StatItem,
    FaqContent,
    FaqItem,
    get_content_schema_for_section,
    SECTION_CONTENT_SCHEMAS,
)
from builder.ai.schemas.header_schema import (
    HeaderConfig,
    NavItem,
    HEADER_TYPE_DESCRIPTIONS,
)
from builder.ai.schemas.footer_schema import (
    FooterConfig,
    FooterColumn,
    FooterLink,
    SocialLinks,
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
        """Test block with styles"""
        block = FrappeBlock(
            blockId="test-block",
            element="section",
            baseStyles=FrappeStyles(padding="20px"),
            mobileStyles=FrappeStyles(padding="10px"),
        )
        self.assertEqual(block.blockId, "test-block")
        self.assertEqual(block.baseStyles.padding, "20px")
        self.assertEqual(block.mobileStyles.padding, "10px")

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
            baseStyles=FrappeStyles(color="red"),
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


class TestPageStructure(unittest.TestCase):
    """Tests for PageStructure schema"""

    def test_basic_structure(self):
        """Test creating a basic page structure"""
        structure = PageStructure(
            page_type="landing",
            sections=[
                SectionInfo(type="hero", title="Hero", priority=10),
                SectionInfo(type="features", title="Features", priority=8),
            ],
        )
        self.assertEqual(structure.page_type, "landing")
        self.assertEqual(len(structure.sections), 2)

    def test_get_sections_by_priority(self):
        """Test sorting sections by priority"""
        structure = PageStructure(
            page_type="landing",
            sections=[
                SectionInfo(type="cta", priority=5),
                SectionInfo(type="hero", priority=10),
                SectionInfo(type="features", priority=8),
            ],
        )
        sorted_sections = structure.get_sections_by_priority()
        self.assertEqual(sorted_sections[0].type, "hero")
        self.assertEqual(sorted_sections[1].type, "features")
        self.assertEqual(sorted_sections[2].type, "cta")


class TestHeroContent(unittest.TestCase):
    """Tests for HeroContent schema"""

    def test_minimal_hero(self):
        """Test creating minimal hero content"""
        content = HeroContent(
            headline="Welcome",
            subheadline="This is a test",
        )
        self.assertEqual(content.headline, "Welcome")
        self.assertEqual(content.primary_cta_text, "Get Started")  # default

    def test_hero_with_all_fields(self):
        """Test hero with all fields"""
        content = HeroContent(
            badge="New",
            headline="Welcome",
            subheadline="Test",
            primary_cta_text="Start",
            primary_cta_url="/start",
            secondary_cta_text="Learn More",
            secondary_cta_url="/learn",
            image_url="/hero.jpg",
            image_alt="Hero image",
        )
        self.assertEqual(content.badge, "New")
        self.assertEqual(content.secondary_cta_text, "Learn More")


class TestFeaturesContent(unittest.TestCase):
    """Tests for FeaturesContent schema"""

    def test_features_validation(self):
        """Test features list validation"""
        content = FeaturesContent(
            section_title="Features",
            features=[
                FeatureItem(icon="🚀", title="Fast", description="Very fast"),
                FeatureItem(icon="🔒", title="Secure", description="Very secure"),
                FeatureItem(icon="💡", title="Smart", description="Very smart"),
            ],
        )
        self.assertEqual(len(content.features), 3)

    def test_features_min_length(self):
        """Test that features must have at least 3 items"""
        with self.assertRaises(ValidationError):
            FeaturesContent(
                section_title="Features",
                features=[
                    FeatureItem(icon="🚀", title="Fast", description="Test"),
                ],
            )


class TestPricingContent(unittest.TestCase):
    """Tests for PricingContent schema"""

    def test_pricing_tiers(self):
        """Test pricing tiers"""
        content = PricingContent(
            section_title="Pricing",
            tiers=[
                PricingTier(
                    name="Starter",
                    description="For small teams",
                    price="$9",
                    features=[
                        PricingFeature(text="5 users"),
                        PricingFeature(text="10GB storage"),
                        PricingFeature(text="Email support", included=False),
                    ],
                ),
                PricingTier(
                    name="Pro",
                    description="For growing teams",
                    price="$29",
                    is_popular=True,
                    features=[
                        PricingFeature(text="Unlimited users"),
                        PricingFeature(text="100GB storage"),
                        PricingFeature(text="Priority support"),
                    ],
                ),
            ],
        )
        self.assertEqual(len(content.tiers), 2)
        self.assertTrue(content.tiers[1].is_popular)


class TestHeaderConfig(unittest.TestCase):
    """Tests for HeaderConfig schema"""

    def test_basic_header(self):
        """Test creating basic header config"""
        config = HeaderConfig(
            type="multi_page",
            layout="logo_left_menu_right",
            logo_type="text",
            logo_value="Brand",
            menu_items=[
                NavItem(label="Home", href="/"),
                NavItem(label="About", href="/about"),
            ],
        )
        self.assertEqual(config.type, "multi_page")
        self.assertEqual(len(config.menu_items), 2)

    def test_header_with_actions(self):
        """Test header with login/signup"""
        config = HeaderConfig(
            type="saas",
            show_login=True,
            show_signup=True,
            login_text="Sign In",
            signup_text="Get Started",
        )
        self.assertTrue(config.show_login)
        self.assertEqual(config.signup_text, "Get Started")


class TestFooterConfig(unittest.TestCase):
    """Tests for FooterConfig schema"""

    def test_basic_footer(self):
        """Test creating basic footer config"""
        config = FooterConfig(
            type="standard",
            layout="columns",
            company_name="Acme Inc",
        )
        self.assertEqual(config.type, "standard")

    def test_footer_with_social(self):
        """Test footer with social links"""
        config = FooterConfig(
            type="standard",
            show_social=True,
            social_links=SocialLinks(
                twitter="https://twitter.com/test",
                linkedin="https://linkedin.com/test",
            ),
        )
        links = config.social_links.get_active_links()
        self.assertIn("twitter", links)
        self.assertIn("linkedin", links)


class TestSectionContentSchemas(unittest.TestCase):
    """Tests for section content schema mapping"""

    def test_schema_mapping_exists(self):
        """Test that all expected section types have schemas"""
        expected = ["hero", "features", "testimonials", "pricing", "cta", "stats", "faq"]
        for section_type in expected:
            schema = get_content_schema_for_section(section_type)
            self.assertIsNotNone(schema, f"Missing schema for {section_type}")

    def test_get_content_schema(self):
        """Test getting content schema for section type"""
        hero_schema = get_content_schema_for_section("hero")
        self.assertEqual(hero_schema, HeroContent)

        features_schema = get_content_schema_for_section("features")
        self.assertEqual(features_schema, FeaturesContent)

    def test_unknown_section_returns_none(self):
        """Test that unknown section type returns None"""
        schema = get_content_schema_for_section("unknown")
        self.assertIsNone(schema)


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
        heights = SectionHeights()
        self.assertEqual(heights.hero_min_height, "90vh")
        self.assertEqual(heights.hero_min_height_mobile, "70vh")
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
        self.assertIn("TYPOGRAPHY", prompt)
        self.assertIn("FONTS", prompt)

    def test_to_prompt_section_contains_heights(self):
        """Test that to_prompt_section includes section heights"""
        brief = DesignBrief(
            section_heights=SectionHeights(hero_min_height="95vh"),
        )
        prompt = brief.to_prompt_section()
        self.assertIn("95vh", prompt)
        self.assertIn("SECTION HEIGHTS", prompt)

    def test_to_prompt_section_contains_paddings(self):
        """Test that to_prompt_section includes section paddings"""
        brief = DesignBrief()
        prompt = brief.to_prompt_section()
        self.assertIn("SECTION PADDINGS", prompt)
        self.assertIn("Hero", prompt)
        self.assertIn("Standard", prompt)

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
