# Builder AI Module
# Provides AI-powered generation for Frappe Builder pages and components
#
# This module implements a multi-pass AI generation pipeline:
# 1. Analysis: Parse user prompt and determine page structure
# 2. Context: Load theme and design tokens
# 3. Generation: Generate header, sections, footer using templates
# 4. Validation: Validate and auto-fix all blocks

from builder.ai.config import AIConfig, get_ai_settings
from builder.ai.providers import get_provider
from builder.ai.generators.page_generator import PageGenerator, generate_page
from builder.ai.generators.section_generator import SectionGenerator
from builder.ai.generators.header_generator import HeaderGenerator
from builder.ai.generators.footer_generator import FooterGenerator
from builder.ai.validators import BlockValidator, AutoFixer, validate_block
from builder.ai.design_system import get_theme, list_themes, DESIGN_TOKENS

__version__ = "1.0.0"

__all__ = [
    # Config
    "AIConfig",
    "get_ai_settings",
    # Providers
    "get_provider",
    # Generators
    "PageGenerator",
    "generate_page",
    "SectionGenerator",
    "HeaderGenerator",
    "FooterGenerator",
    # Validators
    "BlockValidator",
    "AutoFixer",
    "validate_block",
    # Design System
    "get_theme",
    "list_themes",
    "DESIGN_TOKENS",
]
