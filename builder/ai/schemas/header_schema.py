"""
Header Configuration Schemas
Defines the declarative header types and configurations for the configurable header system.

The system supports:
- 3 base layouts: logo_menu_cta, menu_logo_cta, logo_cta_menu
- 5 feature toggles: show_user, show_search, show_wishlist, show_cart, show_search_bar
- Auto-burger menu with sidebar slide-in
"""

from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field


# =============================================================================
# BASE TYPES
# =============================================================================

# The 3 base layouts
HeaderLayout = Literal[
    "logo_menu_cta",   # Layout A: [Logo] [Nav...] [Icons] [CTA] - Standard, versatile
    "menu_logo_cta",   # Layout B: [Nav...] [Logo] [Icons] [CTA] - Centered logo
    "logo_cta_menu",   # Layout C: [Logo] [CTA] [Nav...] [Icons] - CTA priority
]

# Logo display types
LogoType = Literal["text", "image"]


# =============================================================================
# NAVIGATION ITEM
# =============================================================================

class NavItem(BaseModel):
    """Navigation menu item configuration"""
    label: str = Field(description="Display text for the menu item")
    href: str = Field(default="#", description="Link URL (anchor #section or page /about)")
    is_external: bool = Field(default=False, description="Opens in new tab?")
    icon: Optional[str] = Field(default=None, description="Optional icon name")
    children: Optional[list["NavItem"]] = Field(default=None, description="Dropdown items")


# Rebuild for forward reference
NavItem.model_rebuild()


# =============================================================================
# HEADER CONFIGURATION
# =============================================================================

class HeaderConfig(BaseModel):
    """
    Declarative header configuration.
    The configuration defines what features to show - templates handle the structure.
    """
    # Layout selection (one of the 3 base layouts)
    layout: HeaderLayout = Field(
        default="logo_menu_cta",
        description="Base layout arrangement"
    )

    # Logo configuration
    logo_type: LogoType = Field(
        default="text",
        description="Type of logo to display (text or image)"
    )
    logo_value: str = Field(
        default="Brand",
        description="Logo text or image URL"
    )
    logo_url: str = Field(
        default="/",
        description="Link destination when clicking logo"
    )
    logo_alt: Optional[str] = Field(
        default="Logo",
        description="Alt text for logo image"
    )

    # Feature toggles (the 5 icons)
    show_user: bool = Field(
        default=False,
        description="Show user/account icon"
    )
    show_search: bool = Field(
        default=False,
        description="Show search icon (magnifying glass)"
    )
    show_wishlist: bool = Field(
        default=False,
        description="Show wishlist/favorites icon (heart)"
    )
    show_cart: bool = Field(
        default=False,
        description="Show shopping cart icon"
    )
    show_search_bar: bool = Field(
        default=False,
        description="Show full search bar (takes more space)"
    )

    # Navigation items
    nav_items: list[NavItem] = Field(
        default_factory=list,
        description="Main navigation menu items"
    )

    # CTA button (optional)
    cta_text: Optional[str] = Field(
        default=None,
        description="Call-to-action button text (None = no CTA)"
    )
    cta_url: str = Field(
        default="#",
        description="CTA button destination URL"
    )

    # Behavior options
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

    # Icon URLs (optional overrides)
    user_url: str = Field(default="/account", description="User icon link")
    search_url: str = Field(default="/search", description="Search icon link")
    wishlist_url: str = Field(default="/wishlist", description="Wishlist icon link")
    cart_url: str = Field(default="/cart", description="Cart icon link")

    # ==========================================================================
    # FACTORY METHODS
    # ==========================================================================

    @classmethod
    def for_single_page(
        cls,
        logo: str = "Brand",
        sections: list[str] = None,
        logo_type: LogoType = "text"
    ) -> "HeaderConfig":
        """Create config for single-page site with anchor navigation"""
        sections = sections or ["Features", "About", "Pricing", "Contact"]
        return cls(
            layout="logo_menu_cta",
            logo_type=logo_type,
            logo_value=logo,
            nav_items=[
                NavItem(
                    label=section.title(),
                    href=f"#{section.lower().replace(' ', '-')}"
                )
                for section in sections
            ],
            cta_text="Get Started",
            cta_url="#contact",
            sticky=True,
        )

    @classmethod
    def for_ecommerce(
        cls,
        logo: str = "/files/logo-default.png",
        categories: list[str] = None,
        logo_type: LogoType = "image"
    ) -> "HeaderConfig":
        """Create config for e-commerce site"""
        categories = categories or ["Products", "New Arrivals", "Sale"]
        return cls(
            layout="logo_menu_cta",
            logo_type=logo_type,
            logo_value=logo,
            nav_items=[
                NavItem(label=cat, href=f"/shop-by-category/{cat.lower().replace(' ', '-')}")
                for cat in categories
            ],
            # E-commerce features
            show_cart=True,
            show_search=True,
            show_wishlist=True,
            show_user=True,
            # No CTA for e-commerce (icons are the CTAs)
            cta_text=None,
            sticky=True,
        )

    @classmethod
    def for_saas(
        cls,
        logo: str = "ProductName",
        pages: list[str] = None,
        has_auth: bool = True,
        logo_type: LogoType = "text"
    ) -> "HeaderConfig":
        """Create config for SaaS product"""
        pages = pages or ["Features", "Pricing", "Resources"]
        nav_items = [
            NavItem(label=page, href=f"/{page.lower().replace(' ', '-')}")
            for page in pages
        ]

        return cls(
            layout="logo_menu_cta",
            logo_type=logo_type,
            logo_value=logo,
            nav_items=nav_items,
            # SaaS typically has user login
            show_user=has_auth,
            show_search=False,
            # CTA for signup/demo
            cta_text="Start Free Trial" if has_auth else "Get Started",
            cta_url="/signup" if has_auth else "#contact",
            sticky=True,
            blur_on_scroll=True,
        )

    @classmethod
    def for_portfolio(
        cls,
        logo: str = "John Doe",
        logo_type: LogoType = "text"
    ) -> "HeaderConfig":
        """Create config for portfolio site"""
        return cls(
            layout="menu_logo_cta",  # Centered logo works well for portfolios
            logo_type=logo_type,
            logo_value=logo,
            nav_items=[
                NavItem(label="Work", href="/work"),
                NavItem(label="About", href="/about"),
            ],
            # Minimal icons for portfolio
            show_user=False,
            show_search=False,
            show_wishlist=False,
            show_cart=False,
            # Contact as CTA
            cta_text="Contact",
            cta_url="/contact",
            sticky=True,
        )

    @classmethod
    def for_blog(
        cls,
        logo: str = "Blog Name",
        categories: list[str] = None,
        logo_type: LogoType = "text"
    ) -> "HeaderConfig":
        """Create config for blog site"""
        categories = categories or ["Tech", "Design", "Business"]
        return cls(
            layout="logo_menu_cta",
            logo_type=logo_type,
            logo_value=logo,
            nav_items=[
                NavItem(label=cat, href=f"/category/{cat.lower()}")
                for cat in categories
            ] + [NavItem(label="About", href="/about")],
            # Blog needs search
            show_search=True,
            show_user=False,
            show_wishlist=False,
            show_cart=False,
            # Subscribe CTA
            cta_text="Subscribe",
            cta_url="#newsletter",
            sticky=True,
        )


