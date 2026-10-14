"""Tests for Tier 3.3 — tools.json schema validation."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from backendpro.scripts.core import CSV_CONFIG, STACK_CONFIG
from backendpro.scripts.gen_tools_schema import TOOLS

ROOT = Path(__file__).resolve().parent.parent
TOOLS_JSON = ROOT / "tools.json"


def test_public_tool_names_do_not_repeat_the_server_namespace():
    assert {tool["name"] for tool in TOOLS} == {
        "search", "search_all", "search_stack", "compare",
        "decide", "adr", "design", "find_stale", "evidence_detail", "repository_context", "memory_context",
    }


class TestToolsJsonExists:
    def test_file_exists(self):
        assert TOOLS_JSON.exists(), "tools.json not found at repo root"

    def test_valid_json(self):
        data = json.loads(TOOLS_JSON.read_text(encoding="utf-8"))
        assert isinstance(data, dict)


class TestOpenAIFormat:
    def _load(self):
        return json.loads(TOOLS_JSON.read_text(encoding="utf-8"))["openai"]

    def test_has_openai_key(self):
        data = json.loads(TOOLS_JSON.read_text(encoding="utf-8"))
        assert "openai" in data

    def test_all_tools_present(self):
        tools = self._load()
        names = {t["function"]["name"] for t in tools}
        expected = {
            "search", "search_all", "search_stack",
            "compare", "decide", "adr",
            "design", "find_stale", "evidence_detail", "repository_context", "memory_context",
        }
        assert names == expected

    def test_each_tool_has_required_fields(self):
        for tool in self._load():
            assert tool["type"] == "function"
            fn = tool["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn
            assert fn["parameters"]["type"] == "object"
            assert "properties" in fn["parameters"]
            assert "required" in fn["parameters"]


class TestAnthropicFormat:
    def _load(self):
        return json.loads(TOOLS_JSON.read_text(encoding="utf-8"))["anthropic"]

    def test_has_anthropic_key(self):
        data = json.loads(TOOLS_JSON.read_text(encoding="utf-8"))
        assert "anthropic" in data

    def test_all_tools_present(self):
        tools = self._load()
        names = {t["name"] for t in tools}
        assert len(names) == 11

    def test_each_tool_has_input_schema(self):
        for tool in self._load():
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert tool["input_schema"]["type"] == "object"


class TestFreshness:
    def test_check_mode(self):
        """Verify --check would pass (content matches generator output)."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "gen_tools_schema",
            ROOT / "src" / "backend-pro-max" / "scripts" / "gen_tools_schema.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        expected = json.dumps(mod.generate(), indent=2, ensure_ascii=False) + "\n"
        actual = TOOLS_JSON.read_text(encoding="utf-8")
        assert actual == expected, "tools.json is stale — regenerate with gen_tools_schema.py"


def test_registry_enums_on_every_domain_and_stack_surface():
    for tool in TOOLS:
        properties = tool["parameters"]["properties"]
        if "domain" in properties:
            assert set(properties["domain"]["enum"]) - {None} == set(CSV_CONFIG)
        if "context_domains" in properties:
            assert set(properties["context_domains"]["items"]["enum"]) == set(CSV_CONFIG)
        if "stack" in properties:
            assert set(properties["stack"]["enum"]) - {None} == set(STACK_CONFIG)


def test_cli_and_documented_catalogues_cover_registries():
    result = subprocess.run(
        [sys.executable, "-m", "backendpro.scripts.search", "--list"],
        check=True, capture_output=True, text=True,
    )
    for name in (*CSV_CONFIG, *STACK_CONFIG):
        assert name in result.stdout
    base = ROOT / "src/backend-pro-max/templates/base"
    text = (base / "skill-content.md").read_text()
    for name in (*CSV_CONFIG, *STACK_CONFIG):
        assert f"`{name}`" in text
    assert "`backendpro --list`" in (base / "SKILL.md").read_text()


def test_provider_formats_have_identical_contracts():
    value = json.loads(TOOLS_JSON.read_text())
    for left, right in zip(value["openai"], value["anthropic"]):
        assert left["function"]["name"] == right["name"]
        assert left["function"]["parameters"] == right["input_schema"]
