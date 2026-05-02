# System Design — Staff Engineer Interview Catalogue

> 50 system designs that cover the full spectrum of staff-level interviews.  
> ✅ = completed | ⬚ = planned

---

## Completed

| # | System | Key Topics |
|---|--------|------------|
| 1 | [Netflix](./netflix-system-design.md) | CDN (Open Connect), adaptive streaming, microservices, chaos engineering |
| 3 | [Instagram / Photo Sharing](./instagram-system-design.md) | News feed, image pipeline, CDN, celebrity problem, sharding |
| 4 | [Twitter / X](./twitter-system-design.md) | Hybrid fan-out (push/pull), timeline ranking, trending (CMS + Heron), Earlybird real-time search |
| 2 | [WhatsApp / Messaging System](./whatsapp-messaging-system.md) | End-to-end encryption, message queues, presence, delivery receipts, fan-out |
| 5 | [Facebook News Feed](./facebook-news-feed.md) | Multi-source aggregation, EdgeRank → DNN ranking, pull-heavy hybrid, TAO social graph, mcrouter edge caching |
| 6 | [LinkedIn](./linkedin-system-design.md) | Connection graph + degree pre-compute, Galene search, feed ranking, InMail credit ledger, skill endorsements, Economic Graph |
| 7 | [Discord / Slack](./discord-slack-system-design.md) | Erlang gateway at 250K WS/node, Channel Server single-writer ordering, ScyllaDB messages, presence amplification, WebRTC SFU voice |

---

## Planned (43 Remaining)

### Social & Communication Platforms

| # | System | Key Topics |
|---|--------|------------|
| 8 | Zoom / Video Conferencing | SFU vs. MCU, WebRTC, SRTP, adaptive bitrate, breakout rooms |

### Content & Media

| # | System | Key Topics |
|---|--------|------------|
| 9 | YouTube | Video upload pipeline, transcoding, CDN, recommendation, live streaming |
| 10 | Spotify | Audio streaming, offline sync, collaborative playlists, podcast ingest |
| 11 | TikTok / Short Video Feed | For-You ranking, content moderation pipeline, edge caching, creator tools |
| 12 | Twitch / Live Streaming | Low-latency ingest, chat at scale, VOD, drops, transcoding |

### E-Commerce & Marketplaces

| # | System | Key Topics |
|---|--------|------------|
| 13 | Amazon E-Commerce | Product catalog, cart, inventory, order pipeline, warehouse routing |
| 14 | Uber / Ride-Sharing | Geospatial matching, dynamic pricing, ETA, dispatch, payments |
| 15 | Uber Eats / DoorDash | Multi-sided marketplace, order tracking, kitchen delay estimation |
| 16 | Airbnb | Search ranking, availability calendar, booking, trust & safety |
| 17 | Stripe / Payment System | Idempotent payments, ledger, PCI compliance, webhooks, reconciliation |
| 18 | Ticketmaster / Event Booking | High-contention inventory, virtual queue, seat selection, surge |

### Search & Discovery

| # | System | Key Topics |
|---|--------|------------|
| 19 | Google Search | Web crawling, inverted index, PageRank, query parsing, serving tiers |
| 20 | Elasticsearch / Distributed Search | Sharding, replication, inverted index, relevance scoring |
| 21 | Yelp / Nearby Places | Geospatial index (Quadtree / S2), reviews, ranking, map tiles |
| 22 | Google Maps / Navigation | Graph routing (Dijkstra/A*), tile serving, ETA, live traffic |

### Storage & Infrastructure

| # | System | Key Topics |
|---|--------|------------|
| 23 | S3 / Object Storage | Erasure coding, metadata service, consistency, multi-tenancy |
| 24 | Dropbox / Google Drive | File sync, chunking, dedup, conflict resolution, sharing |
| 25 | Distributed Key-Value Store (Dynamo) | Consistent hashing, vector clocks, sloppy quorum, hinted handoff |
| 26 | Distributed Cache (Redis Cluster) | Sharding, eviction, replication, pub/sub, persistence |
| 27 | Distributed Message Queue (Kafka) | Partitions, ISR, exactly-once, compaction, consumer groups |
| 28 | Distributed SQL (CockroachDB / Spanner) | Raft consensus, TrueTime, serializable isolation, range sharding |

