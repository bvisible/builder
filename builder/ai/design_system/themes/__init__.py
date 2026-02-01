"""
Design Themes
Creative visual themes for AI-generated pages.
Each theme provides colors, styles, and creative guidance.
"""

from builder.ai.design_system.themes.modern import MODERN_THEME
from builder.ai.design_system.themes.neobrutalist import NEOBRUTALIST_THEME
from builder.ai.design_system.themes.glassmorphism import GLASSMORPHISM_THEME
from builder.ai.design_system.themes.minimal import MINIMAL_THEME
from builder.ai.design_system.themes.corporate import CORPORATE_THEME
from builder.ai.design_system.themes.creative import CREATIVE_THEME


THEMES = {
    "modern": MODERN_THEME,
    "neobrutalist": NEOBRUTALIST_THEME,
    "glassmorphism": GLASSMORPHISM_THEME,
    "minimal": MINIMAL_THEME,
    "corporate": CORPORATE_THEME,
    "creative": CREATIVE_THEME,
}


def get_theme(theme_name: str) -> dict:
    """
    Get theme configuration by name.

    Args:
        theme_name: Name of the theme

    Returns:
        Theme configuration dict with colors, styles, characteristics
    """
    return THEMES.get(theme_name, MODERN_THEME)


def list_themes() -> list[str]:
    """Get list of available theme names"""
    return list(THEMES.keys())


def get_theme_prompt(theme_name: str) -> str:
    """
    Get the creative guidance prompt for a theme.

    Args:
        theme_name: Name of the theme

    Returns:
        str: Creative guidance prompt for the theme
    """
    theme = get_theme(theme_name)
    return theme.get("prompt", "")


def get_theme_characteristics(theme_name: str) -> list[str]:
    """Get the visual characteristics of a theme"""
    theme = get_theme(theme_name)
    return theme.get("characteristics", [])


def get_theme_anti_patterns(theme_name: str) -> list[str]:
    """Get the anti-patterns to avoid for a theme"""
    theme = get_theme(theme_name)
    return theme.get("anti_patterns", [])


__all__ = [
    "THEMES",
    "get_theme",
    "list_themes",
    "get_theme_prompt",
    "get_theme_characteristics",
    "get_theme_anti_patterns",
    "MODERN_THEME",
    "NEOBRUTALIST_THEME",
    "GLASSMORPHISM_THEME",
    "MINIMAL_THEME",
    "CORPORATE_THEME",
    "CREATIVE_THEME",
]
