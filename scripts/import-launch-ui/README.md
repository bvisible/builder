<!-- //// Neoffice — added file (no upstream equivalent): how the sections of launch-ui become blocks of the Builder Hub -->
# launch-ui → blocks of the hub

[launch-ui](https://github.com/launch-ui/launch-ui) (MIT, Copyright (c) 2024 Mikolaj Dobrucki) is a library of landing-page sections written as React
components with shadcn/ui and Tailwind. A block of the hub is markup, so its sections are rendered first, then read by the importer
(`builder/site_ai/nora/importer.py`, `import_launch_ui`).

```bash
# 1. the sources, at the commit the importer pins (importer.LAUNCH_UI["ref"])
mkdir -p ~/.cache/claude-builder-importer && cd ~/.cache/claude-builder-importer
gh api repos/launch-ui/launch-ui/tarball/<ref> > launch-ui.tgz && mkdir launch-ui && tar -xzf launch-ui.tgz -C launch-ui --strip-components=1
# 2. the renderer (a copy of this folder, so that node_modules stay out of the repository)
cp -R <this folder> render && cd render && npm install --ignore-scripts
# 3. the sections, as HTML
node render.mjs ../launch-ui ../html hero cta items faq pricing stats logos
# 4. on osiris, where the hub's publisher key is: upload ../html there, then
bench --site prod.local execute builder.site_ai.nora.importer.import_launch_ui --kwargs "{'folder': '/home/neoffice/launch-ui-html', 'push': True}"
```

Nothing is published: the blocks reach the hub as drafts, with the source, its licence and its holder in their notes.
