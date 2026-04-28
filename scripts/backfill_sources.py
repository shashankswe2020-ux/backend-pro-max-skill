#!/usr/bin/env python3
"""One-shot backfill script for Source URL, Source Type, Last Updated on all CSVs."""
import csv
from pathlib import Path

DATA = Path("src/backend-pro-max/data")
DATE = "2026-04-28"

# ============================================================
# DOMAIN CSV BACKFILL MAPPINGS
# Key = CSV filename
# Value = dict  name_substring → (Source URL, Source Type)
# ============================================================

BACKFILL = {
    "databases.csv": {
        "PostgreSQL": ("https://www.postgresql.org/docs/current/", "official-docs"),
        "MySQL": ("https://dev.mysql.com/doc/refman/8.0/en/", "official-docs"),
        "CockroachDB": ("https://www.cockroachlabs.com/docs/stable/", "official-docs"),
        "Spanner": ("https://cloud.google.com/spanner/docs", "official-docs"),
        "MongoDB": ("https://www.mongodb.com/docs/manual/", "official-docs"),
        "Cassandra": ("https://cassandra.apache.org/doc/latest/", "official-docs"),
        "DynamoDB": ("https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/", "official-docs"),
        "Redis": ("https://redis.io/docs/", "official-docs"),
        "Memcached": ("https://memcached.org/about", "official-docs"),
        "Elasticsearch": ("https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html", "official-docs"),
        "ClickHouse": ("https://clickhouse.com/docs", "official-docs"),
        "DuckDB": ("https://duckdb.org/docs/", "official-docs"),
        "Snowflake": ("https://docs.snowflake.com/en/", "official-docs"),
        "Neo4j": ("https://neo4j.com/docs/", "official-docs"),
        "InfluxDB": ("https://docs.influxdata.com/influxdb/", "official-docs"),
        "Qdrant": ("https://qdrant.tech/documentation/", "official-docs"),
        "S3": ("https://docs.aws.amazon.com/AmazonS3/latest/userguide/", "official-docs"),
        "etcd": ("https://etcd.io/docs/", "official-docs"),
        "SQLite": ("https://www.sqlite.org/docs.html", "official-docs"),
    },
    "messaging.csv": {
        "Apache Kafka": ("https://kafka.apache.org/documentation/", "official-docs"),
        "Redpanda": ("https://docs.redpanda.com/", "official-docs"),
        "Apache Pulsar": ("https://pulsar.apache.org/docs/", "official-docs"),
        "RabbitMQ": ("https://www.rabbitmq.com/docs", "official-docs"),
        "NATS": ("https://docs.nats.io/", "official-docs"),
        "MQTT": ("https://mqtt.org/mqtt-specification/", "official-docs"),
        "AWS SQS": ("https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/", "official-docs"),
        "AWS SNS": ("https://docs.aws.amazon.com/sns/latest/dg/", "official-docs"),
        "AWS Kinesis": ("https://docs.aws.amazon.com/streams/latest/dev/", "official-docs"),
        "Google Pub/Sub": ("https://cloud.google.com/pubsub/docs", "official-docs"),
        "Azure Service Bus": ("https://learn.microsoft.com/en-us/azure/service-bus-messaging/", "official-docs"),
        "ZeroMQ": ("https://zeromq.org/get-started/", "official-docs"),
    },
    "cache.csv": {
        "In-process LRU": ("https://github.com/ben-manes/caffeine/wiki", "official-docs"),
        "Redis cache (single": ("https://redis.io/docs/manual/patterns/caching/", "official-docs"),
        "Redis Cluster": ("https://redis.io/docs/management/scaling/", "official-docs"),
        "CDN edge cache": ("https://developers.cloudflare.com/cache/", "official-docs"),
        "HTTP cache": ("https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching", "official-docs"),
        "Read-through": ("https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Strategies.html", "official-docs"),
        "Write-through": ("https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Strategies.html", "official-docs"),
        "Write-back": ("https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Strategies.html", "official-docs"),
        "Materialized view": ("https://www.postgresql.org/docs/current/rules-materializedviews.html", "official-docs"),
        "Negative caching": ("https://aws.amazon.com/blogs/networking-and-content-delivery/amazon-cloudfront-support-for-negative-caching/", "engineering-blog"),
        "Bloom filter": ("https://en.wikipedia.org/wiki/Bloom_filter", "paper"),
        "L1+L2 hybrid": ("https://redis.io/docs/manual/patterns/caching/", "official-docs"),
    },
    "reliability.csv": {
        "SLO": ("https://sre.google/workbook/implementing-slos/", "book"),
        "Timeouts": ("https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/", "engineering-blog"),
        "Retries": ("https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/", "engineering-blog"),
        "Circuit breaker": ("https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker", "official-docs"),
        "Bulkhead": ("https://learn.microsoft.com/en-us/azure/architecture/patterns/bulkhead", "official-docs"),
        "Idempotency": ("https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/", "engineering-blog"),
        "Graceful shutdown": ("https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-termination", "official-docs"),
        "Health checks": ("https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/", "official-docs"),
        "Capacity planning": ("https://sre.google/sre-book/software-engineering-in-sre/", "book"),
        "Disaster recovery": ("https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html", "official-docs"),
        "Multi-AZ": ("https://docs.aws.amazon.com/whitepapers/latest/real-time-communication-on-aws/high-availability-and-scalability-on-aws.html", "official-docs"),
        "Backups": ("https://www.postgresql.org/docs/current/continuous-archiving.html", "official-docs"),
        "Chaos engineering": ("https://principlesofchaos.org/", "paper"),
        "Runbooks": ("https://sre.google/sre-book/effective-troubleshooting/", "book"),
        "Blue/Green": ("https://docs.aws.amazon.com/whitepapers/latest/overview-deployment-options/bluegreen-deployments.html", "official-docs"),
        "Feature flags": ("https://martinfowler.com/articles/feature-toggles.html", "engineering-blog"),
        "Quotas": ("https://cloud.google.com/architecture/rate-limiting-strategies-techniques", "official-docs"),
        "Postmortems": ("https://sre.google/sre-book/postmortem-culture/", "book"),
    },
    "architecture.csv": {
        "Monolith": ("https://martinfowler.com/bliki/MonolithFirst.html", "engineering-blog"),
        "Modular Monolith": ("https://www.youtube.com/watch?v=5OjqD-ow8GE", "engineering-blog"),
        "Microservices": ("https://martinfowler.com/articles/microservices.html", "engineering-blog"),
        "Serverless": ("https://docs.aws.amazon.com/lambda/latest/dg/welcome.html", "official-docs"),
        "Event-Driven": ("https://martinfowler.com/articles/201701-event-driven.html", "engineering-blog"),
        "Hexagonal": ("https://alistair.cockburn.us/hexagonal-architecture/", "engineering-blog"),
        "Clean Architecture": ("https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html", "engineering-blog"),
        "Domain-Driven Design": ("https://martinfowler.com/bliki/DomainDrivenDesign.html", "engineering-blog"),
        "CQRS": ("https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs", "official-docs"),
        "Service Mesh": ("https://istio.io/latest/docs/concepts/what-is-istio/", "official-docs"),
        "BFF": ("https://samnewman.io/patterns/architectural/bff/", "engineering-blog"),
        "Lambda": ("https://nathanmarz.com/blog/how-to-beat-the-cap-theorem.html", "engineering-blog"),
        "Actor Model": ("https://doc.akka.io/docs/akka/current/typed/guide/actors-intro.html", "official-docs"),
        "Cell-Based": ("https://docs.aws.amazon.com/wellarchitected/latest/reducing-scope-of-impact-with-cell-based-architecture/what-is-a-cell-based-architecture.html", "official-docs"),
    },
    "performance.csv": {
        "N+1 query": ("https://secure.phabricator.com/book/phabcontrib/article/n_plus_one/", "engineering-blog"),
        "Missing index": ("https://www.postgresql.org/docs/current/indexes.html", "official-docs"),
        "Wrong query plan": ("https://www.postgresql.org/docs/current/using-explain.html", "official-docs"),
        "Connection pool": ("https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing", "engineering-blog"),
        "GC pauses": ("https://docs.oracle.com/en/java/javase/21/gctuning/", "official-docs"),
        "Hot key": ("https://aws.amazon.com/blogs/database/amazon-dynamodb-adaptive-capacity/", "engineering-blog"),
        "Tail latency": ("https://research.google/pubs/pub40801/", "paper"),
        "Thundering herd": ("https://en.wikipedia.org/wiki/Thundering_herd_problem", "paper"),
        "Async/await blocking": ("https://blog.stephencleary.com/2012/07/dont-block-on-async-code.html", "engineering-blog"),
        "Hot Lambda": ("https://docs.aws.amazon.com/lambda/latest/operatorguide/execution-environments.html", "official-docs"),
        "Memory leak": ("https://docs.oracle.com/javase/8/docs/technotes/guides/troubleshoot/memleaks002.html", "official-docs"),
        "Goroutine": ("https://go.dev/blog/concurrency-timeouts", "official-docs"),
        "File descriptor": ("https://man7.org/linux/man-pages/man2/close.2.html", "official-docs"),
        "Hot path allocations": ("https://tip.golang.org/doc/gc-guide", "official-docs"),
        "Slow JSON": ("https://github.com/simdjson/simdjson", "benchmark"),
        "Network round-trips": ("https://research.google/pubs/pub40801/", "paper"),
        "TLS handshake": ("https://datatracker.ietf.org/doc/html/rfc8446", "rfc"),
    },
    "cloud.csv": {
        "EC2": ("https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/", "official-docs"),
        "ECS": ("https://docs.aws.amazon.com/AmazonECS/latest/developerguide/", "official-docs"),
        "EKS": ("https://docs.aws.amazon.com/eks/latest/userguide/", "official-docs"),
        "Lambda": ("https://docs.aws.amazon.com/lambda/latest/dg/", "official-docs"),
        "S3": ("https://docs.aws.amazon.com/AmazonS3/latest/userguide/", "official-docs"),
        "RDS": ("https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/", "official-docs"),
        "DynamoDB": ("https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/", "official-docs"),
        "ElastiCache": ("https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/", "official-docs"),
        "SQS": ("https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/", "official-docs"),
        "SNS": ("https://docs.aws.amazon.com/sns/latest/dg/", "official-docs"),
        "Kinesis": ("https://docs.aws.amazon.com/streams/latest/dev/", "official-docs"),
        "Cloud Run": ("https://cloud.google.com/run/docs", "official-docs"),
        "GKE": ("https://cloud.google.com/kubernetes-engine/docs", "official-docs"),
        "BigQuery": ("https://cloud.google.com/bigquery/docs", "official-docs"),
        "Pub/Sub": ("https://cloud.google.com/pubsub/docs", "official-docs"),
        "Cloud Spanner": ("https://cloud.google.com/spanner/docs", "official-docs"),
        "AKS": ("https://learn.microsoft.com/en-us/azure/aks/", "official-docs"),
        "Azure Functions": ("https://learn.microsoft.com/en-us/azure/azure-functions/", "official-docs"),
        "Cosmos DB": ("https://learn.microsoft.com/en-us/azure/cosmos-db/", "official-docs"),
        "Cloudflare Workers": ("https://developers.cloudflare.com/workers/", "official-docs"),
        "Vercel": ("https://vercel.com/docs", "official-docs"),
    },
    "consistency.csv": {
        "Linearizability": ("https://cs.brown.edu/~mph/HerlihyW90/p463-herlihy.pdf", "paper"),
        "Sequential consistency": ("https://lamport.azurewebsites.net/pubs/multi.pdf", "paper"),
        "Causal consistency": ("https://jepsen.io/consistency/models/causal", "engineering-blog"),
        "Read-your-writes": ("https://jepsen.io/consistency/models/read-your-writes", "engineering-blog"),
        "Eventual consistency": ("https://www.allthingsdistributed.com/2008/12/eventually_consistent.html", "engineering-blog"),
        "Strong eventual": ("https://hal.inria.fr/inria-00609399/document", "paper"),
        "CAP theorem": ("https://groups.csail.mit.edu/tds/papers/Gilbert/brewer2.pdf", "paper"),
        "PACELC": ("https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf", "paper"),
        "Raft": ("https://raft.github.io/raft.pdf", "paper"),
        "Paxos": ("https://lamport.azurewebsites.net/pubs/paxos-simple.pdf", "paper"),
        "Two-Phase Commit": ("https://dsf.berkeley.edu/cs286/papers/2pc-tods1986.pdf", "paper"),
        "Snapshot Isolation": ("https://www.microsoft.com/en-us/research/wp-content/uploads/2005/01/HAT.pdf", "paper"),
        "Quorum": ("https://www.allthingsdistributed.com/2006/12/eventually_consistent_revisited.html", "engineering-blog"),
        "Lamport": ("https://lamport.azurewebsites.net/pubs/time-clocks.pdf", "paper"),
        "Hybrid Logical": ("https://cse.buffalo.edu/tech-reports/2014-04.pdf", "paper"),
    },
    "containers.csv": {
        "Docker": ("https://docs.docker.com/", "official-docs"),
        "Podman": ("https://docs.podman.io/", "official-docs"),
        "containerd": ("https://containerd.io/docs/", "official-docs"),
        "Kubernetes": ("https://kubernetes.io/docs/home/", "official-docs"),
        "EKS / GKE / AKS": ("https://kubernetes.io/docs/setup/production-environment/turnkey-cloud-solutions/", "official-docs"),
        "Helm": ("https://helm.sh/docs/", "official-docs"),
        "Kustomize": ("https://kustomize.io/", "official-docs"),
        "ArgoCD": ("https://argo-cd.readthedocs.io/en/stable/", "official-docs"),
        "Istio": ("https://istio.io/latest/docs/", "official-docs"),
        "Envoy": ("https://www.envoyproxy.io/docs/envoy/latest/", "official-docs"),
        "Ingress NGINX": ("https://kubernetes.github.io/ingress-nginx/", "official-docs"),
        "Karpenter": ("https://karpenter.sh/docs/", "official-docs"),
        "Nomad": ("https://developer.hashicorp.com/nomad/docs", "official-docs"),
        "Docker Compose": ("https://docs.docker.com/compose/", "official-docs"),
        "Testcontainers": ("https://testcontainers.com/getting-started/", "official-docs"),
    },
    "anti-patterns.csv": {
        "Distributed Monolith": ("https://www.ben-morris.com/the-distributed-monolith/", "engineering-blog"),
        "Shared Database": ("https://microservices.io/patterns/data/shared-database.html", "engineering-blog"),
        "God Service": ("https://martinfowler.com/bliki/MonolithFirst.html", "engineering-blog"),
        "Sync-over-Async": ("https://blog.stephencleary.com/2012/07/dont-block-on-async-code.html", "engineering-blog"),
        "Dual Writes": ("https://www.confluent.io/blog/dual-write-problem/", "engineering-blog"),
        "Chatty Microservices": ("https://learn.microsoft.com/en-us/azure/architecture/antipatterns/chatty-io/", "official-docs"),
        "Unbounded Retry": ("https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/", "engineering-blog"),
        "Missing Idempotency": ("https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/", "engineering-blog"),
        "Premature Microservices": ("https://martinfowler.com/bliki/MonolithFirst.html", "engineering-blog"),
        "Log-and-Throw": ("https://www.baeldung.com/java-logging-exceptions", "engineering-blog"),
        "Generic Error": ("https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design#handle-errors", "official-docs"),
        "N+1 Query": ("https://secure.phabricator.com/book/phabcontrib/article/n_plus_one/", "engineering-blog"),
        "Secrets in Environment": ("https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html", "official-docs"),
        "Time-Based Cache": ("https://learn.microsoft.com/en-us/azure/architecture/best-practices/caching", "official-docs"),
        "Polling Instead": ("https://martinfowler.com/articles/201701-event-driven.html", "engineering-blog"),
    },
    "api.csv": {
        "REST": ("https://restfulapi.net/", "official-docs"),
        "GraphQL": ("https://graphql.org/learn/", "official-docs"),
        "gRPC-Web": ("https://grpc.io/docs/platforms/web/", "official-docs"),
        "gRPC": ("https://grpc.io/docs/", "official-docs"),
        "WebSocket": ("https://datatracker.ietf.org/doc/html/rfc6455", "rfc"),
        "Server-Sent Events": ("https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events", "official-docs"),
        "HTTP/2": ("https://datatracker.ietf.org/doc/html/rfc7540", "rfc"),
        "HTTP/3": ("https://datatracker.ietf.org/doc/html/rfc9114", "rfc"),
        "WebHooks": ("https://www.standardwebhooks.com/", "official-docs"),
        "WebSub": ("https://www.w3.org/TR/websub/", "rfc"),
        "JSON-RPC": ("https://www.jsonrpc.org/specification", "rfc"),
        "SOAP": ("https://www.w3.org/TR/soap12/", "rfc"),
    },
    "auth.csv": {
        "OAuth 2.0": ("https://datatracker.ietf.org/doc/html/rfc6749", "rfc"),
        "OpenID Connect": ("https://openid.net/specs/openid-connect-core-1_0.html", "rfc"),
        "JWT": ("https://datatracker.ietf.org/doc/html/rfc7519", "rfc"),
        "SAML": ("https://docs.oasis-open.org/security/saml/v2.0/saml-core-2.0-os.pdf", "rfc"),
        "mTLS": ("https://datatracker.ietf.org/doc/html/rfc8446", "rfc"),
        "API Keys": ("https://cloud.google.com/docs/authentication/api-keys", "official-docs"),
        "HMAC": ("https://datatracker.ietf.org/doc/html/rfc2104", "rfc"),
        "Session cookies": ("https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html", "official-docs"),
        "Passkeys": ("https://www.w3.org/TR/webauthn-3/", "rfc"),
        "Magic links": ("https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html", "official-docs"),
        "RBAC": ("https://csrc.nist.gov/projects/role-based-access-control", "official-docs"),
        "ABAC": ("https://csrc.nist.gov/publications/detail/sp/800-162/final", "official-docs"),
        "SCIM": ("https://datatracker.ietf.org/doc/html/rfc7644", "rfc"),
        "Service-account": ("https://cloud.google.com/iam/docs/workload-identity-federation", "official-docs"),
    },
    "cicd.csv": {
        "GitHub Actions": ("https://docs.github.com/en/actions", "official-docs"),
        "GitLab CI": ("https://docs.gitlab.com/ee/ci/", "official-docs"),
        "Jenkins": ("https://www.jenkins.io/doc/", "official-docs"),
        "CircleCI": ("https://circleci.com/docs/", "official-docs"),
        "Buildkite": ("https://buildkite.com/docs", "official-docs"),
        "Drone": ("https://docs.drone.io/", "official-docs"),
        "Tekton": ("https://tekton.dev/docs/", "official-docs"),
        "Argo Workflows": ("https://argo-workflows.readthedocs.io/en/latest/", "official-docs"),
        "ArgoCD": ("https://argo-cd.readthedocs.io/en/stable/", "official-docs"),
        "Flux": ("https://fluxcd.io/docs/", "official-docs"),
        "Spinnaker": ("https://spinnaker.io/docs/", "official-docs"),
        "Argo Rollouts": ("https://argo-rollouts.readthedocs.io/en/stable/", "official-docs"),
        "Renovate": ("https://docs.renovatebot.com/", "official-docs"),
        "SonarQube": ("https://docs.sonarsource.com/sonarqube/latest/", "official-docs"),
        "GitHub Advanced Security": ("https://docs.github.com/en/code-security", "official-docs"),
    },
    "data-engineering.csv": {
        "Apache Spark": ("https://spark.apache.org/docs/latest/", "official-docs"),
        "Apache Flink": ("https://nightlies.apache.org/flink/flink-docs-stable/", "official-docs"),
        "Kafka Streams": ("https://kafka.apache.org/documentation/streams/", "official-docs"),
        "Airbyte": ("https://docs.airbyte.com/", "official-docs"),
        "dbt": ("https://docs.getdbt.com/docs/introduction", "official-docs"),
        "Apache Airflow": ("https://airflow.apache.org/docs/", "official-docs"),
        "Dagster": ("https://docs.dagster.io/", "official-docs"),
        "Prefect": ("https://docs.prefect.io/", "official-docs"),
        "Iceberg": ("https://iceberg.apache.org/docs/latest/", "official-docs"),
        "ClickHouse": ("https://clickhouse.com/docs", "official-docs"),
        "Spark Structured Streaming": ("https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html", "official-docs"),
        "Debezium": ("https://debezium.io/documentation/", "official-docs"),
        "Kafka Connect": ("https://kafka.apache.org/documentation/#connect", "official-docs"),
        "LakeFS": ("https://docs.lakefs.io/", "official-docs"),
        "Vector DBs": ("https://qdrant.tech/documentation/", "official-docs"),
        "Feature stores": ("https://docs.feast.dev/", "official-docs"),
    },
    "iac.csv": {
        "Terraform": ("https://developer.hashicorp.com/terraform/docs", "official-docs"),
        "Pulumi": ("https://www.pulumi.com/docs/", "official-docs"),
        "AWS CDK": ("https://docs.aws.amazon.com/cdk/v2/guide/home.html", "official-docs"),
        "CloudFormation": ("https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/", "official-docs"),
        "Bicep": ("https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/", "official-docs"),
        "Ansible": ("https://docs.ansible.com/ansible/latest/", "official-docs"),
        "Chef": ("https://docs.chef.io/", "official-docs"),
        "Crossplane": ("https://docs.crossplane.io/latest/", "official-docs"),
        "Helm": ("https://helm.sh/docs/", "official-docs"),
        "Kustomize": ("https://kustomize.io/", "official-docs"),
        "Packer": ("https://developer.hashicorp.com/packer/docs", "official-docs"),
        "Vagrant": ("https://developer.hashicorp.com/vagrant/docs", "official-docs"),
    },
    "languages.csv": {
        "Go": ("https://go.dev/doc/", "official-docs"),
        "Java": ("https://docs.oracle.com/en/java/", "official-docs"),
        "Kotlin": ("https://kotlinlang.org/docs/home.html", "official-docs"),
        "Python": ("https://docs.python.org/3/", "official-docs"),
        "Rust": ("https://doc.rust-lang.org/book/", "official-docs"),
        "Node.js": ("https://nodejs.org/docs/latest/api/", "official-docs"),
        "C#": ("https://learn.microsoft.com/en-us/dotnet/csharp/", "official-docs"),
        "Scala": ("https://docs.scala-lang.org/", "official-docs"),
        "Elixir": ("https://elixir-lang.org/docs.html", "official-docs"),
        "Ruby": ("https://ruby-doc.org/", "official-docs"),
        "PHP": ("https://www.php.net/docs.php", "official-docs"),
        "C++": ("https://en.cppreference.com/w/", "official-docs"),
    },
    "observability.csv": {
        "Prometheus": ("https://prometheus.io/docs/introduction/overview/", "official-docs"),
        "Mimir": ("https://grafana.com/docs/mimir/latest/", "official-docs"),
        "Grafana": ("https://grafana.com/docs/grafana/latest/", "official-docs"),
        "Loki": ("https://grafana.com/docs/loki/latest/", "official-docs"),
        "ELK": ("https://www.elastic.co/guide/en/elastic-stack/current/index.html", "official-docs"),
        "Tempo": ("https://grafana.com/docs/tempo/latest/", "official-docs"),
        "OpenTelemetry": ("https://opentelemetry.io/docs/", "official-docs"),
        "Pyroscope": ("https://grafana.com/docs/pyroscope/latest/", "official-docs"),
        "Datadog": ("https://docs.datadoghq.com/", "official-docs"),
        "New Relic": ("https://docs.newrelic.com/", "official-docs"),
        "Sentry": ("https://docs.sentry.io/", "official-docs"),
        "Fluent Bit": ("https://docs.fluentbit.io/manual/", "official-docs"),
        "PagerDuty": ("https://developer.pagerduty.com/docs/", "official-docs"),
        "SLO frameworks": ("https://github.com/slok/sloth", "official-docs"),
    },
    "scaling.csv": {
        "Vertical scaling": ("https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-resize.html", "official-docs"),
        "Horizontal scaling": ("https://docs.aws.amazon.com/autoscaling/ec2/userguide/", "official-docs"),
        "Auto-scaling": ("https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/", "official-docs"),
        "Sharding": ("https://www.mongodb.com/docs/manual/sharding/", "official-docs"),
        "Read replicas": ("https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html", "official-docs"),
        "Caching (multi-tier": ("https://aws.amazon.com/caching/", "official-docs"),
        "Connection pooling": ("https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing", "engineering-blog"),
        "Backpressure": ("https://www.reactivemanifesto.org/glossary#Back-Pressure", "official-docs"),
        "Bulkhead": ("https://learn.microsoft.com/en-us/azure/architecture/patterns/bulkhead", "official-docs"),
        "Hedged requests": ("https://research.google/pubs/pub40801/", "paper"),
        "Load balancing": ("https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/", "official-docs"),
        "CDN": ("https://developers.cloudflare.com/cache/", "official-docs"),
        "Geo-distribution": ("https://docs.aws.amazon.com/global-accelerator/latest/dg/", "official-docs"),
        "Async": ("https://learn.microsoft.com/en-us/azure/architecture/patterns/queue-based-load-leveling", "official-docs"),
        "Database indexing": ("https://www.postgresql.org/docs/current/indexes.html", "official-docs"),
        "Materialized views": ("https://www.postgresql.org/docs/current/rules-materializedviews.html", "official-docs"),
        "Partitioning": ("https://www.postgresql.org/docs/current/ddl-partitioning.html", "official-docs"),
    },
    "security.csv": {
        "SQL Injection": ("https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html", "official-docs"),
        "Cross-Site Scripting": ("https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html", "official-docs"),
        "CSRF": ("https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html", "official-docs"),
        "SSRF": ("https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html", "official-docs"),
        "Insecure Deserialization": ("https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html", "official-docs"),
        "Secret in source": ("https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html", "official-docs"),
        "Dependency vulnerability": ("https://owasp.org/www-project-dependency-check/", "official-docs"),
        "Container image": ("https://docs.docker.com/scout/", "official-docs"),
        "Supply-chain": ("https://slsa.dev/spec/v1.0/", "official-docs"),
        "Zero Trust": ("https://csrc.nist.gov/publications/detail/sp/800-207/final", "official-docs"),
        "Encryption at rest": ("https://docs.aws.amazon.com/kms/latest/developerguide/", "official-docs"),
        "TLS": ("https://datatracker.ietf.org/doc/html/rfc8446", "rfc"),
        "Logging & PII": ("https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html", "official-docs"),
        "Rate limiting": ("https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html", "official-docs"),
        "CORS": ("https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS", "official-docs"),
        "SBOM": ("https://www.cisa.gov/sbom", "official-docs"),
        "Static analysis": ("https://owasp.org/www-community/Source_Code_Analysis_Tools", "official-docs"),
        "Dynamic analysis": ("https://owasp.org/www-community/Fuzzing", "official-docs"),
    },
    "testing.csv": {
        "Unit tests": ("https://martinfowler.com/bliki/UnitTest.html", "engineering-blog"),
        "Component": ("https://martinfowler.com/bliki/ComponentTest.html", "engineering-blog"),
        "Integration tests": ("https://martinfowler.com/bliki/IntegrationTest.html", "engineering-blog"),
        "Contract tests": ("https://docs.pact.io/", "official-docs"),
        "End-to-End": ("https://playwright.dev/docs/intro", "official-docs"),
        "Property-based": ("https://hypothesis.readthedocs.io/en/latest/", "official-docs"),
        "Fuzz testing": ("https://go.dev/security/fuzz/", "official-docs"),
        "Snapshot tests": ("https://jestjs.io/docs/snapshot-testing", "official-docs"),
        "Mutation testing": ("https://pitest.org/", "official-docs"),
        "Load tests": ("https://grafana.com/docs/k6/latest/", "official-docs"),
        "Stress": ("https://grafana.com/docs/k6/latest/testing-guides/test-types/stress-testing/", "official-docs"),
        "Chaos engineering": ("https://principlesofchaos.org/", "paper"),
        "Smoke tests": ("https://docs.datadoghq.com/synthetics/", "official-docs"),
    },
}

