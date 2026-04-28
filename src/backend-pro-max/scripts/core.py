#!/usr/bin/env python3
"""
Backend Pro Max Core - BM25 search engine for backend / distributed-systems
knowledge bases.

Pure standard-library implementation (Python 3.8+). No external dependencies.

Public API (stable):
    search(query, domain=None, max_results=5, *, min_score=0.0, max_age_months=None)
    search_stack(query, stack, max_results=5, *, min_score=0.0)
    search_all(query, max_results=2, *, min_score=0.0)
    compare(names, domain=None, max_per_name=1)
    detect_domain(query)
    classify_intent(query)
    find_stale(domain, months)
    clear_cache()
    CSV_CONFIG, STACK_CONFIG, AVAILABLE_STACKS, MAX_RESULTS, Intent
"""

import csv
import enum
import re
from collections import defaultdict
from datetime import datetime
from math import log
from pathlib import Path

# ============ CONFIGURATION ============
DATA_DIR = Path(__file__).parent.parent / "data"
MAX_RESULTS = 5

# Standard column shapes used by most domain CSVs.
_GENERIC_OUTPUT = [
    "Name", "Category", "Use Case", "Strengths", "Weaknesses", "When to Use",
    "When NOT to Use", "Alternatives", "Notes",
]

CSV_CONFIG = {
    "language": {
        "file": "languages.csv",
        "search_cols": ["Name", "Paradigms", "Strengths", "Use Case", "Ecosystem", "Keywords"],
        "output_cols": [
            "Name", "Paradigms", "Typing", "Concurrency Model", "Performance Tier",
            "Strengths", "Weaknesses", "Use Case", "Notable Frameworks", "Ecosystem",
            "Build Tooling", "Package Manager", "Testing Tooling", "Notes",
            "Source URL", "Source Type", "Last Updated",
        ],
    },
    "pattern": {
        "file": "patterns.csv",
        "search_cols": ["Name", "Category", "Problem", "Keywords", "When to Use"],
        "output_cols": [
            "Name", "Category", "Problem", "Solution", "When to Use",
            "When NOT to Use", "Trade-offs", "Related Patterns", "Source URL",
            "Source Type", "Last Updated",
        ],
    },
    "database": {
        "file": "databases.csv",
        "search_cols": ["Name", "Category", "Use Case", "Strengths", "Keywords"],
        "output_cols": [
            "Name", "Category", "Data Model", "Consistency Model", "Replication",
            "Sharding", "Use Case", "Strengths", "Weaknesses", "Typical Latency",
            "Operational Cost", "Cloud Managed Options", "Notes",
            "Throughput Tier", "Latency Tier", "Consistency Tier", "Cost Tier",
            "Cloud Native", "Source URL", "Source Type", "Last Updated",
        ],
    },
    "messaging": {
        "file": "messaging.csv",
        "search_cols": ["Name", "Category", "Use Case", "Delivery", "Keywords"],
        "output_cols": [
            "Name", "Category", "Delivery", "Ordering", "Throughput", "Latency",
            "Persistence", "Replay", "Use Case", "Strengths", "Weaknesses",
            "Cloud Managed Options", "Notes",
            "Throughput Tier", "Latency Tier", "Consistency Tier", "Cost Tier",
            "Cloud Native", "Source URL", "Source Type", "Last Updated",
        ],
    },
    "cache": {
        "file": "cache.csv",
        "search_cols": ["Name", "Strategy", "Use Case", "Keywords"],
        "output_cols": [
            "Name", "Strategy", "Topology", "Eviction", "Consistency",
            "Use Case", "Strengths", "Weaknesses", "Pitfalls", "Notes",
            "Throughput Tier", "Latency Tier", "Consistency Tier", "Cost Tier",
            "Cloud Native", "Source URL", "Source Type", "Last Updated",
        ],
    },
    "cloud": {
        "file": "cloud.csv",
        "search_cols": ["Service", "Provider", "Category", "Use Case", "Keywords"],
        "output_cols": [
            "Service", "Provider", "Category", "Equivalent AWS", "Equivalent GCP",
            "Equivalent Azure", "Use Case", "Strengths", "Weaknesses", "Pricing Model",
            "Notes", "Source URL", "Source Type", "Last Updated",
        ],
    },
    "iac": {
        "file": "iac.csv",
        "search_cols": ["Name", "Category", "Use Case", "Keywords"],
        "output_cols": [
            "Name", "Category", "Language", "Provider Coverage", "State Management",
            "Strengths", "Weaknesses", "Use Case", "Notes",
            "Source URL", "Source Type", "Last Updated",
        ],
    },
    "container": {
        "file": "containers.csv",
        "search_cols": ["Name", "Category", "Use Case", "Keywords"],
        "output_cols": [
            "Name", "Category", "Layer", "Use Case", "Strengths", "Weaknesses",
            "Alternatives", "Notes",
            "Source URL", "Source Type", "Last Updated",
        ],
    },
    "observability": {
        "file": "observability.csv",
        "search_cols": ["Tool", "Signal", "Use Case", "Keywords"],
        "output_cols": [
            "Tool", "Signal", "Type", "Open Source", "Use Case", "Strengths",
            "Weaknesses", "Integrations", "Notes",
            "Source URL", "Source Type", "Last Updated",
        ],
    },
    "api": {
        "file": "api.csv",
        "search_cols": ["Style", "Use Case", "Keywords", "Transport"],
        "output_cols": [
            "Style", "Transport", "Schema", "Streaming", "Browser Friendly",
            "Backwards Compatibility", "Use Case", "Strengths", "Weaknesses",
            "Tooling", "Notes",
            "Source URL", "Source Type", "Last Updated",
        ],
    },
    "auth": {
        "file": "auth.csv",
        "search_cols": ["Name", "Category", "Use Case", "Keywords"],
        "output_cols": [
            "Name", "Category", "Token Type", "Use Case", "Strengths", "Weaknesses",
            "Common Pitfalls", "Notes",
            "Source URL", "Source Type", "Last Updated",
        ],
    },
    "security": {
        "file": "security.csv",
        "search_cols": ["Topic", "Category", "Threat", "Keywords"],
        "output_cols": [
            "Topic", "Category", "Threat", "Mitigation", "Do", "Don't",
            "Tooling", "Severity", "Source URL", "Source Type", "Last Updated",
        ],
    },
    "cicd": {
        "file": "cicd.csv",
        "search_cols": ["Tool", "Category", "Use Case", "Keywords"],
        "output_cols": [
            "Tool", "Category", "Hosting", "Use Case", "Strengths", "Weaknesses",
            "Notable Features", "Notes",
            "Source URL", "Source Type", "Last Updated",
        ],
    },
    "testing": {
        "file": "testing.csv",
        "search_cols": ["Name", "Level", "Use Case", "Keywords"],
        "output_cols": [
            "Name", "Level", "Use Case", "Strengths", "Weaknesses", "Tooling",
            "Pitfalls", "Notes",
            "Source URL", "Source Type", "Last Updated",
        ],
    },
    "architecture": {
        "file": "architecture.csv",
        "search_cols": ["Name", "Category", "When to Use", "Keywords"],
        "output_cols": [
            "Name", "Category", "When to Use", "When NOT to Use", "Strengths",
            "Weaknesses", "Team Size", "Operational Cost", "Notes",
            "Source URL", "Source Type", "Last Updated",
        ],
    },
    "scaling": {
        "file": "scaling.csv",
        "search_cols": ["Technique", "Category", "Use Case", "Keywords"],
        "output_cols": [
            "Technique", "Category", "Layer", "Use Case", "Strengths", "Weaknesses",
            "Pitfalls", "Notes",
            "Source URL", "Source Type", "Last Updated",
        ],
    },
    "consistency": {
        "file": "consistency.csv",
        "search_cols": ["Model", "Category", "Use Case", "Keywords"],
        "output_cols": [
            "Model", "Category", "Guarantees", "Use Case", "Strengths", "Weaknesses",
            "Algorithms", "Notes",
            "Source URL", "Source Type", "Last Updated",
        ],
    },
    "performance": {
        "file": "performance.csv",
        "search_cols": ["Topic", "Category", "Symptom", "Keywords"],
        "output_cols": [
            "Topic", "Category", "Symptom", "Root Cause", "Fix", "Tooling",
            "Severity", "Notes",
            "Source URL", "Source Type", "Last Updated",
        ],
    },
    "reliability": {
        "file": "reliability.csv",
        "search_cols": ["Topic", "Category", "Failure Mode", "Keywords"],
        "output_cols": [
            "Topic", "Category", "Failure Mode", "Mitigation", "Do", "Don't",
            "Metric", "Notes",
            "Source URL", "Source Type", "Last Updated",
        ],
    },
    "data": {
        "file": "data-engineering.csv",
        "search_cols": ["Name", "Category", "Use Case", "Keywords"],
        "output_cols": [
            "Name", "Category", "Workload", "Use Case", "Strengths", "Weaknesses",
            "Tooling", "Notes",
            "Source URL", "Source Type", "Last Updated",
        ],
    },
    "antipattern": {
        "file": "anti-patterns.csv",
        "search_cols": ["Name", "Category", "Symptom", "Root Cause", "Keywords"],
        "output_cols": [
            "Name", "Category", "Symptom", "Root Cause", "Why It's Tempting",
            "Fix", "Related Patterns", "Severity", "Source URL", "Source Type", "Last Updated",
        ],
    },
    "cost": {
        "file": "cost.csv",
        "search_cols": ["Name", "Category", "Cloud", "Service", "Cost Driver", "Mitigation"],
        "output_cols": [
            "Name", "Category", "Cloud", "Service", "Cost Driver", "Mitigation",
            "Order of Magnitude", "Gotcha", "Source URL", "Source Type", "Last Updated",
        ],
    },
    "migration": {
        "file": "migration.csv",
        "search_cols": ["Name", "Category", "Strategy", "From", "To", "Risk"],
        "output_cols": [
            "Name", "Category", "Strategy", "From", "To", "Risk", "Rollback Plan",
            "Duration Estimate", "Gotcha", "Related Patterns", "Source URL", "Source Type", "Last Updated",
        ],
    },
    "incident": {
        "file": "incident.csv",
        "search_cols": ["Name", "Category", "Severity", "Symptom", "Root Cause", "Mitigation"],
        "output_cols": [
            "Name", "Category", "Severity", "Symptom", "Root Cause", "Mitigation",
            "Communication Template", "Postmortem Checklist", "Source URL", "Source Type", "Last Updated",
        ],
    },
    "capacity": {
        "file": "capacity.csv",
        "search_cols": ["Name", "Category", "Formula", "Inputs", "Rule of Thumb"],
        "output_cols": [
            "Name", "Category", "Formula", "Inputs", "Example Calculation",
            "Rule of Thumb", "Gotcha", "Source URL", "Source Type", "Last Updated",
        ],
    },
    "compliance": {
        "file": "compliance.csv",
        "search_cols": ["Name", "Standard", "Category", "Engineering Requirement", "Verification Method"],
        "output_cols": [
            "Name", "Standard", "Category", "Engineering Requirement", "Verification Method",
            "Gotcha", "Penalty", "Source URL", "Source Type", "Last Updated",
        ],
    },
    "multi-tenant": {
        "file": "multi-tenant.csv",
        "search_cols": ["Name", "Category", "Strategy", "Isolation Level", "Strengths", "Weaknesses"],
        "output_cols": [
            "Name", "Category", "Strategy", "Isolation Level", "Strengths", "Weaknesses",
            "When to Use", "Gotcha", "Source URL", "Source Type", "Last Updated",
        ],
    },
    "release": {
        "file": "release.csv",
        "search_cols": ["Name", "Category", "Strategy", "Risk", "Tooling"],
        "output_cols": [
            "Name", "Category", "Strategy", "Risk", "Rollback Time", "Blast Radius",
            "Tooling", "Gotcha", "Source URL", "Source Type", "Last Updated",
        ],
    },
    "ml-platform": {
        "file": "ml-platform.csv",
        "search_cols": ["Name", "Category", "Use Case", "Strengths", "Alternatives"],
        "output_cols": [
            "Name", "Category", "Use Case", "Strengths", "Weaknesses",
            "Alternatives", "Gotcha", "Source URL", "Source Type", "Last Updated",
        ],
    },
    "edge": {
        "file": "edge.csv",
        "search_cols": ["Name", "Category", "Runtime", "Use Case", "Strengths"],
        "output_cols": [
            "Name", "Category", "Runtime", "Use Case", "Strengths", "Weaknesses",
            "Consistency Model", "Gotcha", "Source URL", "Source Type", "Last Updated",
        ],
    },
    "mobile-backend": {
        "file": "mobile-backend.csv",
        "search_cols": ["Name", "Category", "Pattern", "Use Case", "Strengths"],
        "output_cols": [
            "Name", "Category", "Pattern", "Use Case", "Strengths", "Weaknesses",
            "Gotcha", "Source URL", "Source Type", "Last Updated",
        ],
    },
    "api-contract": {
        "file": "api-contract.csv",
        "search_cols": ["Name", "Category", "Strategy", "Tooling", "Strengths"],
        "output_cols": [
            "Name", "Category", "Strategy", "Tooling", "Strengths", "Weaknesses",
            "When to Use", "Gotcha", "Source URL", "Source Type", "Last Updated",
        ],
    },
    "interview": {
        "file": "interview.csv",
        "search_cols": ["Name", "Category", "Level", "Key Signals", "Common Mistakes"],
        "output_cols": [
            "Name", "Category", "Level", "Key Signals", "Common Mistakes",
            "Evaluation Criteria", "Source URL", "Source Type", "Last Updated",
        ],
    },
    "latency": {
        "file": "latency-numbers.csv",
        "search_cols": ["Operation", "Category", "Latency", "Notes", "Hardware Era"],
        "output_cols": [
            "Operation", "Category", "Latency", "Order of Magnitude",
            "Hardware Era", "Notes", "Source URL", "Source Type", "Last Updated",
        ],
    },
}

