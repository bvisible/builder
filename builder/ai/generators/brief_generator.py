"""
Brief Generator - Design Brief Generation for Site Consistency
Generates a design brief ONCE at the start, then used for ALL pages.
"""

from typing import Optional
import frappe

from builder.ai.config import get_ai_settings, AIConfig
from builder.ai.providers import get_provider
from builder.ai.design_system import get_theme
from builder.ai.schemas.design_brief import DesignBrief
from builder.ai.logging import ai_log


# Default fallback brief when generation fails
def get_default_brief(
    theme: str = "modern",
    primary_color: str = "#6366f1",
    secondary_color: str = "#8b5cf6",
) -> DesignBrief:
    """Get a default design brief based on theme."""
    theme_data = get_theme(theme)
    theme_colors = theme_data.get("colors", {})

    effective_primary = primary_color or theme_colors.get("primary", "#6366f1")
    effective_secondary = secondary_color or theme_colors.get("secondary", "#8b5cf6")

    # Theme-specific defaults
    theme_briefs = {
        "neobrutalist": {
            "site_tone": "bold",
            "border_radius_style": "none",
            "use_shadows": True,
            "use_gradients": False,
            "hero_style": "solid",
            "section_backgrounds": ["#ffffff", "#fef3c7", "#ffffff", effective_primary],
            "card_style": {
                "backgroundColor": "#ffffff",
                "borderRadius": "0",
                "boxShadow": "8px 8px 0 #000000",
                "padding": "24px",
                "border": "3px solid #000000",
            },
        },
        "glassmorphism": {
            "site_tone": "elegant",
            "border_radius_style": "rounded",
            "use_shadows": True,
            "use_gradients": True,
            "hero_style": "gradient",
            "card_style": {
                "backgroundColor": "rgba(255, 255, 255, 0.15)",
                "borderRadius": "16px",
                "boxShadow": "0 8px 32px rgba(0, 0, 0, 0.1)",
                "padding": "24px",
                "border": "1px solid rgba(255, 255, 255, 0.2)",
            },
        },
        "minimal": {
            "site_tone": "minimal",
            "border_radius_style": "subtle",
            "use_shadows": False,
            "use_gradients": False,
            "hero_style": "solid",
            "section_backgrounds": ["#ffffff", "#fafafa", "#ffffff", "#f5f5f5"],
            "card_style": {
                "backgroundColor": "#ffffff",
                "borderRadius": "4px",
                "boxShadow": "none",
                "padding": "24px",
                "border": "1px solid #e5e5e5",
            },
        },
        "corporate": {
            "site_tone": "professional",
            "border_radius_style": "subtle",
            "use_shadows": True,
            "use_gradients": False,
            "hero_style": "image",
        },
        "creative": {
            "site_tone": "playful",
            "border_radius_style": "rounded",
            "use_shadows": True,
            "use_gradients": True,
            "hero_style": "gradient",
        },
    }

    # Get theme-specific overrides
    overrides = theme_briefs.get(theme, {})

    # Build the brief
    brief_data = {
        "site_tone": overrides.get("site_tone", "professional"),
        "primary_usage": "CTA buttons, links, key highlights, icons",
        "secondary_usage": "Gradients, hover states, secondary accents",
        "section_backgrounds": overrides.get(
            "section_backgrounds",
            ["#ffffff", "#f8fafc", "#ffffff", effective_primary]
        ),
        "button_primary": {
            "backgroundColor": "var(--primary-color)",
            "color": "#ffffff",
            "padding": "14px 28px",
            "borderRadius": overrides.get("card_style", {}).get("borderRadius", "8px"),
            "fontWeight": "600",
            "border": "none",
            "cursor": "pointer",
        },
        "button_secondary": {
            "backgroundColor": "transparent",
            "color": "var(--primary-color)",
            "padding": "14px 28px",
            "borderRadius": overrides.get("card_style", {}).get("borderRadius", "8px"),
            "fontWeight": "600",
            "border": "2px solid var(--primary-color)",
            "cursor": "pointer",
        },
        "card_style": overrides.get("card_style", {
            "backgroundColor": "#ffffff",
            "borderRadius": "12px",
            "boxShadow": "0 4px 20px rgba(0, 0, 0, 0.08)",
            "padding": "24px",
            "border": "1px solid rgba(0, 0, 0, 0.05)",
        }),
        "hero_background": f"linear-gradient(135deg, {effective_primary} 0%, {effective_secondary} 100%)",
        "hero_text_color": "#ffffff",
        "hero_style": overrides.get("hero_style", "gradient"),
        "section_padding": "80px 24px",
        "section_padding_mobile": "48px 16px",
        "content_max_width": "1200px",
        "heading_color": "var(--text-color)",
        "body_color": "var(--muted-color)",
        "link_color": "var(--primary-color)",
        "use_shadows": overrides.get("use_shadows", True),
        "use_gradients": overrides.get("use_gradients", True),
        "border_radius_style": overrides.get("border_radius_style", "rounded"),
    }

    return DesignBrief(**brief_data)


