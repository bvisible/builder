"""
Section Templates
Pre-built section structures for consistent AI generation.
"""

from typing import Optional


# =============================================================================
# SECTION TEMPLATES
# =============================================================================

SECTION_TEMPLATES = {
    "hero_centered": {
        "description": "Centered hero with headline, subheadline, and CTA",
        "structure": {
            "blockId": "hero-section",
            "element": "section",
            "baseStyles": {
                "minHeight": "90vh",
                "display": "flex",
                "flexDirection": "column",
                "alignItems": "center",
                "justifyContent": "center",
                "padding": "80px 24px",
                "textAlign": "center",
                "backgroundColor": "var(--surface-color)",
            },
            "mobileStyles": {
                "minHeight": "80vh",
                "padding": "48px 16px",
            },
            "children": [
                {
                    "blockId": "hero-content",
                    "element": "div",
                    "baseStyles": {
                        "maxWidth": "800px",
                    },
                    "children": [
                        {"slot": "badge"},
                        {"slot": "headline"},
                        {"slot": "subheadline"},
                        {"slot": "cta_group"},
                    ]
                }
            ]
        }
    },

    "hero_split": {
        "description": "Split hero with content and image",
        "structure": {
            "blockId": "hero-section",
            "element": "section",
            "baseStyles": {
                "minHeight": "90vh",
                "display": "grid",
                "gridTemplateColumns": "1fr 1fr",
                "gap": "48px",
                "alignItems": "center",
                "padding": "80px 24px",
            },
            "mobileStyles": {
                "gridTemplateColumns": "1fr",
                "minHeight": "auto",
                "padding": "48px 16px",
            },
            "children": [
                {
                    "blockId": "hero-content",
                    "element": "div",
                    "children": [
                        {"slot": "badge"},
                        {"slot": "headline"},
                        {"slot": "subheadline"},
                        {"slot": "cta_group"},
                    ]
                },
                {
                    "blockId": "hero-media",
                    "element": "div",
                    "baseStyles": {
                        "position": "relative",
                    },
                    "children": [{"slot": "image"}]
                }
            ]
        }
    },

    "features_grid": {
        "description": "Feature cards in a grid layout",
        "structure": {
            "blockId": "features-section",
            "element": "section",
            "baseStyles": {
                "padding": "80px 24px",
            },
            "mobileStyles": {
                "padding": "48px 16px",
            },
            "children": [
                {
                    "blockId": "features-header",
                    "element": "div",
                    "baseStyles": {
                        "textAlign": "center",
                        "maxWidth": "600px",
                        "marginLeft": "auto",
                        "marginRight": "auto",
                        "marginBottom": "48px",
                    },
                    "children": [
                        {"slot": "section_title"},
                        {"slot": "section_description"},
                    ]
                },
                {
                    "blockId": "features-grid",
                    "element": "div",
                    "baseStyles": {
                        "display": "grid",
                        "gridTemplateColumns": "repeat(3, 1fr)",
                        "gap": "32px",
                        "maxWidth": "1200px",
                        "marginLeft": "auto",
                        "marginRight": "auto",
                    },
                    "mobileStyles": {
                        "gridTemplateColumns": "1fr",
                    },
                    "children": [{"slot": "feature_cards"}]
                }
            ]
        }
    },

    "features_alternating": {
        "description": "Alternating feature rows with image and content",
        "structure": {
            "blockId": "features-section",
            "element": "section",
            "baseStyles": {
                "padding": "80px 24px",
            },
            "children": [
                {
                    "blockId": "features-header",
                    "element": "div",
                    "baseStyles": {
                        "textAlign": "center",
                        "maxWidth": "600px",
                        "marginLeft": "auto",
                        "marginRight": "auto",
                        "marginBottom": "64px",
                    },
                    "children": [
                        {"slot": "section_title"},
                        {"slot": "section_description"},
                    ]
                },
                {
                    "blockId": "features-rows",
                    "element": "div",
                    "baseStyles": {
                        "display": "flex",
                        "flexDirection": "column",
                        "gap": "64px",
                        "maxWidth": "1200px",
                        "marginLeft": "auto",
                        "marginRight": "auto",
                    },
                    "children": [{"slot": "feature_rows"}]
                }
            ]
        }
    },

    "testimonials": {
        "description": "Testimonials section with quotes",
        "structure": {
            "blockId": "testimonials-section",
            "element": "section",
            "baseStyles": {
                "padding": "80px 24px",
                "backgroundColor": "var(--surface-color)",
            },
            "children": [
                {
                    "blockId": "testimonials-header",
                    "element": "div",
                    "baseStyles": {
                        "textAlign": "center",
                        "marginBottom": "48px",
                    },
                    "children": [
                        {"slot": "section_title"},
                    ]
                },
                {
                    "blockId": "testimonials-grid",
                    "element": "div",
                    "baseStyles": {
                        "display": "grid",
                        "gridTemplateColumns": "repeat(3, 1fr)",
                        "gap": "32px",
                        "maxWidth": "1200px",
                        "marginLeft": "auto",
                        "marginRight": "auto",
                    },
                    "mobileStyles": {
                        "gridTemplateColumns": "1fr",
                    },
                    "children": [{"slot": "testimonial_cards"}]
                }
            ]
        }
    },

    "pricing": {
        "description": "Pricing tiers section",
        "structure": {
            "blockId": "pricing-section",
            "element": "section",
            "baseStyles": {
                "padding": "80px 24px",
            },
            "children": [
                {
                    "blockId": "pricing-header",
                    "element": "div",
                    "baseStyles": {
                        "textAlign": "center",
                        "maxWidth": "600px",
                        "marginLeft": "auto",
                        "marginRight": "auto",
                        "marginBottom": "48px",
                    },
                    "children": [
                        {"slot": "section_title"},
                        {"slot": "section_description"},
                        {"slot": "billing_toggle"},
                    ]
                },
                {
                    "blockId": "pricing-tiers",
                    "element": "div",
                    "baseStyles": {
                        "display": "grid",
                        "gridTemplateColumns": "repeat(3, 1fr)",
                        "gap": "24px",
                        "maxWidth": "1100px",
                        "marginLeft": "auto",
                        "marginRight": "auto",
                        "alignItems": "start",
                    },
                    "mobileStyles": {
                        "gridTemplateColumns": "1fr",
                    },
                    "children": [{"slot": "pricing_cards"}]
                }
            ]
        }
    },

    "cta": {
        "description": "Call-to-action section",
        "structure": {
            "blockId": "cta-section",
            "element": "section",
            "baseStyles": {
                "padding": "80px 24px",
                "textAlign": "center",
                "backgroundColor": "var(--primary-color)",
            },
            "children": [
                {
                    "blockId": "cta-content",
                    "element": "div",
                    "baseStyles": {
                        "maxWidth": "600px",
                        "marginLeft": "auto",
                        "marginRight": "auto",
                    },
                    "children": [
                        {"slot": "headline"},
                        {"slot": "description"},
                        {"slot": "cta_button"},
                    ]
                }
            ]
        }
    },

    "contact": {
        "description": "Contact section with form",
        "structure": {
            "blockId": "contact-section",
            "element": "section",
            "baseStyles": {
                "padding": "80px 24px",
            },
            "children": [
                {
                    "blockId": "contact-container",
                    "element": "div",
                    "baseStyles": {
                        "display": "grid",
                        "gridTemplateColumns": "1fr 1fr",
                        "gap": "64px",
                        "maxWidth": "1200px",
                        "marginLeft": "auto",
                        "marginRight": "auto",
                    },
                    "mobileStyles": {
                        "gridTemplateColumns": "1fr",
                    },
                    "children": [
                        {
                            "blockId": "contact-info",
                            "element": "div",
                            "children": [
                                {"slot": "section_title"},
                                {"slot": "section_description"},
                                {"slot": "contact_details"},
                            ]
                        },
                        {
                            "blockId": "contact-form-container",
                            "element": "div",
                            "children": [{"slot": "contact_form"}]
                        }
                    ]
                }
            ]
        }
    },

    "faq": {
        "description": "FAQ accordion section",
        "structure": {
            "blockId": "faq-section",
            "element": "section",
            "baseStyles": {
                "padding": "80px 24px",
            },
            "children": [
                {
                    "blockId": "faq-header",
                    "element": "div",
                    "baseStyles": {
                        "textAlign": "center",
                        "maxWidth": "600px",
                        "marginLeft": "auto",
                        "marginRight": "auto",
                        "marginBottom": "48px",
                    },
                    "children": [
                        {"slot": "section_title"},
                        {"slot": "section_description"},
                    ]
                },
                {
                    "blockId": "faq-list",
                    "element": "div",
                    "baseStyles": {
                        "maxWidth": "800px",
                        "marginLeft": "auto",
                        "marginRight": "auto",
                    },
                    "children": [{"slot": "faq_items"}]
                }
            ]
        }
    },

    "stats": {
        "description": "Statistics/numbers section",
        "structure": {
            "blockId": "stats-section",
            "element": "section",
            "baseStyles": {
                "padding": "64px 24px",
                "backgroundColor": "var(--surface-color)",
            },
            "children": [
                {
                    "blockId": "stats-grid",
                    "element": "div",
                    "baseStyles": {
                        "display": "grid",
                        "gridTemplateColumns": "repeat(4, 1fr)",
                        "gap": "32px",
                        "maxWidth": "1000px",
                        "marginLeft": "auto",
                        "marginRight": "auto",
                        "textAlign": "center",
                    },
                    "mobileStyles": {
                        "gridTemplateColumns": "repeat(2, 1fr)",
                    },
                    "children": [{"slot": "stat_items"}]
                }
            ]
        }
    },

    "clients": {
        "description": "Client/partner logos section",
        "structure": {
            "blockId": "clients-section",
            "element": "section",
            "baseStyles": {
                "padding": "48px 24px",
            },
            "children": [
                {
                    "blockId": "clients-header",
                    "element": "p",
                    "innerHTML": "Trusted by leading companies",
                    "baseStyles": {
                        "textAlign": "center",
                        "color": "var(--muted-color)",
                        "fontSize": "14px",
                        "marginBottom": "32px",
                    }
                },
                {
                    "blockId": "clients-logos",
                    "element": "div",
                    "baseStyles": {
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "center",
                        "gap": "48px",
                        "flexWrap": "wrap",
                    },
                    "children": [{"slot": "logo_items"}]
                }
            ]
        }
    },
}


