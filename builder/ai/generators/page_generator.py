"""
Page Generator
Main orchestrator for multi-pass page generation.
"""

from typing import Optional
import frappe

from builder.ai.config import get_ai_settings, AIConfig
from builder.ai.providers import get_provider, BaseProvider
from builder.ai.schemas.block_schema import FrappeBlock, PageStructure, SectionInfo
from builder.ai.schemas.header_schema import HeaderConfig
from builder.ai.schemas.footer_schema import FooterConfig
from builder.ai.design_system import get_theme, DESIGN_TOKENS
from builder.ai.design_system.tokens import get_token
from builder.ai.prompts import (
    get_main_prompt,
    get_analysis_prompt,
    CREATIVE_GUIDANCE,
)
from builder.ai.prompts.anti_patterns import format_anti_patterns_for_prompt
from builder.ai.validators import BlockValidator, AutoFixer
from builder.ai.rag import get_examples_for_section


class PageGenerator:
    """
    Multi-pass page generator for Frappe Builder.

    Pipeline:
    1. ANALYSIS: Parse user prompt and determine structure
    2. ENRICHMENT: Inject design system and RAG examples
    3. GENERATION: Generate each section with structured output
    4. VALIDATION: Validate and auto-fix blocks
    5. ASSEMBLY: Combine all blocks into final page
    """

    def __init__(
        self,
        provider: str = None,
        model: str = None,
        config: AIConfig = None
    ):
        """
        Initialize the page generator.

        Args:
            provider: AI provider name (ollama, openai)
            model: Model name override
            config: Pre-configured AIConfig
        """
        self.config = config or get_ai_settings()

        # Override provider/model if specified
        if provider:
            self.config.provider = provider
        if model:
            self.config.model = model

        self.llm = get_provider(
            self.config.provider,
            model=self.config.model,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            temperature=self.config.temperature,
        )

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

        # PASS 1: Analyze structure
        structure = self._analyze_structure(prompt, site_type)

        # PASS 2: Get theme and prepare context
        theme_data = get_theme(theme)

        # PASS 3: Generate sections
        blocks = []

        # Generate header if requested
        if include_header:
            header_block = self._generate_header(
                prompt=prompt,
                structure=structure,
                theme=theme_data
            )
            if header_block:
                blocks.append(header_block)

        # Generate content sections
        for section in structure.sections:
            section_block = self._generate_section(
                section=section,
                page_context=prompt,
                theme=theme_data
            )
            if section_block:
                blocks.append(section_block)

        # Generate footer if requested
        if include_footer:
            footer_block = self._generate_footer(
                prompt=prompt,
                structure=structure,
                theme=theme_data
            )
            if footer_block:
                blocks.append(footer_block)

        # PASS 4: Validate and fix
        validated_blocks = []
        for block in blocks:
            fixed_block = self._validate_and_fix(block)
            validated_blocks.append(fixed_block)

        return validated_blocks

    def _analyze_structure(self, prompt: str, site_type: str) -> PageStructure:
        """
        PASS 1: Analyze the prompt and determine page structure.
        """
        analysis_prompt = get_analysis_prompt(prompt, site_type)

        try:
            structure = self.llm.generate_structured(
                prompt=analysis_prompt,
                schema=PageStructure,
                temperature=0.3  # Lower temp for analysis
            )
            return structure
        except Exception as e:
            frappe.log_error(f"Structure analysis failed: {e}")
            # Return default structure
            return PageStructure(
                page_type="landing",
                sections=[
                    SectionInfo(type="hero", title="Hero", priority=10),
                    SectionInfo(type="features", title="Features", priority=8),
                    SectionInfo(type="cta", title="Call to Action", priority=6),
                ],
                header_type="multi_page",
                footer_type="standard"
            )

    def _generate_section(
        self,
        section: SectionInfo,
        page_context: str,
        theme: dict
    ) -> Optional[dict]:
        """
        PASS 3: Generate a single section.
        """
        # Build the prompt
        theme_prompt = theme.get("prompt", "")
        examples = get_examples_for_section(section.type, max_examples=2)
        anti_patterns = format_anti_patterns_for_prompt(section.type)

        system_prompt = get_main_prompt(
            design_tokens=self._format_design_tokens(),
            theme_guidelines=theme_prompt
        )
        system_prompt += f"\n\n{CREATIVE_GUIDANCE}"
        system_prompt += f"\n\n{anti_patterns}"

        if examples:
            system_prompt += f"\n\n{examples}"

        user_prompt = f"""
Generate a {section.type} section for this page:

PAGE CONTEXT: {page_context}
SECTION PURPOSE: {section.title}
{f'SECTION DETAILS: {section.description}' if section.description else ''}

Generate a complete, creative {section.type} section as a FrappeBlock JSON.
The blockId should start with "{section.type}-".
"""

        try:
            block = self.llm.generate_structured(
                prompt=user_prompt,
                schema=FrappeBlock,
                system_prompt=system_prompt,
                temperature=self.config.temperature
            )
            return block.to_dict()
        except Exception as e:
            frappe.log_error(f"Section generation failed ({section.type}): {e}")
            return None

    def _generate_header(
        self,
        prompt: str,
        structure: PageStructure,
        theme: dict
    ) -> Optional[dict]:
        """Generate header block"""
        # Use HeaderGenerator in Phase 2
        # For now, return a basic header structure
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
            "children": []
        }

    def _generate_footer(
        self,
        prompt: str,
        structure: PageStructure,
        theme: dict
    ) -> Optional[dict]:
        """Generate footer block"""
        # Use FooterGenerator in Phase 2
        # For now, return a basic footer structure
        return {
            "blockId": "footer-main",
            "element": "footer",
            "baseStyles": {
                "padding": "48px 24px",
                "backgroundColor": "var(--surface-color)",
            },
            "children": []
        }

    def _validate_and_fix(self, block: dict) -> dict:
        """
        PASS 4: Validate and auto-fix a block.
        """
        # First validate
        is_valid = self.validator.validate(block)

        if not is_valid:
            # Auto-fix issues
            block = self.auto_fixer.fix(block)

        return block

    def _format_design_tokens(self) -> str:
        """Format design tokens for prompt injection"""
        return f"""
SPACING: xs=4px, sm=8px, md=16px, lg=24px, xl=32px, section=80px
TYPOGRAPHY: xs=12px, sm=14px, base=16px, lg=18px, xl=20px, 2xl=24px, 3xl=30px, 4xl=36px
COLORS: Use var(--primary-color), var(--surface-color), var(--text-color), var(--muted-color)
RADIUS: sm=4px, md=6px, lg=8px, xl=12px, 2xl=16px, full=9999px
SHADOWS: sm="0 1px 3px rgba(0,0,0,0.1)", md="0 4px 6px rgba(0,0,0,0.1)", lg="0 10px 15px rgba(0,0,0,0.1)"
"""


def generate_page(
    prompt: str,
    theme: str = "modern",
    site_type: str = "multi_page",
    provider: str = None,
    model: str = None
) -> list[dict]:
    """
    Convenience function to generate a page.

    Args:
        prompt: Description of the desired page
        theme: Visual theme
        site_type: Type of site
        provider: AI provider override
        model: Model override

    Returns:
        list[dict]: Generated Frappe Builder blocks
    """
    generator = PageGenerator(provider=provider, model=model)
    return generator.generate_page(
        prompt=prompt,
        theme=theme,
        site_type=site_type
    )


__all__ = [
    "PageGenerator",
    "generate_page",
]
