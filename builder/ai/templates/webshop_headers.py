"""
Webshop Header Templates
Pre-built header structures optimized for e-commerce with Frappe Webshop.
These headers integrate with webshop features: cart, wishlist, search, user account.
"""

from typing import Optional
from builder.ai.schemas.header_schema import HeaderConfig, NavItem


# Default logo path for all webshop headers
DEFAULT_LOGO = "/files/logo-default.png"


def _build_webshop_logo(config: HeaderConfig = None, style: str = "standard") -> dict:
    """Build logo block for webshop headers"""
    logo_value = config.logo_value if config else DEFAULT_LOGO

    if config and config.logo_type == "text":
        return {
            "blockId": "ws-header-logo",
            "element": "a",
            "innerHTML": logo_value,
            "attributes": {"href": "/"},
            "baseStyles": {
                "fontSize": "24px",
                "fontWeight": "700",
                "color": "var(--text-color)",
                "textDecoration": "none",
                "letterSpacing": "-0.02em",
            }
        }

    return {
        "blockId": "ws-header-logo",
        "element": "a",
        "attributes": {"href": "/"},
        "baseStyles": {"textDecoration": "none", "display": "flex", "alignItems": "center"},
        "children": [{
            "blockId": "ws-header-logo-img",
            "element": "img",
            "attributes": {
                "src": logo_value,
                "alt": config.logo_alt if config else "Logo"
            },
            "baseStyles": {
                "height": "40px",
                "width": "auto",
                "objectFit": "contain",
            }
        }]
    }


def _build_webshop_nav(items: list[NavItem] = None) -> dict:
    """Build navigation for webshop"""
    default_items = [
        NavItem(label="Home", href="/"),
        NavItem(label="Products", href="/all-products"),
        NavItem(label="Categories", href="/shop-by-category"),
        NavItem(label="About", href="/about"),
        NavItem(label="Contact", href="/contact"),
    ]
    items = items or default_items

    nav_links = []
    for i, item in enumerate(items):
        nav_links.append({
            "blockId": f"ws-nav-link-{i}",
            "element": "a",
            "innerHTML": item.label,
            "attributes": {
                "href": item.href,
                **({"target": "_blank", "rel": "noopener"} if item.is_external else {})
            },
            "baseStyles": {
                "color": "var(--text-color)",
                "textDecoration": "none",
                "fontWeight": "500",
                "fontSize": "15px",
                "padding": "8px 12px",
                "borderRadius": "6px",
                "transition": "all 200ms ease",
            }
        })

    return {
        "blockId": "ws-header-nav",
        "element": "nav",
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "gap": "4px",
        },
        "mobileStyles": {
            "display": "none",
        },
        "children": nav_links
    }


