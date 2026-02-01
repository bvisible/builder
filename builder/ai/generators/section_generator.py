"""
Section Generator
Generates individual page sections.
"""

from typing import Optional
import frappe

from builder.ai.config import get_ai_settings, AIConfig
from builder.ai.providers import get_provider, BaseProvider
from builder.ai.schemas.block_schema import FrappeBlock, SectionInfo
from builder.ai.design_system import get_theme
from builder.ai.prompts import get_section_prompt, CREATIVE_GUIDANCE
from builder.ai.prompts.creative_prompts import get_style_prompt
from builder.ai.prompts.anti_patterns import format_anti_patterns_for_prompt
from builder.ai.rag import get_examples_for_section
from builder.ai.validators import AutoFixer


class SectionGenerator:
    """
    Generates individual page sections with creative styling.
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

        self.llm = get_provider(
            self.config.provider,
            model=self.config.model,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            temperature=self.config.temperature,
        )
        self.auto_fixer = AutoFixer()

    def generate(
        self,
        section_type: str,
        context: str,
        theme: str = "modern",
        description: str = None
    ) -> Optional[dict]:
        """
        Generate a single section.

        Args:
            section_type: Type of section (hero, features, etc.)
            context: Page/site context for relevant content
            theme: Visual theme name
            description: Additional section description

        Returns:
            dict: Generated Frappe Builder block
        """
        theme_data = get_theme(theme)

        # Build comprehensive prompt
        system_prompt = self._build_system_prompt(section_type, theme_data)
        user_prompt = self._build_user_prompt(section_type, context, description)

        try:
            block = self.llm.generate_with_retry(
                prompt=user_prompt,
                schema=FrappeBlock,
                system_prompt=system_prompt,
                max_retries=self.config.max_retries
            )
            return self.auto_fixer.fix(block.to_dict())
        except Exception as e:
            frappe.log_error(f"Section generation failed: {e}")
            return None

    def generate_multiple(
        self,
        sections: list[SectionInfo],
        context: str,
        theme: str = "modern"
    ) -> list[dict]:
        """
        Generate multiple sections.

        Args:
            sections: List of SectionInfo objects
            context: Page context
            theme: Visual theme

        Returns:
            list[dict]: List of generated blocks
        """
        blocks = []
        for section in sections:
            block = self.generate(
                section_type=section.type,
                context=context,
                theme=theme,
                description=section.description
            )
            if block:
                blocks.append(block)
        return blocks

    def _build_system_prompt(self, section_type: str, theme: dict) -> str:
        """Build the system prompt with all context"""
        parts = [
            "You are an expert UI designer generating Frappe Builder blocks.",
            "",
            "## OUTPUT FORMAT",
            "Respond with valid JSON only - no markdown, no explanations.",
            "",
            f"## THEME: {theme.get('name', 'Modern')}",
            theme.get("prompt", ""),
            "",
            "## SECTION-SPECIFIC GUIDANCE",
            get_style_prompt(section_type) or f"Create a compelling {section_type} section.",
            "",
            "## ANTI-PATTERNS",
            format_anti_patterns_for_prompt(section_type),
        ]

        # Add examples if available
        examples = get_examples_for_section(section_type, max_examples=2)
        if examples:
            parts.extend(["", "## REFERENCE EXAMPLES", examples])

        parts.extend(["", CREATIVE_GUIDANCE])

        return "\n".join(parts)

    def _build_user_prompt(
        self,
        section_type: str,
        context: str,
        description: str = None
    ) -> str:
        """Build the user prompt"""
        prompt = f"""Generate a {section_type} section.

CONTEXT: {context}
"""
        if description:
            prompt += f"REQUIREMENTS: {description}\n"

        prompt += f"""
Create a creative, unique {section_type} section as a FrappeBlock JSON.
- Use blockId prefix: "{section_type}-"
- Include realistic content (no Lorem ipsum)
- Apply the theme styles consistently
- Ensure mobile responsiveness with mobileStyles
"""
        return prompt


def generate_section(
    section_type: str,
    context: str,
    theme: str = "modern",
    provider: str = None
) -> Optional[dict]:
    """
    Convenience function to generate a section.
    """
    generator = SectionGenerator(provider=provider)
    return generator.generate(
        section_type=section_type,
        context=context,
        theme=theme
    )


__all__ = [
    "SectionGenerator",
    "generate_section",
]
