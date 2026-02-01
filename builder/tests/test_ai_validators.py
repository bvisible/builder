"""
Tests for AI Validators Module
Tests for builder.ai.validators
"""

import unittest
from builder.ai.validators import (
    BlockValidator,
    AutoFixer,
    ValidationError,
    validate_block,
    auto_fix_block,
)


class TestBlockValidator(unittest.TestCase):
    """Tests for BlockValidator class"""

    def setUp(self):
        self.validator = BlockValidator()

    def test_valid_block(self):
        """Test validation of a valid block"""
        block = {
            "blockId": "test-block",
            "element": "div",
            "baseStyles": {
                "padding": "20px",
                "backgroundColor": "#fff",
            },
            "children": []
        }
        self.assertTrue(self.validator.validate(block))
        self.assertEqual(len(self.validator.errors), 0)

    def test_missing_block_id(self):
        """Test validation with missing blockId"""
        block = {"element": "div"}
        self.validator.validate(block)
        # Should have warning, not error
        self.assertTrue(len(self.validator.warnings) > 0)

    def test_invalid_element(self):
        """Test validation with invalid element"""
        block = {
            "blockId": "test",
            "element": "invalid-element",
        }
        self.assertFalse(self.validator.validate(block))
        self.assertTrue(len(self.validator.errors) > 0)

    def test_duplicate_block_ids(self):
        """Test validation catches duplicate blockIds"""
        block = {
            "blockId": "duplicate",
            "element": "div",
            "children": [
                {"blockId": "duplicate", "element": "span"}
            ]
        }
        self.assertFalse(self.validator.validate(block))
        self.assertTrue(any("Duplicate" in e.message for e in self.validator.errors))

    def test_kebab_case_warning(self):
        """Test that kebab-case properties generate warnings"""
        block = {
            "blockId": "test",
            "element": "div",
            "baseStyles": {
                "background-color": "#fff",  # kebab-case
            }
        }
        self.validator.validate(block)
        self.assertTrue(any("camelCase" in w.message for w in self.validator.warnings))

    def test_img_without_src(self):
        """Test warning for img without src attribute"""
        block = {
            "blockId": "test-img",
            "element": "img",
        }
        self.validator.validate(block)
        self.assertTrue(any("src" in w.message for w in self.validator.warnings))

    def test_img_without_alt(self):
        """Test warning for img without alt attribute"""
        block = {
            "blockId": "test-img",
            "element": "img",
            "attributes": {"src": "/image.jpg"}
        }
        self.validator.validate(block)
        self.assertTrue(any("alt" in w.message for w in self.validator.warnings))

    def test_a_without_href(self):
        """Test warning for anchor without href"""
        block = {
            "blockId": "test-link",
            "element": "a",
            "innerHTML": "Click me"
        }
        self.validator.validate(block)
        self.assertTrue(any("href" in w.message for w in self.validator.warnings))

    def test_lorem_ipsum_warning(self):
        """Test warning for lorem ipsum content"""
        block = {
            "blockId": "test",
            "element": "p",
            "innerHTML": "Lorem ipsum dolor sit amet"
        }
        self.validator.validate(block)
        self.assertTrue(any("Lorem ipsum" in w.message for w in self.validator.warnings))

    def test_validation_report(self):
        """Test get_report method"""
        block = {"element": "invalid"}
        self.validator.validate(block)
        report = self.validator.get_report()
        self.assertIn("valid", report)
        self.assertIn("errors", report)
        self.assertIn("warnings", report)
        self.assertIn("error_count", report)
        self.assertIn("warning_count", report)

    def test_strict_mode(self):
        """Test strict mode raises exceptions"""
        validator = BlockValidator(strict=True)
        block = {"element": "invalid-element"}
        with self.assertRaises(ValidationError):
            validator.validate(block)


