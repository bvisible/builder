"""
Header Templates
Pre-built header structures for different site types.
"""

from typing import Optional
from builder.ai.schemas.header_schema import HeaderConfig, NavItem

# Backwards compatibility alias
MenuItem = NavItem


def _generate_menu_items(config: HeaderConfig, theme_styles: dict = None) -> list[dict]:
    """Generate menu item blocks from config"""
    items = []
    link_style = theme_styles.get("link", {}) if theme_styles else {}
    cta_style = theme_styles.get("cta", {}) if theme_styles else {}

    for i, item in enumerate(config.menu_items):
        if item.is_cta:
            items.append({
                "blockId": f"header-nav-cta-{i}",
                "element": "a",
                "innerHTML": item.label,
                "attributes": {
                    "href": item.href,
                    **({"target": "_blank", "rel": "noopener"} if item.is_external else {})
                },
                "baseStyles": {
                    "padding": "10px 20px",
                    "backgroundColor": "var(--primary-color)",
                    "color": "#ffffff",
                    "borderRadius": "8px",
                    "fontWeight": "600",
                    "textDecoration": "none",
                    "transition": "all 200ms ease",
                    **cta_style
                }
            })
        else:
            items.append({
                "blockId": f"header-nav-link-{i}",
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
                    "transition": "color 200ms ease",
                    **link_style
                }
            })
    return items


def _build_logo_block(config: HeaderConfig, theme_styles: dict = None) -> dict:
    """Build logo block from config"""
    logo_style = theme_styles.get("logo", {}) if theme_styles else {}

    if config.logo_type == "text":
        return {
            "blockId": "header-logo",
            "element": "a",
            "innerHTML": config.logo_value,
            "attributes": {"href": "/"},
            "baseStyles": {
                "fontSize": "22px",
                "fontWeight": "700",
                "color": "var(--text-color)",
                "textDecoration": "none",
                "letterSpacing": "-0.02em",
                **logo_style
            }
        }
    elif config.logo_type == "image":
        return {
            "blockId": "header-logo",
            "element": "a",
            "attributes": {"href": "/"},
            "baseStyles": {"textDecoration": "none"},
            "children": [{
                "blockId": "header-logo-img",
                "element": "img",
                "attributes": {
                    "src": config.logo_value,
                    "alt": config.logo_alt or "Logo"
                },
                "baseStyles": {
                    "height": "36px",
                    "width": "auto",
                    "objectFit": "contain",
                    **logo_style
                }
            }]
        }
    else:  # icon_text or svg
        return {
            "blockId": "header-logo",
            "element": "a",
            "attributes": {"href": "/"},
            "baseStyles": {
                "display": "flex",
                "alignItems": "center",
                "gap": "8px",
                "textDecoration": "none",
            },
            "children": [
                {
                    "blockId": "header-logo-icon",
                    "element": "div",
                    "innerHTML": "◆",
                    "baseStyles": {
                        "fontSize": "24px",
                        "color": "var(--primary-color)",
                    }
                },
                {
                    "blockId": "header-logo-text",
                    "element": "span",
                    "innerHTML": config.logo_value,
                    "baseStyles": {
                        "fontSize": "20px",
                        "fontWeight": "700",
                        "color": "var(--text-color)",
                    }
                }
            ]
        }


