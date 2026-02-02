"""
Header Icons Module
SVG icon components for the configurable header system.

Icons available:
- Search (magnifying glass)
- Cart (shopping bag)
- Wishlist (heart)
- User (person)
- Search bar (input with icon)
"""

from builder.ai.templates.headers.base import (
    generate_unique_id,
    get_icon_button_styles,
    get_icons_group_styles,
    get_search_bar_styles,
    get_search_input_styles,
    get_svg_icon_attrs,
    ICON_SVG_SIZE,
)


# =============================================================================
# SVG ICON PATHS
# =============================================================================

# Search icon (magnifying glass)
SEARCH_ICON_CHILDREN = [
    {
        "blockId": "search-icon-circle",
        "element": "circle",
        "attributes": {"cx": "11", "cy": "11", "r": "8"}
    },
    {
        "blockId": "search-icon-line",
        "element": "line",
        "attributes": {"x1": "21", "y1": "21", "x2": "16.65", "y2": "16.65"}
    }
]

# Cart icon (shopping bag)
CART_ICON_CHILDREN = [
    {
        "blockId": "cart-icon-path",
        "element": "path",
        "attributes": {
            "d": "M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"
        }
    },
    {
        "blockId": "cart-icon-line",
        "element": "line",
        "attributes": {"x1": "3", "y1": "6", "x2": "21", "y2": "6"}
    },
    {
        "blockId": "cart-icon-path2",
        "element": "path",
        "attributes": {"d": "M16 10a4 4 0 0 1-8 0"}
    }
]

# Wishlist icon (heart)
WISHLIST_ICON_CHILDREN = [
    {
        "blockId": "wishlist-icon-path",
        "element": "path",
        "attributes": {
            "d": "M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"
        }
    }
]

# User icon (person)
USER_ICON_CHILDREN = [
    {
        "blockId": "user-icon-path",
        "element": "path",
        "attributes": {"d": "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"}
    },
    {
        "blockId": "user-icon-circle",
        "element": "circle",
        "attributes": {"cx": "12", "cy": "7", "r": "4"}
    }
]


# =============================================================================
# ICON BUILDER FUNCTIONS
# =============================================================================

def build_search_icon(
    href: str = "/search",
    id_prefix: str = "header"
) -> dict:
    """
    Build search icon button (magnifying glass).

    Args:
        href: Link destination for the search icon
        id_prefix: Prefix for block IDs

    Returns:
        dict: Complete search icon block
    """
    icon_id = f"{id_prefix}-search-icon"

    return {
        "blockId": f"{id_prefix}-search-btn",
        "element": "a",
        "attributes": {"href": href, "aria-label": "Search"},
        "baseStyles": get_icon_button_styles(),
        "children": [{
            "blockId": icon_id,
            "element": "svg",
            "attributes": get_svg_icon_attrs(),
            "children": [
                {**child, "blockId": f"{icon_id}-{i}"}
                for i, child in enumerate(SEARCH_ICON_CHILDREN)
            ]
        }]
    }


def build_cart_icon(
    href: str = "/cart",
    id_prefix: str = "header"
) -> dict:
    """
    Build cart icon button (shopping bag).

    Args:
        href: Link destination for the cart icon
        id_prefix: Prefix for block IDs

    Returns:
        dict: Complete cart icon block
    """
    icon_id = f"{id_prefix}-cart-icon"

    return {
        "blockId": f"{id_prefix}-cart-btn",
        "element": "a",
        "attributes": {"href": href, "aria-label": "Cart"},
        "baseStyles": get_icon_button_styles(),
        "children": [{
            "blockId": icon_id,
            "element": "svg",
            "attributes": get_svg_icon_attrs(),
            "children": [
                {**child, "blockId": f"{icon_id}-{i}"}
                for i, child in enumerate(CART_ICON_CHILDREN)
            ]
        }]
    }


def build_wishlist_icon(
    href: str = "/wishlist",
    id_prefix: str = "header"
) -> dict:
    """
    Build wishlist icon button (heart).

    Args:
        href: Link destination for the wishlist icon
        id_prefix: Prefix for block IDs

    Returns:
        dict: Complete wishlist icon block
    """
    icon_id = f"{id_prefix}-wishlist-icon"

    return {
        "blockId": f"{id_prefix}-wishlist-btn",
        "element": "a",
        "attributes": {"href": href, "aria-label": "Wishlist"},
        "baseStyles": get_icon_button_styles(),
        "children": [{
            "blockId": icon_id,
            "element": "svg",
            "attributes": get_svg_icon_attrs(),
            "children": [
                {**child, "blockId": f"{icon_id}-{i}"}
                for i, child in enumerate(WISHLIST_ICON_CHILDREN)
            ]
        }]
    }