# =============================================================================
# SITE TYPE DEFAULTS
# =============================================================================

SITE_TYPE_HEADER_DEFAULTS = {
    "ecommerce": {
        "layout": "logo_menu_cta",
        "show_cart": True,
        "show_wishlist": True,
        "show_user": True,
        "show_search": True,
        "cta_text": None,
    },
    "saas": {
        "layout": "logo_menu_cta",
        "show_user": True,
        "show_search": False,
        "show_wishlist": False,
        "show_cart": False,
        "cta_text": "Start Free Trial",
    },
    "portfolio": {
        "layout": "menu_logo_cta",
        "show_user": False,
        "show_search": False,
        "show_wishlist": False,
        "show_cart": False,
        "cta_text": "Contact",
    },
    "blog": {
        "layout": "logo_menu_cta",
        "show_search": True,
        "show_user": False,
        "show_wishlist": False,
        "show_cart": False,
        "cta_text": "Subscribe",
    },
    "single_page": {
        "layout": "logo_menu_cta",
        "show_user": False,
        "show_search": False,
        "show_wishlist": False,
        "show_cart": False,
        "cta_text": "Get Started",
    },
    "multi_page": {
        "layout": "logo_menu_cta",
        "show_user": False,
        "show_search": False,
        "show_wishlist": False,
        "show_cart": False,
        "cta_text": "Contact",
    },
    "documentation": {
        "layout": "logo_menu_cta",
        "show_search": True,
        "show_search_bar": True,
        "show_user": False,
        "show_wishlist": False,
        "show_cart": False,
        "cta_text": None,
    },
}


# =============================================================================
# HEADER TYPE DESCRIPTIONS (for AI context)
# =============================================================================

HEADER_TYPE_DESCRIPTIONS = {
    "single_page": {
        "description": "Simple header for one-page landing sites",
        "features": ["Anchor navigation", "Smooth scroll", "Minimal design"],
        "typical_items": ["Features", "About", "Pricing", "Contact"],
    },
    "multi_page": {
        "description": "Standard header for multi-page websites",
        "features": ["Page navigation", "Dropdown menus", "Active states"],
        "typical_items": ["Home", "About", "Services", "Blog", "Contact"],
    },
    "ecommerce": {
        "description": "E-commerce header with shopping features",
        "features": ["Search", "Cart", "Wishlist", "User account", "Categories"],
        "typical_items": ["Products", "Categories", "New Arrivals", "Sale"],
    },
    "blog": {
        "description": "Blog or magazine style header",
        "features": ["Category navigation", "Search", "Subscribe button"],
        "typical_items": ["Categories", "About", "Subscribe"],
    },
    "portfolio": {
        "description": "Minimal portfolio header",
        "features": ["Clean design", "Work/Projects link", "Contact CTA"],
        "typical_items": ["Work", "About", "Contact"],
    },
    "saas": {
        "description": "SaaS product header",
        "features": ["Product nav", "Pricing", "Login/Signup", "Demo CTA"],
        "typical_items": ["Features", "Pricing", "Resources", "Login"],
    },
    "documentation": {
        "description": "Documentation site header",
        "features": ["Search bar", "Version selector", "GitHub link"],
        "typical_items": ["Docs", "API", "Examples", "GitHub"],
    },
}


__all__ = [
    "HeaderLayout",
    "LogoType",
    "NavItem",
    "HeaderConfig",
    "SITE_TYPE_HEADER_DEFAULTS",
    "HEADER_TYPE_DESCRIPTIONS",
]
