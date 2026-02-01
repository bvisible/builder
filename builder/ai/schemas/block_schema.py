"""
Frappe Builder Block Schemas
Pydantic models for structured AI output that matches Frappe Builder's block format.
"""

from __future__ import annotations
from typing import Optional, Literal, Any
from pydantic import BaseModel, Field, field_validator
import uuid


# Supported HTML elements in Frappe Builder
ElementType = Literal[
    # Structural
    "div", "section", "article", "aside", "main", "header", "footer", "nav",
    # Text
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "span", "label", "blockquote",
    # Links & Buttons
    "a", "button",
    # Media
    "img", "video", "iframe",
    # Lists
    "ul", "ol", "li",
    # Forms
    "form", "input", "textarea", "select", "option",
    # Other
    "hr", "br", "figure", "figcaption",
]

# Section types for page structure analysis
SectionType = Literal[
    "header", "hero", "features", "about", "services", "testimonials",
    "pricing", "team", "portfolio", "gallery", "blog", "contact",
    "cta", "faq", "stats", "clients", "newsletter", "footer", "custom"
]


class BlockDataKey(BaseModel):
    """Data binding configuration for dynamic content"""
    key: str = Field(description="Data key path (e.g., 'item.title')")
    property: str = Field(default="innerHTML", description="Block property to bind")
    type: str = Field(default="text", description="Data type (text, attribute, style)")


class FrappeStyles(BaseModel):
    """
    CSS styles in camelCase format for Frappe Builder.
    All properties are optional to allow flexible styling.
    """
    # Display & Layout
    display: Optional[str] = None
    flexDirection: Optional[str] = None
    flexWrap: Optional[str] = None
    alignItems: Optional[str] = None
    justifyContent: Optional[str] = None
    gap: Optional[str] = None
    gridTemplateColumns: Optional[str] = None
    gridTemplateRows: Optional[str] = None
    position: Optional[str] = None
    top: Optional[str] = None
    right: Optional[str] = None
    bottom: Optional[str] = None
    left: Optional[str] = None
    zIndex: Optional[str] = None

    # Sizing
    width: Optional[str] = None
    minWidth: Optional[str] = None
    maxWidth: Optional[str] = None
    height: Optional[str] = None
    minHeight: Optional[str] = None
    maxHeight: Optional[str] = None

    # Spacing
    padding: Optional[str] = None
    paddingTop: Optional[str] = None
    paddingRight: Optional[str] = None
    paddingBottom: Optional[str] = None
    paddingLeft: Optional[str] = None
    margin: Optional[str] = None
    marginTop: Optional[str] = None
    marginRight: Optional[str] = None
    marginBottom: Optional[str] = None
    marginLeft: Optional[str] = None

    # Colors & Background
    color: Optional[str] = None
    backgroundColor: Optional[str] = None
    backgroundImage: Optional[str] = None
    backgroundSize: Optional[str] = None
    backgroundPosition: Optional[str] = None
    backgroundRepeat: Optional[str] = None
    opacity: Optional[str] = None

    # Typography
    fontSize: Optional[str] = None
    fontWeight: Optional[str] = None
    fontFamily: Optional[str] = None
    fontStyle: Optional[str] = None
    lineHeight: Optional[str] = None
    letterSpacing: Optional[str] = None
    textAlign: Optional[str] = None
    textDecoration: Optional[str] = None
    textTransform: Optional[str] = None

    # Borders
    border: Optional[str] = None
    borderTop: Optional[str] = None
    borderRight: Optional[str] = None
    borderBottom: Optional[str] = None
    borderLeft: Optional[str] = None
    borderRadius: Optional[str] = None
    borderColor: Optional[str] = None
    borderWidth: Optional[str] = None
    borderStyle: Optional[str] = None

    # Effects
    boxShadow: Optional[str] = None
    textShadow: Optional[str] = None
    transform: Optional[str] = None
    transition: Optional[str] = None
    overflow: Optional[str] = None
    overflowX: Optional[str] = None
    overflowY: Optional[str] = None

    # Flex item properties
    flex: Optional[str] = None
    flexGrow: Optional[str] = None
    flexShrink: Optional[str] = None
    flexBasis: Optional[str] = None
    alignSelf: Optional[str] = None
    order: Optional[str] = None

    # Cursor & Interaction
    cursor: Optional[str] = None
    pointerEvents: Optional[str] = None
    userSelect: Optional[str] = None

    # Other
    objectFit: Optional[str] = None
    objectPosition: Optional[str] = None
    aspectRatio: Optional[str] = None
    filter: Optional[str] = None
    backdropFilter: Optional[str] = None
    clipPath: Optional[str] = None

    class Config:
        extra = "allow"  # Allow additional CSS properties

    def to_dict(self) -> dict:
        """Convert to dict, excluding None values"""
        return {k: v for k, v in self.model_dump().items() if v is not None}