def _build_webshop_actions(
    show_search: bool = True,
    show_wishlist: bool = True,
    show_cart: bool = True,
    show_user: bool = True,
    style: str = "icons"
) -> dict:
    """Build action icons for webshop (cart, wishlist, search, user)"""
    children = []

    if show_search:
        children.append({
            "blockId": "ws-action-search",
            "element": "a",
            "attributes": {"href": "/search", "aria-label": "Search"},
            "baseStyles": {
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "width": "40px",
                "height": "40px",
                "borderRadius": "50%",
                "color": "var(--text-color)",
                "textDecoration": "none",
                "transition": "background 200ms ease",
            },
            "children": [{
                "blockId": "ws-search-icon",
                "element": "svg",
                "attributes": {
                    "xmlns": "http://www.w3.org/2000/svg",
                    "width": "20",
                    "height": "20",
                    "viewBox": "0 0 24 24",
                    "fill": "none",
                    "stroke": "currentColor",
                    "stroke-width": "2",
                    "stroke-linecap": "round",
                    "stroke-linejoin": "round"
                },
                "children": [{
                    "blockId": "ws-search-icon-circle",
                    "element": "circle",
                    "attributes": {"cx": "11", "cy": "11", "r": "8"}
                }, {
                    "blockId": "ws-search-icon-line",
                    "element": "line",
                    "attributes": {"x1": "21", "y1": "21", "x2": "16.65", "y2": "16.65"}
                }]
            }]
        })

    if show_wishlist:
        children.append({
            "blockId": "ws-action-wishlist",
            "element": "a",
            "attributes": {"href": "/wishlist", "aria-label": "Wishlist"},
            "baseStyles": {
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "width": "40px",
                "height": "40px",
                "borderRadius": "50%",
                "color": "var(--text-color)",
                "textDecoration": "none",
                "transition": "background 200ms ease",
            },
            "children": [{
                "blockId": "ws-wishlist-icon",
                "element": "svg",
                "attributes": {
                    "xmlns": "http://www.w3.org/2000/svg",
                    "width": "20",
                    "height": "20",
                    "viewBox": "0 0 24 24",
                    "fill": "none",
                    "stroke": "currentColor",
                    "stroke-width": "2",
                    "stroke-linecap": "round",
                    "stroke-linejoin": "round"
                },
                "children": [{
                    "blockId": "ws-wishlist-icon-path",
                    "element": "path",
                    "attributes": {
                        "d": "M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"
                    }
                }]
            }]
        })

    if show_cart:
        children.append({
            "blockId": "ws-action-cart",
            "element": "a",
            "attributes": {"href": "/cart", "aria-label": "Cart"},
            "baseStyles": {
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "width": "40px",
                "height": "40px",
                "borderRadius": "50%",
                "color": "var(--text-color)",
                "textDecoration": "none",
                "position": "relative",
                "transition": "background 200ms ease",
            },
            "children": [{
                "blockId": "ws-cart-icon",
                "element": "svg",
                "attributes": {
                    "xmlns": "http://www.w3.org/2000/svg",
                    "width": "20",
                    "height": "20",
                    "viewBox": "0 0 24 24",
                    "fill": "none",
                    "stroke": "currentColor",
                    "stroke-width": "2",
                    "stroke-linecap": "round",
                    "stroke-linejoin": "round"
                },
                "children": [{
                    "blockId": "ws-cart-icon-path",
                    "element": "path",
                    "attributes": {
                        "d": "M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"
                    }
                }, {
                    "blockId": "ws-cart-icon-line",
                    "element": "line",
                    "attributes": {"x1": "3", "y1": "6", "x2": "21", "y2": "6"}
                }, {
                    "blockId": "ws-cart-icon-path2",
                    "element": "path",
                    "attributes": {"d": "M16 10a4 4 0 0 1-8 0"}
                }]
            }]
        })

    if show_user:
        children.append({
            "blockId": "ws-action-user",
            "element": "a",
            "attributes": {"href": "/me", "aria-label": "Account"},
            "baseStyles": {
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "width": "40px",
                "height": "40px",
                "borderRadius": "50%",
                "color": "var(--text-color)",
                "textDecoration": "none",
                "transition": "background 200ms ease",
            },
            "children": [{
                "blockId": "ws-user-icon",
                "element": "svg",
                "attributes": {
                    "xmlns": "http://www.w3.org/2000/svg",
                    "width": "20",
                    "height": "20",
                    "viewBox": "0 0 24 24",
                    "fill": "none",
                    "stroke": "currentColor",
                    "stroke-width": "2",
                    "stroke-linecap": "round",
                    "stroke-linejoin": "round"
                },
                "children": [{
                    "blockId": "ws-user-icon-path",
                    "element": "path",
                    "attributes": {"d": "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"}
                }, {
                    "blockId": "ws-user-icon-circle",
                    "element": "circle",
                    "attributes": {"cx": "12", "cy": "7", "r": "4"}
                }]
            }]
        })

    return {
        "blockId": "ws-header-actions",
        "element": "div",
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "gap": "4px",
        },
        "children": children
    }


def _build_mobile_toggle() -> dict:
    """Build mobile menu toggle button"""
    return {
        "blockId": "ws-mobile-toggle",
        "element": "button",
        "attributes": {"type": "button", "aria-label": "Menu"},
        "baseStyles": {
            "display": "none",
            "alignItems": "center",
            "justifyContent": "center",
            "width": "40px",
            "height": "40px",
            "padding": "0",
            "background": "transparent",
            "border": "none",
            "cursor": "pointer",
            "color": "var(--text-color)",
        },
        "mobileStyles": {
            "display": "flex",
        },
        "children": [{
            "blockId": "ws-mobile-toggle-icon",
            "element": "svg",
            "attributes": {
                "xmlns": "http://www.w3.org/2000/svg",
                "width": "24",
                "height": "24",
                "viewBox": "0 0 24 24",
                "fill": "none",
                "stroke": "currentColor",
                "stroke-width": "2",
                "stroke-linecap": "round",
                "stroke-linejoin": "round"
            },
            "children": [{
                "blockId": "ws-toggle-line1",
                "element": "line",
                "attributes": {"x1": "3", "y1": "12", "x2": "21", "y2": "12"}
            }, {
                "blockId": "ws-toggle-line2",
                "element": "line",
                "attributes": {"x1": "3", "y1": "6", "x2": "21", "y2": "6"}
            }, {
                "blockId": "ws-toggle-line3",
                "element": "line",
                "attributes": {"x1": "3", "y1": "18", "x2": "21", "y2": "18"}
            }]
        }]
    }


