"""
Configurable Header System
==========================

A flexible header system with 3 base layouts and 5 feature toggles.

Layouts:
- A: logo_menu_cta  → [Logo] [Nav...] [Icons] [CTA]  (Standard)
- B: menu_logo_cta  → [Nav...] [Logo] [Icons] [CTA]  (Centered logo)
- C: logo_cta_menu  → [Logo] [CTA] [Nav...] [Icons]  (CTA priority)

Feature Toggles:
- show_user: User/account icon
- show_search: Search icon (magnifying glass)
- show_wishlist: Wishlist/favorites icon (heart)
- show_cart: Shopping cart icon
- show_search_bar: Full search bar with input

Usage:
------

```python
from builder.ai.schemas.header_schema import HeaderConfig, NavItem
from builder.ai.templates.headers import build_header

# Create a configuration
config = HeaderConfig(
    layout="logo_menu_cta",
    logo_type="text",
    logo_value="My Brand",
    nav_items=[
        NavItem(label="Home", href="/"),
        NavItem(label="About", href="/about"),
        NavItem(label="Contact", href="/contact"),
    ],
    show_cart=True,
    show_user=True,
    cta_text="Get Started",
    cta_url="/signup",
)

# Build the header
header_block = build_header(config)
```

Or use factory methods:
```python
config = HeaderConfig.for_ecommerce(logo="/files/logo.png")
header_block = build_header(config)
```
"""

from builder.ai.schemas.header_schema import HeaderConfig, NavItem
from builder.ai.templates.headers.layouts import (
    build_layout,
    build_logo,
    build_nav,
    build_cta,
    build_icons,
    LAYOUT_BUILDERS,
)
from builder.ai.templates.headers.icons import (
    build_search_icon,
    build_cart_icon,
    build_wishlist_icon,
    build_user_icon,
    build_search_bar,
    build_icons_group,
)
from builder.ai.templates.headers.burger import (
    build_burger_button,
    build_sidebar,
    build_sidebar_overlay,
    build_sidebar_panel,
    get_auto_burger_script,
    build_script_block,
)
from builder.ai.templates.headers.base import (
    generate_unique_id,
    get_header_base_styles,
    get_header_mobile_styles,
)


def build_header(
    config: HeaderConfig,
    include_sidebar: bool = True,
    include_script: bool = False,
    id_prefix: str = "header"
) -> dict:
    """
    Build a complete header from configuration.

    This is the main entry point for creating headers with the new
    configurable system.

    Args:
        config: HeaderConfig with all header settings
        include_sidebar: Whether to include the mobile sidebar (default: True)
        include_script: Whether to include auto-burger script inline (default: False)
        id_prefix: Prefix for block IDs

    Returns:
        dict: Complete header block structure ready for Frappe Builder

    Example:
        >>> config = HeaderConfig.for_ecommerce(logo="/files/logo.png")
        >>> header = build_header(config)
    """
    # Build the main header layout
    header = build_layout(config, id_prefix)

    # Build sidebar for mobile
    if include_sidebar:
        # Build icons for sidebar (same as header)
        sidebar_icons = build_icons_group(
            show_search_bar=False,  # Never show search bar in sidebar
            show_search=config.show_search,
            show_wishlist=config.show_wishlist,
            show_cart=config.show_cart,
            show_user=config.show_user,
            search_url=config.search_url,
            wishlist_url=config.wishlist_url,
            cart_url=config.cart_url,
            user_url=config.user_url,
            id_prefix="sidebar",
        )

        sidebar = build_sidebar(
            nav_items=config.nav_items,
            icons_block=sidebar_icons,
            cta_text=config.cta_text,
            cta_url=config.cta_url,
            id_prefix="sidebar",
        )

        # Add sidebar as a sibling to header children
        header["children"].append(sidebar)

    # Optionally include the auto-burger script
    if include_script:
        header["children"].append(build_script_block(id_prefix))

    return header