class FrappeBlock(BaseModel):
    """
    Frappe Builder Block schema.
    This is the core structure that the AI must generate.
    """
    blockId: str = Field(
        default_factory=lambda: f"block-{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the block (format: type-xxx)"
    )
    element: ElementType = Field(
        default="div",
        description="HTML element type"
    )
    innerHTML: Optional[str] = Field(
        default=None,
        description="Text content of the block (for text elements)"
    )
    innerText: Optional[str] = Field(
        default=None,
        description="Plain text content (alternative to innerHTML)"
    )
    baseStyles: FrappeStyles = Field(
        default_factory=FrappeStyles,
        description="Desktop styles (default breakpoint)"
    )
    mobileStyles: FrappeStyles = Field(
        default_factory=FrappeStyles,
        description="Mobile styles (< 576px)"
    )
    tabletStyles: FrappeStyles = Field(
        default_factory=FrappeStyles,
        description="Tablet styles (576px - 1024px)"
    )
    rawStyles: Optional[dict] = Field(
        default=None,
        description="Raw CSS that bypasses camelCase conversion"
    )
    attributes: Optional[dict[str, Any]] = Field(
        default=None,
        description="HTML attributes (href, src, alt, etc.)"
    )
    classes: Optional[list[str]] = Field(
        default=None,
        description="CSS classes to apply"
    )
    children: list["FrappeBlock"] = Field(
        default_factory=list,
        description="Nested child blocks"
    )
    blockName: Optional[str] = Field(
        default=None,
        description="Human-readable name for the block"
    )
    dataKey: Optional[BlockDataKey] = Field(
        default=None,
        description="Dynamic data binding configuration"
    )
    visibilityCondition: Optional[str] = Field(
        default=None,
        description="Jinja2 condition for conditional rendering"
    )
    isRepeaterBlock: bool = Field(
        default=False,
        description="Whether this block repeats over data"
    )
    extendedFromComponent: Optional[str] = Field(
        default=None,
        description="Component ID if this block extends a component"
    )

    @field_validator("blockId", mode="before")
    @classmethod
    def ensure_block_id(cls, v):
        """Ensure blockId is always set"""
        if not v:
            return f"block-{uuid.uuid4().hex[:8]}"
        return v

    def to_dict(self) -> dict:
        """Convert to Frappe Builder compatible dict"""
        result = {
            "blockId": self.blockId,
            "element": self.element,
        }

        if self.innerHTML:
            result["innerHTML"] = self.innerHTML
        if self.innerText:
            result["innerText"] = self.innerText
        if self.baseStyles:
            styles = self.baseStyles.to_dict()
            if styles:
                result["baseStyles"] = styles
        if self.mobileStyles:
            styles = self.mobileStyles.to_dict()
            if styles:
                result["mobileStyles"] = styles
        if self.tabletStyles:
            styles = self.tabletStyles.to_dict()
            if styles:
                result["tabletStyles"] = styles
        if self.rawStyles:
            result["rawStyles"] = self.rawStyles
        if self.attributes:
            result["attributes"] = self.attributes
        if self.classes:
            result["classes"] = self.classes
        if self.children:
            result["children"] = [child.to_dict() for child in self.children]
        if self.blockName:
            result["blockName"] = self.blockName
        if self.dataKey:
            result["dataKey"] = self.dataKey.model_dump()
        if self.visibilityCondition:
            result["visibilityCondition"] = self.visibilityCondition
        if self.isRepeaterBlock:
            result["isRepeaterBlock"] = self.isRepeaterBlock
        if self.extendedFromComponent:
            result["extendedFromComponent"] = self.extendedFromComponent

        return result

    class Config:
        extra = "ignore"


# Rebuild model to resolve forward references
FrappeBlock.model_rebuild()


