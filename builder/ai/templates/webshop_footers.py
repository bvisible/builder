"""
Webshop Footer Templates
Pre-built footer structures optimized for e-commerce with Frappe Webshop.
"""

from typing import Optional, List
from builder.ai.schemas.header_schema import NavItem


# Default logo path for all webshop footers
DEFAULT_LOGO = "/files/logo-default.png"


def _build_footer_logo(logo_value: str = None, style: str = "standard") -> dict:
    """Build logo block for footer"""
    return {
        "blockId": "ws-footer-logo",
        "element": "a",
        "attributes": {"href": "/"},
        "baseStyles": {"textDecoration": "none", "display": "inline-block"},
        "children": [{
            "blockId": "ws-footer-logo-img",
            "element": "img",
            "attributes": {
                "src": logo_value or DEFAULT_LOGO,
                "alt": "Logo"
            },
            "baseStyles": {
                "height": "40px",
                "width": "auto",
                "objectFit": "contain",
            }
        }]
    }


def _build_footer_column(
    title: str,
    links: List[NavItem],
    block_id: str = "footer-col"
) -> dict:
    """Build a footer column with title and links"""
    link_blocks = []
    for i, link in enumerate(links):
        link_blocks.append({
            "blockId": f"{block_id}-link-{i}",
            "element": "a",
            "innerHTML": link.label,
            "attributes": {
                "href": link.href,
                **({"target": "_blank", "rel": "noopener"} if link.is_external else {})
            },
            "baseStyles": {
                "color": "var(--muted-color, #6b7280)",
                "textDecoration": "none",
                "fontSize": "14px",
                "lineHeight": "2",
                "transition": "color 200ms ease",
            }
        })

    return {
        "blockId": block_id,
        "element": "div",
        "baseStyles": {
            "display": "flex",
            "flexDirection": "column",
            "gap": "12px",
        },
        "children": [
            {
                "blockId": f"{block_id}-title",
                "element": "h4",
                "innerHTML": title,
                "baseStyles": {
                    "fontSize": "14px",
                    "fontWeight": "600",
                    "color": "var(--text-color)",
                    "marginBottom": "8px",
                    "textTransform": "uppercase",
                    "letterSpacing": "0.05em",
                }
            },
            *link_blocks
        ]
    }


