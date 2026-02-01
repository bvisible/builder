"""
Footer Templates
Pre-built footer structures for different site types.
"""

import datetime
from typing import Optional
from builder.ai.schemas.footer_schema import FooterConfig, FooterColumn, SocialLinks


def _build_social_links_block(social: SocialLinks, theme_styles: dict = None) -> Optional[dict]:
    """Build social media links block"""
    if not social:
        return None

    active_links = social.get_active_links()
    if not active_links:
        return None

    # Social icons (using unicode/emoji for simplicity - can be replaced with SVG)
    social_icons = {
        "facebook": "𝐟",
        "twitter": "𝕏",
        "instagram": "📷",
        "linkedin": "in",
        "youtube": "▶",
        "github": "⌘",
        "discord": "💬",
        "tiktok": "♪",
    }

    icon_style = theme_styles.get("social_icon", {}) if theme_styles else {}

    children = []
    for platform, url in active_links.items():
        children.append({
            "blockId": f"footer-social-{platform}",
            "element": "a",
            "innerHTML": social_icons.get(platform, platform[0].upper()),
            "attributes": {
                "href": url,
                "target": "_blank",
                "rel": "noopener noreferrer",
                "aria-label": platform.title()
            },
            "baseStyles": {
                "width": "40px",
                "height": "40px",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "borderRadius": "50%",
                "backgroundColor": "var(--border-color)",
                "color": "var(--text-color)",
                "textDecoration": "none",
                "fontSize": "16px",
                "transition": "all 200ms ease",
                **icon_style
            }
        })

    return {
        "blockId": "footer-social",
        "element": "div",
        "baseStyles": {
            "display": "flex",
            "gap": "12px",
        },
        "children": children
    }


def _build_link_column(column: FooterColumn, index: int, theme_styles: dict = None) -> dict:
    """Build a column of footer links"""
    link_style = theme_styles.get("link", {}) if theme_styles else {}

    links = []
    for j, link in enumerate(column.links):
        links.append({
            "blockId": f"footer-link-{index}-{j}",
            "element": "li",
            "baseStyles": {"marginBottom": "12px"},
            "children": [{
                "blockId": f"footer-link-{index}-{j}-a",
                "element": "a",
                "innerHTML": link.label,
                "attributes": {
                    "href": link.href,
                    **({"target": "_blank", "rel": "noopener"} if link.is_external else {})
                },
                "baseStyles": {
                    "color": "var(--muted-color)",
                    "textDecoration": "none",
                    "fontSize": "14px",
                    "transition": "color 200ms ease",
                    **link_style
                }
            }]
        })

    return {
        "blockId": f"footer-col-{index}",
        "element": "div",
        "children": [
            {
                "blockId": f"footer-col-{index}-title",
                "element": "h4",
                "innerHTML": column.title,
                "baseStyles": {
                    "fontSize": "14px",
                    "fontWeight": "600",
                    "textTransform": "uppercase",
                    "letterSpacing": "0.05em",
                    "marginBottom": "20px",
                    "color": "var(--text-color)",
                }
            },
            {
                "blockId": f"footer-col-{index}-links",
                "element": "ul",
                "baseStyles": {
                    "listStyle": "none",
                    "padding": "0",
                    "margin": "0",
                },
                "children": links
            }
        ]
    }


