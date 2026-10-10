# backendpro.cc — redesign kit (Oct 2026)

**Direction: “Field manual & observatory.”** Everything you *read* lives on warm paper with an editorial serif. The brain lives in a dark observatory panel, and it stays the hero. The site's green (`#22D67A`) remains the signal colour. The redesign aims to read as staff-engineer judgement rather than as a hacker side-project.

- **Prototype:** `designs/redesign/landing.html`. Serve the repo root (`python -m http.server`) and open `/designs/redesign/landing.html`. The brain needs HTTP because it fetches `brain.glb`.
- **Preview:** `designs/redesign/preview-full.jpg`
- **Figma:** https://www.figma.com/design/fHnLnjygf2YNS9b2HrQC7i. Pages: Foundations (variables, text/effect styles, logo, 28 icon components, Button set, Install pill, Domain card), Assets, Landing (1440 desktop).

---

## 1. Brain: preserved

The three.js scene is preserved from the original site: same `brain.glb`, same `vault-graph.js` data (685 nodes · 1,405 edges · 46 legend groups), bloom, orbit controls, hover tooltip, click-to-highlight, legend toggles, Auto/Reset. It lives in `designs/redesign/brain-module.html` and is inlined by the build script. The graph caption calls the 46 groups “domain / stack groups”, not domains.

There are two additive changes, and neither alters the visuals:

1. `loader.load(window.BRAIN_URL || './brain.glb')`, so the page can sit in any folder.
2. A small hook, `window.brainFocus(ids)` / `window.brainReset()`. It reuses the existing click-highlight logic so the new **"ask the brain"** box can light up matching rows plus their cross-domain edges. Type `saga` and Outbox, Saga and Process Manager glow, wired to their neighbours.

## 2. Competitive audit

Rival benchmark: **Context7** (Upstash), the best-known "ground your AI" MCP. I couldn't load its live page from this session, so this column reflects its public positioning (up-to-date library docs for LLMs, delivered over MCP) rather than a pixel audit.

| Rival does | backendpro.cc today | Redesign move |
|---|---|---|
| One-sentence promise; install in the hero | Headline “Backend Pro Max Design Intelligence” is ambiguous ("design"?). Install appears only in the terminal mock | **“Staff-engineer judgement, *cited.*”** plus a copyable `pip install backendpro` pill above the fold |
| Shows the product doing its job | Brain is impressive but passive: you can hover, not ask | **Ask the brain**: type a concept and matching rows light up with their links. Brain stays the centrepiece |
| Clear "what it is vs. what it isn't" | Real differentiator (100% sourced, dated, CI-audited rows) buried in tool card #14 | Dedicated dark **Provenance ledger** section: a sample row card with source, type, date and severity, plus the validate / freshness / conflicts trio |
| Before/after value | None | **Same question. Different reviewer.** Plain-LLM answer vs. grounded answer |
| Decision support | `decide` shown as static terminal text | Interactive **decide widget** (facet toggles re-rank candidates; labelled illustrative) |
| Scannable breadth | 35 domain cards + 17 tool cards, all same weight, emoji/CDN icons | Index-card **catalogue** with live filter; 16 tools in a quiet ruled grid with a consistent icon set |
| Per-client install | 7 equal cards | **Tabbed installer** (Claude Code · Cursor · Windsurf · Copilot · Continue · CLI/MCP) with copy buttons |
| Community / spread | “⭐ the repo” line only | **README badges** (4 styles) plus copy-ready Markdown, so every user who adds one links back |
| SEO comparison pages | None | Footer **Compare** column (vs Context7, vs plain LLM, vs system-design wikis), marked *page soon* |
| FAQ | None | 6 FAQs answering the review objections (network? cost? staleness? vs Context7?) |

**Bugs on the live site, fixed in the prototype:**
- The footer says “20 Domains” while the page says 35.
- The favicon is an emoji.
- Lucide icons load from `@latest`, which is unpinned.
- `decide` reuses the brain icon.
- The legend says 46 “domains” where the copy says 35. The legend counts stack groups too, so the copy now says “cross-domain links” instead.

## 3. Asset inventory

