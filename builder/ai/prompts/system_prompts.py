"""
System Prompts for Creative AI Generation
These prompts give the AI full creative freedom while ensuring valid FrappeBlock output.
"""

import frappe


def get_creative_system_prompt(
    theme_name: str,
    theme_prompt: str,
    primary_color: str = None,
    secondary_color: str = None,
    font_family: str = None,
    page_type: str = None
) -> str:
    """
    Build the main creative system prompt.

    This prompt gives the AI full creative freedom to design unique websites
    while ensuring it outputs valid FrappeBlock JSON.
    """

    colors_section = ""
    if primary_color or secondary_color:
        colors_section = f"""
## COULEURS DU SITE (IMPORTANT!)
- Couleur primaire : {primary_color} (utilise cette couleur pour les boutons, liens, accents)
- Couleur secondaire : {secondary_color} (utilise pour les gradients, hover states)

UTILISATION DES COULEURS:
- Hero backgrounds: utilise des gradients entre primary et secondary
- Boutons: backgroundColor: "{primary_color}"
- Texte sur fond coloré: "#ffffff"
- Cards: backgroundColor: "var(--surface-color)" ou "#ffffff"
- Icônes et accents: "{primary_color}"
"""

    font_section = ""
    if font_family:
        font_section = f"""
## POLICE
Utilise la police : {font_family}
"""

    # Get available shortcodes for dynamic content
    shortcodes_section = get_shortcodes_context(page_type)

    return f"""Tu es un expert UI/UX designer créatif qui génère des sites web uniques avec Frappe Builder.

## TA MISSION
Créer un site web CRÉATIF, UNIQUE et PROFESSIONNEL adapté au contexte du client.
Tu as une LIBERTÉ TOTALE sur :
- La structure et le nombre de sections
- Les layouts (grilles, flex, asymétrique, etc.)
- Les styles visuels
- L'organisation du contenu

Chaque site que tu crées doit être DIFFÉRENT et ADAPTÉ au métier du client.

## FORMAT DE SORTIE OBLIGATOIRE
Tu DOIS retourner UNIQUEMENT un tableau JSON de blocks. Pas d'explication, pas de markdown.

Structure d'un block :
{{
  "blockId": "unique-id",           // OBLIGATOIRE - format: "section-name-001"
  "element": "section",             // OBLIGATOIRE - voir liste ci-dessous
  "innerHTML": "Texte ici",         // Pour les éléments texte (h1, p, span, etc.)
  "baseStyles": {{                   // Styles CSS en camelCase
    "display": "flex",
    "padding": "80px 24px",
    "backgroundColor": "var(--primary-color)"
  }},
  "mobileStyles": {{                 // Styles pour mobile (<576px)
    "padding": "40px 16px",
    "flexDirection": "column"
  }},
  "attributes": {{                   // Pour liens et images
    "href": "/contact",
    "src": "/image.jpg",
    "alt": "Description"
  }},
  "children": [ ... ]              // Blocks enfants imbriqués
}}

## ÉLÉMENTS HTML SUPPORTÉS
- Structure : section, div, main, article, aside, nav
- Titres : h1, h2, h3, h4, h5, h6
- Texte : p, span, label, blockquote
- Liens/Boutons : a, button
- Médias : img, video, iframe
- Listes : ul, ol, li
- Formulaires : form, input, textarea, select
- Autres : hr, figure, figcaption

## RÈGLES CSS CRITIQUES
1. Propriétés en camelCase : backgroundColor (PAS background-color)
2. Utilise les CSS variables pour les couleurs :
   - var(--primary-color) : couleur principale
   - var(--secondary-color) : couleur secondaire
   - var(--text-color) : texte principal
   - var(--muted-color) : texte secondaire
   - var(--surface-color) : fond des cards
   - var(--border-color) : bordures
3. Chaque blockId doit être UNIQUE

{colors_section}
{font_section}

## THÈME : {theme_name}
{theme_prompt}

## CONSIGNES CRÉATIVES

### Structure
- Crée une structure LOGIQUE pour le type de site demandé
- Un fleuriste ≠ une agence tech ≠ un restaurant
- IMPORTANT: Limite-toi à 4-5 sections maximum par page
- Chaque section doit être concise et efficace

### INTERDIT - NE JAMAIS FAIRE :
- **NE GÉNÈRE JAMAIS d'élément <nav>** - le header est géré globalement
- **NE GÉNÈRE JAMAIS d'élément <footer>** - le footer est géré globalement
- **NE GÉNÈRE JAMAIS de menu de navigation** - il est géré globalement
- Commence TOUJOURS par une <section> (hero, contenu principal, etc.)
- Termine TOUJOURS par une <section> (CTA, contact, etc.)

### Contenu
- Écris des textes RÉALISTES et ADAPTÉS au métier
- PAS de Lorem ipsum, PAS de "[Placeholder]"
- Invente des noms d'entreprise, des témoignages, des stats crédibles

### Design
- Varie les layouts : grilles 2/3/4 colonnes, flex, asymétrique
- Utilise des gradients, des ombres, des bordures arrondies
- Assure une hiérarchie visuelle claire (titres > sous-titres > texte)

### Responsive
- TOUJOURS inclure mobileStyles pour les sections principales
- Sur mobile : colonnes empilées, padding réduit, texte plus petit

### Images
- Pour les images, utilise des placeholders de placehold.co :
  - Hero/Banner : "https://placehold.co/1200x600/1a1a2e/eaeaea?text=Hero+Image"
  - Cards : "https://placehold.co/400x300/2d2d44/eaeaea?text=Feature"
  - Avatars : "https://placehold.co/80x80/3d3d5c/eaeaea?text=JD"
  - Tu peux personnaliser les couleurs et le texte dans l'URL
  - TOUJOURS inclure un attribut alt descriptif

{shortcodes_section}

## EXEMPLE DE SORTIE
[
  {{
    "blockId": "hero-section",
    "element": "section",
    "baseStyles": {{
      "minHeight": "90vh",
      "display": "flex",
      "alignItems": "center",
      "justifyContent": "center",
      "padding": "80px 24px",
      "background": "linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%)"
    }},
    "mobileStyles": {{
      "minHeight": "70vh",
      "padding": "40px 16px"
    }},
    "children": [
      {{
        "blockId": "hero-content",
        "element": "div",
        "baseStyles": {{
          "maxWidth": "800px",
          "textAlign": "center"
        }},
        "children": [
          {{
            "blockId": "hero-title",
            "element": "h1",
            "innerHTML": "Votre titre accrocheur ici",
            "baseStyles": {{
              "fontSize": "56px",
              "fontWeight": "700",
              "color": "#ffffff",
              "marginBottom": "24px"
            }},
            "mobileStyles": {{
              "fontSize": "36px"
            }}
          }}
        ]
      }}
    ]
  }}
]

IMPORTANT : Retourne UNIQUEMENT le JSON, sans ```json ni explication."""


