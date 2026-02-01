"""
Page Generator
Main orchestrator for multi-pass page generation.
"""

from typing import Optional
import frappe

from builder.ai.config import get_ai_settings, AIConfig
from builder.ai.providers import get_provider
from builder.ai.schemas.block_schema import PageStructure, SectionInfo
from builder.ai.design_system import get_theme
from builder.ai.prompts import get_analysis_prompt
from builder.ai.validators import BlockValidator, AutoFixer
from builder.ai.generators.section_generator import SectionGenerator
from builder.ai.generators.header_generator import HeaderGenerator
from builder.ai.generators.footer_generator import FooterGenerator


class PageGenerator:
    """
    Multi-pass page generator for Frappe Builder.

    Pipeline:
    1. ANALYSIS: Parse user prompt and determine optimal page structure
    2. CONTEXT: Load theme and design system tokens
    3. GENERATION: Generate header, sections, footer using templates
    4. VALIDATION: Validate and auto-fix all blocks
    5. ASSEMBLY: Combine into final page

    This generator orchestrates specialized generators:
    - HeaderGenerator: Template-based header generation
    - SectionGenerator: Content-only generation + templates
    - FooterGenerator: Template-based footer generation
    """

    def __init__(
        self,
        provider: str = None,
        model: str = None,
        config: AIConfig = None
    ):
        self.config = config or get_ai_settings()

        if provider:
            self.config.provider = provider
        if model:
            self.config.model = model

        # Main LLM for analysis
        self.llm = get_provider(
            self.config.provider,
            model=self.config.model,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            temperature=self.config.temperature,
        )

        # Specialized generators
        self.header_generator = HeaderGenerator(provider=provider, model=model)
        self.section_generator = SectionGenerator(provider=provider, model=model)
        self.footer_generator = FooterGenerator(provider=provider, model=model)

        # Validators
        self.validator = BlockValidator()
        self.auto_fixer = AutoFixer()

    def generate_page(
        self,
        prompt: str,
        theme: str = None,
        site_type: str = None,
        include_header: bool = True,
        include_footer: bool = True
    ) -> list[dict]:
        """
        Generate a complete page from a prompt.

        Args:
            prompt: User's description of the desired page
            theme: Visual theme (modern, neobrutalist, etc.)
            site_type: Type of site (single_page, ecommerce, etc.)
            include_header: Whether to generate header
            include_footer: Whether to generate footer

        Returns:
            list[dict]: List of Frappe Builder blocks
        """
        theme = theme or self.config.default_theme
        site_type = site_type or self.config.default_site_type

        # =========================================================
        # PASS 1: ANALYSIS - Understand what to build
        # =========================================================
        structure = self._analyze_structure(prompt, site_type)
        frappe.logger().info(f"Page structure: {structure.page_type} with {len(structure.sections)} sections")

        # =========================================================
        # PASS 2: CONTEXT - Load theme and design tokens
        # =========================================================
        theme_data = get_theme(theme)
        theme_name = theme_data.get("name", theme)

        # =========================================================
        # PASS 3: GENERATION - Build all page components
        # =========================================================
        blocks = []

        # 3.1 Generate header
        if include_header:
            header_block = self._generate_header(
                prompt=prompt,
                structure=structure,
                theme=theme_name,
                site_type=site_type
            )
            if header_block:
                blocks.append(header_block)

        # 3.2 Generate content sections
        for section in structure.sections:
            section_block = self._generate_section(
                section=section,
                context=prompt,
                theme=theme_name
            )
            if section_block:
                blocks.append(section_block)

        # 3.3 Generate footer
        if include_footer:
            footer_block = self._generate_footer(
                prompt=prompt,
                structure=structure,
                theme=theme_name,
                site_type=site_type
            )
            if footer_block:
                blocks.append(footer_block)

        # =========================================================
        # PASS 4: VALIDATION - Ensure quality
        # =========================================================
        validated_blocks = []
        for block in blocks:
            fixed_block = self._validate_and_fix(block)
            validated_blocks.append(fixed_block)

        return validated_blocks

    def _analyze_structure(self, prompt: str, site_type: str) -> PageStructure:
        """
        PASS 1: Analyze the prompt and determine optimal page structure.

        Uses AI to understand:
        - What type of page is requested
        - What sections are needed
        - Optimal order and priority
        - Suggested theme and colors
        """
        analysis_prompt = get_analysis_prompt(prompt, site_type)

        try:
            structure = self.llm.generate_structured(
                prompt=analysis_prompt,
                schema=PageStructure,
                system_prompt=self._get_analysis_system_prompt(),
                temperature=0.3  # Lower temp for analytical tasks
            )

            # Validate and enrich structure
            structure = self._enrich_structure(structure, site_type)
            return structure

        except Exception as e:
            frappe.log_error("Structure analysis failed", str(e))
            return self._get_default_structure(site_type)

    def _get_analysis_system_prompt(self) -> str:
        """System prompt for structure analysis"""
        return """You are an expert web designer analyzing page requirements.

Your task is to determine the optimal structure for a web page based on the user's description.

Consider:
1. What is the primary purpose of this page?
2. What sections will best achieve that purpose?
3. What's the logical flow of information?
4. What header/footer type best suits this page?

Output a structured PageStructure with:
- page_type: The category of page
- sections: List of sections with type, title, description, priority
- header_type: Appropriate header style
- footer_type: Appropriate footer style
- theme_suggestion: A visual theme that fits the content

Be specific and thoughtful. Quality over quantity for sections.
Most landing pages need only 4-6 sections."""

    def _enrich_structure(self, structure: PageStructure, site_type: str) -> PageStructure:
        """Enrich and validate the analyzed structure"""
        # Ensure header_type matches site_type if not specified
        if not structure.header_type:
            structure.header_type = site_type

        # Ensure we have at least one section
        if not structure.sections:
            structure.sections = [
                SectionInfo(type="hero", title="Hero Section", priority=10),
            ]

        # Sort sections by priority (highest first)
        structure.sections = sorted(
            structure.sections,
            key=lambda s: s.priority,
            reverse=True
        )

        # Limit to reasonable number of sections
        if len(structure.sections) > 8:
            structure.sections = structure.sections[:8]

        return structure

    def _get_default_structure(self, site_type: str) -> PageStructure:
        """Get a sensible default structure based on site type"""
        default_sections = {
            "single_page": [
                SectionInfo(type="hero", title="Hero", priority=10),
                SectionInfo(type="features", title="Features", priority=8),
                SectionInfo(type="testimonials", title="Testimonials", priority=6),
                SectionInfo(type="cta", title="Call to Action", priority=5),
            ],
            "multi_page": [
                SectionInfo(type="hero", title="Hero", priority=10),
                SectionInfo(type="features", title="Features", priority=8),
                SectionInfo(type="stats", title="Statistics", priority=7),
                SectionInfo(type="testimonials", title="Testimonials", priority=6),
                SectionInfo(type="cta", title="Call to Action", priority=5),
            ],
            "ecommerce": [
                SectionInfo(type="hero", title="Hero", priority=10),
                SectionInfo(type="features", title="Features", priority=8),
                SectionInfo(type="pricing", title="Pricing", priority=7),
                SectionInfo(type="testimonials", title="Testimonials", priority=6),
                SectionInfo(type="faq", title="FAQ", priority=5),
                SectionInfo(type="cta", title="Call to Action", priority=4),
            ],
            "saas": [
                SectionInfo(type="hero", title="Hero", priority=10),
                SectionInfo(type="features", title="Features", priority=9),
                SectionInfo(type="stats", title="Statistics", priority=7),
                SectionInfo(type="pricing", title="Pricing", priority=8),
                SectionInfo(type="testimonials", title="Testimonials", priority=6),
                SectionInfo(type="faq", title="FAQ", priority=5),
                SectionInfo(type="cta", title="Call to Action", priority=4),
            ],
            "blog": [
                SectionInfo(type="hero", title="Hero", priority=10),
                SectionInfo(type="features", title="Categories", priority=8),
                SectionInfo(type="cta", title="Subscribe", priority=6),
            ],
            "portfolio": [
                SectionInfo(type="hero", title="Hero", priority=10),
                SectionInfo(type="features", title="Work", priority=9),
                SectionInfo(type="testimonials", title="Testimonials", priority=7),
                SectionInfo(type="cta", title="Contact", priority=5),
            ],
        }

        sections = default_sections.get(site_type, default_sections["multi_page"])

        return PageStructure(
            page_type="landing",
            sections=sections,
            header_type=site_type,
            footer_type="standard",
            theme_suggestion="modern"
        )

    def _generate_header(
        self,
        prompt: str,
        structure: PageStructure,
        theme: str,
        site_type: str
    ) -> Optional[dict]:
        """Generate header using HeaderGenerator"""
        try:
            # Extract page names from sections for navigation
            pages = self._extract_nav_pages(structure)

            return self.header_generator.generate(
                site_description=prompt,
                site_type=structure.header_type or site_type,
                pages=pages,
                theme=theme
            )
        except Exception as e:
            frappe.log_error("Header generation failed", str(e))
            return self._get_fallback_header()

    def _generate_section(
        self,
        section: SectionInfo,
        context: str,
        theme: str
    ) -> Optional[dict]:
        """Generate a section using SectionGenerator"""
        try:
            return self.section_generator.generate(
                section_type=section.type,
                context=context,
                theme=theme,
                description=section.description
            )
        except Exception as e:
            frappe.log_error(f"Section generation failed: {section.type}", str(e))
            return None

    def _generate_footer(
        self,
        prompt: str,
        structure: PageStructure,
        theme: str,
        site_type: str
    ) -> Optional[dict]:
        """Generate footer using FooterGenerator"""
        try:
            return self.footer_generator.generate(
                site_description=prompt,
                site_type=structure.footer_type or "standard",
                theme=theme
            )
        except Exception as e:
            frappe.log_error("Footer generation failed", str(e))
            return self._get_fallback_footer()

    def _extract_nav_pages(self, structure: PageStructure) -> list[str]:
        """Extract navigation page names from structure"""
        # For single-page sites, use section titles as anchors
        if structure.header_type == "single_page":
            return [s.title for s in structure.sections[:5]]

        # For multi-page, use standard pages
        return ["Home", "About", "Services", "Contact"]

    def _validate_and_fix(self, block: dict) -> dict:
        """PASS 4: Validate and auto-fix a block"""
        is_valid = self.validator.validate(block)

        if not is_valid:
            block = self.auto_fixer.fix(block)

        return block

    def _get_fallback_header(self) -> dict:
        """Fallback header if generation fails"""
        return {
            "blockId": "header-main",
            "element": "header",
            "baseStyles": {
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "space-between",
                "padding": "16px 24px",
                "backgroundColor": "var(--surface-color)",
            },
            "children": [
                {
                    "blockId": "header-logo",
                    "element": "a",
                    "innerHTML": "Brand",
                    "attributes": {"href": "/"},
                    "baseStyles": {
                        "fontSize": "20px",
                        "fontWeight": "700",
                        "textDecoration": "none",
                        "color": "var(--text-color)",
                    }
                }
            ]
        }

    def _get_fallback_footer(self) -> dict:
        """Fallback footer if generation fails"""
        return {
            "blockId": "footer-main",
            "element": "footer",
            "baseStyles": {
                "padding": "48px 24px",
                "backgroundColor": "var(--surface-color)",
                "textAlign": "center",
            },
            "children": [
                {
                    "blockId": "footer-copyright",
                    "element": "p",
                    "innerHTML": "© 2024 Company. All rights reserved.",
                    "baseStyles": {
                        "color": "var(--muted-color)",
                        "fontSize": "14px",
                    }
                }
            ]
        }


def generate_page(
    prompt: str,
    theme: str = "modern",
    site_type: str = "multi_page",
    provider: str = None,
    model: str = None,
    include_header: bool = True,
    include_footer: bool = True
) -> list[dict]:
    """
    Convenience function to generate a page.

    Args:
        prompt: Description of the desired page
        theme: Visual theme
        site_type: Type of site
        provider: AI provider override
        model: Model override
        include_header: Include header block
        include_footer: Include footer block

    Returns:
        list[dict]: Generated Frappe Builder blocks
    """
    generator = PageGenerator(provider=provider, model=model)
    return generator.generate_page(
        prompt=prompt,
        theme=theme,
        site_type=site_type,
        include_header=include_header,
        include_footer=include_footer
    )


__all__ = [
    "PageGenerator",
    "generate_page",
]