def _build_newsletter_block(config: FooterConfig, theme_styles: dict = None) -> Optional[dict]:
    """Build newsletter signup block"""
    if not config.show_newsletter or not config.newsletter:
        return None

    newsletter = config.newsletter
    input_style = theme_styles.get("input", {}) if theme_styles else {}
    button_style = theme_styles.get("button", {}) if theme_styles else {}

    return {
        "blockId": "footer-newsletter",
        "element": "div",
        "baseStyles": {
            "maxWidth": "400px",
        },
        "children": [
            {
                "blockId": "footer-newsletter-title",
                "element": "h4",
                "innerHTML": newsletter.title,
                "baseStyles": {
                    "fontSize": "16px",
                    "fontWeight": "600",
                    "marginBottom": "8px",
                    "color": "var(--text-color)",
                }
            },
            {
                "blockId": "footer-newsletter-desc",
                "element": "p",
                "innerHTML": newsletter.description or "Get the latest updates in your inbox.",
                "baseStyles": {
                    "color": "var(--muted-color)",
                    "fontSize": "14px",
                    "marginBottom": "16px",
                }
            },
            {
                "blockId": "footer-newsletter-form",
                "element": "form",
                "baseStyles": {
                    "display": "flex",
                    "gap": "8px",
                },
                "mobileStyles": {
                    "flexDirection": "column",
                },
                "children": [
                    {
                        "blockId": "footer-newsletter-input",
                        "element": "input",
                        "attributes": {
                            "type": "email",
                            "placeholder": newsletter.placeholder,
                            "required": "true"
                        },
                        "baseStyles": {
                            "flex": "1",
                            "padding": "12px 16px",
                            "border": "1px solid var(--border-color)",
                            "borderRadius": "8px",
                            "fontSize": "14px",
                            "backgroundColor": "var(--surface-color)",
                            **input_style
                        }
                    },
                    {
                        "blockId": "footer-newsletter-button",
                        "element": "button",
                        "innerHTML": newsletter.button_text,
                        "attributes": {"type": "submit"},
                        "baseStyles": {
                            "padding": "12px 24px",
                            "backgroundColor": "var(--primary-color)",
                            "color": "#ffffff",
                            "border": "none",
                            "borderRadius": "8px",
                            "fontWeight": "600",
                            "cursor": "pointer",
                            "transition": "all 200ms ease",
                            **button_style
                        }
                    }
                ]
            },
            {
                "blockId": "footer-newsletter-privacy",
                "element": "p",
                "innerHTML": newsletter.privacy_text or "We respect your privacy.",
                "baseStyles": {
                    "color": "var(--muted-color)",
                    "fontSize": "12px",
                    "marginTop": "12px",
                }
            } if newsletter.privacy_text else None
        ]
    }


def _build_brand_block(config: FooterConfig, theme_styles: dict = None) -> dict:
    """Build brand/logo section"""
    children = []

    if config.show_logo and config.logo_value:
        children.append({
            "blockId": "footer-logo",
            "element": "div",
            "innerHTML": config.logo_value,
            "baseStyles": {
                "fontSize": "22px",
                "fontWeight": "700",
                "color": "var(--text-color)",
                "marginBottom": "16px",
            }
        })

    if config.tagline:
        children.append({
            "blockId": "footer-tagline",
            "element": "p",
            "innerHTML": config.tagline,
            "baseStyles": {
                "color": "var(--muted-color)",
                "fontSize": "14px",
                "lineHeight": "1.6",
                "marginBottom": "20px",
                "maxWidth": "300px",
            }
        })

    if config.show_social and config.social_links:
        social_block = _build_social_links_block(config.social_links, theme_styles)
        if social_block:
            children.append(social_block)

    return {
        "blockId": "footer-brand",
        "element": "div",
        "children": children
    }


def _build_bottom_section(config: FooterConfig, theme_styles: dict = None) -> dict:
    """Build bottom section with copyright and legal links"""
    year = datetime.datetime.now().year if config.show_year else ""
    company = config.company_name or "Company"
    copyright_text = f"© {year} {company}. {config.copyright_text}"

    legal_links = []
    for i, link in enumerate(config.legal_links or []):
        legal_links.append({
            "blockId": f"footer-legal-{i}",
            "element": "a",
            "innerHTML": link.label,
            "attributes": {"href": link.href},
            "baseStyles": {
                "color": "var(--muted-color)",
                "fontSize": "13px",
                "textDecoration": "none",
                "transition": "color 200ms ease",
            }
        })

    return {
        "blockId": "footer-bottom",
        "element": "div",
        "baseStyles": {
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "paddingTop": "24px",
            "borderTop": "1px solid var(--border-color)",
            "flexWrap": "wrap",
            "gap": "16px",
        },
        "mobileStyles": {
            "flexDirection": "column",
            "textAlign": "center",
        },
        "children": [
            {
                "blockId": "footer-copyright",
                "element": "p",
                "innerHTML": copyright_text,
                "baseStyles": {
                    "color": "var(--muted-color)",
                    "fontSize": "13px",
                    "margin": "0",
                }
            },
            {
                "blockId": "footer-legal",
                "element": "div",
                "baseStyles": {
                    "display": "flex",
                    "gap": "24px",
                },
                "children": legal_links
            } if legal_links else None
        ]
    }


