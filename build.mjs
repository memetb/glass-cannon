// Builds dist/ from content/site.md + src/index.html.
// Tailwind runs afterwards (see package.json "build").
import { readFileSync, writeFileSync, mkdirSync, rmSync, cpSync, existsSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, extname } from "node:path";
import { Marked } from "marked";
import markedKatex from "marked-katex-extension";

const require = createRequire(import.meta.url);
const pkgDir = name => dirname(require.resolve(`${name}/package.json`));
const OUT = "dist";
const CONTENT = "content";
const CARD_META_KEYS = new Set(["kicker", "tags"]);
// ![alt](src "optional caption") alone on a line
const IMAGE_LINE = /^!\[([^\]]*)\]\(\s*<?([^\s>)]+)>?(?:\s+"([^"]*)")?\s*\)\s*$/;
const isExternal = src => /^([a-z][a-z0-9+.-]*:|\/\/)/i.test(src);

const md = new Marked({ gfm: true }).use(markedKatex({ throwOnError: false }));

const warn = msg => console.warn(`warn: ${msg}`);

function parseFrontMatter(src) {
  const m = src.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?/);
  if (!m) return { meta: {}, rest: src };
  const meta = {};
  for (const line of m[1].split(/\r?\n/)) {
    if (!line.trim() || line.trim().startsWith("#")) continue;
    const i = line.indexOf(":");
    if (i < 0) { warn(`front matter: ignoring "${line}"`); continue; }
    meta[line.slice(0, i).trim()] = line.slice(i + 1).trim().replace(/^(["'])(.*)\1$/, "$2");
  }
  return { meta, rest: src.slice(m[0].length) };
}

const slugify = s => s.toLowerCase().replace(/<[^>]+>/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "card";

function parseCard(chunk, ids) {
  const lines = chunk.split(/\r?\n/);
  const title = lines.shift().replace(/^##\s+/, "").trim();
  const card = { title: md.parseInline(title), kicker: "", tags: [], aside: null, quote: null, image: null };

  let i = 0;
  const skipBlank = () => { while (i < lines.length && !lines[i].trim()) i++; };

  // meta lines (only known keys, so a body line like "Note: ..." isn't swallowed)
  skipBlank();
  for (let m; i < lines.length && (m = lines[i].match(/^(\w+):\s*(.*)$/)) && CARD_META_KEYS.has(m[1].toLowerCase()); i++) {
    const [, k, v] = m;
    if (k.toLowerCase() === "tags") card.tags = v.split(",").map(t => t.trim()).filter(Boolean);
    else card.kicker = v.trim();
  }

  // optional aside: a leading blockquote (pull-quote) OR a leading image line
  skipBlank();
  const img = i < lines.length && lines[i].trim().match(IMAGE_LINE);
  if (img) {
    i++;
    const [, alt, src, caption] = img;
    if (!isExternal(src) && !existsSync(join(CONTENT, src.replace(/^\//, ""))))
      warn(`card "${title}": image not found: ${join(CONTENT, src)}`);
    card.image = { src: src.replace(/^\//, ""), alt, caption: caption ? md.parseInline(caption) : "" };
    card.aside = "image";
  } else {
    const q = [];
    while (i < lines.length && /^\s*>/.test(lines[i])) q.push(lines[i++].replace(/^\s*>\s?/, ""));
    const quote = q.join(" ").replace(/\s+/g, " ").trim();
    if (quote) { card.quote = md.parseInline(quote); card.aside = "quote"; }
  }

  card.body = md.parse(lines.slice(i).join("\n").trim());

  let id = slugify(title), n = 2;
  while (ids.has(id)) id = `${slugify(title)}-${n++}`;
  ids.add(id);
  card.id = id;
  if (!card.title) warn(`card "${id}" has an empty title`);
  return card;
}

function parseSite(src) {
  const { meta, rest } = parseFrontMatter(src);
  const chunks = rest.split(/^(?=##\s)/m);
  if (chunks.length && !/^##\s/.test(chunks[0])) {
    const pre = chunks.shift().replace(/<!--[\s\S]*?-->/g, "").trim();
    if (pre) warn("content before the first '## ' heading is ignored");
  }
  const ids = new Set(["hero", "end"]);
  const cards = chunks.map(c => parseCard(c, ids));
  if (!cards.length) warn("no cards found");
  return {
    title: meta.title ?? "Untitled",
    eyebrow: meta.eyebrow ?? "",
    headline: md.parseInline(meta.headline ?? ""),
    byline: md.parseInline(meta.byline ?? ""),
    footer: md.parseInline(meta.footer ?? ""),
    repo: meta.repo ?? "",
    description: meta.description ?? meta.headline ?? "",
    cards,
  };
}

const escAttr = s => String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
// Safe inside <script type="application/json">
const jsonForScript = o => JSON.stringify(o).replace(/</g, "\\u003c").replace(/\u2028/g, "\\u2028").replace(/\u2029/g, "\\u2029");

const site = parseSite(readFileSync("content/site.md", "utf8"));
const html = readFileSync("src/index.html", "utf8")
  .replaceAll("%TITLE%", escAttr(site.title))
  .replaceAll("%DESCRIPTION%", escAttr(site.description))
  .replace("%CONTENT_JSON%", () => jsonForScript(site));

rmSync(OUT, { recursive: true, force: true });
mkdirSync(join(OUT, "vendor"), { recursive: true });
writeFileSync(join(OUT, "index.html"), html);
cpSync("src/_headers", join(OUT, "_headers"));
// content assets (images etc.) keep their paths relative to content/
cpSync(CONTENT, OUT, { recursive: true, filter: f => extname(f).toLowerCase() !== ".md" });
cpSync(join(pkgDir("vue"), "dist/vue.global.prod.js"), join(OUT, "vendor/vue.global.prod.js"));
cpSync(join(pkgDir("katex"), "dist/katex.min.css"), join(OUT, "vendor/katex/katex.min.css"));
cpSync(join(pkgDir("katex"), "dist/fonts"), join(OUT, "vendor/katex/fonts"), { recursive: true });

console.log(`built ${OUT}/index.html — ${site.cards.length} cards (${site.cards.filter(c => c.quote).length} quotes, ${site.cards.filter(c => c.image).length} images)`);