# =============================================================================
# WEBSHOP HEADER VARIATIONS
# =============================================================================

WEBSHOP_HEADER_VARIATIONS = {
    "webshop_standard": {
        "name": "Standard E-commerce",
        "description": "Classic e-commerce header: logo left, nav center, actions right",
        "preview": "Logo | -------- Nav -------- | Search Wishlist Cart User",
    },

    "webshop_centered": {
        "name": "Centered Logo",
        "description": "Logo centered with nav and actions on sides",
        "preview": "Nav | -------- Logo -------- | Actions",
    },

    "webshop_minimal": {
        "name": "Minimal",
        "description": "Clean minimal header for boutique shops",
        "preview": "Logo | -------- | Cart User",
    },

    "webshop_mega": {
        "name": "Mega Menu",
        "description": "Header with category mega menu support",
        "preview": "Logo | Categories Nav | Actions",
    },

    "webshop_transparent": {
        "name": "Transparent Overlay",
        "description": "Transparent header for hero sections",
        "preview": "Logo | Nav | Actions (overlay)",
    },

    "webshop_split": {
        "name": "Split Navigation",
        "description": "Navigation split on both sides of logo",
        "preview": "Nav-Left | Logo | Nav-Right | Actions",
    },
}


def build_webshop_header_standard(config: HeaderConfig = None) -> dict:
    """
    Standard e-commerce header.
    Layout: Logo left | Nav center | Actions right
    """
    return {
        "blockId": "ws-header",
        "element": "header",
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
            "padding": "12px 24px",
            "backgroundColor": "var(--surface-color, #ffffff)",
            "borderBottom": "1px solid var(--border-color, #e5e7eb)",
            "position": "sticky",
            "top": "0",
            "zIndex": "1000",
        },
        "mobileStyles": {
            "padding": "12px 16px",
        },
        "children": [
            _build_webshop_logo(config),
            _build_webshop_nav(config.menu_items if config else None),
            {
                "blockId": "ws-header-right",
                "element": "div",
                "baseStyles": {
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "8px",
                },
                "children": [
                    _build_webshop_actions(),
                    _build_mobile_toggle(),
                ]
            }
        ]
    }


def build_webshop_header_centered(config: HeaderConfig = None) -> dict:
    """
    Centered logo header.
    Layout: Nav left | Logo center | Actions right
    """
    return {
        "blockId": "ws-header",
        "element": "header",
        "baseStyles": {
            "display": "grid",
            "gridTemplateColumns": "1fr auto 1fr",
            "alignItems": "center",
            "padding": "16px 24px",
            "backgroundColor": "var(--surface-color, #ffffff)",
            "borderBottom": "1px solid var(--border-color, #e5e7eb)",
            "position": "sticky",
            "top": "0",
            "zIndex": "1000",
        },
        "mobileStyles": {
            "display": "flex",
            "justifyContent": "space-between",
            "padding": "12px 16px",
        },
        "children": [
            {
                "blockId": "ws-header-left",
                "element": "div",
                "baseStyles": {
                    "display": "flex",
                    "alignItems": "center",
                },
                "mobileStyles": {
                    "display": "none",
                },
                "children": [_build_webshop_nav(config.menu_items if config else None)]
            },
            _build_webshop_logo(config),
            {
                "blockId": "ws-header-right",
                "element": "div",
                "baseStyles": {
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "flex-end",
                    "gap": "8px",
                },
                "children": [
                    _build_webshop_actions(),
                    _build_mobile_toggle(),
                ]
            }
        ]
    }


