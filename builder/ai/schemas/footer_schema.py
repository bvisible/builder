"""
Footer Configuration Schemas
Defines the declarative footer types and configurations.
"""

from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field


# Footer types with their characteristics
FooterType = Literal[
    "minimal",           # Simple copyright + social links
    "standard",          # Multi-column with links
    "extended",          # Full footer with newsletter, multiple sections
    "ecommerce",         # E-commerce with payment methods, trust badges
    "saas",              # SaaS with product links, resources
    "blog",              # Blog with categories, recent posts
    "centered",          # Centered layout, minimal links
]

# Layout variations
FooterLayout = Literal[
    "columns",           # Traditional multi-column layout
    "centered",          # Centered single section
    "two_rows",          # Links row + copyright row
    "sidebar",           # Large branding section + links
]


class FooterLink(BaseModel):
    """Footer link item"""
    label: str = Field(description="Display text")
    href: str = Field(description="Link URL")
    is_external: bool = Field(default=False, description="Opens in new tab")


class FooterColumn(BaseModel):
    """Footer column with title and links"""
    title: str = Field(description="Column heading")
    links: list[FooterLink] = Field(default_factory=list, description="Links in this column")


class SocialLinks(BaseModel):
    """Social media links configuration"""
    facebook: Optional[str] = Field(default=None, description="Facebook URL")
    twitter: Optional[str] = Field(default=None, description="Twitter/X URL")
    instagram: Optional[str] = Field(default=None, description="Instagram URL")
    linkedin: Optional[str] = Field(default=None, description="LinkedIn URL")
    youtube: Optional[str] = Field(default=None, description="YouTube URL")
    github: Optional[str] = Field(default=None, description="GitHub URL")
    discord: Optional[str] = Field(default=None, description="Discord URL")
    tiktok: Optional[str] = Field(default=None, description="TikTok URL")

    def get_active_links(self) -> dict[str, str]:
        """Get only the social links that are set"""
        return {k: v for k, v in self.model_dump().items() if v is not None}


class NewsletterConfig(BaseModel):
    """Newsletter signup configuration"""
    title: str = Field(default="Subscribe to our newsletter", description="Newsletter title")
    description: Optional[str] = Field(default=None, description="Newsletter description")
    placeholder: str = Field(default="Enter your email", description="Input placeholder")
    button_text: str = Field(default="Subscribe", description="Submit button text")
    privacy_text: Optional[str] = Field(default=None, description="Privacy notice text")


class FooterConfig(BaseModel):
    """
    Declarative footer configuration.
    The AI fills in the content data, templates handle the structure.
    """
    # Type and layout
    type: FooterType = Field(
        default="standard",
        description="Type of footer based on site purpose"
    )
    layout: FooterLayout = Field(
        default="columns",
        description="Visual arrangement of footer elements"
    )

    # Logo/Branding
    show_logo: bool = Field(default=True, description="Show logo in footer")
    logo_value: Optional[str] = Field(default=None, description="Logo text or image URL")
    tagline: Optional[str] = Field(default=None, description="Brand tagline/description")

    # Content columns
    columns: list[FooterColumn] = Field(
        default_factory=list,
        description="Footer link columns"
    )

    # Social links
    show_social: bool = Field(default=True, description="Show social media links")
    social_links: Optional[SocialLinks] = Field(default=None, description="Social media URLs")

    # Newsletter
    show_newsletter: bool = Field(default=False, description="Show newsletter signup")
    newsletter: Optional[NewsletterConfig] = Field(default=None, description="Newsletter config")

    # Copyright
    copyright_text: str = Field(
        default="All rights reserved.",
        description="Copyright notice text"
    )
    company_name: Optional[str] = Field(default=None, description="Company name for copyright")
    show_year: bool = Field(default=True, description="Show current year in copyright")

    # E-commerce specific
    show_payment_methods: bool = Field(default=False, description="Show payment method icons")
    payment_methods: Optional[list[str]] = Field(
        default=None,
        description="Payment methods to display (visa, mastercard, paypal, etc.)"
    )
    show_trust_badges: bool = Field(default=False, description="Show trust/security badges")

    # Legal links (always at bottom)
    legal_links: list[FooterLink] = Field(
        default_factory=lambda: [
            FooterLink(label="Privacy Policy", href="/privacy"),
            FooterLink(label="Terms of Service", href="/terms"),
        ],
        description="Legal/policy links"
    )

    # Contact info
    show_contact: bool = Field(default=False, description="Show contact information")
    contact_email: Optional[str] = Field(default=None, description="Contact email")
    contact_phone: Optional[str] = Field(default=None, description="Contact phone")
    contact_address: Optional[str] = Field(default=None, description="Physical address")

    # Style hints
    style_hints: Optional[dict] = Field(
        default=None,
        description="Styling suggestions"
    )

    @classmethod
    def minimal(cls, company_name: str, social: SocialLinks = None) -> "FooterConfig":
        """Create minimal footer config"""
        return cls(
            type="minimal",
            layout="centered",
            show_logo=False,
            columns=[],
            show_social=social is not None,
            social_links=social,
            company_name=company_name,
        )

    @classmethod
    def standard(
        cls,
        company_name: str,
        columns: list[FooterColumn],
        social: SocialLinks = None
    ) -> "FooterConfig":
        """Create standard multi-column footer"""
        return cls(
            type="standard",
            layout="columns",
            company_name=company_name,
            columns=columns,
            show_social=social is not None,
            social_links=social,
        )

    @classmethod
    def for_ecommerce(
        cls,
        company_name: str,
        columns: list[FooterColumn],
        social: SocialLinks = None,
        payment_methods: list[str] = None
    ) -> "FooterConfig":
        """Create e-commerce footer"""
        return cls(
            type="ecommerce",
            layout="columns",
            company_name=company_name,
            columns=columns,
            show_social=social is not None,
            social_links=social,
            show_payment_methods=True,
            payment_methods=payment_methods or ["visa", "mastercard", "paypal", "stripe"],
            show_trust_badges=True,
            show_newsletter=True,
            newsletter=NewsletterConfig(
                title="Get exclusive offers",
                description="Subscribe for deals and new arrivals",
            ),
        )

    @classmethod
    def for_saas(
        cls,
        company_name: str,
        tagline: str = None,
        social: SocialLinks = None
    ) -> "FooterConfig":
        """Create SaaS footer"""
        return cls(
            type="saas",
            layout="columns",
            company_name=company_name,
            tagline=tagline,
            columns=[
                FooterColumn(
                    title="Product",
                    links=[
                        FooterLink(label="Features", href="/features"),
                        FooterLink(label="Pricing", href="/pricing"),
                        FooterLink(label="Integrations", href="/integrations"),
                        FooterLink(label="Changelog", href="/changelog"),
                    ]
                ),
                FooterColumn(
                    title="Resources",
                    links=[
                        FooterLink(label="Documentation", href="/docs"),
                        FooterLink(label="API Reference", href="/api"),
                        FooterLink(label="Blog", href="/blog"),
                        FooterLink(label="Support", href="/support"),
                    ]
                ),
                FooterColumn(
                    title="Company",
                    links=[
                        FooterLink(label="About", href="/about"),
                        FooterLink(label="Careers", href="/careers"),
                        FooterLink(label="Contact", href="/contact"),
                    ]
                ),
            ],
            show_social=social is not None,
            social_links=social,
            show_newsletter=True,
            newsletter=NewsletterConfig(
                title="Stay updated",
                description="Get product news and tips",
            ),
        )


