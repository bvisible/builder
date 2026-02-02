"""
Header Layouts Module
The 3 base layouts for the configurable header system.

Layouts:
- A: logo_menu_cta  → [Logo] [Nav...] [Icons] [CTA]
- B: menu_logo_cta  → [Nav...] [Logo] [Icons] [CTA]
- C: logo_cta_menu  → [Logo] [CTA] [Nav...] [Icons]
"""

from typing import Optional
from builder.ai.schemas.header_schema import HeaderConfig, NavItem
from builder.ai.templates.headers.base import (
    generate_unique_id,
    get_header_base_styles,
    get_header_mobile_styles,
    get_logo_text_styles,
    get_logo_image_styles,
    get_logo_image_mobile_styles,
    get_nav_container_styles,
    get_nav_link_styles,
    get_cta_button_styles,
)
from builder.ai.templates.headers.icons import build_icons_group
from builder.ai.templates.headers.burger import build_burger_button


# =============================================================================
# COMPONENT BUILDERS
# =============================================================================

def build_logo(config: HeaderConfig, id_prefix: str = "header") -> dict:
    """
    Build logo block based on configuration.

    Args:
        config: Header configuration with logo settings
        id_prefix: Prefix for block IDs

    Returns:
        dict: Logo block structure
    """
    if config.logo_type == "text":
        return {
            "blockId": f"{id_prefix}-logo",
            "element": "a",
            "innerHTML": config.logo_value,
            "attributes": {"href": config.logo_url},
            "baseStyles": get_logo_text_styles(),
        }

    # Image logo
    return {
        "blockId": f"{id_prefix}-logo",
        "element": "a",
        "attributes": {"href": config.logo_url},
        "baseStyles": {"textDecoration": "none", "display": "flex", "alignItems": "center"},
        "children": [{
            "blockId": f"{id_prefix}-logo-img",
            "element": "img",
            "attributes": {
                "src": config.logo_value,
                "alt": config.logo_alt or "Logo"
            },
            "baseStyles": get_logo_image_styles(),
            "mobileStyles": get_logo_image_mobile_styles(),
        }]
    }


def build_nav(config: HeaderConfig, id_prefix: str = "header") -> dict:
    """
    Build navigation block from configuration.

    Args:
        config: Header configuration with nav items
        id_prefix: Prefix for block IDs

    Returns:
        dict: Navigation block structure
    """
    nav_links = []

    for i, item in enumerate(config.nav_items):
        link = {
            "blockId": f"{id_prefix}-nav-link-{i}",
            "element": "a",
            "innerHTML": item.label,
            "attributes": {
                "href": item.href,
            },
            "baseStyles": get_nav_link_styles(),
        }

        # Add external link attributes
        if item.is_external:
            link["attributes"]["target"] = "_blank"
            link["attributes"]["rel"] = "noopener"

        nav_links.append(link)

    return {
        "blockId": f"{id_prefix}-nav",
        "element": "nav",
        "baseStyles": get_nav_container_styles(),
        "mobileStyles": {
            "display": "none",  # Hidden on mobile, shown in sidebar
        },
        "children": nav_links,
    }


def build_cta(config: HeaderConfig, id_prefix: str = "header") -> dict | None:
    """
    Build CTA button if configured.

    Args:
        config: Header configuration with CTA settings
        id_prefix: Prefix for block IDs

    Returns:
        dict: CTA button block, or None if no CTA
    """
    if not config.cta_text:
        return None

    return {
        "blockId": f"{id_prefix}-cta",
        "element": "a",
        "innerHTML": config.cta_text,
        "attributes": {"href": config.cta_url},
        "baseStyles": get_cta_button_styles(),
        "mobileStyles": {
            "display": "none",  # Hidden on mobile, shown in sidebar
        },
    }


def build_icons(config: HeaderConfig, id_prefix: str = "header") -> dict | None:
    """
    Build icons group from configuration.

    Args:
        config: Header configuration with icon toggles
        id_prefix: Prefix for block IDs

    Returns:
        dict: Icons group block, or None if no icons
    """
    return build_icons_group(
        show_search_bar=config.show_search_bar,
        show_search=config.show_search,
        show_wishlist=config.show_wishlist,
        show_cart=config.show_cart,
        show_user=config.show_user,
        search_url=config.search_url,
        wishlist_url=config.wishlist_url,
        cart_url=config.cart_url,
        user_url=config.user_url,
        id_prefix=id_prefix,
    )


# =============================================================================
# LAYOUT A: logo_menu_cta
# [Logo] [Nav...] [Icons] [CTA]
# Standard layout - most versatile
# =============================================================================

def build_layout_logo_menu_cta(config: HeaderConfig, id_prefix: str = "header") -> dict:
    """
    Build Layout A: Logo left, navigation center-right, icons and CTA on right.

    Structure:
    [Logo] -------- [Nav] -------- [Icons] [CTA] [Burger]

    Args:
        config: Header configuration
        id_prefix: Prefix for block IDs

    Returns:
        dict: Complete header block structure
    """
    logo = build_logo(config, id_prefix)
    nav = build_nav(config, id_prefix)
    icons = build_icons(config, id_prefix)
    cta = build_cta(config, id_prefix)
    burger = build_burger_button(id_prefix)

    # Build right section (nav + icons + cta)
    right_children = []

    # Add nav to right section
    if nav.get("children"):
        right_children.append(nav)

    # Add icons
    if icons:
        right_children.append(icons)

    # Add CTA
    if cta:
        right_children.append(cta)

    # Add burger (always visible on mobile)
    right_children.append(burger)

    right_section = {
        "blockId": f"{id_prefix}-right",
        "element": "div",
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "gap": "24px",
        },
        "children": right_children,
    }

    return {
        "blockId": f"{id_prefix}-main",
        "element": "header",
        "attributes": {
            "data-auto-burger": "true",
            "data-layout": "logo_menu_cta",
        },
        "baseStyles": get_header_base_styles(
            sticky=config.sticky,
            transparent=config.transparent,
            blur_on_scroll=config.blur_on_scroll,
        ),
        "mobileStyles": get_header_mobile_styles(),
        "children": [logo, right_section],
    }


