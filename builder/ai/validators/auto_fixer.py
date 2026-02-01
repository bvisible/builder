"""
Auto Fixer
Automatically fixes common issues in generated blocks.
"""

import json
import re
import uuid
from typing import Any, Optional

from builder.ai.utils import KEBAB_TO_CAMEL, kebab_to_camel


class AutoFixer:
    """
    Automatically fixes common issues in AI-generated blocks.

    Uses shared utilities from builder.ai.utils for CSS property mappings.
    """

    def __init__(self):
        self.fixes_applied: list[str] = []
        self._seen_ids: set[str] = set()

    def fix(self, block: dict) -> dict:
        """
        Fix common issues in a block and its children.

        Args:
            block: Block dictionary to fix

        Returns:
            dict: Fixed block
        """
        self.fixes_applied = []
        self._seen_ids = set()
        return self._fix_block(block)

    def fix_json(self, json_str: str) -> str:
        """
        Fix common JSON issues before parsing.

        Args:
            json_str: JSON string to fix

        Returns:
            str: Fixed JSON string
        """
        fixed = json_str.strip()

        # Remove markdown code blocks
        if fixed.startswith("```"):
            first_newline = fixed.find("\n")
            if first_newline != -1:
                fixed = fixed[first_newline + 1:]
            if fixed.endswith("```"):
                fixed = fixed[:-3]
            fixed = fixed.strip()
            self.fixes_applied.append("Removed markdown code blocks")

        # Try to find JSON start if there's leading text
        if not (fixed.startswith("{") or fixed.startswith("[")):
            obj_start = fixed.find("{")
            arr_start = fixed.find("[")

            if obj_start == -1 and arr_start == -1:
                return fixed  # Nothing we can do

            start = min(obj_start, arr_start) if obj_start >= 0 and arr_start >= 0 else max(obj_start, arr_start)
            fixed = fixed[start:]
            self.fixes_applied.append("Removed leading non-JSON text")

        # Fix trailing commas before } or ]
        fixed = re.sub(r',\s*}', '}', fixed)
        fixed = re.sub(r',\s*]', ']', fixed)
        if "Removed trailing comma" not in self.fixes_applied:
            self.fixes_applied.append("Removed trailing commas")

        # Fix unquoted property names (simple cases)
        # Match: { propertyName: value } and convert to { "propertyName": value }
        fixed = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', fixed)

        # Fix single quotes to double quotes
        # This is risky but common issue
        # Only fix if it looks like JSON structure
        if fixed.count("'") > fixed.count('"'):
            # Replace single quotes used for strings
            fixed = re.sub(r"'([^']*)'", r'"\1"', fixed)
            self.fixes_applied.append("Converted single quotes to double quotes")

        return fixed

    def _fix_block(self, block: dict) -> dict:
        """Fix a single block recursively"""
        if not isinstance(block, dict):
            return block

        fixed = dict(block)

        # Fix blockId
        fixed = self._fix_block_id(fixed)

        # Fix element
        fixed = self._fix_element(fixed)

        # Fix styles
        for style_key in ["baseStyles", "mobileStyles", "tabletStyles", "rawStyles"]:
            if style_key in fixed:
                fixed[style_key] = self._fix_styles(fixed[style_key])

        # Fix attributes
        if "attributes" in fixed:
            fixed["attributes"] = self._fix_attributes(fixed.get("element", "div"), fixed["attributes"])

        # Fix children recursively
        if "children" in fixed and isinstance(fixed["children"], list):
            fixed["children"] = [self._fix_block(child) for child in fixed["children"]]

        return fixed

    def _fix_block_id(self, block: dict) -> dict:
        """Ensure block has a unique blockId"""
        block_id = block.get("blockId")

        if not block_id or not isinstance(block_id, str):
            element = block.get("element", "block")
            new_id = f"{element}-{uuid.uuid4().hex[:8]}"
            block["blockId"] = new_id
            self.fixes_applied.append(f"Generated blockId: {new_id}")
        elif block_id in self._seen_ids:
            new_id = f"{block_id}-{uuid.uuid4().hex[:4]}"
            block["blockId"] = new_id
            self.fixes_applied.append(f"Fixed duplicate blockId: {block_id} -> {new_id}")

        self._seen_ids.add(block["blockId"])
        return block

    def _fix_element(self, block: dict) -> dict:
        """Fix or set default element"""
        element = block.get("element")

        if not element:
            block["element"] = "div"
            self.fixes_applied.append("Set default element: div")
        elif not isinstance(element, str):
            block["element"] = str(element)
            self.fixes_applied.append(f"Converted element to string: {element}")

        return block

    def _fix_styles(self, styles: Any) -> dict:
        """Fix style object"""
        if not styles:
            return {}

        if not isinstance(styles, dict):
            return {}

        fixed = {}
        for key, value in styles.items():
            # Convert kebab-case to camelCase
            if "-" in key:
                camel_key = KEBAB_TO_CAMEL.get(key)
                if camel_key:
                    key = camel_key
                    self.fixes_applied.append(f"Converted {key} to camelCase")
                else:
                    # Try to auto-convert
                    key = kebab_to_camel(key)

            # Ensure value is string
            if value is not None:
                if not isinstance(value, str):
                    value = str(value)
                fixed[key] = value

        return fixed

    def _fix_attributes(self, element: str, attributes: Any) -> dict:
        """Fix attributes object"""
        if not attributes:
            return {}

        if not isinstance(attributes, dict):
            return {}

        fixed = dict(attributes)

        # Add required attributes for specific elements
        if element == "img":
            if "alt" not in fixed:
                fixed["alt"] = "Image"
                self.fixes_applied.append("Added default alt attribute for img")

        if element == "a":
            if "href" not in fixed:
                fixed["href"] = "#"
                self.fixes_applied.append("Added default href for a element")

        return fixed

    def get_fixes_report(self) -> list[str]:
        """Get list of fixes applied"""
        return self.fixes_applied