def _build_payment_methods(config: FooterConfig) -> Optional[dict]:
    """Build payment methods icons for e-commerce"""
    if not config.show_payment_methods:
        return None

    methods = config.payment_methods or ["visa", "mastercard", "paypal", "stripe"]

    # Simple text representation - can be replaced with images
    method_display = {
        "visa": "VISA",
        "mastercard": "MC",
        "paypal": "PayPal",
        "stripe": "Stripe",
        "amex": "AMEX",
        "apple_pay": "Apple Pay",
        "google_pay": "G Pay",
    }

    children = []
    for method in methods:
        children.append({
            "blockId": f"footer-payment-{method}",
            "element": "span",
            "innerHTML": method_display.get(method, method),
            "baseStyles": {
                "padding": "4px 8px",
                "fontSize": "11px",
                "backgroundColor": "var(--surface-color)",
                "borderRadius": "4px",
                "color": "var(--muted-color)",
            }
        })

    return {
        "blockId": "footer-payments",
        "element": "div",
        "baseStyles": {
            "display": "flex",
            "gap": "8px",
            "flexWrap": "wrap",
            "alignItems": "center",
        },
        "children": [
            {
                "blockId": "footer-payments-label",
                "element": "span",
                "innerHTML": "We accept:",
                "baseStyles": {
                    "fontSize": "12px",
                    "color": "var(--muted-color)",
                    "marginRight": "8px",
                }
            },
            *children
        ]
    }


# =============================================================================
# FOOTER TEMPLATES BY TYPE
# =============================================================================

FOOTER_TEMPLATES = {
    "minimal": {
        "description": "Simple centered footer",
        "structure": {
            "blockId": "footer-main",
            "element": "footer",
            "baseStyles": {
                "padding": "48px 24px",
                "textAlign": "center",
                "backgroundColor": "var(--surface-color)",
            },
            "children": [
                {"slot": "social"},
                {"slot": "copyright"},
            ]
        }
    },

    "columns": {
        "description": "Multi-column footer layout",
        "structure": {
            "blockId": "footer-main",
            "element": "footer",
            "baseStyles": {
                "padding": "64px 24px 24px",
                "backgroundColor": "var(--surface-color)",
            },
            "children": [
                {
                    "blockId": "footer-container",
                    "element": "div",
                    "baseStyles": {
                        "maxWidth": "1200px",
                        "marginLeft": "auto",
                        "marginRight": "auto",
                    },
                    "children": [
                        {"slot": "top_section"},
                        {"slot": "bottom_section"},
                    ]
                }
            ]
        }
    },

    "two_rows": {
        "description": "Two-row layout with links above copyright",
        "structure": {
            "blockId": "footer-main",
            "element": "footer",
            "baseStyles": {
                "padding": "48px 24px 24px",
                "backgroundColor": "var(--surface-color)",
            },
            "children": [
                {
                    "blockId": "footer-links-row",
                    "element": "div",
                    "baseStyles": {
                        "display": "flex",
                        "justifyContent": "center",
                        "gap": "32px",
                        "marginBottom": "32px",
                        "flexWrap": "wrap",
                    },
                    "children": [{"slot": "inline_links"}]
                },
                {"slot": "social"},
                {"slot": "bottom_section"},
            ]
        }
    },

    "sidebar": {
        "description": "Large brand section with links sidebar",
        "structure": {
            "blockId": "footer-main",
            "element": "footer",
            "baseStyles": {
                "padding": "64px 24px 24px",
                "backgroundColor": "var(--surface-color)",
            },
            "children": [
                {
                    "blockId": "footer-content",
                    "element": "div",
                    "baseStyles": {
                        "display": "grid",
                        "gridTemplateColumns": "2fr 3fr",
                        "gap": "64px",
                        "maxWidth": "1200px",
                        "marginLeft": "auto",
                        "marginRight": "auto",
                        "marginBottom": "48px",
                    },
                    "mobileStyles": {
                        "gridTemplateColumns": "1fr",
                        "gap": "32px",
                    },
                    "children": [
                        {"slot": "brand"},
                        {"slot": "columns_grid"},
                    ]
                },
                {"slot": "bottom_section"},
            ]
        }
    },
}


