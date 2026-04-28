#!/usr/bin/env python3
"""
Capacity calculators for back-of-envelope estimation.

Pure standard-library implementation. Each calculator is a pure function
returning a dict of results. All functions are registered in CALCULATORS
for CLI discovery.
"""

from __future__ import annotations

import math


def calc_qps(daily: int, peak_factor: float = 3.0) -> dict:
    """Calculate QPS from daily request count."""
    avg = daily / 86400
    peak = avg * peak_factor
    return {
        "calculator": "qps",
        "inputs": {"daily": daily, "peak_factor": peak_factor},
        "avg_qps": round(avg),
        "peak_qps": round(peak),
        "description": (
            f"~{round(avg):,} QPS avg, ~{round(peak):,} QPS peak ({peak_factor}x)"
        ),
    }


def calc_storage(
    rows: int, row_bytes: int, replication: int = 3
) -> dict:
    """Calculate raw and replicated storage."""
    raw = rows * row_bytes
    replicated = raw * replication
    return {
        "calculator": "storage",
        "inputs": {"rows": rows, "row_bytes": row_bytes, "replication": replication},
        "raw_bytes": raw,
        "replicated_bytes": replicated,
        "raw_human": _human_bytes(raw),
        "replicated_human": _human_bytes(replicated),
        "description": (
            f"~{_human_bytes(raw)} raw, ~{_human_bytes(replicated)} with {replication}x replication"
        ),
    }


def calc_bandwidth(qps: int, payload_kb: float) -> dict:
    """Calculate bandwidth requirement."""
    bw_kbps = qps * payload_kb
    bw_mbps = bw_kbps / 1000
    return {
        "calculator": "bandwidth",
        "inputs": {"qps": qps, "payload_kb": payload_kb},
        "bandwidth_kbps": round(bw_kbps, 2),
        "bandwidth_mbps": round(bw_mbps, 2),
        "description": f"~{round(bw_mbps, 1)} MB/s ({round(bw_mbps * 8, 1)} Mbps)",
    }


def calc_concurrency(rps: int, latency_ms: float) -> dict:
    """Little's Law: L = λ × W."""
    latency_s = latency_ms / 1000
    concurrent = rps * latency_s
    return {
        "calculator": "concurrency",
        "inputs": {"rps": rps, "latency_ms": latency_ms},
        "concurrent_requests": round(concurrent),
        "formula": f"L = {rps} × {latency_s} = {concurrent}",
        "description": (
            f"{round(concurrent)} concurrent requests "
            f"(Little's Law: L = {rps} × {latency_s})"
        ),
    }


def calc_partitions(
    target_throughput_mb: float, per_partition_mb: float = 1.0
) -> dict:
    """Calculate Kafka partition count."""
    partitions = math.ceil(target_throughput_mb / per_partition_mb)
    return {
        "calculator": "partitions",
        "inputs": {
            "target_throughput_mb": target_throughput_mb,
            "per_partition_mb": per_partition_mb,
        },
        "partitions": partitions,
        "description": (
            f"{partitions} partitions "
            f"({target_throughput_mb} MB/s ÷ {per_partition_mb} MB/s per partition)"
        ),
    }


def calc_cache_hit(
    requests: int, cache_size: int, zipf: float = 0.8
) -> dict:
    """Estimate cache hit rate using Zipfian approximation.

    The estimate is: hit_rate ≈ (cache_size / requests) ^ (1 - zipf).
    For typical web workloads (zipf ≈ 0.8), a cache holding 10% of the
    key space hits ~63% of the time.
    """
    if cache_size >= requests:
        hit_rate = 1.0
    else:
        ratio = cache_size / requests
        hit_rate = min(ratio ** (1 - zipf), 1.0)
    return {
        "calculator": "cache-hit",
        "inputs": {"requests": requests, "cache_size": cache_size, "zipf": zipf},
        "estimated_hit_rate": round(hit_rate, 4),
        "estimated_hit_pct": f"{round(hit_rate * 100, 1)}%",
        "description": (
            f"~{round(hit_rate * 100, 1)}% estimated hit rate "
            f"(Zipf α={zipf}, cache {cache_size:,}/{requests:,} keys)"
        ),
    }


def calc_fanout(
    followers: int, posts_per_day: int, fanout_on: str = "write"
) -> dict:
    """Calculate fanout writes per day."""
    if fanout_on == "write":
        total = followers * posts_per_day
        description = (
            f"{total:,} writes/day "
            f"({followers:,} followers × {posts_per_day} posts/day, fanout-on-write)"
        )
    else:
        total = posts_per_day
        description = (
            f"{total:,} writes/day (fanout-on-read: writes = posts only)"
        )
    return {
        "calculator": "fanout",
        "inputs": {
            "followers": followers,
            "posts_per_day": posts_per_day,
            "fanout_on": fanout_on,
        },
        "total_writes_per_day": total,
        "description": description,
    }


# ── Registry ─────────────────────────────────────────────────────────────────

CALCULATORS = {
    "qps": calc_qps,
    "storage": calc_storage,
    "bandwidth": calc_bandwidth,
    "concurrency": calc_concurrency,
    "partitions": calc_partitions,
    "cache-hit": calc_cache_hit,
    "fanout": calc_fanout,
}


# ── Formatting ───────────────────────────────────────────────────────────────

def format_calc_result(name: str, result: dict) -> str:
    """Format a calculator result as readable markdown."""
    lines = [f"## 🧮 {name.upper()} Calculator", ""]
    lines.append(f"**Result:** {result.get('description', '')}")
    lines.append("")
    inputs = result.get("inputs", {})
    if inputs:
        lines.append("**Inputs:**")
        for k, v in inputs.items():
            lines.append(f"  - {k}: {v}")
    lines.append("")
    lines.append("**Details:**")
    for k, v in result.items():
        if k in ("calculator", "inputs", "description"):
            continue
        lines.append(f"  - {k}: {v}")
    return "\n".join(lines)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _human_bytes(n: int) -> str:
    """Convert bytes to human-readable string."""
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}" if n != int(n) else f"{n} {unit}"
        n /= 1024
    return f"{n:.1f} EB"
