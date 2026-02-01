# AI Prompts Module
# System prompts, creative guidance, and anti-patterns

from builder.ai.prompts.system_prompts import (
    MAIN_SYSTEM_PROMPT,
    ANALYSIS_PROMPT,
    SECTION_GENERATION_PROMPT,
    HEADER_GENERATION_PROMPT,
    FOOTER_GENERATION_PROMPT,
    get_main_prompt,
    get_analysis_prompt,
    get_section_prompt,
    get_header_prompt,
    get_footer_prompt,
)
from builder.ai.prompts.creative_prompts import (
    CREATIVE_GUIDANCE,
    STYLE_PROMPTS,
    SECTION_EXAMPLES,
    get_creative_guidance,
    get_style_prompt,
    get_combined_creative_prompt,
    get_section_examples,
)
from builder.ai.prompts.anti_patterns import (
    ANTI_PATTERNS,
    SECTION_ANTI_PATTERNS,
    JSON_ANTI_PATTERNS,
    get_anti_patterns,
    get_section_anti_patterns,
    get_json_anti_patterns,
    format_anti_patterns_for_prompt,
)

__all__ = [
    # System prompts
    "MAIN_SYSTEM_PROMPT",
    "ANALYSIS_PROMPT",
    "SECTION_GENERATION_PROMPT",
    "HEADER_GENERATION_PROMPT",
    "FOOTER_GENERATION_PROMPT",
    "get_main_prompt",
    "get_analysis_prompt",
    "get_section_prompt",
    "get_header_prompt",
    "get_footer_prompt",
    # Creative prompts
    "CREATIVE_GUIDANCE",
    "STYLE_PROMPTS",
    "SECTION_EXAMPLES",
    "get_creative_guidance",
    "get_style_prompt",
    "get_combined_creative_prompt",
    "get_section_examples",
    # Anti-patterns
    "ANTI_PATTERNS",
    "SECTION_ANTI_PATTERNS",
    "JSON_ANTI_PATTERNS",
    "get_anti_patterns",
    "get_section_anti_patterns",
    "get_json_anti_patterns",
    "format_anti_patterns_for_prompt",
]
