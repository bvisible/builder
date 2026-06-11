"""
Page Generator - Creative AI Page Generation
Direct LLM generation with full creative freedom.
"""

import json
import re
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

        # Validate and auto-repair blocks (instead of rejecting)
        ai_log("debug", "Validating and repairing blocks", blocks_count=len(blocks))
        blocks = self.validator.validate_and_repair(blocks)
        if not blocks:
            ai_log("error", "Block validation failed — no recoverable blocks", prompt_preview=prompt[:100])
            frappe.log_error("Block validation failed", f"Prompt: {prompt[:100]}")
            raise ValueError("Generated blocks failed validation — no recoverable blocks")

        # Apply colors as CSS variables (always apply theme colors)
        blocks = self._apply_custom_colors(blocks, effective_primary, effective_secondary)

        # Post-processing: always inject fonts to ensure consistency
        if design_brief:
            ai_log("debug", "Injecting fonts from design brief",
                   heading_font=design_brief.heading_font,
                   body_font=design_brief.body_font)
            blocks = self._inject_fonts(blocks, design_brief)
        # Fix text color contrast issues (white text on light backgrounds)
        blocks = self._fix_contrast(blocks)

        # WCAG hard guard: resolve the actual luminance of every element's
        # effective background vs its text color and repair unreadable pairs
        # (e.g. the LLM emitting backgroundColor AND color = var(--text-color)
        # on a CTA — black on black).
        blocks = self._fix_contrast_wcag(blocks, effective_primary, effective_secondary)

        # Sanitize Jinja includes — fix or remove invalid template paths
        blocks = self._sanitize_jinja_includes(blocks)

        # Jinja syntax hard guard: every innerHTML carrying Jinja statements
        # must COMPILE. Repairs the classic LLM mistake of single-quoting a
        # string that contains a French apostrophe ({% set address = 'Route de
        # l'Industrie…' %} → TemplateSyntaxError → whole page 500s); strips
        # the statement entirely when unrecoverable.
        blocks = self._sanitize_jinja_syntax(blocks)

        # Strip layout props that contradict the block's display mode.
        # Kimi (and other reasoning models) sometimes emit `display: flex`
        # together with `gridTemplateColumns` — the browser picks one and
        # the layout collapses. This pass guarantees a clean contract.
        blocks = self._sanitize_layout_styles(blocks)

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

    def _fix_contrast(self, blocks: list[dict]) -> list[dict]:
        """
        Fix text color contrast issues.
        - White text on light/white backgrounds → dark text
        - Dark text on dark/gradient backgrounds → white text
        """
        for block in blocks:
            self._fix_contrast_recursive(block)
        return blocks

    def _fix_contrast_recursive(self, block: dict) -> None:
        """Recursively detect and fix contrast issues in blocks."""
        base_styles = block.get('baseStyles', {})
        bg = base_styles.get('backgroundColor', '') or base_styles.get('background', '')
        has_bg_image = bool(base_styles.get('backgroundImage', ''))

        # Sections with light backgrounds: fix white text children
        if self._is_light_background(bg) and not has_bg_image:
            self._fix_text_colors_recursive(block, 'var(--text-color)')
        # Sections with dark/gradient backgrounds or background images: fix dark text children
        elif has_bg_image or self._is_dark_background(bg):
            self._ensure_light_text_recursive(block)

        # Recurse into children sections
        for child in block.get('children', []):
            if isinstance(child, dict):
                child_el = child.get('element', '')
                if child_el in ('section', 'div', 'main', 'article'):
                    self._fix_contrast_recursive(child)

    def _ensure_light_text_recursive(self, block: dict) -> None:
        """Ensure text on dark backgrounds is white."""
        dark_text = [
            'var(--text-color)', '#333', '#333333', '#1a1a1a', '#111',
            '#000', '#000000', 'black', '#374151', '#1f2937',
        ]
        for child in block.get('children', []):
            if not isinstance(child, dict):
                continue
            child_styles = child.get('baseStyles', {})
            color = child_styles.get('color', '')
            # If text has a dark color and no own background
            child_bg = child_styles.get('backgroundColor', '') or child_styles.get('background', '')
            if color.lower() in [c.lower() for c in dark_text] and not child_bg:
                child_styles['color'] = '#ffffff'
                child['baseStyles'] = child_styles
            self._ensure_light_text_recursive(child)

    # ------------------------------------------------------------------
    # WCAG luminance guard
    # ------------------------------------------------------------------
    # Approximate luminance of the theme CSS variables (light theme values).
    # Used when an element's color/background is expressed as a variable the
    # generator cannot resolve from the brief.
    CSS_VAR_FALLBACK_LUMINANCE = {
        "var(--text-color)": 0.02,        # near-black body text
        "var(--muted-color)": 0.18,       # medium gray
        "var(--background-color)": 0.95,  # near-white page background
        "var(--surface-color)": 0.93,
        "var(--border-color)": 0.75,
    }

    def _fix_contrast_wcag(self, blocks: list[dict], primary_color: str = None,
                           secondary_color: str = None) -> list[dict]:
        """Hard contrast guard: compute the WCAG luminance of every element's
        effective background and of its text color, and repair any pair below
        a 3:1 ratio (large-text/UI threshold). Catches what the heuristic
        passes miss — e.g. the LLM emitting the SAME value for backgroundColor
        and color on a CTA (black on black), or a dark text on var-based dark
        backgrounds."""
        var_map = {}
        if primary_color:
            var_map["var(--primary-color)"] = primary_color
        if secondary_color:
            var_map["var(--secondary-color)"] = secondary_color
        fixed_count = 0

        def contrast(l1: float, l2: float) -> float:
            hi, lo = max(l1, l2), min(l1, l2)
            return (hi + 0.05) / (lo + 0.05)

        def walk(block: dict, inherited_bg_lum):
            nonlocal fixed_count
            styles = block.get("baseStyles") or {}
            own_bg = styles.get("backgroundColor") or styles.get("background") or ""
            own_bg_lum = self._resolve_luminance(own_bg, var_map)
            bg_lum = own_bg_lum if own_bg_lum is not None else inherited_bg_lum

            element = block.get("element", "")
            has_text = bool((block.get("innerHTML") or "").strip()) and element not in (
                "img", "video", "iframe", "hr", "input", "textarea", "select",
            )
            if has_text and bg_lum is not None:
                color = styles.get("color") or ""
                text_lum = self._resolve_luminance(color, var_map)
                if text_lum is None and not color:
                    # No own color: rendered color is inherited. A parent fix
                    # already turned dark-section children white, so only the
                    # default dark body text remains a realistic assumption.
                    text_lum = self.CSS_VAR_FALLBACK_LUMINANCE["var(--text-color)"]
                if text_lum is not None and contrast(bg_lum, text_lum) < 3.0:
                    styles["color"] = "#ffffff" if bg_lum < 0.35 else "var(--text-color)"
                    block["baseStyles"] = styles
                    fixed_count += 1

            for child in block.get("children") or []:
                if isinstance(child, dict):
                    walk(child, bg_lum)

        for block in blocks:
            walk(block, None)
        if fixed_count:
            ai_log("info", "WCAG contrast guard repaired unreadable text", fixes=fixed_count)
        return blocks

    def _resolve_luminance(self, value: str, var_map: dict):
        """WCAG relative luminance of a CSS color value, or None when the
        value cannot be resolved (unknown variable, image url, ...)."""
        if not value or not isinstance(value, str):
            return None
        v = value.strip().lower()
        if v in ("transparent", "none", "inherit", "unset", "initial", "currentcolor"):
            return None

        # Resolve known CSS variables (brief colors first, theme fallbacks second)
        for var_name, hex_val in var_map.items():
            if v == var_name.lower():
                v = hex_val.lower()
                break
        else:
            if v in self.CSS_VAR_FALLBACK_LUMINANCE:
                return self.CSS_VAR_FALLBACK_LUMINANCE[v]

        # Gradients: approximate with the first resolvable color stop
        if "gradient" in v:
            m = re.search(r"#[0-9a-f]{6}\b|#[0-9a-f]{3}\b", v)
            if m:
                v = m.group(0)
            else:
                for var_name, hex_val in var_map.items():
                    if var_name.lower() in v:
                        v = hex_val.lower()
                        break
                else:
                    return None
        if v.startswith("var(") or "url(" in v:
            return None

        v = {"white": "#ffffff", "black": "#000000"}.get(v, v)

        rgb = None
        m = re.match(r"^#([0-9a-f]{3})$", v)
        if m:
            rgb = tuple(int(c * 2, 16) for c in m.group(1))
        else:
            m = re.match(r"^#([0-9a-f]{6})(?:[0-9a-f]{2})?$", v)
            if m:
                raw = m.group(1)
                rgb = tuple(int(raw[i:i + 2], 16) for i in (0, 2, 4))
            else:
                m = re.match(r"^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", v)
                if m:
                    rgb = tuple(min(255, int(g)) for g in m.groups())
        if rgb is None:
            return None

        channels = []
        for c in rgb:
            c = c / 255
            channels.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
        r, g, b = channels
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

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

    # Pattern to match {{ google_map address="..." }} shortcode from AI
    SHORTCODE_PATTERN = re.compile(
        r"""\{\{\s*google_map\s+address=["']([^"']+)["']\s*\}\}"""
    )

    def _convert_shortcodes(self, inner: str) -> str:
        """Convert AI shortcode notation to valid Jinja includes."""
        def replace_google_map(m):
            addr = m.group(1)
            return (
                '{%% set address = "%s" %%}'
                '{%% set height = "400px" %%}'
                '{%% include "builder/templates/includes/google_map.html" %%}'
            ) % addr

        return self.SHORTCODE_PATTERN.sub(replace_google_map, inner)

    # ------------------------------------------------------------------
    # Jinja syntax guard
    # ------------------------------------------------------------------
    def _sanitize_jinja_syntax(self, blocks: list[dict]) -> list[dict]:
        """Guarantee that every innerHTML containing Jinja compiles.

        A single bad statement (typically an unescaped apostrophe inside a
        single-quoted {% set %} string) makes the WHOLE page render a 500.
        Repair strategy per block: compile → requote single-quoted set-strings
        to double quotes → compile again → as a last resort drop the Jinja
        statements and keep the plain markup."""
        fixed = 0
        stripped = 0

        def walk(block: dict):
            nonlocal fixed, stripped
            html = block.get("innerHTML")
            if isinstance(html, str) and ("{%" in html or "{{" in html):
                if not self._jinja_compiles(html):
                    requoted = self._requote_jinja_set_strings(html)
                    if requoted != html and self._jinja_compiles(requoted):
                        block["innerHTML"] = requoted
                        fixed += 1
                    else:
                        block["innerHTML"] = re.sub(r"{%.*?%}", "", html, flags=re.S)
                        stripped += 1
            for child in block.get("children") or []:
                if isinstance(child, dict):
                    walk(child)

        for block in blocks:
            walk(block)
        if fixed or stripped:
            ai_log("warning", "Jinja syntax guard repaired blocks",
                   requoted=fixed, stripped=stripped)
        return blocks

    def _jinja_compiles(self, html: str) -> bool:
        try:
            from frappe.utils.jinja import get_jenv

            get_jenv().from_string(html)
            return True
        except Exception as e:
            import jinja2

            if isinstance(e, jinja2.TemplateSyntaxError):
                return False
            # Non-syntax failure (env/db hiccup while building the jinja env):
            # fail open — never strip valid markup over a transient error.
            return True

    @staticmethod
    def _requote_jinja_set_strings(html: str) -> str:
        """Rewrite {% set x = '…' %} statements to double-quoted strings.

        The greedy inner capture spans from the FIRST to the LAST single quote
        of the statement, so apostrophes inside the value (French text) are
        kept as content instead of terminating the string."""

        def fix_statement(match: re.Match) -> str:
            statement = match.group(0)
            set_match = re.match(
                r"({%-?\s*set\s+\w+\s*=\s*)'(.*)'(\s*-?%})$", statement, flags=re.S
            )
            if not set_match:
                return statement
            value = set_match.group(2).replace('"', '\\"')
            return f'{set_match.group(1)}"{value}"{set_match.group(3)}'

        return re.sub(r"{%.*?%}", fix_statement, html, flags=re.S)

    def _sanitize_jinja_includes(self, blocks: list[dict]) -> list[dict]:
        """
        Sanitize Jinja {% include %} in innerHTML fields.
        - Converts AI shortcodes ({{ google_map ... }}) to valid Jinja includes
        - Strips escaped backslash-quotes from LLM output (\" → ")
        - Fixes wrong template paths and removes includes to non-existent templates.
        """
        import re

        include_pattern = re.compile(
            r"""{%[-\s]*include\s+['"]([^'"]+)['"]\s*[-\s]*%}"""
        )

        def sanitize_block(block: dict) -> bool:
            """Sanitize a block's innerHTML. Returns False if block should be removed."""
            inner = block.get("innerHTML", "")
            if not inner or ("{%" not in inner and "{{" not in inner):
                # Recurse into children
                if block.get("children"):
                    block["children"] = [
                        c for c in block["children"]
                        if not isinstance(c, dict) or sanitize_block(c)
                    ]
                return True

            # Fix escaped quotes from LLM JSON output (\" → ")
            if '\\"' in inner or "\\'" in inner:
                inner = inner.replace('\\"', '"').replace("\\'", "'")
                block["innerHTML"] = inner
                ai_log("info", "Fixed escaped quotes in Jinja innerHTML",
                       blockId=block.get("blockId"))

            # Convert shortcodes to valid Jinja includes
            if "google_map" in inner:
                converted = self._convert_shortcodes(inner)
                if converted != inner:
                    inner = converted
                    block["innerHTML"] = inner
                    ai_log("info", "Converted google_map shortcode to Jinja include",
                           blockId=block.get("blockId"))

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

    # Props that only make sense under `display: grid`. Kept in camelCase
    # because that's the format the AI outputs and the Builder frontend
    # uses internally (converted to kebab-case at CSS-serialise time).
    _GRID_ONLY_STYLE_KEYS = (
        "gridTemplateColumns",
        "gridTemplateRows",
        "gridTemplateAreas",
        "gridAutoColumns",
        "gridAutoRows",
        "gridAutoFlow",
        "gridArea",
        "gridColumn",
        "gridColumnStart",
        "gridColumnEnd",
        "gridRow",
        "gridRowStart",
        "gridRowEnd",
        "columnGap",
        "rowGap",
    )

    # Props that only make sense under `display: flex`. `gap`,
    # `justifyContent`, `alignItems`, `alignContent`, `placeItems`,
    # `placeContent` are intentionally absent — they work identically
    # in flex and grid.
    _FLEX_ONLY_STYLE_KEYS = (
        "flexDirection",
        "flexFlow",
        "flexWrap",
        "flexGrow",
        "flexShrink",
        "flexBasis",
        "order",
    )

    def _sanitize_layout_styles(self, blocks: list[dict]) -> list[dict]:
        """Strip style keys that contradict each block's display mode.

        The LLM sometimes mixes `display: flex` with `gridTemplateColumns`
        (or the reverse). The browser honours only one display value and
        silently drops the contradicting rules — visually the layout
        collapses. We enforce the contract here before the blocks are
        persisted as a Builder Page.

        Only `baseStyles` / `mobileStyles` / `tabletStyles` are touched.
        `rawStyles` (user-authored CSS overrides) is never modified.
        """
        stripped_total = 0

        def clean_style_dict(style_dict: dict, display: str | None) -> int:
            if not isinstance(style_dict, dict) or not display:
                return 0
            if display == "flex":
                unwanted = self._GRID_ONLY_STYLE_KEYS
            elif display == "grid":
                unwanted = self._FLEX_ONLY_STYLE_KEYS
            else:
                return 0
            removed = 0
            for key in unwanted:
                if key in style_dict:
                    del style_dict[key]
                    removed += 1
            return removed

        def walk(block: dict) -> None:
            nonlocal stripped_total
            base = block.get("baseStyles") or {}
            # Display may be declared on any breakpoint but the CRITICAL
            # cleanup target is whichever breakpoint sets display: we
            # strip contradicting props from that SAME breakpoint's dict.
            for key in ("baseStyles", "mobileStyles", "tabletStyles"):
                style_dict = block.get(key)
                if not isinstance(style_dict, dict):
                    continue
                # Effective display for this breakpoint = the one set on it,
                # falling back to baseStyles (breakpoint inheritance).
                display = style_dict.get("display") or base.get("display")
                stripped_total += clean_style_dict(style_dict, display)

            for child in block.get("children", []) or []:
                if isinstance(child, dict):
                    walk(child)

        for block in blocks:
            if isinstance(block, dict):
                walk(block)

        if stripped_total:
            ai_log("info", "Sanitized contradictory layout styles",
                   props_stripped=stripped_total)

        return blocks

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


