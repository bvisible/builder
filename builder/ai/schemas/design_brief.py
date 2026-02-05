"""
Design Brief Schema for AI Site Generation
Ensures visual consistency across all generated pages.
"""

from __future__ import annotations
import json
from typing import Literal, Optional
from pydantic import BaseModel, Field


class TypographyScale(BaseModel):
    """Typography scale for consistent sizing across all pages."""
    h1_size: str = Field(default="48px", description="H1 font size desktop")
    h1_size_mobile: str = Field(default="32px", description="H1 font size mobile")
    h1_weight: str = Field(default="700", description="H1 font weight")
    h1_line_height: str = Field(default="1.2", description="H1 line height")

    h2_size: str = Field(default="36px", description="H2 font size desktop")
    h2_size_mobile: str = Field(default="26px", description="H2 font size mobile")
    h2_weight: str = Field(default="600", description="H2 font weight")
    h2_line_height: str = Field(default="1.25", description="H2 line height")

    h3_size: str = Field(default="24px", description="H3 font size desktop")
    h3_size_mobile: str = Field(default="20px", description="H3 font size mobile")
    h3_weight: str = Field(default="600", description="H3 font weight")

    body_size: str = Field(default="16px", description="Body font size desktop")
    body_size_mobile: str = Field(default="15px", description="Body font size mobile")
    body_line_height: str = Field(default="1.6", description="Body line height")

    class Config:
        extra = "ignore"


class SectionHeights(BaseModel):
    """Mandatory section heights for consistency."""
    hero_min_height: str = Field(default="90vh", description="Hero minimum height desktop")
    hero_min_height_mobile: str = Field(default="70vh", description="Hero minimum height mobile")
    standard_min_height: str = Field(default="auto", description="Standard section min height")

    class Config:
        extra = "ignore"


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

    # NEW: Typography Scale (prescriptive sizes)
    typography: TypographyScale = Field(
        default_factory=TypographyScale,
        description="Typography scale for consistent sizing"
    )

    # NEW: Font families
    heading_font: str = Field(
        default="Inter",
        description="Font family for headings (h1-h6)"
    )
    body_font: str = Field(
        default="Inter",
        description="Font family for body text"
    )

    # NEW: Section Heights
    section_heights: SectionHeights = Field(
        default_factory=SectionHeights,
        description="Section height constraints"
    )

    # NEW: Padding by section type
    section_paddings: dict = Field(
        default_factory=lambda: {
            "hero": "100px 24px",
            "standard": "80px 24px",
            "compact": "60px 24px",
            "cta": "60px 24px",
        },
        description="Padding values per section type"
    )

    # NEW: Dark background detection pattern
    dark_background_threshold: str = Field(
        default="gradient|primary|secondary|#[0-5]",
        description="Regex pattern for dark backgrounds requiring white text"
    )

    # Typography colors
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
        """Convert to a prescriptive prompt section for the AI."""
        bg_sequence = " → ".join(self.section_backgrounds)
        typo = self.typography
        heights = self.section_heights
        paddings = self.section_paddings

        return f"""## DESIGN BRIEF (MANDATORY - COPY THESE VALUES EXACTLY)

### Site Tone: {self.site_tone}

### TYPOGRAPHY (MANDATORY - USE THESE EXACT VALUES)
| Element | Desktop | Mobile | Weight | Line Height |
|---------|---------|--------|--------|-------------|
| h1 | {typo.h1_size} | {typo.h1_size_mobile} | {typo.h1_weight} | {typo.h1_line_height} |
| h2 | {typo.h2_size} | {typo.h2_size_mobile} | {typo.h2_weight} | {typo.h2_line_height} |
| h3 | {typo.h3_size} | {typo.h3_size_mobile} | {typo.h3_weight} | 1.3 |
| p  | {typo.body_size} | {typo.body_size_mobile} | 400 | {typo.body_line_height} |

### FONTS (MANDATORY - ALWAYS INCLUDE IN baseStyles)
- Headings (h1-h6): fontFamily: "'{self.heading_font}', sans-serif"
- Body (p, span, li): fontFamily: "'{self.body_font}', sans-serif"
⚠️ ALWAYS include fontFamily in baseStyles for h1, h2, h3, h4, p, span elements!

### SECTION HEIGHTS (MANDATORY)
| Type | minHeight Desktop | minHeight Mobile |
|------|-------------------|------------------|
| Hero | {heights.hero_min_height} | {heights.hero_min_height_mobile} |
| Standard | {heights.standard_min_height} | auto |

### SECTION PADDINGS BY TYPE
| Type | Desktop | Mobile |
|------|---------|--------|
| Hero | {paddings.get('hero', '100px 24px')} | 60px 16px |
| Standard | {paddings.get('standard', '80px 24px')} | 48px 16px |
| Compact | {paddings.get('compact', '60px 24px')} | 40px 16px |
| CTA | {paddings.get('cta', '60px 24px')} | 40px 16px |

### Color Usage
- **Primary color**: {self.primary_usage}
- **Secondary color**: {self.secondary_usage}

### Section Background Alternation (use in this order)
{bg_sequence}

### Button Styles (COPY EXACTLY)
Primary: {json.dumps(self.button_primary)}
Secondary: {json.dumps(self.button_secondary)}

### Card Style
- background={self.card_style.get('backgroundColor')}
- borderRadius={self.card_style.get('borderRadius')}
- boxShadow={self.card_style.get('boxShadow')}

### Hero Section
- Background: {self.hero_background}
- Text color: {self.hero_text_color}
- Style: {self.hero_style}
- minHeight: {heights.hero_min_height} (mobile: {heights.hero_min_height_mobile})

### Spacing
- Content max-width: {self.content_max_width}

### Typography Colors
- Headings: {self.heading_color}
- Body text: {self.body_color}
- Links: {self.link_color}

### TEXT COLOR CONTRAST (CRITICAL - NEVER VIOLATE!)
Apply these rules for EVERY section based on its background:
| Background | Text Color |
|------------|------------|
| Gradient or colored (primary/secondary) | "#ffffff" |
| #ffffff (white) | "var(--text-color)" |
| #f8fafc, #fafafa, #f5f5f5 (light gray) | "var(--text-color)" |
| var(--surface-color) | "var(--text-color)" |

⚠️ NEVER use white text (#ffffff) on white or light gray backgrounds!
⚠️ ALWAYS check parent background before setting text color!

### Visual Effects
- Shadows: {"Yes" if self.use_shadows else "No"}
- Gradients: {"Yes" if self.use_gradients else "No"}
- Border radius: {self.border_radius_style} ({self.get_border_radius()})
{self._get_inspiration_section()}
**CRITICAL**: Apply these EXACT values CONSISTENTLY across ALL pages and sections.
Every page MUST have the same hero minHeight, typography scale, and fonts.
"""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()

    class Config:
        extra = "ignore"


__all__ = ["DesignBrief", "TypographyScale", "SectionHeights"]
