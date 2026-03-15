"""
Block Validator - Validation + auto-repair for FrappeBlock structures.
Fixes common LLM output issues instead of rejecting the entire generation.
"""

import uuid
from typing import Optional
import frappe
from builder.ai.logging import ai_log


class BlockValidator:
    """
    Validator and auto-repairer for FrappeBlock structures.
    Fixes common issues (missing blockId, invalid elements) instead of failing.
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

    def __init__(self):
        self._repairs = 0

    def repair_block(self, block: dict, _depth: int = 0) -> Optional[dict]:
        """
        Validate and auto-repair a single block.
        Returns the repaired block, or None if unfixable.
        """
        if not isinstance(block, dict):
            return None

        # Auto-generate missing blockId
        if "blockId" not in block or not block["blockId"]:
            element = block.get("element", "div")
            block["blockId"] = f"{element}-auto-{uuid.uuid4().hex[:8]}"
            self._repairs += 1

        # Default to div if element missing
        if "element" not in block or not block["element"]:
            block["element"] = "div"
            self._repairs += 1

        # Fix invalid element type — map to closest valid or use div
        element = block.get("element")
        if element not in self.VALID_ELEMENTS:
            ai_log("debug", "Replacing invalid element with div",
                   invalid_element=element, blockId=block.get("blockId"))
            block["element"] = "div"
            self._repairs += 1

        # Recursively repair children
        children = block.get("children")
        if children:
            if not isinstance(children, list):
                block["children"] = []
                self._repairs += 1
            else:
                repaired_children = []
                for child in children:
                    repaired = self.repair_block(child, _depth=_depth + 1)
                    if repaired:
                        repaired_children.append(repaired)
                block["children"] = repaired_children

        return block

    def validate_and_repair(self, blocks: list[dict]) -> list[dict]:
        """
        Validate and auto-repair a list of blocks.
        Returns the repaired blocks list. Only returns empty if input was completely invalid.
        """
        self._repairs = 0

        if not isinstance(blocks, list):
            ai_log("warning", "Blocks is not a list", type=str(type(blocks)))
            return []

        if not blocks:
            ai_log("warning", "Blocks list is empty")
            return []

        # Deduplicate blockIds
        seen_ids = set()

        def dedup_ids(block):
            if not isinstance(block, dict):
                return
            block_id = block.get("blockId", "")
            if block_id in seen_ids:
                new_id = f"{block_id}-{uuid.uuid4().hex[:6]}"
                block["blockId"] = new_id
                self._repairs += 1
            seen_ids.add(block.get("blockId", ""))
            for child in block.get("children", []):
                dedup_ids(child)

        # Repair each block
        repaired = []
        for block in blocks:
            fixed = self.repair_block(block)
            if fixed:
                repaired.append(fixed)

        # Dedup after repair
        for block in repaired:
            dedup_ids(block)

        if self._repairs > 0:
            ai_log("info", "Blocks auto-repaired",
                   repairs=self._repairs, blocks_count=len(repaired))

        return repaired

    def validate(self, block: dict, _depth: int = 0) -> bool:
        """Legacy validation — still returns bool for backward compat."""
        if not isinstance(block, dict):
            return False
        if "blockId" not in block:
            return False
        if "element" not in block:
            return False
        if block.get("element") not in self.VALID_ELEMENTS:
            return False
        children = block.get("children")
        if children:
            if not isinstance(children, list):
                return False
            for child in children:
                if not self.validate(child, _depth=_depth + 1):
                    return False
        return True

    def validate_blocks(self, blocks: list[dict]) -> bool:
        """Legacy validation — returns True if all blocks valid."""
        if not isinstance(blocks, list) or not blocks:
            return False
        for i, block in enumerate(blocks):
            if not self.validate(block):
                ai_log("warning", "Block validation failed at index",
                       index=i, element=block.get("element"), blockId=block.get("blockId"))
                return False
        return True


__all__ = [
    "BlockValidator",
]
