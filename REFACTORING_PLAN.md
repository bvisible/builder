# Plan de Refactoring : AI Créative pour Frappe Builder

## Vision

L'AI doit avoir la **liberté créative totale** pour générer des sites web uniques et adaptés au contexte, tout en respectant strictement le format `FrappeBlock`. Le Header et Footer restent fixes (via Website Header Footer Config), mais le contenu central est 100% généré par l'AI.

---

## Fichiers à SUPPRIMER

| Fichier | Raison |
|---------|--------|
| `builder/ai/templates/sections.py` | Templates rigides qui brident la créativité |
| `builder/ai/schemas/block_schema.py` (partiellement) | Supprimer `HeroContent`, `FeaturesContent`, etc. - ne garder que `FrappeBlock` |
| `builder/ai/generators/header_generator.py` | Header géré par Website Header Footer Config |
| `builder/ai/generators/footer_generator.py` | Footer géré par Website Header Footer Config |
| `builder/ai/templates/headers/*` | Inutile, header via config |
| `builder/ai/templates/footers.py` | Inutile, footer via config |
| `builder/ai/templates/webshop_headers.py` | Inutile |
| `builder/ai/templates/webshop_footers.py` | Inutile |
| `builder/ai/validators/auto_fixer.py` | Pas de fallback, ça marche ou erreur |
| `builder/ai/rag/*` | Non utilisé |

---

## Fichiers à MODIFIER

### 1. `builder/ai/schemas/block_schema.py` → SIMPLIFIER

**Garder uniquement :**
- `FrappeBlock` (le schéma de base)
- `FrappeStyles` (les styles CSS)
- `ElementType` (les éléments HTML supportés)

