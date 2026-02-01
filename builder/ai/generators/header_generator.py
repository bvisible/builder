"""
Header Generator
Generates headers from declarative configurations.
"""

from typing import Optional
import json
import frappe

from builder.ai.config import get_ai_settings
from builder.ai.providers import get_provider
from builder.ai.schemas.header_schema import HeaderConfig, HeaderType, HEADER_TYPE_DESCRIPTIONS
from builder.ai.design_system import get_theme
from builder.ai.prompts import get_header_prompt


class HeaderGenerator:
    """
    Generates header blocks from HeaderConfig.

    The AI's job is simplified to:
    1. Choose the appropriate header type
    2. Fill in the content (logo, menu items, etc.)

    The actual block structure comes from templates.
    """

    def __init__(self, provider: str = None, model: str = None):
        self.config = get_ai_settings()
        if provider:
            self.config.provider = provider
        if model:
            self.config.model = model

        self.llm = get_provider(
            self.config.provider,
            model=self.config.model,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
        )

    def generate_config(
        self,
        site_description: str,
        site_type: str = "multi_page",
        pages: list[str] = None
    ) -> HeaderConfig:
        """
        Generate header configuration using AI.

        Args:
            site_description: Description of the site
            site_type: Type of site
            pages: List of page names for navigation

        Returns:
            HeaderConfig: Configuration for header generation
        """
        # Determine features based on site type
        features = self._get_features_for_type(site_type)

        prompt = get_header_prompt(
            site_type=site_type,
            site_description=site_description,
            pages=pages or ["Home", "About", "Services", "Contact"],
            header_type=site_type,
            layout="logo_left_menu_right",
            features=features
        )

        try:
            config = self.llm.generate_structured(
                prompt=prompt,
                schema=HeaderConfig,
                temperature=0.5
            )
            return config
        except Exception as e:
            frappe.log_error(f"Header config generation failed: {e}")
            return self._get_default_config(site_type, pages)

    def generate(
        self,
        config: HeaderConfig = None,
        site_description: str = None,
        site_type: str = "multi_page",
        pages: list[str] = None,
        theme: str = "modern"
    ) -> dict:
        """
        Generate header block from config or by generating config first.

        Args:
            config: Pre-made HeaderConfig
            site_description: Site description (used if config not provided)
            site_type: Site type
            pages: Navigation pages
            theme: Visual theme

        Returns:
            dict: Frappe Builder block for header
        """
        if not config:
            config = self.generate_config(
                site_description=site_description or "Website",
                site_type=site_type,
                pages=pages
            )

        theme_data = get_theme(theme)
        return self._build_header_block(config, theme_data)

    def _build_header_block(self, config: HeaderConfig, theme: dict) -> dict:
        """
        Build the actual header block from configuration.
        """
        # Get base styles from theme
        styles = theme.get("styles", {}).get("header", {})

        # Build header structure based on layout
        header = {
            "blockId": "header-main",
            "element": "header",
            "baseStyles": {
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "space-between",
                "padding": "16px 24px",
                "backgroundColor": "var(--surface-color)",
                "position": "sticky" if config.sticky else "relative",
                "top": "0" if config.sticky else None,
                "zIndex": "1000" if config.sticky else None,
                **{k: v for k, v in styles.items() if v}
            },
            "mobileStyles": {
                "padding": "12px 16px",
            },
            "children": []
        }

        # Add logo
        logo_block = self._build_logo_block(config)
        header["children"].append(logo_block)

        # Add navigation
        nav_block = self._build_nav_block(config)
        header["children"].append(nav_block)

        # Add action buttons (login, signup, cart, etc.)
        if self._has_action_buttons(config):
            actions_block = self._build_actions_block(config)
            header["children"].append(actions_block)

        return header

    def _build_logo_block(self, config: HeaderConfig) -> dict:
        """Build logo block"""
        if config.logo_type == "text":
            return {
                "blockId": "header-logo",
                "element": "a",
                "innerHTML": config.logo_value,
                "attributes": {"href": "/"},
                "baseStyles": {
                    "fontSize": "20px",
                    "fontWeight": "700",
                    "color": "var(--text-color)",
                    "textDecoration": "none",
                }
            }
        else:  # image
            return {
                "blockId": "header-logo",
                "element": "a",
                "attributes": {"href": "/"},
                "children": [{
                    "blockId": "header-logo-img",
                    "element": "img",
                    "attributes": {
                        "src": config.logo_value,
                        "alt": config.logo_alt or "Logo"
                    },
                    "baseStyles": {
                        "height": "40px",
                        "width": "auto",
                    }
                }]
            }

    def _build_nav_block(self, config: HeaderConfig) -> dict:
        """Build navigation block"""
        nav = {
            "blockId": "header-nav",
            "element": "nav",
            "baseStyles": {
                "display": "flex",
                "alignItems": "center",
                "gap": "24px",
            },
            "mobileStyles": {
                "display": "none",  # Hide on mobile, would need hamburger
            },
            "children": []
        }

        for i, item in enumerate(config.menu_items):
            if item.is_cta:
                # CTA button style
                link = {
                    "blockId": f"header-nav-{i}",
                    "element": "a",
                    "innerHTML": item.label,
                    "attributes": {
                        "href": item.href,
                        **({"target": "_blank"} if item.is_external else {})
                    },
                    "baseStyles": {
                        "padding": "10px 20px",
                        "backgroundColor": "var(--primary-color)",
                        "color": "#ffffff",
                        "borderRadius": "6px",
                        "fontWeight": "500",
                        "textDecoration": "none",
                    }
                }
            else:
                # Regular link
                link = {
                    "blockId": f"header-nav-{i}",
                    "element": "a",
                    "innerHTML": item.label,
                    "attributes": {
                        "href": item.href,
                        **({"target": "_blank"} if item.is_external else {})
                    },
                    "baseStyles": {
                        "color": "var(--text-color)",
                        "textDecoration": "none",
                        "fontWeight": "500",
                        "transition": "color 200ms ease",
                    }
                }
            nav["children"].append(link)

        return nav

    def _build_actions_block(self, config: HeaderConfig) -> dict:
        """Build action buttons block (login, cart, etc.)"""
        actions = {
            "blockId": "header-actions",
            "element": "div",
            "baseStyles": {
                "display": "flex",
                "alignItems": "center",
                "gap": "12px",
            },
            "children": []
        }

        if config.show_search:
            actions["children"].append({
                "blockId": "header-search",
                "element": "button",
                "innerHTML": "🔍",
                "baseStyles": {
                    "padding": "8px",
                    "background": "transparent",
                    "border": "none",
                    "cursor": "pointer",
                }
            })

        if config.show_cart:
            actions["children"].append({
                "blockId": "header-cart",
                "element": "a",
                "innerHTML": "🛒",
                "attributes": {"href": "/cart"},
                "baseStyles": {
                    "padding": "8px",
                    "textDecoration": "none",
                }
            })

        if config.show_login:
            actions["children"].append({
                "blockId": "header-login",
                "element": "a",
                "innerHTML": config.login_text,
                "attributes": {"href": "/login"},
                "baseStyles": {
                    "color": "var(--text-color)",
                    "textDecoration": "none",
                    "fontWeight": "500",
                }
            })

        if config.show_signup:
            actions["children"].append({
                "blockId": "header-signup",
                "element": "a",
                "innerHTML": config.signup_text,
                "attributes": {"href": "/signup"},
                "baseStyles": {
                    "padding": "10px 20px",
                    "backgroundColor": "var(--primary-color)",
                    "color": "#ffffff",
                    "borderRadius": "6px",
                    "fontWeight": "500",
                    "textDecoration": "none",
                }
            })

        return actions

    def _has_action_buttons(self, config: HeaderConfig) -> bool:
        """Check if config has any action buttons"""
        return any([
            config.show_cart,
            config.show_search,
            config.show_wishlist,
            config.show_user_menu,
            config.show_login,
            config.show_signup,
        ])

    def _get_features_for_type(self, site_type: str) -> list[str]:
        """Get expected features for site type"""
        features_map = {
            "single_page": ["anchor navigation", "smooth scroll"],
            "multi_page": ["page navigation", "dropdown menus"],
            "multi_page_auth": ["page navigation", "login", "signup"],
            "ecommerce": ["search", "cart", "wishlist", "user menu", "categories"],
            "blog": ["categories", "search", "subscribe"],
            "portfolio": ["minimal", "contact link"],
            "saas": ["product nav", "pricing", "login", "signup"],
        }
        return features_map.get(site_type, ["basic navigation"])

    def _get_default_config(self, site_type: str, pages: list[str] = None) -> HeaderConfig:
        """Get default config if AI generation fails"""
        from builder.ai.schemas.header_schema import MenuItem

        pages = pages or ["Home", "About", "Services", "Contact"]
        menu_items = [
            MenuItem(label=page, href=f"/{page.lower()}" if page != "Home" else "/")
            for page in pages
        ]

        return HeaderConfig(
            type=site_type,
            layout="logo_left_menu_right",
            logo_type="text",
            logo_value="Brand",
            menu_items=menu_items,
            sticky=True,
            show_login=site_type in ["multi_page_auth", "saas", "ecommerce"],
            show_signup=site_type in ["multi_page_auth", "saas"],
            show_cart=site_type == "ecommerce",
            show_search=site_type in ["ecommerce", "blog"],
        )


def generate_header(
    site_type: str,
    pages: list[str] = None,
    site_description: str = None,
    theme: str = "modern"
) -> dict:
    """Convenience function to generate a header"""
    generator = HeaderGenerator()
    return generator.generate(
        site_type=site_type,
        pages=pages,
        site_description=site_description,
        theme=theme
    )


__all__ = [
    "HeaderGenerator",
    "generate_header",
]
