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
