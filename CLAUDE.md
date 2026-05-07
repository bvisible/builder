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