def auto_fix_block(block: dict) -> tuple[dict, list[str]]:
    """
    Convenience function to fix a block.

    Args:
        block: Block to fix

    Returns:
        tuple: (fixed_block, list_of_fixes)
    """
    fixer = AutoFixer()
    fixed = fixer.fix(block)
    return fixed, fixer.fixes_applied


def auto_fix_json(json_str: str) -> tuple[str, list[str]]:
    """
    Convenience function to fix JSON string.

    Args:
        json_str: JSON string to fix

    Returns:
        tuple: (fixed_json_str, list_of_fixes)
    """
    fixer = AutoFixer()
    fixed = fixer.fix_json(json_str)
    return fixed, fixer.fixes_applied


def fix_and_parse(json_str: str) -> tuple[Optional[dict], list[str], Optional[str]]:
    """
    Fix JSON string and parse it.

    Args:
        json_str: JSON string to fix and parse

    Returns:
        tuple: (parsed_dict_or_none, list_of_fixes, error_message_or_none)
    """
    fixer = AutoFixer()

    # First fix the JSON string
    fixed_json = fixer.fix_json(json_str)

    # Try to parse
    try:
        parsed = json.loads(fixed_json)
    except json.JSONDecodeError as e:
        return None, fixer.fixes_applied, str(e)

    # If it's a dict (single block), fix it
    if isinstance(parsed, dict):
        fixed = fixer.fix(parsed)
        return fixed, fixer.fixes_applied, None

    # If it's a list (array of blocks), fix each
    if isinstance(parsed, list):
        fixed = [fixer.fix(block) if isinstance(block, dict) else block for block in parsed]
        return fixed, fixer.fixes_applied, None

    return parsed, fixer.fixes_applied, None


__all__ = [
    "AutoFixer",
    "auto_fix_block",
    "auto_fix_json",
    "fix_and_parse",
]
