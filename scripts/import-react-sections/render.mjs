//// Neoffice — added file (no upstream equivalent): renders sections written as React components (launch-ui, Tailblocks: MIT) to static HTML.
// Usage: node render.mjs <checkout> <output folder> <entry> [<entry>…]
//   launch-ui: an entry is a section name (hero cta items faq pricing stats logos), read at components/sections/<name>/default.tsx
//   anything else (Tailblocks): an entry is a path in the checkout, `src/blocks/hero/light/a.js`; the page is `<folder>/src__blocks__hero__light__a.html`
//
// launch-ui is a library of sections written as React components (words and pictures in the props' defaults, classes built by class-variance-authority
// and tailwind-merge). To read one as a block (builder/site_ai/nora/importer.py), its own components are run, as written, and their markup is kept:
// the words and the classes are the ones of the source. Three modules are replaced by what the markup needs: Next's link and image (an <a>, an <img>)
// and Radix's accordion (a <details> and its <summary>, which is what a folding question is in a block).
import { build } from "esbuild";
import path from "node:path";
import fs from "node:fs";
import { pathToFileURL } from "node:url";

const here = path.dirname(new URL(import.meta.url).pathname);
const [checkout, outFolder, ...sections] = process.argv.slice(2);
if (!checkout || !outFolder || !sections.length) {
  console.error(
    "usage: node render.mjs <launch-ui checkout> <output folder> <section> [<section>…]",
  );
  process.exit(2);
}
const src = path.resolve(checkout);
const html = path.resolve(outFolder);
const work = path.join(here, ".render");
fs.mkdirSync(work, { recursive: true });
fs.mkdirSync(html, { recursive: true });

const SHIMS = {
  "next/link": `import React from "react"; export default function Link({ href, children, ...rest }) { return React.createElement("a", { href: typeof href === "string" ? href : "#", ...rest }, children); }`,
  "next/image": `import React from "react"; export default function Image({ src, alt, width, height, className, loading }) { return React.createElement("img", { src, alt, width, height, className, loading }); }`,
  "@radix-ui/react-accordion": `import React from "react";
const tag = (name, drop = []) => React.forwardRef(function Part({ children, ...rest }, ref) { for (const k of drop) delete rest[k]; return React.createElement(name, { ref, ...rest }, children); });
export const Root = tag("div", ["type", "collapsible", "defaultValue", "value", "onValueChange"]);
export const Item = tag("details", ["value", "disabled"]);
export const Header = ({ children }) => React.createElement(React.Fragment, null, children);
export const Trigger = tag("summary");
export const Content = tag("div", ["forceMount"]);`,
};

const shims = {
  name: "shims",
  setup(b) {
    b.onResolve(
      { filter: /^(next\/link|next\/image|@radix-ui\/react-accordion)$/ },
      (a) => ({ path: a.path, namespace: "shim" }),
    );
    b.onLoad({ filter: /.*/, namespace: "shim" }, (a) => ({
      contents: SHIMS[a.path],
      loader: "jsx",
      resolveDir: here,
    }));
    b.onResolve({ filter: /^@\// }, async (a) => {
      const r = await b.resolve("./" + a.path.slice(2), {
        resolveDir: src,
        kind: a.kind,
      });
      return r.errors.length ? { errors: r.errors } : { path: r.path };
    });
  },
};

for (const name of sections) {
  // a path in the checkout (Tailblocks: a component with a `theme` prop) or a launch-ui section
  const isPath = name.includes("/");
  const file = path.join(
    work,
    `${isPath ? name.replace(/\.[a-z]+$/, "").replaceAll("/", "__") : name}.mjs`,
  );
  const source = isPath
    ? path.join(src, name)
    : path.join(src, "components/sections", name, "default.tsx");
  const props = isPath ? '{ theme: "indigo" }' : "null";
  // React is bundled with the section, so that the section and the renderer share one copy of it
  const entry = `import React from "react"; import { renderToStaticMarkup } from "react-dom/server"; import C from ${JSON.stringify(source)}; export default () => renderToStaticMarkup(React.createElement(C, ${props}));`;
  await build({
    stdin: { contents: entry, resolveDir: here, loader: "jsx" },
    bundle: true,
    platform: "node",
    format: "esm",
    outfile: file,
    jsx: "automatic",
    logLevel: "error",
    loader: { ".js": "jsx" },
    nodePaths: [path.join(here, "node_modules")],
    plugins: [shims],
    define: { "process.env.NODE_ENV": '"production"' },
    banner: {
      js: "import { createRequire } from 'module'; const require = createRequire(import.meta.url);",
    },
  });
  const markup = (await import(pathToFileURL(file).href)).default();
  const out = isPath
    ? name.replace(/\.[a-z]+$/, "").replaceAll("/", "__")
    : name;
  fs.writeFileSync(
    path.join(html, `${out}.html`),
    `<!doctype html><html><head><meta charset="utf-8"></head><body>${markup}</body></html>\n`,
  );
  console.log(out, markup.length, "characters");
}
