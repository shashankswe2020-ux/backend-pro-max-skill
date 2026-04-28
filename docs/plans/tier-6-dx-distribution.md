# Tier 6 — DX & Distribution

> Grow from CLI tool to platform. Meet engineers where they already are:
> IDE, browser, CI pipeline, learning workflow, knowledge export.

**Status:** ✅ Phase A+B+C complete (6.3 Linter, 6.4 Learn, 6.5 Export shipped; 6.1 IDE ext and 6.2 Web SPA deferred)
**Branch:** per-task (each feature is independently shippable)
**Depends on:** Tier 3 (MCP server, citations, tools.json), Tier 4 (KB depth for lint rules + learn mode), Tier 5 (source URLs for web playground links)

---

## Overview

| # | Feature | Surface | Complexity | Standalone? |
|---|---------|---------|------------|-------------|
| 6.1 | VS Code / JetBrains extension | IDE marketplace | High | Yes |
| 6.2 | Web playground (`backendpro.dev`) | Static SPA | High | Yes |
| 6.3 | Pre-commit / CI linter (`backendpro lint`) | CLI + pre-commit hook | High | Yes |
| 6.4 | Learn mode — spaced-repetition flashcards | CLI (`backendpro learn`) | Medium | Yes |
| 6.5 | Export (Obsidian / Notion / Org-mode) | CLI (`backendpro export`) | Medium | Yes |

All five are independently shippable. Prioritise by distribution impact:
**6.3 (lint)** and **6.2 (web)** drive the most adoption.

---

## Architecture Decisions

1. **VS Code extension calls the MCP server** (Tier 3) or shells out to
   `backendpro --json`. No bundled Python — the extension is a thin TS client.
   JetBrains variant uses the same MCP transport.
2. **Web playground is a static SPA** (Vite + vanilla TS or Preact). Search
   runs client-side via a WASM-compiled BM25 index or pre-built JSON index
   shipped as a static asset. Zero backend. Deploy to GitHub Pages / Cloudflare Pages.
3. **Linter is a new module `scripts/lint.py`** that scans source files (Python,
   Go, Java, TS, etc.) for anti-pattern signatures using regex/AST-lite rules.
   Rules are defined in a YAML file (`lint-rules.yml`). Pure stdlib.
4. **Learn mode persists state** in `~/.backendpro/learn.json` (spaced-repetition
   scheduler: SM-2 algorithm). Pure stdlib.
5. **Export module `scripts/export.py`** renders CSVs into target formats
   (Obsidian markdown vault, Notion CSV import, Org-mode). Pure stdlib.

---

## Task 6.1 — VS Code / JetBrains Extension

### Description

Right-click → "Ask Backend Pro Max about this code". Inline CodeLens showing
relevant KB rules for the current file's stack. Powered by the MCP server
(Tier 3) or direct CLI invocation.

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 6.1.1 | Scaffold VS Code extension (`yo code` or manual) | `extensions/vscode/` (new dir) | 1h |
| 6.1.2 | Command: "Backend Pro Max: Search" — input box → `backendpro --json` → output panel | `extensions/vscode/src/` | 2h |
| 6.1.3 | Command: "Backend Pro Max: Explain Selection" — selected text → search → hover/panel | `extensions/vscode/src/` | 2h |
| 6.1.4 | CodeLens provider — detect stack from file extension → show relevant guidelines | `extensions/vscode/src/` | 3h |
| 6.1.5 | Settings: `backendpro.path`, `backendpro.defaultDomain`, `backendpro.useMcp` | `extensions/vscode/package.json` | 0.5h |
| 6.1.6 | MCP client mode — connect to `backendpro-mcp` via stdio instead of shelling out | `extensions/vscode/src/` | 2h |
| 6.1.7 | Package + marketplace metadata (`README.md`, icon, `package.json` publisher) | `extensions/vscode/` | 1h |
| 6.1.8 | JetBrains plugin stub — `plugin.xml` + action that shells out to `backendpro --json` | `extensions/jetbrains/` (new dir) | 3h |
| 6.1.9 | Tests — VS Code extension unit tests with `@vscode/test-electron` | `extensions/vscode/src/test/` | 2h |

