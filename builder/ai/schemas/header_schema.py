"""
Header Configuration Schemas
Defines the declarative header types and configurations.
The AI only needs to fill in the data - the structure comes from templates.
"""

from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field


# Header types with their characteristics
HeaderType = Literal[
    "single_page",       # Simple header for one-page sites
    "multi_page",        # Standard navigation for multi-page sites
    "multi_page_auth",   # Multi-page with login/signup
    "ecommerce",         # E-commerce with cart, search, wishlist, user
    "blog",              # Blog/magazine style
    "portfolio",         # Minimal portfolio style
    "saas",              # SaaS product header
    "documentation",     # Documentation site header
]

# Layout variations for header arrangement
HeaderLayout = Literal[
    "logo_left_menu_right",       # Logo left, menu on right (most common)
    "logo_left_menu_center",      # Logo left, menu centered
    "logo_center_menu_below",     # Logo centered, menu below
    "logo_center_menu_split",     # Logo centered, menu split on sides
    "hamburger_always",           # Always show hamburger menu
    "hamburger_mobile",           # Hamburger on mobile only
]

# Logo types
LogoType = Literal["image", "text", "svg", "icon_text"]


class MenuItem(BaseModel):
    """Menu item configuration"""
    label: str = Field(description="Display text for the menu item")
    href: str = Field(description="Link URL (can be anchor #section or page /about)")
    is_cta: bool = Field(default=False, description="Is this a call-to-action button?")
    is_external: bool = Field(default=False, description="Opens in new tab?")
    icon: Optional[str] = Field(default=None, description="Icon name (for icon menus)")
    children: Optional[list["MenuItem"]] = Field(default=None, description="Dropdown items")


# Rebuild for forward reference
MenuItem.model_rebuild()


class HeaderConfig(BaseModel):
    """
    Declarative header configuration.
    The AI fills in the content data, templates handle the structure.
    """
    # Type and layout
    type: HeaderType = Field(
        default="multi_page",
        description="Type of header based on site purpose"
    )
    layout: HeaderLayout = Field(
        default="logo_left_menu_right",
        description="Visual arrangement of header elements"
    )

    # Logo configuration
    logo_type: LogoType = Field(
        default="text",
        description="Type of logo to display"
    )
    logo_value: str = Field(
        default="Brand",
        description="Logo text, image URL, or SVG content"
    )
    logo_alt: Optional[str] = Field(
        default=None,
        description="Alt text for logo image"
    )

    # Navigation
    menu_items: list[MenuItem] = Field(
        default_factory=list,
        description="Main navigation menu items"
    )

    # Behavior
    sticky: bool = Field(
        default=True,
        description="Header sticks to top on scroll"
    )
    transparent: bool = Field(
        default=False,
        description="Transparent background (for hero overlays)"
    )
    blur_on_scroll: bool = Field(
        default=False,
        description="Add blur effect when scrolling"
    )

    # E-commerce specific
    show_cart: bool = Field(default=False, description="Show shopping cart icon")
    show_search: bool = Field(default=False, description="Show search bar/icon")
    show_wishlist: bool = Field(default=False, description="Show wishlist icon")
    show_user_menu: bool = Field(default=False, description="Show user account menu")

    # Auth specific
    show_login: bool = Field(default=False, description="Show login button")
    show_signup: bool = Field(default=False, description="Show signup button")
    login_text: str = Field(default="Login", description="Login button text")
    signup_text: str = Field(default="Sign Up", description="Signup button text")

    # Blog/Docs specific
    show_categories: bool = Field(default=False, description="Show category navigation")
    categories: Optional[list[MenuItem]] = Field(default=None, description="Category menu items")

    # Styling hints (AI can suggest, templates implement)
    style_hints: Optional[dict] = Field(
        default=None,
        description="Styling suggestions (colors, fonts, etc.)"
    )

    @classmethod
    def for_single_page(cls, logo: str, sections: list[str]) -> "HeaderConfig":
        """Create config for single-page site"""
        return cls(
            type="single_page",
            layout="logo_left_menu_right",
            logo_type="text",
            logo_value=logo,
            menu_items=[
                MenuItem(label=section.title(), href=f"#{section.lower().replace(' ', '-')}")
                for section in sections
            ],
            sticky=True,
        )

    @classmethod
    def for_ecommerce(
        cls,
        logo: str,
        categories: list[str],
        logo_type: LogoType = "image"
    ) -> "HeaderConfig":
        """Create config for e-commerce site"""
        return cls(
            type="ecommerce",
            layout="logo_center_menu_below",
            logo_type=logo_type,
            logo_value=logo,
            menu_items=[
                MenuItem(label=cat, href=f"/category/{cat.lower().replace(' ', '-')}")
                for cat in categories
            ],
            sticky=True,
            show_cart=True,
            show_search=True,
            show_wishlist=True,
            show_user_menu=True,
        )

    @classmethod
    def for_saas(
        cls,
        logo: str,
        features: list[str],
        has_auth: bool = True
    ) -> "HeaderConfig":
        """Create config for SaaS product"""
        menu_items = [
            MenuItem(label=feat, href=f"/{feat.lower().replace(' ', '-')}")
            for feat in features
        ]
        menu_items.append(MenuItem(label="Pricing", href="/pricing"))

        return cls(
            type="saas" if not has_auth else "multi_page_auth",
            layout="logo_left_menu_right",
            logo_type="text",
            logo_value=logo,
            menu_items=menu_items,
            sticky=True,
            blur_on_scroll=True,
            show_login=has_auth,
            show_signup=has_auth,
            signup_text="Get Started",
        )


# Header type descriptions for AI context
HEADER_TYPE_DESCRIPTIONS = {
    "single_page": {
        "description": "Simple header for one-page landing sites",
        "features": ["Anchor navigation", "Smooth scroll", "Minimal design"],
        "typical_items": ["Home", "Features", "About", "Contact"],
    },
    "multi_page": {
        "description": "Standard header for multi-page websites",
        "features": ["Page navigation", "Dropdown menus", "Active states"],
        "typical_items": ["Home", "About", "Services", "Blog", "Contact"],
    },
    "multi_page_auth": {
        "description": "Multi-page with authentication options",
        "features": ["Login/Signup buttons", "User dropdown", "Page navigation"],
        "typical_items": ["Home", "Features", "Pricing", "Login", "Sign Up"],
    },
    "ecommerce": {
        "description": "E-commerce header with shopping features",
        "features": ["Search bar", "Cart icon", "Wishlist", "User menu", "Categories"],
        "typical_items": ["Categories", "New Arrivals", "Sale", "Account", "Cart"],
    },
    "blog": {
        "description": "Blog or magazine style header",
        "features": ["Category navigation", "Search", "Subscribe button"],
        "typical_items": ["Home", "Categories", "About", "Subscribe"],
    },
    "portfolio": {
        "description": "Minimal portfolio header",
        "features": ["Clean design", "Work/Projects link", "Contact CTA"],
        "typical_items": ["Work", "About", "Contact"],
    },
    "saas": {
        "description": "SaaS product header",
        "features": ["Product nav", "Pricing", "Login/Signup", "Demo CTA"],
        "typical_items": ["Product", "Solutions", "Pricing", "Resources", "Login"],
    },
    "documentation": {
        "description": "Documentation site header",
        "features": ["Search", "Version selector", "GitHub link"],
        "typical_items": ["Docs", "API", "Examples", "GitHub"],
    },
}


__all__ = [
    "HeaderType",
    "HeaderLayout",
    "LogoType",
    "MenuItem",
    "HeaderConfig",
    "HEADER_TYPE_DESCRIPTIONS",
]