def _build_social_icons(
    facebook: str = "#",
    instagram: str = "#",
    twitter: str = "#",
    linkedin: str = None,
    youtube: str = None
) -> dict:
    """Build social media icons"""
    icons = []

    # Facebook
    icons.append({
        "blockId": "ws-social-facebook",
        "element": "a",
        "attributes": {"href": facebook, "aria-label": "Facebook", "target": "_blank", "rel": "noopener"},
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "width": "36px",
            "height": "36px",
            "borderRadius": "50%",
            "backgroundColor": "var(--border-color, #e5e7eb)",
            "color": "var(--text-color)",
            "textDecoration": "none",
            "transition": "all 200ms ease",
        },
        "children": [{
            "blockId": "ws-fb-icon",
            "element": "svg",
            "attributes": {
                "xmlns": "http://www.w3.org/2000/svg",
                "width": "18",
                "height": "18",
                "viewBox": "0 0 24 24",
                "fill": "currentColor"
            },
            "children": [{
                "blockId": "ws-fb-path",
                "element": "path",
                "attributes": {
                    "d": "M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"
                }
            }]
        }]
    })

    # Instagram
    icons.append({
        "blockId": "ws-social-instagram",
        "element": "a",
        "attributes": {"href": instagram, "aria-label": "Instagram", "target": "_blank", "rel": "noopener"},
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "width": "36px",
            "height": "36px",
            "borderRadius": "50%",
            "backgroundColor": "var(--border-color, #e5e7eb)",
            "color": "var(--text-color)",
            "textDecoration": "none",
            "transition": "all 200ms ease",
        },
        "children": [{
            "blockId": "ws-ig-icon",
            "element": "svg",
            "attributes": {
                "xmlns": "http://www.w3.org/2000/svg",
                "width": "18",
                "height": "18",
                "viewBox": "0 0 24 24",
                "fill": "none",
                "stroke": "currentColor",
                "stroke-width": "2",
                "stroke-linecap": "round",
                "stroke-linejoin": "round"
            },
            "children": [
                {"blockId": "ws-ig-rect", "element": "rect", "attributes": {"x": "2", "y": "2", "width": "20", "height": "20", "rx": "5", "ry": "5"}},
                {"blockId": "ws-ig-path", "element": "path", "attributes": {"d": "M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"}},
                {"blockId": "ws-ig-line", "element": "line", "attributes": {"x1": "17.5", "y1": "6.5", "x2": "17.51", "y2": "6.5"}}
            ]
        }]
    })

    # Twitter/X
    icons.append({
        "blockId": "ws-social-twitter",
        "element": "a",
        "attributes": {"href": twitter, "aria-label": "Twitter", "target": "_blank", "rel": "noopener"},
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "width": "36px",
            "height": "36px",
            "borderRadius": "50%",
            "backgroundColor": "var(--border-color, #e5e7eb)",
            "color": "var(--text-color)",
            "textDecoration": "none",
            "transition": "all 200ms ease",
        },
        "children": [{
            "blockId": "ws-tw-icon",
            "element": "svg",
            "attributes": {
                "xmlns": "http://www.w3.org/2000/svg",
                "width": "16",
                "height": "16",
                "viewBox": "0 0 24 24",
                "fill": "currentColor"
            },
            "children": [{
                "blockId": "ws-tw-path",
                "element": "path",
                "attributes": {
                    "d": "M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"
                }
            }]
        }]
    })

    return {
        "blockId": "ws-footer-social",
        "element": "div",
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "gap": "12px",
        },
        "children": icons
    }


def _build_newsletter_form() -> dict:
    """Build newsletter subscription form"""
    return {
        "blockId": "ws-newsletter",
        "element": "div",
        "baseStyles": {
            "display": "flex",
            "flexDirection": "column",
            "gap": "12px",
        },
        "children": [
            {
                "blockId": "ws-newsletter-title",
                "element": "h4",
                "innerHTML": "Newsletter",
                "baseStyles": {
                    "fontSize": "14px",
                    "fontWeight": "600",
                    "color": "var(--text-color)",
                    "marginBottom": "4px",
                    "textTransform": "uppercase",
                    "letterSpacing": "0.05em",
                }
            },
            {
                "blockId": "ws-newsletter-desc",
                "element": "p",
                "innerHTML": "Subscribe to receive updates and exclusive offers.",
                "baseStyles": {
                    "fontSize": "14px",
                    "color": "var(--muted-color, #6b7280)",
                    "marginBottom": "8px",
                }
            },
            {
                "blockId": "ws-newsletter-form",
                "element": "form",
                "attributes": {"action": "/api/method/frappe.email.queue.subscribe", "method": "POST"},
                "baseStyles": {
                    "display": "flex",
                    "gap": "8px",
                },
                "children": [
                    {
                        "blockId": "ws-newsletter-input",
                        "element": "input",
                        "attributes": {
                            "type": "email",
                            "name": "email",
                            "placeholder": "Enter your email",
                            "required": "true"
                        },
                        "baseStyles": {
                            "flex": "1",
                            "padding": "10px 14px",
                            "border": "1px solid var(--border-color, #e5e7eb)",
                            "borderRadius": "6px",
                            "fontSize": "14px",
                            "outline": "none",
                        }
                    },
                    {
                        "blockId": "ws-newsletter-btn",
                        "element": "button",
                        "innerHTML": "Subscribe",
                        "attributes": {"type": "submit"},
                        "baseStyles": {
                            "padding": "10px 20px",
                            "backgroundColor": "var(--primary-color)",
                            "color": "#ffffff",
                            "border": "none",
                            "borderRadius": "6px",
                            "fontWeight": "600",
                            "fontSize": "14px",
                            "cursor": "pointer",
                            "transition": "all 200ms ease",
                        }
                    }
                ]
            }
        ]
    }


