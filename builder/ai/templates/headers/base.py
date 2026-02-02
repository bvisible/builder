"""
Header Base Module
Common constants, utilities, and base styles for the configurable header system.
"""

import uuid
from typing import Optional


# =============================================================================
# ID GENERATION
# =============================================================================

def generate_unique_id(prefix: str = "header") -> str:
    """Generate a unique block ID with the given prefix"""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# =============================================================================
# STYLE CONSTANTS
# =============================================================================

# Header container padding
HEADER_PADDING_DESKTOP = "16px 48px"
HEADER_PADDING_TABLET = "14px 32px"
HEADER_PADDING_MOBILE = "12px 16px"

# Logo sizes
LOGO_HEIGHT_DESKTOP = "36px"
LOGO_HEIGHT_MOBILE = "32px"
LOGO_FONT_SIZE = "22px"

# Navigation gaps
NAV_GAP = "28px"
NAV_GAP_MOBILE = "16px"

# Icon button sizes
ICON_BUTTON_SIZE = "40px"
ICON_SVG_SIZE = "20"
ICON_GAP = "4px"

# Search bar width
SEARCH_BAR_WIDTH = "200px"
SEARCH_BAR_WIDTH_EXPANDED = "280px"

# CTA button
CTA_PADDING = "10px 20px"
CTA_BORDER_RADIUS = "8px"

# Z-index values
HEADER_Z_INDEX = "1000"
SIDEBAR_Z_INDEX = "2000"
OVERLAY_Z_INDEX = "1999"

# Transitions
TRANSITION_FAST = "150ms ease"
TRANSITION_NORMAL = "200ms ease"
TRANSITION_SLOW = "300ms ease"


# =============================================================================
# BASE STYLES
# =============================================================================

def get_header_base_styles(
    sticky: bool = True,
    transparent: bool = False,
    blur_on_scroll: bool = False
) -> dict:
    """Get base styles for header container"""
    styles = {
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "space-between",
        "padding": HEADER_PADDING_DESKTOP,
        "backgroundColor": "var(--surface-color, #ffffff)",
        "transition": f"background-color {TRANSITION_NORMAL}",
    }

    if sticky:
        styles["position"] = "sticky"
        styles["top"] = "0"
        styles["zIndex"] = HEADER_Z_INDEX

    if transparent:
        styles["backgroundColor"] = "transparent"
        styles["position"] = "absolute"
        styles["left"] = "0"
        styles["right"] = "0"

    if blur_on_scroll and not transparent:
        styles["backdropFilter"] = "blur(10px)"
        styles["backgroundColor"] = "rgba(255, 255, 255, 0.85)"

    return styles


def get_header_mobile_styles() -> dict:
    """Get mobile styles for header container"""
    return {
        "padding": HEADER_PADDING_MOBILE,
    }


# =============================================================================
# LOGO STYLES
# =============================================================================

def get_logo_text_styles() -> dict:
    """Get styles for text logo"""
    return {
        "fontSize": LOGO_FONT_SIZE,
        "fontWeight": "700",
        "color": "var(--text-color)",
        "textDecoration": "none",
        "letterSpacing": "-0.02em",
        "whiteSpace": "nowrap",
    }


def get_logo_image_styles() -> dict:
    """Get styles for image logo"""
    return {
        "height": LOGO_HEIGHT_DESKTOP,
        "width": "auto",
        "objectFit": "contain",
    }


def get_logo_image_mobile_styles() -> dict:
    """Get mobile styles for image logo"""
    return {
        "height": LOGO_HEIGHT_MOBILE,
    }


# =============================================================================
# NAVIGATION STYLES
# =============================================================================

def get_nav_container_styles() -> dict:
    """Get styles for navigation container"""
    return {
        "display": "flex",
        "alignItems": "center",
        "gap": NAV_GAP,
    }


def get_nav_link_styles() -> dict:
    """Get styles for navigation links"""
    return {
        "color": "var(--text-color)",
        "textDecoration": "none",
        "fontWeight": "500",
        "fontSize": "15px",
        "padding": "8px 4px",
        "transition": f"color {TRANSITION_FAST}",
        "whiteSpace": "nowrap",
    }