class TestAutoFixer(unittest.TestCase):
    """Tests for AutoFixer class"""

    def setUp(self):
        self.fixer = AutoFixer()

    def test_fix_missing_block_id(self):
        """Test fixing missing blockId"""
        block = {"element": "div"}
        fixed = self.fixer.fix(block)
        self.assertIn("blockId", fixed)
        self.assertTrue(fixed["blockId"].startswith("div-"))

    def test_fix_missing_element(self):
        """Test fixing missing element"""
        block = {"blockId": "test"}
        fixed = self.fixer.fix(block)
        self.assertEqual(fixed["element"], "div")

    def test_fix_kebab_case_styles(self):
        """Test fixing kebab-case CSS properties"""
        block = {
            "blockId": "test",
            "element": "div",
            "baseStyles": {
                "background-color": "#fff",
                "font-size": "16px",
            }
        }
        fixed = self.fixer.fix(block)
        self.assertIn("backgroundColor", fixed["baseStyles"])
        self.assertIn("fontSize", fixed["baseStyles"])
        self.assertNotIn("background-color", fixed["baseStyles"])
        self.assertNotIn("font-size", fixed["baseStyles"])

    def test_fix_numeric_style_values(self):
        """Test that numeric style values are converted to strings"""
        block = {
            "blockId": "test",
            "element": "div",
            "baseStyles": {
                "opacity": 0.5,
                "zIndex": 10,
            }
        }
        fixed = self.fixer.fix(block)
        self.assertEqual(fixed["baseStyles"]["opacity"], "0.5")
        self.assertEqual(fixed["baseStyles"]["zIndex"], "10")

    def test_fix_duplicate_block_ids(self):
        """Test fixing duplicate blockIds"""
        block = {
            "blockId": "same-id",
            "element": "div",
            "children": [
                {"blockId": "same-id", "element": "span"}
            ]
        }
        fixed = self.fixer.fix(block)
        # Parent should keep original
        self.assertEqual(fixed["blockId"], "same-id")
        # Child should get new ID
        self.assertNotEqual(fixed["children"][0]["blockId"], "same-id")

    def test_fix_adds_img_alt(self):
        """Test that img elements get default alt"""
        block = {
            "blockId": "test",
            "element": "img",
            "attributes": {"src": "/image.jpg"}
        }
        fixed = self.fixer.fix(block)
        self.assertIn("alt", fixed["attributes"])

    def test_fix_adds_a_href(self):
        """Test that anchor elements get default href"""
        block = {
            "blockId": "test",
            "element": "a",
            "innerHTML": "Link"
        }
        fixed = self.fixer.fix(block)
        self.assertIn("href", fixed["attributes"])

    def test_fixes_report(self):
        """Test that fixes are tracked"""
        block = {"element": "div"}
        self.fixer.fix(block)
        fixes = self.fixer.get_fixes_report()
        self.assertIsInstance(fixes, list)
        self.assertTrue(len(fixes) > 0)

    def test_fix_json_markdown_blocks(self):
        """Test fixing JSON with markdown code blocks"""
        json_str = "```json\n{\"key\": \"value\"}\n```"
        fixed = self.fixer.fix_json(json_str)
        self.assertEqual(fixed.strip(), '{"key": "value"}')

    def test_fix_json_trailing_commas(self):
        """Test fixing JSON with trailing commas"""
        json_str = '{"a": 1, "b": 2,}'
        fixed = self.fixer.fix_json(json_str)
        self.assertEqual(fixed, '{"a": 1, "b": 2}')

    def test_fix_nested_children(self):
        """Test that nested children are fixed recursively"""
        block = {
            "blockId": "parent",
            "element": "div",
            "children": [
                {
                    "element": "div",  # missing blockId
                    "baseStyles": {
                        "background-color": "#000",  # kebab-case
                    },
                    "children": [
                        {"element": "span"}  # missing blockId
                    ]
                }
            ]
        }
        fixed = self.fixer.fix(block)
        # Check child has blockId
        self.assertIn("blockId", fixed["children"][0])
        # Check grandchild has blockId
        self.assertIn("blockId", fixed["children"][0]["children"][0])
        # Check styles are fixed
        self.assertIn("backgroundColor", fixed["children"][0]["baseStyles"])


class TestConvenienceFunctions(unittest.TestCase):
    """Tests for convenience functions"""

    def test_validate_block_function(self):
        """Test validate_block convenience function"""
        block = {"blockId": "test", "element": "div"}
        is_valid, report = validate_block(block)
        self.assertTrue(is_valid)
        self.assertIsInstance(report, dict)

    def test_auto_fix_block_function(self):
        """Test auto_fix_block convenience function"""
        block = {"element": "div"}
        fixed, fixes = auto_fix_block(block)
        self.assertIn("blockId", fixed)
        self.assertIsInstance(fixes, list)


if __name__ == "__main__":
    unittest.main()
