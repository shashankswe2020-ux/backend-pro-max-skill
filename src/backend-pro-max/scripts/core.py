#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backend Pro Max Core - BM25 search engine for backend / distributed-systems
knowledge bases.

Pure standard-library implementation (Python 3.8+). No external dependencies.
"""

import csv
import re
from pathlib import Path
from math import log
from collections import defaultdict

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
        ],
    },
    "pattern": {
        "file": "patterns.csv",
        "search_cols": ["Name", "Category", "Problem", "Keywords", "When to Use"],
        "output_cols": [
            "Name", "Category", "Problem", "Solution", "When to Use",
            "When NOT to Use", "Trade-offs", "Related Patterns", "Reference",
        ],
    },
    "database": {
        "file": "databases.csv",
        "search_cols": ["Name", "Category", "Use Case", "Strengths", "Keywords"],
        "output_cols": [
            "Name", "Category", "Data Model", "Consistency Model", "Replication",
            "Sharding", "Use Case", "Strengths", "Weaknesses", "Typical Latency",
            "Operational Cost", "Cloud Managed Options", "Notes",
        ],
    },
    "messaging": {
        "file": "messaging.csv",
        "search_cols": ["Name", "Category", "Use Case", "Delivery", "Keywords"],
        "output_cols": [
            "Name", "Category", "Delivery", "Ordering", "Throughput", "Latency",
            "Persistence", "Replay", "Use Case", "Strengths", "Weaknesses",
            "Cloud Managed Options", "Notes",
        ],
    },
    "cache": {
        "file": "cache.csv",
        "search_cols": ["Name", "Strategy", "Use Case", "Keywords"],
        "output_cols": [
            "Name", "Strategy", "Topology", "Eviction", "Consistency",
            "Use Case", "Strengths", "Weaknesses", "Pitfalls", "Notes",
        ],
    },
    "cloud": {
        "file": "cloud.csv",
        "search_cols": ["Service", "Provider", "Category", "Use Case", "Keywords"],
        "output_cols": [
            "Service", "Provider", "Category", "Equivalent AWS", "Equivalent GCP",
            "Equivalent Azure", "Use Case", "Strengths", "Weaknesses", "Pricing Model",
            "Notes",
        ],
    },
    "iac": {
        "file": "iac.csv",
        "search_cols": ["Name", "Category", "Use Case", "Keywords"],
        "output_cols": [
            "Name", "Category", "Language", "Provider Coverage", "State Management",
            "Strengths", "Weaknesses", "Use Case", "Notes",
        ],
    },
    "container": {
        "file": "containers.csv",
        "search_cols": ["Name", "Category", "Use Case", "Keywords"],
        "output_cols": [
            "Name", "Category", "Layer", "Use Case", "Strengths", "Weaknesses",
            "Alternatives", "Notes",
        ],
    },
    "observability": {
        "file": "observability.csv",
        "search_cols": ["Tool", "Signal", "Use Case", "Keywords"],
        "output_cols": [
            "Tool", "Signal", "Type", "Open Source", "Use Case", "Strengths",
            "Weaknesses", "Integrations", "Notes",
        ],
    },
    "api": {
        "file": "api.csv",
        "search_cols": ["Style", "Use Case", "Keywords", "Transport"],
        "output_cols": [
            "Style", "Transport", "Schema", "Streaming", "Browser Friendly",
            "Backwards Compatibility", "Use Case", "Strengths", "Weaknesses",
            "Tooling", "Notes",
        ],
    },
    "auth": {
        "file": "auth.csv",
        "search_cols": ["Name", "Category", "Use Case", "Keywords"],
        "output_cols": [
            "Name", "Category", "Token Type", "Use Case", "Strengths", "Weaknesses",
            "Common Pitfalls", "Notes",
        ],
    },
    "security": {
        "file": "security.csv",
        "search_cols": ["Topic", "Category", "Threat", "Keywords"],
        "output_cols": [
            "Topic", "Category", "Threat", "Mitigation", "Do", "Don't",
            "Tooling", "Severity", "Reference",
        ],
    },
    "cicd": {
        "file": "cicd.csv",
        "search_cols": ["Tool", "Category", "Use Case", "Keywords"],
        "output_cols": [
            "Tool", "Category", "Hosting", "Use Case", "Strengths", "Weaknesses",
            "Notable Features", "Notes",
        ],
    },
    "testing": {
        "file": "testing.csv",
        "search_cols": ["Name", "Level", "Use Case", "Keywords"],
        "output_cols": [
            "Name", "Level", "Use Case", "Strengths", "Weaknesses", "Tooling",
            "Pitfalls", "Notes",
        ],
    },
    "architecture": {
        "file": "architecture.csv",
        "search_cols": ["Name", "Category", "Use Case", "Keywords"],
        "output_cols": [
            "Name", "Category", "When to Use", "When NOT to Use", "Strengths",
            "Weaknesses", "Team Size", "Operational Cost", "Notes",
        ],
    },
    "scaling": {
        "file": "scaling.csv",
        "search_cols": ["Technique", "Category", "Use Case", "Keywords"],
        "output_cols": [
            "Technique", "Category", "Layer", "Use Case", "Strengths", "Weaknesses",
            "Pitfalls", "Notes",
        ],
    },
    "consistency": {
        "file": "consistency.csv",
        "search_cols": ["Model", "Category", "Use Case", "Keywords"],
        "output_cols": [
            "Model", "Category", "Guarantees", "Use Case", "Strengths", "Weaknesses",
            "Algorithms", "Notes",
        ],
    },
    "performance": {
        "file": "performance.csv",
        "search_cols": ["Topic", "Category", "Symptom", "Keywords"],
        "output_cols": [
            "Topic", "Category", "Symptom", "Root Cause", "Fix", "Tooling",
            "Severity", "Notes",
        ],
    },
    "reliability": {
        "file": "reliability.csv",
        "search_cols": ["Topic", "Category", "Failure Mode", "Keywords"],
        "output_cols": [
            "Topic", "Category", "Failure Mode", "Mitigation", "Do", "Don't",
            "Metric", "Notes",
        ],
    },
    "data": {
        "file": "data-engineering.csv",
        "search_cols": ["Name", "Category", "Use Case", "Keywords"],
        "output_cols": [
            "Name", "Category", "Workload", "Use Case", "Strengths", "Weaknesses",
            "Tooling", "Notes",
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
                    "Code Good", "Code Bad", "Severity", "Docs URL"],
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
    with open(filepath, 'r', encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def _search_csv(filepath, search_cols, output_cols, query, max_results):
    if not filepath.exists():
        return []

    data = _load_csv(filepath)
    documents = [" ".join(str(row.get(col, "")) for col in search_cols) for row in data]

    bm25 = BM25()
    bm25.fit(documents)
    ranked = bm25.score(query)

    results = []
    for idx, score in ranked[:max_results]:
        if score > 0:
            row = data[idx]
            results.append({col: row.get(col, "") for col in output_cols if col in row})
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


def search(query, domain=None, max_results=MAX_RESULTS):
    """Main search function with auto-domain detection."""
    if domain is None:
        domain = detect_domain(query)

    config = CSV_CONFIG.get(domain)
    if config is None:
        return {"error": f"Unknown domain: {domain}. Available: {', '.join(CSV_CONFIG)}"}

    filepath = DATA_DIR / config["file"]
    if not filepath.exists():
        return {"error": f"File not found: {filepath}", "domain": domain}

    results = _search_csv(filepath, config["search_cols"], config["output_cols"], query, max_results)

    return {
        "domain": domain,
        "query": query,
        "file": config["file"],
        "count": len(results),
        "results": results,
    }


def search_stack(query, stack, max_results=MAX_RESULTS):
    """Search stack-specific guidelines."""
    if stack not in STACK_CONFIG:
        return {"error": f"Unknown stack: {stack}. Available: {', '.join(AVAILABLE_STACKS)}"}

    filepath = DATA_DIR / STACK_CONFIG[stack]["file"]
    if not filepath.exists():
        return {"error": f"Stack file not found: {filepath}", "stack": stack}

    results = _search_csv(filepath, _STACK_COLS["search_cols"], _STACK_COLS["output_cols"],
                          query, max_results)

    return {
        "domain": "stack",
        "stack": stack,
        "query": query,
        "file": STACK_CONFIG[stack]["file"],
        "count": len(results),
        "results": results,
    }


def search_all(query, max_results=2):
    """Cross-domain search: returns top hits across every domain CSV."""
    aggregated = {}
    for domain, config in CSV_CONFIG.items():
        filepath = DATA_DIR / config["file"]
        if not filepath.exists():
            continue
        hits = _search_csv(filepath, config["search_cols"], config["output_cols"],
                           query, max_results)
        if hits:
            aggregated[domain] = hits
    return {"query": query, "domains": list(aggregated.keys()), "results": aggregated}