### Acceptance Criteria

- [ ] `code --install-extension backendpro-*.vsix` installs without error
- [ ] "Backend Pro Max: Search" command opens input, returns results in output panel
- [ ] Right-click on selected text → "Explain with Backend Pro Max" works
- [ ] CodeLens appears in `.go` files showing Go stack guidelines
- [ ] Extension works in both CLI mode and MCP mode
- [ ] JetBrains plugin runs basic search via Tools menu
- [ ] `npm test` in `extensions/vscode/` passes

### Verification

```bash
cd extensions/vscode && npm install && npm run compile && npm test
npx @vscode/vsce package  # produces .vsix
code --install-extension backendpro-*.vsix
# Manual: open a .go file, verify CodeLens appears
```

---

## Task 6.2 — Web Playground (`backendpro.dev`)

### Description

Static SPA with search-as-you-type, shareable permalink per query, domain
filter sidebar. Zero backend — all search happens client-side against a
pre-built JSON index.

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 6.2.1 | Index builder — `scripts/build_web_index.py` converts all CSVs to a single JSON blob with pre-tokenized BM25 data | `scripts/build_web_index.py` (new) | 2h |
| 6.2.2 | Scaffold Vite + Preact (or vanilla TS) SPA | `web/` (new dir) | 1h |
| 6.2.3 | BM25 search in TypeScript — port core scoring logic (~100 LOC) | `web/src/search.ts` | 2h |
| 6.2.4 | Search UI — input, domain filter, results list, keyboard navigation | `web/src/` | 3h |
| 6.2.5 | Permalink — `?q=kafka&domain=messaging` synced to URL bar | `web/src/` | 1h |
| 6.2.6 | Compare view — side-by-side table (reuse `format_compare` logic) | `web/src/` | 2h |
| 6.2.7 | Citation links — clicking `[BPM:messaging.kafka]` deep-links to that row | `web/src/` | 1h |
| 6.2.8 | Deploy config — GitHub Pages action or Cloudflare Pages | `.github/workflows/deploy-web.yml` (new) | 1h |
| 6.2.9 | CI — rebuild index on CSV changes, deploy on `main` push | `.github/workflows/deploy-web.yml` | 1h |
| 6.2.10 | Tests — index builder output shape, search accuracy on 5 golden queries | `web/tests/`, `tests/test_web_index.py` | 2h |

### Acceptance Criteria

- [ ] `python scripts/build_web_index.py` produces `web/public/index.json` (<500 KB gzipped)
- [ ] `cd web && npm run dev` serves the SPA locally
- [ ] Search-as-you-type returns results within 50ms (client-side BM25)
- [ ] Domain filter sidebar works
- [ ] `backendpro.dev/?q=kafka&domain=messaging` produces a shareable permalink
- [ ] Compare view renders side-by-side table
- [ ] GitHub Pages deploy Action triggers on `main` push
- [ ] `npm test` in `web/` passes

### Verification

```bash
python3 src/backend-pro-max/scripts/build_web_index.py
ls -lh web/public/index.json
cd web && npm install && npm run dev  # open http://localhost:5173
npm test
```

---

## Task 6.3 — Pre-commit / CI Linter (`backendpro lint`)

### Description

`backendpro lint` scans source files for anti-patterns: unbounded retries,
`time.Sleep` in HTTP handlers, missing `context.Context`, sync HTTP in async
functions, missing idempotency keys on POSTs, secrets in env files. Turns the
knowledge base into an **enforcer**.

