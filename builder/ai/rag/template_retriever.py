"""
Template Retriever
Simple RAG implementation for retrieving similar template examples.
"""

import json
from typing import Optional
import frappe


class TemplateRetriever:
    """
    Retrieves relevant template examples for AI context.
    Uses Frappe's existing block templates and components.
    """

    def __init__(self):
        self._template_cache: dict = {}
        self._component_cache: dict = {}

    def get_similar_templates(
        self,
        query: str,
        category: str = None,
        limit: int = 3
    ) -> list[dict]:
        """
        Get block templates similar to the query.

        Args:
            query: Search query (e.g., "hero section", "pricing table")
            category: Optional category filter
            limit: Maximum number of results

        Returns:
            List of template examples with their blocks
        """
        templates = self._get_all_templates()

        # Simple keyword matching (can be enhanced with embeddings)
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored = []
        for template in templates:
            name = template.get("template_name", "").lower()
            cat = template.get("category", "").lower()

            # Calculate simple relevance score
            score = 0
            name_words = set(name.split("_"))

            # Exact category match
            if category and cat == category.lower():
                score += 10

            # Word overlap
            score += len(query_words & name_words) * 5

            # Partial match
            if query_lower in name:
                score += 3

            # Category relevance
            if query_lower in cat:
                score += 2

            if score > 0:
                scored.append((score, template))

        # Sort by score and return top results
        scored.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in scored[:limit]]

    def get_components_for_context(
        self,
        section_type: str,
        limit: int = 2
    ) -> list[dict]:
        """
        Get component examples for a specific section type.

        Args:
            section_type: Type of section (hero, features, etc.)
            limit: Maximum components to return

        Returns:
            List of component examples
        """
        components = self._get_all_components()

        # Filter by section type keywords
        type_keywords = {
            "hero": ["hero", "banner", "header", "landing"],
            "features": ["feature", "benefit", "service", "capability"],
            "testimonials": ["testimonial", "review", "quote", "customer"],
            "pricing": ["pricing", "price", "plan", "tier"],
            "cta": ["cta", "action", "signup", "subscribe"],
            "contact": ["contact", "form", "email", "message"],
            "footer": ["footer", "bottom"],
            "header": ["header", "nav", "navigation", "menu"],
        }

        keywords = type_keywords.get(section_type, [section_type])

        matched = []
        for comp in components:
            name = comp.get("component_name", "").lower()
            if any(kw in name for kw in keywords):
                matched.append(comp)

        return matched[:limit]

    def get_template_by_name(self, name: str) -> Optional[dict]:
        """Get a specific template by name"""
        templates = self._get_all_templates()
        for t in templates:
            if t.get("template_name") == name or t.get("name") == name:
                return t
        return None

    def get_examples_for_prompt(
        self,
        section_type: str,
        max_examples: int = 2
    ) -> str:
        """
        Get formatted examples for injection into prompts.

        Args:
            section_type: Type of section to get examples for
            max_examples: Maximum number of examples

        Returns:
            Formatted string with JSON examples
        """
        templates = self.get_similar_templates(section_type, limit=max_examples)

        if not templates:
            return ""

        output = "## REFERENCE EXAMPLES\n\n"
        for i, template in enumerate(templates, 1):
            block = template.get("block", "{}")
            if isinstance(block, str):
                try:
                    block = json.loads(block)
                except:
                    continue

            output += f"### Example {i}: {template.get('template_name', 'Template')}\n"
            output += "```json\n"
            output += json.dumps(block, indent=2)[:1000]  # Limit size
            output += "\n```\n\n"

        return output

    def _get_all_templates(self) -> list[dict]:
        """Get all block templates from database"""
        if self._template_cache:
            return list(self._template_cache.values())

        try:
            templates = frappe.get_all(
                "Block Template",
                fields=["name", "template_name", "category", "block", "preview"],
                limit_page_length=0
            )
            for t in templates:
                self._template_cache[t["name"]] = t
            return templates
        except Exception:
            return []

    def _get_all_components(self) -> list[dict]:
        """Get all builder components from database"""
        if self._component_cache:
            return list(self._component_cache.values())

        try:
            components = frappe.get_all(
                "Builder Component",
                fields=["name", "component_name", "block", "component_id"],
                limit_page_length=0
            )
            for c in components:
                self._component_cache[c["name"]] = c
            return components
        except Exception:
            return []

    def clear_cache(self):
        """Clear the template and component cache"""
        self._template_cache = {}
        self._component_cache = {}


# Global instance for convenience
_retriever: Optional[TemplateRetriever] = None


def get_retriever() -> TemplateRetriever:
    """Get the global template retriever instance"""
    global _retriever
    if _retriever is None:
        _retriever = TemplateRetriever()
    return _retriever


def get_examples_for_section(section_type: str, max_examples: int = 2) -> str:
    """Convenience function to get examples for a section type"""
    return get_retriever().get_examples_for_prompt(section_type, max_examples)


__all__ = [
    "TemplateRetriever",
    "get_retriever",
    "get_examples_for_section",
]