class BriefComplianceChecker:
    """
    Post-generation checker that ensures all pages conform to the design brief.
    Runs after ALL pages are generated to fix cross-page inconsistencies,
    primarily hardcoded colors that don't match the brief palette.
    """

    def __init__(self, brief, primary_color: str, secondary_color: str):
        self.brief = brief
        self.primary = primary_color
        self.secondary = secondary_color
        self.primary_rgb = self._hex_to_rgb(primary_color) if primary_color else None
        self.secondary_rgb = self._hex_to_rgb(secondary_color) if secondary_color else None

    def check_and_fix(self, blocks: list[dict], page_title: str) -> tuple[list[dict], list[str]]:
        """Check blocks against brief and fix issues. Returns (fixed_blocks, list_of_fixes)."""
        fixes = []
        for block in blocks:
            self._fix_block(block, fixes)
        if fixes:
            ai_log("info", "Brief compliance fixes applied",
                   page=page_title, fix_count=len(fixes), fixes=fixes)
        return blocks, fixes

    def _fix_block(self, block: dict, fixes: list[str]) -> None:
        """Recursively check and fix a block's colors."""
        styles = block.get("baseStyles", {})
        bid = block.get("blockId", "?")

        # Check background and backgroundColor for hardcoded rgba colors
        for prop in ("background", "backgroundColor"):
            val = styles.get(prop, "")
            if not val or "rgba(" not in val:
                continue
            # Skip values that already use CSS variables
            if "var(--primary" in val or "var(--secondary" in val:
                continue
            fixed = self._fix_rgba_colors(val)
            if fixed != val:
                styles[prop] = fixed
                block["baseStyles"] = styles
                fixes.append(f"{bid}: {prop} colors aligned to brief")

        # Recurse into children
        for child in block.get("children", []):
            if isinstance(child, dict):
                self._fix_block(child, fixes)

    def _fix_rgba_colors(self, value: str) -> str:
        """Replace hardcoded rgba values with brief colors.

        In a gradient, the first color maps to primary, the second to secondary.
        Preserves alpha values. Only replaces colors that don't already match.
        """
        import re
        pattern = r'rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)'
        matches = list(re.finditer(pattern, value))

        if not matches or not self.primary_rgb:
            return value

        result = value
        # Process matches in reverse order to preserve string positions
        for i, match in enumerate(reversed(matches)):
            original_idx = len(matches) - 1 - i
            r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
            alpha = match.group(4)

            # Determine target color: first occurrence = primary, second = secondary
            if original_idx == 0:
                target = self.primary_rgb
            elif original_idx == 1 and self.secondary_rgb:
                target = self.secondary_rgb
            else:
                target = self.primary_rgb

            # Skip if already correct
            if (r, g, b) == target:
                continue

            # Skip near-black/white colors (likely intentional overlays, not theme colors)
            if r + g + b < 30 or r + g + b > 735:
                continue

            new_rgba = f"rgba({target[0]},{target[1]},{target[2]},{alpha})"
            result = result[:match.start()] + new_rgba + result[match.end():]

        return result

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        h = hex_color.lstrip("#")
        if len(h) < 6:
            return (0, 0, 0)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


__all__ = [
    "PageGenerator",
    "BriefComplianceChecker",
    "generate_page",
]