def get_footer_template(layout: str) -> dict:
    """Get footer template structure by layout name"""
    template = FOOTER_TEMPLATES.get(layout)
    if template:
        return template.get("structure", {})
    return FOOTER_TEMPLATES["columns"]["structure"]


def build_footer_from_config(config: FooterConfig, theme: dict = None) -> dict:
    """
    Build a complete footer block from configuration.

    Args:
        config: FooterConfig with all footer settings
        theme: Optional theme for styling

    Returns:
        dict: Complete footer block structure
    """
    import copy

    theme_styles = theme.get("styles", {}) if theme else {}

    # Determine layout from config type
    layout_map = {
        "minimal": "minimal",
        "centered": "minimal",
        "standard": "columns",
        "extended": "sidebar",
        "ecommerce": "columns",
        "saas": "sidebar",
        "blog": "columns",
    }
    layout = layout_map.get(config.type, "columns")

    # Build the footer structure
    footer = {
        "blockId": "footer-main",
        "element": "footer",
        "baseStyles": {
            "padding": "64px 24px 24px",
            "backgroundColor": "var(--surface-color)",
        },
        "mobileStyles": {
            "padding": "48px 16px 16px",
        },
        "children": []
    }

    # Container
    container = {
        "blockId": "footer-container",
        "element": "div",
        "baseStyles": {
            "maxWidth": "1200px",
            "marginLeft": "auto",
            "marginRight": "auto",
        },
        "children": []
    }

    # Build top section based on type
    if config.type == "minimal":
        # Simple centered footer
        if config.show_social and config.social_links:
            social = _build_social_links_block(config.social_links, theme_styles)
            if social:
                social["baseStyles"]["justifyContent"] = "center"
                social["baseStyles"]["marginBottom"] = "24px"
                container["children"].append(social)

        bottom = _build_bottom_section(config, theme_styles)
        bottom["baseStyles"]["justifyContent"] = "center"
        bottom["baseStyles"]["borderTop"] = "none"
        container["children"].append(bottom)

    else:
        # Multi-column layout
        top_section = {
            "blockId": "footer-top",
            "element": "div",
            "baseStyles": {
                "display": "grid",
                "gridTemplateColumns": f"1.5fr repeat({len(config.columns)}, 1fr)" if config.columns else "1fr",
                "gap": "48px",
                "marginBottom": "48px",
            },
            "mobileStyles": {
                "gridTemplateColumns": "1fr",
                "gap": "32px",
            },
            "children": []
        }

        # Add brand section
        brand = _build_brand_block(config, theme_styles)
        top_section["children"].append(brand)

        # Add link columns
        for i, column in enumerate(config.columns or []):
            col = _build_link_column(column, i, theme_styles)
            top_section["children"].append(col)

        # Add newsletter if enabled
        if config.show_newsletter:
            newsletter = _build_newsletter_block(config, theme_styles)
            if newsletter:
                top_section["children"].append(newsletter)

        container["children"].append(top_section)

        # Add payment methods for e-commerce
        if config.type == "ecommerce" and config.show_payment_methods:
            payments = _build_payment_methods(config)
            if payments:
                payments["baseStyles"]["marginBottom"] = "24px"
                container["children"].append(payments)

        # Add bottom section
        bottom = _build_bottom_section(config, theme_styles)
        container["children"].append(bottom)

    footer["children"].append(container)

    # Clean up None children
    def clean_none_children(block):
        if isinstance(block, dict) and "children" in block:
            block["children"] = [
                clean_none_children(child)
                for child in block["children"]
                if child is not None
            ]
        return block

    return clean_none_children(footer)


__all__ = [
    "FOOTER_TEMPLATES",
    "get_footer_template",
    "build_footer_from_config",
]
