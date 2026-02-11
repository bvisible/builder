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

        # Log design brief details if available
        if design_brief:
            ai_log("info", "Design brief received",
                heading_font=design_brief.heading_font,
                body_font=design_brief.body_font,
                hero_height=design_brief.section_heights.hero_min_height if design_brief.section_heights else "not set",
                hero_style=design_brief.hero_style,
                primary_color=effective_primary,
                secondary_color=effective_secondary)

        # Get output language from config
        output_language = self.config.output_language

        # Build the system prompt with all context
        system_prompt = get_creative_system_prompt(
            theme_name=theme_name,
            theme_prompt=theme_prompt,
            primary_color=effective_primary,
            secondary_color=effective_secondary,
            font_family=font_family,
            page_type=page_type,
            design_brief=design_brief,
            output_language=output_language,
        )

        # Build the user prompt
        user_prompt = get_page_generation_prompt(
            user_prompt=prompt,
            page_title=page_title,
            page_type=page_type,
            output_language=output_language,
        )

        # Generate blocks via LLM
        ai_log("info", "PageGenerator.generate_page() calling LLM",
            provider=self.config.provider, model=self.config.model,
            theme=theme_name, page_type=page_type)
        ai_log("debug", "Prompt sizes",
            system_prompt_len=len(system_prompt), user_prompt_len=len(user_prompt))
        ai_log("debug", "System prompt preview",
            system_prompt_start=system_prompt[:500])
        ai_log("debug", "User prompt preview",
            user_prompt_start=user_prompt[:300])
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

        # Post-processing: always inject fonts to ensure consistency
        if design_brief:
            ai_log("debug", "Injecting fonts from design brief",
                   heading_font=design_brief.heading_font,
                   body_font=design_brief.body_font)
            blocks = self._inject_fonts(blocks, design_brief)
            # Note: _auto_fix_styles removed - AI should decide heights/styles

        # Sanitize Jinja includes — fix or remove invalid template paths
        blocks = self._sanitize_jinja_includes(blocks)

        # Log summary of generated blocks
        first_block_info = None
        if blocks:
            first_block = blocks[0]
            first_block_info = {
                "element": first_block.get("element"),
                "blockId": first_block.get("blockId"),
                "has_children": len(first_block.get("children", [])) > 0
            }

        ai_log("info", "Page generation complete",
            blocks_count=len(blocks),
            first_block=first_block_info,
            page_type=page_type,
            theme=theme_name)
        frappe.logger().info(f"Generated {len(blocks)} blocks successfully")
        return blocks

    def _parse_response(self, response: str) -> list[dict]:
        """Parse the LLM response into a list of blocks."""
        import json_repair

        # Clean up response - remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)

        # Step 1: Try standard json.loads first (fastest path)
        try:
            data = json.loads(response)
            return self._ensure_list(data)
        except json.JSONDecodeError as e:
            ai_log("debug", "Standard JSON parse failed, using json_repair",
                   error=str(e)[:100], response_len=len(response))

        # Step 2: Use json-repair library (handles all common LLM errors)
        try:
            data = json_repair.loads(response)
            if data:
                result = self._ensure_list(data)
                ai_log("info", "JSON repaired successfully by json-repair",
                       blocks_count=len(result))
                return result
        except Exception as e:
            ai_log("warning", "json_repair also failed", error=str(e)[:100])

        # Step 3: Last resort - truncation repair + json-repair
        repaired = self._repair_truncated_json(response)
        if repaired:
            try:
                data = json_repair.loads(repaired)
                if data:
                    result = self._ensure_list(data)
                    ai_log("info", "JSON repaired after truncation fix",
                           blocks_count=len(result))
                    return result
            except Exception:
                pass

        frappe.log_error("JSON parse error",
                         f"All repair strategies failed. Response: {response[:500]}")
        raise ValueError("Failed to parse LLM response as JSON")

    def _ensure_list(self, data) -> list[dict]:
        """Ensure parsed data is a list of blocks."""
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list) and len(data) > 0:
            return data
        raise ValueError("Response is not a list of blocks")

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

    def _inject_fonts(self, blocks: list[dict], brief: DesignBrief) -> list[dict]:
        """
        Inject font families into all text elements based on design brief.
        Ensures fonts are applied even if AI forgot to include them.
        """
        heading_elements = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
        body_elements = {'p', 'span', 'label', 'li', 'blockquote', 'a'}

        heading_font = f"'{brief.heading_font}', sans-serif"
        body_font = f"'{brief.body_font}', sans-serif"

        def process_block(block: dict) -> None:
            element = block.get('element', '')
            base_styles = block.get('baseStyles', {})

            if element in heading_elements:
                if 'fontFamily' not in base_styles:
                    base_styles['fontFamily'] = heading_font
                    block['baseStyles'] = base_styles
            elif element in body_elements:
                if 'fontFamily' not in base_styles:
                    base_styles['fontFamily'] = body_font
                    block['baseStyles'] = base_styles

            # Process children recursively
            for child in block.get('children', []):
                process_block(child)

        for block in blocks:
            process_block(block)

        return blocks

    # Known valid Jinja include paths
    VALID_INCLUDES = {
        # Builder templates
        "builder/templates/includes/contact_form.html",
        "builder/templates/includes/contact_info.html",
        "builder/templates/includes/team_grid.html",
        "builder/templates/includes/company_timeline.html",
        "builder/templates/includes/google_map.html",
        # Webshop templates
        "webshop/templates/includes/product_carousel.html",
        "webshop/templates/includes/brand_carousel.html",
        # Frappe templates
        "templates/generators/webpage_scripts.html",
    }

    # Map of wrong paths to correct paths
    INCLUDE_CORRECTIONS = {
        "webshop/templates/includes/contact_form.html": "builder/templates/includes/contact_form.html",
        "webshop/templates/includes/contact_info.html": "builder/templates/includes/contact_info.html",
        "webshop/templates/includes/team_grid.html": "builder/templates/includes/team_grid.html",
        "webshop/templates/includes/google_map.html": "builder/templates/includes/google_map.html",
    }

    def _sanitize_jinja_includes(self, blocks: list[dict]) -> list[dict]:
        """
        Sanitize Jinja {% include %} in innerHTML fields.
        Fixes wrong template paths and removes includes to non-existent templates.
        """
        import re

        include_pattern = re.compile(
            r"""{%[-\s]*include\s+['"]([^'"]+)['"]\s*[-\s]*%}"""
        )

        def sanitize_block(block: dict) -> bool:
            """Sanitize a block's innerHTML. Returns False if block should be removed."""
            inner = block.get("innerHTML", "")
            if not inner or "{%" not in inner:
                # Recurse into children
                if block.get("children"):
                    block["children"] = [
                        c for c in block["children"]
                        if not isinstance(c, dict) or sanitize_block(c)
                    ]
                return True

            matches = include_pattern.findall(inner)
            for template_path in matches:
                if template_path in self.VALID_INCLUDES:
                    continue

                # Try to correct the path
                corrected = self.INCLUDE_CORRECTIONS.get(template_path)
                if corrected:
                    ai_log("warning", "Correcting Jinja include path",
                           wrong=template_path, corrected=corrected)
                    inner = inner.replace(template_path, corrected)
                    block["innerHTML"] = inner
                else:
                    # Unknown template — remove the include
                    ai_log("warning", "Removing invalid Jinja include",
                           template=template_path,
                           blockId=block.get("blockId"))
                    # Remove the entire include tag
                    bad_pattern = re.compile(
                        r"""{%[-\s]*include\s+['"]""" + re.escape(template_path) + r"""['"]\s*[-\s]*%}"""
                    )
                    inner = bad_pattern.sub("", inner).strip()
                    block["innerHTML"] = inner

            # If innerHTML is now empty, signal removal
            if not block.get("innerHTML", "").strip() and not block.get("children"):
                return False

            # Recurse into children
            if block.get("children"):
                block["children"] = [
                    c for c in block["children"]
                    if not isinstance(c, dict) or sanitize_block(c)
                ]
            return True

        # Process top-level blocks, removing empty ones
        result = []
        for block in blocks:
            if sanitize_block(block):
                result.append(block)
            else:
                ai_log("info", "Removed empty block after Jinja sanitization",
                       blockId=block.get("blockId"))

        return result

    def _auto_fix_styles(self, blocks: list[dict], brief: DesignBrief) -> list[dict]:
        """
        Auto-fix common style issues based on design brief.
        - Fix hero heights
        - Fix contrast issues (white text on light backgrounds)
        """
        for block in blocks:
            self._fix_block_styles(block, brief)

        return blocks

    def _fix_block_styles(self, block: dict, brief: DesignBrief) -> None:
        """Recursively fix styles in a block and its children."""
        block_id = block.get('blockId', '').lower()
        base_styles = block.get('baseStyles', {})
        mobile_styles = block.get('mobileStyles', {})

        # Fix hero section heights
        if 'hero' in block_id:
            if 'minHeight' not in base_styles:
                base_styles['minHeight'] = brief.section_heights.hero_min_height
            if 'minHeight' not in mobile_styles:
                mobile_styles['minHeight'] = brief.section_heights.hero_min_height_mobile
            block['baseStyles'] = base_styles
            block['mobileStyles'] = mobile_styles

        # Fix contrast: detect light backgrounds with white text
        bg = base_styles.get('backgroundColor', '') or base_styles.get('background', '')
        if self._is_light_background(bg):
            self._fix_text_colors_recursive(block, 'var(--text-color)')

        # Process children
        for child in block.get('children', []):
            self._fix_block_styles(child, brief)

    def _is_light_background(self, bg: str) -> bool:
        """Detect if a background is light (requiring dark text)."""
        if not bg:
            return False

        light_patterns = [
            '#ffffff', '#fff', '#f8fafc', '#fafafa', '#f5f5f5',
            '#f9fafb', '#f3f4f6', '#e5e7eb', '#f1f5f9', '#f4f4f5',
            'var(--surface-color)', 'white', 'rgb(255', 'rgba(255, 255, 255'
        ]
        bg_lower = bg.lower()
        return any(p in bg_lower for p in light_patterns)

    def _is_dark_background(self, bg: str) -> bool:
        """Detect if a background is dark (requiring white text)."""
        if not bg:
            return False

        dark_patterns = [
            'gradient', 'linear-gradient', 'radial-gradient',
            'var(--primary-color)', 'var(--secondary-color)',
            '#0', '#1', '#2', '#3', '#4', '#5',  # Dark hex colors
            'rgb(0', 'rgb(1', 'rgb(2', 'rgb(3', 'rgb(4', 'rgb(5',
        ]
        bg_lower = bg.lower()
        return any(p in bg_lower for p in dark_patterns)

    def _fix_text_colors_recursive(self, block: dict, target_color: str) -> None:
        """
        Recursively fix text colors in children if they're white on a light background.
        """
        for child in block.get('children', []):
            child_styles = child.get('baseStyles', {})

            # Check if this child has white text
            current_color = child_styles.get('color', '')
            if current_color in ['#ffffff', '#fff', 'white', 'rgb(255, 255, 255)']:
                # Check if this child doesn't have its own dark background
                child_bg = child_styles.get('backgroundColor', '') or child_styles.get('background', '')
                if not self._is_dark_background(child_bg):
                    child_styles['color'] = target_color
                    child['baseStyles'] = child_styles

            # Continue recursively
            self._fix_text_colors_recursive(child, target_color)


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
