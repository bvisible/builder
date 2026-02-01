"""
Header Generator
Generates headers from declarative configurations using templates.
"""

from typing import Optional
import frappe

from builder.ai.config import get_ai_settings
from builder.ai.providers import get_provider
from builder.ai.schemas.header_schema import HeaderConfig, MenuItem, HEADER_TYPE_DESCRIPTIONS
from builder.ai.design_system import get_theme
from builder.ai.prompts import get_header_prompt
from builder.ai.templates.headers import build_header_from_config


class HeaderGenerator:
    """
    Generates header blocks from HeaderConfig using templates.

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
            frappe.log_error("Header config generation failed", str(e))
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
        # Use template-based generation
        return build_header_from_config(config, theme_data)

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
        pages = pages or ["Home", "About", "Services", "Contact"]

        # Use anchor links for single-page sites, URLs for multi-page
        if site_type == "single_page":
            menu_items = [
                MenuItem(
                    label=page,
                    href=f"#{page.lower().replace(' ', '-')}" if page != "Home" else "#hero"
                )
                for page in pages
            ]
        else:
            menu_items = [
                MenuItem(
                    label=page,
                    href=f"/{page.lower().replace(' ', '-')}" if page != "Home" else "/"
                )
                for page in pages
            ]

        # Use image logo by default with standard path
        return HeaderConfig(
            type=site_type,
            layout="logo_left_menu_right",
            logo_type="image",
            logo_value="/files/logo-default.png",
            logo_alt="Logo",
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
