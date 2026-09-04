#//// Neoffice — added file (no upstream equivalent): design-system package: tokens, base styles,
#//// themes. builder/ai/** = the Neoffice AI site generator; frappe/builder ships no such module. First
#//// commit 563d9875 2026-02-01.
# Design System Module
# Design tokens, styles, and themes for consistent UI generation

from builder.ai.design_system.tokens import DESIGN_TOKENS, get_token
from builder.ai.design_system.styles import BASE_STYLES, get_component_styles
from builder.ai.design_system.themes import (
    THEMES,
    get_theme,
    list_themes,
    get_theme_prompt,
    get_theme_characteristics,
    get_theme_anti_patterns,
    apply_theme_to_block,
    get_theme_styles_for_section,
)

__all__ = [
    # Tokens
    "DESIGN_TOKENS",
    "get_token",
    # Styles
    "BASE_STYLES",
    "get_component_styles",
    # Themes
    "THEMES",
    "get_theme",
    "list_themes",
    "get_theme_prompt",
    "get_theme_characteristics",
    "get_theme_anti_patterns",
    "apply_theme_to_block",
    "get_theme_styles_for_section",
]
