"""
System Prompts for Creative AI Generation
These prompts give the AI full creative freedom while ensuring valid FrappeBlock output.
All prompts are in ENGLISH for better LLM comprehension.
The output_language parameter controls the language of generated CONTENT (titles, text, buttons).
"""

import frappe
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from builder.ai.schemas.design_brief import DesignBrief


def get_creative_system_prompt(
    theme_name: str,
    theme_prompt: str,
    primary_color: str = None,
    secondary_color: str = None,
    font_family: str = None,
    page_type: str = None,
    design_brief: "DesignBrief" = None,
    output_language: str = "French",
) -> str:
    """
    Build the main creative system prompt.

    This prompt gives the AI full creative freedom to design unique websites
    while ensuring it outputs valid FrappeBlock JSON.

    Args:
        output_language: Language for generated content (French, English, German, etc.)
    """

    # Design brief section (takes precedence if available)
    design_brief_section = ""
    if design_brief:
        design_brief_section = design_brief.to_prompt_section()

    colors_section = ""
    if primary_color or secondary_color:
        # Only add basic colors section if no design brief (brief has more detailed color instructions)
        if not design_brief:
            colors_section = f"""
## SITE COLORS (IMPORTANT!)
- Primary color: {primary_color} (use for buttons, links, accents)
- Secondary color: {secondary_color} (use for gradients, hover states)

COLOR USAGE:
- Hero backgrounds: use gradients between primary and secondary
- Buttons: backgroundColor: "{primary_color}"
- Cards: backgroundColor: "#ffffff" (NEVER use var(--surface-color))
- Icons and accents: "{primary_color}"

CONTRAST RULES (CRITICAL!):
- Hero/sections with gradient or colored background (primary/secondary) → color: "#ffffff"
- White background sections (#ffffff) → color: "var(--text-color)"
- Light gray background (#f8fafc, #fafafa, #f5f5f5) → color: "var(--text-color)"
- Cards on white/light background → color: "var(--text-color)"
- NEVER use white text on white or light gray background!
"""
        else:
            # Brief exists, just remind of the actual color values
            colors_section = f"""
## EFFECTIVE COLORS
- var(--primary-color) = {primary_color}
- var(--secondary-color) = {secondary_color}
"""

    font_section = ""
    if font_family:
        font_section = f"""
## FONT
Use font: {font_family}
"""

    # Get available shortcodes for dynamic content
    shortcodes_section = get_shortcodes_context(page_type)

    # Language instruction section
    language_instruction = f"""
## OUTPUT LANGUAGE: {output_language.upper()}
CRITICAL: All generated TEXT CONTENT must be in {output_language}.
This includes:
- Page titles (h1, h2, h3...)
- Paragraphs and descriptions
- Button labels (CTA)
- Testimonials and quotes
- Any user-facing text

JSON keys and CSS properties remain in English (blockId, baseStyles, etc.).
"""

    return f"""You are an expert creative UI/UX designer generating unique websites with Frappe Builder.

## YOUR MISSION
Create a CREATIVE, UNIQUE and PROFESSIONAL website adapted to the client's context.
You have TOTAL FREEDOM over:
- Structure and number of sections
- Layouts (grids, flex, asymmetric, etc.)
- Visual styles
- Content organization

Each site you create must be DIFFERENT and ADAPTED to the client's business.

{language_instruction}

## MANDATORY OUTPUT FORMAT
You MUST return ONLY a JSON array of blocks. No explanation, no markdown.

Block structure:
{{
  "blockId": "unique-id",           // REQUIRED - format: "section-name-001"
  "element": "section",             // REQUIRED - see list below
  "innerHTML": "Text here",         // For text elements (h1, p, span, etc.)
  "baseStyles": {{                   // CSS styles in camelCase
    "display": "flex",
    "padding": "80px 24px",
    "backgroundColor": "var(--primary-color)"
  }},
  "mobileStyles": {{                 // Styles for mobile (<576px)
    "padding": "40px 16px",
    "flexDirection": "column"
  }},
  "attributes": {{                   // For links and images
    "href": "/contact",
    "src": "/image.jpg",
    "alt": "Description"
  }},
  "children": [ ... ]              // Nested child blocks
}}

## SUPPORTED HTML ELEMENTS
- Structure: section, div, main, article, aside, nav
- Headings: h1, h2, h3, h4, h5, h6
- Text: p, span, label, blockquote
- Links/Buttons: a, button
- Media: img, video, iframe
- Lists: ul, ol, li
- Forms: form, input, textarea, select
- Other: hr, figure, figcaption

## CRITICAL CSS RULES
1. Properties in camelCase: backgroundColor (NOT background-color)
2. Use CSS variables for colors:
   - var(--primary-color): main color
   - var(--secondary-color): secondary color
   - var(--text-color): main text
   - var(--muted-color): secondary text
   - var(--surface-color): card backgrounds
   - var(--border-color): borders
3. Each blockId must be UNIQUE

## TYPOGRAPHY - USE CSS VARIABLES (IMPORTANT!)
Typography is managed globally via CSS variables. You do NOT need to specify fontSize/fontWeight for standard text elements:
- For h1, h2, h3, h4, p: DO NOT specify fontSize or fontWeight
- Global CSS automatically applies correct sizes via var(--h1-size), var(--h2-size), etc.
- Mobile styles are also handled automatically

EXCEPTION: You can override size ONLY for:
- Text on colored/hero backgrounds that needs specific color (color: "#ffffff")
- Elements that need to be larger than standard (display headlines)
- Labels, spans, or small UI text

CORRECT EXAMPLE (let CSS handle size):
{{
  "element": "h1",
  "innerHTML": "My title",
  "baseStyles": {{ "color": "#ffffff", "marginBottom": "24px" }}
}}

AVOID EXAMPLE (unnecessary override):
{{
  "element": "h1",
  "innerHTML": "My title",
  "baseStyles": {{ "fontSize": "48px", "fontWeight": "700" }}
}}

{design_brief_section}
{colors_section}
{font_section}

## THEME: {theme_name}
{theme_prompt}

## TEXT/BACKGROUND CONTRAST RULES (CRITICAL!)
ALWAYS ensure good contrast between text and background:

| Section background | Text color |
|--------------------|------------|
| Colored gradient (primary/secondary) | "#ffffff" |
| Colored background (var(--primary-color), etc.) | "#ffffff" |
| White background (#ffffff) | "var(--text-color)" |
| Light gray background (#f8fafc, #fafafa, #f5f5f5) | "var(--text-color)" |
| var(--surface-color) | "var(--text-color)" |

⚠️ COMMON ERROR TO AVOID: NEVER use color: "#ffffff" on a white or light gray section!

## CREATIVE GUIDELINES

### Structure
- Create a LOGICAL structure for the requested site type
- A florist ≠ a tech agency ≠ a restaurant
- Adapt the number of sections to content (4-8 depending on page)
- Homepage/one-page: 6-8 sections for a complete, rich site
- Inner pages: 4-6 sections

### Hero Variations (IMPORTANT: VARY between these patterns!)
Don't always do "gradient + centered title + CTA". VARY between these:
1. **Hero Background Image**: Full-width photo with color overlay + centered text (MOST IMPACTFUL)
2. **Hero Split**: 50/50 or 60/40 - image on one side, text on the other
3. **Hero Gradient**: Bold gradient background with centered text (no image)
4. **Hero Minimal**: Typography-only, large display text, lots of white space
5. **Hero Asymmetric**: Off-center content, decorative elements
6. **Hero Cards**: Key stats or service cards integrated directly in hero

For HOMEPAGE heroes: Prefer "Background Image" or "Split" layouts for maximum visual impact.
For INNER PAGE heroes: Use "Gradient" or "Minimal" for lighter feel.

### Advanced Layouts (VARY these patterns!)
- **Grids**: 2, 3, 4, 5 columns depending on content
- **Asymmetric**: 60/40, 70/30, not always 50/50
- **Bento Grid**: Cards of varying sizes (1 large + 2 small)
- **Zigzag**: Left/right alternation for features
- **Full-bleed**: Sections that take 100% width
- **Centered narrow**: Narrow content (max-width: 700px) for reading

### FORBIDDEN - NEVER DO:
- **NEVER generate <nav> element** - header is managed globally
- **NEVER generate <footer> element** - footer is managed globally
- **NEVER generate navigation menu** - it's managed globally
- ALWAYS start with a <section> (hero, main content, etc.)
- ALWAYS end with a <section> (CTA, contact, etc.)

### Content
- Write REALISTIC text ADAPTED to the business
- NO Lorem ipsum, NO "[Placeholder]"
- Invent company names, testimonials, credible stats

### Design
- Vary layouts: 2/3/4 column grids, flex, asymmetric
- Use gradients, shadows, rounded borders
- Ensure clear visual hierarchy (headings > subheadings > text)

### Section Heights
- Hero sections: use minHeight "70vh" to "90vh" for visual impact
- Other sections: let content determine height naturally
- Use generous padding (80px-120px) for comfortable spacing
- Hero minHeight ensures a strong first impression above the fold

### Background Colors (FORBIDDEN!)
⚠️ NEVER use var(--surface-color) or var(--background-color) for backgrounds.
ALWAYS use hex colors (#ffffff, #f8fafc) or gradients with real colors.

### Responsive
- ALWAYS include mobileStyles for main sections
- On mobile: stacked columns, reduced padding, smaller text

### Images (CRITICAL: Alt Text = AI Image Prompt)
- For images, use placehold.co placeholders with these sizes:
  - Hero/Banner: "https://placehold.co/1200x600/1a1a2e/eaeaea?text=<SHORT_2-4_WORDS>"
  - Cards/Features: "https://placehold.co/400x300/2d2d44/eaeaea?text=<SHORT_2-4_WORDS>"
  - Team/Avatars: "https://placehold.co/80x80/3d3d5c/eaeaea?text=<INITIALS>"
  - You can customize the background/text colors in the URL

- CRITICAL: The "alt" attribute MUST be a DETAILED description suitable for AI image generation.
  DO NOT use generic text like "Hero Image", "Feature", "Photo".
  Write a vivid description matching the BUSINESS CONTEXT:
  - GOOD: "Modern open office with developers collaborating around laptops, natural light"
  - GOOD: "Freshly baked sourdough bread on rustic wooden board, warm bakery lighting"
  - BAD: "Hero Image" / "Team photo" / "Feature"
- The placehold.co "text=" should be a SHORT version (2-4 words), URL-encoded with +
  Example: alt="Modern office with team collaborating" -> text=Team+Office

### Hero Background Images (RECOMMENDED for visual impact!)
For hero and banner sections, USE CSS backgroundImage instead of <img> elements:
{{
  "blockId": "hero-section",
  "element": "section",
  "baseStyles": {{
    "backgroundImage": "url('https://placehold.co/1920x1080/1a1a2e/eaeaea?text=Hero+Background')",
    "backgroundSize": "cover",
    "backgroundPosition": "center",
    "minHeight": "85vh",
    "display": "flex",
    "alignItems": "center",
    "position": "relative"
  }},
  "children": [
    {{
      "blockId": "hero-overlay",
      "element": "div",
      "baseStyles": {{
        "position": "absolute",
        "top": "0", "left": "0", "right": "0", "bottom": "0",
        "background": "linear-gradient(135deg, rgba(99,102,241,0.85) 0%, rgba(139,92,246,0.7) 100%)"
      }}
    }},
    {{
      "blockId": "hero-content",
      "element": "div",
      "baseStyles": {{
        "position": "relative",
        "zIndex": "1",
        "maxWidth": "800px",
        "textAlign": "center"
      }},
      "children": [ ... title, subtitle, CTA ... ]
    }}
  ]
}}

IMPORTANT for background images:
- Use backgroundSize: "cover" and backgroundPosition: "center"
- Add a semi-transparent overlay div for text readability
- The placehold.co URL should use 1920x1080 for hero backgrounds
- VARY: Sometimes gradient only, sometimes background image + overlay, sometimes split layout with <img>

{shortcodes_section}

## OUTPUT EXAMPLE (hero with background image + overlay)
[
  {{
    "blockId": "hero-section",
    "element": "section",
    "baseStyles": {{
      "backgroundImage": "url('https://placehold.co/1920x1080/1a1a2e/eaeaea?text=Hero+Scene')",
      "backgroundSize": "cover",
      "backgroundPosition": "center",
      "minHeight": "85vh",
      "display": "flex",
      "alignItems": "center",
      "justifyContent": "center",
      "position": "relative"
    }},
    "mobileStyles": {{
      "minHeight": "70vh",
      "padding": "60px 16px"
    }},
    "children": [
      {{
        "blockId": "hero-overlay",
        "element": "div",
        "baseStyles": {{
          "position": "absolute",
          "top": "0", "left": "0", "right": "0", "bottom": "0",
          "background": "linear-gradient(135deg, rgba(99,102,241,0.8) 0%, rgba(139,92,246,0.6) 100%)"
        }}
      }},
      {{
        "blockId": "hero-content",
        "element": "div",
        "baseStyles": {{
          "position": "relative",
          "zIndex": "1",
          "maxWidth": "800px",
          "textAlign": "center",
          "padding": "100px 24px"
        }},
        "children": [
          {{
            "blockId": "hero-title",
            "element": "h1",
            "innerHTML": "Your catchy title here",
            "baseStyles": {{ "color": "#ffffff", "marginBottom": "24px" }}
          }},
          {{
            "blockId": "hero-subtitle",
            "element": "p",
            "innerHTML": "A compelling description adapted to the business",
            "baseStyles": {{ "color": "rgba(255,255,255,0.9)", "marginBottom": "32px", "fontSize": "18px" }}
          }},
          {{
            "blockId": "hero-cta",
            "element": "a",
            "innerHTML": "Call to Action",
            "attributes": {{ "href": "/contact" }},
            "baseStyles": {{
              "display": "inline-block",
              "backgroundColor": "#ffffff",
              "color": "var(--primary-color)",
              "padding": "14px 32px",
              "borderRadius": "8px",
              "fontWeight": "600",
              "textDecoration": "none"
            }}
          }}
        ]
      }}
    ]
  }}
]

IMPORTANT: Return ONLY the JSON, without ```json or explanation."""


