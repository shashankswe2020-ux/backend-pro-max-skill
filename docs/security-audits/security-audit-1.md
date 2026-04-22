# Security Audit Report #1

> **Auditor:** Security Auditor Agent (Security Engineer)
> **Date:** 2026-04-22
> **Scope:** Tier 1 changes — `decide.py`, `search.py`, `core.py` (diff vs `main`)
> **Dependencies:** Pure stdlib only — no third-party packages to audit

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 0 |
| Medium | 1 |
| Low | 2 |
| Info | 2 |

---

## Findings

### [MEDIUM-1] Path traversal via `adr --out` — arbitrary file write

- **Location:** `src/backend-pro-max/scripts/decide.py:343–346`
- **Description:** The `adr()` function accepts an `out_path` parameter and writes the generated ADR text to it via `Path(out_path).write_text()`. The path is used as-is with `mkdir(parents=True)` — no validation, no confinement to a project directory. A user (or an LLM agent calling the tool) could pass `--out /etc/cron.d/malicious` or `--out ~/.ssh/authorized_keys` to write attacker-controlled content to arbitrary filesystem locations.
- **Impact:** Arbitrary file write. The content is mostly template-controlled markdown, but the `title` field is user-supplied and lands in the output verbatim. In a CI/agent context where this tool runs with elevated privileges, this is exploitable.
- **Proof of concept:**
  ```bash
  backendpro --adr "pwned" --domain cache --out /tmp/proof.txt
  # (once --out is wired) writes to /tmp/proof.txt
  # More dangerous: --out ~/.bashrc  (appends to shell config)
  ```
- **Recommendation:** Confine writes to a project-relative directory and validate the path:
  ```python
  if out_path:
      out = Path(out_path).resolve()
      # Optionally restrict to CWD subtree:
      cwd = Path.cwd().resolve()
      if not str(out).startswith(str(cwd)):
          return {"error": f"--out path must be under current directory: {cwd}"}
      out.parent.mkdir(parents=True, exist_ok=True)
      out.write_text(adr_text, encoding="utf-8")
  ```
  At minimum, resolve the path and refuse absolute paths or paths containing `..`.

### [LOW-1] ADR template uses `str.format()` with user-controlled title — potential format string confusion

- **Location:** `src/backend-pro-max/scripts/decide.py:328–340`
- **Description:** `_ADR_TEMPLATE.format(title=title, ...)` passes the user-supplied `title` into a `.format()` call. If a user's title contains `{` or `}` characters (e.g. `"Use {Redis} for cache"`), it will raise `KeyError` or `IndexError` at runtime. This is a denial-of-service / crash, not an injection vector, since `.format()` cannot execute code.
- **Impact:** Low — crashes the command with an unhelpful traceback. Not exploitable for code execution.
- **Recommendation:** Escape braces in user input before formatting, or switch to simple string concatenation / `Template.safe_substitute()`:
  ```python
  safe_title = title.replace("{", "{{").replace("}", "}}")
  ```

### [LOW-2] CSV data from disk is trusted without integrity verification

- **Location:** `src/backend-pro-max/scripts/core.py:293` (existing, not new)
- **Description:** CSV files are read from disk and their content is directly surfaced in tool output (markdown, JSON). If an attacker can modify the CSV files (supply-chain attack on the package, or local tampering), they could inject misleading architecture recommendations. The new constraint columns add more trusted-without-verification surface.
- **Impact:** Low for a CLI tool installed via pip. Higher in an agent/MCP context where the tool's output drives automated decisions.
- **Recommendation:** For future tiers (especially Tier 5 — Trust & Verifiability), consider adding CSV checksums or a manifest file that can be verified at load time.

---

## Info Observations

### [INFO-1] No network calls — excellent attack surface minimization
- The entire codebase is pure stdlib with zero network I/O. No HTTP clients, no DNS lookups, no telemetry. This eliminates entire categories of vulnerabilities (SSRF, data exfiltration, dependency confusion via network).

### [INFO-2] `mkdir(parents=True, exist_ok=True)` creates directories without checking permissions
- **Location:** `src/backend-pro-max/scripts/decide.py:345`
- Not a vulnerability per se, but `mkdir(parents=True)` will create deep directory trees with default permissions. In security-sensitive contexts, explicitly setting `mode=0o755` is preferred.

---

## Positive Observations

- **Zero runtime dependencies** — eliminates the #1 source of Python supply-chain vulnerabilities. No `requests`, no `pyyaml`, no transitive dependency tree to audit.
- **No `eval()`, `exec()`, `pickle`, `subprocess`, or `shell=True`** anywhere in the codebase. Input is processed purely through string operations and regex.
- **`.gitignore` covers secrets** — `.env`, `.env.*` patterns are excluded. No secrets found in git history.
- **Read-only by default** — the only file-write capability (`adr --out`) is opt-in and not yet wired to the CLI, limiting current exposure.
- **CSV data is read-only** — the tool never writes back to its knowledge base files.

---

## Action Items (Priority Order)

| # | Severity | Finding | Recommendation |
|---|----------|---------|----------------|
| 1 | Medium | Path traversal via `adr --out` | Validate/confine `out_path` before writing |
| 2 | Low | Format string crash with `{`/`}` in ADR title | Escape braces or use safe_substitute |
| 3 | Low | CSV data trusted without integrity check | Consider checksums in future Tier 5 |