| Path | What | Source |
|---|---|---|
| `designs/brand/3d/{drawer,cube,keycap}.{png,webp}` | Card-catalog drawer (provenance) · glass MCP cube (MCP/CTA) · `>_` keycap (workflow). Transparent, soft shadow | Blender 5.2 (bpy, Cycles CPU, AgX) — `designs/blender/scene.py` |
| `designs/brand/video/mcp-cube-loop.{mp4,webm}` + `mcp-cube-poster.jpg` | 10s ping-pong loop of the cube, 1280×720, silent | Runway Seedance 2 Fast (image-to-video from the cube render) + ffmpeg |
| `designs/brand/photo/desk-{diagram,notebook}.{jpg,webp}` | Editorial desk still-lifes echoing the 3D objects | Runway Nano Banana Pro |
| `designs/brand/logo/*` | Mark (prompt caret → cited node), wordmark light/dark/text-only, mono mark, favicon svg/32px | `designs/scripts/build_vectors.py` (text outlined; no font dependency) |
| `designs/brand/icons/*.svg`, `icons.json`, `_sheet.svg` | 28 icons, 24px, 1.75 stroke, `currentColor` | same |
| `designs/brand/buttons/badge-{ink,green,paper,outline}.svg` | “Grounded by Backend Pro Max” README badges | same |
| `designs/brand/illustrations/*` | Glow blob, ruler divider, client avatar stack | same |
| `designs/brand/social/og.png`, `app-icon-{180,512,1024}.png` | 1200×630 OG card, app icons | Playwright render |
| `designs/brand/tokens/tokens.{css,json}` | Colour ramps, type, space, radius, shadow tokens | hand-written → JSON by script |
| `designs/brand/fonts/*.woff2` | Instrument Serif, Inter Tight, JetBrains Mono (OFL) | @fontsource |

## 4. Tokens (summary)

- **Green** 50 `#E7FAF0` · 100 `#BDF2D5` · 300 `#63E3A0` · **500 `#22D67A`** · 700 `#0F8A4C` · 900 `#0A4A2A`
- **Ink** 950 `#07090A` · 900 `#0D1110` · 800 `#151A18` · 700 `#222825` · 500 `#4A524E` · 300 `#8A928D`
- **Paper** `#F3F0E8` / `#EBE6DA` / `#E0D9CA`, rule `#D3CBB9`, text `#141714` / `#4F544F` / `#7C807A`
- **Accents / severity:** amber `#F2C14A` (HIGH) · coral `#EE6A4E` (CRITICAL) · blue `#5B9CF6` · violet `#A78BFA`
- **Type:** Instrument Serif (display, italic for the green emphasis word) · Inter Tight (UI) · JetBrains Mono (labels, code). Figma uses Inter for UI because Inter Tight isn't installed there.
- **Space** 4-px base (4 → 144). **Radius:** 4 / 8 / 14 / 22 / pill.

## 5. Shipping it

The live site is a static [`sites/index.html`](../sites/index.html). Build it from
the canonical template and assets (no manual path replacement):

```bash
python3 designs/scripts/build_landing.py . --site
python3 -m http.server 8000 --directory sites
# Open http://localhost:8000/
```

The `--site` build copies `designs/brand/` into `sites/brand/` and writes the page
with site-relative asset URLs. It leaves `sites/brain.glb` and
`sites/vault-graph.js` untouched. Deploy the **entire `sites/` directory**.
Without `--site`, the command still builds only the prototype. Both commands
also work without a repo-root argument, from any working directory.

Edit `designs/scripts/landing.template.html`, `designs/redesign/brain-module.html`,
or `designs/brand/`, then regenerate both pages rather than editing generated HTML.
The font files are local; three.js, anime.js and stack icons still require CDN
access. Clipboard buttons require HTTPS or localhost and report copy failures.
The closing CTA includes a “Buy me a coffee” button linking directly to
https://buymeacoffee.com/shashanksw9, without a third-party widget or script.

The OG meta already points to `https://backendpro.cc/brand/social/og.png`.

If the site later moves to Next.js, `designs/brand` is already laid out for it:

```tsx
<Image src="/brand/3d/drawer.webp" width={947} height={702} alt="Card-catalog drawer" />
<video autoPlay muted loop playsInline poster="/brand/video/mcp-cube-poster.jpg">
  <source src="/brand/video/mcp-cube-loop.webm" type="video/webm" />
  <source src="/brand/video/mcp-cube-loop.mp4" type="video/mp4" />
</video>
```

## 6. Regenerate

```bash
pip install bpy fonttools brotli pillow playwright
python designs/scripts/build_vectors.py . designs/brand/fonts
python designs/blender/scene.py drawer /tmp/drawer.png 1000 40   # also: cube, keycap
python designs/scripts/postprocess_renders.py /tmp/drawer.png designs/brand/3d
python designs/scripts/build_landing.py .
```

## 7. Placeholders and caveats

- **Agensi installs:** the hero's “44+ installs” links to the [Agensi listing](https://www.agensi.io/skills/backend-pro-max), which showed 44 installs on 2026-10-10. This is a manually maintained milestone, not a live counter or a count of PyPI downloads.
- **Illustrative, not real data:** the row card's ID (`row 0412`) and the decide widget's scores are labelled *illustrative* on the page. The figures 685, 1,405, 652, 239, 35, 12 and 6 come from the current site and repo.
- **Compare pages** in the footer don't exist yet (*page soon*).
- **Figma images:** the Plugin API can't fetch files here, so image slots are labelled frames (`IMAGE · designs/brand/...`). Drag the files in. The brain stage is labelled as the live WebGL embed.
- Blender renders were made in the cloud with bpy (not your local Blender); `.blend` files are in `designs/blender/`.
- The MCP loop has a slight camera drift; the ping-pong edit keeps it seamless.
- Stack logos still come from devicons via jsDelivr (pinned to `v2.16.0`).
