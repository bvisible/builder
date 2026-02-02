"""
Header Generator
Generates headers from declarative configurations using templates.
"""

from typing import Optional
import frappe

from builder.ai.config import get_ai_settings
from builder.ai.providers import get_provider
from builder.ai.schemas.header_schema import HeaderConfig, NavItem, HEADER_TYPE_DESCRIPTIONS
from builder.ai.design_system import get_theme
from builder.ai.prompts import get_header_prompt
from builder.ai.templates.headers import build_header


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

        # Use template-based generation (theme is applied via CSS variables)
        return build_header(config)

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
        # Use factory methods when available
        factory_methods = {
            "single_page": lambda: HeaderConfig.for_single_page(sections=pages),
            "ecommerce": lambda: HeaderConfig.for_ecommerce(categories=pages),
            "saas": lambda: HeaderConfig.for_saas(pages=pages),
            "portfolio": lambda: HeaderConfig.for_portfolio(),
            "blog": lambda: HeaderConfig.for_blog(categories=pages),
        }

        if site_type in factory_methods:
            return factory_methods[site_type]()

        # Default fallback for unknown site types
        pages = pages or ["Home", "About", "Services", "Contact"]
        nav_items = [
            NavItem(
                label=page,
                href=f"/{page.lower().replace(' ', '-')}" if page != "Home" else "/"
            )
            for page in pages
        ]

        return HeaderConfig(
            layout="logo_menu_cta",
            logo_type="image",
            logo_value="/files/logo-default.png",
            nav_items=nav_items,
            sticky=True,
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
