<!-- //// Neoffice — REPLACED. Upstream's CLAUDE.md is a single line, `@AGENTS.md`. Ours
     //// documents the fork's own rules: where the branch lives, how the commit-the-build
     //// pipeline works, and the two working rules for the AI generator. Written in French
     //// on purpose — it addresses the operator, not the code (see the report: it is the
     //// only French left in a file that is not a UI string). At the merge, keep ours. -->
# RÈGLES DE TRAVAIL — Génération de sites clients (PRIORITAIRES)

Ces deux règles s'appliquent à TOUT travail sur le Builder AI (chat, génération, ingestion) :

1. **TOUJOURS tester avec Chrome.** Les `bench execute` / console sont OK pour les premiers tests de logique backend, mais la validation finale se fait DANS Chrome, sur l'interface réelle (`/app/builder-chat`, l'éditeur `/builder`, et les pages publiées rendues). Chrome est l'interface que les **clients** utilisent — donc ça doit être solide là, pas seulement « ça répond en console ». Pas de « c'est bon » sans avoir vu le résultat dans le navigateur.
2. **TOUJOURS documenter dans Obsidian.** Toute décision durable, gotcha, ou avancée du projet va dans le vault Obsidian (`~/Documents/Obsidian/Obsidian/Neoffice/Builder/...`) — en plus de la mémoire projet. Si le vault est inaccessible (lock sandbox), créer une note dédiée (l'écriture de nouveaux fichiers passe même quand la lecture est bloquée) et le signaler.

# Git Configuration

## Branch de production
- **Branche:** `version-15`
- **Remote:** `origin` (bvisible)

## Upstream (lecture seule)
- **Repo:** https://github.com/frappe/builder.git
- **Remote:** `upstream`
- **Branche upstream:** `develop`
- **Usage:** Pull uniquement pour sync les mises à jour officielles

## Règles
1. TOUJOURS push sur `origin`, JAMAIS sur `upstream`
2. Pour sync: `git fetch upstream && git merge upstream/develop`
3. Branch de travail: `version-15`

## Build pipeline (commit-the-build)

⚠️ **Ne jamais lancer `yarn build` ou `bench build --app builder` localement sur un serveur Neoffice** (4 GB RAM → OOM-kill garanti). Le build se fait UNIQUEMENT sur GitHub Actions (ubuntu-latest, 16 GB RAM).

### Comment ça marche

1. Modif d'un fichier source (`frontend/...`) en local → `git commit` → `git push origin version-15`. **Ne pas builder localement.**
2. Le workflow `.github/workflows/build-frontend.yml` détecte le push, lance `yarn build` sur ubuntu-latest (~1-2 min) et commit les artefacts back avec un commit `[skip-build] frontend artifacts for <SHA>` (par `github-actions[bot]`).
3. Sur les instances clients, le pipeline d'update fait `git pull` (ramène ton commit + le commit du bot). Quand `bench build --app builder` tourne, il appelle `yarn build` à la racine — **le `package.json` voit les artefacts déjà présents et skip vite** (gate). Plus d'OOM-kill.

### Paths spécifiques

- **Source frontend** : `frontend/`
- **Artefacts vite (commités)** : `builder/public/frontend/`
- **SPA HTML(s) (commités)** : `builder/www/_builder.html`
- **Build script root** : `yarn workspace (root → frontend)`

### Forcer un rebuild local (si vraiment nécessaire)

```bash
FORCE_REBUILD=1 yarn build
```

### Documentation complète

- Doc canonique : `bvisible/neoffice-devops:main` → `docs/COMMIT-BUILD-PATTERN.md`
- Doc batch migration (12 apps) : même fichier, sections "Apps that have adopted the pattern" + "Edge cases discovered"
- Vault Obsidian : `[[NORA/04-savoir-faire/drive-frontend-build-pattern]]`

### Edge cases spécifiques à builder

- `builder/public/page_scripts` et `page_styles` restent ignorés (générés runtime quand un user publie une page dans Builder).
