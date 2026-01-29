# Builder AI - Documentation Technique

## Vue d'ensemble

Builder AI est un module d'intelligence artificielle intégré à Frappe Builder qui permet de générer des sites web via une interface de chat conversationnelle. L'utilisateur décrit son projet en langage naturel, et l'IA collecte les informations nécessaires puis génère des pages structurées avec des blocks Frappe Builder.

## Architecture

```
builder/
├── builder_ai.py                    # Logique principale AI
├── builder/
│   ├── doctype/
│   │   ├── builder_ai_conversation/ # DocType: conversations
│   │   ├── builder_ai_settings/     # DocType: configuration (Single)
│   │   └── builder_ai_shortcode/    # DocType: shortcodes (Child Table)
│   └── tests/
│       └── test_builder_ai.py       # Tests unitaires
└── docs/
    └── AI_BUILDER.md                # Cette documentation
```

## DocTypes

### Builder AI Settings (Single DocType)

Configuration centralisée de l'AI Builder.

| Champ | Type | Description |
|-------|------|-------------|
| `enabled` | Check | Active/désactive l'AI Builder |
| `ai_provider` | Select | `ollama` ou `openai` |
| `ollama_base_url` | Data | URL de l'API Ollama (défaut: `http://localhost:11434`) |
| `ollama_api_key` | Password | Clé API pour Cloudflare WAF (header X-API-Key) |
| `ollama_model` | Data | Modèle texte Ollama (défaut: `llama3.1`) |
| `ollama_vision_model` | Data | Modèle vision Ollama (défaut: `llava`) |
| `ollama_timeout` | Int | Timeout en secondes (défaut: 120) |
| `openai_api_key` | Password | Clé API OpenAI |
| `openai_model` | Data | Modèle texte OpenAI (défaut: `gpt-4o-mini`) |
| `openai_vision_model` | Data | Modèle vision OpenAI (défaut: `gpt-4o`) |
| `openai_timeout` | Int | Timeout en secondes (défaut: 60) |
| `enable_vision` | Check | Active le support des images |
| `creativity_level` | Select | `conservative`, `balanced`, `creative`, `experimental` |
| `default_style` | Select | Style par défaut des sites générés |
| `use_modern_design` | Check | Privilégier les designs modernes |
| `default_site_type` | Select | `auto`, `one_page`, `multi_page` |
| `allow_multipage` | Check | Autoriser les sites multi-pages |
| `shortcodes` | Table | Table des shortcodes disponibles |
| `custom_system_prompt` | Text | Prompt système personnalisé |
| `design_guidelines` | Text | Directives de design additionnelles |
| `debug_mode` | Check | Mode debug (logs détaillés) |

### Builder AI Conversation

Stocke les conversations avec l'AI.

| Champ | Type | Description |
|-------|------|-------------|
| `title` | Data | Titre de la conversation |
| `status` | Select | `collecting`, `generating`, `completed`, `cancelled` |
| `messages` | Long Text | Messages JSON de la conversation |
| `site_context` | Long Text | Contexte du site collecté (JSON) |
| `generated_blocks` | Long Text | Blocks générés (JSON) |
| `page` | Link | Lien vers la page générée |

### Builder AI Shortcode (Child Table)

Composants réutilisables pour la génération.

| Champ | Type | Description |
|-------|------|-------------|
| `name1` | Data | Nom du shortcode |
| `shortcode` | Small Text | Code Jinja du shortcode |
| `category` | Select | Navigation, E-commerce, User, Search, etc. |
| `use_when` | Small Text | Quand utiliser ce shortcode |
| `description` | Text | Description du shortcode |

## API Endpoints

### Configuration

#### `get_ai_config()`
Retourne la configuration actuelle (pour le frontend).

```python
# Réponse
{
    "enabled": True,
    "provider": "ollama",
    "ollama_model": "llama3.1",
    "enable_vision": True,
    "creativity_level": "balanced",
    ...
}
```

#### `test_llm_connection()`
Teste la connexion au LLM.

```python
# Réponse succès
{
    "success": True,
    "provider": "ollama",
    "model": "llama3.1",
    "message": "Connection successful!"
}
```

### Conversation

#### `start_conversation(title: str)`
Démarre une nouvelle conversation.

```python
# Réponse
{
    "conversation_id": "CONV-00001",
    "message": "Bonjour! Quel type de site souhaitez-vous créer?",
    "site_context": {},
    "collection_complete": False
}
```

#### `send_message(conversation_id: str, message: str)`
Envoie un message dans la conversation.

```python
# Réponse
{
    "conversation_id": "CONV-00001",
    "message": "Réponse de l'AI",
    "site_context": {...},
    "collection_complete": False,
    "next_topic": "colors"
}
```

#### `send_message_with_image(conversation_id, message, image_data, image_type)`
Envoie un message avec une image (logo, référence, contenu).

