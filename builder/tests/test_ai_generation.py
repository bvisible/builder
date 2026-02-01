"""
Tests for AI Site Generation
Tests for builder.api generate_site and webshop templates
"""

import unittest
import json


class TestWebshopHeaders(unittest.TestCase):
    """Tests for webshop header templates"""

    def test_webshop_header_variations_exist(self):
        """Test that all webshop header variations are defined"""
        from builder.ai.templates.webshop_headers import WEBSHOP_HEADER_VARIATIONS

        expected_variations = [
            "webshop_standard",
            "webshop_centered",
            "webshop_minimal",
            "webshop_mega",
            "webshop_transparent",
            "webshop_split",
        ]

        for variation in expected_variations:
            self.assertIn(variation, WEBSHOP_HEADER_VARIATIONS)
            self.assertIn("name", WEBSHOP_HEADER_VARIATIONS[variation])
            self.assertIn("description", WEBSHOP_HEADER_VARIATIONS[variation])

    def test_build_webshop_header_standard(self):
        """Test building standard webshop header"""
        from builder.ai.templates.webshop_headers import build_webshop_header_standard

        header = build_webshop_header_standard()

        self.assertEqual(header["blockId"], "ws-header")
        self.assertEqual(header["element"], "header")
        self.assertIn("children", header)
        self.assertEqual(len(header["children"]), 3)  # logo, nav, actions

        # Check logo
        logo = header["children"][0]
        self.assertEqual(logo["blockId"], "ws-header-logo")

    def test_build_webshop_header_centered(self):
        """Test building centered webshop header"""
        from builder.ai.templates.webshop_headers import build_webshop_header_centered

        header = build_webshop_header_centered()

        self.assertEqual(header["blockId"], "ws-header")
        self.assertIn("gridTemplateColumns", header["baseStyles"])

    def test_build_webshop_header_minimal(self):
        """Test building minimal webshop header"""
        from builder.ai.templates.webshop_headers import build_webshop_header_minimal

        header = build_webshop_header_minimal()

        self.assertEqual(header["blockId"], "ws-header")
        # Minimal should have fewer nav items
        self.assertIn("children", header)

    def test_build_webshop_header_factory(self):
        """Test the factory function for webshop headers"""
        from builder.ai.templates.webshop_headers import build_webshop_header

        for variation in ["webshop_standard", "webshop_centered", "webshop_minimal"]:
            header = build_webshop_header(variation=variation)
            self.assertEqual(header["blockId"], "ws-header")
            self.assertEqual(header["element"], "header")

    def test_webshop_header_has_cart_icon(self):
        """Test that webshop headers include cart icon"""
        from builder.ai.templates.webshop_headers import build_webshop_header_standard

        header = build_webshop_header_standard()

        # Find cart in nested structure
        def find_block_by_id(block, target_id):
            if isinstance(block, dict):
                if block.get("blockId") == target_id:
                    return block
                for child in block.get("children", []):
                    result = find_block_by_id(child, target_id)
                    if result:
                        return result
            return None

        cart = find_block_by_id(header, "ws-action-cart")
        self.assertIsNotNone(cart, "Cart icon should be present in webshop header")

    def test_webshop_header_default_logo(self):
        """Test that default logo path is /files/logo-default.png"""
        from builder.ai.templates.webshop_headers import build_webshop_header_standard

        header = build_webshop_header_standard()

        # Find logo image
        def find_logo_src(block):
            if isinstance(block, dict):
                attrs = block.get("attributes", {})
                if attrs.get("src"):
                    return attrs["src"]
                for child in block.get("children", []):
                    result = find_logo_src(child)
                    if result:
                        return result
            return None

        logo_src = find_logo_src(header)
        self.assertEqual(logo_src, "/files/logo-default.png")


class TestWebshopFooters(unittest.TestCase):
    """Tests for webshop footer templates"""

    def test_webshop_footer_variations_exist(self):
        """Test that all webshop footer variations are defined"""
        from builder.ai.templates.webshop_footers import WEBSHOP_FOOTER_VARIATIONS

        expected_variations = [
            "webshop_standard",
            "webshop_simple",
            "webshop_centered",
            "webshop_dark",
            "webshop_minimal",
            "webshop_newsletter",
        ]

        for variation in expected_variations:
            self.assertIn(variation, WEBSHOP_FOOTER_VARIATIONS)

    def test_build_webshop_footer_standard(self):
        """Test building standard webshop footer"""
        from builder.ai.templates.webshop_footers import build_webshop_footer_standard

        footer = build_webshop_footer_standard(company_name="Test Company")

        self.assertEqual(footer["blockId"], "ws-footer")
        self.assertEqual(footer["element"], "footer")

    def test_build_webshop_footer_dark(self):
        """Test building dark webshop footer"""
        from builder.ai.templates.webshop_footers import build_webshop_footer_dark

        footer = build_webshop_footer_dark(company_name="Test Company")

        self.assertEqual(footer["blockId"], "ws-footer-dark")
        # Should have dark background
        self.assertEqual(footer["baseStyles"]["backgroundColor"], "#111827")

    def test_build_webshop_footer_factory(self):
        """Test the factory function for webshop footers"""
        from builder.ai.templates.webshop_footers import build_webshop_footer

        for variation in ["webshop_standard", "webshop_simple", "webshop_dark"]:
            footer = build_webshop_footer(variation=variation, company_name="Test")
            self.assertEqual(footer["element"], "footer")


