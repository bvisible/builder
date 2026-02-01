# Claude Code Guide for Frappe Builder

This document provides guidance for AI assistants working with the Frappe Builder codebase.

## Project Overview

Frappe Builder is a visual website builder for the Frappe framework. It allows users to create pages using a drag-and-drop interface with blocks stored as JSON.

### Key Directories

```
builder/
├── builder/                    # Main Python module
│   ├── api.py                  # API endpoints (whitelist functions)
│   ├── ai/                     # AI generation module (NEW)
│   │   ├── generators/         # Page/section generators
│   │   ├── templates/          # Block templates
│   │   ├── schemas/            # Pydantic models
│   │   ├── providers/          # OpenAI/Ollama providers
│   │   ├── design_system/      # Themes and tokens
│   │   ├── validators/         # Block validation
│   │   └── prompts/            # AI prompts
│   ├── builder/
│   │   └── doctype/            # Frappe DocTypes
│   └── tests/                  # Unit tests
├── frontend/                   # Vue.js frontend
│   └── src/
│       ├── components/
│       └── pages/
└── package.json
```

## Frappe Builder Block Format

Blocks are stored as JSON with this structure:

```json
{
  "blockId": "unique-id",
  "element": "section",
  "innerHTML": "Text content",
  "baseStyles": {
    "display": "flex",
    "padding": "20px",
    "backgroundColor": "#fff"
  },
  "mobileStyles": {
    "padding": "10px"
  },
  "attributes": {
    "href": "/link",
    "src": "/image.jpg"
  },
  "children": []
}
```

### Important Rules

1. **CSS properties are camelCase** - Use `backgroundColor` not `background-color`
2. **blockId must be unique** - Each block needs a unique ID
3. **Use CSS variables for theming**:
   - `var(--primary-color)`
   - `var(--surface-color)`
   - `var(--text-color)`
   - `var(--muted-color)`
   - `var(--border-color)`
4. **Responsive styles** - `baseStyles` for desktop, `mobileStyles` for mobile

## AI Generation Module

The `builder/ai/` module provides AI-powered page generation.

### Architecture

```
User Prompt
    ↓
PASS 1: Analysis (determine structure)
    ↓
PASS 2: Context (load theme, tokens)
    ↓
PASS 3: Generation (templates + AI content)
    ↓
PASS 4: Validation (fix issues)
    ↓
Frappe Builder Blocks
```

### Key Components

| Component | Purpose |
|-----------|---------|
| `PageGenerator` | Main orchestrator |
| `SectionGenerator` | Generate individual sections |
| `HeaderGenerator` | Generate headers from config |
| `FooterGenerator` | Generate footers from config |
| `BlockValidator` | Validate block structure |
| `AutoFixer` | Fix common issues |

### Templates vs AI

The system separates concerns:
- **Templates** provide structure (HTML/CSS layout)
- **AI** generates content (text, descriptions)

This ensures consistent output while allowing creative content.

### Content Schemas

AI generates structured content using Pydantic models:

```python
class HeroContent(BaseModel):
    headline: str
    subheadline: str
    primary_cta_text: str = "Get Started"
```

### Themes

6 built-in themes:
- `modern` - Clean, professional
- `neobrutalist` - Bold, high contrast
- `glassmorphism` - Frosted glass effects
- `minimal` - Ultra-clean
- `corporate` - Professional
- `creative` - Artistic

### Site Types

- `single_page` - One-page site with anchors
- `multi_page` - Standard multi-page site
- `ecommerce` - Online store
- `saas` - Software product
- `blog` - Blog/content site
- `portfolio` - Portfolio/showcase

## Common Tasks

### Adding a New API Endpoint

```python
# In builder/api.py
@frappe.whitelist()
def my_endpoint(param: str):
    """Description"""
    # Implementation
    return result
```

### Adding a New Section Type

1. Add content schema in `ai/schemas/block_schema.py`
2. Add template in `ai/templates/sections.py`
3. Add builder function in same file
4. Register in `SECTION_CONTENT_SCHEMAS`

### Adding a New Theme

1. Create `ai/design_system/themes/mytheme.py`
2. Define `MYTHEME_THEME` dict with colors, styles, prompt
3. Register in `themes/__init__.py`

## Testing

```bash
# Run AI module tests
python -m pytest builder/tests/test_ai_*.py -v

# Run specific test
python -m pytest builder/tests/test_ai_validators.py::TestAutoFixer -v
```

## Code Style

- Python: Follow Frappe conventions
- Use type hints for function signatures
- Document public functions with docstrings
- Keep functions focused and small
- Use constants from `ai/utils.py` (don't duplicate)

## Providers

### OpenAI
- Requires API key in site config or AI Settings
- Default model: `gpt-4o`

### Ollama
- Self-hosted, requires Ollama running locally
- Default URL: `http://localhost:11434`
- Recommended models: `llama3.1:8b`, `mistral`

## Useful Commands

```bash
# Bench commands
bench --site [site] console  # Python console
bench --site [site] execute builder.api.generate_page_blocks --kwargs '{"prompt": "..."}'

# Frontend
cd apps/builder && yarn dev
```

## Recent Changes

### AI Module (v1.0.0)
- Multi-pass generation pipeline
- Template-based section generation
- 6 creative themes
- OpenAI and Ollama support
- Structured output with Pydantic
- Block validation and auto-fixing
- Comprehensive test suite
