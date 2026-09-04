#//// Neoffice — added file (no upstream equivalent): inspiration package: capture a site or an image
#//// and feed the brief. builder/ai/** = the Neoffice AI site generator; frappe/builder ships no such
#//// module. First commit 5c48fc99 2026-02-04.
"""
Inspiration Module for Builder AI

This module allows users to capture and analyze websites or upload images
for design inspiration. The captured content is analyzed to extract:
- Dominant colors
- Layout patterns
- Design elements

This information is then used to enhance the AI design brief.
"""

from builder.ai.inspiration.screenshotter import WebsiteScreenshotter
from builder.ai.inspiration.analyzer import DesignAnalyzer
from builder.ai.inspiration.brief_enhancer import enhance_brief_with_inspirations

__all__ = [
    "WebsiteScreenshotter",
    "DesignAnalyzer",
    "enhance_brief_with_inspirations",
]
