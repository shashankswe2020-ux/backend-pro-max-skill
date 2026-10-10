"""Build Backend Pro Max vector brand assets.
Outputs into designs/brand/{logo,icons,buttons,illustrations,tokens}.
Text is outlined with fontTools so SVGs don't depend on installed fonts.
Usage: python build_vectors.py <repo_root> <fonts_dir(woff2)>"""
import sys, os, json, re
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
FONTS = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "designs/brand/fonts")
B = os.path.join(ROOT, "designs/brand")
G5, G7, INK, PAPER, AMBER, CORAL = "#22D67A", "#0F8A4C", "#0D1110", "#F3F0E8", "#F2C14A", "#EE6A4E"

def w(path, s):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(s)

def r1(d):  # round coordinates to 1 decimal to keep files small
    return re.sub(r"-?\d+\.\d+", lambda m: f"{float(m.group()):.1f}".rstrip("0").rstrip("."), d)

_fonts = {}
def font(name):
    if name not in _fonts:
        _fonts[name] = TTFont(os.path.join(FONTS, name))
    return _fonts[name]

def text_path(txt, fname, size, x=0, y=0, tracking=0):
    """Return (svg path d, advance width) for txt with baseline at y."""
    f = font(fname); gs = f.getGlyphSet(); cmap = f.getBestCmap()
    upm = f["head"].unitsPerEm; s = size / upm
    pen = SVGPathPen(gs); cx = 0
    for ch in txt:
        g = cmap.get(ord(ch))
        if g is None: continue
        tp = TransformPen(pen, (s, 0, 0, -s, x + cx, y))
        gs[g].draw(tp)
        cx += gs[g].width * s + tracking
    return r1(pen.getCommands()), cx - tracking

# ── Logo mark ─────────────────────────────────────────────────────────
# A prompt caret that resolves into a cited node: "ask → grounded answer".
def mark_inner(c_caret=G5, c_node=G5, c_edge=G5, ring=True):
    return f'''<path d="M18 19 L29 32 L18 45" fill="none" stroke="{c_caret}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M36 44 H44" stroke="{c_edge}" stroke-width="5.5" stroke-linecap="round" opacity=".55"/>
  <circle cx="47" cy="22" r="6" fill="{c_node}"/>
  {'<circle cx="47" cy="22" r="10.5" fill="none" stroke="'+c_node+'" stroke-width="2" opacity=".35"/>' if ring else ''}
  <path d="M41.5 26.5 L33 33" stroke="{c_edge}" stroke-width="2.5" stroke-linecap="round" opacity=".55"/>'''

def mark_svg(bg=INK, **kw):
    tile = f'<rect width="64" height="64" rx="16" fill="{bg}"/>' if bg else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">{tile}\n  {mark_inner(**kw)}\n</svg>\n'

w(f"{B}/logo/mark.svg", mark_svg())
w(f"{B}/logo/mark-paper.svg", mark_svg(bg=PAPER, c_caret=INK, c_node=G7, c_edge=INK))
w(f"{B}/logo/mark-mono.svg", mark_svg(bg=None, c_caret="currentColor", c_node="currentColor", c_edge="currentColor"))

# ── Wordmark: "Backend Pro" (serif) + MAX (mono tag) ─────────────────
def wordmark(fg, tag_bg, tag_fg, with_mark=True, mark_bg=INK, **mk):
    x0 = 84 if with_mark else 0
    d1, adv = text_path("Backend Pro", "instrument-serif-latin-400-normal.woff2", 46, x0, 44)
    tx = x0 + adv + 12
    d2, adv2 = text_path("MAX", "jetbrains-mono-latin-700-normal.woff2", 15, tx + 9, 35.5, tracking=1.5)
    tw = adv2 + 18; W = int(tx + tw + 2)
    m = f'<g>{"<rect width=\"64\" height=\"64\" rx=\"16\" fill=\"" + mark_bg + "\"/>" if mark_bg else ""}{mark_inner(**mk)}</g>' if with_mark else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} 64" width="{W}" height="64">{m}'
            f'<path d="{d1}" fill="{fg}"/><rect x="{tx:.1f}" y="17" width="{tw:.1f}" height="25" rx="6" fill="{tag_bg}"/>'
            f'<path d="{d2}" fill="{tag_fg}"/></svg>\n')

w(f"{B}/logo/wordmark-dark.svg", wordmark(PAPER, G5, INK, mark_bg="#1A201D"))
w(f"{B}/logo/wordmark-light.svg", wordmark("#141714", INK, G5))
w(f"{B}/logo/wordmark-text-only.svg", wordmark("#141714", INK, G5, with_mark=False))

