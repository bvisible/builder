"""
Header Burger Menu Module
Burger button and sidebar slide-in components for mobile navigation.

Features:
- Burger button (hamburger icon, hidden on desktop, shown on mobile)
- Sidebar overlay (dark backdrop)
- Sidebar panel (slide-in from right)
- Close button
- Auto-burger JavaScript (detects overflow and shows burger)
"""

from builder.ai.templates.headers.base import (
    generate_unique_id,
    get_svg_icon_attrs,
    get_nav_link_styles,
    get_cta_button_styles,
    get_icons_group_styles,
    SIDEBAR_Z_INDEX,
    OVERLAY_Z_INDEX,
    TRANSITION_SLOW,
)


# =============================================================================
# BURGER BUTTON
# =============================================================================

def build_burger_button(id_prefix: str = "header") -> dict:
    """
    Build the hamburger menu button (hidden on desktop, visible on mobile).

    The burger button triggers the sidebar slide-in on mobile.

    Args:
        id_prefix: Prefix for block IDs

    Returns:
        dict: Burger button block
    """
    return {
        "blockId": f"{id_prefix}-burger-btn",
        "element": "button",
        "attributes": {
            "type": "button",
            "aria-label": "Menu",
            "data-toggle": "sidebar",
        },
        "baseStyles": {
            "display": "none",  # Hidden on desktop
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
            "display": "flex",  # Shown on mobile
        },
        "children": [{
            "blockId": f"{id_prefix}-burger-icon",
            "element": "svg",
            "attributes": get_svg_icon_attrs("24"),
            "children": [
                {
                    "blockId": f"{id_prefix}-burger-line1",
                    "element": "line",
                    "attributes": {"x1": "3", "y1": "6", "x2": "21", "y2": "6"}
                },
                {
                    "blockId": f"{id_prefix}-burger-line2",
                    "element": "line",
                    "attributes": {"x1": "3", "y1": "12", "x2": "21", "y2": "12"}
                },
                {
                    "blockId": f"{id_prefix}-burger-line3",
                    "element": "line",
                    "attributes": {"x1": "3", "y1": "18", "x2": "21", "y2": "18"}
                },
            ]
        }]
    }


# =============================================================================
# CLOSE BUTTON
# =============================================================================

def build_close_button(id_prefix: str = "sidebar") -> dict:
    """
    Build close button for the sidebar.

    Args:
        id_prefix: Prefix for block IDs

    Returns:
        dict: Close button block
    """
    return {
        "blockId": f"{id_prefix}-close-btn",
        "element": "button",
        "attributes": {
            "type": "button",
            "aria-label": "Close menu",
            "data-close": "sidebar",
        },
        "baseStyles": {
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "width": "40px",
            "height": "40px",
            "padding": "0",
            "background": "transparent",
            "border": "none",
            "cursor": "pointer",
            "color": "var(--text-color)",
            "position": "absolute",
            "top": "16px",
            "right": "16px",
        },
        "children": [{
            "blockId": f"{id_prefix}-close-icon",
            "element": "svg",
            "attributes": get_svg_icon_attrs("24"),
            "children": [
                {
                    "blockId": f"{id_prefix}-close-line1",
                    "element": "line",
                    "attributes": {"x1": "18", "y1": "6", "x2": "6", "y2": "18"}
                },
                {
                    "blockId": f"{id_prefix}-close-line2",
                    "element": "line",
                    "attributes": {"x1": "6", "y1": "6", "x2": "18", "y2": "18"}
                },
            ]
        }]
    }


# =============================================================================
# SIDEBAR OVERLAY
# =============================================================================

def build_sidebar_overlay(id_prefix: str = "sidebar") -> dict:
    """
    Build the dark overlay backdrop for the sidebar.

    The overlay covers the entire screen when sidebar is open.
    Clicking it closes the sidebar.

    Args:
        id_prefix: Prefix for block IDs

    Returns:
        dict: Sidebar overlay block
    """
    return {
        "blockId": f"{id_prefix}-overlay",
        "element": "div",
        "attributes": {
            "data-overlay": "sidebar",
            "role": "presentation",
        },
        "baseStyles": {
            "position": "fixed",
            "top": "0",
            "left": "0",
            "right": "0",
            "bottom": "0",
            "backgroundColor": "rgba(0, 0, 0, 0.5)",
            "opacity": "0",
            "pointerEvents": "none",
            "transition": f"opacity {TRANSITION_SLOW}",
            "zIndex": OVERLAY_Z_INDEX,
        },
    }


