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
    MenuItem,
    HeaderType,
)
from builder.ai.schemas.footer_schema import (
    FooterConfig,
    FooterColumn,
    FooterType,
)

__all__ = [
    # Block schemas
    "FrappeBlock",
    "FrappeStyles",
    "BlockDataKey",
    "PageStructure",
    "SectionInfo",
    # Header schemas
    "HeaderConfig",
    "MenuItem",
    "HeaderType",
    # Footer schemas
    "FooterConfig",
    "FooterColumn",
    "FooterType",
]