def _build_copyright(company_name: str = "Your Company") -> dict:
    """Build copyright section"""
    return {
        "blockId": "ws-footer-copyright",
        "element": "div",
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
            "paddingTop": "24px",
            "borderTop": "1px solid var(--border-color, #e5e7eb)",
            "flexWrap": "wrap",
            "gap": "16px",
        },
        "mobileStyles": {
            "flexDirection": "column",
            "alignItems": "center",
            "textAlign": "center",
        },
        "children": [
            {
                "blockId": "ws-copyright-text",
                "element": "p",
                "innerHTML": f"© 2025 {company_name}. All rights reserved.",
                "baseStyles": {
                    "fontSize": "13px",
                    "color": "var(--muted-color, #6b7280)",
                }
            },
            {
                "blockId": "ws-footer-legal",
                "element": "div",
                "baseStyles": {
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "24px",
                },
                "children": [
                    {
                        "blockId": "ws-legal-privacy",
                        "element": "a",
                        "innerHTML": "Privacy Policy",
                        "attributes": {"href": "/privacy"},
                        "baseStyles": {
                            "fontSize": "13px",
                            "color": "var(--muted-color, #6b7280)",
                            "textDecoration": "none",
                        }
                    },
                    {
                        "blockId": "ws-legal-terms",
                        "element": "a",
                        "innerHTML": "Terms of Service",
                        "attributes": {"href": "/terms"},
                        "baseStyles": {
                            "fontSize": "13px",
                            "color": "var(--muted-color, #6b7280)",
                            "textDecoration": "none",
                        }
                    }
                ]
            }
        ]
    }


# =============================================================================
# WEBSHOP FOOTER VARIATIONS
# =============================================================================

WEBSHOP_FOOTER_VARIATIONS = {
    "webshop_standard": {
        "name": "Standard E-commerce",
        "description": "Full footer with columns, newsletter, and social links",
        "preview": "Logo + About | Shop Links | Support Links | Newsletter | Social + Copyright",
    },

    "webshop_simple": {
        "name": "Simple",
        "description": "Simple footer with essential links and copyright",
        "preview": "Logo | Links | Social | Copyright",
    },

    "webshop_centered": {
        "name": "Centered",
        "description": "Centered footer for minimal designs",
        "preview": "Logo | Nav | Social | Copyright (all centered)",
    },

    "webshop_dark": {
        "name": "Dark",
        "description": "Dark background footer",
        "preview": "Same as standard but with dark theme",
    },

    "webshop_minimal": {
        "name": "Minimal",
        "description": "Ultra minimal footer with just copyright",
        "preview": "Logo | Copyright | Social",
    },

    "webshop_newsletter": {
        "name": "Newsletter Focused",
        "description": "Footer with prominent newsletter signup",
        "preview": "Newsletter CTA | Columns | Copyright",
    },
}