class TestHeaderSchemaDefaults(unittest.TestCase):
    """Tests for header schema default values"""

    def test_default_logo_is_image(self):
        """Test that default logo type is image"""
        from builder.ai.schemas.header_schema import HeaderConfig

        config = HeaderConfig()
        self.assertEqual(config.logo_type, "image")
        self.assertEqual(config.logo_value, "/files/logo-default.png")

    def test_single_page_uses_anchors(self):
        """Test that single-page config uses anchor links"""
        from builder.ai.schemas.header_schema import HeaderConfig

        config = HeaderConfig.for_single_page(sections=["Home", "Features", "About", "Contact"])

        # Check that menu items use anchors
        for item in config.menu_items:
            self.assertTrue(
                item.href.startswith("#"),
                f"Single-page menu item should use anchor: {item.href}"
            )

    def test_ecommerce_has_cart(self):
        """Test that ecommerce config enables cart"""
        from builder.ai.schemas.header_schema import HeaderConfig

        config = HeaderConfig.for_ecommerce()

        self.assertTrue(config.show_cart)
        self.assertTrue(config.show_wishlist)
        self.assertTrue(config.show_search)


class TestNavigationLinks(unittest.TestCase):
    """Tests for navigation link generation"""

    def test_single_page_default_config_uses_anchors(self):
        """Test that default config for single-page uses anchors"""
        from builder.ai.generators.header_generator import HeaderGenerator

        generator = HeaderGenerator.__new__(HeaderGenerator)
        config = generator._get_default_config("single_page", ["Home", "Features", "About"])

        for item in config.menu_items:
            self.assertTrue(
                item.href.startswith("#"),
                f"Single-page should use anchor links: {item.href}"
            )

    def test_multi_page_default_config_uses_urls(self):
        """Test that default config for multi-page uses URLs"""
        from builder.ai.generators.header_generator import HeaderGenerator

        generator = HeaderGenerator.__new__(HeaderGenerator)
        config = generator._get_default_config("multi_page", ["Home", "About", "Contact"])

        # Home should be "/"
        home_item = next(i for i in config.menu_items if i.label == "Home")
        self.assertEqual(home_item.href, "/")

        # Other pages should be URLs
        about_item = next(i for i in config.menu_items if i.label == "About")
        self.assertEqual(about_item.href, "/about")


class TestBlockStructure(unittest.TestCase):
    """Tests for generated block structure validity"""

    def test_header_has_required_fields(self):
        """Test that generated headers have required Frappe Builder fields"""
        from builder.ai.templates.webshop_headers import build_webshop_header

        header = build_webshop_header("webshop_standard")

        required_fields = ["blockId", "element", "baseStyles"]
        for field in required_fields:
            self.assertIn(field, header, f"Header missing required field: {field}")

    def test_footer_has_required_fields(self):
        """Test that generated footers have required Frappe Builder fields"""
        from builder.ai.templates.webshop_footers import build_webshop_footer

        footer = build_webshop_footer("webshop_standard")

        required_fields = ["blockId", "element", "baseStyles"]
        for field in required_fields:
            self.assertIn(field, footer, f"Footer missing required field: {field}")

    def test_blocks_are_json_serializable(self):
        """Test that all generated blocks can be serialized to JSON"""
        from builder.ai.templates.webshop_headers import build_webshop_header
        from builder.ai.templates.webshop_footers import build_webshop_footer

        header = build_webshop_header("webshop_standard")
        footer = build_webshop_footer("webshop_standard")

        # Should not raise
        json.dumps(header)
        json.dumps(footer)

    def test_css_properties_are_camelcase(self):
        """Test that CSS properties use camelCase (Frappe Builder requirement)"""
        from builder.ai.templates.webshop_headers import build_webshop_header

        header = build_webshop_header("webshop_standard")

        def check_styles(block):
            if isinstance(block, dict):
                for style_key in ["baseStyles", "mobileStyles"]:
                    styles = block.get(style_key, {})
                    for prop in styles.keys():
                        self.assertNotIn(
                            "-", prop,
                            f"CSS property should be camelCase, not kebab-case: {prop}"
                        )
                for child in block.get("children", []):
                    check_styles(child)

        check_styles(header)


if __name__ == "__main__":
    unittest.main()