def build_webshop_header_minimal(config: HeaderConfig = None) -> dict:
    """
    Minimal header for boutique shops.
    Layout: Logo left | spacer | Cart + User only
    """
    return {
        "blockId": "ws-header",
        "element": "header",
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
            "padding": "20px 32px",
            "backgroundColor": "var(--surface-color, #ffffff)",
            "position": "sticky",
            "top": "0",
            "zIndex": "1000",
        },
        "mobileStyles": {
            "padding": "16px 20px",
        },
        "children": [
            _build_webshop_logo(config),
            {
                "blockId": "ws-header-right",
                "element": "div",
                "baseStyles": {
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "16px",
                },
                "children": [
                    _build_webshop_nav(config.menu_items if config else [
                        NavItem(label="Shop", href="/all-products"),
                        NavItem(label="About", href="/about"),
                    ]),
                    _build_webshop_actions(
                        show_search=False,
                        show_wishlist=False,
                        show_cart=True,
                        show_user=True
                    ),
                    _build_mobile_toggle(),
                ]
            }
        ]
    }


def build_webshop_header_mega(config: HeaderConfig = None) -> dict:
    """
    Header with mega menu support for categories.
    Layout: Logo | Categories dropdown + Nav | Actions
    """
    categories_nav = {
        "blockId": "ws-categories-nav",
        "element": "div",
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "gap": "24px",
        },
        "mobileStyles": {
            "display": "none",
        },
        "children": [
            {
                "blockId": "ws-categories-btn",
                "element": "button",
                "attributes": {"type": "button"},
                "baseStyles": {
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "8px",
                    "padding": "10px 16px",
                    "backgroundColor": "var(--primary-color)",
                    "color": "#ffffff",
                    "border": "none",
                    "borderRadius": "8px",
                    "fontWeight": "600",
                    "fontSize": "14px",
                    "cursor": "pointer",
                },
                "children": [
                    {
                        "blockId": "ws-categories-icon",
                        "element": "svg",
                        "attributes": {
                            "xmlns": "http://www.w3.org/2000/svg",
                            "width": "18",
                            "height": "18",
                            "viewBox": "0 0 24 24",
                            "fill": "none",
                            "stroke": "currentColor",
                            "stroke-width": "2"
                        },
                        "children": [{
                            "blockId": "ws-cat-line1",
                            "element": "line",
                            "attributes": {"x1": "3", "y1": "12", "x2": "21", "y2": "12"}
                        }, {
                            "blockId": "ws-cat-line2",
                            "element": "line",
                            "attributes": {"x1": "3", "y1": "6", "x2": "21", "y2": "6"}
                        }, {
                            "blockId": "ws-cat-line3",
                            "element": "line",
                            "attributes": {"x1": "3", "y1": "18", "x2": "21", "y2": "18"}
                        }]
                    },
                    {
                        "blockId": "ws-categories-text",
                        "element": "span",
                        "innerHTML": "Categories",
                    }
                ]
            },
            _build_webshop_nav(config.menu_items if config else None),
        ]
    }

    return {
        "blockId": "ws-header",
        "element": "header",
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
            "padding": "12px 24px",
            "backgroundColor": "var(--surface-color, #ffffff)",
            "borderBottom": "1px solid var(--border-color, #e5e7eb)",
            "position": "sticky",
            "top": "0",
            "zIndex": "1000",
        },
        "children": [
            _build_webshop_logo(config),
            categories_nav,
            {
                "blockId": "ws-header-right",
                "element": "div",
                "baseStyles": {
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "8px",
                },
                "children": [
                    _build_webshop_actions(),
                    _build_mobile_toggle(),
                ]
            }
        ]
    }


def build_webshop_header_transparent(config: HeaderConfig = None) -> dict:
    """
    Transparent header for hero overlays.
    Positioned absolute over content with light text.
    """
    # Override styles for transparent/light text
    logo = _build_webshop_logo(config)
    if "baseStyles" in logo:
        logo["baseStyles"]["color"] = "#ffffff"
    for child in logo.get("children", []):
        if "baseStyles" in child:
            child["baseStyles"]["filter"] = "brightness(0) invert(1)"

    nav = _build_webshop_nav(config.menu_items if config else None)
    for child in nav.get("children", []):
        if "baseStyles" in child:
            child["baseStyles"]["color"] = "#ffffff"

    actions = _build_webshop_actions()
    for child in actions.get("children", []):
        if "baseStyles" in child:
            child["baseStyles"]["color"] = "#ffffff"

    return {
        "blockId": "ws-header",
        "element": "header",
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
            "padding": "20px 32px",
            "backgroundColor": "transparent",
            "position": "absolute",
            "top": "0",
            "left": "0",
            "right": "0",
            "zIndex": "100",
        },
        "mobileStyles": {
            "padding": "16px 20px",
        },
        "children": [
            logo,
            nav,
            {
                "blockId": "ws-header-right",
                "element": "div",
                "baseStyles": {
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "8px",
                },
                "children": [
                    actions,
                    _build_mobile_toggle(),
                ]
            }
        ]
    }