class SectionInfo(BaseModel):
    """Information about a page section for structure analysis"""
    type: SectionType = Field(description="Type of section")
    title: Optional[str] = Field(default=None, description="Section title/heading")
    description: Optional[str] = Field(default=None, description="Brief description of section content")
    priority: int = Field(default=5, ge=1, le=10, description="Importance (1-10)")
    estimated_blocks: int = Field(default=3, ge=1, le=20, description="Estimated number of blocks")


class PageStructure(BaseModel):
    """Page structure analysis result"""
    page_type: str = Field(description="Type of page (landing, about, contact, etc.)")
    theme_suggestion: Optional[str] = Field(default=None, description="Suggested visual theme")
    sections: list[SectionInfo] = Field(
        default_factory=list,
        description="List of sections to generate"
    )
    header_type: Optional[str] = Field(default="multi_page", description="Header type to use")
    footer_type: Optional[str] = Field(default="standard", description="Footer type to use")
    color_scheme: Optional[dict] = Field(default=None, description="Suggested color scheme")
    total_estimated_blocks: int = Field(default=10, description="Total estimated blocks")

    def get_sections_by_priority(self) -> list[SectionInfo]:
        """Get sections sorted by priority (highest first)"""
        return sorted(self.sections, key=lambda s: s.priority, reverse=True)


class GeneratedPage(BaseModel):
    """Complete generated page with all blocks"""
    name: str = Field(description="Page name/title")
    route: str = Field(description="URL route for the page")
    blocks: list[FrappeBlock] = Field(default_factory=list)
    meta: Optional[dict] = Field(default=None, description="Page metadata")

    def to_frappe_format(self) -> dict:
        """Convert to Frappe Builder page format"""
        return {
            "page_name": self.name,
            "route": self.route,
            "blocks": [block.to_dict() for block in self.blocks],
        }


# =============================================================================
# SECTION CONTENT SCHEMAS
# These schemas define only the CONTENT that AI should generate.
# The structure comes from templates.
# =============================================================================

class HeroContent(BaseModel):
    """Content for hero section"""
    badge: Optional[str] = Field(default=None, description="Small badge text above headline (e.g., 'New', '2024 Launch')")
    headline: str = Field(description="Main headline (short, impactful)")
    subheadline: str = Field(description="Supporting text (1-2 sentences)")
    primary_cta_text: str = Field(default="Get Started", description="Primary button text")
    primary_cta_url: str = Field(default="#", description="Primary button URL")
    secondary_cta_text: Optional[str] = Field(default=None, description="Secondary button text")
    secondary_cta_url: Optional[str] = Field(default=None, description="Secondary button URL")
    image_url: Optional[str] = Field(default=None, description="Hero image URL")
    image_alt: Optional[str] = Field(default=None, description="Hero image alt text")


class FeatureItem(BaseModel):
    """Single feature item"""
    icon: str = Field(default="✨", description="Emoji or icon character")
    title: str = Field(description="Feature title (2-4 words)")
    description: str = Field(description="Feature description (1-2 sentences)")


class FeaturesContent(BaseModel):
    """Content for features section"""
    section_title: str = Field(default="Why Choose Us", description="Section heading")
    section_description: Optional[str] = Field(default=None, description="Section intro text")
    features: list[FeatureItem] = Field(default_factory=list, min_length=0, max_length=6, description="List of features")


class TestimonialItem(BaseModel):
    """Single testimonial"""
    quote: str = Field(description="The testimonial quote (1-3 sentences)")
    name: str = Field(description="Person's name")
    title: str = Field(description="Person's title/company (e.g., 'CEO at Company')")
    avatar_url: Optional[str] = Field(default=None, description="Avatar image URL")


class TestimonialsContent(BaseModel):
    """Content for testimonials section"""
    section_title: str = Field(default="What Our Customers Say", description="Section heading")
    testimonials: list[TestimonialItem] = Field(min_length=2, max_length=4, description="List of testimonials")


class PricingFeature(BaseModel):
    """Feature item in pricing tier"""
    text: str = Field(description="Feature description")
    included: bool = Field(default=True, description="Whether feature is included")


