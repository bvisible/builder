"""
Section Generator
Generates individual page sections using templates and content schemas.
"""

from typing import Optional
import frappe

from builder.ai.config import get_ai_settings, AIConfig
from builder.ai.generators.image_generator import ImageGenerator
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
        config: AIConfig = None,
        generate_images: bool = True
    ):
        self.config = config or get_ai_settings()
        self.generate_images = generate_images

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

        # Initialize image generator if enabled
        self.image_generator = None
        if self.generate_images:
            try:
                self.image_generator = ImageGenerator()
            except Exception as e:
                frappe.log_error("Failed to init ImageGenerator", str(e))
                self.generate_images = False

    def generate(
        self,
        section_type: str,
        context: str,
        theme: str = "modern",
        description: str = None,
        shortcodes_context: str = ""
    ) -> Optional[dict]:
        """
        Generate a single section using template + AI content.

        Args:
            section_type: Type of section (hero, features, etc.)
            context: Page/site context for relevant content
            theme: Visual theme name
            description: Additional section description
            shortcodes_context: Optional shortcodes documentation for dynamic content

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
                theme_data=theme_data,
                shortcodes_context=shortcodes_context
            )
        else:
            # Fallback: no template available, use basic generation
            frappe.log_error("No content schema for section", section_type)
            return self._generate_fallback(section_type, context, theme_data)

    def _generate_with_template(
        self,
        section_type: str,
        content_schema,
        context: str,
        description: str,
        theme_data: dict,
        shortcodes_context: str = ""
    ) -> Optional[dict]:
        """Generate section using template and content schema"""

        # Build prompt for content generation
        prompt = self._build_content_prompt(section_type, context, description, theme_data, shortcodes_context)

        try:
            # AI generates only the content
            content = self.llm.generate_structured(
                prompt=prompt,
                schema=content_schema,
                system_prompt=self._get_content_system_prompt(theme_data),
                temperature=self.config.temperature
            )

            # Generate images from prompts (if enabled)
            self._process_images(content, section_type)

            # Build section from template + content
            theme_styles = theme_data.get("styles", {}).get(section_type, {})
            section = build_section_from_content(section_type, content, theme_styles)

            if section:
                return section
            else:
                frappe.log_error("Failed to build section", section_type)
                return self._generate_fallback(section_type, context, theme_data)

        except Exception as e:
            frappe.log_error("Section content generation failed", str(e))
            return self._generate_fallback(section_type, context, theme_data)

    def _build_content_prompt(
        self,
        section_type: str,
        context: str,
        description: str,
        theme_data: dict,
        shortcodes_context: str = ""
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

        # Add shortcodes context for e-commerce sections
        if shortcodes_context:
            prompt += f"""AVAILABLE SHORTCODES:
{shortcodes_context}

You can reference these shortcodes in content if appropriate for dynamic product displays.
"""

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

IMAGE PROMPTS:
When providing image_prompt, avatar_prompt, or background_image_prompt fields:
- Write detailed, descriptive prompts for AI image generation
- Include style (photo, illustration, 3D render), subject, mood, colors
- Example hero: "Professional photo of diverse team collaborating in modern office, warm lighting, shallow depth of field"
- Example avatar: "Professional headshot of confident female executive, early 40s, warm smile, neutral gray background"
- Example background: "Abstract geometric gradient in blue and purple tones, subtle tech pattern"
- NEVER use URLs or references to stock photo sites

Respond only with the structured content - no explanations."""

    def _get_section_guidance(self, section_type: str) -> str:
        """Get section-specific content guidance"""
        guidance = {
            "hero": """
- Headline: 5-10 words, impactful and clear value proposition
- Subheadline: 1-2 sentences expanding on the headline
- Badge: Optional, use for announcements or key differentiators
- CTAs: Action-oriented, clear benefit
- image_prompt: Describe the ideal hero image in detail (style, subject, mood, colors)""",
            "features": """
- Section title: Clear and benefit-focused
- Each feature: Concrete benefit with real examples
- Icons: Use meaningful emojis that relate to the feature
- Descriptions: Focus on user benefits, not just features""",
            "testimonials": """
- Quotes: Authentic-sounding, specific praise
- Include concrete results or outcomes when possible
- Names: Realistic full names
- Titles: Include company name for B2B contexts
- avatar_prompt: Describe the person (professional headshot, gender, age, style)""",
            "pricing": """
- Tier names: Descriptive (Starter, Pro, Enterprise)
- Prices: Realistic for the product category
- Features: Mix of included and excluded items
- Mark one tier as popular/recommended""",
            "cta": """
- Headline: Urgency or clear value proposition
- Keep it short and action-focused
- Button text: Action verb (Get Started, Start Free Trial)
- background_image_prompt: Describe a subtle background image if appropriate""",
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

    def _process_images(self, content, section_type: str) -> None:
        """
        Process image prompts in content and generate actual images.
        Updates the content object in-place with generated image URLs.
        """
        if not self.generate_images or not self.image_generator:
            return

        # Process different content types
        content_dict = content.model_dump() if hasattr(content, 'model_dump') else content

        # Hero section images
        if hasattr(content, 'image_prompt') and content.image_prompt:
            try:
                result = self.image_generator.generate(
                    prompt=content.image_prompt,
                    size="1024x576"  # Landscape for hero
                )
                content.image_url = result.file_url
                if not content.image_alt:
                    content.image_alt = content.image_prompt[:100]
                frappe.logger().info(f"Generated hero image: {result.file_url}")
            except Exception as e:
                frappe.log_error("Hero image generation failed", str(e))

        # CTA background images
        if hasattr(content, 'background_image_prompt') and content.background_image_prompt:
            try:
                result = self.image_generator.generate(
                    prompt=content.background_image_prompt,
                    size="1920x1080"  # Wide for background
                )
                content.background_image_url = result.file_url
                frappe.logger().info(f"Generated CTA background: {result.file_url}")
            except Exception as e:
                frappe.log_error("CTA background generation failed", str(e))

        # Testimonial avatars
        if hasattr(content, 'testimonials'):
            for testimonial in content.testimonials:
                if hasattr(testimonial, 'avatar_prompt') and testimonial.avatar_prompt:
                    try:
                        result = self.image_generator.generate(
                            prompt=testimonial.avatar_prompt,
                            size="256x256"  # Square for avatar
                        )
                        testimonial.avatar_url = result.file_url
                        frappe.logger().info(f"Generated avatar: {result.file_url}")
                    except Exception as e:
                        frappe.log_error("Avatar generation failed", str(e))

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
