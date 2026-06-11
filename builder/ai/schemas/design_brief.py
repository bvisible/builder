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
    """Suggested section heights - AI has freedom to adapt."""
    hero_min_height: Optional[str] = Field(default=None, description="Hero minimum height desktop (suggested)")
    hero_min_height_mobile: Optional[str] = Field(default=None, description="Hero minimum height mobile (suggested)")
    standard_min_height: str = Field(default="auto", description="Standard section min height")

    class Config:
        extra = "ignore"


class DesignBrief(BaseModel):
    """
    Design brief for visual consistency across pages.
    Generated ONCE at the start, then used for ALL page generations.
    """
    # Art direction — the creative core of the brief. Written by the brief LLM,
    # injected verbatim at the top of every page-generation prompt.
    design_concept: str = Field(
        default="",
        description=(
            "3-5 sentence art direction for this specific site: the chosen aesthetic "
            "direction (e.g. editorial/magazine, luxury/refined, brutalist/raw...), the "
            "atmosphere, how color and typography carry the brand, what makes it distinctive."
        ),
    )
    signature_element: str = Field(
        default="",
        description=(
            "ONE memorable visual idea carried across all pages: an oversized display "
            "headline treatment, a recurring graphic motif, an unexpected accent color "
            "usage, a distinctive section rhythm or image treatment."
        ),
    )

    # Site tone
    site_tone: Literal["professional", "playful", "elegant", "bold", "minimal"] = Field(
        default="professional",
        description="Overall tone of the site"
    )

    # Actual colors (stored for consistency across pages)
    primary_color: str = Field(
        default="#6366f1",
        description="Primary color hex value chosen for this site"
    )
    secondary_color: str = Field(
        default="#8b5cf6",
        description="Secondary color hex value chosen for this site"
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

    # Hero section. No gradient default: the brief LLM must make a deliberate
    # choice per site (empty values are filled by get_default_brief's varied
    # fallback, never by a hardcoded gradient).
    hero_background: str = Field(
        default="",
        description="Hero section background (a deliberate choice — solid, image treatment, dark field...)"
    )
    hero_text_color: str = Field(
        default="",
        description="Hero section text color (must contrast with hero_background)"
    )
    hero_style: Literal[
        "image",        # Image with a deliberate treatment (solid overlay, duotone, scrim)
        "split",        # Split layout (image + text, 60/40, 70/30...)
        "minimal",      # Typography-led, generous space
        "solid",        # Solid color field
        "asymmetric",   # Off-center/overlapping composition
        "cards",        # Content cards integrated in the hero
        "gradient",     # Only as a deliberate, characterful choice
    ] = Field(
        default="split",
        description="Hero composition — choose what serves THIS site's direction"
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

    # NEW: Font families (empty defaults — chosen per site by the brief LLM or
    # the varied theme fallback, never a hardcoded generic face)
    heading_font: str = Field(
        default="",
        description="Distinctive Google Font for headings — characterful, fits the art direction"
    )
    body_font: str = Field(
        default="",
        description="Readable Google Font for body text, pairs with heading_font"
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

    # Site chrome — the locked, site-wide header/footer take their design from
    # the brief (applied to Website Header Footer Config by the worker).
    header_bg_color: str = Field(
        default="#ffffff",
        description="Header background color — MUST be chosen based on logo analysis if logo is provided. Use white (#ffffff) for dark logos, dark for light logos. Must ensure logo readability."
    )
    header_text_color: str = Field(
        default="#1a1a1a",
        description="Header text color — MUST contrast with header_bg_color. Use dark text (#1a1a1a) on light header, white (#ffffff) on dark header."
    )
    header_height: Literal["Standard", "Slim", "Tall"] = Field(
        default="Standard",
        description="Header bar height — Slim (56px) reads refined/editorial, Tall (76px) reads bold"
    )
    header_border: Literal["None", "Subtle"] = Field(
        default="Subtle",
        description="Fine separation line under the header — Subtle or None"
    )
    cta_style: Literal["Primary", "Secondary", "Outline"] = Field(
        default="Primary",
        description="Header CTA fill: Primary (solid accent), Secondary, Outline (border only — refined)"
    )
    cta_shape: Literal["Rounded", "Pill", "Square"] = Field(
        default="Rounded",
        description="Header CTA shape: Pill (soft/refined), Rounded, Square (editorial/brutalist)"
    )
    cta_size: Literal["Medium", "Small"] = Field(
        default="Small",
        description="Header CTA size — Small reads discreet and refined"
    )
    footer_template: Literal["Minimal", "Standard", "Extended"] = Field(
        default="Standard",
        description="Footer density — Minimal (one line), Standard, Extended (rich columns)"
    )
    footer_bg_color: str = Field(
        default="",
        description="Footer background — often a deep field of the palette or the surface tone"
    )
    footer_text_color: str = Field(
        default="",
        description="Footer text color — must contrast with footer_bg_color"
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
        """Convert to a suggestive prompt section for the AI - guidelines not mandates."""
        bg_sequence = " → ".join(self.section_backgrounds)
        typo = self.typography
        heights = self.section_heights
        paddings = self.section_paddings

        # Heights section - recommend minHeight for heroes
        heights_section = """
### Section Heights
- Hero sections: use minHeight "70vh" to "90vh" for visual impact
- Other sections: let content determine height naturally
- Use generous padding (80px-120px) for comfortable spacing
"""

        concept_section = ""
        if self.design_concept:
            concept_section = f"""### ART DIRECTION (follow this — it defines the site)
{self.design_concept}
"""
        if self.signature_element:
            concept_section += f"""
### SIGNATURE ELEMENT (must appear, consistently, on every page)
{self.signature_element}
"""

        return f"""## DESIGN BRIEF
{concept_section}
### Site Tone: {self.site_tone}

### Typography suggestions
Consider these sizes, but feel free to adapt:
| Element | Desktop | Mobile | Weight |
|---------|---------|--------|--------|
| h1 | ~{typo.h1_size} | ~{typo.h1_size_mobile} | {typo.h1_weight} |
| h2 | ~{typo.h2_size} | ~{typo.h2_size_mobile} | {typo.h2_weight} |
| h3 | ~{typo.h3_size} | ~{typo.h3_size_mobile} | {typo.h3_weight} |
| p  | ~{typo.body_size} | ~{typo.body_size_mobile} | 400 |

### Fonts
- Headings: consider "{self.heading_font}" or similar
- Body: consider "{self.body_font}"
- Include fontFamily in baseStyles for text elements
{heights_section}
### Section Paddings (suggestions)
| Type | Desktop | Mobile |
|------|---------|--------|
| Hero | ~{paddings.get('hero', '100px 24px')} | ~60px 16px |
| Standard | ~{paddings.get('standard', '80px 24px')} | ~48px 16px |

### Color Usage
- **Primary color**: {self.primary_usage}
- **Secondary color**: {self.secondary_usage}

### Section Background Alternation (suggested pattern)
{bg_sequence}

### Button Styles (suggested)
Primary: {json.dumps(self.button_primary)}
Secondary: {json.dumps(self.button_secondary)}

### Card Style (suggested)
- background: {self.card_style.get('backgroundColor')}
- borderRadius: {self.card_style.get('borderRadius')}
- boxShadow: {self.card_style.get('boxShadow')}

### Hero Section
- Background: {self.hero_background}
- Text color: {self.hero_text_color}
- Style: {self.hero_style}

### Typography Colors
- Headings: {self.heading_color}
- Body text: {self.body_color}
- Links: {self.link_color}

### TEXT CONTRAST (CRITICAL - always follow!)
| Background | Text Color |
|------------|------------|
| Gradient or colored (primary/secondary) | "#ffffff" |
| White (#ffffff) | "var(--text-color)" |
| Light gray (#f8fafc, #fafafa, #f5f5f5) | "var(--text-color)" |

⚠️ NEVER use white text on white or light backgrounds!

### Visual Effects
- Shadows: {"Yes" if self.use_shadows else "No"}
- Gradients: {"Yes" if self.use_gradients else "No"}
- Border radius: {self.border_radius_style} ({self.get_border_radius()})
{self._get_inspiration_section()}
Use these as guidelines for visual consistency while exercising creative freedom.
"""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()

    def get_missing_fields(self) -> list[str]:
        """
        Return list of fields that are still at default values.
        Useful for checking if AI properly filled all fields.
        """
        defaults = DesignBrief()
        missing = []

        # Fonts are pre-selected by theme, no need to check for defaults

        # Check hero fields
        if self.hero_background == defaults.hero_background:
            missing.append("hero_background")
        if self.hero_text_color == defaults.hero_text_color:
            missing.append("hero_text_color")

        # Check button styles (compare backgroundColor)
        if self.button_primary.get("backgroundColor") == defaults.button_primary.get("backgroundColor"):
            missing.append("button_primary")

        # Check section paddings
        if self.section_paddings == defaults.section_paddings:
            missing.append("section_paddings")

        return missing

    def merge_with_defaults(self, defaults: "DesignBrief") -> "DesignBrief":
        """
        Merge this brief with defaults, filling in missing values.
        Returns a new DesignBrief with all fields populated.
        """
        data = self.model_dump()
        defaults_data = defaults.model_dump()

        # Merge missing/empty string fields
        for field in ["heading_font", "body_font", "hero_background", "hero_text_color"]:
            if not data.get(field) or data.get(field) == "":
                data[field] = defaults_data[field]

        # Merge incomplete dict fields
        for field in ["button_primary", "button_secondary", "card_style", "section_paddings"]:
            if not data.get(field) or not isinstance(data.get(field), dict):
                data[field] = defaults_data[field]
            else:
                # Fill missing keys
                for key, value in defaults_data.get(field, {}).items():
                    if key not in data[field] or not data[field][key]:
                        data[field][key] = value

        # Merge typography if needed
        if data.get("typography"):
            typo_data = data["typography"]
            typo_defaults = defaults_data.get("typography", {})
            for key, value in typo_defaults.items():
                if key not in typo_data or not typo_data[key]:
                    typo_data[key] = value
            data["typography"] = typo_data

        return DesignBrief(**data)

    class Config:
        extra = "ignore"


__all__ = ["DesignBrief", "TypographyScale", "SectionHeights"]