```python
# image_type: "logo" | "reference" | "content"
# Réponse
{
    "conversation_id": "CONV-00001",
    "message": "J'ai analysé votre logo...",
    "site_context": {...},
    "collection_complete": False,
    "image_analysis": {
        "colors": ["#FF5733", "#2E86AB"],
        "mood": "professional",
        ...
    }
}
```

#### `get_conversation(conversation_id: str)`
Récupère les détails d'une conversation.

#### `list_conversations()`
Liste les conversations de l'utilisateur courant.

### Vision

#### `analyze_logo(image_data: str)`
Analyse un logo pour extraire couleurs et style.

```python
# Réponse
{
    "success": True,
    "analysis": {
        "description": "Logo moderne avec...",
        "colors": ["#3B82F6", "#10B981"],
        "mood": "professional and innovative",
        "style_suggestions": ["minimal", "tech"],
        "design_insights": {
            "recommended_palette": [...],
            "typography_style": "sans-serif modern",
            "layout_suggestions": "..."
        }
    }
}
```

#### `analyze_reference_image(image_data, context)`
Analyse une image de référence/inspiration.

### Génération

#### `generate_page(conversation_id, page_name)`
Génère une page Builder à partir du contexte collecté.

```python
# Réponse
{
    "success": True,
    "page_name": "my-company",
    "page_route": "/my-company",
    "blocks": [...]
}
```

#### `generate_blocks_with_llm(conversation_id)`
Génère des blocks via le LLM (plus créatif).

#### `preview_blocks(conversation_id)`
Prévisualise les blocks sans créer de page.

#### `update_site_context(conversation_id, site_context)`
Met à jour manuellement le contexte du site.

## Structure des Blocks

Les blocks Frappe Builder suivent cette structure:

```json
{
    "blockId": "abc123def",
    "element": "section",
    "blockName": "hero",
    "innerHTML": "",
    "attributes": {},
    "customAttributes": {},
    "classes": [],
    "dataKey": null,
    "baseStyles": {
        "display": "flex",
        "flexDirection": "column",
        "paddingTop": "120px"
    },
    "tabletStyles": {},
    "mobileStyles": {
        "paddingTop": "80px"
    },
    "rawStyles": {
        "hover:opacity": "0.9"
    },
    "children": []
}
```

## Prompt Système

Le prompt système est généré dynamiquement via `get_collector_prompt(settings)`:

1. **Personnalité créative**: L'AI se comporte comme un web designer expert
2. **Psychologie des couleurs**: Suggestions basées sur l'industrie
   - Fleuriste → couleurs chaudes, naturelles
   - Tech/SaaS → bleus, violets
   - Restaurant → oranges, rouges
   - Luxe → noir, or, tons bijou
3. **Shortcodes dynamiques**: Injectés depuis les settings
4. **Niveau de créativité**: Ajuste la température du LLM
   - `conservative`: 0.5
   - `balanced`: 0.7
   - `creative`: 0.9
   - `experimental`: 1.1

## Niveaux de Créativité

| Niveau | Temperature | Comportement |
|--------|-------------|--------------|
| Conservative | 0.5 | Designs classiques, prévisibles |
| Balanced | 0.7 | Équilibre créativité/cohérence |
| Creative | 0.9 | Designs uniques, innovants |
| Experimental | 1.1 | Très créatif, parfois imprévisible |

## Support Vision

### Modèles supportés

| Provider | Modèle Vision | Capacités |
|----------|---------------|-----------|
| Ollama | llava, llava:13b, bakllava | Analyse d'images locale |
| OpenAI | gpt-4o, gpt-4-vision-preview | Analyse d'images cloud |

### Types d'images

| Type | Usage | Extraction |
|------|-------|------------|
| `logo` | Logo de l'entreprise | Couleurs → palette du site |
| `reference` | Design d'inspiration | Layout, effets, ambiance |
| `content` | Contenu à intégrer | Description pour le design |

## Shortcodes Disponibles

Exemples de shortcodes configurables:

```jinja
{# Panier e-commerce #}
{% include "cart_icon.html" %}

{# Menu utilisateur #}
{% if frappe.session.user != "Guest" %}
  {{ user_menu() }}
{% endif %}

{# Recherche #}
<div id="search-widget">{{ search_bar() }}</div>

{# Menu mobile #}
<button class="mobile-menu-toggle">☰</button>
```

## Tests

### Lancer les tests

```bash
# Tous les tests AI Builder
bench --site [site] run-tests --module builder.builder.tests.test_builder_ai

# Tests du DocType Conversation
bench --site [site] run-tests --module builder.builder.doctype.builder_ai_conversation.test_builder_ai_conversation
```

### Tests disponibles

