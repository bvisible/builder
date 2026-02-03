"""
Block Validator - Simple validation for FrappeBlock structures.
No auto-fix, just validation.
"""

from typing import Optional
import frappe


class BlockValidator:
    """
    Simple validator for FrappeBlock structures.
    Validates that blocks have required fields and valid structure.
    """

    VALID_ELEMENTS = {
        "div", "section", "article", "aside", "main", "header", "footer", "nav",
        "h1", "h2", "h3", "h4", "h5", "h6", "p", "span", "label", "blockquote",
        "a", "button", "img", "video", "iframe",
        "ul", "ol", "li", "form", "input", "textarea", "select", "option",
        "hr", "br", "figure", "figcaption",
    }

    def validate(self, block: dict) -> bool:
        """
        Validate a single block.

        Args:
            block: Block dictionary to validate

        Returns:
            bool: True if valid, False otherwise
        """
        if not isinstance(block, dict):
            return False

        # Check required fields
        if "blockId" not in block:
            frappe.logger().warning("Block missing blockId")
            return False

        if "element" not in block:
            frappe.logger().warning(f"Block {block.get('blockId')} missing element")
            return False

        # Validate element type
        element = block.get("element")
        if element not in self.VALID_ELEMENTS:
            frappe.logger().warning(f"Invalid element type: {element}")
            return False

        # Validate children recursively
        children = block.get("children")
        if children:
            if not isinstance(children, list):
                frappe.logger().warning(f"Block {block.get('blockId')} children is not a list")
                return False

            for child in children:
                if not self.validate(child):
                    return False

        return True

    def validate_blocks(self, blocks: list[dict]) -> bool:
        """
        Validate a list of blocks.

        Args:
            blocks: List of block dictionaries

        Returns:
            bool: True if all blocks are valid
        """
        if not isinstance(blocks, list):
            frappe.logger().warning("Blocks is not a list")
            return False

        if not blocks:
            frappe.logger().warning("Blocks list is empty")
            return False

        # Check for duplicate blockIds
        block_ids = set()

        def collect_ids(block):
            if not isinstance(block, dict):
                return
            block_id = block.get("blockId")
            if block_id:
                if block_id in block_ids:
                    frappe.logger().warning(f"Duplicate blockId: {block_id}")
                block_ids.add(block_id)
            for child in block.get("children", []):
                collect_ids(child)

        for block in blocks:
            collect_ids(block)

        # Validate each block
        for block in blocks:
            if not self.validate(block):
                return False

        return True


__all__ = [
    "BlockValidator",
]