# =============================================================================
# COMPONENT TEMPLATES (reusable blocks within sections)
# =============================================================================

COMPONENT_TEMPLATES = {
    "feature_card": {
        "blockId": "feature-card-{index}",
        "element": "div",
        "baseStyles": {
            "padding": "32px",
            "backgroundColor": "var(--surface-color)",
            "borderRadius": "12px",
            "transition": "all 200ms ease",
        },
        "children": [
            {
                "blockId": "feature-icon-{index}",
                "element": "div",
                "innerHTML": "{icon}",
                "baseStyles": {
                    "width": "48px",
                    "height": "48px",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "backgroundColor": "var(--primary-color)",
                    "borderRadius": "10px",
                    "fontSize": "24px",
                    "marginBottom": "20px",
                }
            },
            {
                "blockId": "feature-title-{index}",
                "element": "h3",
                "innerHTML": "{title}",
                "baseStyles": {
                    "fontSize": "18px",
                    "fontWeight": "600",
                    "marginBottom": "12px",
                    "color": "var(--text-color)",
                }
            },
            {
                "blockId": "feature-desc-{index}",
                "element": "p",
                "innerHTML": "{description}",
                "baseStyles": {
                    "fontSize": "15px",
                    "color": "var(--muted-color)",
                    "lineHeight": "1.6",
                }
            }
        ]
    },

    "testimonial_card": {
        "blockId": "testimonial-card-{index}",
        "element": "div",
        "baseStyles": {
            "padding": "32px",
            "backgroundColor": "#ffffff",
            "borderRadius": "12px",
            "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
        },
        "children": [
            {
                "blockId": "testimonial-quote-{index}",
                "element": "p",
                "innerHTML": "\"{quote}\"",
                "baseStyles": {
                    "fontSize": "16px",
                    "lineHeight": "1.7",
                    "color": "var(--text-color)",
                    "marginBottom": "24px",
                }
            },
            {
                "blockId": "testimonial-author-{index}",
                "element": "div",
                "baseStyles": {
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "12px",
                },
                "children": [
                    {
                        "blockId": "testimonial-avatar-{index}",
                        "element": "img",
                        "attributes": {
                            "src": "{avatar}",
                            "alt": "{name}"
                        },
                        "baseStyles": {
                            "width": "48px",
                            "height": "48px",
                            "borderRadius": "50%",
                            "objectFit": "cover",
                        }
                    },
                    {
                        "blockId": "testimonial-info-{index}",
                        "element": "div",
                        "children": [
                            {
                                "blockId": "testimonial-name-{index}",
                                "element": "p",
                                "innerHTML": "{name}",
                                "baseStyles": {
                                    "fontWeight": "600",
                                    "marginBottom": "2px",
                                }
                            },
                            {
                                "blockId": "testimonial-title-{index}",
                                "element": "p",
                                "innerHTML": "{title}",
                                "baseStyles": {
                                    "fontSize": "14px",
                                    "color": "var(--muted-color)",
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    },

    "pricing_card": {
        "blockId": "pricing-card-{index}",
        "element": "div",
        "baseStyles": {
            "padding": "32px",
            "backgroundColor": "#ffffff",
            "borderRadius": "16px",
            "border": "1px solid var(--border-color)",
        },
        "children": [
            {
                "blockId": "pricing-name-{index}",
                "element": "h3",
                "innerHTML": "{name}",
                "baseStyles": {
                    "fontSize": "20px",
                    "fontWeight": "600",
                    "marginBottom": "8px",
                }
            },
            {
                "blockId": "pricing-desc-{index}",
                "element": "p",
                "innerHTML": "{description}",
                "baseStyles": {
                    "color": "var(--muted-color)",
                    "marginBottom": "24px",
                }
            },
            {
                "blockId": "pricing-price-{index}",
                "element": "div",
                "baseStyles": {
                    "marginBottom": "24px",
                },
                "children": [
                    {
                        "blockId": "pricing-amount-{index}",
                        "element": "span",
                        "innerHTML": "{price}",
                        "baseStyles": {
                            "fontSize": "48px",
                            "fontWeight": "700",
                        }
                    },
                    {
                        "blockId": "pricing-period-{index}",
                        "element": "span",
                        "innerHTML": "/month",
                        "baseStyles": {
                            "color": "var(--muted-color)",
                        }
                    }
                ]
            },
            {
                "blockId": "pricing-features-{index}",
                "element": "ul",
                "baseStyles": {
                    "listStyle": "none",
                    "padding": "0",
                    "marginBottom": "24px",
                },
                "children": [{"slot": "features"}]
            },
            {
                "blockId": "pricing-cta-{index}",
                "element": "button",
                "innerHTML": "{cta_text}",
                "baseStyles": {
                    "width": "100%",
                    "padding": "14px 24px",
                    "backgroundColor": "var(--primary-color)",
                    "color": "#ffffff",
                    "border": "none",
                    "borderRadius": "8px",
                    "fontWeight": "600",
                    "cursor": "pointer",
                }
            }
        ]
    },

    "stat_item": {
        "blockId": "stat-{index}",
        "element": "div",
        "children": [
            {
                "blockId": "stat-number-{index}",
                "element": "div",
                "innerHTML": "{number}",
                "baseStyles": {
                    "fontSize": "48px",
                    "fontWeight": "700",
                    "color": "var(--primary-color)",
                    "marginBottom": "8px",
                }
            },
            {
                "blockId": "stat-label-{index}",
                "element": "p",
                "innerHTML": "{label}",
                "baseStyles": {
                    "color": "var(--muted-color)",
                    "fontSize": "14px",
                }
            }
        ]
    },

    "faq_item": {
        "blockId": "faq-item-{index}",
        "element": "div",
        "baseStyles": {
            "borderBottom": "1px solid var(--border-color)",
            "paddingBottom": "24px",
            "marginBottom": "24px",
        },
        "children": [
            {
                "blockId": "faq-question-{index}",
                "element": "h3",
                "innerHTML": "{question}",
                "baseStyles": {
                    "fontSize": "18px",
                    "fontWeight": "600",
                    "marginBottom": "12px",
                    "cursor": "pointer",
                }
            },
            {
                "blockId": "faq-answer-{index}",
                "element": "p",
                "innerHTML": "{answer}",
                "baseStyles": {
                    "color": "var(--muted-color)",
                    "lineHeight": "1.7",
                }
            }
        ]
    },
}


def get_section_template(section_type: str) -> Optional[dict]:
    """Get section template by type"""
    return SECTION_TEMPLATES.get(section_type, {}).get("structure")


def get_component_template(component_type: str) -> Optional[dict]:
    """Get component template by type"""
    return COMPONENT_TEMPLATES.get(component_type)


# =============================================================================
# SECTION BUILDERS
# Functions to build sections from content schemas
# =============================================================================

def build_hero_section(content, variant: str = "centered", theme_styles: dict = None) -> dict:
    """Build a hero section from HeroContent"""
    import copy

    styles = theme_styles or {}
    template_name = f"hero_{variant}" if f"hero_{variant}" in SECTION_TEMPLATES else "hero_centered"
    template = copy.deepcopy(SECTION_TEMPLATES.get(template_name, SECTION_TEMPLATES["hero_centered"])["structure"])

    # Build content blocks
    content_children = []

    # Badge
    if content.badge:
        content_children.append({
            "blockId": "hero-badge",
            "element": "span",
            "innerHTML": content.badge,
            "baseStyles": {
                "display": "inline-block",
                "padding": "6px 14px",
                "backgroundColor": "rgba(var(--primary-rgb), 0.1)",
                "color": "var(--primary-color)",
                "borderRadius": "20px",
                "fontSize": "13px",
                "fontWeight": "600",
                "marginBottom": "20px",
            }
        })

    # Headline
    content_children.append({
        "blockId": "hero-headline",
        "element": "h1",
        "innerHTML": content.headline,
        "baseStyles": {
            "fontSize": "56px",
            "fontWeight": "700",
            "lineHeight": "1.1",
            "marginBottom": "24px",
            "color": "var(--text-color)",
            "letterSpacing": "-0.02em",
            **styles.get("headline", {})
        },
        "mobileStyles": {
            "fontSize": "36px",
        }
    })

    # Subheadline
    content_children.append({
        "blockId": "hero-subheadline",
        "element": "p",
        "innerHTML": content.subheadline,
        "baseStyles": {
            "fontSize": "20px",
            "color": "var(--muted-color)",
            "lineHeight": "1.6",
            "marginBottom": "32px",
            "maxWidth": "600px",
        },
        "mobileStyles": {
            "fontSize": "17px",
        }
    })

    # CTA buttons
    cta_group = {
        "blockId": "hero-cta-group",
        "element": "div",
        "baseStyles": {
            "display": "flex",
            "gap": "16px",
            "justifyContent": "center" if variant == "centered" else "flex-start",
        },
        "mobileStyles": {
            "flexDirection": "column",
            "alignItems": "stretch",
        },
        "children": [
            {
                "blockId": "hero-cta-primary",
                "element": "a",
                "innerHTML": content.primary_cta_text,
                "attributes": {"href": content.primary_cta_url},
                "baseStyles": {
                    "padding": "16px 32px",
                    "backgroundColor": "var(--primary-color)",
                    "color": "#ffffff",
                    "borderRadius": "8px",
                    "fontWeight": "600",
                    "fontSize": "16px",
                    "textDecoration": "none",
                    "textAlign": "center",
                    "transition": "all 200ms ease",
                }
            }
        ]
    }

    if content.secondary_cta_text:
        cta_group["children"].append({
            "blockId": "hero-cta-secondary",
            "element": "a",
            "innerHTML": content.secondary_cta_text,
            "attributes": {"href": content.secondary_cta_url or "#"},
            "baseStyles": {
                "padding": "16px 32px",
                "backgroundColor": "transparent",
                "color": "var(--text-color)",
                "borderRadius": "8px",
                "fontWeight": "600",
                "fontSize": "16px",
                "textDecoration": "none",
                "textAlign": "center",
                "border": "1px solid var(--border-color)",
                "transition": "all 200ms ease",
            }
        })

    content_children.append(cta_group)

    # Fill content into template
    def fill_content(block):
        if isinstance(block, dict):
            if block.get("blockId") == "hero-content":
                block["children"] = content_children
            elif block.get("blockId") == "hero-media" and content.image_url:
                block["children"] = [{
                    "blockId": "hero-image",
                    "element": "img",
                    "attributes": {
                        "src": content.image_url,
                        "alt": content.image_alt or "Hero image"
                    },
                    "baseStyles": {
                        "width": "100%",
                        "height": "auto",
                        "borderRadius": "16px",
                    }
                }]
            elif "children" in block:
                block["children"] = [fill_content(child) for child in block["children"]]
        return block

    return fill_content(template)


def build_features_section(content, variant: str = "grid", theme_styles: dict = None) -> dict:
    """Build a features section from FeaturesContent"""
    import copy

    styles = theme_styles or {}
    template_name = f"features_{variant}" if f"features_{variant}" in SECTION_TEMPLATES else "features_grid"
    template = copy.deepcopy(SECTION_TEMPLATES.get(template_name, SECTION_TEMPLATES["features_grid"])["structure"])

    # Build feature cards
    feature_cards = []
    for i, feature in enumerate(content.features):
        card = copy.deepcopy(COMPONENT_TEMPLATES["feature_card"])
        card["blockId"] = f"feature-card-{i}"

        # Update children with content
        for child in card.get("children", []):
            if "icon" in child.get("blockId", ""):
                child["blockId"] = f"feature-icon-{i}"
                child["innerHTML"] = feature.icon
            elif "title" in child.get("blockId", ""):
                child["blockId"] = f"feature-title-{i}"
                child["innerHTML"] = feature.title
            elif "desc" in child.get("blockId", ""):
                child["blockId"] = f"feature-desc-{i}"
                child["innerHTML"] = feature.description

        feature_cards.append(card)

    # Fill slots in template
    def fill_slots(block):
        if isinstance(block, dict):
            if block.get("slot") == "section_title":
                return {
                    "blockId": "features-title",
                    "element": "h2",
                    "innerHTML": content.section_title,
                    "baseStyles": {
                        "fontSize": "40px",
                        "fontWeight": "700",
                        "marginBottom": "16px",
                        "color": "var(--text-color)",
                    },
                    "mobileStyles": {
                        "fontSize": "28px",
                    }
                }
            elif block.get("slot") == "section_description":
                if content.section_description:
                    return {
                        "blockId": "features-description",
                        "element": "p",
                        "innerHTML": content.section_description,
                        "baseStyles": {
                            "fontSize": "18px",
                            "color": "var(--muted-color)",
                            "lineHeight": "1.6",
                        }
                    }
                return None
            elif block.get("slot") == "feature_cards":
                return feature_cards
            elif "children" in block:
                block["children"] = [
                    filled for filled in
                    [fill_slots(child) for child in block["children"]]
                    if filled is not None
                ]
                # Flatten lists
                new_children = []
                for child in block["children"]:
                    if isinstance(child, list):
                        new_children.extend(child)
                    else:
                        new_children.append(child)
                block["children"] = new_children
        return block

    return fill_slots(template)


def build_testimonials_section(content, theme_styles: dict = None) -> dict:
    """Build a testimonials section from TestimonialsContent"""
    import copy

    template = copy.deepcopy(SECTION_TEMPLATES["testimonials"]["structure"])

    # Build testimonial cards
    cards = []
    for i, testimonial in enumerate(content.testimonials):
        card = copy.deepcopy(COMPONENT_TEMPLATES["testimonial_card"])
        card["blockId"] = f"testimonial-card-{i}"

        def update_card(block, idx):
            if isinstance(block, dict):
                block_id = block.get("blockId", "")
                if "quote" in block_id:
                    block["blockId"] = f"testimonial-quote-{idx}"
                    block["innerHTML"] = f'"{testimonial.quote}"'
                elif "avatar" in block_id:
                    block["blockId"] = f"testimonial-avatar-{idx}"
                    block["attributes"]["src"] = testimonial.avatar_url or f"https://ui-avatars.com/api/?name={testimonial.name.replace(' ', '+')}"
                    block["attributes"]["alt"] = testimonial.name
                elif "name" in block_id and "author" not in block_id:
                    block["blockId"] = f"testimonial-name-{idx}"
                    block["innerHTML"] = testimonial.name
                elif "title" in block_id:
                    block["blockId"] = f"testimonial-title-{idx}"
                    block["innerHTML"] = testimonial.title
                elif "author" in block_id:
                    block["blockId"] = f"testimonial-author-{idx}"
                elif "info" in block_id:
                    block["blockId"] = f"testimonial-info-{idx}"

                if "children" in block:
                    for child in block["children"]:
                        update_card(child, idx)
            return block

        update_card(card, i)
        cards.append(card)

    # Fill slots
    def fill_slots(block):
        if isinstance(block, dict):
            if block.get("slot") == "section_title":
                return {
                    "blockId": "testimonials-title",
                    "element": "h2",
                    "innerHTML": content.section_title,
                    "baseStyles": {
                        "fontSize": "40px",
                        "fontWeight": "700",
                        "color": "var(--text-color)",
                    }
                }
            elif block.get("slot") == "testimonial_cards":
                return cards
            elif "children" in block:
                block["children"] = [
                    filled for filled in
                    [fill_slots(child) for child in block["children"]]
                    if filled is not None
                ]
                new_children = []
                for child in block["children"]:
                    if isinstance(child, list):
                        new_children.extend(child)
                    else:
                        new_children.append(child)
                block["children"] = new_children
        return block

    return fill_slots(template)


def build_pricing_section(content, theme_styles: dict = None) -> dict:
    """Build a pricing section from PricingContent"""
    import copy

    template = copy.deepcopy(SECTION_TEMPLATES["pricing"]["structure"])

    # Build pricing cards
    cards = []
    for i, tier in enumerate(content.tiers):
        card = {
            "blockId": f"pricing-card-{i}",
            "element": "div",
            "baseStyles": {
                "padding": "32px",
                "backgroundColor": "#ffffff",
                "borderRadius": "16px",
                "border": f"2px solid {'var(--primary-color)' if tier.is_popular else 'var(--border-color)'}",
                "position": "relative",
            },
            "children": []
        }

        if tier.is_popular:
            card["children"].append({
                "blockId": f"pricing-popular-{i}",
                "element": "span",
                "innerHTML": "Most Popular",
                "baseStyles": {
                    "position": "absolute",
                    "top": "-12px",
                    "left": "50%",
                    "transform": "translateX(-50%)",
                    "padding": "4px 12px",
                    "backgroundColor": "var(--primary-color)",
                    "color": "#ffffff",
                    "borderRadius": "12px",
                    "fontSize": "12px",
                    "fontWeight": "600",
                }
            })

        card["children"].extend([
            {
                "blockId": f"pricing-name-{i}",
                "element": "h3",
                "innerHTML": tier.name,
                "baseStyles": {
                    "fontSize": "22px",
                    "fontWeight": "600",
                    "marginBottom": "8px",
                }
            },
            {
                "blockId": f"pricing-desc-{i}",
                "element": "p",
                "innerHTML": tier.description,
                "baseStyles": {
                    "color": "var(--muted-color)",
                    "fontSize": "14px",
                    "marginBottom": "24px",
                }
            },
            {
                "blockId": f"pricing-price-{i}",
                "element": "div",
                "baseStyles": {"marginBottom": "24px"},
                "children": [
                    {
                        "blockId": f"pricing-amount-{i}",
                        "element": "span",
                        "innerHTML": tier.price,
                        "baseStyles": {
                            "fontSize": "48px",
                            "fontWeight": "700",
                        }
                    },
                    {
                        "blockId": f"pricing-period-{i}",
                        "element": "span",
                        "innerHTML": tier.period,
                        "baseStyles": {
                            "color": "var(--muted-color)",
                            "fontSize": "16px",
                        }
                    }
                ]
            },
            {
                "blockId": f"pricing-features-{i}",
                "element": "ul",
                "baseStyles": {
                    "listStyle": "none",
                    "padding": "0",
                    "marginBottom": "24px",
                },
                "children": [
                    {
                        "blockId": f"pricing-feature-{i}-{j}",
                        "element": "li",
                        "innerHTML": f"{'✓' if feat.included else '✗'} {feat.text}",
                        "baseStyles": {
                            "padding": "8px 0",
                            "color": "var(--muted-color)" if feat.included else "#ccc",
                            "fontSize": "14px",
                        }
                    }
                    for j, feat in enumerate(tier.features)
                ]
            },
            {
                "blockId": f"pricing-cta-{i}",
                "element": "button",
                "innerHTML": tier.cta_text,
                "baseStyles": {
                    "width": "100%",
                    "padding": "14px 24px",
                    "backgroundColor": "var(--primary-color)" if tier.is_popular else "transparent",
                    "color": "#ffffff" if tier.is_popular else "var(--primary-color)",
                    "border": "2px solid var(--primary-color)",
                    "borderRadius": "8px",
                    "fontWeight": "600",
                    "cursor": "pointer",
                    "transition": "all 200ms ease",
                }
            }
        ])

        cards.append(card)

    # Fill slots
    def fill_slots(block):
        if isinstance(block, dict):
            if block.get("slot") == "section_title":
                return {
                    "blockId": "pricing-title",
                    "element": "h2",
                    "innerHTML": content.section_title,
                    "baseStyles": {
                        "fontSize": "40px",
                        "fontWeight": "700",
                        "marginBottom": "16px",
                    }
                }
            elif block.get("slot") == "section_description":
                if content.section_description:
                    return {
                        "blockId": "pricing-description",
                        "element": "p",
                        "innerHTML": content.section_description,
                        "baseStyles": {
                            "fontSize": "18px",
                            "color": "var(--muted-color)",
                        }
                    }
                return None
            elif block.get("slot") == "billing_toggle":
                return None  # Skip for now
            elif block.get("slot") == "pricing_cards":
                return cards
            elif "children" in block:
                block["children"] = [
                    filled for filled in
                    [fill_slots(child) for child in block["children"]]
                    if filled is not None
                ]
                new_children = []
                for child in block["children"]:
                    if isinstance(child, list):
                        new_children.extend(child)
                    else:
                        new_children.append(child)
                block["children"] = new_children
        return block

    return fill_slots(template)


def build_cta_section(content, theme_styles: dict = None) -> dict:
    """Build a CTA section from CtaContent"""
    import copy

    template = copy.deepcopy(SECTION_TEMPLATES["cta"]["structure"])

    # Fill slots
    def fill_slots(block):
        if isinstance(block, dict):
            if block.get("slot") == "headline":
                return {
                    "blockId": "cta-headline",
                    "element": "h2",
                    "innerHTML": content.headline,
                    "baseStyles": {
                        "fontSize": "40px",
                        "fontWeight": "700",
                        "color": "#ffffff",
                        "marginBottom": "16px",
                    },
                    "mobileStyles": {
                        "fontSize": "28px",
                    }
                }
            elif block.get("slot") == "description":
                if content.description:
                    return {
                        "blockId": "cta-description",
                        "element": "p",
                        "innerHTML": content.description,
                        "baseStyles": {
                            "fontSize": "18px",
                            "color": "rgba(255,255,255,0.8)",
                            "marginBottom": "32px",
                        }
                    }
                return None
            elif block.get("slot") == "cta_button":
                return {
                    "blockId": "cta-button",
                    "element": "a",
                    "innerHTML": content.button_text,
                    "attributes": {"href": content.button_url},
                    "baseStyles": {
                        "padding": "16px 32px",
                        "backgroundColor": "#ffffff",
                        "color": "var(--primary-color)",
                        "borderRadius": "8px",
                        "fontWeight": "600",
                        "fontSize": "16px",
                        "textDecoration": "none",
                        "display": "inline-block",
                    }
                }
            elif "children" in block:
                block["children"] = [
                    filled for filled in
                    [fill_slots(child) for child in block["children"]]
                    if filled is not None
                ]
        return block

    return fill_slots(template)


def build_stats_section(content, theme_styles: dict = None) -> dict:
    """Build a stats section from StatsContent"""
    import copy

    template = copy.deepcopy(SECTION_TEMPLATES["stats"]["structure"])

    # Build stat items
    stat_items = []
    for i, stat in enumerate(content.stats):
        item = copy.deepcopy(COMPONENT_TEMPLATES["stat_item"])
        item["blockId"] = f"stat-{i}"

        for child in item.get("children", []):
            if "number" in child.get("blockId", ""):
                child["blockId"] = f"stat-number-{i}"
                child["innerHTML"] = stat.number
            elif "label" in child.get("blockId", ""):
                child["blockId"] = f"stat-label-{i}"
                child["innerHTML"] = stat.label

        stat_items.append(item)

    # Fill slots
    def fill_slots(block):
        if isinstance(block, dict):
            if block.get("slot") == "stat_items":
                return stat_items
            elif "children" in block:
                block["children"] = [
                    filled for filled in
                    [fill_slots(child) for child in block["children"]]
                    if filled is not None
                ]
                new_children = []
                for child in block["children"]:
                    if isinstance(child, list):
                        new_children.extend(child)
                    else:
                        new_children.append(child)
                block["children"] = new_children
        return block

    return fill_slots(template)


def build_faq_section(content, theme_styles: dict = None) -> dict:
    """Build a FAQ section from FaqContent"""
    import copy

    template = copy.deepcopy(SECTION_TEMPLATES["faq"]["structure"])

    # Build FAQ items
    faq_items = []
    for i, faq in enumerate(content.faqs):
        item = copy.deepcopy(COMPONENT_TEMPLATES["faq_item"])
        item["blockId"] = f"faq-item-{i}"

        for child in item.get("children", []):
            if "question" in child.get("blockId", ""):
                child["blockId"] = f"faq-question-{i}"
                child["innerHTML"] = faq.question
            elif "answer" in child.get("blockId", ""):
                child["blockId"] = f"faq-answer-{i}"
                child["innerHTML"] = faq.answer

        faq_items.append(item)

    # Fill slots
    def fill_slots(block):
        if isinstance(block, dict):
            if block.get("slot") == "section_title":
                return {
                    "blockId": "faq-title",
                    "element": "h2",
                    "innerHTML": content.section_title,
                    "baseStyles": {
                        "fontSize": "40px",
                        "fontWeight": "700",
                        "marginBottom": "16px",
                    }
                }
            elif block.get("slot") == "section_description":
                if content.section_description:
                    return {
                        "blockId": "faq-description",
                        "element": "p",
                        "innerHTML": content.section_description,
                        "baseStyles": {
                            "fontSize": "18px",
                            "color": "var(--muted-color)",
                        }
                    }
                return None
            elif block.get("slot") == "faq_items":
                return faq_items
            elif "children" in block:
                block["children"] = [
                    filled for filled in
                    [fill_slots(child) for child in block["children"]]
                    if filled is not None
                ]
                new_children = []
                for child in block["children"]:
                    if isinstance(child, list):
                        new_children.extend(child)
                    else:
                        new_children.append(child)
                block["children"] = new_children
        return block

    return fill_slots(template)


def build_section_from_content(section_type: str, content, theme_styles: dict = None) -> Optional[dict]:
    """
    Build a section from content using the appropriate builder.

    Args:
        section_type: Type of section (hero, features, etc.)
        content: Content object (HeroContent, FeaturesContent, etc.)
        theme_styles: Optional theme-specific styles

    Returns:
        dict: Complete section block ready for Frappe Builder
    """
    # Auto-select hero variant based on image presence
    def hero_variant_for_content(c):
        # Use split layout if there's an image, otherwise centered
        if hasattr(c, 'image_url') and c.image_url:
            return "split"
        return "centered"

    builders = {
        "hero": lambda c: build_hero_section(c, hero_variant_for_content(c), theme_styles),
        "hero_centered": lambda c: build_hero_section(c, "centered", theme_styles),
        "hero_split": lambda c: build_hero_section(c, "split", theme_styles),
        "features": lambda c: build_features_section(c, "grid", theme_styles),
        "features_grid": lambda c: build_features_section(c, "grid", theme_styles),
        "features_alternating": lambda c: build_features_section(c, "alternating", theme_styles),
        "testimonials": lambda c: build_testimonials_section(c, theme_styles),
        "pricing": lambda c: build_pricing_section(c, theme_styles),
        "cta": lambda c: build_cta_section(c, theme_styles),
        "stats": lambda c: build_stats_section(c, theme_styles),
        "faq": lambda c: build_faq_section(c, theme_styles),
    }

    builder = builders.get(section_type)
    if builder:
        return builder(content)

    return None


__all__ = [
    "SECTION_TEMPLATES",
    "COMPONENT_TEMPLATES",
    "get_section_template",
    "get_component_template",
    "build_hero_section",
    "build_features_section",
    "build_testimonials_section",
    "build_pricing_section",
    "build_cta_section",
    "build_stats_section",
    "build_faq_section",
    "build_section_from_content",
]
