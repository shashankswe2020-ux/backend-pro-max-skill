"""Guard the units, scope, and arithmetic of reviewed cost guidance."""
from __future__ import annotations

import csv
import re
from datetime import date
from decimal import Decimal
from urllib.parse import urlparse

import core
import pytest

with (core.DATA_DIR / "cost.csv").open(encoding="utf-8", newline="") as cost_file:
    COST_ROWS = {row["Name"]: row for row in csv.DictReader(cost_file)}


@pytest.mark.parametrize("name", list(COST_ROWS))
def test_cost_entries_have_reviewed_sources_and_price_scope(name):
    row = COST_ROWS[name]
    source = urlparse(row["Source URL"])
    assert source.scheme == "https"
    assert source.hostname in {"aws.amazon.com", "cloud.google.com", "www.finops.org"}
    assert row["Source Type"] == "official-docs"
    assert date.fromisoformat(row["Last Updated"]) >= date(2026, 9, 29)
    if "$" in row["Order of Magnitude"]:
        assert "USD" in row["Order of Magnitude"]
        assert any(scope in row["Order of Magnitude"] for scope in (
            "us-east-1", "us-east-2", "us-west-2", "us-central1", "Ohio", "US East",
            "confirm regional pricing",
        ))


@pytest.mark.parametrize("name, field, required", [
    ("DynamoDB On-Demand Pricing", "Order of Magnitude", "$0.625/million WRUs + $0.125/million RRUs"),
    ("DynamoDB On-Demand Pricing", "Gotcha", "4 KB"),
    ("DynamoDB Provisioned vs On-Demand", "Gotcha", "four times per rolling 24 hours"),
    ("ElastiCache Node Costs", "Order of Magnitude", "$0.0023/million ECPUs"),
    ("ElastiCache Node Costs", "Order of Magnitude", "$0.084/GB-hour"),
    ("ElastiCache Node Costs", "Gotcha", "100 MB"),
    ("S3 Storage Classes", "Order of Magnitude", "Flexible Retrieval 90 days"),
    ("S3 Storage Classes", "Order of Magnitude", "Deep Archive 180 days"),
    ("Kubernetes Cluster Overhead", "Order of Magnitude", "$0.60/cluster-hour"),
    ("GCP BigQuery Pricing", "Order of Magnitude", "$6.25/TiB"),
    ("GCP BigQuery Pricing", "Gotcha", "LIMIT does not reduce bytes scanned"),
    ("Load Balancer Idle Costs", "Gotcha", "highest usage dimension"),
    ("CloudFront Costs", "Gotcha", "Flat-rate plans and pay-as-you-go are different"),
    ("FinOps Tagging Strategy", "Gotcha", "require billing activation"),
])
def test_cost_review_keeps_critical_units_and_caveats(name, field, required):
    assert required in COST_ROWS[name][field]


@pytest.mark.parametrize("name, obsolete", [
    ("DynamoDB On-Demand Pricing", "$1.25/million"),
    ("DynamoDB Provisioned vs On-Demand", "5-7x cheaper"),
    ("GPU Instance Costs", "$32/hr"),
    ("ElastiCache Node Costs", "$0.0034/ECPU"),
    ("FinOps Tagging Strategy", "often represent 30-50%"),
    ("RDS Multi-AZ Costs", "Multi-AZ = 2x"),
])
def test_superseded_claims_do_not_reappear(name, obsolete):
    assert obsolete not in " ".join(COST_ROWS[name].values())


def test_nat_example_arithmetic():
    text = COST_ROWS["NAT Gateway Processing"]["Order of Magnitude"]
    match = re.search(
        r"\$([\d.]+)/hour \+ \$([\d.]+)/GB; (\d+) hours and (\d+) GB processed = \$([\d.]+)", text
    )
    assert match is not None
    hourly_rate, processing_rate, hours, gigabytes, total = map(Decimal, match.groups())
    assert hourly_rate * hours + processing_rate * gigabytes == total


def test_interface_endpoint_example_arithmetic():
    text = COST_ROWS["VPC Endpoint Costs"]["Order of Magnitude"]
    match = re.search(
        r"\$([\d.]+)/endpoint-ENI-hour .*one endpoint in (\d+) AZs for (\d+) hours = \$([\d.]+)", text
    )
    assert match is not None
    rate, zones, hours, total = map(Decimal, match.groups())
    assert rate * zones * hours == total


def test_cross_region_example_distinguishes_monthly_and_daily_volume():
    text = COST_ROWS["Data Transfer Between Regions"]["Order of Magnitude"]
    match = re.search(
        r"\$([\d.]+)/GB; (\d+) billable GB/month = \$([\d.]+); "
        r"(\d+) billable GB/day for (\d+) days = \$([\d.]+)", text
    )
    assert match is not None
    rate, monthly_gb, monthly_cost, daily_gb, days, daily_cost = map(Decimal, match.groups())
    assert rate * monthly_gb == monthly_cost
    assert rate * daily_gb * days == daily_cost


@pytest.mark.parametrize("name, pattern", [
    ("Load Balancer Idle Costs", r"\$([\d.]+)/hour; (\d+) hours = \$([\d.]+)"),
    ("Kubernetes Cluster Overhead", r"\$([\d.]+)/cluster-hour or \$([\d.]+) per (\d+) hours"),
])
def test_hourly_examples(name, pattern):
    matches = re.findall(pattern, COST_ROWS[name]["Order of Magnitude"])
    assert matches
    for values in matches:
        rate, middle, last = map(Decimal, values)
        hours, total = (last, middle) if name == "Kubernetes Cluster Overhead" else (middle, last)
        assert rate * hours == total


def test_msk_example_arithmetic():
    text = COST_ROWS["Managed Kafka (MSK) Costs"]["Order of Magnitude"]
    match = re.search(r"\$([\d.]+)/broker-hour; (\d+) brokers for (\d+) hours = \$([\d.]+)", text)
    assert match is not None
    rate, brokers, hours, total = map(Decimal, match.groups())
    assert rate * brokers * hours == total
