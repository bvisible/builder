"""
Anti-Patterns
Common mistakes to avoid in AI-generated designs.
"""

# General anti-patterns for all designs
ANTI_PATTERNS = """
## ANTI-PATTERNS TO AVOID

These are common AI generation mistakes. NEVER do these:

### LAYOUT ANTI-PATTERNS
❌ Three equal columns with identical content structure
❌ Perfect symmetry everywhere (asymmetry is more engaging)
❌ All sections with the same padding/height
❌ Centered everything (vary alignment)
❌ No visual hierarchy (everything same size/weight)

### TYPOGRAPHY ANTI-PATTERNS
❌ Lorem ipsum or placeholder text
❌ "Click Here" or "Learn More" as CTA text
❌ Headlines that don't say anything specific
❌ Body text smaller than 14px
❌ Poor contrast (light gray on white)
❌ Too many font sizes (stick to a scale)

### COLOR ANTI-PATTERNS
❌ Generic purple-to-blue gradients (overused)
❌ Using all accent colors equally (creates chaos)
❌ Pure black (#000000) for text (too harsh)
❌ Not enough contrast for accessibility
❌ Random color choices without purpose

### CONTENT ANTI-PATTERNS
❌ "Welcome to our website" as a headline
❌ "We provide solutions" type vague copy
❌ Generic stock photo descriptions
❌ Features without specific benefits
❌ CTAs without clear value proposition

### COMPONENT ANTI-PATTERNS
❌ Buttons that look like links (or vice versa)
❌ Cards without clear boundaries or purpose
❌ Forms with too many fields
❌ Images without alt text
❌ Links that don't indicate where they go

### RESPONSIVE ANTI-PATTERNS
❌ Ignoring mobile styles completely
❌ Keeping desktop font sizes on mobile
❌ Not adjusting grid columns for small screens
❌ Horizontal overflow on mobile
❌ Touch targets smaller than 44px

### SPECIFIC SECTION ANTI-PATTERNS

HERO:
❌ Just a title and button (no supporting content)
❌ Generic "hero image" of smiling people
❌ Vague value proposition
❌ Multiple CTAs with equal emphasis

FEATURES:
❌ 6+ features (cognitive overload)
❌ Features that all sound the same
❌ No icons or visual differentiation
❌ Wall of text descriptions

TESTIMONIALS:
❌ Fake-sounding quotes
❌ Missing attribution (name, company, photo)
❌ 5+ testimonials (pick the best 2-3)
❌ All testimonials saying the same thing

PRICING:
❌ More than 4 pricing tiers
❌ No clear recommended option
❌ Feature lists that are hard to compare
❌ Hidden/unclear pricing

FOOTER:
❌ Too many links (organize into categories)
❌ Missing legal links (privacy, terms)
❌ No visual hierarchy in footer
❌ Cluttered with unnecessary information
"""


# Anti-patterns by section type
SECTION_ANTI_PATTERNS = {
    "hero": [
        "Generic 'Welcome to X' headline",
        "Vague value propositions ('solutions for your needs')",
        "Multiple CTAs with equal visual weight",
        "Stock photo of people shaking hands",
        "No clear next step for the user",
    ],
    "features": [
        "More than 5-6 features listed",
        "All features look identical",
        "Generic icons that don't relate to feature",
        "Long paragraph descriptions",
        "No clear benefit stated",
    ],
    "testimonials": [
        "Fake-sounding or generic quotes",
        "Missing photos or using obvious stock photos",
        "No name/title/company attribution",
        "All testimonials with identical length",
        "More than 4 testimonials shown",
    ],
    "pricing": [
        "More than 4 pricing tiers",
        "No highlighted/recommended option",
        "Unclear what's included",
        "No annual/monthly toggle when appropriate",
        "Missing CTA buttons on each tier",
    ],
    "cta": [
        "Weak action words ('Learn More', 'Click Here')",
        "No clear value proposition",
        "Multiple competing CTAs",
        "Blends into surrounding content",
        "No sense of urgency or benefit",
    ],
    "contact": [
        "Too many form fields",
        "No alternative contact methods",
        "Missing field labels (placeholder-only)",
        "No expected response time",
        "Looks like spam will result",
    ],
    "footer": [
        "Unorganized link dump",
        "Missing privacy/terms links",
        "Too much content",
        "No visual hierarchy",
        "Outdated copyright year",
    ],
}


# JSON structure anti-patterns
JSON_ANTI_PATTERNS = [
    "Using kebab-case for CSS properties (background-color instead of backgroundColor)",
    "Missing blockId or using generic IDs (block-1, block-2)",
    "Empty or missing baseStyles",
    "Forgetting mobileStyles for responsive design",
    "Using px for everything (should mix with rem, %, vh/vw)",
    "Hardcoded colors instead of CSS variables",
    "Missing children array when element has nested content",
    "Using innerHTML for containers (should be empty or use children)",
]


def get_anti_patterns() -> str:
    """Get the full anti-patterns guidance"""
    return ANTI_PATTERNS


def get_section_anti_patterns(section_type: str) -> list:
    """Get anti-patterns for a specific section type"""
    return SECTION_ANTI_PATTERNS.get(section_type, [])


def get_json_anti_patterns() -> list:
    """Get JSON structure anti-patterns"""
    return JSON_ANTI_PATTERNS


def format_anti_patterns_for_prompt(section_type: str = None) -> str:
    """Format anti-patterns as a prompt section"""
    output = "## AVOID THESE MISTAKES\n\n"

    if section_type and section_type in SECTION_ANTI_PATTERNS:
        output += f"### {section_type.upper()} ANTI-PATTERNS\n"
        for ap in SECTION_ANTI_PATTERNS[section_type]:
            output += f"❌ {ap}\n"
        output += "\n"

    output += "### JSON STRUCTURE\n"
    for ap in JSON_ANTI_PATTERNS[:5]:
        output += f"❌ {ap}\n"

    return output


__all__ = [
    "ANTI_PATTERNS",
    "SECTION_ANTI_PATTERNS",
    "JSON_ANTI_PATTERNS",
    "get_anti_patterns",
    "get_section_anti_patterns",
    "get_json_anti_patterns",
    "format_anti_patterns_for_prompt",
]