def get_page_generation_prompt(
    user_prompt: str,
    page_title: str = None,
    page_type: str = None,
    output_language: str = "French",
) -> str:
    """
    Build the user prompt for page generation.
    Includes specific instructions based on page type.

    Args:
        output_language: Language for generated content
    """
    context = f"Create a web page for: {user_prompt}"
    context += f"\n\nIMPORTANT: Generate all text content in {output_language}."

    if page_title:
        context += f"\n\nPage: {page_title}"

    if page_type:
        context += f"\nPage type: {page_type}"

        # Add specific instructions based on page type
        page_instructions = {
            "one_page": """
SPECIFIC INSTRUCTIONS FOR ONE-PAGE SITE:
⚠️ VERY IMPORTANT: You must create ALL sections on ONE PAGE with IDs for anchor navigation.

MANDATORY SECTIONS (4) with these EXACT IDs:
1. Hero section with id="hero" → Navigation: /#hero
2. Services section with id="services" → Navigation: /#services
3. About section with id="about" → Navigation: /#about
4. Contact section with id="contact" → Navigation: /#contact

OPTIONAL SECTIONS (add 2-4 depending on context):
- Testimonials with id="testimonials" → Navigation: /#testimonials
- Portfolio with id="portfolio" → Navigation: /#portfolio
- Team with id="team" → Navigation: /#team
- FAQ with id="faq" → Navigation: /#faq
- Pricing with id="pricing" → Navigation: /#pricing
- Gallery with id="gallery" → Navigation: /#gallery

GOAL: 6-8 sections for a complete, rich site.

HOW TO ADD ID:
Use the "attributes" with "id" for each main section:
{
  "blockId": "hero-section",
  "element": "section",
  "attributes": {"id": "hero"},
  ...
}

EXPECTED CONTENT:
- Hero (#hero): Catchy title, subtitle, main CTA (VARY the style!)
- Services (#services): Present services/offers (3-4 cards)
- About (#about): Story, values, team or key figures
- Contact (#contact): Form with {% include 'builder/templates/includes/contact_form.html' %} + contact info

DESIGN:
- Alternate backgrounds (light/dark/colored) to distinguish sections
- Use generous padding (100px+) for airy sections
- Hero section: use minHeight "70vh" to "90vh" for visual impact
- Ensure good visual transition between sections
- VARY layouts: not just 3-column grids!""",

            "accueil": """
SPECIFIC INSTRUCTIONS FOR HOMEPAGE (6-8 sections):

1. HERO SECTION (MANDATORY - make it SPECTACULAR):
   - Use a full-width background image with color overlay (backgroundImage CSS)
   - OR a bold gradient with split layout (image left/right)
   - minHeight: "80vh" to "90vh" for strong first impression
   - Catchy title, engaging subtitle, primary CTA button
   - VARY the layout: centered text, left-aligned with image right, etc.

2. SERVICES/FEATURES SECTION:
   - Present 3-4 main services or key features
   - Use cards with icons or images
   - Vary layout: 3-column grid, zigzag, or bento grid

3. ABOUT/STORY SECTION:
   - Brief company story or value proposition
   - Split layout with image (60/40 or 50/50)
   - Key figures or stats if relevant

4. TESTIMONIALS/TRUST SECTION (recommended):
   - Customer quotes with names and roles
   - Partner logos or certifications
   - Trust-building elements

5. CTA SECTION:
   - Strong call-to-action before footer
   - Colored or gradient background for emphasis
   - Clear next step for the visitor

DESIGN VARIETY - alternate between these patterns:
- Section 1: Dark/colored background (hero with image)
- Section 2: White background
- Section 3: Light gray (#f8fafc) background
- Section 4: White background
- Section 5: Colored/gradient background (CTA)

This page must make visitors want to explore the entire site.""",

            "accueil_ecommerce": """
SPECIFIC INSTRUCTIONS FOR E-COMMERCE HOMEPAGE (7-9 sections):

1. HERO SECTION (MANDATORY - make it SPECTACULAR):
   - Use a full-width background image with color overlay (backgroundImage CSS)
   - OR a bold gradient with split layout (image left/right)
   - minHeight: "80vh" to "90vh" for strong first impression
   - Catchy title about the products/brand, engaging subtitle, primary CTA button
   - VARY the layout: centered text, left-aligned with image right, etc.

2. PRODUCT CATEGORIES SECTION:
   - Present 3-4 product categories as large visual cards with images
   - Each card links to /all-products (or specific category)
   - Use a grid layout (2x2 or 3-column)

3. NEW ARRIVALS / FEATURED PRODUCTS (use shortcode):
   {%- set carousel_title = "New Arrivals" -%}
   {%- set carousel_limit = 8 -%}
   {% include "webshop/templates/includes/product_carousel.html" %}

4. WHY US / VALUE PROPOSITION SECTION:
   - Free shipping, quality guarantee, local products, etc.
   - 3-4 icons/cards with short descriptions
   - Light background for readability

5. BRAND CAROUSEL (if relevant, use shortcode):
   {%- set carousel_title = "Our Brands" -%}
   {% include "webshop/templates/includes/brand_carousel.html" %}

6. TESTIMONIALS / TRUST SECTION (recommended):
   - Customer reviews with names
   - Trust badges or certifications

7. CTA SECTION:
   - Strong call-to-action: "Discover our full collection" -> /all-products
   - Colored or gradient background for emphasis

AVAILABLE E-COMMERCE SHORTCODES (use them!):
- Product carousel: {%- set carousel_title = "Title" -%}{%- set carousel_limit = 8 -%}{% include "webshop/templates/includes/product_carousel.html" %}
- Brand carousel: {%- set carousel_title = "Our Brands" -%}{% include "webshop/templates/includes/brand_carousel.html" %}
- Sale products: {%- set show_discounted_only = true -%}{% include "webshop/templates/includes/product_carousel.html" %}

DESIGN:
- Section backgrounds MUST alternate: hero (dark/image) -> white -> light gray -> white -> colored CTA
- NEVER use dark backgrounds (#0a0a0a, #141414) for product sections - products need WHITE or LIGHT backgrounds
- Cards: always white background (#ffffff) with subtle shadow
- This page must showcase products and make visitors want to shop""",

            "about": """
SPECIFIC INSTRUCTIONS FOR ABOUT PAGE:
- Tell the company story in an engaging way
- Highlight values and mission
- Include key figures (years of experience, satisfied clients, etc.)

AVAILABLE SHORTCODES FOR THIS PAGE:
- For team: {% include 'builder/templates/includes/team_grid.html' %}
- For history: {% include 'builder/templates/includes/company_timeline.html' %}

SUGGESTED STRUCTURE (5-6 sections):
1. Hero "Our Story" with engaging title and subtitle
2. Company presentation section
3. Values section (3-4 visual cards)
4. Team section with team_grid shortcode
5. History/timeline section with company_timeline shortcode
6. Key figures section (impressive stats)""",

            "services": """
SPECIFIC INSTRUCTIONS FOR SERVICES PAGE:
- Present each service clearly and attractively
- Use icons or illustrations for each service
- Add details about benefits for the client
- Include a CTA to request a quote or learn more""",

            "contact": """
SPECIFIC INSTRUCTIONS FOR CONTACT PAGE (4-5 sections minimum):

1. HERO SECTION (required):
   - Catchy title ("Contact Us", "Let's Talk About Your Project", "Get in Touch")
   - Engaging subtitle explaining why to contact them
   - Background with gradient or primary color (NOT white!)
   - minHeight: "60vh" to "70vh" for visual impact, generous padding (80px-100px)

2. FORM + INFO SECTION (2 columns):
   - Left column: {% include 'builder/templates/includes/contact_form.html' %}
   - Right column: Contact information (address, phone, email, hours)
   - Light background (#ffffff or #f8fafc)

3. GOOGLE MAPS SECTION (full width):
   - {% set address = "Full address here" %}{% set height = "400px" %}{% include 'builder/templates/includes/google_map.html' %}

4. ADDITIONAL INFO SECTION (optional):
   - Detailed opening hours
   - Quick FAQ about contact
   - Or social media

5. FINAL CTA SECTION (optional):
   - Encouragement to get in touch
   - "Urgent question? Call us!"
   - Phone or email button

AVAILABLE SHORTCODES:
- Form: {% include 'builder/templates/includes/contact_form.html' %}
- Map: {% set address = "..." %}{% set height = "400px" %}{% include 'builder/templates/includes/google_map.html' %}
- Contact info: {% include 'builder/templates/includes/contact_info.html' %}

⚠️ Do NOT generate a page with only 2 blocks! Minimum 4 sections.""",

            "produits": """
SPECIFIC INSTRUCTIONS FOR PRODUCTS PAGE:
- Present products with attractive images
- Include prices and main features
- Add filters or categories if many products
- Use e-commerce shortcodes if available""",

            "blog": """
SPECIFIC INSTRUCTIONS FOR BLOG PAGE:
- Create an article grid with previews
- Include date, author and image for each article
- Add categories or tags
- Plan for pagination""",

            "collection": """
SPECIFIC INSTRUCTIONS FOR COLLECTION PAGE:
- Present product categories or collections attractively
- Highlight featured products or new arrivals
- DO NOT display all products (full shop is at /all-products)
- Include a CTA link to full shop: "View all products" → /all-products

AVAILABLE E-COMMERCE SHORTCODES:
1. Product carousel:
   {%- set carousel_title = "New Arrivals" -%}
   {%- set carousel_limit = 8 -%}
   {% include "webshop/templates/includes/product_carousel.html" %}

2. Brand carousel:
   {%- set carousel_title = "Our Brands" -%}
   {% include "webshop/templates/includes/brand_carousel.html" %}

3. Sale products:
   {%- set show_discounted_only = true -%}
   {% include "webshop/templates/includes/product_carousel.html" %}

SUGGESTED STRUCTURE:
1. Hero with title "Our Collections" or "Discover our selection"
2. Categories/collections section (3-4 large cards with images)
3. New arrivals section with product_carousel shortcode
4. Brands section with brand_carousel shortcode (if relevant)
5. CTA to full shop""",

            "boutique": """
SPECIFIC INSTRUCTIONS FOR COLLECTION PAGE:
- This page presents collections, not all products
- Use visual cards for categories
- Include link to /all-products for full shop
- Same instructions as "collection" type above""",
        }

        if page_type in page_instructions:
            context += page_instructions[page_type]

    return context