BRIEF_SYSTEM_PROMPT = """You are a design system expert. Your task is to create a design brief that ensures visual consistency across a multi-page website.

The design brief defines:
1. How colors should be used (primary for CTAs, secondary for accents, etc.)
2. Section background alternation pattern for visual rhythm
3. Button and card styles
4. Hero section styling
5. Spacing and typography rules

Your brief will be used by another AI to generate multiple pages. The goal is that ALL pages look cohesive and part of the same site.

IMPORTANT RULES:
- Use CSS variable names like var(--primary-color) instead of actual hex values for primary/secondary colors
- Choose a background alternation pattern that creates visual rhythm (e.g., white → light gray → white → primary)
- Be specific about border-radius values and shadow intensities
- Consider the site type and theme when making decisions

CRITICAL - TEXT COLOR CONTRAST RULES:
- For hero_text_color: ONLY use "#ffffff" if hero_background is a gradient or colored background
- If hero is solid light color, hero_text_color MUST be "var(--text-color)"
- section_backgrounds with light colors (#ffffff, #f8fafc, #fafafa) → body_color: "var(--muted-color)", heading_color: "var(--text-color)"
- section_backgrounds with dark/colored backgrounds → text should be "#ffffff"
- NEVER create white text on white/light backgrounds!

Output a valid JSON object matching the DesignBrief schema.
"""


class BriefGenerator:
    """
    Generates a design brief for visual consistency across pages.
    Uses low temperature (0.4) for deterministic, consistent decisions.
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

        # Low temperature for consistent, deterministic decisions
        self.llm = get_provider(
            self.config.provider,
            model=self.config.model,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            temperature=0.4,  # Lower temperature for consistency
        )

    def generate_brief(
        self,
        prompt: str,
        site_name: str,
        site_type: str,
        theme: str = "modern",
        primary_color: str = None,
        secondary_color: str = None,
        pages_config: list[dict] = None,
    ) -> DesignBrief:
        """
        Generate a design brief for the site.

        Args:
            prompt: User's site description
            site_name: Name of the site
            site_type: Type of site (vitrine, ecommerce, etc.)
            theme: Visual theme name
            primary_color: Custom primary color
            secondary_color: Custom secondary color
            pages_config: List of pages that will be generated

        Returns:
            DesignBrief: Generated design brief
        """
        ai_log("info", "BriefGenerator.generate_brief() starting",
            site_name=site_name, site_type=site_type, theme=theme)

        # Get theme data
        theme_data = get_theme(theme)
        theme_name = theme_data.get("name", theme)
        theme_prompt = theme_data.get("prompt", "")
        theme_colors = theme_data.get("colors", {})

        effective_primary = primary_color or theme_colors.get("primary", "#6366f1")
        effective_secondary = secondary_color or theme_colors.get("secondary", "#8b5cf6")

        # Build user prompt
        pages_list = ""
        if pages_config:
            pages_list = "\n".join([f"- {p['title']} ({p['type']})" for p in pages_config])

        user_prompt = f"""Create a design brief for this website:

**Site Name:** {site_name}
**Site Type:** {site_type}
**Description:** {prompt}

**Theme:** {theme_name}
{theme_prompt}

**Colors:**
- Primary: {effective_primary}
- Secondary: {effective_secondary}

**Pages to generate:**
{pages_list}

Create a DesignBrief that ensures ALL these pages will look cohesive and part of the same site.
Focus on:
1. How to use the colors consistently
2. A section background alternation pattern
3. Consistent button and card styles
4. Hero styling that matches the theme
5. Appropriate spacing for the site type

Return ONLY the JSON object, no markdown code blocks.
"""

        try:
            # Try structured generation with high thinking for better creativity
            # Using "high" level for best creative decisions on design brief
            ai_log("debug", "Calling generate_structured for DesignBrief (think=high)")
            brief = self.llm.generate_structured(
                prompt=user_prompt,
                schema=DesignBrief,
                system_prompt=BRIEF_SYSTEM_PROMPT,
                think="high",  # High reasoning for best creative decisions on brief
            )
            ai_log("info", "Design brief generated successfully",
                site_tone=brief.site_tone, hero_style=brief.hero_style)
            return brief

        except Exception as e:
            # Fallback to default brief
            ai_log("warning", "Brief generation failed, using defaults", error=str(e)[:100])
            frappe.log_error("Brief generation failed", str(e))
            return get_default_brief(
                theme=theme,
                primary_color=effective_primary,
                secondary_color=effective_secondary,
            )


__all__ = ["BriefGenerator", "get_default_brief"]