STACK_CONFIG = {
    "go":              {"file": "stacks/go.csv"},
    "java-spring":     {"file": "stacks/java-spring.csv"},
    "python-fastapi":  {"file": "stacks/python-fastapi.csv"},
    "nodejs-express":  {"file": "stacks/nodejs-express.csv"},
    "rust-axum":       {"file": "stacks/rust-axum.csv"},
    "csharp-aspnet":   {"file": "stacks/csharp-aspnet.csv"},
    "kotlin-spring":   {"file": "stacks/kotlin-spring.csv"},
    "scala-akka":      {"file": "stacks/scala-akka.csv"},
    "elixir-phoenix":  {"file": "stacks/elixir-phoenix.csv"},
    "ruby-rails":      {"file": "stacks/ruby-rails.csv"},
    "php-laravel":     {"file": "stacks/php-laravel.csv"},
    "cpp":             {"file": "stacks/cpp.csv"},
}

# Common columns for all stacks
_STACK_COLS = {
    "search_cols": ["Category", "Guideline", "Description", "Do", "Don't"],
    "output_cols": ["Category", "Guideline", "Description", "Do", "Don't",
                    "Code Good", "Code Bad", "Severity", "Docs URL",
                    "Source URL", "Last Updated"],
}

AVAILABLE_STACKS = list(STACK_CONFIG.keys())


