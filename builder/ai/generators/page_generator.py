"""
Page Generator - Creative AI Page Generation
Direct LLM generation with full creative freedom.
"""

import json
from typing import Optional
import frappe

from builder.ai.config import get_ai_settings, AIConfig
from builder.ai.providers import get_provider
from builder.ai.design_system import get_theme
from builder.ai.prompts.system_prompts import get_creative_system_prompt, get_page_generation_prompt
from builder.ai.validators import BlockValidator
from builder.ai.logging import ai_log
from builder.ai.schemas.design_brief import DesignBrief


class PageGenerator:
    """
    Creative page generator using direct LLM generation.

    The AI has full creative freedom to design unique pages.
    It receives a rich system prompt with theme guidelines and
    outputs valid FrappeBlock JSON directly.
    """

    def __init__(
        self,
        provider: str = None,
        model: str = None,
        config: AIConfig = None
    ):
        self.config = config or get_ai_settings()

        if provider:
            self.config.provider = provider
        if model:
            self.config.model = model

        self.llm = get_provider(
            self.config.provider,
            model=self.config.model,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            temperature=0.9,  # Higher temperature for more creative designs
        )

        self.validator = BlockValidator()

    def generate_page(
        self,
        prompt: str,
        theme: str = "modern",
        primary_color: str = None,
        secondary_color: str = None,
        font_family: str = None,
        page_title: str = None,
        page_type: str = None,
        design_brief: DesignBrief = None,
    ) -> list[dict]:
        """
        Generate a complete page with full creative freedom.

        Args:
            prompt: User's description of the desired page/site
            theme: Visual theme name (modern, neobrutalist, etc.)
            primary_color: Custom primary color (e.g., "#6c5ce7")
            secondary_color: Custom secondary color (e.g., "#00b894")
            font_family: Custom font family
            page_title: Page title for context
            page_type: Type of page (accueil, services, contact, etc.)
            design_brief: Optional design brief for visual consistency across pages

        Returns:
            list[dict]: List of FrappeBlock dictionaries
        """
        # Get theme data
        theme_data = get_theme(theme)
        theme_name = theme_data.get("name", theme)
        theme_prompt = theme_data.get("prompt", "")
        theme_colors = theme_data.get("colors", {})

        # Use theme colors as fallback if not provided
        effective_primary = primary_color or theme_colors.get("primary", "#6366f1")
        effective_secondary = secondary_color or theme_colors.get("secondary", "#8b5cf6")

        # Build the system prompt with all context
        system_prompt = get_creative_system_prompt(
            theme_name=theme_name,
            theme_prompt=theme_prompt,
            primary_color=effective_primary,
            secondary_color=effective_secondary,
            font_family=font_family,
            page_type=page_type,
            design_brief=design_brief,
        )

        # Build the user prompt
        user_prompt = get_page_generation_prompt(
            user_prompt=prompt,
            page_title=page_title,
            page_type=page_type,
        )

        # Generate blocks via LLM
        ai_log("info", "PageGenerator.generate_page() calling LLM",
            provider=self.config.provider, model=self.config.model,
            theme=theme_name, page_type=page_type)
        ai_log("debug", "Prompt sizes",
            system_prompt_len=len(system_prompt), user_prompt_len=len(user_prompt))
        frappe.logger().info(f"Generating page: {prompt[:50]}...")

        try:
            # Use configurable think level for creative reasoning
            think_value = self.config.get_think_value(self.config.page_think_level)
            response = self.llm.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                think=think_value,
            )
            ai_log("info", "LLM response received", response_len=len(response))
        except Exception as e:
            ai_log("error", "LLM.generate() failed", error=str(e))
            raise

        # Parse JSON response
        ai_log("debug", "Parsing LLM response as JSON")
        blocks = self._parse_response(response)

        # Validate blocks
        ai_log("debug", "Validating blocks", blocks_count=len(blocks))
        if not self.validator.validate_blocks(blocks):
            ai_log("error", "Block validation failed", prompt_preview=prompt[:100])
            frappe.log_error("Block validation failed", f"Prompt: {prompt[:100]}")
            raise ValueError("Generated blocks failed validation")

        # Apply colors as CSS variables (always apply theme colors)
        blocks = self._apply_custom_colors(blocks, effective_primary, effective_secondary)

        ai_log("info", "Page generation complete", blocks_count=len(blocks))
        frappe.logger().info(f"Generated {len(blocks)} blocks successfully")
        return blocks

    def _parse_response(self, response: str) -> list[dict]:
        """
        Parse the LLM response into a list of blocks.
        Includes repair logic for truncated JSON.
        """
        # Clean up response - remove markdown code blocks if present
        response = response.strip()

        if response.startswith("```"):
            # Remove markdown code block
            lines = response.split("\n")
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)

        # Try to parse JSON
        try:
            data = json.loads(response)

            # Ensure it's a list
            if isinstance(data, dict):
                # If it's a single block, wrap in list
                data = [data]

            if not isinstance(data, list):
                raise ValueError("Response is not a list of blocks")

            return data

        except json.JSONDecodeError as e:
            # Try to repair truncated JSON
            frappe.logger().warning(f"JSON parse error, attempting repair: {e}")
            repaired = self._repair_truncated_json(response)
            if repaired:
                try:
                    data = json.loads(repaired)
                    if isinstance(data, dict):
                        data = [data]
                    if isinstance(data, list) and len(data) > 0:
                        frappe.logger().info(f"JSON repair successful, recovered {len(data)} blocks")
                        return data
                except json.JSONDecodeError:
                    pass

            frappe.log_error("JSON parse error", f"Error: {e}\nResponse: {response[:500]}")
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")

    def _repair_truncated_json(self, response: str) -> str:
        """
        Attempt to repair truncated JSON by closing open structures.
        Returns repaired JSON string or None if repair fails.
        """
        # Find the last complete block by looking for closing braces/brackets
        # Strategy: progressively truncate and add closing brackets

        # Count open brackets
        open_braces = 0
        open_brackets = 0
        in_string = False
        escape_next = False
        last_valid_pos = 0

        for i, char in enumerate(response):
            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == '{':
                open_braces += 1
            elif char == '}':
                open_braces -= 1
                if open_braces >= 0 and open_brackets >= 0:
                    last_valid_pos = i + 1
            elif char == '[':
                open_brackets += 1
            elif char == ']':
                open_brackets -= 1
                if open_braces >= 0 and open_brackets >= 0:
                    last_valid_pos = i + 1

        # If we're in the middle of a string, find the start and truncate there
        if in_string:
            # Find the last complete object/array before the broken string
            # Look backwards for a comma or opening bracket at the same nesting level
            for i in range(len(response) - 1, -1, -1):
                if response[i] == ',' or response[i] in '[{':
                    # Truncate here and close
                    response = response[:i]
                    if response[i-1:i] == ',':
                        response = response[:-1]
                    break

        # Try to close the JSON properly
        # Remove trailing incomplete content
        response = response.rstrip()

        # Remove trailing comma if present
        if response.endswith(','):
            response = response[:-1]

        # Add closing brackets
        closers = ""
        for char in response:
            if char == '"':
                in_string = not in_string
            if not in_string:
                if char == '{':
                    closers = '}' + closers
                elif char == '}' and closers.startswith('}'):
                    closers = closers[1:]
                elif char == '[':
                    closers = ']' + closers
                elif char == ']' and closers.startswith(']'):
                    closers = closers[1:]

        return response + closers

    def _apply_custom_colors(
        self,
        blocks: list[dict],
        primary_color: str = None,
        secondary_color: str = None
    ) -> list[dict]:
        """
        Apply custom colors as CSS variables to root blocks.
        """
        if not primary_color and not secondary_color:
            return blocks

        for block in blocks:
            # Apply to section-level blocks
            element = block.get("element", "")
            if element in ("section", "div", "main", "article"):
                if "rawStyles" not in block:
                    block["rawStyles"] = {}

                if primary_color:
                    block["rawStyles"]["--primary-color"] = primary_color
                    # Add RGB version for rgba() usage
                    if primary_color.startswith("#") and len(primary_color) >= 7:
                        try:
                            r = int(primary_color[1:3], 16)
                            g = int(primary_color[3:5], 16)
                            b = int(primary_color[5:7], 16)
                            block["rawStyles"]["--primary-rgb"] = f"{r}, {g}, {b}"
                        except ValueError:
                            pass

                if secondary_color:
                    block["rawStyles"]["--secondary-color"] = secondary_color

        return blocks


def generate_page(
    prompt: str,
    theme: str = "modern",
    provider: str = None,
    model: str = None,
    primary_color: str = None,
    secondary_color: str = None,
) -> list[dict]:
    """
    Convenience function to generate a page.
    """
    generator = PageGenerator(provider=provider, model=model)
    return generator.generate_page(
        prompt=prompt,
        theme=theme,
        primary_color=primary_color,
        secondary_color=secondary_color,
    )


__all__ = [
    "PageGenerator",
    "generate_page",
]
