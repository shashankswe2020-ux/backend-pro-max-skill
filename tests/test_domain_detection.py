"""Tests for keyword-bag domain auto-detection."""
from __future__ import annotations

import core
import pytest


@pytest.mark.parametrize("query,expected", [
    ("kafka consumer group lag", "messaging"),
    ("postgres index bloat", "database"),
    ("error budget slo retry timeout", "reliability"),
    ("oauth2 pkce flow", "auth"),
    ("prometheus alert manager", "observability"),
    ("terraform state locking", "iac"),
    ("p99 tail latency profiling", "performance"),
    ("raft leader election quorum", "consistency"),
    ("kubernetes hpa autoscaler", "container"),
    ("graphql schema federation", "api"),
    ("redis cache stampede", "cache"),
])
def test_domain_detection(query, expected):
    assert core.detect_domain(query) == expected


def test_unknown_query_falls_back_to_pattern():
    assert core.detect_domain("xyzzy plugh frobnicate") == "pattern"