### Notifications & Real-Time

| # | System | Key Topics |
|---|--------|------------|
| 29 | Push Notification System | APNS/FCM, fan-out, rate limiting, preference management, analytics |
| 30 | Real-Time Analytics Dashboard | Streaming aggregation (Flink), time-series DB, WebSocket push |
| 31 | Newsfeed / Activity Stream | Fan-out strategies, denormalization, ranking, cursor pagination |

### URL & Content Delivery

| # | System | Key Topics |
|---|--------|------------|
| 32 | URL Shortener (bit.ly) | Hash/counter-based ID, 301 vs 302, analytics, bloom filter |
| 33 | Pastebin / Code Sharing | Content-addressable storage, expiration, rate limiting |
| 34 | Web Crawler | Politeness, URL frontier, dedup (bloom filter), distributed scheduling |

### Collaboration & Productivity

| # | System | Key Topics |
|---|--------|------------|
| 35 | Google Docs / Collaborative Editor | CRDT vs OT, cursor sync, presence, version history |
| 36 | Notion / Wiki System | Block-based storage, real-time sync, permissions, search |
| 37 | Figma / Collaborative Design | CRDT, multiplayer cursors, component library, large canvas rendering |
| 38 | Google Calendar | Recurring events, timezone handling, conflict detection, notifications |

### Monitoring & Observability

| # | System | Key Topics |
|---|--------|------------|
| 39 | Metrics System (Datadog / Prometheus) | Time-series DB, downsampling, alerting, cardinality |
| 40 | Distributed Tracing (Jaeger) | Span collection, sampling, trace assembly, dependency graph |
| 41 | Log Aggregation (ELK / Splunk) | Ingestion pipeline, indexing, retention, query language |

### AI / ML Platform

| # | System | Key Topics |
|---|--------|------------|
| 42 | Recommendation Engine | Collaborative filtering, embedding ANN, feature store, A/B testing |
| 43 | Ad Serving / Ad Exchange | Real-time bidding, auction, pacing, fraud detection, attribution |
| 44 | ML Feature Store & Training Platform | Feature pipelines, model registry, serving, GPU scheduling |

### Security & Identity

| # | System | Key Topics |
|---|--------|------------|
| 45 | Auth System (OAuth2 / SSO) | Token lifecycle, PKCE, refresh rotation, federation, RBAC |
| 46 | Rate Limiter | Token bucket, sliding window, distributed counters, hierarchical limits |
| 47 | API Gateway | Routing, auth, rate limiting, canary, circuit breaker, observability |

### Gaming & Miscellaneous

| # | System | Key Topics |
|---|--------|------------|
| 48 | Online Multiplayer Game Backend | State sync, lag compensation, matchmaking, leaderboard |
| 49 | IoT Platform (Smart Home) | Device registry, MQTT, time-series ingest, edge processing |
| 50 | Healthcare / Telemedicine Platform | HIPAA compliance, HL7/FHIR, scheduling, video, audit logging |

---

## Topic Coverage Matrix

| Topic | Systems Covering It |
|-------|-------------------|
| **Caching (multi-tier)** | 1, 5, 13, 19, 26 |
| **CDN / Edge** | 1, 9, 11, 12, 34 |
| **Consistent Hashing** | 25, 26, 27, 32 |
| **CRDT / OT** | 35, 36, 37 |
| **Database Sharding** | 3, 13, 20, 25, 28 |
| **Event Sourcing / CQRS** | 13, 17, 30, 31 |
| **Fan-out** | 4, 5, 29, 31 |
| **Geospatial** | 14, 21, 22 |
| **Idempotency** | 1, 17, 27, 29 |
| **Leader Election / Consensus** | 25, 27, 28 |
| **Low Latency Streaming** | 1, 8, 10, 12 |
| **ML / Ranking** | 1, 4, 11, 42, 43 |
| **Rate Limiting** | 32, 46, 47 |
| **Real-Time (WebSocket)** | 7, 30, 35, 37, 48 |
| **Search (Inverted Index)** | 4, 19, 20, 21 |
| **Security / Compliance** | 2, 17, 45, 50 |
| **Video / Audio Pipeline** | 1, 8, 9, 10, 12 |

---

*Pick any system → create an ADR + full design doc with Mermaid diagrams in this folder.*