# ── Icons: 24px, 1.75 stroke, round caps, currentColor ───────────────
I = {
 "search":   '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
 "compare":  '<rect x="3" y="4" width="7.5" height="16" rx="1.5"/><rect x="13.5" y="4" width="7.5" height="16" rx="1.5"/><path d="M6 9h2M6 13h2M16.5 9h2M16.5 13h2"/>',
 "repl":     '<rect x="3" y="4" width="18" height="16" rx="2.5"/><path d="M7 10l3 2.5L7 15M12.5 15H17"/>',
 "freshness":'<circle cx="12" cy="13" r="7.5"/><path d="M12 9v4l2.5 2M9.5 3h5"/>',
 "confidence":'<path d="M4 18a8 8 0 0 1 16 0"/><path d="M12 18l4.5-5.5"/><circle cx="12" cy="18" r="1.2"/>',
 "synonym":  '<path d="M4 8h12l-3-3M20 16H8l3 3"/>',
 "cache":    '<path d="M13 3L5 13.5h6L10 21l8-10.5h-6z"/>',
 "validator":'<path d="M4 5h16M4 10h10M4 15h7"/><path d="M14 17l2.5 2.5L21 15"/>',
 "tests":    '<path d="M9 3h6M10 3v6.5L4.8 18.2A1.8 1.8 0 0 0 6.4 21h11.2a1.8 1.8 0 0 0 1.6-2.8L14 9.5V3"/><path d="M7.5 15h9"/>',
 "intent":   '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r=".6"/>',
 "hybrid":   '<circle cx="6" cy="6" r="2.5"/><circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="12" r="2.5"/><path d="M8.3 7.2l7.4 3.6M8.3 16.8l7.4-3.6"/>',
 "rerank":   '<path d="M7 20V4M7 4L4 7M7 4l3 3"/><path d="M13 6h7M13 11h5M13 16h3"/>',
 "decide":   '<path d="M12 3v6M12 9l-6 6v6M12 9l6 6v6"/><circle cx="18" cy="15" r="1.4"/>',
 "adr":      '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 16h4"/>',
 "design-doc":'<path d="M3 20h18M5 20V9l7-5 7 5v11"/><path d="M9.5 20v-6h5v6"/>',
 "citation": '<path d="M10 14l4-4"/><path d="M8.5 11.5L6 14a3 3 0 0 0 4.2 4.2l2.5-2.5M15.5 12.5L18 10a3 3 0 0 0-4.2-4.2l-2.5 2.5"/>',
 "conflict": '<path d="M12 3.5L2.8 19.5h18.4z"/><path d="M12 10v4M12 17v.2"/>',
 "dedup":    '<rect x="3" y="3" width="12" height="12" rx="2"/><rect x="9" y="9" width="12" height="12" rx="2"/>',
 "coverage": '<path d="M4 20V10M10 20V4M16 20v-7M20 20H3"/>',
 "mcp":      '<path d="M9 3v5M15 3v5M6 8h12v3a6 6 0 0 1-12 0z"/><path d="M12 17v4"/>',
 "brain":    '<path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 6 1V5a2 2 0 0 0-3-1z"/><path d="M15 4a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-6 1"/>',
 "github":   '<path d="M9 19c-4 1.3-4-2-6-2.5M15 21v-3.5a3 3 0 0 0-.9-2.4c2.9-.3 6-1.4 6-6.4a5 5 0 0 0-1.4-3.5 4.6 4.6 0 0 0-.1-3.5s-1.1-.3-3.6 1.4a12.4 12.4 0 0 0-6.4 0C6.1 1.4 5 1.7 5 1.7a4.6 4.6 0 0 0-.1 3.5A5 5 0 0 0 3.5 8.7c0 5 3.1 6.1 6 6.4a3 3 0 0 0-.9 2.4V21"/>',
 "copy":     '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
 "arrow-right":'<path d="M4 12h15M14 6l6 6-6 6"/>',
 "check":    '<path d="M4.5 12.5l5 5L19.5 7"/>',
 "x":        '<path d="M6 6l12 12M18 6L6 18"/>',
 "terminal": '<path d="M4 7l5 5-5 5M12 18h8"/>',
 "shield":   '<path d="M12 3l7.5 3v6c0 4.5-3.2 7.8-7.5 9-4.3-1.2-7.5-4.5-7.5-9V6z"/><path d="M9 12l2 2 4-4"/>',
}
def icon(body, size=24):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" '
            f'stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">{body}</svg>\n')
for k, v in I.items():
    w(f"{B}/icons/{k}.svg", icon(v))
json.dump({k: v for k, v in I.items()}, open(f"{B}/icons/icons.json", "w"), indent=1)

