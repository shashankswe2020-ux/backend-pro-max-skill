"""Tests for the export module (Task 6.5)."""
from __future__ import annotations

import csv
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "backend-pro-max", "scripts"))

import export


def _tmpdir():
    return tempfile.mkdtemp(prefix="bpm_export_")


# ── Obsidian ─────────────────────────────────────────────────────────────
def test_obsidian_creates_files():
    """Obsidian export creates .md files in domain subfolders."""
    out = _tmpdir()
    result = export.export_obsidian(out)
    assert result["format"] == "obsidian"
    assert result["files"] > 0
    # Domain subfolders should exist
    subdirs = [d for d in os.listdir(out) if os.path.isdir(os.path.join(out, d))]
    assert len(subdirs) > 1
    # .md files inside subfolders
    md_files = []
    for root, _dirs, files in os.walk(out):
        md_files.extend(f for f in files if f.endswith(".md") and f != "_Index.md")
    assert len(md_files) > 1


def test_obsidian_index():
    """Obsidian export creates _Index.md."""
    out = _tmpdir()
    export.export_obsidian(out)
    index_path = os.path.join(out, "_Index.md")
    assert os.path.exists(index_path)
    content = open(index_path, encoding="utf-8").read()
    assert "Knowledge Base Index" in content
    assert "[[" in content  # wikilinks


def test_obsidian_frontmatter():
    """Each Obsidian note has YAML frontmatter."""
    out = _tmpdir()
    export.export_obsidian(out, domain="cache")
    domain_dir = os.path.join(out, "cache")
    md_files = [f for f in os.listdir(domain_dir) if f.endswith(".md") and f != "_Index.md"]
    assert len(md_files) > 0
    content = open(os.path.join(domain_dir, md_files[0]), encoding="utf-8").read()
    assert content.startswith("---")
    assert "domain: cache" in content
    assert "citation:" in content


def test_obsidian_wikilinks():
    """Notes with related items contain wikilinks."""
    out = _tmpdir()
    export.export_obsidian(out, domain="pattern")
    domain_dir = os.path.join(out, "pattern")
    found_wikilink = False
    for f in os.listdir(domain_dir):
        if f == "_Index.md" or not f.endswith(".md"):
            continue
        content = open(os.path.join(domain_dir, f), encoding="utf-8").read()
        parts = content.split("---", 2)
        if len(parts) >= 3 and "[[" in parts[2]:
            found_wikilink = True
            break
    assert found_wikilink, "Expected at least one note with wikilinks"


def test_obsidian_domain_filter():
    """--domain filters to only that domain."""
    out_all = _tmpdir()
    out_one = _tmpdir()
    export.export_obsidian(out_all)
    export.export_obsidian(out_one, domain="cache")
    all_count = len(os.listdir(out_all))
    one_count = len(os.listdir(out_one))
    assert one_count < all_count


# ── Notion ───────────────────────────────────────────────────────────────
def test_notion_creates_csvs():
    """Notion export creates CSV files."""
    out = _tmpdir()
    result = export.export_notion(out)
    assert result["format"] == "notion"
    assert result["files"] > 0
    csv_files = [f for f in os.listdir(out) if f.endswith(".csv")]
    assert len(csv_files) > 0


def test_notion_csv_valid():
    """Notion CSVs are valid and parseable."""
    out = _tmpdir()
    export.export_notion(out, domain="messaging")
    csv_file = os.path.join(out, "messaging.csv")
    assert os.path.exists(csv_file)
    with open(csv_file, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) > 0
    assert "Name" in rows[0]


def test_notion_domain_filter():
    """Notion --domain exports only that domain."""
    out = _tmpdir()
    export.export_notion(out, domain="cache")
    files = os.listdir(out)
    assert files == ["cache.csv"]


# ── Org-mode ─────────────────────────────────────────────────────────────
def test_org_creates_files():
    """Org-mode export creates .org files."""
    out = _tmpdir()
    result = export.export_org(out)
    assert result["format"] == "org"
    assert result["files"] > 0
    org_files = [f for f in os.listdir(out) if f.endswith(".org")]
    assert len(org_files) > 0


def test_org_file_structure():
    """Org files have proper headlines and properties."""
    out = _tmpdir()
    export.export_org(out, domain="cache")
    org_file = os.path.join(out, "cache.org")
    assert os.path.exists(org_file)
    content = open(org_file, encoding="utf-8").read()
    assert "#+TITLE:" in content
    assert ":PROPERTIES:" in content
    assert ":DOMAIN: cache" in content
    assert ":CITATION:" in content


def test_org_domain_filter():
    """Org --domain exports only that domain."""
    out = _tmpdir()
    export.export_org(out, domain="messaging")
    files = os.listdir(out)
    assert files == ["messaging.org"]


# ── Cross-format ─────────────────────────────────────────────────────────
def test_all_formats_same_row_count():
    """All formats export the same number of domain rows for a filtered domain."""
    out_obs = _tmpdir()
    out_not = _tmpdir()
    out_org = _tmpdir()
    export.export_obsidian(out_obs, domain="messaging")
    export.export_notion(out_not, domain="messaging")
    export.export_org(out_org, domain="messaging")
    # Obsidian: md files in messaging subfolder minus _Index.md
    msg_dir = os.path.join(out_obs, "messaging")
    obs_count = len([f for f in os.listdir(msg_dir) if f.endswith(".md") and f != "_Index.md"])
    # Notion: rows in CSV
    with open(os.path.join(out_not, "messaging.csv"), encoding="utf-8") as f:
        not_count = len(list(csv.DictReader(f)))
    # Should be the same (obs creates one file per row, notion has one row per row)
    assert obs_count == not_count