# ============ BM25 IMPLEMENTATION ============
class BM25:
    """BM25 ranking algorithm for text search."""

    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.corpus = []
        self.doc_lengths = []
        self.avgdl = 0
        self.idf = {}
        self.doc_freqs = defaultdict(int)
        self.N = 0

    def tokenize(self, text):
        """Lowercase, split, remove punctuation, filter very short words."""
        text = re.sub(r'[^\w\s]', ' ', str(text).lower())
        return [w for w in text.split() if len(w) > 1]

    def fit(self, documents):
        self.corpus = [self.tokenize(doc) for doc in documents]
        self.N = len(self.corpus)
        if self.N == 0:
            return
        self.doc_lengths = [len(doc) for doc in self.corpus]
        self.avgdl = sum(self.doc_lengths) / self.N if self.N else 0

        for doc in self.corpus:
            for word in set(doc):
                self.doc_freqs[word] += 1

        for word, freq in self.doc_freqs.items():
            self.idf[word] = log((self.N - freq + 0.5) / (freq + 0.5) + 1)

    def score(self, query):
        query_tokens = self.tokenize(query)
        scores = []
        for idx, doc in enumerate(self.corpus):
            doc_len = self.doc_lengths[idx]
            term_freqs = defaultdict(int)
            for word in doc:
                term_freqs[word] += 1

            score = 0.0
            for token in query_tokens:
                if token in self.idf:
                    tf = term_freqs[token]
                    idf = self.idf[token]
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                    score += idf * numerator / denominator if denominator else 0
            scores.append((idx, score))
        return sorted(scores, key=lambda x: x[1], reverse=True)


