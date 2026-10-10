"""Build the prototype, or use --site to publish it and its assets into sites/."""

import argparse
import json
import re
import shutil
from pathlib import Path


def build(root: Path, site: bool = False) -> Path:
    designs = root / "designs"
    template = (designs / "scripts/landing.template.html").read_text(encoding="utf-8")
    icons = json.loads((designs / "brand/icons/icons.json").read_text(encoding="utf-8"))

    def svg(match: re.Match) -> str:
        return (
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" '
            f'stroke-linecap="round" stroke-linejoin="round">{icons[match.group(1)]}</svg>'
        )

    template = re.sub(r"\{\{I:([\w-]+)\}\}", svg, template)
    template = template.replace("{{ICONS_JSON}}", json.dumps(icons))
    template = template.replace(
        "{{BRAIN_MODULE}}",
        (designs / "redesign/brain-module.html").read_text(encoding="utf-8"),
    )
    media = (
        '<video autoplay muted loop playsinline preload="metadata" poster="{{B}}/video/mcp-cube-poster.jpg">'
        '<source src="{{B}}/video/mcp-cube-loop.webm" type="video/webm">'
        '<source src="{{B}}/video/mcp-cube-loop.mp4" type="video/mp4"></video>'
    )
    template = template.replace("{{MCP_MEDIA}}", media)
    template = template.replace("{{B}}", "brand" if site else "../brand")
    template = template.replace("{{SITES}}", "." if site else "../../sites")
    output = root / "sites/index.html" if site else designs / "redesign/landing.html"
    if site:
        shutil.copytree(designs / "brand", root / "sites/brand", dirs_exist_ok=True)
    output.write_text(template, encoding="utf-8")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_root", nargs="?", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--site", action="store_true", help="Build sites/index.html and copy brand assets")
    args = parser.parse_args()
    print(build(args.repo_root, args.site))
