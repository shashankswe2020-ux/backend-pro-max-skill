"""Tests for the linter (Task 6.3)."""
from __future__ import annotations

import json
import os
import sys

# Ensure the scripts dir is on the path for direct imports.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "backend-pro-max", "scripts"))

import lint

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "lint")
RULES_PATH = os.path.join(os.path.dirname(__file__), "..", "lint-rules.yml")


def _load():
    return lint.load_rules(RULES_PATH)


# ── Rule loading ─────────────────────────────────────────────────────────
def test_load_rules_count():
    """At least 15 rules must be defined."""
    rules = _load()
    assert len(rules) >= 15, f"Expected ≥15 rules, got {len(rules)}"


def test_rule_required_fields():
    """Each rule must have id, name, pattern, severity, message."""
    for r in _load():
        for key in ("id", "name", "pattern", "severity", "message"):
            assert key in r, f"Rule {r.get('id', '?')} missing '{key}'"


def test_rule_ids_unique():
    """Rule IDs must be unique."""
    ids = [r["id"] for r in _load()]
    assert len(ids) == len(set(ids))


def test_rule_severity_valid():
    """Severity must be error, warning, or info."""
    for r in _load():
        assert r["severity"] in ("error", "warning", "info"), f"Bad severity in {r['id']}"


def test_rule_has_citation():
    """Each rule should have a BPM citation."""
    for r in _load():
        assert r.get("citation", "").startswith("[BPM:"), f"Rule {r['id']} missing citation"


# ── Python fixture ───────────────────────────────────────────────────────
def _py_findings():
    rules = _load()
    return lint.lint_file(os.path.join(FIXTURES, "sample.py"), rules)


def test_python_requests_no_timeout():
    """BPM-L003: requests.get without timeout detected."""
    ids = [f.rule_id for f in _py_findings()]
    assert "BPM-L003" in ids


def test_python_requests_with_timeout_not_flagged():
    """requests.get(url, timeout=10) should NOT trigger BPM-L003."""
    findings = _py_findings()
    l003 = [f for f in findings if f.rule_id == "BPM-L003"]
    # Should only match the one without timeout, not the one with timeout
    lines = [f.line for f in l003]
    assert 12 not in lines, "timeout= call should not be flagged"


def test_python_sync_in_async():
    """BPM-L004: sync requests in async function."""
    ids = [f.rule_id for f in _py_findings()]
    assert "BPM-L004" in ids


def test_python_eval():
    """BPM-L015: eval() usage detected."""
    ids = [f.rule_id for f in _py_findings()]
    assert "BPM-L015" in ids


def test_python_bare_except():
    """BPM-L010: bare except detected."""
    ids = [f.rule_id for f in _py_findings()]
    assert "BPM-L010" in ids


def test_python_sql_interpolation():
    """BPM-L016: f-string SQL detected."""
    ids = [f.rule_id for f in _py_findings()]
    assert "BPM-L016" in ids


def test_python_jwt_hardcoded():
    """BPM-L017: hardcoded JWT secret."""
    ids = [f.rule_id for f in _py_findings()]
    assert "BPM-L017" in ids


# ── Go fixture ───────────────────────────────────────────────────────────
def _go_findings():
    rules = _load()
    return lint.lint_file(os.path.join(FIXTURES, "sample.go"), rules)


def test_go_time_sleep():
    """BPM-L001: time.Sleep in handler."""
    ids = [f.rule_id for f in _go_findings()]
    assert "BPM-L001" in ids


def test_go_missing_context():
    """BPM-L002: missing context.Context."""
    ids = [f.rule_id for f in _go_findings()]
    assert "BPM-L002" in ids


def test_go_context_present_not_flagged():
    """func with ctx context.Context should NOT trigger BPM-L002."""
    findings = _go_findings()
    l002 = [f for f in findings if f.rule_id == "BPM-L002"]
    names = [f.matched_text for f in l002]
    assert "GetUser" not in names


