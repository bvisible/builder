"""
Footer Generator
Generates footers from declarative configurations.
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


class FooterGenerator:
    """
    Generates footer blocks from FooterConfig.
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
            frappe.log_error(f"Footer config generation failed: {e}")
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
        return self._build_footer_block(config, theme_data)

    def _build_footer_block(self, config: FooterConfig, theme: dict) -> dict:
        """Build the actual footer block from configuration"""
        styles = theme.get("styles", {}).get("footer", {})

        footer = {
            "blockId": "footer-main",
            "element": "footer",
            "baseStyles": {
                "padding": "64px 24px 24px",
                "backgroundColor": "var(--surface-color)",
                **{k: v for k, v in styles.items() if v}
            },
            "mobileStyles": {
                "padding": "48px 16px 16px",
            },
            "children": []
        }

        # Container for content
        container = {
            "blockId": "footer-container",
            "element": "div",
            "baseStyles": {
                "maxWidth": "1200px",
                "marginLeft": "auto",
                "marginRight": "auto",
            },
            "children": []
        }

        # Top section with columns
        if config.columns or config.show_logo or config.show_newsletter:
            top_section = self._build_top_section(config)
            container["children"].append(top_section)

        # Bottom section with copyright and legal
        bottom_section = self._build_bottom_section(config)
        container["children"].append(bottom_section)

        footer["children"].append(container)
        return footer

    def _build_top_section(self, config: FooterConfig) -> dict:
        """Build the main content area of footer"""
        section = {
            "blockId": "footer-top",
            "element": "div",
            "baseStyles": {
                "display": "grid",
                "gridTemplateColumns": f"repeat({len(config.columns) + (1 if config.show_logo else 0)}, 1fr)",
                "gap": "48px",
                "marginBottom": "48px",
                "paddingBottom": "48px",
                "borderBottom": "1px solid var(--border-color)",
            },
            "mobileStyles": {
                "gridTemplateColumns": "1fr",
                "gap": "32px",
            },
            "children": []
        }

        # Logo/brand column
        if config.show_logo:
            brand_col = {
                "blockId": "footer-brand",
                "element": "div",
                "children": []
            }

            if config.logo_value:
                brand_col["children"].append({
                    "blockId": "footer-logo",
                    "element": "div",
                    "innerHTML": config.logo_value,
                    "baseStyles": {
                        "fontSize": "20px",
                        "fontWeight": "700",
                        "marginBottom": "16px",
                    }
                })

            if config.tagline:
                brand_col["children"].append({
                    "blockId": "footer-tagline",
                    "element": "p",
                    "innerHTML": config.tagline,
                    "baseStyles": {
                        "color": "var(--muted-color)",
                        "marginBottom": "24px",
                    }
                })

            # Social links
            if config.show_social and config.social_links:
                social_block = self._build_social_links(config.social_links)
                brand_col["children"].append(social_block)

            section["children"].append(brand_col)

        # Link columns
        for i, column in enumerate(config.columns):
            col_block = self._build_link_column(column, i)
            section["children"].append(col_block)

        # Newsletter column
        if config.show_newsletter and config.newsletter:
            newsletter_col = self._build_newsletter_column(config)
            section["children"].append(newsletter_col)

        return section

    def _build_link_column(self, column: FooterColumn, index: int) -> dict:
        """Build a column of links"""
        col = {
            "blockId": f"footer-col-{index}",
            "element": "div",
            "children": [
                {
                    "blockId": f"footer-col-{index}-title",
                    "element": "h4",
                    "innerHTML": column.title,
                    "baseStyles": {
                        "fontSize": "14px",
                        "fontWeight": "600",
                        "textTransform": "uppercase",
                        "letterSpacing": "0.05em",
                        "marginBottom": "16px",
                        "color": "var(--text-color)",
                    }
                },
                {
                    "blockId": f"footer-col-{index}-links",
                    "element": "ul",
                    "baseStyles": {
                        "listStyle": "none",
                        "padding": "0",
                        "margin": "0",
                    },
                    "children": [
                        {
                            "blockId": f"footer-link-{index}-{j}",
                            "element": "li",
                            "baseStyles": {"marginBottom": "12px"},
                            "children": [{
                                "blockId": f"footer-link-{index}-{j}-a",
                                "element": "a",
                                "innerHTML": link.label,
                                "attributes": {
                                    "href": link.href,
                                    **({"target": "_blank"} if link.is_external else {})
                                },
                                "baseStyles": {
                                    "color": "var(--muted-color)",
                                    "textDecoration": "none",
                                    "transition": "color 200ms ease",
                                }
                            }]
                        }
                        for j, link in enumerate(column.links)
                    ]
                }
            ]
        }
        return col

    def _build_social_links(self, social: SocialLinks) -> dict:
        """Build social media links"""
        active_links = social.get_active_links()

        social_icons = {
            "facebook": "f",
            "twitter": "𝕏",
            "instagram": "📷",
            "linkedin": "in",
            "youtube": "▶",
            "github": "⌘",
        }

        return {
            "blockId": "footer-social",
            "element": "div",
            "baseStyles": {
                "display": "flex",
                "gap": "12px",
            },
            "children": [
                {
                    "blockId": f"footer-social-{platform}",
                    "element": "a",
                    "innerHTML": social_icons.get(platform, platform[0].upper()),
                    "attributes": {
                        "href": url,
                        "target": "_blank",
                        "rel": "noopener noreferrer"
                    },
                    "baseStyles": {
                        "width": "40px",
                        "height": "40px",
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "center",
                        "borderRadius": "50%",
                        "backgroundColor": "var(--border-color)",
                        "color": "var(--text-color)",
                        "textDecoration": "none",
                        "transition": "background-color 200ms ease",
                    }
                }
                for platform, url in active_links.items()
            ]
        }

    def _build_newsletter_column(self, config: FooterConfig) -> dict:
        """Build newsletter signup column"""
        newsletter = config.newsletter

        return {
            "blockId": "footer-newsletter",
            "element": "div",
            "children": [
                {
                    "blockId": "footer-newsletter-title",
                    "element": "h4",
                    "innerHTML": newsletter.title,
                    "baseStyles": {
                        "fontSize": "14px",
                        "fontWeight": "600",
                        "textTransform": "uppercase",
                        "letterSpacing": "0.05em",
                        "marginBottom": "16px",
                    }
                },
                {
                    "blockId": "footer-newsletter-desc",
                    "element": "p",
                    "innerHTML": newsletter.description or "Get updates in your inbox.",
                    "baseStyles": {
                        "color": "var(--muted-color)",
                        "marginBottom": "16px",
                    }
                },
                {
                    "blockId": "footer-newsletter-form",
                    "element": "form",
                    "baseStyles": {
                        "display": "flex",
                        "gap": "8px",
                    },
                    "children": [
                        {
                            "blockId": "footer-newsletter-input",
                            "element": "input",
                            "attributes": {
                                "type": "email",
                                "placeholder": newsletter.placeholder
                            },
                            "baseStyles": {
                                "flex": "1",
                                "padding": "10px 16px",
                                "border": "1px solid var(--border-color)",
                                "borderRadius": "6px",
                            }
                        },
                        {
                            "blockId": "footer-newsletter-button",
                            "element": "button",
                            "innerHTML": newsletter.button_text,
                            "attributes": {"type": "submit"},
                            "baseStyles": {
                                "padding": "10px 20px",
                                "backgroundColor": "var(--primary-color)",
                                "color": "#ffffff",
                                "border": "none",
                                "borderRadius": "6px",
                                "fontWeight": "500",
                                "cursor": "pointer",
                            }
                        }
                    ]
                }
            ]
        }

    def _build_bottom_section(self, config: FooterConfig) -> dict:
        """Build bottom section with copyright and legal links"""
        import datetime
        year = datetime.datetime.now().year if config.show_year else ""

        company = config.company_name or "Company"
        copyright_text = f"© {year} {company}. {config.copyright_text}"

        section = {
            "blockId": "footer-bottom",
            "element": "div",
            "baseStyles": {
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "flexWrap": "wrap",
                "gap": "16px",
            },
            "mobileStyles": {
                "flexDirection": "column",
                "textAlign": "center",
            },
            "children": [
                {
                    "blockId": "footer-copyright",
                    "element": "p",
                    "innerHTML": copyright_text,
                    "baseStyles": {
                        "color": "var(--muted-color)",
                        "fontSize": "14px",
                    }
                },
                {
                    "blockId": "footer-legal",
                    "element": "div",
                    "baseStyles": {
                        "display": "flex",
                        "gap": "24px",
                    },
                    "children": [
                        {
                            "blockId": f"footer-legal-{i}",
                            "element": "a",
                            "innerHTML": link.label,
                            "attributes": {"href": link.href},
                            "baseStyles": {
                                "color": "var(--muted-color)",
                                "fontSize": "14px",
                                "textDecoration": "none",
                            }
                        }
                        for i, link in enumerate(config.legal_links)
                    ]
                }
            ]
        }

        return section

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