# =============================================================================
# SIDEBAR PANEL
# =============================================================================

def build_sidebar_panel(
    nav_items: list = None,
    icons_block: dict = None,
    cta_text: str = None,
    cta_url: str = "#",
    id_prefix: str = "sidebar"
) -> dict:
    """
    Build the sidebar panel that slides in from the right.

    Content structure:
    - Close button (top right)
    - Navigation links (vertical)
    - Icons group (if provided)
    - CTA button (if provided)

    Args:
        nav_items: List of NavItem objects for navigation
        icons_block: Pre-built icons group block
        cta_text: CTA button text
        cta_url: CTA button URL
        id_prefix: Prefix for block IDs

    Returns:
        dict: Sidebar panel block
    """
    children = []

    # Close button
    children.append(build_close_button(id_prefix))

    # Navigation links (vertical layout)
    if nav_items:
        nav_links = []
        for i, item in enumerate(nav_items):
            link_styles = get_nav_link_styles()
            link_styles.update({
                "display": "block",
                "padding": "12px 0",
                "fontSize": "18px",
                "borderBottom": "1px solid var(--border-color, #e5e7eb)",
            })

            nav_links.append({
                "blockId": f"{id_prefix}-nav-link-{i}",
                "element": "a",
                "innerHTML": item.label,
                "attributes": {
                    "href": item.href,
                    **({"target": "_blank", "rel": "noopener"} if item.is_external else {})
                },
                "baseStyles": link_styles,
            })

        children.append({
            "blockId": f"{id_prefix}-nav",
            "element": "nav",
            "baseStyles": {
                "display": "flex",
                "flexDirection": "column",
                "marginTop": "60px",  # Space for close button
                "padding": "0 24px",
            },
            "children": nav_links,
        })

    # Icons group (at the bottom of nav)
    if icons_block:
        # Modify icons to be horizontal and centered
        icons_modified = {
            **icons_block,
            "blockId": f"{id_prefix}-icons",
            "baseStyles": {
                **get_icons_group_styles(),
                "justifyContent": "center",
                "padding": "24px",
            },
        }
        children.append(icons_modified)

    # CTA button (at the bottom)
    if cta_text:
        cta_styles = get_cta_button_styles()
        cta_styles.update({
            "width": "calc(100% - 48px)",
            "margin": "24px",
            "textAlign": "center",
        })

        children.append({
            "blockId": f"{id_prefix}-cta",
            "element": "a",
            "innerHTML": cta_text,
            "attributes": {"href": cta_url},
            "baseStyles": cta_styles,
        })

    return {
        "blockId": f"{id_prefix}-panel",
        "element": "aside",
        "attributes": {
            "data-panel": "sidebar",
            "role": "dialog",
            "aria-modal": "true",
        },
        "baseStyles": {
            "position": "fixed",
            "top": "0",
            "right": "0",
            "width": "300px",
            "maxWidth": "80vw",
            "height": "100vh",
            "backgroundColor": "var(--surface-color, #ffffff)",
            "boxShadow": "-4px 0 20px rgba(0, 0, 0, 0.15)",
            "transform": "translateX(100%)",
            "transition": f"transform {TRANSITION_SLOW}",
            "zIndex": SIDEBAR_Z_INDEX,
            "overflowY": "auto",
        },
        "children": children,
    }


# =============================================================================
# COMPLETE SIDEBAR COMPONENT
# =============================================================================

def build_sidebar(
    nav_items: list = None,
    icons_block: dict = None,
    cta_text: str = None,
    cta_url: str = "#",
    id_prefix: str = "sidebar"
) -> dict:
    """
    Build the complete sidebar component (overlay + panel).

    This component should be placed at the end of the header or body.

    Args:
        nav_items: List of NavItem objects for navigation
        icons_block: Pre-built icons group block
        cta_text: CTA button text
        cta_url: CTA button URL
        id_prefix: Prefix for block IDs

    Returns:
        dict: Complete sidebar wrapper block
    """
    return {
        "blockId": f"{id_prefix}-wrapper",
        "element": "div",
        "attributes": {
            "data-sidebar": "true",
        },
        "baseStyles": {
            "display": "none",  # Hidden by default on desktop
        },
        "mobileStyles": {
            "display": "block",  # Available on mobile
        },
        "children": [
            build_sidebar_overlay(id_prefix),
            build_sidebar_panel(nav_items, icons_block, cta_text, cta_url, id_prefix),
        ]
    }


