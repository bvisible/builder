# AI Schemas Module
# Pydantic schemas for structured AI output

from builder.ai.schemas.block_schema import (
    FrappeBlock,
    FrappeStyles,
    BlockDataKey,
    PageStructure,
    SectionInfo,
)
from builder.ai.schemas.header_schema import (
    HeaderConfig,
    NavItem,
    HeaderLayout,
    LogoType,
    SITE_TYPE_HEADER_DEFAULTS,
    HEADER_TYPE_DESCRIPTIONS,
)
from builder.ai.schemas.footer_schema import (
    FooterConfig,
    FooterColumn,
    FooterType,
)

# Backwards compatibility alias
MenuItem = NavItem
HeaderType = HeaderLayout

__all__ = [
    # Block schemas
    "FrappeBlock",
    "FrappeStyles",
    "BlockDataKey",
    "PageStructure",
    "SectionInfo",
    # Header schemas
    "HeaderConfig",
    "NavItem",
    "MenuItem",  # Alias for backwards compatibility
    "HeaderLayout",
    "HeaderType",  # Alias for backwards compatibility
    "LogoType",
    "SITE_TYPE_HEADER_DEFAULTS",
    "HEADER_TYPE_DESCRIPTIONS",
    # Footer schemas
    "FooterConfig",
    "FooterColumn",
    "FooterType",
]
