"""
Block Validator - Simple validation for FrappeBlock structures.
No auto-fix, just validation.
"""

from typing import Optional
import frappe
from builder.ai.logging import ai_log


class BlockValidator:
    """
    Simple validator for FrappeBlock structures.
    Validates that blocks have required fields and valid structure.
    """

    VALID_ELEMENTS = {
        # Layout
        "div", "section", "article", "aside", "main", "header", "footer", "nav",
        # Headings & text
        "h1", "h2", "h3", "h4", "h5", "h6", "p", "span", "label", "blockquote",
        "small", "strong", "em", "b", "i", "u", "sub", "sup", "mark", "code", "pre",
        "cite", "abbr", "time", "address", "q", "del", "ins", "kbd", "samp", "var",
        "dl", "dt", "dd", "data", "wbr",
        # Interactive
        "a", "button", "img", "video", "iframe", "audio", "source",
        # Lists
        "ul", "ol", "li",
        # Forms
        "form", "input", "textarea", "select", "option",
        # Table
        "table", "thead", "tbody", "tfoot", "tr", "td", "th", "caption", "colgroup", "col",
        # Misc
        "hr", "br", "figure", "figcaption", "details", "summary",
        # SVG (LLM sometimes generates inline SVG icons)
        "svg", "path", "circle", "rect", "line", "polyline", "polygon", "g", "defs",
        "clipPath", "use", "symbol", "text", "tspan",
    }

    def validate(self, block: dict, _depth: int = 0) -> bool:
        """
        Validate a single block.

        Args:
            block: Block dictionary to validate
            _depth: Internal recursion depth tracker

        Returns:
            bool: True if valid, False otherwise
        """
        if not isinstance(block, dict):
            return False

        # Check required fields
        if "blockId" not in block:
            ai_log("warning", "Block missing blockId", block_keys=list(block.keys())[:5])
            return False

        if "element" not in block:
            ai_log("warning", "Block missing element", blockId=block.get("blockId"))
            return False

        # Validate element type
        element = block.get("element")
        if element not in self.VALID_ELEMENTS:
            ai_log("warning", "Invalid element type in block", element=element, blockId=block.get("blockId"))
            return False

        # Validate children recursively
        children = block.get("children")
        if children:
            if not isinstance(children, list):
                ai_log("warning", "Block children is not a list", blockId=block.get("blockId"))
                return False

            for child in children:
                if not self.validate(child, _depth=_depth + 1):
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
            ai_log("warning", "Blocks is not a list", type=str(type(blocks)))
            return False

        if not blocks:
            ai_log("warning", "Blocks list is empty")
            return False

        # Check for duplicate blockIds
        block_ids = set()

        def collect_ids(block):
            if not isinstance(block, dict):
                return
            block_id = block.get("blockId")
            if block_id:
                if block_id in block_ids:
                    ai_log("warning", "Duplicate blockId", blockId=block_id)
                block_ids.add(block_id)
            for child in block.get("children", []):
                collect_ids(child)

        for block in blocks:
            collect_ids(block)

        # Validate each block
        for i, block in enumerate(blocks):
            if not self.validate(block):
                ai_log("warning", "Block validation failed at index",
                       index=i, element=block.get("element"), blockId=block.get("blockId"))
                return False

        return True


__all__ = [
    "BlockValidator",
]