1. **TestBuilderAI**: Tests des fonctions de génération
   - `test_generate_block_id`: Génération d'IDs uniques
   - `test_get_llm_config_defaults`: Configuration par défaut
   - `test_get_hero_template`: Template hero
   - `test_get_features_template`: Template features
   - `test_get_cta_template`: Template CTA
   - `test_get_footer_template`: Template footer
   - `test_block_structure_validity`: Structure des blocks
   - `test_responsive_styles`: Styles responsive

2. **TestBuilderAIAPI**: Tests des endpoints API
   - `test_get_ai_config_api`: Configuration API
   - `test_start_conversation_api`: Démarrage conversation
   - `test_send_message_api`: Envoi de messages
   - `test_generate_page_api`: Génération de page
   - `test_preview_blocks_api`: Prévisualisation

3. **TestBuilderAIConversation**: Tests du DocType
   - `test_create_conversation`: Création
   - `test_update_messages`: Mise à jour messages
   - `test_update_site_context`: Mise à jour contexte
   - `test_status_transitions`: Transitions d'état
   - `test_link_to_page`: Lien vers page

## Installation & Configuration

### Prérequis

**Option 1: Ollama Local (développement)**
```bash
# Installer Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Télécharger les modèles
ollama pull llama3.1      # Modèle texte
ollama pull llava         # Modèle vision (optionnel)

# Démarrer le serveur
ollama serve
```

**Option 2: Ollama avec Cloudflare WAF (production)**

Pour les serveurs Ollama protégés par Cloudflare WAF:

1. Configurer l'URL avec le suffixe `/v1` (endpoint OpenAI-compatible)
   ```
   https://ollama.example.com/v1
   ```
2. Configurer la clé API dans `ollama_api_key` (sera envoyée via header `X-API-Key`)

Le Builder AI détecte automatiquement le mode à utiliser:
- Si `ollama_api_key` est défini → Mode proxy Cloudflare (OpenAI-compatible)
- Si l'URL contient `/v1` → Mode proxy Cloudflare (OpenAI-compatible)
- Sinon → Mode Ollama natif (local)

**Option 3: OpenAI**
- Obtenir une clé API sur https://platform.openai.com

### Configuration

1. Aller dans **Builder AI Settings** (`/app/builder-ai-settings`)
2. Activer l'AI Builder
3. Configurer le provider (Ollama/OpenAI)
4. Pour Ollama avec Cloudflare: renseigner l'API Key
5. Tester la connexion
6. (Optionnel) Activer la vision
7. (Optionnel) Configurer les shortcodes
8. (Optionnel) Ajuster le niveau de créativité

## Dépannage

### Ollama ne répond pas

```bash
# Vérifier que Ollama est lancé
curl http://localhost:11434/api/tags

# Si erreur, redémarrer
ollama serve
```

### Erreur de timeout

Augmenter `ollama_timeout` dans les settings (défaut: 120s).

### Vision ne fonctionne pas

1. Vérifier que `enable_vision` est activé
2. Vérifier que le modèle vision est installé (`ollama pull llava`)
3. Vérifier les logs (`debug_mode`)

### Blocks mal formatés

Activer `debug_mode` pour voir les réponses LLM brutes dans les Error Logs.

### Erreur 403 (Cloudflare WAF)

Si vous utilisez un serveur Ollama protégé par Cloudflare:

1. Vérifier que `ollama_api_key` est correctement configuré
2. Vérifier que la clé est valide auprès de l'administrateur
3. L'URL doit être au format `https://ollama.example.com/v1`

### Erreur 401 (Authentication)

La clé API est invalide ou expirée. Régénérer une nouvelle clé.

## Flux de Travail Complet

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Vue.js)                         │
│  AIBuilder.vue ──> Chat Interface ──> SitePreview.vue           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API (builder_ai.py)                          │
│                                                                  │
│  start_conversation() ──> send_message() ──> generate_page()    │
│         │                      │                    │            │
│         ▼                      ▼                    ▼            │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────┐      │
│  │  Collector  │    │  Context Update │    │  Generator  │      │
│  │   Prompt    │    │   + Vision      │    │  Templates  │      │
│  └─────────────┘    └─────────────────┘    └─────────────┘      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         LLM Provider                             │
│                                                                  │
│          ┌──────────┐              ┌──────────────┐             │
│          │  Ollama  │      OR      │   OpenAI     │             │
│          │ (Local)  │              │   (Cloud)    │             │
│          └──────────┘              └──────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Frappe Database                             │
│                                                                  │
│  Builder AI Conversation ──> Builder Page (blocks JSON)         │
└─────────────────────────────────────────────────────────────────┘
```

## Changelog

### v1.0.0 (Initial)
- Chat conversationnel pour création de sites
- Support Ollama et OpenAI
- Génération de blocks (hero, features, CTA, footer)
- DocTypes: Conversation, Settings

### v1.1.0 (Vision + Créativité)
- Support vision (analyse de logos/images)
- Shortcodes configurables
- Niveaux de créativité
- Prompt dynamique avec psychologie des couleurs
- Modèles vision séparés (llava, gpt-4o)