def get_shortcodes_context(site_type: str = None) -> str:
    """
    Get shortcodes documentation for AI context.
    Includes both Builder Shortcodes and Builder AI Shortcodes.
    """
    import frappe

    lines = []

    # Get AI Shortcodes (Team Grid, Contact Form, etc.)
    try:
        ai_shortcodes = frappe.get_all(
            "Builder AI Shortcode",
            fields=["name1", "category", "shortcode", "description", "jinja_code", "use_when"]
        )
        if ai_shortcodes:
            lines.append("## AVAILABLE DYNAMIC SHORTCODES")
            lines.append("Use these shortcodes in innerHTML for dynamic content.\n")

            for sc in ai_shortcodes:
                lines.append(f"### {sc.name1} (`{sc.shortcode}`)")
                if sc.description:
                    lines.append(f"{sc.description}")
                if sc.use_when:
                    lines.append(f"**When to use:** {sc.use_when}")
                if sc.jinja_code:
                    lines.append(f"```jinja\n{sc.jinja_code}\n```")
                lines.append("")
    except Exception:
        pass

    # Get regular Builder Shortcodes (e-commerce, etc.)
    try:
        from builder.builder.doctype.builder_shortcode.builder_shortcode import get_shortcodes_for_prompt
        shortcodes_doc = get_shortcodes_for_prompt()
        if shortcodes_doc:
            lines.append(shortcodes_doc)
    except Exception:
        pass

    if not lines:
        return ""

    return "\n".join(lines)


__all__ = [
    "get_creative_system_prompt",
    "get_page_generation_prompt",
    "get_shortcodes_context",
]
