"""Tests for Tier 3.3 — tools.json schema validation."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS_JSON = ROOT / "tools.json"


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
            "backendpro_search", "backendpro_search_all", "backendpro_search_stack",
            "backendpro_compare", "backendpro_decide", "backendpro_adr",
            "backendpro_design", "backendpro_find_stale",
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
        assert len(names) == 8

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