class PricingTier(BaseModel):
    """Single pricing tier"""
    name: str = Field(description="Plan name (e.g., 'Starter', 'Pro', 'Enterprise')")
    description: str = Field(description="Brief plan description")
    price: str = Field(description="Price with currency (e.g., '$29', 'Free', 'Custom')")
    period: str = Field(default="/month", description="Billing period")
    features: list[PricingFeature] = Field(min_length=3, max_length=8, description="Plan features")
    cta_text: str = Field(default="Get Started", description="Button text")
    is_popular: bool = Field(default=False, description="Mark as popular/recommended")


class PricingContent(BaseModel):
    """Content for pricing section"""
    section_title: str = Field(default="Simple, Transparent Pricing", description="Section heading")
    section_description: Optional[str] = Field(default=None, description="Section intro text")
    tiers: list[PricingTier] = Field(min_length=2, max_length=4, description="Pricing tiers")


class CtaContent(BaseModel):
    """Content for CTA section"""
    headline: str = Field(description="CTA headline")
    description: Optional[str] = Field(default=None, description="Supporting text")
    button_text: str = Field(default="Get Started", description="Button text")
    button_url: str = Field(default="#", description="Button URL")


class StatItem(BaseModel):
    """Single statistic"""
    number: str = Field(description="The number/value (e.g., '10K+', '99%', '24/7')")
    label: str = Field(description="What the number represents (e.g., 'Active Users')")


class StatsContent(BaseModel):
    """Content for stats section"""
    stats: list[StatItem] = Field(min_length=3, max_length=6, description="Statistics to display")


class FaqItem(BaseModel):
    """Single FAQ item"""
    question: str = Field(description="The question")
    answer: str = Field(description="The answer (1-3 sentences)")


class FaqContent(BaseModel):
    """Content for FAQ section"""
    section_title: str = Field(default="Frequently Asked Questions", description="Section heading")
    section_description: Optional[str] = Field(default=None, description="Section intro text")
    faqs: list[FaqItem] = Field(min_length=4, max_length=8, description="FAQ items")


class ContactContent(BaseModel):
    """Content for contact section"""
    section_title: str = Field(default="Get in Touch", description="Section heading")
    section_description: Optional[str] = Field(default=None, description="Section intro text")
    email: Optional[str] = Field(default=None, description="Contact email")
    phone: Optional[str] = Field(default=None, description="Contact phone")
    address: Optional[str] = Field(default=None, description="Physical address")
    form_fields: list[str] = Field(default=["name", "email", "message"], description="Form fields to include")
    submit_text: str = Field(default="Send Message", description="Submit button text")


class ClientItem(BaseModel):
    """Single client/partner logo"""
    name: str = Field(description="Company name")
    logo_text: str = Field(description="Text representation of logo (for placeholder)")


class ClientsContent(BaseModel):
    """Content for clients/partners section"""
    headline: str = Field(default="Trusted by leading companies", description="Section intro")
    clients: list[ClientItem] = Field(min_length=4, max_length=8, description="Client logos")


# Map section types to content schemas
SECTION_CONTENT_SCHEMAS = {
    "hero": HeroContent,
    "hero_centered": HeroContent,
    "hero_split": HeroContent,
    "features": FeaturesContent,
    "features_grid": FeaturesContent,
    "features_alternating": FeaturesContent,
    "testimonials": TestimonialsContent,
    "pricing": PricingContent,
    "cta": CtaContent,
    "stats": StatsContent,
    "faq": FaqContent,
    "contact": ContactContent,
    "clients": ClientsContent,
}


def get_content_schema_for_section(section_type: str):
    """Get the appropriate content schema for a section type"""
    return SECTION_CONTENT_SCHEMAS.get(section_type)


__all__ = [
    "ElementType",
    "SectionType",
    "BlockDataKey",
    "FrappeStyles",
    "FrappeBlock",
    "SectionInfo",
    "PageStructure",
    "GeneratedPage",
    # Content schemas
    "HeroContent",
    "FeatureItem",
    "FeaturesContent",
    "TestimonialItem",
    "TestimonialsContent",
    "PricingFeature",
    "PricingTier",
    "PricingContent",
    "CtaContent",
    "StatItem",
    "StatsContent",
    "FaqItem",
    "FaqContent",
    "ContactContent",
    "ClientItem",
    "ClientsContent",
    "SECTION_CONTENT_SCHEMAS",
    "get_content_schema_for_section",
]
