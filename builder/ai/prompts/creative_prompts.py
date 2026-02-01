"""
Creative Prompts
Guidance for generating creative, non-generic designs.
"""

# General creative guidance added to all generation prompts
CREATIVE_GUIDANCE = """
## CREATIVE DESIGN PRINCIPLES

To create unique, engaging designs (not generic templates), follow these principles:

### 1. VISUAL HIERARCHY
- One dominant element per section (not everything equal)
- Size contrast: some elements should be noticeably larger
- Color contrast: use accent colors strategically, not everywhere
- Whitespace: empty space is a design element

### 2. LAYOUT VARIETY
- Avoid perfect symmetry (60/40, 70/30 splits are more interesting)
- Break the grid occasionally for visual interest
- Use overlapping elements for depth
- Vary section heights and padding

### 3. TYPOGRAPHY
- Headlines should make a statement (large, bold)
- Create clear distinction between heading levels
- Use line-height and letter-spacing intentionally
- Mix weights (not just regular and bold)

### 4. CONTENT REALISM
- Never use "Lorem ipsum" - write realistic content
- Use specific numbers and data
- Include realistic CTAs (not just "Click Here")
- Imagery descriptions should be specific

### 5. MICRO-INTERACTIONS
- All interactive elements need hover states
- Buttons should have visual feedback
- Links should be clearly identifiable
- Forms should feel responsive

### 6. INSPIRATION SOURCES (think beyond web)
- Magazine editorial layouts
- Architecture and interior design
- Film photography composition
- Modern art and typography

REMEMBER: Generic = forgettable. Each section should have character.
"""


# Style-specific prompts
STYLE_PROMPTS = {
    "hero_centered": """
Create a centered hero section that commands attention:
- Large, impactful headline (48-72px)
- Supporting subheadline that adds context
- Clear CTA button(s) with visual hierarchy
- Consider: background treatment (gradient, image, pattern)
- Mobile: Stack elements, reduce headline size
""",

    "hero_split": """
Create a split hero with content and visual:
- 50/50 or 60/40 split (not equal thirds)
- Content side: headline, description, CTA
- Visual side: image, illustration, or graphic
- Strong alignment between text baseline and image
- Mobile: Stack with image above or below
""",

    "features_grid": """
Create a features section showcasing capabilities:
- Section title that frames the features
- 3-4 feature cards (not more)
- Each card: icon/visual, title, brief description
- Cards should be scannable (not text-heavy)
- Consider: subtle hover effects on cards
""",

    "features_alternating": """
Create alternating feature rows:
- Each row: image on one side, content on other
- Alternate image position (left, right, left)
- Large feature images with context
- Content: overline, headline, description, optional link
- Creates visual rhythm down the page
""",

    "testimonials": """
Create a testimonials section with social proof:
- Feature 1-3 testimonials (quality over quantity)
- Include: quote, name, title, company, photo
- Photos should be real (or realistic placeholder)
- Consider: star ratings, company logos
- Design for credibility and trust
""",

    "pricing": """
Create a pricing section:
- Clear pricing tiers (2-4 options)
- Highlight recommended/popular plan
- Feature comparison that's scannable
- Strong CTAs for each tier
- Consider: annual vs monthly toggle
""",

    "cta": """
Create a call-to-action section:
- Single, focused message
- Compelling headline that creates urgency
- Clear value proposition
- Prominent button(s)
- Can use contrasting background color
""",

    "contact": """
Create a contact section:
- Multiple contact methods (form, email, phone)
- Form: minimal fields, clear labels
- Include expected response time
- Consider: map, office hours, social links
- Make it easy to reach out
""",

    "footer": """
Create a footer that completes the page:
- Organized link sections by category
- Company info and/or newsletter signup
- Social media links
- Legal links (privacy, terms)
- Copyright with current year
""",
}


def get_creative_guidance() -> str:
    """Get the general creative guidance"""
    return CREATIVE_GUIDANCE


def get_style_prompt(style: str) -> str:
    """Get style-specific guidance"""
    return STYLE_PROMPTS.get(style, "")


def get_combined_creative_prompt(style: str = None) -> str:
    """Get combined creative guidance with optional style-specific prompt"""
    prompt = CREATIVE_GUIDANCE
    if style and style in STYLE_PROMPTS:
        prompt += f"\n\n## SPECIFIC GUIDANCE FOR {style.upper()}\n"
        prompt += STYLE_PROMPTS[style]
    return prompt


# Section-specific prompts with examples
SECTION_EXAMPLES = {
    "hero": {
        "good_example": """
A hero that works:
- Headline: "Ship faster with AI-powered development" (specific, benefit-focused)
- Subheadline: "Build and deploy web applications 10x faster..." (quantified value)
- CTA: "Start Free Trial" + "Watch Demo" (primary + secondary)
- Visual: Product screenshot or abstract representation
""",
        "bad_example": """
Avoid this:
- Headline: "Welcome to Our Website" (generic, says nothing)
- Subheadline: "We provide solutions for your needs" (vague)
- CTA: "Learn More" (weak, unclear action)
- Visual: Generic stock photo of people in office
"""
    },
    "features": {
        "good_example": """
Features that work:
- Icon that represents the feature visually
- Title: "Real-time Collaboration" (specific capability)
- Description: "Edit documents with your team simultaneously..." (concrete)
- 3-4 features total (focused, not overwhelming)
""",
        "bad_example": """
Avoid this:
- Generic icons that don't relate to feature
- Title: "Feature 1" (meaningless)
- Description: "This is a great feature that helps you..." (says nothing)
- 8+ features (overwhelming, none memorable)
"""
    },
}


def get_section_examples(section_type: str) -> dict:
    """Get good and bad examples for a section type"""
    return SECTION_EXAMPLES.get(section_type, {})


__all__ = [
    "CREATIVE_GUIDANCE",
    "STYLE_PROMPTS",
    "SECTION_EXAMPLES",
    "get_creative_guidance",
    "get_style_prompt",
    "get_combined_creative_prompt",
    "get_section_examples",
]
