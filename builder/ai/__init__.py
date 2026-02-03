# Builder AI Module
# Provides AI-powered creative generation for Frappe Builder pages
#
# This module implements direct LLM generation with full creative freedom.
# The AI generates unique, context-adapted websites while respecting
# the FrappeBlock JSON format.

from builder.ai.config import AIConfig, get_ai_settings
from builder.ai.providers import get_provider
from builder.ai.generators.page_generator import PageGenerator, generate_page
from builder.ai.validators import BlockValidator
from builder.ai.design_system import get_theme, list_themes, DESIGN_TOKENS

__version__ = "2.0.0"

__all__ = [
    # Config
    "AIConfig",
    "get_ai_settings",
    # Providers
    "get_provider",
    # Generators
    "PageGenerator",
    "generate_page",
    # Validators
    "BlockValidator",
    # Design System
    "get_theme",
    "list_themes",
    "DESIGN_TOKENS",
]
