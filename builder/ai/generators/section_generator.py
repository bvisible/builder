"""
Section Generator
Generates individual page sections using templates and content schemas.
"""

from typing import Optional
import frappe

from builder.ai.config import get_ai_settings, AIConfig
from builder.ai.providers import get_provider
from builder.ai.schemas.block_schema import (
    SectionInfo,
    get_content_schema_for_section,
    HeroContent,
    FeaturesContent,
    TestimonialsContent,
    PricingContent,
    CtaContent,
    StatsContent,
    FaqContent,
)
from builder.ai.design_system import get_theme
from builder.ai.templates.sections import build_section_from_content


class SectionGenerator:
    """
    Generates individual page sections using templates.

    The AI's job is simplified:
    1. Generate content (text, descriptions) using structured schemas
    2. Template system handles structure and styling

    This ensures consistent, well-structured output while allowing
    creative content generation.
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

    def generate(
        self,
        section_type: str,
        context: str,
        theme: str = "modern",
        description: str = None
    ) -> Optional[dict]:
        """
        Generate a single section using template + AI content.

        Args:
            section_type: Type of section (hero, features, etc.)
            context: Page/site context for relevant content
            theme: Visual theme name
            description: Additional section description

        Returns:
            dict: Generated Frappe Builder block
        """
        theme_data = get_theme(theme)

        # Get the content schema for this section type
        content_schema = get_content_schema_for_section(section_type)

        if content_schema:
            # Use template-based generation
            return self._generate_with_template(
                section_type=section_type,
                content_schema=content_schema,
                context=context,
                description=description,
                theme_data=theme_data
            )
        else:
            # Fallback: no template available, use basic generation
            frappe.log_error(f"No content schema for section type: {section_type}")
            return self._generate_fallback(section_type, context, theme_data)

    def _generate_with_template(
        self,
        section_type: str,
        content_schema,
        context: str,
        description: str,
        theme_data: dict
    ) -> Optional[dict]:
        """Generate section using template and content schema"""

        # Build prompt for content generation
        prompt = self._build_content_prompt(section_type, context, description, theme_data)

        try:
            # AI generates only the content
            content = self.llm.generate_structured(
                prompt=prompt,
                schema=content_schema,
                system_prompt=self._get_content_system_prompt(theme_data),
                temperature=self.config.temperature
            )

            # Build section from template + content
            theme_styles = theme_data.get("styles", {}).get(section_type, {})
            section = build_section_from_content(section_type, content, theme_styles)

            if section:
                return section
            else:
                frappe.log_error(f"Failed to build section from content: {section_type}")
                return self._generate_fallback(section_type, context, theme_data)

        except Exception as e:
            frappe.log_error(f"Section content generation failed: {e}")
            return self._generate_fallback(section_type, context, theme_data)

    def _build_content_prompt(
        self,
        section_type: str,
        context: str,
        description: str,
        theme_data: dict
    ) -> str:
        """Build prompt for content generation"""
        theme_name = theme_data.get("name", "Modern")

        prompt = f"""Generate content for a {section_type} section.

SITE CONTEXT: {context}

THEME: {theme_name}
{theme_data.get('characteristics', '')}

"""
        if description:
            prompt += f"SPECIFIC REQUIREMENTS: {description}\n\n"

        # Add section-specific guidance
        guidance = self._get_section_guidance(section_type)
        if guidance:
            prompt += f"CONTENT GUIDELINES:\n{guidance}\n\n"

        prompt += """IMPORTANT:
- Write compelling, realistic content (NO placeholder text like Lorem ipsum)
- Match the tone and style to the site context
- Be specific and creative with your content
- Keep text concise and impactful
"""
        return prompt

    def _get_content_system_prompt(self, theme_data: dict) -> str:
        """Get system prompt for content generation"""
        return """You are an expert copywriter generating website content.

Your task is to generate compelling, realistic content for website sections.
The content should be professional, engaging, and appropriate for the given context.

RULES:
- Never use placeholder text (Lorem ipsum, etc.)
- Write in a natural, professional tone
- Be specific and creative
- Match content to the site's purpose and audience
- Keep text concise - websites need scannable content

Respond only with the structured content - no explanations."""

    def _get_section_guidance(self, section_type: str) -> str:
        """Get section-specific content guidance"""
        guidance = {
            "hero": """
- Headline: 5-10 words, impactful and clear value proposition
- Subheadline: 1-2 sentences expanding on the headline
- Badge: Optional, use for announcements or key differentiators
- CTAs: Action-oriented, clear benefit""",
            "features": """
- Section title: Clear and benefit-focused
- Each feature: Concrete benefit with real examples
- Icons: Use meaningful emojis that relate to the feature
- Descriptions: Focus on user benefits, not just features""",
            "testimonials": """
- Quotes: Authentic-sounding, specific praise
- Include concrete results or outcomes when possible
- Names: Realistic full names
- Titles: Include company name for B2B contexts""",
            "pricing": """
- Tier names: Descriptive (Starter, Pro, Enterprise)
- Prices: Realistic for the product category
- Features: Mix of included and excluded items
- Mark one tier as popular/recommended""",
            "cta": """
- Headline: Urgency or clear value proposition
- Keep it short and action-focused
- Button text: Action verb (Get Started, Start Free Trial)""",
            "stats": """
- Use impressive but believable numbers
- Include units (K, M, %, etc.)
- Labels should be specific and meaningful""",
            "faq": """
- Questions: Common concerns customers have
- Answers: Clear, helpful, not too long
- Address objections and build trust""",
        }
        return guidance.get(section_type, "")

    def _generate_fallback(
        self,
        section_type: str,
        context: str,
        theme_data: dict
    ) -> dict:
        """Generate a basic fallback section"""
        return {
            "blockId": f"{section_type}-section",
            "element": "section",
            "baseStyles": {
                "padding": "80px 24px",
                "textAlign": "center",
            },
            "children": [
                {
                    "blockId": f"{section_type}-placeholder",
                    "element": "p",
                    "innerHTML": f"{section_type.title()} section content goes here",
                    "baseStyles": {
                        "color": "var(--muted-color)",
                        "fontSize": "16px",
                    }
                }
            ]
        }

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