def test_go_panic():
    """BPM-L013: panic in library code."""
    ids = [f.rule_id for f in _go_findings()]
    assert "BPM-L013" in ids


# ── TypeScript fixture ───────────────────────────────────────────────────
def _ts_findings():
    rules = _load()
    return lint.lint_file(os.path.join(FIXTURES, "sample.ts"), rules)


def test_ts_console_log():
    """BPM-L012: console.log detected."""
    ids = [f.rule_id for f in _ts_findings()]
    assert "BPM-L012" in ids


def test_ts_select_star():
    """BPM-L009: SELECT * detected."""
    ids = [f.rule_id for f in _ts_findings()]
    assert "BPM-L009" in ids


# ── Env fixture ──────────────────────────────────────────────────────────
def _env_findings():
    rules = _load()
    return lint.lint_file(os.path.join(FIXTURES, "sample.env"), rules)


def test_env_secrets():
    """BPM-L007: secrets in .env detected."""
    ids = [f.rule_id for f in _env_findings()]
    assert "BPM-L007" in ids


def test_env_secret_count():
    """Should find SECRET_KEY, API_KEY, PASSWORD (at least 3)."""
    findings = [f for f in _env_findings() if f.rule_id == "BPM-L007"]
    assert len(findings) >= 3


# ── Java fixture ─────────────────────────────────────────────────────────
def _java_findings():
    rules = _load()
    return lint.lint_file(os.path.join(FIXTURES, "sample.java"), rules)


def test_java_thread_sleep():
    """BPM-L005: Thread.sleep in controller."""
    ids = [f.rule_id for f in _java_findings()]
    assert "BPM-L005" in ids


def test_java_sql_format():
    """BPM-L016: String.format SQL injection."""
    ids = [f.rule_id for f in _java_findings()]
    assert "BPM-L016" in ids


# ── Directory scanning ───────────────────────────────────────────────────
def test_lint_paths_directory():
    """lint_paths on fixtures dir returns findings from all files."""
    rules = _load()
    findings = lint.lint_paths([FIXTURES], rules)
    files = {f.file for f in findings}
    assert len(files) >= 3, "Should find issues in at least 3 fixture files"


def test_lint_paths_severity_filter():
    """Severity filter 'error' should exclude warnings and infos."""
    rules = _load()
    all_findings = lint.lint_paths([FIXTURES], rules)
    error_only = lint.lint_paths([FIXTURES], rules, severity_filter="error")
    assert all(f.severity == "error" for f in error_only)
    assert len(error_only) < len(all_findings)


# ── Output formatters ───────────────────────────────────────────────────
def test_format_human_no_findings():
    assert "No issues" in lint.format_human([])


def test_format_human_with_findings():
    rules = _load()
    findings = lint.lint_paths([FIXTURES], rules)
    output = lint.format_human(findings)
    assert "BPM-L" in output
    assert "Fix:" in output


def test_format_json_valid():
    rules = _load()
    findings = lint.lint_paths([FIXTURES], rules)
    parsed = json.loads(lint.format_json(findings))
    assert isinstance(parsed, list)
    assert len(parsed) > 0
    assert "rule_id" in parsed[0]


def test_format_sarif_valid():
    rules = _load()
    findings = lint.lint_paths([FIXTURES], rules)
    sarif = json.loads(lint.format_sarif(findings))
    assert sarif["version"] == "2.1.0"
    assert len(sarif["runs"]) == 1
    assert len(sarif["runs"][0]["results"]) > 0
    assert "rules" in sarif["runs"][0]["tool"]["driver"]


# ── Finding structure ────────────────────────────────────────────────────
def test_finding_has_all_fields():
    """Each finding must have file, line, rule_id, severity, message, fix, citation."""
    rules = _load()
    findings = lint.lint_paths([FIXTURES], rules)
    for f in findings:
        assert f.file
        assert f.line > 0
        assert f.rule_id.startswith("BPM-L")
        assert f.severity in ("error", "warning", "info")
        assert f.message
        assert f.citation.startswith("[BPM:")