def build_header_with_script(config: HeaderConfig, id_prefix: str = "header") -> tuple[dict, str]:
    """
    Build a header and return both the block and the JavaScript separately.

    Use this when you want to include the script in a separate location
    (e.g., at the end of the page).

    Args:
        config: HeaderConfig with all header settings
        id_prefix: Prefix for block IDs

    Returns:
        tuple: (header_block, javascript_code)
    """
    header = build_header(config, include_sidebar=True, include_script=False, id_prefix=id_prefix)
    script = get_auto_burger_script()
    return header, script


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def build_ecommerce_header(
    logo: str = "/files/logo-default.png",
    categories: list[str] = None,
    logo_type: str = "image",
) -> dict:
    """
    Build an e-commerce header with cart, wishlist, search, and user icons.

    Args:
        logo: Logo image URL or text
        categories: List of category names for navigation
        logo_type: "text" or "image"

    Returns:
        dict: Complete e-commerce header block
    """
    config = HeaderConfig.for_ecommerce(
        logo=logo,
        categories=categories,
        logo_type=logo_type,
    )
    return build_header(config)


def build_saas_header(
    logo: str = "ProductName",
    pages: list[str] = None,
    has_auth: bool = True,
    logo_type: str = "text",
) -> dict:
    """
    Build a SaaS product header with login/signup options.

    Args:
        logo: Logo text or image URL
        pages: List of page names for navigation
        has_auth: Whether to show user icon
        logo_type: "text" or "image"

    Returns:
        dict: Complete SaaS header block
    """
    config = HeaderConfig.for_saas(
        logo=logo,
        pages=pages,
        has_auth=has_auth,
        logo_type=logo_type,
    )
    return build_header(config)


def build_portfolio_header(
    logo: str = "John Doe",
    logo_type: str = "text",
) -> dict:
    """
    Build a minimal portfolio header with centered logo.

    Args:
        logo: Logo text (usually name) or image URL
        logo_type: "text" or "image"

    Returns:
        dict: Complete portfolio header block
    """
    config = HeaderConfig.for_portfolio(
        logo=logo,
        logo_type=logo_type,
    )
    return build_header(config)


def build_blog_header(
    logo: str = "Blog Name",
    categories: list[str] = None,
    logo_type: str = "text",
) -> dict:
    """
    Build a blog header with search and subscribe button.

    Args:
        logo: Logo text or image URL
        categories: List of blog categories
        logo_type: "text" or "image"

    Returns:
        dict: Complete blog header block
    """
    config = HeaderConfig.for_blog(
        logo=logo,
        categories=categories,
        logo_type=logo_type,
    )
    return build_header(config)


def build_single_page_header(
    logo: str = "Brand",
    sections: list[str] = None,
    logo_type: str = "text",
) -> dict:
    """
    Build a header for single-page sites with anchor navigation.

    Args:
        logo: Logo text or image URL
        sections: List of section names (will be converted to anchors)
        logo_type: "text" or "image"

    Returns:
        dict: Complete single-page header block
    """
    config = HeaderConfig.for_single_page(
        logo=logo,
        sections=sections,
        logo_type=logo_type,
    )
    return build_header(config)


__all__ = [
    # Main entry point
    "build_header",
    "build_header_with_script",
    # Convenience functions
    "build_ecommerce_header",
    "build_saas_header",
    "build_portfolio_header",
    "build_blog_header",
    "build_single_page_header",
    # Layout builders
    "build_layout",
    "build_logo",
    "build_nav",
    "build_cta",
    "build_icons",
    "LAYOUT_BUILDERS",
    # Icon builders
    "build_search_icon",
    "build_cart_icon",
    "build_wishlist_icon",
    "build_user_icon",
    "build_search_bar",
    "build_icons_group",
    # Burger/sidebar
    "build_burger_button",
    "build_sidebar",
    "build_sidebar_overlay",
    "build_sidebar_panel",
    "get_auto_burger_script",
    "build_script_block",
    # Utilities
    "generate_unique_id",
    "get_header_base_styles",
    "get_header_mobile_styles",
]
