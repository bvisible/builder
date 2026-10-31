<!-- //// Neoffice — added file (no upstream equivalent): how sections written as React components become blocks of the Builder Hub -->
# React sections → blocks of the hub

A block of the hub is markup. Two MIT libraries write their sections as React components, so they are rendered first, then read by the importer
(`builder/site_ai/nora/importer.py`):

- [launch-ui](https://github.com/launch-ui/launch-ui) (Copyright (c) 2024 Mikolaj Dobrucki), shadcn/ui and Tailwind, `import_launch_ui`;
- [Tailblocks](https://github.com/mertJF/tailblocks) (Copyright (c) 2020 Mert Cukuren), `import_tailblocks`.

```bash
# 1. the sources, at the commit the importer pins (importer.LAUNCH_UI["ref"], importer.TAILBLOCKS["ref"])
mkdir -p ~/.cache/claude-builder-importer && cd ~/.cache/claude-builder-importer
gh api repos/<owner>/<repo>/tarball/<ref> > src.tgz && mkdir launch-ui && tar -xzf src.tgz -C launch-ui --strip-components=1
# 2. the renderer (a copy of this folder, so that node_modules stay out of the repository)
cp -R <this folder> render && cd render && npm install --ignore-scripts
# 3. the sections, as HTML
node render.mjs ../launch-ui ../html hero cta items faq pricing stats logos                    # launch-ui: section names
node render.mjs ../tailblocks ../html-tb src/blocks/hero/light/a.js src/blocks/feature/light/a.js   # Tailblocks: paths
# 4. on osiris, where the hub's publisher key is: upload the folders there, then
bench --site prod.local execute builder.site_ai.nora.importer.import_launch_ui --kwargs "{'folder': '/home/neoffice/launch-ui-html', 'push': True}"
bench --site prod.local execute builder.site_ai.nora.importer.import_tailblocks --kwargs "{'folder': '/home/neoffice/tailblocks-html', 'push': True}"
```

Nothing is published: the blocks reach the hub as drafts, with the source, its licence and its holder in their notes.