# ============================================================
# STACK CSV BACKFILL (Source URL + Last Updated only, no Source Type)
# ============================================================

STACK_BACKFILL = {
    "stacks/go.csv": ("https://go.dev/doc/effective_go", "official-docs"),
    "stacks/java-spring.csv": ("https://docs.spring.io/spring-boot/reference/", "official-docs"),
    "stacks/python-fastapi.csv": ("https://fastapi.tiangolo.com/", "official-docs"),
    "stacks/nodejs-express.csv": ("https://expressjs.com/en/guide/routing.html", "official-docs"),
    "stacks/rust-axum.csv": ("https://docs.rs/axum/latest/axum/", "official-docs"),
    "stacks/csharp-aspnet.csv": ("https://learn.microsoft.com/en-us/aspnet/core/", "official-docs"),
    "stacks/kotlin-spring.csv": ("https://docs.spring.io/spring-boot/reference/", "official-docs"),
    "stacks/scala-akka.csv": ("https://doc.akka.io/docs/akka/current/", "official-docs"),
    "stacks/elixir-phoenix.csv": ("https://hexdocs.pm/phoenix/overview.html", "official-docs"),
    "stacks/ruby-rails.csv": ("https://guides.rubyonrails.org/", "official-docs"),
    "stacks/php-laravel.csv": ("https://laravel.com/docs/", "official-docs"),
    "stacks/cpp.csv": ("https://en.cppreference.com/w/", "official-docs"),
}