**Supprimer :**
- `HeroContent`, `FeaturesContent`, `TestimonialsContent`, etc.
- `SECTION_CONTENT_SCHEMAS`
- `SectionInfo`, `PageStructure` (l'AI décide librement)

### 2. `builder/ai/generators/page_generator.py` → RÉÉCRIRE

**Nouvelle logique simple :**
```python
class PageGenerator:
    def generate_page(self, prompt: str, theme: str, colors: dict = None) -> list[dict]:
        """
        1. Construire le system prompt avec thème + couleurs + règles FrappeBlock
        2. Envoyer au LLM avec structured output (list[FrappeBlock])
        3. Valider que c'est du JSON valide
        4. Retourner les blocks
        """
```

**Supprimer :**
- `SECTION_TYPE_MAPPING` (plus de mapping forcé)
- `_analyze_structure()` (l'AI décide tout seule)
- `_get_default_structure()` (pas de fallback)
- `_generate_header()` / `_generate_footer()` (via config)
- `_get_fallback_header()` / `_get_fallback_footer()` (pas de fallback)

### 3. `builder/ai/generators/section_generator.py` → SUPPRIMER ou SIMPLIFIER

Ce fichier devient **inutile** car `PageGenerator` génère tout d'un coup. L'AI décide de la structure complète.

Option : le garder si on veut régénérer une section individuelle.

### 4. `builder/ai/prompts/system_prompts.py` → AMÉLIORER

**Nouveau prompt principal ultra-complet :**

```python
CREATIVE_SYSTEM_PROMPT = """
Tu es un expert UI/UX designer qui crée des sites web uniques avec Frappe Builder.

## TA MISSION
Créer un site web CRÉATIF et UNIQUE adapté au contexte du client.
Tu as une liberté totale sur la structure, le layout, le nombre de sections.
Sois créatif ! Chaque site doit être différent.

## FORMAT DE SORTIE OBLIGATOIRE
Tu DOIS retourner une liste de FrappeBlock en JSON valide.

Structure d'un block :
{
  "blockId": "unique-id",           // OBLIGATOIRE, unique
  "element": "section|div|h1|p|...", // OBLIGATOIRE
  "innerHTML": "Texte",             // Pour les éléments texte
  "baseStyles": {                   // CSS en camelCase
    "display": "flex",
    "padding": "80px 24px",
    ...
  },
  "mobileStyles": { ... },          // Styles mobile (<576px)
  "attributes": { "href": "/" },    // Pour liens, images
  "children": [ ... ]               // Blocks enfants
}

## RÈGLES CSS CRITIQUES
- Propriétés en camelCase : backgroundColor, fontSize, flexDirection
- Utiliser les CSS variables pour les couleurs :
  - var(--primary-color) : {primary_color}
  - var(--secondary-color) : {secondary_color}
  - var(--text-color) : couleur du texte
  - var(--muted-color) : texte secondaire
  - var(--surface-color) : fond des cards
  - var(--border-color) : bordures

## THÈME : {theme_name}
{theme_prompt}

## ÉLÉMENTS HTML SUPPORTÉS
section, div, header, footer, nav, main, article, aside,
h1, h2, h3, h4, h5, h6, p, span, a, button,
img, video, iframe, ul, ol, li, form, input, textarea

## CONSIGNES CRÉATIVES
1. Crée une structure logique pour le type de site demandé
2. Utilise des textes RÉALISTES (pas de Lorem ipsum)
3. Varie les layouts (grilles, flex, asymétrique)
4. Inclus des styles responsive (mobileStyles)
5. Assure une hiérarchie visuelle claire
6. Sois CRÉATIF - chaque génération doit être unique !

## EXEMPLE D'OUTPUT
[
  {
    "blockId": "hero-section",
    "element": "section",
    "baseStyles": {
      "minHeight": "90vh",
      "display": "flex",
      "alignItems": "center",
      "padding": "80px 24px",
      "background": "linear-gradient(135deg, var(--primary-color), var(--secondary-color))"
    },
    "children": [...]
  },
  ...
]
"""
```

### 5. `builder/api.py` → SIMPLIFIER

**Modifier `_generate_complete_site_worker()` :**
- Supprimer les références à `SectionGenerator`
- Appeler directement `PageGenerator.generate_page()` pour chaque page
- Pas de include_header/include_footer (géré par la config)

---

## Nouvelle Architecture

```
USER PROMPT
    ↓
┌─────────────────────────────────────────────┐
│  PageGenerator.generate_page()              │
│  ├─ Construit le prompt (thème + couleurs)  │
│  ├─ Appelle LLM avec structured output      │
│  └─ Retourne list[FrappeBlock]              │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│  BlockValidator.validate()                  │
│  └─ Vérifie JSON valide, blockIds uniques   │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│  Builder Page (avec Header/Footer config)   │
└─────────────────────────────────────────────┘
```

---

## Fichiers Finaux (après nettoyage)

```
builder/ai/
├── __init__.py
├── config.py                    # Configuration AI
├── providers/
│   ├── __init__.py
│   ├── base.py
│   ├── ollama_provider.py
│   └── openai_provider.py
├── generators/
│   ├── __init__.py
│   ├── page_generator.py        # SIMPLIFIÉ - génère les pages
│   └── image_generator.py       # Génère les images AI
├── schemas/
│   ├── __init__.py
│   └── block_schema.py          # SIMPLIFIÉ - uniquement FrappeBlock
├── design_system/
│   ├── __init__.py
│   ├── tokens.py
│   ├── styles.py
│   └── themes/                  # Thèmes avec prompts créatifs
│       ├── __init__.py
│       ├── modern.py
│       ├── neobrutalist.py
│       ├── glassmorphism.py
│       ├── minimal.py
│       ├── corporate.py
│       └── creative.py
├── prompts/
│   ├── __init__.py
│   └── system_prompts.py        # AMÉLIORÉ - prompts créatifs
├── validators/
│   ├── __init__.py
│   └── block_validator.py       # SIMPLIFIÉ - validation basique
└── utils.py
```

---

## Ordre d'Implémentation

1. **Simplifier `block_schema.py`** - Garder uniquement FrappeBlock
2. **Réécrire `page_generator.py`** - Génération directe via LLM
3. **Améliorer `system_prompts.py`** - Prompt créatif complet
4. **Simplifier `block_validator.py`** - Validation basique
5. **Modifier `api.py`** - Utiliser le nouveau générateur
6. **Supprimer les fichiers inutiles**
7. **Tester sur Osiris**

---

## Tests de Validation

```bash
# Test rapide
bench --site prod.local execute builder.api.generate_page_blocks \
  --kwargs '{"prompt": "Site pour un fleuriste parisien", "theme": "modern"}'

# Test complet
bench --site prod.local execute builder.api.generate_complete_site \
  --kwargs '{"prompt": "Fleuriste Le Bouquet Parisien - livraison dans tout Paris", "site_name": "bouquet-parisien", "site_type": "vitrine", "theme": "creative"}'
```

**Critères de succès :**
- ✅ Structure de page différente à chaque génération (créativité)
- ✅ Textes réalistes adaptés au contexte (pas de Lorem ipsum)
- ✅ JSON valide avec blockIds uniques
- ✅ Styles responsive inclus
- ✅ Couleurs du thème appliquées
- ✅ Pas d'erreur, pas de fallback