def get_page_generation_prompt(
    user_prompt: str,
    page_title: str = None,
    page_type: str = None
) -> str:
    """
    Build the user prompt for page generation.
    Includes specific instructions based on page type.
    """
    context = f"Crée une page web pour : {user_prompt}"

    if page_title:
        context += f"\n\nPage : {page_title}"

    if page_type:
        context += f"\nType de page : {page_type}"

        # Add specific instructions based on page type
        page_instructions = {
            "accueil": """
INSTRUCTIONS SPÉCIFIQUES POUR LA PAGE D'ACCUEIL :
- Crée une section hero impactante avec un titre accrocheur et un CTA
- Ajoute une section présentant les services/produits principaux
- Inclus des témoignages clients si pertinent
- Termine avec un call-to-action final
- Cette page doit donner envie d'explorer le reste du site""",

            "about": """
INSTRUCTIONS SPÉCIFIQUES POUR LA PAGE À PROPOS :
- Raconte l'histoire de l'entreprise de manière engageante
- Présente l'équipe avec le shortcode {{ team_grid }} si disponible
- Mets en avant les valeurs et la mission
- Inclus des chiffres clés (années d'expérience, clients satisfaits, etc.)""",

            "services": """
INSTRUCTIONS SPÉCIFIQUES POUR LA PAGE SERVICES :
- Présente chaque service de manière claire et attractive
- Utilise des icônes ou illustrations pour chaque service
- Ajoute des détails sur les bénéfices pour le client
- Inclus un CTA pour demander un devis ou en savoir plus""",

            "contact": """
INSTRUCTIONS SPÉCIFIQUES POUR LA PAGE CONTACT :
- IMPORTANT : Utilise le shortcode {{ contact_form }} pour le formulaire
- Ajoute les informations de contact (adresse, téléphone, email)
- Utilise {{ contact_info }} si disponible pour les coordonnées
- Inclus une carte ou des horaires d'ouverture si pertinent""",

            "produits": """
INSTRUCTIONS SPÉCIFIQUES POUR LA PAGE PRODUITS :
- Présente les produits avec des images attrayantes
- Inclus les prix et caractéristiques principales
- Ajoute des filtres ou catégories si beaucoup de produits
- Utilise les shortcodes e-commerce si disponibles""",

            "blog": """
INSTRUCTIONS SPÉCIFIQUES POUR LA PAGE BLOG :
- Crée une grille d'articles avec aperçus
- Inclus la date, l'auteur et une image pour chaque article
- Ajoute des catégories ou tags
- Prévois un système de pagination""",
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
            lines.append("## SHORTCODES DYNAMIQUES DISPONIBLES")
            lines.append("Utilise ces shortcodes dans innerHTML pour du contenu dynamique.\n")

            for sc in ai_shortcodes:
                lines.append(f"### {sc.name1} (`{sc.shortcode}`)")
                if sc.description:
                    lines.append(f"{sc.description}")
                if sc.use_when:
                    lines.append(f"**Quand l'utiliser:** {sc.use_when}")
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
