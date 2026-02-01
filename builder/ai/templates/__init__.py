"""
AI Templates Module
Pre-built block templates for consistent AI generation.
"""

from builder.ai.templates.headers import (
    HEADER_TEMPLATES,
    get_header_template,
    build_header_from_config,
)
from builder.ai.templates.footers import (
    FOOTER_TEMPLATES,
    get_footer_template,
    build_footer_from_config,
)
from builder.ai.templates.sections import (
    SECTION_TEMPLATES,
    COMPONENT_TEMPLATES,
    get_section_template,
    get_component_template,
    build_section_from_content,
    build_hero_section,
    build_features_section,
    build_testimonials_section,
    build_pricing_section,
    build_cta_section,
    build_stats_section,
    build_faq_section,
)
from builder.ai.templates.webshop_headers import (
    WEBSHOP_HEADER_VARIATIONS,
    build_webshop_header,
    build_webshop_header_standard,
    build_webshop_header_centered,
    build_webshop_header_minimal,
    build_webshop_header_mega,
    build_webshop_header_transparent,
    build_webshop_header_split,
    get_webshop_header_variations,
)
from builder.ai.templates.webshop_footers import (
    WEBSHOP_FOOTER_VARIATIONS,
    build_webshop_footer,
    build_webshop_footer_standard,
    build_webshop_footer_simple,
    build_webshop_footer_centered,
    build_webshop_footer_dark,
    build_webshop_footer_minimal,
    build_webshop_footer_newsletter,
    get_webshop_footer_variations,
)

__all__ = [
    # Headers
    "HEADER_TEMPLATES",
    "get_header_template",
    "build_header_from_config",
    # Footers
    "FOOTER_TEMPLATES",
    "get_footer_template",
    "build_footer_from_config",
    # Sections
    "SECTION_TEMPLATES",
    "COMPONENT_TEMPLATES",
    "get_section_template",
    "get_component_template",
    "build_section_from_content",
    "build_hero_section",
    "build_features_section",
    "build_testimonials_section",
    "build_pricing_section",
    "build_cta_section",
    "build_stats_section",
    "build_faq_section",
    # Webshop Headers
    "WEBSHOP_HEADER_VARIATIONS",
    "build_webshop_header",
    "build_webshop_header_standard",
    "build_webshop_header_centered",
    "build_webshop_header_minimal",
    "build_webshop_header_mega",
    "build_webshop_header_transparent",
    "build_webshop_header_split",
    "get_webshop_header_variations",
    # Webshop Footers
    "WEBSHOP_FOOTER_VARIATIONS",
    "build_webshop_footer",
    "build_webshop_footer_standard",
    "build_webshop_footer_simple",
    "build_webshop_footer_centered",
    "build_webshop_footer_dark",
    "build_webshop_footer_minimal",
    "build_webshop_footer_newsletter",
    "get_webshop_footer_variations",
]