def build_webshop_footer_standard(
    company_name: str = "Your Company",
    logo: str = None,
    description: str = None
) -> dict:
    """
    Standard e-commerce footer with multiple columns.
    """
    shop_links = [
        NavItem(label="All Products", href="/all-products"),
        NavItem(label="Categories", href="/shop-by-category"),
        NavItem(label="New Arrivals", href="/all-products?sort=creation"),
        NavItem(label="Sale", href="/all-products?on_sale=1"),
    ]

    support_links = [
        NavItem(label="Contact Us", href="/contact"),
        NavItem(label="FAQs", href="/faq"),
        NavItem(label="Shipping Info", href="/shipping"),
        NavItem(label="Returns", href="/returns"),
    ]

    company_links = [
        NavItem(label="About Us", href="/about"),
        NavItem(label="Blog", href="/blog"),
        NavItem(label="Careers", href="/careers"),
        NavItem(label="Press", href="/press"),
    ]

    return {
        "blockId": "ws-footer",
        "element": "footer",
        "baseStyles": {
            "backgroundColor": "var(--surface-color, #f9fafb)",
            "padding": "48px 24px 24px",
        },
        "children": [
            {
                "blockId": "ws-footer-container",
                "element": "div",
                "baseStyles": {
                    "maxWidth": "1200px",
                    "margin": "0 auto",
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "32px",
                },
                "children": [
                    {
                        "blockId": "ws-footer-main",
                        "element": "div",
                        "baseStyles": {
                            "display": "grid",
                            "gridTemplateColumns": "2fr 1fr 1fr 1fr 1.5fr",
                            "gap": "32px",
                        },
                        "mobileStyles": {
                            "gridTemplateColumns": "1fr",
                            "gap": "24px",
                        },
                        "children": [
                            # About column
                            {
                                "blockId": "ws-footer-about",
                                "element": "div",
                                "baseStyles": {
                                    "display": "flex",
                                    "flexDirection": "column",
                                    "gap": "16px",
                                },
                                "children": [
                                    _build_footer_logo(logo),
                                    {
                                        "blockId": "ws-footer-desc",
                                        "element": "p",
                                        "innerHTML": description or "Quality products for your everyday needs. Shop with confidence and enjoy fast shipping.",
                                        "baseStyles": {
                                            "fontSize": "14px",
                                            "color": "var(--muted-color, #6b7280)",
                                            "lineHeight": "1.6",
                                            "maxWidth": "280px",
                                        }
                                    },
                                    _build_social_icons(),
                                ]
                            },
                            _build_footer_column("Shop", shop_links, "ws-footer-shop"),
                            _build_footer_column("Support", support_links, "ws-footer-support"),
                            _build_footer_column("Company", company_links, "ws-footer-company"),
                            _build_newsletter_form(),
                        ]
                    },
                    _build_copyright(company_name),
                ]
            }
        ]
    }


def build_webshop_footer_simple(
    company_name: str = "Your Company",
    logo: str = None
) -> dict:
    """Simple footer with essential elements."""
    return {
        "blockId": "ws-footer",
        "element": "footer",
        "baseStyles": {
            "backgroundColor": "var(--surface-color, #f9fafb)",
            "padding": "32px 24px",
        },
        "children": [
            {
                "blockId": "ws-footer-container",
                "element": "div",
                "baseStyles": {
                    "maxWidth": "1200px",
                    "margin": "0 auto",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",
                    "flexWrap": "wrap",
                    "gap": "24px",
                },
                "mobileStyles": {
                    "flexDirection": "column",
                    "textAlign": "center",
                },
                "children": [
                    _build_footer_logo(logo),
                    {
                        "blockId": "ws-footer-nav",
                        "element": "nav",
                        "baseStyles": {
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "24px",
                        },
                        "children": [
                            {"blockId": "ws-fn-1", "element": "a", "innerHTML": "Shop", "attributes": {"href": "/all-products"}, "baseStyles": {"fontSize": "14px", "color": "var(--muted-color)", "textDecoration": "none"}},
                            {"blockId": "ws-fn-2", "element": "a", "innerHTML": "About", "attributes": {"href": "/about"}, "baseStyles": {"fontSize": "14px", "color": "var(--muted-color)", "textDecoration": "none"}},
                            {"blockId": "ws-fn-3", "element": "a", "innerHTML": "Contact", "attributes": {"href": "/contact"}, "baseStyles": {"fontSize": "14px", "color": "var(--muted-color)", "textDecoration": "none"}},
                            {"blockId": "ws-fn-4", "element": "a", "innerHTML": "Privacy", "attributes": {"href": "/privacy"}, "baseStyles": {"fontSize": "14px", "color": "var(--muted-color)", "textDecoration": "none"}},
                        ]
                    },
                    {
                        "blockId": "ws-footer-right",
                        "element": "div",
                        "baseStyles": {
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "16px",
                        },
                        "children": [
                            _build_social_icons(),
                        ]
                    }
                ]
            },
            {
                "blockId": "ws-footer-bottom",
                "element": "div",
                "baseStyles": {
                    "maxWidth": "1200px",
                    "margin": "24px auto 0",
                    "paddingTop": "16px",
                    "borderTop": "1px solid var(--border-color, #e5e7eb)",
                    "textAlign": "center",
                },
                "children": [{
                    "blockId": "ws-copyright",
                    "element": "p",
                    "innerHTML": f"© 2025 {company_name}. All rights reserved.",
                    "baseStyles": {
                        "fontSize": "13px",
                        "color": "var(--muted-color, #6b7280)",
                    }
                }]
            }
        ]
    }


