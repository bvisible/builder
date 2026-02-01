"""
Block Validator
Validates generated blocks against Frappe Builder requirements.
"""

import re
import uuid

from builder.ai.utils import KEBAB_TO_CAMEL, VALID_ELEMENTS


class ValidationError(Exception):
    """Raised when block validation fails"""
    def __init__(self, message: str, field: str = None, block_id: str = None):
        self.message = message
        self.field = field
        self.block_id = block_id
        super().__init__(self.message)

    def __str__(self):
        parts = [self.message]
        if self.field:
            parts.append(f"Field: {self.field}")
        if self.block_id:
            parts.append(f"Block: {self.block_id}")
        return " | ".join(parts)


class ValidationWarning:
    """Non-critical validation issue"""
    def __init__(self, message: str, field: str = None, suggestion: str = None):
        self.message = message
        self.field = field
        self.suggestion = suggestion


class BlockValidator:
    """
    Validates Frappe Builder blocks for correctness and best practices.

    Uses shared constants from builder.ai.utils:
    - VALID_ELEMENTS: Valid HTML elements
    - KEBAB_TO_CAMEL: CSS property name mappings
    """

    def __init__(self, strict: bool = False):
        """
        Initialize validator.

        Args:
            strict: If True, warnings become errors
        """
        self.strict = strict
        self.errors: list[ValidationError] = []
        self.warnings: list[ValidationWarning] = []
        self._seen_block_ids: set[str] = set()

    def validate(self, block: dict, parent_id: str = None) -> bool:
        """
        Validate a block and its children.

        Args:
            block: Block dictionary to validate
            parent_id: Parent block ID for context

        Returns:
            bool: True if valid (no errors)

        Raises:
            ValidationError: If validation fails and strict mode
        """
        self.errors = []
        self.warnings = []
        self._seen_block_ids = set()

        self._validate_block(block, parent_id)

        if self.errors:
            if self.strict:
                raise self.errors[0]
            return False

        return True

    def _validate_block(self, block: dict, parent_id: str = None):
        """Recursively validate a block"""
        if not isinstance(block, dict):
            self.errors.append(ValidationError(
                "Block must be a dictionary",
                block_id=parent_id
            ))
            return

        block_id = block.get("blockId", "unknown")

        # Validate required fields
        self._validate_block_id(block)
        self._validate_element(block)
        self._validate_styles(block)
        self._validate_attributes(block)
        self._validate_content(block)

        # Validate children recursively
        children = block.get("children", [])
        if children:
            if not isinstance(children, list):
                self.errors.append(ValidationError(
                    "children must be an array",
                    field="children",
                    block_id=block_id
                ))
            else:
                for child in children:
                    self._validate_block(child, block_id)

    def _validate_block_id(self, block: dict):
        """Validate blockId field"""
        block_id = block.get("blockId")

        if not block_id:
            self.warnings.append(ValidationWarning(
                "Missing blockId - will be auto-generated",
                field="blockId",
                suggestion=f"block-{uuid.uuid4().hex[:8]}"
            ))
            return

        if not isinstance(block_id, str):
            self.errors.append(ValidationError(
                "blockId must be a string",
                field="blockId"
            ))
            return

        # Check for uniqueness
        if block_id in self._seen_block_ids:
            self.errors.append(ValidationError(
                f"Duplicate blockId: {block_id}",
                field="blockId",
                block_id=block_id
            ))
        else:
            self._seen_block_ids.add(block_id)

        # Check format (should be descriptive)
        if re.match(r"^block-\d+$", block_id):
            self.warnings.append(ValidationWarning(
                "Generic blockId - consider using descriptive name",
                field="blockId",
                suggestion="hero-title-001 or cta-button-main"
            ))

    def _validate_element(self, block: dict):
        """Validate element field"""
        block_id = block.get("blockId", "unknown")
        element = block.get("element")

        if not element:
            self.warnings.append(ValidationWarning(
                "Missing element - defaulting to 'div'",
                field="element"
            ))
            return

        if element not in VALID_ELEMENTS:
            self.errors.append(ValidationError(
                f"Invalid element: {element}",
                field="element",
                block_id=block_id
            ))

    def _validate_styles(self, block: dict):
        """Validate style objects"""
        block_id = block.get("blockId", "unknown")

        for style_key in ["baseStyles", "mobileStyles", "tabletStyles"]:
            styles = block.get(style_key)
            if styles:
                self._validate_style_object(styles, style_key, block_id)

    def _validate_style_object(self, styles: dict, style_key: str, block_id: str):
        """Validate a single style object"""
        if not isinstance(styles, dict):
            self.errors.append(ValidationError(
                f"{style_key} must be an object",
                field=style_key,
                block_id=block_id
            ))
            return

        for prop, value in styles.items():
            # Check for kebab-case (common mistake)
            if "-" in prop:
                camel = KEBAB_TO_CAMEL.get(prop)
                if camel:
                    self.warnings.append(ValidationWarning(
                        f"Use camelCase: '{prop}' should be '{camel}'",
                        field=f"{style_key}.{prop}",
                        suggestion=camel
                    ))
                else:
                    self.warnings.append(ValidationWarning(
                        f"Property '{prop}' contains hyphen - use camelCase",
                        field=f"{style_key}.{prop}"
                    ))

            # Check value is string
            if value is not None and not isinstance(value, str):
                self.warnings.append(ValidationWarning(
                    f"Style value should be string: {prop}={value}",
                    field=f"{style_key}.{prop}",
                    suggestion=str(value)
                ))

    def _validate_attributes(self, block: dict):
        """Validate attributes object"""
        block_id = block.get("blockId", "unknown")
        element = block.get("element", "div")
        attributes = block.get("attributes")

        if not attributes:
            # Check if element requires attributes
            if element == "img" and not attributes:
                self.warnings.append(ValidationWarning(
                    "img element should have src attribute",
                    field="attributes",
                    suggestion='{"src": "/path/to/image.jpg", "alt": "description"}'
                ))
            if element == "a" and not attributes:
                self.warnings.append(ValidationWarning(
                    "a element should have href attribute",
                    field="attributes",
                    suggestion='{"href": "/page"}'
                ))
            return

        if not isinstance(attributes, dict):
            self.errors.append(ValidationError(
                "attributes must be an object",
                field="attributes",
                block_id=block_id
            ))
            return

        # Check for required attributes
        if element == "img":
            if "src" not in attributes:
                self.warnings.append(ValidationWarning(
                    "img missing src attribute",
                    field="attributes.src"
                ))
            if "alt" not in attributes:
                self.warnings.append(ValidationWarning(
                    "img missing alt attribute (accessibility)",
                    field="attributes.alt"
                ))

        if element == "a" and "href" not in attributes:
            self.warnings.append(ValidationWarning(
                "a element missing href attribute",
                field="attributes.href"
            ))

    def _validate_content(self, block: dict):
        """Validate content fields (innerHTML, innerText)"""
        block_id = block.get("blockId", "unknown")
        element = block.get("element", "div")
        inner_html = block.get("innerHTML")
        inner_text = block.get("innerText")
        children = block.get("children", [])

        # Check for content on container elements
        if element in {"div", "section", "article", "header", "footer", "nav", "main"}:
            if inner_html and children:
                self.warnings.append(ValidationWarning(
                    f"Container '{element}' has both innerHTML and children - children take precedence",
                    field="innerHTML",
                    block_id=block_id
                ))

        # Check for Lorem ipsum
        for content in [inner_html, inner_text]:
            if content and isinstance(content, str):
                if "lorem ipsum" in content.lower():
                    self.warnings.append(ValidationWarning(
                        "Placeholder text detected - use realistic content",
                        suggestion="Replace Lorem ipsum with actual content"
                    ))

    def get_report(self) -> dict:
        """Get validation report"""
        return {
            "valid": len(self.errors) == 0,
            "errors": [
                {
                    "message": e.message,
                    "field": e.field,
                    "block_id": e.block_id
                }
                for e in self.errors
            ],
            "warnings": [
                {
                    "message": w.message,
                    "field": w.field,
                    "suggestion": w.suggestion
                }
                for w in self.warnings
            ],
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


def validate_block(block: dict, strict: bool = False) -> tuple[bool, dict]:
    """
    Convenience function to validate a block.

    Args:
        block: Block dictionary to validate
        strict: If True, raise on errors

    Returns:
        tuple: (is_valid, report_dict)
    """
    validator = BlockValidator(strict=strict)
    is_valid = validator.validate(block)
    return is_valid, validator.get_report()


__all__ = [
    "BlockValidator",
    "ValidationError",
    "ValidationWarning",
    "validate_block",
]