Rules are defined in a YAML config (`lint-rules.yml`) for extensibility.

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 6.3.1 | `scripts/lint.py` — rule engine: load YAML rules, scan files, report findings | `scripts/lint.py` (new) | 3h |
| 6.3.2 | Rule format: `id`, `name`, `pattern` (regex), `languages`, `severity`, `message`, `fix`, `bpm_citation` | `lint-rules.yml` (new) | 1h |
| 6.3.3 | Initial rule set — ≥15 rules across Go, Python, Java, TypeScript | `lint-rules.yml` | 4h |
| 6.3.4 | Output formatters — human-readable, JSON, SARIF (for GitHub Code Scanning) | `scripts/lint.py` | 2h |
| 6.3.5 | CLI integration — `backendpro lint <path> [--format human\|json\|sarif] [--severity warning]` | `scripts/search.py` | 1h |
| 6.3.6 | Pre-commit hook config — `.pre-commit-hooks.yaml` for pre-commit framework | `.pre-commit-hooks.yaml` (new) | 0.5h |
| 6.3.7 | GitHub Action — `backendpro-lint-action` (composite action using `backendpro lint --format sarif`) | `.github/actions/lint/action.yml` (new) | 1.5h |
| 6.3.8 | `--fix` mode — auto-fix simple patterns (e.g. add context parameter placeholder) | `scripts/lint.py` | 2h |
| 6.3.9 | Tests — each rule has ≥1 positive + ≥1 negative fixture | `tests/test_lint.py` (new), `tests/fixtures/lint/` (new) | 3h |

### Initial Rules (examples)

| ID | Pattern | Languages | Severity | Citation |
|----|---------|-----------|----------|----------|
| BPM-L001 | `time.Sleep` in HTTP handler | Go | warning | `[BPM:performance.blocking-sleep]` |
| BPM-L002 | Missing `context.Context` in function signature | Go | warning | `[BPM:reliability.context-propagation]` |
| BPM-L003 | `requests.get` without `timeout=` | Python | error | `[BPM:reliability.unbounded-timeout]` |
| BPM-L004 | `async def` calling `requests.*` (sync in async) | Python | error | `[BPM:performance.sync-in-async]` |
| BPM-L005 | `Thread.sleep` in Spring `@RestController` | Java | warning | `[BPM:performance.blocking-sleep]` |
| BPM-L006 | Retry without backoff (`while.*retry` without `sleep\|delay\|backoff`) | All | warning | `[BPM:reliability.unbounded-retry]` |
| BPM-L007 | `SECRET\|PASSWORD\|API_KEY` in `.env` files | All | error | `[BPM:security.secrets-in-env]` |
| BPM-L008 | POST endpoint without idempotency key header check | All | info | `[BPM:reliability.missing-idempotency]` |

### Acceptance Criteria

- [ ] `backendpro lint src/` scans Python files and reports findings
- [ ] `backendpro lint --format sarif` produces valid SARIF JSON
- [ ] `backendpro lint --format json` produces machine-readable output
- [ ] Each finding includes: file, line, rule ID, severity, message, fix suggestion, BPM citation
- [ ] ≥15 rules shipping in `lint-rules.yml`
- [ ] Pre-commit hook works: `pre-commit run backendpro-lint --all-files`
- [ ] GitHub Action composite works in a test workflow
- [ ] `pytest tests/test_lint.py` passes (≥30 test cases: 2 per rule)

### Verification

```bash
backendpro lint tests/fixtures/lint/ --format human
backendpro lint tests/fixtures/lint/ --format json
backendpro lint tests/fixtures/lint/ --format sarif | python3 -m json.tool > /dev/null
backendpro lint src/ --severity warning
pytest tests/test_lint.py -v
```

---

## Task 6.4 — Learn Mode (Spaced Repetition)

### Description

`backendpro learn --domain consistency --daily 5` presents flashcard-style
Q&A from the KB using SM-2 spaced repetition. State persists in
`~/.backendpro/learn.json`.

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 6.4.1 | SM-2 scheduler implementation (pure stdlib) | `scripts/learn.py` (new) | 2h |
| 6.4.2 | Flashcard generator — convert CSV rows to Q/A pairs | `scripts/learn.py` | 1.5h |
| 6.4.3 | Interactive session — present card, accept self-rating (1-5), update schedule | `scripts/learn.py` | 1.5h |
| 6.4.4 | State persistence — `~/.backendpro/learn.json` | `scripts/learn.py` | 1h |
| 6.4.5 | CLI integration — `backendpro learn [--domain D] [--daily N] [--reset]` | `scripts/search.py` | 1h |
| 6.4.6 | Stats command — `backendpro learn --stats` (cards seen, due, mastered) | `scripts/learn.py` | 0.5h |
| 6.4.7 | Tests — SM-2 math, card generation, session flow | `tests/test_learn.py` (new) | 2h |

