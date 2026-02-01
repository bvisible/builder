"""
Footer Generator
Generates footers from declarative configurations using templates.
"""

from typing import Optional
import frappe

from builder.ai.config import get_ai_settings
from builder.ai.providers import get_provider
from builder.ai.schemas.footer_schema import (
    FooterConfig, FooterColumn, FooterLink, SocialLinks,
    FOOTER_TYPE_DESCRIPTIONS, DEFAULT_FOOTER_COLUMNS
)
from builder.ai.design_system import get_theme
from builder.ai.prompts import get_footer_prompt
from builder.ai.templates.footers import build_footer_from_config


class FooterGenerator:
    """
    Generates footer blocks from FooterConfig using templates.
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
        site_type: str = "standard",
        company_name: str = None
    ) -> FooterConfig:
        """
        Generate footer configuration using AI.

        Args:
            site_description: Description of the site
            site_type: Type of footer
            company_name: Company name for copyright

        Returns:
            FooterConfig: Configuration for footer generation
        """
        prompt = get_footer_prompt(
            site_type=site_type,
            site_description=site_description,
            company_info=company_name or "Company",
            footer_type=site_type,
            include_newsletter=site_type in ["extended", "ecommerce", "saas"],
            social_platforms=["twitter", "linkedin", "github"]
        )

        try:
            config = self.llm.generate_structured(
                prompt=prompt,
                schema=FooterConfig,
                temperature=0.5
            )
            return config
        except Exception as e:
            frappe.log_error("Footer config generation failed", str(e))
            return self._get_default_config(site_type, company_name)

    def generate(
        self,
        config: FooterConfig = None,
        site_description: str = None,
        site_type: str = "standard",
        company_name: str = None,
        theme: str = "modern"
    ) -> dict:
        """
        Generate footer block.

        Args:
            config: Pre-made FooterConfig
            site_description: Site description
            site_type: Type of footer
            company_name: Company name
            theme: Visual theme

        Returns:
            dict: Frappe Builder block for footer
        """
        if not config:
            config = self.generate_config(
                site_description=site_description or "Website",
                site_type=site_type,
                company_name=company_name
            )

        theme_data = get_theme(theme)
        # Use template-based generation
        return build_footer_from_config(config, theme_data)

    def _get_default_config(self, site_type: str, company_name: str = None) -> FooterConfig:
        """Get default config if AI generation fails"""
        columns = DEFAULT_FOOTER_COLUMNS.get(site_type, DEFAULT_FOOTER_COLUMNS.get("standard", []))

        return FooterConfig(
            type=site_type,
            layout="columns",
            show_logo=True,
            logo_value=company_name or "Brand",
            columns=columns,
            show_social=True,
            social_links=SocialLinks(
                twitter="https://twitter.com",
                linkedin="https://linkedin.com"
            ),
            company_name=company_name or "Company",
            copyright_text="All rights reserved.",
            show_newsletter=site_type in ["extended", "ecommerce", "saas"],
        )


def generate_footer(
    site_type: str = "standard",
    company_name: str = None,
    site_description: str = None,
    theme: str = "modern"
) -> dict:
    """Convenience function to generate a footer"""
    generator = FooterGenerator()
    return generator.generate(
        site_type=site_type,
        company_name=company_name,
        site_description=site_description,
        theme=theme
    )


__all__ = [
    "FooterGenerator",
    "generate_footer",
]