# =============================================================================
# ICON BUTTON STYLES
# =============================================================================

def get_icon_button_styles() -> dict:
    """Get styles for icon buttons (search, cart, wishlist, user)"""
    return {
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
        "width": ICON_BUTTON_SIZE,
        "height": ICON_BUTTON_SIZE,
        "padding": "0",
        "border": "none",
        "borderRadius": "50%",
        "backgroundColor": "transparent",
        "color": "var(--text-color)",
        "cursor": "pointer",
        "textDecoration": "none",
        "transition": f"background-color {TRANSITION_FAST}",
    }


def get_icons_group_styles() -> dict:
    """Get styles for icons container"""
    return {
        "display": "flex",
        "alignItems": "center",
        "gap": ICON_GAP,
    }


# =============================================================================
# CTA BUTTON STYLES
# =============================================================================

def get_cta_button_styles() -> dict:
    """Get styles for CTA button"""
    return {
        "display": "inline-flex",
        "alignItems": "center",
        "justifyContent": "center",
        "padding": CTA_PADDING,
        "backgroundColor": "var(--primary-color)",
        "color": "#ffffff",
        "borderRadius": CTA_BORDER_RADIUS,
        "fontWeight": "600",
        "fontSize": "14px",
        "textDecoration": "none",
        "border": "none",
        "cursor": "pointer",
        "transition": f"all {TRANSITION_NORMAL}",
        "whiteSpace": "nowrap",
    }


# =============================================================================
# SEARCH BAR STYLES
# =============================================================================

def get_search_bar_styles() -> dict:
    """Get styles for search bar input container"""
    return {
        "display": "flex",
        "alignItems": "center",
        "gap": "8px",
        "padding": "8px 12px",
        "backgroundColor": "var(--muted-color, #f5f5f5)",
        "borderRadius": "8px",
        "border": "1px solid var(--border-color, #e5e7eb)",
        "transition": f"all {TRANSITION_FAST}",
    }


def get_search_input_styles() -> dict:
    """Get styles for search input"""
    return {
        "width": SEARCH_BAR_WIDTH,
        "border": "none",
        "outline": "none",
        "backgroundColor": "transparent",
        "fontSize": "14px",
        "color": "var(--text-color)",
    }


# =============================================================================
# SVG ICON ATTRIBUTES
# =============================================================================

def get_svg_icon_attrs(size: str = ICON_SVG_SIZE) -> dict:
    """Get common SVG icon attributes"""
    return {
        "xmlns": "http://www.w3.org/2000/svg",
        "width": size,
        "height": size,
        "viewBox": "0 0 24 24",
        "fill": "none",
        "stroke": "currentColor",
        "stroke-width": "2",
        "stroke-linecap": "round",
        "stroke-linejoin": "round",
    }


__all__ = [
    # ID generation
    "generate_unique_id",
    # Style constants
    "HEADER_PADDING_DESKTOP",
    "HEADER_PADDING_TABLET",
    "HEADER_PADDING_MOBILE",
    "LOGO_HEIGHT_DESKTOP",
    "LOGO_HEIGHT_MOBILE",
    "LOGO_FONT_SIZE",
    "NAV_GAP",
    "NAV_GAP_MOBILE",
    "ICON_BUTTON_SIZE",
    "ICON_SVG_SIZE",
    "ICON_GAP",
    "SEARCH_BAR_WIDTH",
    "SEARCH_BAR_WIDTH_EXPANDED",
    "CTA_PADDING",
    "CTA_BORDER_RADIUS",
    "HEADER_Z_INDEX",
    "SIDEBAR_Z_INDEX",
    "OVERLAY_Z_INDEX",
    "TRANSITION_FAST",
    "TRANSITION_NORMAL",
    "TRANSITION_SLOW",
    # Style functions
    "get_header_base_styles",
    "get_header_mobile_styles",
    "get_logo_text_styles",
    "get_logo_image_styles",
    "get_logo_image_mobile_styles",
    "get_nav_container_styles",
    "get_nav_link_styles",
    "get_icon_button_styles",
    "get_icons_group_styles",
    "get_cta_button_styles",
    "get_search_bar_styles",
    "get_search_input_styles",
    "get_svg_icon_attrs",
]