### Acceptance Criteria

- [ ] `backendpro learn --domain consistency --daily 5` presents 5 flashcards
- [ ] Each card shows a question (e.g. "What is linearizability?"), user rates 1-5, answer revealed
- [ ] SM-2 schedule persists — cards rated poorly return sooner
- [ ] `backendpro learn --stats` shows progress summary
- [ ] `backendpro learn --reset` clears state
- [ ] `--domain` filters to specific domain; omitted = all domains
- [ ] `pytest tests/test_learn.py` passes

### Verification

```bash
backendpro learn --domain consistency --daily 3
backendpro learn --stats
backendpro learn --reset
pytest tests/test_learn.py -v
```

---

## Task 6.5 — Export (Obsidian / Notion / Org-mode)

### Description

`backendpro export --format obsidian --out vault/` renders the entire KB
into the target format for offline use, personal knowledge management, or
team wikis.

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 6.5.1 | `scripts/export.py` — export engine with pluggable formatters | `scripts/export.py` (new) | 1.5h |
| 6.5.2 | Obsidian formatter — one `.md` file per row, YAML frontmatter, wikilinks between related items | `scripts/export.py` | 2h |
| 6.5.3 | Notion formatter — CSV with Notion-compatible columns (multi-select, URL, date) | `scripts/export.py` | 1.5h |
| 6.5.4 | Org-mode formatter — `.org` file per domain with headlines per row | `scripts/export.py` | 1.5h |
| 6.5.5 | CLI — `backendpro export --format obsidian\|notion\|org [--domain D] --out <path>` | `scripts/search.py` | 1h |
| 6.5.6 | Index/MOC generation — Obsidian gets a `_Index.md` Map of Content | `scripts/export.py` | 1h |
| 6.5.7 | Tests — output file count, frontmatter shape, wikilink validity | `tests/test_export.py` (new) | 2h |

### Acceptance Criteria

- [ ] `backendpro export --format obsidian --out /tmp/vault` creates one `.md` per row with YAML frontmatter
- [ ] Obsidian vault has `_Index.md` with links to all notes
- [ ] Related items are wikilinked: `[[Circuit Breaker]]` in a Retry note
- [ ] `backendpro export --format notion --out /tmp/notion` creates importable CSVs
- [ ] `backendpro export --format org --out /tmp/org` creates `.org` files
- [ ] `--domain messaging` exports only messaging rows
- [ ] `pytest tests/test_export.py` passes

### Verification

```bash
backendpro export --format obsidian --out /tmp/bpm-vault
ls /tmp/bpm-vault/ | head -20
cat /tmp/bpm-vault/_Index.md | head -20
backendpro export --format notion --out /tmp/bpm-notion --domain messaging
backendpro export --format org --out /tmp/bpm-org
pytest tests/test_export.py -v
```

---

## Dependency Graph

```
All tasks are independently shippable.
Priority order by distribution impact:

┌──────────────┐  ┌──────────────┐
│ 6.3 Linter   │  │ 6.2 Web SPA  │   ← Highest impact, start first
│ (enforcer)   │  │ (top funnel) │
└──────────────┘  └──────────────┘

┌──────────────┐  ┌──────────────┐
│ 6.1 IDE ext  │  │ 6.5 Export   │   ← Medium impact
│ (VS Code)    │  │ (Obsidian…)  │
└──────────────┘  └──────────────┘

┌──────────────┐
│ 6.4 Learn    │   ← Niche but high loyalty
│ (flashcards) │
└──────────────┘
```

**No hard dependencies between tasks.** Soft dependencies:
- 6.1 benefits from Tier 3 MCP server (6.1.6)
- 6.2 benefits from Tier 3 citations (permalink to `[BPM:...]`)
- 6.3 benefits from Tier 2 anti-patterns CSV (rule citations)
- 6.4 benefits from Tier 4 expanded KB (more cards to learn)