# Icon sheet
cols = 8; cell = 96; rows = -(-len(I) // cols)
items = []
for n, (k, v) in enumerate(I.items()):
    cx, cy = (n % cols) * cell, (n // cols) * cell
    lbl, lw = text_path(k, "jetbrains-mono-latin-400-normal.woff2", 9, 0, 0)
    items.append(f'<g transform="translate({cx+30},{cy+20}) scale(1.5)" fill="none" stroke="{INK}" stroke-width="1.75" '
                 f'stroke-linecap="round" stroke-linejoin="round">{v}</g>'
                 f'<path transform="translate({cx + (cell-lw)/2:.1f},{cy+80})" d="{lbl}" fill="#7C807A"/>')
w(f"{B}/icons/_sheet.svg",
  f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {cols*cell} {rows*cell}" width="{cols*cell}" height="{rows*cell}">'
  f'<rect width="100%" height="100%" fill="{PAPER}"/>{"".join(items)}</svg>\n')

# ── Embed / badge buttons (for READMEs) — 4 styles ───────────────────
def badge(name, bg, fg, border, label="Grounded by", value="Backend Pro Max", mk=None):
    d1, a1 = text_path(label, "inter-tight-latin-500-normal.woff2", 12.5, 40, 22.5)
    d2, a2 = text_path(value, "inter-tight-latin-700-normal.woff2", 12.5, 40 + a1 + 6, 22.5)
    W = int(40 + a1 + 6 + a2 + 14)
    mk = mk or {}
    m = f'<g transform="translate(9,5) scale(.39)">{mark_inner(**mk)}</g>'
    w(f"{B}/buttons/{name}.svg",
      f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} 34" width="{W}" height="34">'
      f'<rect x=".5" y=".5" width="{W-1}" height="33" rx="9" fill="{bg}" stroke="{border}"/>{m}'
      f'<path d="{d1}" fill="{fg}" opacity=".7"/><path d="{d2}" fill="{fg}"/></svg>\n')
badge("badge-ink", INK, PAPER, "#2A322E")
badge("badge-paper", PAPER, "#141714", "#D3CBB9", mk=dict(c_caret=INK, c_node=G7, c_edge=INK))
badge("badge-green", G5, INK, G7, mk=dict(c_caret=INK, c_node=INK, c_edge=INK))
badge("badge-outline", "none", "#141714", "#141714", mk=dict(c_caret=INK, c_node=G7, c_edge=INK))

# ── Illustrations ────────────────────────────────────────────────────
w(f"{B}/illustrations/glow-blob.svg", f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="800" height="600">
<defs><radialGradient id="g" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="{G5}" stop-opacity=".55"/>
<stop offset=".45" stop-color="{G5}" stop-opacity=".16"/><stop offset="1" stop-color="{G5}" stop-opacity="0"/></radialGradient>
<filter id="b"><feGaussianBlur stdDeviation="30"/></filter></defs>
<ellipse cx="400" cy="300" rx="360" ry="250" fill="url(#g)" filter="url(#b)"/></svg>\n''')

# Section rule with severity ticks
ticks = "".join(f'<rect x="{i*12}" y="{8 if i%5 else 2}" width="1.5" height="{8 if i%5 else 14}" fill="#D3CBB9"/>' for i in range(100))
w(f"{B}/illustrations/divider-ruler.svg",
  f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 20" width="1200" height="20" preserveAspectRatio="none">{ticks}</svg>\n')

# Assistant-client stack (Claude Code, Cursor, Windsurf, Copilot, Continue, CLI) as monogram chips
clients = [("CC", "#D97757"), ("Cu", "#141714"), ("Ws", "#0B6E79"), ("Co", "#6E40C9"), ("Ct", "#1F6FEB"), ("$_", G7)]
chips = []
for i, (t, c) in enumerate(clients):
    d, a = text_path(t, "jetbrains-mono-latin-700-normal.woff2", 11.5, 0, 0)
    cx = 22 + i * 30
    chips.append(f'<circle cx="{cx}" cy="22" r="20" fill="{c}" stroke="{PAPER}" stroke-width="3"/>'
                 f'<path transform="translate({cx - a/2:.1f},26)" d="{d}" fill="#fff"/>')
w(f"{B}/illustrations/client-stack.svg",
  f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {44+5*30} 44" width="{44+5*30}" height="44">{"".join(chips)}</svg>\n')

# Favicon
w(f"{B}/logo/favicon.svg", mark_svg())

# ── tokens.json from tokens.css ──────────────────────────────────────
css = open(f"{B}/tokens/tokens.css").read()
toks = dict(re.findall(r"--([\w-]+):\s*([^;]+);", css))
out = {"color": {}, "font": {}, "size": {}, "space": {}, "radius": {}, "shadow": {}, "other": {}}
for k, v in toks.items():
    g = ("color" if v.startswith("#") or v.startswith("var(") else
         "font" if k.startswith("font") else "size" if k.startswith(("fs", "lh", "tracking")) else
         "space" if k.startswith("s-") else "radius" if k.startswith("r-") else
         "shadow" if k.startswith("sh") else "other")
    out[g][k] = v.strip()
json.dump(out, open(f"{B}/tokens/tokens.json", "w"), indent=2)
print("vectors ok:", len(I), "icons")
