# Cost Guidance Review: 2026-09-29

## Scope and Method

Reviewed all 22 entries in [cost.csv](../../src/backend-pro-max/data/cost.csv)
against their provider or FinOps Foundation documentation. Each revised entry
has a source type and a review date. Names and CSV columns remain unchanged.
The capacity calculators do not consume these prices; no calculator code changed.

Rates below are public USD examples, not quotes for every region, account,
purchase option, or deployment. Taxes, discounts, credits, and allowances must
be applied separately unless explicitly included. Monthly arithmetic states its
hours or days. "Billable GB" uses the provider's metered unit; it does not imply
that a decimal TB and a binary TiB are interchangeable.

Where the source did not substantiate an old numerical quote, the quote was
removed and replaced with the applicable billing dimensions. This is not a
claim that every old number was wrong for every historical configuration.
Several AWS pages required direct HTML extraction because the web reader could
not extract their pricing text. Dynamic regional pricing tables were not treated
as verified when only surrounding examples were available.

## Review Ledger

| Entry | Verified basis and correction | Primary evidence |
| --- | --- | --- |
| Cross-AZ Data Transfer | Use the EC2-to-ElastiCache example: the EC2 side is billed at $0.01/GiB; ElastiCache does not bill its side. Remove the claim that database replication universally multiplies transfer charges. | [ElastiCache data transfer](https://aws.amazon.com/elasticache/pricing/); [RDS transfer exemptions](https://aws.amazon.com/rds/pricing/) |
| Internet Egress | Scope the $0.09/GB example to Ohio; 1000 already-billable GB costs $90. Explain the shared AWS allowance; remove the unverified GCP/Azure generalization. | [EC2 transfer](https://aws.amazon.com/ec2/pricing/on-demand/); [Ohio internet-transfer example](https://aws.amazon.com/vpc/pricing/) |
| NAT Gateway Processing | Ohio zonal example: $0.045/hour plus $0.045/GB. At 730 hours and 1000 GB, subtotal is $77.85. Gateway-type endpoints, not Gateway Load Balancer endpoints, avoid eligible S3/DynamoDB NAT processing. | [VPC NAT pricing examples](https://aws.amazon.com/vpc/pricing/); [Gateway endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html) |
| DynamoDB On-Demand Pricing | Northern Virginia Standard table examples use $0.625/million WRUs and $0.125/million RRUs, replacing $1.25/$0.25. Explain item-size, consistency, and transactional unit effects. | [On-demand pricing examples](https://aws.amazon.com/dynamodb/pricing/on-demand/) |
| DynamoDB Provisioned vs On-Demand | Standard table examples use $0.00065/WCU-hour and $0.00013/RCU-hour. Remove the guaranteed 5-7x savings claim. Switching to on-demand is limited to four times per rolling 24 hours, not a universal cooldown for both directions. | [Provisioned pricing](https://aws.amazon.com/dynamodb/pricing/provisioned/); [Switching rules](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-switching-capacity-modes.html) |
| S3 Request Pricing | Retain operation/class-specific per-1000-request billing and the LIST/Standard-PUT relationship. Remove unqualified regional rates rather than treating S3 Tables examples as Standard pricing verification. | [S3 requests and pricing](https://aws.amazon.com/s3/pricing/) |
| S3 Storage Classes | Replace ambiguous "Glacier" pricing with named classes and minimum durations: IA 30 days, Instant/Flexible Retrieval 90 days, Deep Archive 180 days. Include one-zone resilience and Intelligent-Tiering size constraints. | [S3 storage-class comparison](https://aws.amazon.com/s3/storage-classes/) |
| GPU Instance Costs | Remove unverified $32/hour P4d and cross-cloud per-GPU prices. Specify whole-instance SKU, region, purchase option, and measured workload cost; do not promise a fixed reservation discount. | [P4 product and purchase options](https://aws.amazon.com/ec2/instance-types/p4/); [EC2 pricing](https://aws.amazon.com/ec2/pricing/on-demand/) |
| CloudWatch Logs Ingestion | Scope $0.50/GB to the first delivery tier in the Northern Virginia vended-log example, and $0.03/GB-month to compressed archival storage. Source/class/volume matter; queries and metrics are separate. | [CloudWatch log-delivery and archival examples](https://aws.amazon.com/cloudwatch/pricing/) |
| Load Balancer Idle Costs | Northern Virginia ALB/NLB base is $0.0225/hour in the examples; 730 hours is $16.425 before capacity units and other charges. ALB uses the highest LCU dimension; the first ten processed rules are excluded from rule-evaluation billing. | [ELB pricing examples and LCU definition](https://aws.amazon.com/elasticloadbalancing/pricing/) |
| RDS Multi-AZ Costs | Remove universal 2x pricing and free Aurora replica-compute assumptions. Deployment, engine, storage, IOPS, and backup choices determine cost. HA selection follows recovery objectives, not just an environment label. | [RDS billing dimensions](https://aws.amazon.com/rds/pricing/); [Multi-AZ deployment types](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html) |
| Kubernetes Cluster Overhead | Scope to EKS: $0.10/cluster-hour for standard support and $0.60 for extended support; 730-hour totals are $73 and $438. Worker resources and optional management charges are separate. Remove unsupported universal system-pod overhead percentages. | [EKS support-tier pricing](https://aws.amazon.com/eks/pricing/) |
| GCP BigQuery Pricing | Iowa on-demand example is $6.25/TiB after the first 1 TiB/month per account. New capacity purchases use editions/slot-hours; legacy flat-rate commitments are no longer offered to new purchases. LIMIT does not limit scanned bytes. | [BigQuery pricing and legacy-plan notice](https://cloud.google.com/bigquery/pricing) |
| VPC Endpoint Costs | Published interface examples use $0.01/endpoint-ENI-hour and $0.01/GB in the first tier. One endpoint in three AZs for 730 hours costs $21.90 before data. Preserve regional qualification and gateway/interface distinction. | [PrivateLink pricing examples](https://aws.amazon.com/privatelink/pricing/) |
| Container Registry Storage | Northern Virginia private ECR example supports $0.10/GB-month. Use actual stored bytes, not image count times nominal size. Scope same-region AWS compute transfer exemption; remove unsupported GCR/ACR pricing implication. | [ECR pricing examples](https://aws.amazon.com/ecr/pricing/) |
| Secrets Manager Costs | Published examples use $0.40/secret-month plus $0.05/10000 calls. Keep regional qualification; remove the recommendation to self-host solely based on secret count. New versions are not separate secret-storage charges. | [Secrets Manager pricing examples](https://aws.amazon.com/secrets-manager/pricing/) |
| Data Transfer Between Regions | S3 Oregon-to-Northern-Virginia example is $0.02/GB. 1000 billable GB/month is $20; 1000/day for 30 days is $600. Remove the old conflation of monthly and daily transfer and the cross-service universal rate. | [S3 inter-region pricing example](https://aws.amazon.com/s3/pricing/) |
| Lambda Invocation Costs | Northern Virginia x86 on-demand example uses $0.20/million requests and $0.0000166667/GB-second before allowances. Provisioned concurrency has separate charges and should serve latency requirements, not be presented as a default savings technique. | [Lambda pricing examples](https://aws.amazon.com/lambda/pricing/) |
| ElastiCache Node Costs | Valkey Serverless Northern Virginia example uses $0.084/GB-hour and $0.0023/million ECPUs. Correct the missing million-unit divisor, distinguish engines, and include the 100 MB Valkey versus 1 GB Redis OSS/Memcached minimum. | [ElastiCache serverless definitions and examples](https://aws.amazon.com/elasticache/pricing/) |
| FinOps Tagging Strategy | Replace the unsupported 30-50% estimate with an organization-specific unallocated-cost KPI. Include shared/untaggable costs and separate AWS billing-tag activation. | [FinOps allocation](https://www.finops.org/framework/capabilities/allocation/); [AWS tag activation](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html) |
| Managed Kafka (MSK) Costs | Scope the US East $0.21/broker-hour example to Standard kafka.m5.large; three brokers for 730 hours cost $459.90 before storage. Physical/provisioned storage across brokers is not logical retention. Express and Serverless must be priced separately. | [MSK deployment models and examples](https://aws.amazon.com/msk/pricing/) |
| CloudFront Costs | Replace universal geography and invalidation estimates with explicit plan selection: current flat-rate plans and pay-as-you-go have different terms and features. Require a current plan/tier quote. | [CloudFront pricing](https://aws.amazon.com/cloudfront/pricing/) |

## Verification and Limits

[Cost regression tests](../../tests/test_cost_review.py) check all entry sources
and review metadata, key units and caveats, removed claims, and arithmetic
extracted from the actual CSV examples using decimal calculations. These tests
are offline regression checks, not a live pricing monitor and not independent
proof of the provider's rates.

Full local suite: **732 passed**, including **48 new cost checks**, on Python
3.14.6. Ruff and CSV validation pass for all 34 domains and 12 stacks.
The remaining date-based backlog is **184 rows across 13 domains**. Hosted CI
and other Python versions were not executed in this follow-up.
The cost-only date scan reports no stale rows after review; URL checking was
disabled for that date scan. Source retrieval was performed separately during
the review, not inferred from the scanner's zero broken-URL count.

The other 184 previously stale entries are outside this review. Pricing remains
time-sensitive; consult the linked provider source and a configuration-specific
quote before making a purchasing decision. No commits or pushes are included
in this follow-up.

Subsequent work: the [concurrent domain review](domain-enrichment-2026-09-29.md)
addressed those 184 entries and added 39. The remaining backlog is now 31 rows;
the cost-review validation counts above describe the earlier checkpoint.