def build_webshop_footer_centered(
    company_name: str = "Your Company",
    logo: str = None
) -> dict:
    """Centered footer for minimal designs."""
    return {
        "blockId": "ws-footer",
        "element": "footer",
        "baseStyles": {
            "backgroundColor": "var(--surface-color, #f9fafb)",
            "padding": "48px 24px",
            "textAlign": "center",
        },
        "children": [
            {
                "blockId": "ws-footer-container",
                "element": "div",
                "baseStyles": {
                    "maxWidth": "600px",
                    "margin": "0 auto",
                    "display": "flex",
                    "flexDirection": "column",
                    "alignItems": "center",
                    "gap": "24px",
                },
                "children": [
                    _build_footer_logo(logo),
                    {
                        "blockId": "ws-footer-nav",
                        "element": "nav",
                        "baseStyles": {
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "gap": "32px",
                            "flexWrap": "wrap",
                        },
                        "children": [
                            {"blockId": "ws-cn-1", "element": "a", "innerHTML": "Shop", "attributes": {"href": "/all-products"}, "baseStyles": {"fontSize": "14px", "color": "var(--text-color)", "textDecoration": "none", "fontWeight": "500"}},
                            {"blockId": "ws-cn-2", "element": "a", "innerHTML": "About", "attributes": {"href": "/about"}, "baseStyles": {"fontSize": "14px", "color": "var(--text-color)", "textDecoration": "none", "fontWeight": "500"}},
                            {"blockId": "ws-cn-3", "element": "a", "innerHTML": "Contact", "attributes": {"href": "/contact"}, "baseStyles": {"fontSize": "14px", "color": "var(--text-color)", "textDecoration": "none", "fontWeight": "500"}},
                            {"blockId": "ws-cn-4", "element": "a", "innerHTML": "FAQ", "attributes": {"href": "/faq"}, "baseStyles": {"fontSize": "14px", "color": "var(--text-color)", "textDecoration": "none", "fontWeight": "500"}},
                        ]
                    },
                    _build_social_icons(),
                    {
                        "blockId": "ws-copyright",
                        "element": "p",
                        "innerHTML": f"© 2025 {company_name}. All rights reserved.",
                        "baseStyles": {
                            "fontSize": "13px",
                            "color": "var(--muted-color, #6b7280)",
                        }
                    }
                ]
            }
        ]
    }


def build_webshop_footer_dark(
    company_name: str = "Your Company",
    logo: str = None,
    description: str = None
) -> dict:
    """Dark theme footer."""
    footer = build_webshop_footer_standard(company_name, logo, description)

    # Override colors for dark theme
    footer["baseStyles"]["backgroundColor"] = "#111827"
    footer["baseStyles"]["color"] = "#ffffff"

    def apply_dark_theme(block):
        if isinstance(block, dict):
            styles = block.get("baseStyles", {})
            # Invert text colors
            if styles.get("color") == "var(--text-color)":
                styles["color"] = "#ffffff"
            elif styles.get("color") == "var(--muted-color, #6b7280)":
                styles["color"] = "#9ca3af"
            # Invert backgrounds
            if styles.get("backgroundColor") == "var(--border-color, #e5e7eb)":
                styles["backgroundColor"] = "#374151"
            # Invert borders
            if styles.get("borderTop") == "1px solid var(--border-color, #e5e7eb)":
                styles["borderTop"] = "1px solid #374151"
            if styles.get("border") == "1px solid var(--border-color, #e5e7eb)":
                styles["border"] = "1px solid #374151"

            for child in block.get("children", []):
                apply_dark_theme(child)

    apply_dark_theme(footer)
    footer["blockId"] = "ws-footer-dark"
    return footer


