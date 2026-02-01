# AI Prompts Module
# System prompts, creative guidance, and anti-patterns

from builder.ai.prompts.system_prompts import (
    MAIN_SYSTEM_PROMPT,
    ANALYSIS_PROMPT,
    SECTION_GENERATION_PROMPT,
    HEADER_GENERATION_PROMPT,
    FOOTER_GENERATION_PROMPT,
)
from builder.ai.prompts.creative_prompts import (
    CREATIVE_GUIDANCE,
    STYLE_PROMPTS,
    get_style_prompt,
)
from builder.ai.prompts.anti_patterns import ANTI_PATTERNS

__all__ = [
    "MAIN_SYSTEM_PROMPT",
    "ANALYSIS_PROMPT",
    "SECTION_GENERATION_PROMPT",
    "HEADER_GENERATION_PROMPT",
    "FOOTER_GENERATION_PROMPT",
    "CREATIVE_GUIDANCE",
    "STYLE_PROMPTS",
    "get_style_prompt",
    "ANTI_PATTERNS",
]