def build_webshop_header_split(config: HeaderConfig = None) -> dict:
    """
    Split navigation header.
    Layout: Nav-Left | Logo | Nav-Right | Actions
    """
    items = config.menu_items if config else [
        NavItem(label="Home", href="/"),
        NavItem(label="Products", href="/all-products"),
        NavItem(label="Categories", href="/shop-by-category"),
        NavItem(label="About", href="/about"),
        NavItem(label="Contact", href="/contact"),
    ]

    # Split items in half
    mid = len(items) // 2
    left_items = items[:mid]
    right_items = items[mid:]

    left_nav = {
        "blockId": "ws-nav-left",
        "element": "nav",
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "gap": "24px",
        },
        "mobileStyles": {"display": "none"},
        "children": [
            {
                "blockId": f"ws-nav-left-{i}",
                "element": "a",
                "innerHTML": item.label,
                "attributes": {"href": item.href},
                "baseStyles": {
                    "color": "var(--text-color)",
                    "textDecoration": "none",
                    "fontWeight": "500",
                    "fontSize": "15px",
                }
            }
            for i, item in enumerate(left_items)
        ]
    }

    right_nav = {
        "blockId": "ws-nav-right",
        "element": "nav",
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "gap": "24px",
        },
        "mobileStyles": {"display": "none"},
        "children": [
            {
                "blockId": f"ws-nav-right-{i}",
                "element": "a",
                "innerHTML": item.label,
                "attributes": {"href": item.href},
                "baseStyles": {
                    "color": "var(--text-color)",
                    "textDecoration": "none",
                    "fontWeight": "500",
                    "fontSize": "15px",
                }
            }
            for i, item in enumerate(right_items)
        ]
    }

    return {
        "blockId": "ws-header",
        "element": "header",
        "baseStyles": {
            "display": "grid",
            "gridTemplateColumns": "1fr auto 1fr auto",
            "alignItems": "center",
            "gap": "32px",
            "padding": "16px 32px",
            "backgroundColor": "var(--surface-color, #ffffff)",
            "borderBottom": "1px solid var(--border-color, #e5e7eb)",
            "position": "sticky",
            "top": "0",
            "zIndex": "1000",
        },
        "mobileStyles": {
            "display": "flex",
            "justifyContent": "space-between",
            "padding": "12px 16px",
        },
        "children": [
            left_nav,
            _build_webshop_logo(config),
            right_nav,
            {
                "blockId": "ws-header-actions-wrap",
                "element": "div",
                "baseStyles": {
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "8px",
                },
                "children": [
                    _build_webshop_actions(show_search=False),
                    _build_mobile_toggle(),
                ]
            }
        ]
    }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def build_webshop_header(
    variation: str = "webshop_standard",
    config: HeaderConfig = None
) -> dict:
    """
    Build a webshop header from a variation name.

    Args:
        variation: Name of header variation (see WEBSHOP_HEADER_VARIATIONS)
        config: Optional HeaderConfig for customization

    Returns:
        dict: Complete header block structure
    """
    builders = {
        "webshop_standard": build_webshop_header_standard,
        "webshop_centered": build_webshop_header_centered,
        "webshop_minimal": build_webshop_header_minimal,
        "webshop_mega": build_webshop_header_mega,
        "webshop_transparent": build_webshop_header_transparent,
        "webshop_split": build_webshop_header_split,
    }

    builder = builders.get(variation, build_webshop_header_standard)
    return builder(config)


def get_webshop_header_variations() -> dict:
    """Get available webshop header variations with descriptions"""
    return WEBSHOP_HEADER_VARIATIONS


__all__ = [
    "build_webshop_header",
    "build_webshop_header_standard",
    "build_webshop_header_centered",
    "build_webshop_header_minimal",
    "build_webshop_header_mega",
    "build_webshop_header_transparent",
    "build_webshop_header_split",
    "get_webshop_header_variations",
    "WEBSHOP_HEADER_VARIATIONS",
]
