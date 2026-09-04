#//// Neoffice — added file (no upstream equivalent): prompt package exports. builder/ai/** = the
#//// Neoffice AI site generator; frappe/builder ships no such module. First commit 563d9875 2026-02-01.
# AI Prompts Module
# Creative system prompts for AI generation with full freedom

from builder.ai.prompts.system_prompts import (
    get_creative_system_prompt,
    get_page_generation_prompt,
    get_shortcodes_context,
)

__all__ = [
    "get_creative_system_prompt",
    "get_page_generation_prompt",
    "get_shortcodes_context",
]
