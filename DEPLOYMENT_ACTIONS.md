# Builder AI - Actions de Déploiement

Ce fichier documente toutes les actions manuelles effectuées lors du déploiement sur les instances.
**Ces actions devront être automatisées par la suite.**

## Instance: Osiris (prod.local)
**Date:** 2026-01-29

### 1. Prérequis vérifiés
- [x] Nora installé avec configuration Ollama fonctionnelle
- [x] Builder app installé

### 2. Configuration récupérée de Nora
```
Provider: ollama
Base URL: https://ollama.noraai.ch
Model: gpt-oss:120b-cloud
API Key: BzTfBEPqBE... (récupérée depuis NORA Settings)
```

### 3. Actions manuelles effectuées

#### 3.1 Désinstallation de neoffice_ia_builder
```bash
bench --site prod.local uninstall-app neoffice_ia_builder
bench remove-app neoffice_ia_builder
```

#### 3.2 Mise à jour de Builder vers la branche avec AI
```bash
cd apps/builder
git fetch origin
git checkout claude/frappe-ai-builder-oZPaw
git pull
```

#### 3.3 Migration
```bash
bench --site prod.local migrate
```

#### 3.4 Configuration Builder AI Settings
Via console Frappe:
```python
# Créer/mettre à jour Builder AI Settings avec:
# - ai_provider: ollama
# - ollama_base_url: https://ollama.noraai.ch/v1
# - ollama_api_key: (clé de Nora)
# - ollama_model: gpt-oss:120b-cloud
```

### 4. Dépendances Python supplémentaires
<!-- Ajouter ici si des pip install sont nécessaires -->

- [ ] Aucune pour l'instant

### 5. Tests effectués
- [x] Test connexion LLM ✅
  ```json
  {"success": true, "provider": "ollama", "model": "gpt-oss:120b-cloud", "auth": "X-API-Key (Cloudflare WAF)"}
  ```
- [x] Test création conversation ✅
  ```
  conversation_id: "0r3intoip9"
  L'AI répond correctement et collecte les informations du site
  ```
- [x] Test envoi de messages (send_message) ✅
  ```
  L'AI extrait: business_name, industry, tagline, colors, sections, etc.
  collection_complete passe à true quand suffisamment d'infos collectées
  ```
- [x] Test génération de page (generate_page) ✅
  ```
  Page créée: page-bc1de489
  Route: la-mie-doree-test
  Blocks: 14301 caractères (hero, features, cta, footer)
  Conversation status: completed
  ```

### 6. Notes importantes découvertes

#### 6.1 Console Frappe et transactions
**IMPORTANT:** Lors des tests via `bench console`, les transactions ne sont pas auto-commitées.
Il faut ajouter `frappe.db.commit()` après les appels qui modifient la base de données.

```python
result = frappe.call("builder.builder_ai.generate_page", ...)
frappe.db.commit()  # OBLIGATOIRE en console
```

#### 6.2 Problèmes mineurs identifiés
- Le titre de page est "My Page" au lieu du business_name (amélioration à faire)
- Les contenus des blocks sont des placeholders génériques en anglais (le LLM ne personnalise pas encore les textes)

---

## Notes pour automatisation future

### Script de migration recommandé
```python
# À inclure dans un patch ou hook post-install
def migrate_from_nora_settings():
    """Copier la configuration Ollama de Nora vers Builder AI Settings"""
    import frappe

    # Vérifier si Nora est installé
    if not frappe.db.exists("DocType", "NORA Settings"):
        return

    nora = frappe.get_single("NORA Settings")

    # Créer/mettre à jour Builder AI Settings
    builder_settings = frappe.get_single("Builder AI Settings")
    builder_settings.ai_provider = "ollama"
    builder_settings.ollama_base_url = nora.base_url + "/v1"
    builder_settings.ollama_api_key = nora.get_password("api_key")
    builder_settings.ollama_model = nora.model
    builder_settings.save()
```
