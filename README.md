# glass-cannon
Project Glass Cannon

## Website

All copy lives in [`content/site.md`](content/site.md). `npm run build` turns it into a static site in `dist/`.

```
content/site.md   ← edit this
src/index.html    ← page template (Vue 3, reads the content as JSON)
src/styles.css    ← Tailwind v4 entry + custom styles
build.mjs         ← md → dist/index.html, copies vendor assets
```

### Content format

Front matter sets the hero/footer: `title`, `eyebrow`, `headline`, `byline`, `description`, `footer`, `repo`.

Each `## Heading` starts a card:

```markdown
## Card title
kicker: Thesis            ← optional
tags: offense, verification  ← optional

> Optional pull-quote shown beside the card

Card body — any Markdown. Inline math $P \neq NP$, display math:

$$ \exists w : V(x, w) = 1 $$
```

Meta lines must come directly after the heading; the pull-quote must be the first thing after them. Both are optional.

### Commands

```bash
npm install
npm run build     # → dist/
npm run preview   # http://localhost:8080
```

### Cloudflare Pages

- Build command: `npm run build`
- Build output directory: `dist`