def build_user_icon(
    href: str = "/account",
    id_prefix: str = "header"
) -> dict:
    """
    Build user icon button (person silhouette).

    Args:
        href: Link destination for the user icon
        id_prefix: Prefix for block IDs

    Returns:
        dict: Complete user icon block
    """
    icon_id = f"{id_prefix}-user-icon"

    return {
        "blockId": f"{id_prefix}-user-btn",
        "element": "a",
        "attributes": {"href": href, "aria-label": "Account"},
        "baseStyles": get_icon_button_styles(),
        "children": [{
            "blockId": icon_id,
            "element": "svg",
            "attributes": get_svg_icon_attrs(),
            "children": [
                {**child, "blockId": f"{icon_id}-{i}"}
                for i, child in enumerate(USER_ICON_CHILDREN)
            ]
        }]
    }


def build_search_bar(
    placeholder: str = "Search...",
    id_prefix: str = "header"
) -> dict:
    """
    Build search bar with input and icon.

    Args:
        placeholder: Placeholder text for the input
        id_prefix: Prefix for block IDs

    Returns:
        dict: Complete search bar block
    """
    icon_id = f"{id_prefix}-searchbar-icon"

    return {
        "blockId": f"{id_prefix}-search-bar",
        "element": "div",
        "baseStyles": get_search_bar_styles(),
        "children": [
            # Search icon inside the bar
            {
                "blockId": icon_id,
                "element": "svg",
                "attributes": {
                    **get_svg_icon_attrs("16"),
                    "style": "flex-shrink: 0; opacity: 0.5;"
                },
                "children": [
                    {**child, "blockId": f"{icon_id}-{i}"}
                    for i, child in enumerate(SEARCH_ICON_CHILDREN)
                ]
            },
            # Input field
            {
                "blockId": f"{id_prefix}-search-input",
                "element": "input",
                "attributes": {
                    "type": "text",
                    "placeholder": placeholder,
                    "aria-label": "Search"
                },
                "baseStyles": get_search_input_styles(),
            }
        ]
    }


def build_icons_group(
    show_search_bar: bool = False,
    show_search: bool = False,
    show_wishlist: bool = False,
    show_cart: bool = False,
    show_user: bool = False,
    search_url: str = "/search",
    wishlist_url: str = "/wishlist",
    cart_url: str = "/cart",
    user_url: str = "/account",
    id_prefix: str = "header"
) -> dict | None:
    """
    Build the icons group container with selected icons.

    Display order: search_bar → search → wishlist → cart → user

    Args:
        show_search_bar: Show full search bar (takes precedence over search icon)
        show_search: Show search icon (ignored if search_bar is shown)
        show_wishlist: Show wishlist icon
        show_cart: Show cart icon
        show_user: Show user icon
        search_url: URL for search icon
        wishlist_url: URL for wishlist icon
        cart_url: URL for cart icon
        user_url: URL for user icon
        id_prefix: Prefix for block IDs

    Returns:
        dict: Icons group block, or None if no icons are shown
    """
    children = []

    # Search bar takes precedence over search icon
    if show_search_bar:
        children.append(build_search_bar(id_prefix=id_prefix))
    elif show_search:
        children.append(build_search_icon(href=search_url, id_prefix=id_prefix))

    if show_wishlist:
        children.append(build_wishlist_icon(href=wishlist_url, id_prefix=id_prefix))

    if show_cart:
        children.append(build_cart_icon(href=cart_url, id_prefix=id_prefix))

    if show_user:
        children.append(build_user_icon(href=user_url, id_prefix=id_prefix))

    if not children:
        return None

    return {
        "blockId": f"{id_prefix}-icons-group",
        "element": "div",
        "baseStyles": get_icons_group_styles(),
        "children": children
    }


__all__ = [
    # Icon builders
    "build_search_icon",
    "build_cart_icon",
    "build_wishlist_icon",
    "build_user_icon",
    "build_search_bar",
    "build_icons_group",
    # Icon data (for reuse)
    "SEARCH_ICON_CHILDREN",
    "CART_ICON_CHILDREN",
    "WISHLIST_ICON_CHILDREN",
    "USER_ICON_CHILDREN",
]
