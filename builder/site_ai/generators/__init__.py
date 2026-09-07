# //// Neoffice — added file (no upstream equivalent): generator package exports. builder/site_ai/** = the
# //// Neoffice AI site generator; frappe/builder ships no such module. First commit 563d9875 2026-02-01.
# AI Generators Module
# Creative page generator with full AI freedom

from builder.site_ai.generators.page_generator import PageGenerator, generate_page
from builder.site_ai.generators.brief_generator import BriefGenerator, get_default_brief

__all__ = [
    "PageGenerator",
    "generate_page",
    "BriefGenerator",
    "get_default_brief",
]