# ============ SEARCH FUNCTIONS ============
def _load_csv(filepath):
    with open(filepath, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


# ----- Synonym expansion (lightweight hybrid search) -----
# Map a token -> list of additional tokens to add to the query. Keep it
# conservative: only well-known backend / distributed-systems aliases.
_SYNONYMS = {
    "failure":     ["fault", "outage", "error"],
    "partial":     ["compensation", "rollback"],
    "compensate":  ["saga", "rollback"],
    "rollback":    ["compensation", "saga"],
    "retry":       ["backoff", "idempotent", "idempotency"],
    "idempotent":  ["idempotency", "deduplication"],
    "queue":       ["broker", "messaging", "topic"],
    "broker":      ["queue", "messaging"],
    "pubsub":      ["topic", "broker", "messaging"],
    "throttle":    ["rate", "limit", "ratelimit"],
    "ratelimit":   ["throttle", "quota"],
    "latency":     ["performance", "p99", "tail"],
    "throughput":  ["performance", "qps", "rps"],
    "outage":      ["failure", "incident", "downtime"],
    "incident":    ["outage", "postmortem", "runbook"],
    "consensus":   ["raft", "paxos", "quorum"],
    "consistency": ["linearizable", "causal", "quorum"],
    "shard":       ["partition", "sharding"],
    "partition":   ["shard", "sharding"],
    "replica":     ["replication", "follower"],
    "cache":       ["caching", "memoization"],
    "auth":        ["authentication", "authorization", "oauth", "jwt"],
    "secret":      ["vault", "kms", "credentials"],
    "trace":       ["tracing", "span", "opentelemetry"],
    "log":         ["logging", "logs"],
    "metric":      ["metrics", "prometheus"],
    "ddd":         ["domain", "bounded", "context"],
    "graphql":     ["api", "schema"],
    "rest":        ["api", "http"],
    "grpc":        ["rpc", "protobuf"],
    # Product-name aliases — users often drop spaces ("cosmosdb" vs "Cosmos DB").
    # We expand the no-space form to the multi-token form so BM25 can match.
    "cosmosdb":    ["cosmos", "db"],
    "dynamodb":    ["dynamo", "db"],
    "documentdb": ["document", "db"],
    "mongodb":     ["mongo", "db"],
    "couchdb":     ["couch", "db"],
    "cockroachdb": ["cockroach", "db"],
    "scylladb":    ["scylla", "db"],
    "influxdb":    ["influx", "db"],
    "rocksdb":     ["rocks", "db"],
    "timescaledb": ["timescale", "db"],
    "clickhouse":  ["click", "house", "olap"],
    "bigquery":    ["big", "query"],
    "bigtable":    ["big", "table"],
    "elasticsearch": ["elastic", "search"],
    "opensearch":  ["open", "search"],
    "rabbitmq":    ["rabbit", "mq", "amqp"],
    "activemq":    ["active", "mq"],
    "kubernetes":  ["k8s"],
    "k8s":         ["kubernetes"],
    "postgresql":  ["postgres"],
    "postgres":    ["postgresql"],
}


def _expand_query(query):
    """Append synonyms for known tokens. Returns the augmented query string."""
    tokens = re.findall(r'\w+', query.lower())
    extras = []
    for t in tokens:
        if t in _SYNONYMS:
            extras.extend(_SYNONYMS[t])
    if not extras:
        return query
    return query + " " + " ".join(extras)


# ----- Index cache (lazy, mtime-invalidated) -----
# _INDEX_CACHE[filepath_str] = {"mtime": float, "data": [rows], "bm25": BM25, "search_cols": [...]}
_INDEX_CACHE = {}


def clear_cache():
    """Drop all cached BM25 indexes (useful for tests / long-running processes)."""
    _INDEX_CACHE.clear()


def _get_index(filepath, search_cols):
    """Return (data, bm25) for filepath, building & caching on first use,
    invalidating when the file's mtime changes or search_cols changes."""
    key = str(filepath)
    try:
        mtime = filepath.stat().st_mtime
    except OSError:
        return None, None

    cached = _INDEX_CACHE.get(key)
    if (
        cached
        and cached["mtime"] == mtime
        and cached["search_cols"] == tuple(search_cols)
    ):
        return cached["data"], cached["bm25"]

    data = _load_csv(filepath)
    documents = [" ".join(str(row.get(col, "")) for col in search_cols) for row in data]
    bm25 = BM25()
    bm25.fit(documents)
    _INDEX_CACHE[key] = {
        "mtime": mtime,
        "data": data,
        "bm25": bm25,
        "search_cols": tuple(search_cols),
    }
    return data, bm25


# ----- Freshness helpers -----
_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y")


def _parse_date(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _months_since(dt, now=None):
    now = now or datetime.now()
    return (now.year - dt.year) * 12 + (now.month - dt.month)


def _is_stale(row, max_age_months):
    """True if row has a Last Updated column older than max_age_months.
    Rows with no/invalid date are NOT considered stale (avoid false positives)."""
    if max_age_months is None:
        return False
    dt = _parse_date(row.get("Last Updated", "") or row.get("Updated", ""))
    if dt is None:
        return False
    return _months_since(dt) > max_age_months


_warned_semantic = False


# ============ CITATION TOKENS ============
def _slugify(text, max_len=40):
    """Convert text to a stable, URL-safe slug: lowercase, hyphens, no specials."""
    s = str(text).lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)   # strip non-alphanumeric
    s = re.sub(r"[\s_]+", "-", s)          # spaces/underscores → hyphens
    s = re.sub(r"-{2,}", "-", s)           # collapse runs of hyphens
    s = s.strip("-")
    return s[:max_len].rstrip("-") if s else "unknown"


def _row_name(row):
    """Extract the best identifier from a row dict."""
    for key in ("Name", "Service", "Technology", "Pattern", "Category", "Guideline"):
        val = str(row.get(key, "")).strip()
        if val:
            return val
    # Last resort — first non-empty value.
    for v in row.values():
        val = str(v).strip()
        if val:
            return val
    return "unknown"


def _make_citation(domain, row, column=None):
    """Build a citation token: ``[BPM:<domain>.<name_slug>]``.

    If *column* is given, appends a third segment:
    ``[BPM:<domain>.<name_slug>.<column_slug>]``.
    """
    name_slug = _slugify(_row_name(row))
    parts = [domain, name_slug]
    if column:
        parts.append(_slugify(column))
    return "[BPM:" + ".".join(parts) + "]"


def _inject_citations(results, domain):
    """Add ``_citation`` to each result row in-place."""
    for row in results:
        row["_citation"] = _make_citation(domain, row)


def _search_csv(filepath, search_cols, output_cols, query, max_results,
                *, min_score=0.0, max_age_months=None, expand=True, engine="bm25"):
    global _warned_semantic
    if not filepath.exists():
        return []

    data, bm25 = _get_index(filepath, search_cols)
    if data is None or bm25 is None or bm25.N == 0:
        return []

    effective_query = _expand_query(query) if expand else query
    bm25_ranked = bm25.score(effective_query)

    # Determine final ranking based on engine choice.
    if engine in ("hybrid", "semantic"):
        try:
            from . import semantic as _sem  # type: ignore[import]
        except ImportError:
            try:
                import semantic as _sem  # type: ignore[import,no-redef]
            except ImportError:
                _sem = None

        if _sem is not None and _sem.is_available():
            cache_key = _sem.build_index(data, search_cols, filepath)
            if cache_key is not None:
                embed_ranked = _sem.semantic_search(query, cache_key, top_k=max(20, max_results * 4))
                if engine == "semantic":
                    ranked = embed_ranked
                else:
                    # hybrid: RRF merge
                    ranked = _sem.reciprocal_rank_fusion(bm25_ranked, embed_ranked)
            else:
                ranked = bm25_ranked
        else:
            if not _warned_semantic:
                _warned_semantic = True
                import sys as _sys
                print(
                    "⚠️  sentence-transformers not installed — falling back to BM25. "
                    "Install with: pip install backendpro[semantic]",
                    file=_sys.stderr,
                )
            ranked = bm25_ranked
    else:
        ranked = bm25_ranked

    results = []
    for idx, score in ranked:
        if len(results) >= max_results:
            break
        if score <= min_score:
            continue
        row = data[idx]
        if max_age_months is not None and _is_stale(row, max_age_months):
            continue
        out = {col: row.get(col, "") for col in output_cols if col in row}
        # Surface "Last Updated" if present even when not in output_cols
        if "Last Updated" in row and "Last Updated" not in out:
            out["Last Updated"] = row["Last Updated"]
        out["_score"] = round(float(score), 4)
        results.append(out)
    return results


# Domain auto-detection (keyword bag per domain).
_DOMAIN_KEYWORDS = {
    "language":      ["language", "go", "golang", "java", "python", "rust", "node", "nodejs", "kotlin",
                      "scala", "elixir", "ruby", "php", "c#", "csharp", "c++", "cpp", "typescript", "jvm",
                      "runtime", "compiler", "interpreter", "gc", "garbage collector"],
    "pattern":       ["saga", "cqrs", "event sourcing", "outbox", "circuit breaker", "bulkhead",
                      "leader election", "retry", "throttling", "rate limit", "idempot", "two-phase",
                      "2pc", "transactional outbox", "sidecar", "ambassador", "anti-corruption",
                      "strangler", "fan-out", "scatter-gather", "competing consumer"],
    "database":      ["database", "db", "rdbms", "sql", "nosql", "postgres", "postgresql", "mysql",
                      "mariadb", "mongo", "mongodb", "cassandra", "scylla", "dynamodb", "redis",
                      "elastic", "elasticsearch", "opensearch", "clickhouse", "neo4j", "cockroach",
                      "spanner", "tidb", "timeseries", "influx", "timescale", "vector db", "qdrant",
                      "pinecone", "milvus", "weaviate", "graph db"],
    "messaging":     ["kafka", "rabbitmq", "rabbit", "nats", "pulsar", "sqs", "sns", "kinesis",
                      "eventbridge", "broker", "queue", "topic", "partition", "consumer group",
                      "pub/sub", "pubsub", "stream", "amqp", "mqtt", "jetstream"],
    "cache":         ["cache", "caching", "redis", "memcached", "hazelcast", "cdn", "cloudflare",
                      "fastly", "akamai", "ttl", "lru", "lfu", "write-through", "write-back",
                      "cache aside", "stampede"],
    "cloud":         ["aws", "gcp", "google cloud", "azure", "lambda", "fargate", "ec2", "ecs",
                      "eks", "gke", "aks", "s3", "gcs", "blob storage", "cloudfront", "route53",
                      "cloud run", "app engine", "app service", "rds", "aurora", "dynamodb",
                      "bigquery", "redshift", "synapse", "iam", "vpc", "subnet", "security group",
                      "managed service"],
    "iac":           ["terraform", "pulumi", "cloudformation", "cdk", "ansible", "chef", "puppet",
                      "salt", "bicep", "crossplane", "infrastructure as code", "iac"],
    "container":     ["docker", "kubernetes", "k8s", "helm", "kustomize", "istio", "linkerd",
                      "envoy", "service mesh", "containerd", "podman", "ecs", "fargate",
                      "openshift", "argo", "argocd", "fluxcd", "flux"],
    "observability": ["observability", "metrics", "logs", "logging", "tracing", "trace", "span",
                      "prometheus", "grafana", "loki", "tempo", "jaeger", "zipkin", "opentelemetry",
                      "otel", "datadog", "newrelic", "splunk", "elk", "elastic stack",
                      "alerting", "pager", "pagerduty", "sli", "slo", "sla", "rum"],
    "api":           ["rest", "graphql", "grpc", "openapi", "swagger", "asyncapi", "websocket",
                      "websockets", "sse", "server-sent events", "json:api", "hateoas", "rpc",
                      "soap", "json schema", "protobuf", "thrift", "avro"],
    "auth":          ["oauth", "oauth2", "oidc", "openid", "jwt", "saml", "mtls", "mutual tls",
                      "session", "cookie", "sso", "single sign on", "rbac", "abac", "scim",
                      "passkey", "webauthn", "spiffe", "spire"],
    "security":      ["owasp", "csrf", "xss", "sqli", "sql injection", "ssrf", "xxe", "rce",
                      "csp", "cors", "secret", "vault", "kms", "hsm", "encryption", "tls",
                      "mtls", "zero trust", "supply chain", "sbom", "sast", "dast", "iast",
                      "vulnerab", "cve", "hardening"],
    "cicd":          ["ci", "cd", "ci/cd", "github actions", "gitlab ci", "jenkins", "circleci",
                      "buildkite", "drone", "tekton", "argo workflows", "argocd", "fluxcd",
                      "spinnaker", "harness", "pipeline"],
    "testing":       ["unit test", "integration test", "e2e", "end to end", "contract test",
                      "pact", "mock", "stub", "fake", "fuzz", "property based", "hypothesis",
                      "load test", "k6", "jmeter", "locust", "gatling", "chaos", "chaos monkey",
                      "litmus", "test pyramid", "tdd", "bdd"],
    "architecture":  ["monolith", "microservice", "microservices", "modular monolith", "soa",
                      "serverless", "event driven", "event-driven", "hexagonal", "ports and adapters",
                      "clean architecture", "onion architecture", "ddd", "domain driven",
                      "bounded context", "actor model", "lambda architecture", "kappa architecture"],
    "scaling":       ["horizontal scale", "vertical scale", "autoscale", "autoscaling", "sharding",
                      "shard", "replication", "read replica", "partition", "consistent hashing",
                      "load balanc", "haproxy", "nginx", "envoy", "anycast", "geo", "edge"],
    "consistency":   ["cap", "pacelc", "consensus", "paxos", "raft", "zab", "leader election",
                      "linearizab", "strong consistency", "eventual consistency", "causal",
                      "quorum", "vector clock", "crdt", "lamport", "two phase commit", "2pc",
                      "three phase commit", "3pc"],
    "performance":   ["latency", "throughput", "p99", "p95", "tail latency", "n+1", "profiling",
                      "flame graph", "perf", "pprof", "async-profiler", "gc pause", "connection pool",
                      "index", "query plan", "explain", "hot path", "back pressure",
                      "backpressure"],
    "reliability":   ["sla", "slo", "sli", "error budget", "retry", "timeout", "deadline",
                      "circuit breaker", "bulkhead", "fallback", "graceful degradation",
                      "blast radius", "blast-radius", "disaster recovery", "rpo", "rto",
                      "chaos", "fault tolerance", "resilien"],
    "data":          ["etl", "elt", "data warehouse", "data lake", "lakehouse", "spark",
                      "flink", "beam", "airflow", "dagster", "prefect", "dbt", "snowflake",
                      "bigquery", "redshift", "delta lake", "iceberg", "hudi", "kafka connect",
                      "debezium", "cdc", "change data capture", "batch", "streaming"],
    "antipattern":   ["anti-pattern", "antipattern", "anti pattern", "don't", "avoid",
                      "distributed monolith", "god service", "dual writes", "dual write",
                      "chatty microservice", "unbounded retry", "n+1", "log and throw",
                      "log-and-throw", "error swallowing", "shared database integration",
                      "sync-over-async", "sync over async", "premature microservice",
                      "missing idempotency", "secrets in env", "polling instead",
                      "time-based cache", "bad practice", "code smell", "pitfall"],
    "cost":          ["cost", "pricing", "egress", "data transfer", "finops", "billing",
                      "expensive", "cheap", "price", "spend", "budget", "invoice",
                      "cross-az", "nat gateway", "reserved instance", "spot instance",
                      "on-demand", "savings plan"],
    "migration":     ["migrate", "migration", "strangler", "strangler fig", "dual write",
                      "cutover", "zero-downtime", "expand-contract", "blue-green migration",
                      "trickle", "parallel run", "cloud migration", "database migration",
                      "replatform", "lift and shift"],
    "incident":      ["incident", "outage", "postmortem", "severity", "sev1", "sev2",
                      "imoc", "incident commander", "status page", "runbook",
                      "blameless", "cascading failure", "root cause analysis", "rca",
                      "communication template", "war room"],
    "capacity":      ["capacity", "little's law", "littles law", "amdahl", "usl",
                      "qps calculation", "storage estimation", "bandwidth estimation",
                      "back of envelope", "back-of-envelope", "connection pool size",
                      "partition sizing", "queue theory"],
    "compliance":    ["compliance", "soc2", "soc 2", "hipaa", "pci", "pci-dss", "gdpr",
                      "ccpa", "audit", "data residency", "encryption at rest",
                      "data breach notification", "right to deletion", "consent",
                      "regulatory", "data protection"],
    "multi-tenant":  ["multi-tenant", "multitenant", "tenant", "tenancy", "noisy neighbor",
                      "noisy neighbour", "tenant isolation", "pool model", "silo model",
                      "row-level security", "rls", "shared nothing", "shared everything",
                      "per-tenant"],
    "release":       ["release", "deployment strategy", "canary", "blue-green", "blue green",
                      "rolling update", "feature flag", "feature toggle", "dark launch",
                      "progressive delivery", "gitops", "deployment freeze", "rollback",
                      "release train", "immutable infrastructure", "ring deployment"],
    "ml-platform":   ["ml platform", "mlops", "feature store", "model registry",
                      "experiment tracking", "training serving skew", "ml pipeline",
                      "model monitoring", "gpu management", "rag", "retrieval augmented",
                      "vector database", "fine-tuning", "fine tuning", "lora", "qlora"],
    "edge":          ["edge compute", "edge computing", "cloudflare workers", "fastly compute",
                      "lambda@edge", "cloudfront functions", "vercel edge", "durable objects",
                      "wasi", "webassembly", "wasm", "edge kv", "edge database"],
    "mobile-backend": ["mobile backend", "mobile api", "bff", "backend for frontend",
                       "offline-first", "offline first", "push notification", "apns", "fcm",
                       "token refresh", "app startup", "image optimization",
                       "optimistic ui", "mobile sync"],
    "api-contract":  ["api contract", "openapi", "swagger", "graphql federation",
                      "schema evolution", "schema registry", "protobuf", "asyncapi",
                      "contract testing", "pact", "api versioning", "hateoas",
                      "grpc-web", "api gateway pattern", "code generation", "codegen"],
    "interview":     ["interview", "system design interview", "rubric", "evaluation criteria",
                      "key signals", "leveling", "staff engineer interview",
                      "trade-off analysis", "back of envelope", "hiring",
                      "system design rubric", "behavioral interview"],
    "latency":       ["latency numbers", "latency reference", "l1 cache", "l2 cache",
                      "memory latency", "disk latency", "nvme latency", "network latency",
                      "cross-region latency", "ssd latency", "hdd seek",
                      "latency comparison", "speed of light"],
}


def detect_domain(query):
    """Auto-detect the most relevant domain from query."""
    q = query.lower()
    scores = {}
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if " " in kw:
                if kw in q:
                    score += 2
            elif re.search(r'\b' + re.escape(kw) + r'\b', q):
                score += 1
        scores[domain] = score
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "pattern"


# ============ INTENT CLASSIFICATION ============
class Intent(enum.Enum):
    """Query intent — determines output template shape."""
    DEFINITION = "definition"
    COMPARISON = "comparison"
    TROUBLESHOOT = "troubleshoot"
    DESIGN = "design"
    MIGRATION = "migration"
    INCIDENT = "incident"
    GENERAL = "general"


# Each intent has a list of (pattern, weight) tuples. First match with
# highest total weight wins.  Patterns are checked against the lowercased
# query.  We keep this deliberately high-precision (few false positives)
# and fall back to GENERAL on low confidence.

_INTENT_PATTERNS: dict = {
    Intent.COMPARISON: [
        # "X vs Y", "X or Y", "X versus Y", "compare X Y", "difference between X and Y"
        (r'\bvs\.?\b', 3),
        (r'\bversus\b', 3),
        (r'\bcompare\b', 3),
        (r'\bcomparison\b', 3),
        (r'\bdifference(?:s)?\s+between\b', 3),
        (r'\bor\b', 1),  # weak — needs other signal
    ],
    Intent.DEFINITION: [
        (r'^what\s+is\b', 3),
        (r'^explain\b', 3),
        (r'^define\b', 3),
        (r'^describe\b', 2),
        (r'\bdefinition\b', 3),
        (r'^how\s+does\b.*\bwork\b', 2),
        (r'^what\s+are\b', 2),
    ],
    Intent.TROUBLESHOOT: [
        (r'\btroubleshoot\b', 3),
        (r'\bdebug\b', 2),
        (r'\bfix\b', 2),
        (r'\berror\b', 2),
        (r'\bfail(?:s|ure|ing|ed)?\b', 2),
        (r'\btimeout\b', 2),
        (r'\blag\b', 2),
        (r'\bslow\b', 2),
        (r'\bcrash\b', 2),
        (r'\bhigh\s+(?:cpu|memory|latency)\b', 2),
        (r'\bconnection\s+(?:pool|refused|reset)\b', 2),
        (r'\bout\s+of\s+memory\b', 3),
        (r'\bexhaust\b', 2),
        (r'\bleak\b', 2),
        (r'\bwhy\s+(?:is|does|do|are)\b', 1),
    ],
    Intent.DESIGN: [
        (r'^design\b', 3),
        (r'\bsystem\s+design\b', 3),
        (r'\barchitect(?:ure)?\s+(?:for|of|a)\b', 2),
        (r'\bhow\s+(?:to|would)\s+(?:build|design|architect)\b', 3),
    ],
    Intent.MIGRATION: [
        (r'\bmigrat(?:e|ion|ing)\b', 3),
        (r'\bmove\s+from\b', 3),
        (r'\bswitch\s+from\b', 3),
        (r'\breplace\b.*\bwith\b', 2),
        (r'\btransition\s+(?:from|to)\b', 2),
        (r'\bupgrade\s+from\b', 2),
    ],
    Intent.INCIDENT: [
        (r'\bincident\b', 3),
        (r'\boutage\b', 3),
        (r'\bfailover\b', 2),
        (r'\bpostmortem\b', 3),
        (r'\bdowntime\b', 2),
        (r'\bdisaster\b', 2),
        (r'\brecovery\b', 1),
        (r'\brunbook\b', 3),
    ],
}


def classify_intent(query: str) -> "Intent":
    """Classify a query into an Intent using keyword/regex patterns.

    Conservative: defaults to GENERAL when confidence is low.
    """
    q = query.lower().strip()
    if not q:
        return Intent.GENERAL

    intent_scores: dict = {}
    for intent, patterns in _INTENT_PATTERNS.items():
        total = 0
        for pattern, weight in patterns:
            if re.search(pattern, q):
                total += weight
        if total > 0:
            intent_scores[intent] = total

    if not intent_scores:
        return Intent.GENERAL

    best_intent = max(intent_scores, key=intent_scores.get)
    best_score = intent_scores[best_intent]

    # Require minimum confidence of 2 to avoid false positives from
    # single weak signals (e.g. "or" alone triggering COMPARISON).
    if best_score < 2:
        return Intent.GENERAL

    return best_intent


# ============ CONSTRAINT FILTERING ============
# Columns that carry structured constraint metadata.
CONSTRAINT_COLUMNS = [
    "Throughput Tier", "Latency Tier", "Consistency Tier", "Cost Tier", "Cloud Native",
]

# Known tier orderings (lower index = more demanding / better).
_TIER_ORDER = {
    "throughput": ["low", "medium", "high", "very-high"],
    "latency": ["sub-ms", "low-ms", "tens-ms", "hundreds-ms", "seconds"],
    "consistency": ["none", "eventual", "tunable", "strong"],
    "cost": ["free", "low", "medium", "medium-high", "high", "very-high"],
}

# Map short constraint key names to CSV column names.
_CONSTRAINT_COL_MAP = {
    "throughput": "Throughput Tier",
    "latency": "Latency Tier",
    "consistency": "Consistency Tier",
    "cost": "Cost Tier",
    "cloud": "Cloud Native",
}


def parse_constraints(constraint_str):
    """Parse a constraint string like 'cloud=gcp,latency=low-ms,consistency=strong'.

    Returns a dict: {key: value} where key is a short name (cloud, latency, …).
    """
    if not constraint_str:
        return {}
    constraints = {}
    for part in constraint_str.split(","):
        part = part.strip()
        if "=" not in part:
            continue
        key, _, val = part.partition("=")
        key = key.strip().lower()
        val = val.strip().lower()
        if key and val:
            constraints[key] = val
    return constraints


def apply_constraints(results, constraints):
    """Post-filter search results against structured constraint columns.

    Each result is annotated with a `_constraints` dict:
      {constraint_key: {"value": csv_value, "wanted": user_value, "match": bool|"unknown"}}
    Results are re-sorted by number of satisfied constraints (descending),
    then by BM25 score.
    """
    if not constraints:
        return results

    for row in results:
        row["_constraints"] = {}
        for key, wanted in constraints.items():
            col = _CONSTRAINT_COL_MAP.get(key)
            if not col:
                continue
            actual = str(row.get(col, "")).strip().lower()
            if not actual:
                row["_constraints"][key] = {"value": "", "wanted": wanted, "match": "unknown"}
                continue

            if key == "cloud":
                # Cloud is comma-separated list; check if wanted value is in it.
                parts = [p.strip() for p in actual.split(",")]
                match = wanted in parts or actual == "multi"
            elif key in _TIER_ORDER:
                # For ordered tiers, check if actual meets or exceeds wanted.
                order = _TIER_ORDER[key]
                try:
                    actual_idx = order.index(actual)
                    wanted_idx = order.index(wanted)
                    if key in ("latency", "cost"):
                        # Lower is better — actual index should be <= wanted.
                        match = actual_idx <= wanted_idx
                    else:
                        # Higher is better — actual index should be >= wanted.
                        match = actual_idx >= wanted_idx
                except ValueError:
                    match = actual == wanted
            else:
                match = actual == wanted

            row["_constraints"][key] = {"value": actual, "wanted": wanted, "match": match}

    # Sort: most constraints satisfied first, then by BM25 score.
    def _sort_key(row):
        cm = row.get("_constraints", {})
        satisfied = sum(1 for v in cm.values() if v["match"] is True)
        return (-satisfied, -float(row.get("_score", 0.0)))

    results.sort(key=_sort_key)
    return results


def search(query, domain=None, max_results=MAX_RESULTS,
           *, min_score=0.0, max_age_months=None, expand=True, engine="bm25"):
    """Main search function with auto-domain detection.

    Args:
        query: Search string.
        domain: Force a specific domain (auto-detected if None).
        max_results: Cap on returned rows.
        min_score: Drop rows whose BM25 score is <= this (default 0.0).
        max_age_months: If set, drop rows whose `Last Updated` column is older
            than this many months. Rows without a date are kept.
        expand: Apply synonym expansion to the query (default True).
        engine: Search engine — "bm25" (default), "hybrid", or "semantic".
    """
    if domain is None:
        domain = detect_domain(query)

    config = CSV_CONFIG.get(domain)
    if config is None:
        return {"error": f"Unknown domain: {domain}. Available: {', '.join(CSV_CONFIG)}"}

    filepath = DATA_DIR / config["file"]
    if not filepath.exists():
        return {"error": f"File not found: {filepath}", "domain": domain}

    results = _search_csv(
        filepath, config["search_cols"], config["output_cols"], query, max_results,
        min_score=min_score, max_age_months=max_age_months, expand=expand, engine=engine,
    )
    _inject_citations(results, domain)

    return {
        "domain": domain,
        "query": query,
        "file": config["file"],
        "count": len(results),
        "results": results,
    }


def search_stack(query, stack, max_results=MAX_RESULTS,
                 *, min_score=0.0, expand=True, engine="bm25"):
    """Search stack-specific guidelines."""
    if stack not in STACK_CONFIG:
        return {"error": f"Unknown stack: {stack}. Available: {', '.join(AVAILABLE_STACKS)}"}

    filepath = DATA_DIR / STACK_CONFIG[stack]["file"]
    if not filepath.exists():
        return {"error": f"Stack file not found: {filepath}", "stack": stack}

    results = _search_csv(
        filepath, _STACK_COLS["search_cols"], _STACK_COLS["output_cols"],
        query, max_results, min_score=min_score, expand=expand, engine=engine,
    )
    _inject_citations(results, f"stack-{stack}")

    return {
        "domain": "stack",
        "stack": stack,
        "query": query,
        "file": STACK_CONFIG[stack]["file"],
        "count": len(results),
        "results": results,
    }


def search_all(query, max_results=2, *, min_score=0.0, expand=True, engine="bm25"):
    """Cross-domain search: returns top hits across every domain CSV."""
    aggregated = {}
    for domain, config in CSV_CONFIG.items():
        filepath = DATA_DIR / config["file"]
        if not filepath.exists():
            continue
        hits = _search_csv(
            filepath, config["search_cols"], config["output_cols"],
            query, max_results, min_score=min_score, expand=expand, engine=engine,
        )
        if hits:
            _inject_citations(hits, domain)
            aggregated[domain] = hits
    return {"query": query, "domains": list(aggregated.keys()), "results": aggregated}


# ============ DECISION HELPERS ============
def compare(names, domain=None, max_per_name=1):
    """Side-by-side comparison of two or more named entries.

    Each name is searched independently (in `domain` if given, else
    auto-detected from the joined names). Returns a dict with one entry
    per name plus a `columns` union for easy table rendering.
    """
    if not names or len(names) < 2:
        return {"error": "compare needs at least two names."}

    auto_domain = domain or detect_domain(" ".join(names))
    config = CSV_CONFIG.get(auto_domain)
    if config is None:
        return {"error": f"Unknown domain: {auto_domain}"}

    entries = {}
    columns_seen = []
    missing = []
    suggestions = {}
    for name in names:
        result = search(name, domain=auto_domain, max_results=max(5, max_per_name * 5))
        rows = result.get("results", [])
        # Prefer rows whose first (identifier) column literally contains the
        # query name — staff engineers expect "compare Kafka" to surface the
        # Kafka row, not whatever happens to mention Kafka most often.
        name_l = name.lower()
        rows.sort(key=lambda r: (
            0 if name_l in str(next(iter(r.values()), "")).lower() else 1,
            -float(r.get("_score", 0.0)),
        ))
        top = rows[0] if rows else None
        # Treat as a real hit only when the identifier column actually
        # contains the queried name. Otherwise BM25 may surface a tangentially
        # related row (e.g. searching "cosmosdb" in `database` returns MongoDB
        # because of the "document" overlap) — that's misleading in a compare
        # table, so we mark it as missing and look elsewhere.
        found = bool(top) and name_l in str(next(iter(top.values()), "")).lower()
        # Normalised match: also accept hits where the user dropped spaces
        # ("cosmosdb" should match "Cosmos DB").
        if not found and top:
            head_l = str(next(iter(top.values()), "")).lower()
            if re.sub(r"\s+", "", name_l) in re.sub(r"\s+", "", head_l):
                found = True
        if found:
            entry = top
            entry["_citation"] = _make_citation(auto_domain, entry)
        else:
            entry = {}
            missing.append(name)
            # Cross-domain fallback: where else does this term actually live?
            cross = search_all(name, max_results=1)
            hints = []
            name_compact = re.sub(r"\s+", "", name_l)
            for d, hits in cross.get("results", {}).items():
                if d == auto_domain or not hits:
                    continue
                head = str(next(iter(hits[0].values()), "")).strip()
                head_compact = re.sub(r"\s+", "", head.lower())
                if name_compact in head_compact:
                    hints.append({"domain": d, "match": head})
            if hints:
                suggestions[name] = hints[:3]
        entries[name] = entry
        for col in entry.keys():
            if col not in columns_seen and col not in ("_score", "_citation"):
                columns_seen.append(col)

    return {
        "mode": "compare",
        "domain": auto_domain,
        "names": list(names),
        "columns": columns_seen,
        "entries": entries,
        "missing": missing,
        "suggestions": suggestions,
    }


def find_stale(domain, months):
    """Return rows in `domain` whose `Last Updated` is older than `months`.
    Rows without a date are skipped (not flagged)."""
    config = CSV_CONFIG.get(domain)
    if config is None:
        return {"error": f"Unknown domain: {domain}"}
    filepath = DATA_DIR / config["file"]
    if not filepath.exists():
        return {"error": f"File not found: {filepath}"}

    data = _load_csv(filepath)
    stale = []
    for row in data:
        dt = _parse_date(row.get("Last Updated", "") or row.get("Updated", ""))
        if dt is None:
            continue
        if _months_since(dt) > months:
            entry = {col: row.get(col, "") for col in config["output_cols"] if col in row}
            entry["Last Updated"] = row.get("Last Updated", row.get("Updated", ""))
            entry["_citation"] = _make_citation(domain, entry)
            stale.append(entry)
    return {
        "domain": domain,
        "file": config["file"],
        "older_than_months": months,
        "count": len(stale),
        "results": stale,
    }