def _build_actions_block(config: HeaderConfig, theme_styles: dict = None) -> Optional[dict]:
    """Build action buttons block (cart, search, login, etc.)"""
    children = []
    icon_style = theme_styles.get("icon", {}) if theme_styles else {}
    button_style = theme_styles.get("button", {}) if theme_styles else {}

    if config.show_search:
        children.append({
            "blockId": "header-search-btn",
            "element": "button",
            "innerHTML": "🔍",
            "attributes": {"type": "button", "aria-label": "Search"},
            "baseStyles": {
                "padding": "8px",
                "background": "transparent",
                "border": "none",
                "cursor": "pointer",
                "fontSize": "18px",
                **icon_style
            }
        })

    if config.show_wishlist:
        children.append({
            "blockId": "header-wishlist",
            "element": "a",
            "innerHTML": "♡",
            "attributes": {"href": "/wishlist", "aria-label": "Wishlist"},
            "baseStyles": {
                "padding": "8px",
                "textDecoration": "none",
                "fontSize": "20px",
                "color": "var(--text-color)",
                **icon_style
            }
        })

    if config.show_cart:
        children.append({
            "blockId": "header-cart",
            "element": "a",
            "innerHTML": "🛒",
            "attributes": {"href": "/cart", "aria-label": "Cart"},
            "baseStyles": {
                "padding": "8px",
                "textDecoration": "none",
                "fontSize": "18px",
                "color": "var(--text-color)",
                **icon_style
            }
        })

    if config.show_user_menu:
        children.append({
            "blockId": "header-user",
            "element": "a",
            "innerHTML": "👤",
            "attributes": {"href": "/account", "aria-label": "Account"},
            "baseStyles": {
                "padding": "8px",
                "textDecoration": "none",
                "fontSize": "18px",
                "color": "var(--text-color)",
                **icon_style
            }
        })

    if config.show_login:
        children.append({
            "blockId": "header-login",
            "element": "a",
            "innerHTML": config.login_text,
            "attributes": {"href": "/login"},
            "baseStyles": {
                "padding": "8px 16px",
                "color": "var(--text-color)",
                "textDecoration": "none",
                "fontWeight": "500",
                **button_style
            }
        })

    if config.show_signup:
        children.append({
            "blockId": "header-signup",
            "element": "a",
            "innerHTML": config.signup_text,
            "attributes": {"href": "/signup"},
            "baseStyles": {
                "padding": "10px 20px",
                "backgroundColor": "var(--primary-color)",
                "color": "#ffffff",
                "borderRadius": "8px",
                "fontWeight": "600",
                "textDecoration": "none",
                "transition": "all 200ms ease",
            }
        })

    if not children:
        return None

    return {
        "blockId": "header-actions",
        "element": "div",
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "gap": "8px",
        },
        "children": children
    }


# =============================================================================
# HEADER TEMPLATES BY LAYOUT
# =============================================================================

HEADER_TEMPLATES = {
    "logo_left_menu_right": {
        "description": "Logo on left, navigation on right",
        "structure": {
            "blockId": "header-main",
            "element": "header",
            "baseStyles": {
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "space-between",
                "padding": "16px 24px",
                "backgroundColor": "var(--surface-color)",
            },
            "mobileStyles": {
                "padding": "12px 16px",
            },
            "children": [
                {"slot": "logo"},
                {
                    "blockId": "header-right",
                    "element": "div",
                    "baseStyles": {
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "32px",
                    },
                    "mobileStyles": {
                        "display": "none",
                    },
                    "children": [
                        {"slot": "nav"},
                        {"slot": "actions"},
                    ]
                },
                {
                    "blockId": "header-mobile-toggle",
                    "element": "button",
                    "innerHTML": "☰",
                    "attributes": {"type": "button", "aria-label": "Menu"},
                    "baseStyles": {
                        "display": "none",
                        "padding": "8px",
                        "background": "transparent",
                        "border": "none",
                        "fontSize": "24px",
                        "cursor": "pointer",
                    },
                    "mobileStyles": {
                        "display": "block",
                    }
                }
            ]
        }
    },

    "logo_center_menu_below": {
        "description": "Logo centered, navigation below",
        "structure": {
            "blockId": "header-main",
            "element": "header",
            "baseStyles": {
                "display": "flex",
                "flexDirection": "column",
                "alignItems": "center",
                "padding": "20px 24px",
                "backgroundColor": "var(--surface-color)",
                "borderBottom": "1px solid var(--border-color)",
            },
            "children": [
                {
                    "blockId": "header-top",
                    "element": "div",
                    "baseStyles": {
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "space-between",
                        "width": "100%",
                        "maxWidth": "1200px",
                        "marginBottom": "16px",
                    },
                    "children": [
                        {"slot": "actions_left"},
                        {"slot": "logo"},
                        {"slot": "actions"},
                    ]
                },
                {
                    "blockId": "header-nav-container",
                    "element": "nav",
                    "baseStyles": {
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "32px",
                    },
                    "mobileStyles": {
                        "display": "none",
                    },
                    "children": [{"slot": "nav"}]
                }
            ]
        }
    },

    "logo_left_menu_center": {
        "description": "Logo on left, navigation centered",
        "structure": {
            "blockId": "header-main",
            "element": "header",
            "baseStyles": {
                "display": "grid",
                "gridTemplateColumns": "1fr auto 1fr",
                "alignItems": "center",
                "padding": "16px 24px",
                "backgroundColor": "var(--surface-color)",
            },
            "children": [
                {"slot": "logo"},
                {
                    "blockId": "header-nav-container",
                    "element": "nav",
                    "baseStyles": {
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "center",
                        "gap": "32px",
                    },
                    "children": [{"slot": "nav"}]
                },
                {
                    "blockId": "header-right",
                    "element": "div",
                    "baseStyles": {
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "flex-end",
                        "gap": "16px",
                    },
                    "children": [{"slot": "actions"}]
                }
            ]
        }
    },

    "transparent_overlay": {
        "description": "Transparent header for hero overlays",
        "structure": {
            "blockId": "header-main",
            "element": "header",
            "baseStyles": {
                "position": "absolute",
                "top": "0",
                "left": "0",
                "right": "0",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "space-between",
                "padding": "20px 32px",
                "backgroundColor": "transparent",
                "zIndex": "100",
            },
            "children": [
                {"slot": "logo"},
                {
                    "blockId": "header-right",
                    "element": "div",
                    "baseStyles": {
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "32px",
                    },
                    "children": [
                        {"slot": "nav"},
                        {"slot": "actions"},
                    ]
                }
            ]
        }
    },

    "minimal": {
        "description": "Minimal header for portfolios",
        "structure": {
            "blockId": "header-main",
            "element": "header",
            "baseStyles": {
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "space-between",
                "padding": "24px 32px",
            },
            "children": [
                {"slot": "logo"},
                {
                    "blockId": "header-nav-container",
                    "element": "nav",
                    "baseStyles": {
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "40px",
                    },
                    "children": [{"slot": "nav"}]
                }
            ]
        }
    },
}