# =============================================================================
# AUTO-BURGER JAVASCRIPT
# =============================================================================

AUTO_BURGER_SCRIPT = """
(function() {
  // Auto-burger: shows hamburger menu when content overflows
  function initAutoBurger() {
    const headers = document.querySelectorAll('[data-auto-burger]');

    headers.forEach(header => {
      const nav = header.querySelector('nav');
      const burger = header.querySelector('[data-toggle="sidebar"]');
      const sidebar = document.querySelector('[data-sidebar]');
      const overlay = document.querySelector('[data-overlay="sidebar"]');
      const panel = document.querySelector('[data-panel="sidebar"]');
      const closeBtn = document.querySelector('[data-close="sidebar"]');

      if (!burger) return;

      // Check if nav overflows
      function checkOverflow() {
        if (!nav) return;

        const headerWidth = header.offsetWidth;
        const contentWidth = calculateContentWidth(header);

        if (contentWidth > headerWidth - 40) {
          nav.style.display = 'none';
          burger.style.display = 'flex';
        } else {
          nav.style.display = '';
          burger.style.display = '';
        }
      }

      function calculateContentWidth(header) {
        let width = 0;
        Array.from(header.children).forEach(child => {
          if (child.offsetWidth) {
            width += child.offsetWidth + 24; // gap
          }
        });
        return width;
      }

      // Toggle sidebar
      function openSidebar() {
        if (!sidebar) return;
        sidebar.style.display = 'block';
        requestAnimationFrame(() => {
          overlay.style.opacity = '1';
          overlay.style.pointerEvents = 'auto';
          panel.style.transform = 'translateX(0)';
        });
        document.body.style.overflow = 'hidden';
      }

      function closeSidebar() {
        if (!sidebar) return;
        overlay.style.opacity = '0';
        overlay.style.pointerEvents = 'none';
        panel.style.transform = 'translateX(100%)';
        document.body.style.overflow = '';
        setTimeout(() => {
          sidebar.style.display = '';
        }, 300);
      }

      // Event listeners
      burger.addEventListener('click', openSidebar);
      if (overlay) overlay.addEventListener('click', closeSidebar);
      if (closeBtn) closeBtn.addEventListener('click', closeSidebar);

      // Close on link click
      if (panel) {
        panel.querySelectorAll('a').forEach(link => {
          link.addEventListener('click', closeSidebar);
        });
      }

      // Check on resize (debounced)
      let resizeTimer;
      window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(checkOverflow, 100);
      });

      // Initial check
      checkOverflow();
    });
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAutoBurger);
  } else {
    initAutoBurger();
  }
})();
"""


def get_auto_burger_script() -> str:
    """
    Get the auto-burger JavaScript code.

    This script should be included in the page to enable:
    - Auto-detection of navigation overflow
    - Burger menu toggle
    - Sidebar slide-in/out animations

    Returns:
        str: JavaScript code for auto-burger functionality
    """
    return AUTO_BURGER_SCRIPT.strip()


def build_script_block(id_prefix: str = "header") -> dict:
    """
    Build a script block containing the auto-burger JavaScript.

    This block can be added to the header children to include
    the JavaScript inline.

    Args:
        id_prefix: Prefix for block ID

    Returns:
        dict: Script block with auto-burger JavaScript
    """
    return {
        "blockId": f"{id_prefix}-script",
        "element": "script",
        "innerHTML": get_auto_burger_script(),
    }


__all__ = [
    # Burger button
    "build_burger_button",
    # Close button
    "build_close_button",
    # Sidebar components
    "build_sidebar_overlay",
    "build_sidebar_panel",
    "build_sidebar",
    # JavaScript
    "get_auto_burger_script",
    "build_script_block",
    "AUTO_BURGER_SCRIPT",
]