def backfill_domain_csv(filename, mapping):
    filepath = DATA / filename
    if not filepath.exists():
        print(f"  SKIP {filename} (not found)")
        return 0

    with open(filepath, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        header = list(reader.fieldnames or [])
        rows = list(reader)

    updated = 0
    for row in rows:
        if (row.get("Source URL") or "").strip():
            continue  # already has a source

        # Find the name field
        name_val = ""
        for col in ["Name", "Topic", "Tool", "Service", "Style", "Model", "Technique", "Operation"]:
            if col in row and row[col]:
                name_val = row[col]
                break

        # Match against mapping (substring match)
        matched = False
        for key, (url, src_type) in mapping.items():
            if key.lower() in name_val.lower():
                row["Source URL"] = url
                if "Source Type" in header:
                    row["Source Type"] = src_type
                if not (row.get("Last Updated") or "").strip():
                    row["Last Updated"] = DATE
                updated += 1
                matched = True
                break

        if not matched and not (row.get("Last Updated") or "").strip():
            row["Last Updated"] = DATE

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)

    return updated


def backfill_stack_csv(filename, default_url, default_type):
    filepath = DATA / filename
    if not filepath.exists():
        print(f"  SKIP {filename} (not found)")
        return 0

    with open(filepath, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        header = list(reader.fieldnames or [])
        rows = list(reader)

    updated = 0
    for row in rows:
        if (row.get("Source URL") or "").strip():
            continue
        row["Source URL"] = default_url
        if not (row.get("Last Updated") or "").strip():
            row["Last Updated"] = DATE
        updated += 1

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)

    return updated


if __name__ == "__main__":
    total = 0
    print("=== Domain CSVs ===")
    for filename, mapping in BACKFILL.items():
        n = backfill_domain_csv(filename, mapping)
        print(f"  {filename}: {n} rows backfilled")
        total += n

    print("\n=== Stack CSVs ===")
    for filename, (url, src_type) in STACK_BACKFILL.items():
        n = backfill_stack_csv(filename, url, src_type)
        print(f"  {filename}: {n} rows backfilled")
        total += n

    print(f"\n✅ Total: {total} rows backfilled with Source URL + Source Type + Last Updated")
