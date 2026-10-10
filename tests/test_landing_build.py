"""The prototype and published landing page share one reproducible build."""

import ast
import csv
import json
import re
import shutil
import subprocess
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from core import CSV_CONFIG

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "designs/scripts/build_landing.py"


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.ids = []
        self.links = []
        self.tags = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append(tag)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
        self.urls.extend(attrs[key] for key in ("src", "poster") if key in attrs)
        if tag == "link" and attrs.get("rel") in {"stylesheet", "icon", "apple-touch-icon"}:
            self.urls.append(attrs["href"])


@pytest.mark.parametrize("site", [False, True])
def test_landing_build(tmp_path, site):
    shutil.copytree(ROOT / "designs", tmp_path / "designs", ignore=shutil.ignore_patterns("blender"))
    shutil.copytree(ROOT / "sites", tmp_path / "sites", ignore=shutil.ignore_patterns("brand"))
    preserved = {name: (tmp_path / "sites" / name).read_bytes() for name in ("brain.glb", "vault-graph.js")}
    prototype = tmp_path / "designs/redesign/landing.html"
    original_prototype = prototype.read_bytes()
    command = [sys.executable, str(BUILDER), str(tmp_path)] + (["--site"] if site else [])
    subprocess.run(command, check=True, capture_output=True, text=True)
    output = tmp_path / "sites/index.html" if site else prototype
    html = output.read_text(encoding="utf-8")
    assert not re.search(r"\{\{[A-Z_]+(?::[\w-]+)?\}\}", html)
    parser = AssetParser()
    parser.feed(html)
    assert len(parser.ids) == len(set(parser.ids))
    for link in parser.links:
        if link.startswith("#") and link != "#":
            assert link[1:] in parser.ids, link
    assert "video" not in parser.tags
    assert not any("/3d/" in url or "/photo/" in url for url in parser.urls)
    assert "https://www.agensi.io/skills/backend-pro-max" in parser.links
    assert "https://buymeacoffee.com/shashanksw9" in parser.links
    for url in parser.urls:
        if not urlsplit(url).scheme and not url.startswith("//"):
            assert (output.parent / url).is_file(), url
    brain_url = re.search(r"window\.BRAIN_URL='([^']+)'", html).group(1)
    assert (output.parent / brain_url).is_file()
    for name, content in preserved.items():
        assert (tmp_path / "sites" / name).read_bytes() == content
    if site:
        assert prototype.read_bytes() == original_prototype
        assert "../../sites" not in html
        assert "../brand" not in html
        for source in (tmp_path / "designs/brand").rglob("*"):
            if source.is_file():
                target = tmp_path / "sites/brand" / source.relative_to(tmp_path / "designs/brand")
                assert target.read_bytes() == source.read_bytes()
    else:
        assert not (tmp_path / "sites/brand").exists()
    tokens = output.parent / ("brand" if site else "../brand") / "tokens/tokens.css"
    for url in re.findall(r'url\("([^"]+)"\)', tokens.read_text(encoding="utf-8")):
        assert (tokens.parent / url).is_file(), url
    subprocess.run(command, check=True, capture_output=True, text=True)
    assert output.read_text(encoding="utf-8") == html


def test_landing_catalogue_matches_registered_domains():
    template = (ROOT / "designs/scripts/landing.template.html").read_text(encoding="utf-8")
    domains = json.loads(re.search(r"const DOMAINS=(\[.*?\]);", template, re.DOTALL).group(1))
    names = [entry[0] for entry in domains]
    assert len(names) == len(set(names))
    assert set(names) == set(CSV_CONFIG)
    assert f"Browse {len(names)} domains" in template
    assert f"{len(names)} / {len(names)} domains" in template


def test_landing_example_matches_knowledge_base():
    template = (ROOT / "designs/scripts/landing.template.html").read_text(encoding="utf-8")
    excerpt = re.search(r'<article class="rowcard".*?</article>', template, re.DOTALL).group(0)
    excerpt = unescape(excerpt)
    with (ROOT / "src/backend-pro-max/data/reliability.csv").open(encoding="utf-8", newline="") as source:
        row = next(row for row in csv.DictReader(source) if row["Topic"] == "Retries with backoff + budget")
    for field in ("Topic", "Mitigation", "Do", "Don't", "Source URL", "Source Type", "Last Updated"):
        assert row[field] in excerpt, field


def test_landing_mcp_setup_matches_package():
    template = (ROOT / "designs/scripts/landing.template.html").read_text(encoding="utf-8")
    block = re.search(r'<div class="cfg">(.*?)</div>', template, re.DOTALL).group(1)
    plain = unescape(re.sub(r"<[^>]+>", "", block))
    config = json.loads("\n".join(line for line in plain.splitlines() if not line.strip().startswith("//")))
    server = config["mcpServers"]["backendpro"]
    assert server == {"command": "backendpro-mcp"}
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'backendpro-mcp = "backendpro.scripts.mcp_server:main"' in project
    clients = json.loads(re.search(r"const CLIENTS=(\[.*?\]);", template, re.DOTALL).group(1))
    commands = next(commands for name, _, commands in clients if name == "CLI / MCP")
    assert commands.splitlines()[0] == "pip install 'backendpro[mcp]'"
    assert commands.splitlines()[-1] == server["command"]
    assert "--mcp" not in template

    module = ast.parse((ROOT / "src/backend-pro-max/scripts/mcp_server.py").read_text(encoding="utf-8"))
    registered = {
        node.name
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and decorator.func.attr == "tool"
            for decorator in node.decorator_list
        )
    }
    tools_block = re.search(r'<div class="mcp-tools">(.*?)</div>', template, re.DOTALL).group(1)
    advertised = re.findall(r"<span>(.*?)</span>", tools_block)
    assert len(advertised) == len(set(advertised))
    assert set(advertised) == registered