def get_header_template(layout: str) -> dict:
    """Get header template structure by layout name"""
    template = HEADER_TEMPLATES.get(layout)
    if template:
        return template.get("structure", {})
    return HEADER_TEMPLATES["logo_left_menu_right"]["structure"]


def build_header_from_config(config: HeaderConfig, theme: dict = None) -> dict:
    """
    Build a complete header block from configuration.

    Args:
        config: HeaderConfig with all header settings
        theme: Optional theme for styling

    Returns:
        dict: Complete header block structure
    """
    import copy

    theme_styles = theme.get("styles", {}) if theme else {}

    # Get base template
    layout = config.layout if hasattr(config, 'layout') else "logo_left_menu_right"
    template = copy.deepcopy(get_header_template(layout))

    # Build components
    logo = _build_logo_block(config, theme_styles)
    nav_items = _generate_menu_items(config, theme_styles)
    actions = _build_actions_block(config, theme_styles)

    nav_block = {
        "blockId": "header-nav",
        "element": "nav",
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "gap": "28px",
        },
        "children": nav_items
    }

    # Apply sticky/transparent styles
    if config.sticky:
        template["baseStyles"]["position"] = "sticky"
        template["baseStyles"]["top"] = "0"
        template["baseStyles"]["zIndex"] = "1000"

    if config.transparent:
        template["baseStyles"]["backgroundColor"] = "transparent"
        template["baseStyles"]["position"] = "absolute"
        template["baseStyles"]["left"] = "0"
        template["baseStyles"]["right"] = "0"

    if config.blur_on_scroll:
        template["baseStyles"]["backdropFilter"] = "blur(10px)"
        template["baseStyles"]["backgroundColor"] = "rgba(255, 255, 255, 0.8)"

    # Fill slots in template
    def fill_slots(block):
        if isinstance(block, dict):
            if block.get("slot") == "logo":
                return logo
            elif block.get("slot") == "nav":
                return nav_block
            elif block.get("slot") == "actions":
                return actions if actions else None
            elif block.get("slot") == "actions_left":
                # For e-commerce: search on left
                if config.show_search:
                    return {
                        "blockId": "header-search-left",
                        "element": "button",
                        "innerHTML": "🔍 Search",
                        "baseStyles": {
                            "padding": "8px 16px",
                            "background": "transparent",
                            "border": "1px solid var(--border-color)",
                            "borderRadius": "6px",
                            "cursor": "pointer",
                        }
                    }
                return None

            if "children" in block:
                block["children"] = [
                    filled for filled in
                    [fill_slots(child) for child in block["children"]]
                    if filled is not None
                ]

        return block

    return fill_slots(template)


__all__ = [
    "HEADER_TEMPLATES",
    "get_header_template",
    "build_header_from_config",
]
