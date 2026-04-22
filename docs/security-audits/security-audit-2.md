# Security Audit #2: Tier 2 — Retrieval Quality

> **Auditor:** Security Auditor Agent
> **Date:** 2026-04-22
> **Scope:** Tier 2 changes — `semantic.py`, `rerank.py`, `templates.py`, intent classifier, anti-patterns CSV, CLI flags
> **Lines Added:** +1,351 across 15 files

---

## Executive Summary

Tier 2 introduces two optional ML dependencies (`sentence-transformers`, `cross-encoder`) and a disk-based embedding cache. The core project remains zero-dependency and the attack surface increase is modest. One medium-severity finding (pickle deserialization) and two low-severity findings. No high or critical findings. Previous Security Audit #1 findings have been addressed.

---

## Findings

### MEDIUM-1: Pickle deserialization of cached embeddings

- **File:** `src/backend-pro-max/scripts/semantic.py:96–102`
- **CWE:** CWE-502 (Deserialization of Untrusted Data)
- **CVSS 3.1:** 5.3 (Medium) — AV:L/AC:H/PR:L/UI:N/S:U/C:H/I:H/A:N
- **Description:** `_load_from_disk()` calls `pickle.load(f)` on files in `.backendpro_cache/`. Python pickle can execute arbitrary code during deserialization. An attacker who gains write access to the cache directory (e.g., shared workstation, symlink from world-writable `/tmp`, compromised CI cache) can craft a malicious pickle file that executes code when the user runs `backendpro search --engine hybrid`.
- **Mitigating Factors:**
  - Cache directory is under the project root (not `/tmp`)
  - mtime validation provides limited freshness check (not a security control)
  - Feature requires explicit `--engine hybrid` opt-in
  - The `# noqa: S301` comment shows the author is aware
- **Recommendation:** Replace pickle with a safe format:
  1. Save embeddings as `.npy` via `numpy.save()` / `numpy.load(allow_pickle=False)`
  2. Save text lists as JSON
  3. If pickle must be used, add an HMAC signature file alongside each cache entry, keyed on a per-install random secret stored in a separate config file

### LOW-1: Cache directory created with default permissions

- **File:** `src/backend-pro-max/scripts/semantic.py:90`
- **CWE:** CWE-732 (Incorrect Permission Assignment)
- **Description:** `_CACHE_DIR.mkdir(exist_ok=True)` creates `.backendpro_cache/` with default umask permissions. On shared systems, other users may be able to read or write cache files depending on the system umask.
- **Recommendation:** Set explicit permissions: `_CACHE_DIR.mkdir(exist_ok=True, mode=0o700)`

### LOW-2: Model download from Hugging Face Hub without integrity verification

- **File:** `src/backend-pro-max/scripts/semantic.py:32`, `src/backend-pro-max/scripts/rerank.py:34`
- **CWE:** CWE-494 (Download of Code Without Integrity Check)
- **Description:** `SentenceTransformer("all-MiniLM-L6-v2")` and `CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")` download model weights from Hugging Face Hub over HTTPS. While HTTPS provides transport security, there is no pinned hash or signature verification of the downloaded model weights.
- **Mitigating Factors:**
  - Hugging Face Hub has its own integrity checks
  - Models are well-known public models, not custom uploads
  - Both features are opt-in via extras
- **Recommendation:** Document the expected model names in a constants file. Consider adding a `--model` flag to allow users to specify local model paths for air-gapped environments.

---

## Previous Findings Status

| Audit #1 Finding | Status | Evidence |
|---|---|---|
| MEDIUM-1: Path traversal via `--out` flag | ✅ Fixed | `decide.py:372–374` — `resolve()` + CWD containment check |

---

## Attack Surface Analysis

| Component | Risk | Notes |
|---|---|---|
| CSV data files | None | Read-only, shipped with package |
| Intent classifier | None | Regex-only, no user-controlled code execution |
| Templates formatter | None | String formatting only, no injection vector |
| BM25 engine | None | Pure computation, no I/O |
| Semantic engine (optional) | Medium | Pickle cache + model download |
| Rerank engine (optional) | Low | Model download only, no disk cache |
| CLI flags | None | argparse validated, no shell injection |
| REPL | None | Input processed through same safe search path |

---

## Secrets Scan

```
git log --all --diff-filter=A -- '*.env' 'tokens.json' '*.key' '*.pem'
→ No results
```

No secrets, tokens, or credentials found in git history.

---

## Recommendations Summary

| # | Severity | Finding | Effort |
|---|----------|---------|--------|
| 1 | Medium | Replace pickle with numpy+JSON for cache | 2–3 hours |
| 2 | Low | Set cache dir permissions to 0o700 | 5 minutes |
| 3 | Low | Document model names, add `--model` flag for air-gap | 1 hour |
