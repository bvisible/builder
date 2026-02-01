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
]
