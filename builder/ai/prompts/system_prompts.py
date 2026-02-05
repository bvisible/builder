"""
System Prompts for Creative AI Generation
These prompts give the AI full creative freedom while ensuring valid FrappeBlock output.
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
) -> str:
    """
    Build the main creative system prompt.

    This prompt gives the AI full creative freedom to design unique websites
    while ensuring it outputs valid FrappeBlock JSON.
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
## COULEURS DU SITE (IMPORTANT!)
- Couleur primaire : {primary_color} (utilise cette couleur pour les boutons, liens, accents)
- Couleur secondaire : {secondary_color} (utilise pour les gradients, hover states)

UTILISATION DES COULEURS:
- Hero backgrounds: utilise des gradients entre primary et secondary
- Boutons: backgroundColor: "{primary_color}"
- Cards: backgroundColor: "var(--surface-color)" ou "#ffffff"
- Icônes et accents: "{primary_color}"

RÈGLES DE CONTRASTE (CRITIQUE!):
- Hero/sections avec gradient ou fond coloré (primary/secondary) → color: "#ffffff"
- Sections fond blanc (#ffffff) → color: "var(--text-color)"
- Sections fond gris clair (#f8fafc, #fafafa, #f5f5f5) → color: "var(--text-color)"
- Cards sur fond blanc/clair → color: "var(--text-color)"
- JAMAIS de texte blanc sur fond blanc ou gris clair!
"""
        else:
            # Brief exists, just remind of the actual color values
            colors_section = f"""
## COULEURS EFFECTIVES
- var(--primary-color) = {primary_color}
- var(--secondary-color) = {secondary_color}
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

## TYPOGRAPHIE - UTILISER LES CSS VARIABLES (IMPORTANT!)
La typographie est gérée globalement via des CSS variables. Tu n'as PAS besoin de spécifier fontSize/fontWeight pour les éléments de texte standard :
- Pour h1, h2, h3, h4, p : NE PAS spécifier fontSize ni fontWeight
- Le CSS global applique automatiquement les bonnes tailles via var(--h1-size), var(--h2-size), etc.
- Les styles mobiles sont aussi gérés automatiquement

EXCEPTION : Tu peux override la taille UNIQUEMENT pour :
- Texte sur fond coloré/hero qui nécessite une couleur spécifique (color: "#ffffff")
- Éléments qui doivent être plus grands que le standard (display headlines)
- Labels, spans, ou petits textes d'UI

EXEMPLE CORRECT (laisser le CSS gérer la taille) :
{{
  "element": "h1",
  "innerHTML": "Mon titre",
  "baseStyles": {{ "color": "#ffffff", "marginBottom": "24px" }}
}}

EXEMPLE À ÉVITER (override inutile) :
{{
  "element": "h1",
  "innerHTML": "Mon titre",
  "baseStyles": {{ "fontSize": "48px", "fontWeight": "700" }}
}}

{design_brief_section}
{colors_section}
{font_section}

## THÈME : {theme_name}
{theme_prompt}

## RÈGLES DE CONTRASTE TEXTE/FOND (CRITIQUE!)
Assure TOUJOURS un bon contraste entre le texte et le fond:

| Fond de section | Couleur du texte |
|-----------------|------------------|
| Gradient coloré (primary/secondary) | "#ffffff" |
| Fond coloré (var(--primary-color), etc.) | "#ffffff" |
| Fond blanc (#ffffff) | "var(--text-color)" |
| Fond gris clair (#f8fafc, #fafafa, #f5f5f5) | "var(--text-color)" |
| var(--surface-color) | "var(--text-color)" |

⚠️ ERREUR FRÉQUENTE À ÉVITER: Ne JAMAIS mettre color: "#ffffff" sur une section à fond blanc ou gris clair!

## CONSIGNES CRÉATIVES

### Structure
- Crée une structure LOGIQUE pour le type de site demandé
- Un fleuriste ≠ une agence tech ≠ un restaurant
- Adapte le nombre de sections au contenu (4-8 selon la page)
- Page d'accueil/one-page : 6-8 sections pour un site complet et riche
- Pages intérieures : 4-6 sections

### Variations de Hero (VARIE tes designs!)
Ne fais pas toujours "titre + sous-titre + CTA". Explore ces variations :
- **Hero Split** : Image à gauche/droite, texte de l'autre côté (layout 50/50)
- **Hero Minimal** : Titre géant seul centré, sans image
- **Hero Stats** : Chiffres clés intégrés directement dans le hero
- **Hero Cards** : 2-3 mini-cards de services dans le hero
- **Hero Asymétrique** : Layout non centré, éléments décalés artistiquement
- **Hero avec carrousel** : Slider de produits ou images

### Layouts Avancés (VARIE ces patterns!)
- **Grilles** : 2, 3, 4, 5 colonnes selon le contenu
- **Asymétrique** : 60/40, 70/30, pas toujours 50/50
- **Bento Grid** : Cards de tailles variées (1 grande + 2 petites)
- **Zigzag** : Alternance gauche/droite pour les features
- **Full-bleed** : Sections qui prennent 100% de la largeur
- **Centered narrow** : Contenu étroit (max-width: 700px) pour la lecture

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
              "color": "#ffffff",
              "marginBottom": "24px"
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
            "one_page": """
INSTRUCTIONS SPÉCIFIQUES POUR UN SITE ONE-PAGE :
⚠️ TRÈS IMPORTANT : Tu dois créer TOUTES les sections sur UNE SEULE PAGE avec des IDs pour la navigation par ancres.

SECTIONS OBLIGATOIRES (4) avec ces IDs EXACTS :
1. Section Hero avec id="hero" → Navigation: /#hero
2. Section Services avec id="services" → Navigation: /#services
3. Section À propos avec id="about" → Navigation: /#about
4. Section Contact avec id="contact" → Navigation: /#contact

SECTIONS OPTIONNELLES (ajoute 2-4 selon le contexte) :
- Témoignages avec id="testimonials" → Navigation: /#testimonials
- Portfolio avec id="portfolio" → Navigation: /#portfolio
- Équipe avec id="team" → Navigation: /#team
- FAQ avec id="faq" → Navigation: /#faq
- Tarifs avec id="pricing" → Navigation: /#pricing
- Galerie avec id="gallery" → Navigation: /#gallery

OBJECTIF : 6-8 sections pour un site complet et riche.

COMMENT AJOUTER L'ID :
Utilise l'attribut "attributes" avec "id" pour chaque section principale :
{
  "blockId": "hero-section",
  "element": "section",
  "attributes": {"id": "hero"},
  ...
}

CONTENU ATTENDU :
- Hero (#hero) : Titre accrocheur, sous-titre, CTA principal (VARIE le style!)
- Services (#services) : Présentation des services/offres (3-4 cards)
- À propos (#about) : Histoire, valeurs, équipe ou chiffres clés
- Contact (#contact) : Formulaire avec {% include 'builder/templates/includes/contact_form.html' %} + coordonnées

DESIGN :
- Alterne les fonds (clair/foncé/coloré) pour distinguer les sections
- Chaque section doit avoir une hauteur confortable (minHeight: 80vh minimum pour hero)
- Assure une bonne transition visuelle entre les sections
- VARIE les layouts : pas que des grilles de 3 colonnes!""",

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
- Mets en avant les valeurs et la mission
- Inclus des chiffres clés (années d'expérience, clients satisfaits, etc.)

SHORTCODES DISPONIBLES POUR CETTE PAGE :
- Pour l'équipe : {%% include 'builder/templates/includes/team_grid.html' %%}
- Pour l'historique : {%% include 'builder/templates/includes/company_timeline.html' %%}

STRUCTURE SUGGÉRÉE (5-6 sections) :
1. Hero "Notre Histoire" avec titre et sous-titre engageants
2. Section présentation de l'entreprise
3. Section valeurs (3-4 cards visuelles)
4. Section équipe avec team_grid shortcode
5. Section historique/timeline avec company_timeline shortcode
6. Section chiffres clés (stats impressionnantes)""",

            "services": """
INSTRUCTIONS SPÉCIFIQUES POUR LA PAGE SERVICES :
- Présente chaque service de manière claire et attractive
- Utilise des icônes ou illustrations pour chaque service
- Ajoute des détails sur les bénéfices pour le client
- Inclus un CTA pour demander un devis ou en savoir plus""",

            "contact": """
INSTRUCTIONS SPÉCIFIQUES POUR LA PAGE CONTACT :
- IMPORTANT : Utilise le shortcode avec include Jinja pour le formulaire :
  {% include 'builder/templates/includes/contact_form.html' %}
- IMPORTANT : Pour la carte Google Maps, utilise cette syntaxe EXACTE :
  {% set address = "Adresse complète ici" %}{% set height = "350px" %}{% include 'builder/templates/includes/google_map.html' %}
- IMPORTANT : Pour les informations de contact, utilise :
  {% include 'builder/templates/includes/contact_info.html' %}
- Structure recommandée: 2 colonnes (formulaire à gauche, carte/infos à droite)
- Ajoute les informations de contact (adresse, téléphone, email)
- Exemple de layout avec carte:
  <section style="display: grid; grid-template-columns: 1fr 1fr; gap: 40px;">
    <div>{% include 'builder/templates/includes/contact_form.html' %}</div>
    <div>
      {% set address = "123 Rue Example, 1000 Ville, Pays" %}{% set height = "350px" %}{% include 'builder/templates/includes/google_map.html' %}
      {% include 'builder/templates/includes/contact_info.html' %}
    </div>
  </section>""",

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

            "collection": """
INSTRUCTIONS SPÉCIFIQUES POUR LA PAGE COLLECTION :
- Présente les catégories ou collections de produits de manière attrayante
- Met en avant les produits phares ou les nouveautés
- NE PAS afficher tous les produits (la boutique complète est sur /all-products)
- Inclus un lien CTA vers la boutique complète : "Voir tous les produits" → /all-products

SHORTCODES E-COMMERCE DISPONIBLES :
1. Carrousel de produits :
   {%- set carousel_title = "Nouveautés" -%}
   {%- set carousel_limit = 8 -%}
   {%% include "webshop/templates/includes/product_carousel.html" %%}

2. Carrousel de marques :
   {%- set carousel_title = "Nos Marques" -%}
   {%% include "webshop/templates/includes/brand_carousel.html" %%}

3. Produits en promo :
   {%- set show_discounted_only = true -%}
   {%% include "webshop/templates/includes/product_carousel.html" %%}

STRUCTURE SUGGÉRÉE :
1. Hero avec titre "Nos Collections" ou "Découvrez notre sélection"
2. Section catégories/collections (3-4 cards grandes avec images)
3. Section nouveautés avec product_carousel shortcode
4. Section marques avec brand_carousel shortcode (si pertinent)
5. CTA vers la boutique complète""",

            "boutique": """
INSTRUCTIONS SPÉCIFIQUES POUR LA PAGE COLLECTION :
- Cette page présente les collections, pas tous les produits
- Utilise des cards visuelles pour les catégories
- Inclus un lien vers /all-products pour la boutique complète
- Même instructions que le type "collection" ci-dessus""",
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