def build_webshop_footer_minimal(
    company_name: str = "Your Company",
    logo: str = None
) -> dict:
    """Ultra minimal footer."""
    return {
        "blockId": "ws-footer",
        "element": "footer",
        "baseStyles": {
            "padding": "24px",
            "borderTop": "1px solid var(--border-color, #e5e7eb)",
        },
        "children": [
            {
                "blockId": "ws-footer-container",
                "element": "div",
                "baseStyles": {
                    "maxWidth": "1200px",
                    "margin": "0 auto",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",
                },
                "mobileStyles": {
                    "flexDirection": "column",
                    "gap": "16px",
                    "textAlign": "center",
                },
                "children": [
                    _build_footer_logo(logo),
                    {
                        "blockId": "ws-copyright",
                        "element": "p",
                        "innerHTML": f"© 2025 {company_name}",
                        "baseStyles": {
                            "fontSize": "13px",
                            "color": "var(--muted-color, #6b7280)",
                        }
                    },
                    _build_social_icons(),
                ]
            }
        ]
    }


def build_webshop_footer_newsletter(
    company_name: str = "Your Company",
    logo: str = None
) -> dict:
    """Footer with prominent newsletter section."""
    return {
        "blockId": "ws-footer",
        "element": "footer",
        "baseStyles": {
            "backgroundColor": "var(--surface-color, #f9fafb)",
        },
        "children": [
            # Newsletter CTA section
            {
                "blockId": "ws-newsletter-cta",
                "element": "div",
                "baseStyles": {
                    "backgroundColor": "var(--primary-color)",
                    "padding": "48px 24px",
                },
                "children": [{
                    "blockId": "ws-newsletter-container",
                    "element": "div",
                    "baseStyles": {
                        "maxWidth": "600px",
                        "margin": "0 auto",
                        "textAlign": "center",
                    },
                    "children": [
                        {
                            "blockId": "ws-nl-title",
                            "element": "h3",
                            "innerHTML": "Stay in the loop",
                            "baseStyles": {
                                "fontSize": "24px",
                                "fontWeight": "700",
                                "color": "#ffffff",
                                "marginBottom": "12px",
                            }
                        },
                        {
                            "blockId": "ws-nl-desc",
                            "element": "p",
                            "innerHTML": "Subscribe to get special offers, free giveaways, and new arrivals.",
                            "baseStyles": {
                                "fontSize": "16px",
                                "color": "rgba(255,255,255,0.9)",
                                "marginBottom": "24px",
                            }
                        },
                        {
                            "blockId": "ws-nl-form",
                            "element": "form",
                            "baseStyles": {
                                "display": "flex",
                                "gap": "12px",
                                "justifyContent": "center",
                            },
                            "mobileStyles": {
                                "flexDirection": "column",
                            },
                            "children": [
                                {
                                    "blockId": "ws-nl-input",
                                    "element": "input",
                                    "attributes": {"type": "email", "placeholder": "Enter your email", "required": "true"},
                                    "baseStyles": {
                                        "flex": "1",
                                        "maxWidth": "300px",
                                        "padding": "14px 18px",
                                        "border": "none",
                                        "borderRadius": "8px",
                                        "fontSize": "16px",
                                    }
                                },
                                {
                                    "blockId": "ws-nl-btn",
                                    "element": "button",
                                    "innerHTML": "Subscribe",
                                    "attributes": {"type": "submit"},
                                    "baseStyles": {
                                        "padding": "14px 28px",
                                        "backgroundColor": "#ffffff",
                                        "color": "var(--primary-color)",
                                        "border": "none",
                                        "borderRadius": "8px",
                                        "fontWeight": "700",
                                        "fontSize": "16px",
                                        "cursor": "pointer",
                                    }
                                }
                            ]
                        }
                    ]
                }]
            },
            # Footer links
            {
                "blockId": "ws-footer-main",
                "element": "div",
                "baseStyles": {
                    "maxWidth": "1200px",
                    "margin": "0 auto",
                    "padding": "48px 24px",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",
                    "flexWrap": "wrap",
                    "gap": "24px",
                },
                "children": [
                    _build_footer_logo(logo),
                    {
                        "blockId": "ws-footer-nav",
                        "element": "nav",
                        "baseStyles": {"display": "flex", "gap": "32px"},
                        "children": [
                            {"blockId": "ws-nf-1", "element": "a", "innerHTML": "Shop", "attributes": {"href": "/all-products"}, "baseStyles": {"fontSize": "14px", "color": "var(--text-color)", "textDecoration": "none"}},
                            {"blockId": "ws-nf-2", "element": "a", "innerHTML": "About", "attributes": {"href": "/about"}, "baseStyles": {"fontSize": "14px", "color": "var(--text-color)", "textDecoration": "none"}},
                            {"blockId": "ws-nf-3", "element": "a", "innerHTML": "Contact", "attributes": {"href": "/contact"}, "baseStyles": {"fontSize": "14px", "color": "var(--text-color)", "textDecoration": "none"}},
                            {"blockId": "ws-nf-4", "element": "a", "innerHTML": "Privacy", "attributes": {"href": "/privacy"}, "baseStyles": {"fontSize": "14px", "color": "var(--text-color)", "textDecoration": "none"}},
                        ]
                    },
                    _build_social_icons(),
                ]
            },
            # Copyright
            {
                "blockId": "ws-footer-bottom",
                "element": "div",
                "baseStyles": {
                    "maxWidth": "1200px",
                    "margin": "0 auto",
                    "padding": "16px 24px",
                    "borderTop": "1px solid var(--border-color, #e5e7eb)",
                    "textAlign": "center",
                },
                "children": [{
                    "blockId": "ws-copyright",
                    "element": "p",
                    "innerHTML": f"© 2025 {company_name}. All rights reserved.",
                    "baseStyles": {"fontSize": "13px", "color": "var(--muted-color, #6b7280)"}
                }]
            }
        ]
    }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def build_webshop_footer(
    variation: str = "webshop_standard",
    company_name: str = "Your Company",
    logo: str = None,
    description: str = None
) -> dict:
    """
    Build a webshop footer from a variation name.

    Args:
        variation: Name of footer variation (see WEBSHOP_FOOTER_VARIATIONS)
        company_name: Company name for copyright
        logo: Logo path (defaults to /files/logo-default.png)
        description: Company description text

    Returns:
        dict: Complete footer block structure
    """
    builders = {
        "webshop_standard": lambda: build_webshop_footer_standard(company_name, logo, description),
        "webshop_simple": lambda: build_webshop_footer_simple(company_name, logo),
        "webshop_centered": lambda: build_webshop_footer_centered(company_name, logo),
        "webshop_dark": lambda: build_webshop_footer_dark(company_name, logo, description),
        "webshop_minimal": lambda: build_webshop_footer_minimal(company_name, logo),
        "webshop_newsletter": lambda: build_webshop_footer_newsletter(company_name, logo),
    }

    builder = builders.get(variation, builders["webshop_standard"])
    return builder()


def get_webshop_footer_variations() -> dict:
    """Get available webshop footer variations with descriptions"""
    return WEBSHOP_FOOTER_VARIATIONS


__all__ = [
    "build_webshop_footer",
    "build_webshop_footer_standard",
    "build_webshop_footer_simple",
    "build_webshop_footer_centered",
    "build_webshop_footer_dark",
    "build_webshop_footer_minimal",
    "build_webshop_footer_newsletter",
    "get_webshop_footer_variations",
    "WEBSHOP_FOOTER_VARIATIONS",
]