# Footer type descriptions for AI context
FOOTER_TYPE_DESCRIPTIONS = {
    "minimal": {
        "description": "Simple footer with copyright and optional social links",
        "features": ["Copyright notice", "Social icons", "Centered layout"],
        "best_for": ["Simple landing pages", "Portfolio sites", "One-page sites"],
    },
    "standard": {
        "description": "Multi-column footer with organized link sections",
        "features": ["Multiple columns", "Categorized links", "Social links", "Copyright"],
        "best_for": ["Corporate sites", "Multi-page websites", "Service businesses"],
    },
    "extended": {
        "description": "Full-featured footer with newsletter and multiple sections",
        "features": ["Newsletter signup", "Multiple columns", "Contact info", "Social links"],
        "best_for": ["Content sites", "News/media", "Large corporate sites"],
    },
    "ecommerce": {
        "description": "E-commerce footer with trust elements",
        "features": ["Payment methods", "Trust badges", "Newsletter", "Multiple columns"],
        "best_for": ["Online stores", "Marketplaces", "E-commerce sites"],
    },
    "saas": {
        "description": "SaaS product footer with resources",
        "features": ["Product links", "Documentation", "Resources", "Newsletter"],
        "best_for": ["SaaS products", "Tech startups", "Developer tools"],
    },
    "blog": {
        "description": "Blog footer with categories and recent content",
        "features": ["Categories", "Recent posts", "Social links", "Newsletter"],
        "best_for": ["Blogs", "Magazines", "Content platforms"],
    },
    "centered": {
        "description": "Centered minimal footer",
        "features": ["Centered layout", "Essential links only", "Clean design"],
        "best_for": ["Creative portfolios", "Minimal sites", "Artist pages"],
    },
}


# Default footer columns for different site types
DEFAULT_FOOTER_COLUMNS = {
    "standard": [
        FooterColumn(
            title="Company",
            links=[
                FooterLink(label="About Us", href="/about"),
                FooterLink(label="Careers", href="/careers"),
                FooterLink(label="Contact", href="/contact"),
            ]
        ),
        FooterColumn(
            title="Services",
            links=[
                FooterLink(label="Our Services", href="/services"),
                FooterLink(label="Pricing", href="/pricing"),
                FooterLink(label="FAQ", href="/faq"),
            ]
        ),
        FooterColumn(
            title="Resources",
            links=[
                FooterLink(label="Blog", href="/blog"),
                FooterLink(label="Support", href="/support"),
                FooterLink(label="Documentation", href="/docs"),
            ]
        ),
    ],
    "ecommerce": [
        FooterColumn(
            title="Shop",
            links=[
                FooterLink(label="All Products", href="/products"),
                FooterLink(label="New Arrivals", href="/new"),
                FooterLink(label="Sale", href="/sale"),
                FooterLink(label="Gift Cards", href="/gift-cards"),
            ]
        ),
        FooterColumn(
            title="Customer Service",
            links=[
                FooterLink(label="Contact Us", href="/contact"),
                FooterLink(label="Shipping Info", href="/shipping"),
                FooterLink(label="Returns", href="/returns"),
                FooterLink(label="Size Guide", href="/size-guide"),
            ]
        ),
        FooterColumn(
            title="About",
            links=[
                FooterLink(label="Our Story", href="/about"),
                FooterLink(label="Sustainability", href="/sustainability"),
                FooterLink(label="Stores", href="/stores"),
            ]
        ),
    ],
}


__all__ = [
    "FooterType",
    "FooterLayout",
    "FooterLink",
    "FooterColumn",
    "SocialLinks",
    "NewsletterConfig",
    "FooterConfig",
    "FOOTER_TYPE_DESCRIPTIONS",
    "DEFAULT_FOOTER_COLUMNS",
]