### Recommended implementation order

1. **Phase A** (parallel): 6.3 (linter) + 6.2 (web playground)
2. **Phase B** (parallel): 6.5 (export) + 6.1 (IDE extension)
3. **Phase C**: 6.4 (learn mode)

---

## Checkpoint Criteria

### After Phase A

- [ ] `backendpro lint` scans code with ≥15 rules, outputs human/JSON/SARIF
- [ ] Pre-commit hook works
- [ ] Web playground deploys to GitHub Pages, search-as-you-type works
- [ ] Permalink sharing works

### After Phase B

- [ ] VS Code extension installable from `.vsix`, search + CodeLens work
- [ ] Export to Obsidian/Notion/Org produces valid output
- [ ] ≥1 format actively usable (Obsidian recommended for dogfooding)

### After Phase C (Tier 6 complete)

- [ ] Learn mode with SM-2 spaced repetition works
- [ ] All 5 features have tests
- [ ] ≥60 new test cases total for Tier 6
- [ ] `ruff check src tests` clean
- [ ] README updated with DX/distribution features
- [ ] CHANGELOG entry

---

## Files to Create / Modify

| Action | File |
|--------|------|
| **Create** | `extensions/vscode/` (full extension scaffold) |
| **Create** | `extensions/jetbrains/` (plugin stub) |
| **Create** | `web/` (Vite SPA scaffold) |
| **Create** | `src/backend-pro-max/scripts/lint.py` |
| **Create** | `src/backend-pro-max/scripts/learn.py` |
| **Create** | `src/backend-pro-max/scripts/export.py` |
| **Create** | `src/backend-pro-max/scripts/build_web_index.py` |
| **Create** | `lint-rules.yml` |
| **Create** | `.pre-commit-hooks.yaml` |
| **Create** | `.github/actions/lint/action.yml` |
| **Create** | `.github/workflows/deploy-web.yml` |
| **Create** | `tests/test_lint.py` |
| **Create** | `tests/test_learn.py` |
| **Create** | `tests/test_export.py` |
| **Create** | `tests/test_web_index.py` |
| **Create** | `tests/fixtures/lint/` (positive/negative test fixtures per language) |
| **Modify** | `src/backend-pro-max/scripts/search.py` (lint, learn, export CLI subcommands) |
| **Modify** | `pyproject.toml` (new entry points: `backendpro-lint`) |
| **Modify** | `README.md`, `CHANGELOG.md` |

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| VS Code extension requires maintaining a separate TS codebase | Keep it thin — delegate all logic to `backendpro --json` or MCP. Extension is a UI shell only. |
| Web playground BM25 in JS may diverge from Python BM25 | Port tests: run the same golden queries against both implementations, assert same top-3 ranking. |
| Web index size could be large with Tier 4 expansion (~650+ rows) | Pre-tokenize and compress. Target <500 KB gzipped. Lazy-load stack CSVs on demand. |
| Linter regex rules have high false-positive rate | Each rule ships with ≥1 negative test case. Default severity is `warning` not `error`. Users can disable rules in config. SARIF output lets GitHub show inline annotations without blocking. |
| Linter scope creep — tempting to build a real AST-based linter | Stay regex-based for v1. Document limitations. AST-based rules (tree-sitter) can be a future enhancement. |
| SM-2 algorithm edge cases (new cards, rating boundary) | Use the well-documented SM-2 spec. Test with edge cases: all-1 ratings, all-5 ratings, 0 cards due. |
| Learn mode state file corruption | Atomic writes (write to temp file, rename). Schema version in JSON for forward-compat. `--reset` as escape hatch. |
| Export format drift (Obsidian/Notion change import format) | Keep formatters simple. Obsidian is just markdown + YAML frontmatter — very stable. Notion CSV import is standard. Org-mode is decades-stable. |
| Pre-commit hook slows down commits | Lint only changed files by default. `--all-files` for CI. Keep rule evaluation fast (pure regex, no file I/O beyond reading the source). |