# =============================================================================
# LAYOUT B: menu_logo_cta
# [Nav...] [Logo] [Icons] [CTA]
# Centered logo layout
# =============================================================================

def build_layout_menu_logo_cta(config: HeaderConfig, id_prefix: str = "header") -> dict:
    """
    Build Layout B: Navigation on left, logo centered, icons and CTA on right.

    Structure:
    [Nav...] -------- [Logo] -------- [Icons] [CTA] [Burger]

    Uses CSS grid to ensure logo stays centered regardless of nav/icons width.

    Args:
        config: Header configuration
        id_prefix: Prefix for block IDs

    Returns:
        dict: Complete header block structure
    """
    logo = build_logo(config, id_prefix)
    nav = build_nav(config, id_prefix)
    icons = build_icons(config, id_prefix)
    cta = build_cta(config, id_prefix)
    burger = build_burger_button(id_prefix)

    # Left section (nav)
    left_section = {
        "blockId": f"{id_prefix}-left",
        "element": "div",
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
        },
        "mobileStyles": {
            "display": "none",
        },
        "children": [nav] if nav.get("children") else [],
    }

    # Right section (icons + cta + burger)
    right_children = []
    if icons:
        right_children.append(icons)
    if cta:
        right_children.append(cta)
    right_children.append(burger)

    right_section = {
        "blockId": f"{id_prefix}-right",
        "element": "div",
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "flex-end",
            "gap": "16px",
        },
        "children": right_children,
    }

    base_styles = get_header_base_styles(
        sticky=config.sticky,
        transparent=config.transparent,
        blur_on_scroll=config.blur_on_scroll,
    )

    # Override to use grid for centered layout
    base_styles.update({
        "display": "grid",
        "gridTemplateColumns": "1fr auto 1fr",
        "alignItems": "center",
    })

    return {
        "blockId": f"{id_prefix}-main",
        "element": "header",
        "attributes": {
            "data-auto-burger": "true",
            "data-layout": "menu_logo_cta",
        },
        "baseStyles": base_styles,
        "mobileStyles": {
            **get_header_mobile_styles(),
            "display": "flex",
            "justifyContent": "space-between",
        },
        "children": [left_section, logo, right_section],
    }


# =============================================================================
# LAYOUT C: logo_cta_menu
# [Logo] [CTA] [Nav...] [Icons]
# CTA priority layout
# =============================================================================

def build_layout_logo_cta_menu(config: HeaderConfig, id_prefix: str = "header") -> dict:
    """
    Build Layout C: Logo and CTA on left, navigation and icons on right.

    Structure:
    [Logo] [CTA] -------- [Nav...] [Icons] [Burger]

    CTA is placed immediately after logo for higher prominence.

    Args:
        config: Header configuration
        id_prefix: Prefix for block IDs

    Returns:
        dict: Complete header block structure
    """
    logo = build_logo(config, id_prefix)
    nav = build_nav(config, id_prefix)
    icons = build_icons(config, id_prefix)
    cta = build_cta(config, id_prefix)
    burger = build_burger_button(id_prefix)

    # Left section (logo + cta)
    left_children = [logo]
    if cta:
        # Override CTA mobile styles to show on desktop in left section
        cta_for_left = {
            **cta,
            "mobileStyles": {"display": "none"},
        }
        left_children.append(cta_for_left)

    left_section = {
        "blockId": f"{id_prefix}-left",
        "element": "div",
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "gap": "24px",
        },
        "children": left_children,
    }

    # Right section (nav + icons + burger)
    right_children = []
    if nav.get("children"):
        right_children.append(nav)
    if icons:
        right_children.append(icons)
    right_children.append(burger)

    right_section = {
        "blockId": f"{id_prefix}-right",
        "element": "div",
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "gap": "24px",
        },
        "children": right_children,
    }

    return {
        "blockId": f"{id_prefix}-main",
        "element": "header",
        "attributes": {
            "data-auto-burger": "true",
            "data-layout": "logo_cta_menu",
        },
        "baseStyles": get_header_base_styles(
            sticky=config.sticky,
            transparent=config.transparent,
            blur_on_scroll=config.blur_on_scroll,
        ),
        "mobileStyles": get_header_mobile_styles(),
        "children": [left_section, right_section],
    }


# =============================================================================
# LAYOUT FACTORY
# =============================================================================

LAYOUT_BUILDERS = {
    "logo_menu_cta": build_layout_logo_menu_cta,
    "menu_logo_cta": build_layout_menu_logo_cta,
    "logo_cta_menu": build_layout_logo_cta_menu,
}


def build_layout(config: HeaderConfig, id_prefix: str = "header") -> dict:
    """
    Build header layout based on configuration.

    Args:
        config: Header configuration with layout selection
        id_prefix: Prefix for block IDs

    Returns:
        dict: Complete header block structure
    """
    builder = LAYOUT_BUILDERS.get(config.layout, build_layout_logo_menu_cta)
    return builder(config, id_prefix)


__all__ = [
    # Component builders
    "build_logo",
    "build_nav",
    "build_cta",
    "build_icons",
    # Layout builders
    "build_layout_logo_menu_cta",
    "build_layout_menu_logo_cta",
    "build_layout_logo_cta_menu",
    "build_layout",
    # Layout registry
    "LAYOUT_BUILDERS",
]
