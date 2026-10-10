"""The prototype and published landing page share one reproducible build."""

import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "designs/scripts/build_landing.py"


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
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
