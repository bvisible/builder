"""
Design Brief Schema for AI Site Generation
Ensures visual consistency across all generated pages.
"""

from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field


class DesignBrief(BaseModel):
    """
    Design brief for visual consistency across pages.
    Generated ONCE at the start, then used for ALL page generations.
    """
    # Site tone
    site_tone: Literal["professional", "playful", "elegant", "bold", "minimal"] = Field(
        default="professional",
        description="Overall tone of the site"
    )

    # Color usage rules
    primary_usage: str = Field(
        default="CTA buttons, links, icons, key highlights",
        description="How to use the primary color"
    )
    secondary_usage: str = Field(
        default="Gradients, hover states, secondary accents, badges",
        description="How to use the secondary color"
    )

    # Section background alternation pattern
    section_backgrounds: list[str] = Field(
        default_factory=lambda: ["#ffffff", "#f8fafc", "#ffffff", "var(--primary-color)"],
        description="Ordered list of backgrounds to alternate between sections"
    )

    # Button styles (CSS camelCase)
    button_primary: dict = Field(
        default_factory=lambda: {
            "backgroundColor": "var(--primary-color)",
            "color": "#ffffff",
            "padding": "14px 28px",
            "borderRadius": "8px",
            "fontWeight": "600",
            "border": "none",
            "cursor": "pointer",
        },
        description="Primary button styles"
    )
    button_secondary: dict = Field(
        default_factory=lambda: {
            "backgroundColor": "transparent",
            "color": "var(--primary-color)",
            "padding": "14px 28px",
            "borderRadius": "8px",
            "fontWeight": "600",
            "border": "2px solid var(--primary-color)",
            "cursor": "pointer",
        },
        description="Secondary/outline button styles"
    )

    # Card styles
    card_style: dict = Field(
        default_factory=lambda: {
            "backgroundColor": "#ffffff",
            "borderRadius": "12px",
            "boxShadow": "0 4px 20px rgba(0, 0, 0, 0.08)",
            "padding": "24px",
            "border": "1px solid rgba(0, 0, 0, 0.05)",
        },
        description="Card container styles"
    )

    # Hero section
    hero_background: str = Field(
        default="linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%)",
        description="Hero section background"
    )
    hero_text_color: str = Field(
        default="#ffffff",
        description="Hero section text color"
    )
    hero_style: Literal[
        "gradient",     # Gradient background (primary → secondary)
        "image",        # Background image with overlay
        "solid",        # Solid color background
        "split",        # Split layout 50/50 (image + text)
        "minimal",      # Typography-focused, no image
        "cards",        # Hero with mini-cards integrated
        "asymmetric",   # Artistic off-center layout
    ] = Field(
        default="gradient",
        description="Hero visual style"
    )

    # Spacing
    section_padding: str = Field(
        default="80px 24px",
        description="Desktop section padding"
    )
    section_padding_mobile: str = Field(
        default="48px 16px",
        description="Mobile section padding"
    )
    content_max_width: str = Field(
        default="1200px",
        description="Maximum content width"
    )

    # Typography
    heading_color: str = Field(
        default="var(--text-color)",
        description="Heading text color"
    )
    body_color: str = Field(
        default="var(--muted-color)",
        description="Body text color"
    )
    link_color: str = Field(
        default="var(--primary-color)",
        description="Link text color"
    )

    # Visual effects
    use_shadows: bool = Field(
        default=True,
        description="Use box shadows on cards/elements"
    )
    use_gradients: bool = Field(
        default=True,
        description="Use gradients for backgrounds/buttons"
    )
    border_radius_style: Literal["none", "subtle", "rounded", "pill"] = Field(
        default="rounded",
        description="Border radius style"
    )

    # Inspiration context (from user-provided reference sites/images)
    inspiration_context: Optional[str] = Field(
        default=None,
        description="Context from inspiration sources (liked/disliked colors, styles)"
    )
    colors_to_avoid: Optional[list[str]] = Field(
        default=None,
        description="Colors to avoid based on disliked inspirations"
    )

    def get_border_radius(self) -> str:
        """Get border radius value based on style."""
        radii = {
            "none": "0",
            "subtle": "4px",
            "rounded": "12px",
            "pill": "9999px",
        }
        return radii.get(self.border_radius_style, "12px")

    def _get_inspiration_section(self) -> str:
        """Get inspiration context section for prompt."""
        parts = []

        if self.inspiration_context:
            parts.append(f"\n### User Inspiration Context\n{self.inspiration_context}")

        if self.colors_to_avoid:
            colors_str = ", ".join(self.colors_to_avoid[:5])
            parts.append(f"\n### Colors to AVOID\n{colors_str}")

        if parts:
            return "\n".join(parts) + "\n"
        return ""

    def to_prompt_section(self) -> str:
        """Convert to a prompt section for the AI."""
        bg_sequence = " → ".join(self.section_backgrounds)

        return f"""## DESIGN BRIEF (MANDATORY - FOLLOW EXACTLY)

### Site Tone: {self.site_tone}

### Color Usage
- **Primary color**: {self.primary_usage}
- **Secondary color**: {self.secondary_usage}

### Section Background Alternation (use in this order)
{bg_sequence}

### Button Styles
- **Primary Button**: background={self.button_primary.get('backgroundColor')}, color={self.button_primary.get('color')}, borderRadius={self.button_primary.get('borderRadius')}
- **Secondary Button**: background={self.button_secondary.get('backgroundColor')}, color={self.button_secondary.get('color')}, border={self.button_secondary.get('border')}

### Card Style
- background={self.card_style.get('backgroundColor')}
- borderRadius={self.card_style.get('borderRadius')}
- boxShadow={self.card_style.get('boxShadow')}

### Hero Section
- Background: {self.hero_background}
- Text color: {self.hero_text_color}
- Style: {self.hero_style}

### Spacing
- Section padding: {self.section_padding} (mobile: {self.section_padding_mobile})
- Content max-width: {self.content_max_width}

### Typography
- Headings: {self.heading_color}
- Body text: {self.body_color}
- Links: {self.link_color}

### TEXT COLOR CONTRAST (CRITICAL!)
Apply these rules for EVERY section based on its background:
| Background | Text Color |
|------------|------------|
| Gradient or colored (primary/secondary) | "#ffffff" |
| #ffffff (white) | "var(--text-color)" |
| #f8fafc, #fafafa, #f5f5f5 (light gray) | "var(--text-color)" |
| var(--surface-color) | "var(--text-color)" |

⚠️ NEVER use white text (#ffffff) on white or light gray backgrounds!

### Visual Effects
- Shadows: {"Yes" if self.use_shadows else "No"}
- Gradients: {"Yes" if self.use_gradients else "No"}
- Border radius: {self.border_radius_style} ({self.get_border_radius()})
{self._get_inspiration_section()}
**IMPORTANT**: Apply these styles CONSISTENTLY across ALL pages and sections.
"""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()

    class Config:
        extra = "ignore"


__all__ = ["DesignBrief"]
