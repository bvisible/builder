# Neoffice fork markers

What in this repository is **ours** and not `frappe/builder`'s, and where the reason
for each divergence is written down. Every hunk of code we changed carries a
`//// Neoffice` comment saying what upstream did, what we do instead and why:
`grep -rn "////" .` is the map. This file holds what a comment cannot reach —
files with no comment syntax (JSON, CSV, binaries), generated artifacts, and the
handful of hunks a comment cannot legally sit next to.

Checked with `fork_markers.py` from `bvisible/neoffice-ci`:

```bash
curl -fsSL https://raw.githubusercontent.com/bvisible/neoffice-ci/main/scripts/fork_markers.py -o /tmp/fm.py
python3 /tmp/fm.py check --base 518e9e7d --head origin/version-15   # → 3, all three explained below
python3 /tmp/fm.py verify --base <the commit before your edits>     # a marking pass is comments only
```

Every line of a multi-line marker carries `////`, so the whole reason survives a
`grep`. A marker written on only its first line is a bug: the map keeps the
headline and loses the argument.

## builder

### The base, and how it was established

| | |
|---|---|
| Fork | `bvisible/builder`, branch **`version-15`** |
| Upstream | `frappe/builder` (`upstream`), default branch **`develop`** |
| **BASE** | **`518e9e7d2c71c9ea4b2960daf67620b32a5cdf01`** — *fix: prevent arrow keys clobbering text InlineInput fields (#661)*, 2026-07-09, Dhruv Chauhan |
| Brought in by | `9864c9a0` *merge: upstream v1.28.2 (develop 518e9e7d) into version-15*, 2026-07-09 |

The branch name is not the base. `git merge-base --is-ancestor` over every
upstream ref shows that our `version-15` fully contains **34 upstream branch
tips** — `for-release-v1.22.0` (`994750a5`) and 33 topic branches — but the
newest upstream commit it contains is the merge-base with `develop`/`master`,
`518e9e7d` (2026-07-09). Every one of those contained tips is older, so **BASE =
the merge-base with `develop`**, which is also exactly the upstream tip our last
sync merged. `git merge-base --all origin/version-15 upstream/develop` returns a
single commit, so there is no ambiguity.

**Attribution.** `git rev-list origin/version-15 ^BASE ^upstream/develop ^upstream/master`
= **433 commits** (416 non-merge + 17 merges), authored by Jérémy Christillin
(385), `github-actions[bot]` (40, the built-asset commits), Claude (6), Jeremy (2).
`git cherry upstream/develop origin/version-15 BASE` marks all 416 non-merge
commits `+` — not one of them exists upstream in any form. There is **no
`(cherry picked from commit …)` line** anywhere in the range: this fork carries no
backport. Blamed (without `-w`) on a random sample of 60 of the 308 code hunks the
checker first reported unmarked, **148 of the 150 distinct blamed commits are
ours**; the two exceptions are upstream lines our merges kept and are both marked
in place (`builder/api.py:11`, `frontend/src/components/BuilderCanvas.vue:175`).

Upstream moved **1084 commits** on `develop` since BASE. The diff BASE→HEAD is
**299 files, +58 194 / −4 007** (260 added, 38 modified, 1 removed; `git` reports
one of them as a rename, `builder/www/__pycache__/__init__.py` →
`builder/ai/ingestion/__init__.py`, only because both files are empty).

### What the marking pass changed

| | hunks the checker reports unmarked |
|---|---|
| before the pass | **345** (215 added, 93 modified, 30 non-commentable, 7 removed-only) |
| after | **3**, all three unreachable by construction — see *Hunks a comment cannot reach* |

The pass is **comments only**: `fork_markers.py verify` reports no added
non-comment line at any step; where it reports a *removed* line (it refuses every
removal by design) the removal is a comment being rewritten, and the rewrite is
proven inert — `@vue/compiler-sfc` emits byte-identical code for the `.vue` files
before and after, `jinja2.Environment.compile` byte-identical Python for the
templates, `py_compile` and `node --check` pass on everything else.

**No file of ours is byte-identical to upstream's.** The three paths we and
upstream both added independently (`builder/locale/fr.po`, `builder/locale/main.pot`,
`frontend/src/translation.ts`) differ on both sides — see *Merge forecast*.

### Files with no comment syntax

The checker treats a non-commentable file as marked once this manifest names its
full path.

#### DocType JSON — modified upstream doctypes, field by field

| File | Our fields / values | Why | Should be a Custom Field? |
|---|---|---|---|
| `builder/builder/doctype/builder_page/builder_page.json` | `ai_generated_at` (Datetime, hidden, read_only, no_copy) | written by the site-generation worker when it creates the page | **yes** — pure Neoffice state on an upstream doctype |
| | `ai_blocks_hash` (Data, hidden, read_only, no_copy) | hash of the blocks at generation time, so we can tell an untouched generated page from one the client edited | **yes** |
| | both added to `field_order` after `template_group` | | |
| | trailing newline removed at EOF | accident, not intent — take upstream's EOF at the merge | — |
| `builder/builder/doctype/block_template/block_template.json` | `description` (Small Text) + its `field_order` entry | the AI generator picks a template by its description | **yes** |
| | `category.options` rewritten: `Shop\|Hero\|Navbar\|Content\|Footer\|Form\|Card\|Structure\|Basic\|Typography\|Media\|Advanced` | upstream's options describe markup (`Basic Forms`, `Form parts`); ours describe page sections, which is what a generator has to choose by. **Upstream's `Basic Forms` and `Form parts` are dropped** — a site that used them keeps the stored value, which no longer validates | no (it is the same field, re-optioned) — but the merge must re-merge the two option lists, not pick a side |

`frontend/src/stores/blockTemplateStore.ts` carries the same list on the client
and must stay in step with the JSON.

#### DocType JSON — entirely ours (no upstream equivalent)

Every field in these files is ours; the `.py` beside each carries the header
marker that says what the doctype is for.

- `builder/builder/doctype/builder_ai_shortcode/builder_ai_shortcode.json`
- `builder/builder/doctype/builder_chat_message/builder_chat_message.json`
- `builder/builder/doctype/builder_chat_session/builder_chat_session.json`
- `builder/builder/doctype/builder_content_asset/builder_content_asset.json`
- `builder/builder/doctype/builder_shortcode/builder_shortcode.json`
- `builder/builder/doctype/builder_shortcode/builder_shortcode_fixtures.json` (fixture data, not a doctype)
- `builder/builder/doctype/builder_site_inspiration/builder_site_inspiration.json`
- `builder/builder/doctype/website_footer_link/website_footer_link.json`
- `builder/builder/doctype/website_header_footer_config/website_header_footer_config.json`
- `builder/builder/doctype/website_header_footer_variant/website_header_footer_variant.json`
- `builder/builder/doctype/website_menu_item/website_menu_item.json`
- `builder/builder/doctype/website_plugin/website_plugin.json`

#### Vendored data — `builder/ai/design_data/data/*.csv`

Copied verbatim from `nextlevelbuilder/ui-ux-pro-max-skill` (MIT, upstream
`f8ac5e1266dba8354ea96e19994d9f4345e7ec31`) on 2026-07-18 by `5502544c`. **Never
hand-edit**: refresh by re-copying from that project and re-running
`scripts/validate_data.py` — see `builder/ai/design_data/README.md`.

`builder/ai/design_data/data/app-interface.csv` ·
`builder/ai/design_data/data/charts.csv` ·
`builder/ai/design_data/data/colors.csv` ·
`builder/ai/design_data/data/google-fonts.csv` ·
`builder/ai/design_data/data/icons.csv` ·
`builder/ai/design_data/data/landing.csv` ·
`builder/ai/design_data/data/motion.csv` ·
`builder/ai/design_data/data/products.csv` ·
`builder/ai/design_data/data/react-performance.csv` ·
`builder/ai/design_data/data/styles.csv` ·
`builder/ai/design_data/data/typography.csv` ·
`builder/ai/design_data/data/ui-reasoning.csv` ·
`builder/ai/design_data/data/ux-guidelines.csv`

#### package manifests

- `package.json` — the root `build` script became a **gate**: it skips the build
  when `builder/public/frontend/assets` already exists, unless `FORCE_REBUILD=1`.
  A client server has 4 GB of RAM and `vite build` OOM-kills there; CI (16 GB)
  always rebuilds. `build:force` is the original script, kept under a new name.
- `frontend/package.json` — `build` gained `NODE_OPTIONS=--max-old-space-size=4096`
  for the same reason.

#### stray files that should not be in the repository

- `errors.log` — a single line, `[Thu Feb  5 10:15:53 CET 2026] Error on osiris:
  All configured authentication methods failed`. Committed by accident. Delete it;
  it is not a divergence anyone has to carry.
- `dump.rdb` — a 105 KB Redis dump, committed by accident (binary, so the checker
  never even reports it). Delete it.

### Generated artifacts — mark the source, never the artifact

These are build outputs. Upstream ignores them; we commit them so a client
instance pulls a built SPA instead of running vite (the *commit-the-build*
pattern). **The intent lives in `.gitignore`, `frontend/vite.config.mjs`,
`package.json` and `.github/workflows/build-frontend.yml`, all of which carry
markers.** At a merge, rebuild rather than resolve.

- `builder/public/frontend/**` — 63 files (vite chunks, CSS, fonts, logos).
  Skipped by the checker.
- `builder/www/_builder.html` — the SPA shell vite writes from
  `frontend/index.html` (`frappe-ui`'s vite plugin, `indexHtmlPath` in
  `frontend/vite.config.mjs`). A marker was put in it on 2026-09-04 and the very
  next build took it back out: `4d66cb31` *[skip-build] frontend artifacts for
  705d2a7b* removed all five lines, three hours later. **This file cannot hold a
  marker** — it is regenerated from a source that has none, and marking that
  source is wrong too, because `frontend/index.html` is byte-identical to
  upstream's and would only manufacture a merge conflict. This entry is the
  durable record; the checker reports the file and always will (see *Hunks a
  comment cannot reach*).
- `frontend/components.d.ts` — written by `unplugin-vue-components`. Its
  divergence is nothing but the list of the `.vue` components we added; each of
  the 9 lines carries a one-line marker, but a local `vite` run rewrites them.
  **Regenerate this file at the merge; never resolve it by hand.**

### Binaries and translations (no comment syntax, not flagged by the checker)

- `builder/public/icon-builder-website.jpg` — the Neoffice Website icon on the
  apps screen (`hooks.py: add_to_apps_screen`, marked there).
- `builder/public/images/builder-bot.svg` — carries its own marker (SVG is markup).
- `builder/locale/fr.po`, `builder/locale/main.pot` — our French catalogue, served
  to the SPA by `builder/i18n.py`. The checker skips `/locale/`. **Upstream added
  its own `fr.po`/`main.pot` after BASE** — see *Merge forecast*.
- `yarn.lock` — +152 / −3816 against BASE. Regenerate at the merge, do not resolve.
- `.github/workflows/{build-frontend,fork-markers,tests,upstream-preview}.yml` —
  all four are ours (upstream has none of them). The checker skips `.github/`.

### Hunks a comment cannot reach

`fork_markers.py check --base <BASE> --head origin/version-15` reports **three**
hunks and will keep reporting them. None is unmarked by neglect; each is
somewhere a marker cannot legally or durably sit. The reason for each lives here.

| File | What changed | Why no marker | Where the reason is |
|---|---|---|---|
| `frontend/src/components/DashboardHead.vue` | `:placeholder="__('Filter by title or route')"`, i18n pass `bd5dc7f1` | the line is **inside a multi-line opening tag** (`<BuilderInput …>`), between two attributes: neither `<!-- -->` nor `//` is legal there | on `<BuilderInput` and at the top of the `<template>` — but the checker only looks 3 lines up, and `class` + `type` sit in between |
| `frontend/src/components/Settings/GlobalAI.vue` | `:placeholder="preset === 'ollama' ? … "`, provider-aware, `c58af069` | same: inside `<FormControl …>` | on `<FormControl`, four lines above |
| `builder/www/_builder.html` | the whole file (generated SPA shell) | **build output**: `yarn build` rewrites it from `frontend/index.html` and any marker is gone, proven by `4d66cb31` | *Generated artifacts* above, `.gitignore`, `frontend/vite.config.mjs` |

The two Vue hunks are one line each and change nothing but a translated string;
the third is not source at all. Raising `LOOKBACK` in the checker would silence
the first two, and adding `www/_builder.html` to its `_BUILT_ASSET` pattern would
silence the third — both are changes to `bvisible/neoffice-ci`, not to this fork.

### Files we added and deliberately left unmarked

Every commentable file we added carries a
`//// Neoffice — added file (no upstream equivalent): …` header — **147 of them**.
Fourteen do not, on purpose:

| File | Content |
|---|---|
| `builder/ai/ingestion/__init__.py` | empty |
| `builder/builder/doctype/builder_chat_message/__init__.py` | empty |
| `builder/builder/doctype/builder_chat_session/__init__.py` | empty |
| `builder/builder/doctype/builder_content_asset/__init__.py` | empty |
| `builder/builder/doctype/website_header_footer_variant/__init__.py` | empty |
| `builder/builder/doctype/website_plugin/__init__.py` | empty |
| `builder/overrides/__init__.py` | empty |
| `builder/builder/doctype/builder_shortcode/__init__.py` | the two-line copyright header `bench new-doctype` writes |
| `builder/builder/doctype/builder_site_inspiration/__init__.py` | idem |
| `builder/builder/doctype/website_footer_link/__init__.py` | idem |
| `builder/builder/doctype/website_header_footer_config/__init__.py` | idem |
| `builder/builder/doctype/website_menu_item/__init__.py` | idem |
| `builder/hf_utils/__init__.py` | idem |
| `builder/tests/__init__.py` | one line, `# Builder Tests Module` |

**Why.** These carry no intent to record. A package marker file exists because
Python needs it and `bench new-doctype` writes it; its content is either nothing
at all or a boilerplate line generated verbatim, identical to the one in every
upstream doctype folder. A `//// Neoffice` header on an empty file says only
"this directory is ours", which the marked `.py` next to it already says with the
reason. The checker never flags them either — a file whose every line is a
comment, or which has no line at all, produces no code hunk. **The one that does
carry intent, `builder/ai/__init__.py`, is marked**: it is not empty, it explains
the lazy `__getattr__` that replaced eager imports.

### Whitespace-only divergence

- `builder/builder/doctype/builder_page/builder_page.json` — the file lost its
  trailing newline. **Take upstream's at the merge.**

### Two upstream files we still carry after upstream removed them

- `builder/www/_builder.html` — upstream gitignored it in `5d9cb881` (2024); we
  re-added it in `7fac350e` when the commit-the-build pattern landed.
- `builder/tests/__init__.py` — upstream removed the placeholder tests folder in
  `556a88ec`; we re-added it in `9e4a19d5` for the AI tests. Its only line is a
  comment, so the checker never flags it.
- `builder/www/__pycache__/__init__.py` — an accidentally committed `__pycache__`
  file that upstream still carries at BASE; we deleted it. Take our side.

### Merge forecast

**36 files are modified on both sides** since BASE (built assets excluded — none
of those is touched by upstream):

`.gitignore` · `builder/api.py` · `builder/builder/doctype/builder_page/builder_page.{json,py}` ·
`builder/builder/doctype/builder_page/test_builder_page.py` · `builder/hooks.py` ·
`builder/install.py` · `builder/locale/{fr.po,main.pot}` · `builder/patches.txt` ·
`builder/templates/generators/webpage.html` · `frontend/components.d.ts` ·
`frontend/package.json` · `frontend/vite.config.mjs` · `package.json` · `pyproject.toml` ·
`yarn.lock` · and 15 files under `frontend/src/` (`main.ts`, `translation.ts`,
`components/BuilderCanvas.vue`, `BuilderSettings.vue`, `BuilderToolbar.vue`,
`BuilderCommandPalette.vue`, `BuilderBlockTemplates.vue`, `DashboardContent.vue`,
`DashboardHead.vue`, `DashboardSidebar.vue`, `DashboardToolbar.vue`, `PageCard.vue`,
`PageListItem.vue`, `Modals/NewBlockTemplate.vue`, `Settings/GlobalAI.vue`,
`BlockPropertySections/LayoutSection.ts`, `composables/useDashboardState.ts`,
`pages/PageBuilderDashboard.vue`, `stores/blockTemplateStore.ts`).

The four things that will hurt:

1. **Upstream now has its own `builder/ai/`.** 55 files (`agent/`, `api.py`,
   `llm.py`, `codex.py`, `page_writer.py`, `prompts.py`, `session.py`, 20 `test_*.py`…),
   with **no `builder/ai/__init__.py`** — an implicit namespace package. No path
   collides with our 68 files **except one that git will not report**: upstream's
   module `builder/ai/prompts.py` against our package `builder/ai/prompts/`.
   Python resolves the package first, so after a naive merge upstream's
   `builder.ai.prompts` is shadowed and their imports break. Our
   `builder/ai/__init__.py` also turns their namespace package into a regular one.
   Decide the layout before merging, not during.
2. **Upstream implemented i18n independently** (Aug 2026): `frontend/src/translation.ts`
   (`window.translated_messages`, `frappe.translate.get_boot_translations`),
   `builder/locale/main.pot` + `fr.po`, Crowdin config. Ours predates it
   (`window.translatedMessages`, `builder.i18n.get_translations`, `builder/i18n.py`,
   `main.ts`). Three **add/add conflicts**, and our whole i18n layer is now
   redundant. Take upstream's mechanism, port our catalogue into their `fr.po`,
   and delete `builder/i18n.py` + our `translation.ts` once the strings match.
3. **`Builder Variable` was renamed `Builder Token` upstream** (`builder_variable.js/json`
   → `builder_token.js/json`, `VariableManager.vue` → `TokenManager.vue`), and
   `DimenstionSection.ts` → `DimensionSection.ts`. We do not modify any of them,
   so this should merge clean — but grep our AI prompts and generated blocks for
   the word "variable" before assuming it.
4. **`builder/templates/generators/webpage.html` and `builder/builder/doctype/builder_page/builder_page.py`.**
   Ours rewrote the document: our `webpage.html` owns `<body>` and wraps the page
   in the site chrome, and `builder_page.py` rewrites the page's own `<body>` into
   `div.builder-page-content` to match. Upstream keeps `{ { __content } }` as the
   whole document. This is the deepest structural divergence in the fork; both
   files must be resolved together, and `TestBuilderPageSiteChrome` in
   `test_builder_page.py` is the guard that says the chrome still renders.

Also worth knowing: `builder/patches.txt` — our 12 patches are appended after
upstream's list and two are inserted at the top of `[post_model_sync]`. A merge
must keep **both** sides; an entry whose module is missing kills `bench migrate`
on the whole fleet.
