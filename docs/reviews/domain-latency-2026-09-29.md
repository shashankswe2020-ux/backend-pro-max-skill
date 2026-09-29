# Latency Numbers Review - 2026-09-29

## Scope and Outcome

Reviewed all 26 existing rows in [src/backend-pro-max/data/latency-numbers.csv](../../src/backend-pro-max/data/latency-numbers.csv) after reading the backend-pro-max skill. Only that CSV and this ledger were edited. No terminal tools, benchmarks, test execution, shared-file edits, commits, or pushes were performed.

- 26 existing rows revised; 0 added, removed, or renamed; original row order retained.
- 12 `Latency` cells changed; 14 numerical values/ranges retained with corrected scope and uncertainty.
- 4 dates advanced to `2026-09-29`: NIC serialization, NVMe sequential transfer, and both cross-region examples.
- 22 dates intentionally remain `2025-01`: 7 historical measurement rows, 1 undated throughput extrapolation, 1 general S3 guidance row without verified same-region scope, and 13 unverified planning assumptions.
- Evidence classification: 9 measurement-backed examples (7 historical and 2 dated 2026 Azure examples), 3 analytical/extrapolated examples, 1 documented general guidance range, and 13 unverified numeric assumptions. None is a performance guarantee.
- All 26 `Source Type` cells populated: 9 `benchmark`, 14 `official-docs`, 2 `rfc`, 1 `engineering-blog`. The type describes the source, not proof of every numeric claim in its row.

The nine-column schema is unchanged. `Latency` remains a number or ASCII-hyphen numeric range followed by its existing unit spelling (`ns`, Greek-mu `μs`, or `ms`). Qualifications and arithmetic are in `Hardware Era` and `Notes`, not mixed into numeric cells. Units and `Order of Magnitude` labels are retained as scale categories; they do not imply statistical confidence. No extra concepts were added: correcting the existing values and preserving uncertainty was more useful than introducing additional unspecific timings.

## Evidence and Date Policy

All sources below were checked using `fetch_webpage` on 2026-09-29. A successful fetch is not numerical verification. Primary means the benchmark author's own measurements, the vendor/project's documentation, or an IETF specification. Independent microbenchmarks are authoritative only for their stated experiment, not for an entire hardware generation.

`Last Updated` is advanced only for the two explicitly derived transfer models and the two dated Azure measurements. It is a review date, not a new benchmark date. Older measurements retain the existing stale marker even where their transcription is now verified. The original `2025-01` marker must not be interpreted as their measurement date. Undated living documentation and stale host measurements are not relabeled as 2026 experiments.

## Row Ledger

Values below use ASCII `us` for readability; the CSV retains its original microsecond symbol. H = historical primary measurement; D = derived/extrapolated; M = dated 2026 primary measurement; G = general vendor guidance with unresolved row scope; U = exact number unverified.

| # | Existing Operation | Before -> After | Evidence and Scope | Date Decision and Unresolved Uncertainty |
| --- | --- | --- | --- | --- |
| 1 | L1 cache reference | 1 -> 0.9 ns | H; [7-cpu Zen3][zen3]: Ryzen 5600G at 4.45 GHz; simple pointer access is 4 cycles, converted to 0.90 ns. | Keep stale. Source also reports 5 cycles for complex addressing; exact test date is unspecified. Not a Zen4 result. |
| 2 | L2 cache reference | 4 -> 2.7 ns | H; [7-cpu Zen3][zen3]: 12 cycles / 4.45 GHz = 2.70 ns. | Keep stale. Same host only; remove the unsupported universal 4x L1 ratio. |
| 3 | L3 cache reference | 12 -> 10.6 ns | H; [7-cpu Zen3][zen3]: 47 cycles / 4.45 GHz = 10.56 ns for 5600G/Cezanne. | Keep stale. Cache topology and slice/core placement vary; not all Zen3 processors have this result. |
| 4 | Branch mispredict | 3 -> 3.4-4.3 ns | H; [7-cpu Zen3][zen3]: 15-16 cycles on micro-op cache hit; about 19 on miss; convert at 4.45 GHz. | Keep stale. Range combines different stated conditions, not a percentile interval. Remove unsupported 95% prediction accuracy. |
| 5 | Mutex lock/unlock | 17 -> 66 ns | H; [Preshing][mutex], 2011-11-24: uncontended pthread lock/unlock pair on Core 2 Duo under Ubuntu 11.10. | Keep stale. Text substantiates 66 ns, not 17 ns on Linux 5.x. Library fast paths, contention, and scheduling remain platform dependent. |
| 6 | Main memory reference (DRAM) | 100 -> 84.6 ns | H; [7-cpu Zen3][zen3]: 47 cycles plus 74 ns on 5600G with 16 GB dual-channel PC4-24000 15-16-16-35 DDR4. | Keep stale. 47 / 4.45 + 74 = 84.56 ns. Not DDR5, CAS alone, or evidence for 200 ns remote NUMA. |
| 7 | Context switch (Linux) | 3-5 -> 1.2-1.5 us | H; [Bendersky][context], 2018-09-04: Haswell i7-4771; pipe and condition-variable tests pinned to one core. | Keep stale. Direct cost only, excluding working-set disruption; unpinned result about 2.2 us. Remove unsupported generic process-switch range. |
| 8 | Compress 1KB with Snappy | 2 -> 4 us | D; [Snappy README][snappy]: one Core i7 core in 64-bit mode; about 250 MB/s or more compression, 500 MB/s or more decompression for its slowest benchmark inputs. | Keep stale. 1000 / 250000000 seconds is an illustrative bulk-rate extrapolation, not measured 1KB call latency. CPU model, benchmark date, and small-block overhead are unspecified. |
| 9 | RDMA round trip | 2 us unchanged | U; [perftest README][rdma], testing methodology: measures RTT but reports half as one-way latency; synthetic microbenchmarks do not emulate application traffic. | Keep stale. No NIC/firmware, verb, size, topology, or percentile establishes 2 us RTT. Do not copy half-RTT output directly into this row. |
| 10 | NVMe SSD random 4KB read | 10 us unchanged | U; [Samsung PM9A3][pm9a3] supports product bandwidth claims, not this 10 us random-read response time. Linked datasheet could not be extracted. | Keep stale. SKU, firmware, QD, read size, cache state, and percentile unresolved. IOPS at high QD is not reciprocal response latency; remove 10x SATA claim. |
| 11 | Send 2KB over 1Gbps NIC | 16 us unchanged | D; [Cisco serialization section][serialization], document updated 2006-02-02, distinguishes frame serialization from queueing/processing. Apply its model to explicitly assumed 2000 B payload and 1 Gbit/s. | Advance review date, not benchmark date. 2000 * 8 / 1e9 = 16 us; excludes all framing/segmentation, kernel, propagation, and queueing. 2 KiB is 16.384 us; 10 Gbit/s payload-only result is 1.6 us. |
| 12 | NVMe SSD sequential read 1MB | 50 -> 147 us | D; [Samsung PM9A3][pm9a3] advertises up to 6800 MB/s. 1000000 / 6800000000 seconds = 147.06 us. Product page lists its datasheet resource as 2022-08-18. | Advance review date for corrected derivation only. Ideal bulk transfer component, not isolated 1MB read latency; SKU/QD and command/queueing overhead remain unresolved. No new device benchmark claimed. |
| 13 | Redis GET (localhost) | 100 us unchanged | U; [Redis benchmark guide][redis] distinguishes concurrency/pipelining throughput from response latency. Its pipeline-16 example reports GET P50 0.391 ms despite 1811594.25 ops/s. | Keep stale. That example does not verify 100 us for this workload. Remove the claim that pipelining makes individual responses below 10 us; payload, clients, hardware, and version required. |
| 14 | SATA SSD random 4KB read | 100 us unchanged | U; [Samsung PM893][pm893] advertises up to 98000 random-read IOPS at QD32; FIO 2.7, RHEL 6.5/kernel 2.6.32, Z170 SATA 6G port, whole LBA range, write cache enabled. | Keep stale. This is neither proof of 100 us nor a QD1 measurement. Remove obsolete IOPS range and fixed NVMe ratio. |
| 15 | Same-AZ network round trip | 0.5 ms unchanged | U; [AWS AZ whitepaper][az] explains AZ topology and connectivity, not a 0.5 ms same-AZ benchmark. | Keep stale. Cloud provider, region, instance type, placement, packet size, transport, load, and percentile unspecified. Remove cross-provider sub-ms generalization. |
| 16 | PostgreSQL simple query | 0.5 ms unchanged | U; [pgbench documentation][postgres] defines select-only `-S` and client-side per-statement measurement; example output lacks a transferable hardware workload. | Keep stale. No primary experiment verifies this exact 0.5 ms. Cache state, protocol/prepared mode, schema/query, concurrency, and network unresolved. |
| 17 | Cross-AZ network round trip | 1 ms unchanged | U; [AWS AZ whitepaper][az] states single-digit-ms synchronous replication and AZ separation up to roughly 100 km. | Keep stale. Replication guidance is not an exact network RTT benchmark or a fixed 2x same-AZ multiplier; no AWS/GCP/Azure equivalence established. |
| 18 | Kafka produce ack (acks=1) | 2 ms unchanged | U; [Kafka 4.1 producer configuration][kafka] defines leader-only ack, all-ISR ack, and no-ack semantics. `linger.ms` default changed from 0 to 5 in Kafka 4.0. | Keep stale. No measured 2 ms, fixed additional 5-10 ms for `acks=all`, or below-1-ms delivery for `acks=0`. Batching can send before linger expires; backpressure can delay longer. `acks=1` does not provide follower replication durability. |
| 19 | HDD seek | 4 ms unchanged | U; [Seagate RPM discussion][hdd] substantiates rotational-speed context but gives no matching 4 ms seek benchmark. Exos manual extraction failed. | Keep stale. Model and seek distance unknown. At assumed 7200 RPM, half a revolution is 4.17 ms; that is rotational wait, not head seek or total I/O latency. Remove IOPS inference. |
| 20 | TLS handshake | 5 ms unchanged | U; [RFC 8446][tls], August 2018, section 2 full-handshake flow; sections 2.1 and 2.3 cover HelloRetryRequest and early data. | Keep stale. RFC verifies RTT structure, not 5 ms. Normal client application send follows one RTT plus processing on established transport; TCP separate. Retry adds RTT; 0-RTT requires PSK and replay-safe use, not zero elapsed latency. |
| 21 | DynamoDB GetItem | 5 ms unchanged | U; [AWS latency guide][dynamo] documents single-digit-ms average `SuccessfulRequestLatency` for most singleton operations and excludes client/network time. | Keep stale. 5 ms is only an illustrative point, not a verified benchmark, p99, or end-to-end guarantee. Item size, consistency, endpoint, retries, and connection reuse matter. |
| 22 | S3 GET (same region) | 10-50 -> 100-200 ms | G; [AWS S3 performance guide][s3] actually quotes roughly 100-200 ms for small objects and first-byte-out of larger objects. | Keep stale. Source does not identify a same-region test setup, percentile, or named storage class for that statement. Use only as general S3 planning guidance; not Express One Zone or full-object transfer. Original 10-50 ms was unsupported by its citation. |
| 23 | DNS resolution (cold) | 20-120 ms unchanged | U; [Google Public DNS performance][dns] explains client-resolver RTT, upstream misses, and timeout tails. Its undated Googlebot observations are 130 ms average for responding nameservers and 300-400 ms including failures. | Keep stale. Those crawler observations are not a contemporary universal cold-DNS benchmark. Original range is an unverified scenario, not a 120 ms ceiling; remote cache hits still pay RTT. |
| 24 | TCP handshake (same AZ) | 0.5 ms unchanged | U; [RFC 9293][tcp], August 2022, section 3.5/Figure 6: SYN, SYN-ACK, final ACK. | Keep stale. Client establishment approximately one loss-free RTT; server establishment awaits final ACK. RFC does not verify 0.5 ms, same-AZ placement, DNS, TLS, or retransmission latency. |
| 25 | Cross-region round trip (US-EU) | 70 -> 71 ms | M; [Azure latency statistics][azure], UK/Northern Europe table: source East US, destination North Europe, 71 ms P50 RTT; 30-day window ending 2026-07-30; 1-minute probe sampling. | Advance review date; retain actual observation window. Specific Azure backbone example, not arbitrary US-EU RTT, p99, SLA, or speed-of-light bound. Reverse-source entry is a separate measurement. |
| 26 | Cross-region round trip (US-Asia) | 150 -> 108 ms | M; [Azure latency statistics][azure], Japan table: source West US, destination Japan East, 108 ms P50 RTT; same 30-day window and sampling. | Advance review date. Specific Azure example, not all US/Asia routes. Remove unsupported higher-variance comparison; no tail distribution or workload-path guarantee supplied. |

## Source Provenance

The links in each ledger row identify the exact fetched primary page. Living pages may change; the salient numeric evidence and limitations are recorded above. For the Azure page, returned metadata identifies source commit `f6dd2afa032abe06ed99a0eac334a8881a8c1398`, document date 2026-07-30, and update timestamp 2026-08-20. These are publisher metadata, not locally reproduced measurements. The Snappy README returned latest-commit link `5973530841ecb9b2ef65364d4c5568a268c29e00`; that does not date its Core i7 benchmark. The Zen3 page includes Linux 5.14 and 7-Zip 21.07 output, but their version dates are not proof of the latency experiment's date.

Fetch failures and rejected evidence:

- Original cache URL `https://www.7-cpu.com/cpu/Zen4.html`: Not Found. Replaced with a fetched Zen3 experiment and changed the platform and numbers accordingly; no Zen4 measurement invented.
- Original context-switch URL `https://eli.thegreenplace.net/2018/measuring-context-switching-and-memory-bandwidths/`: Not Found. Correct article is linked in row 7.
- PM9A3 linked [datasheet PDF](https://download.semiconductor.samsung.com/resources/data-sheet/Samsung_SSD_PM9A3_Data_Sheet_Rev1.0.pdf): failed meaningful-content extraction. Only the readable product page supports the bandwidth derivation; no PDF latency/QD claim imported.
- Attempted [Seagate Exos X18 manual](https://www.seagate.com/files/www-content/product-content/enterprise-hdd-fam/exos-x18/en-us/docs/100865854c.pdf): failed meaningful-content extraction. Not treated as verified evidence for seek time.
- Original [Cloudflare packet-rate article](https://blog.cloudflare.com/how-to-receive-a-million-packets/) was fetched: published 2015-06-16, using 32-byte UDP payloads, 10G Solarflare NICs, and dual six-core 2 GHz Xeon hosts. It does not measure 2KB over 1Gbps. Its displayed 2026 modification timestamp is not a benchmark refresh. Replaced with Cisco's serialization explanation and explicit arithmetic.
- Attempted Cisco URL ending `6407-voip-delay-details.html`: HTTP 404; the fetched document is ID 5125, linked below.
- Google Cloud Performance Dashboard URL ending `/concepts/metrics` redirected to `docs.cloud.google.com`, whose corresponding URL returned HTTP 404. No figures taken from it; Azure's fetched dataset supplies rows 25-26 instead.
- Wikipedia descriptions, a generic VPC introduction, monitoring configuration pages, and a submarine cable map do not establish the original precise numeric examples. Replacements are either primary numerical evidence or explicitly labeled context-only sources.

## Numerical Validation Handoff

Every patch was followed immediately by `get_errors`; the CSV checks reported no editor diagnostics. This does not execute CSV parsing, calculation checks, or repository tests. Parent must run calc/schema/tests; none was run here and no passing runtime result is claimed.

1. Parse with a CSV parser; assert the original nine-column header, 26 rows, unchanged ordered operation names, nine fields per record, nonempty sources, valid source-type enums, 4 review dates at `2026-09-29`, and 22 at `2025-01`.
2. Exercise scalar and range parsing, especially `0.9 ns`, `3.4-4.3 ns`, `1.2-1.5 μs`, `147 μs`, and `100-200 ms`. Retain the existing Greek mu U+03BC spelling; do not silently substitute micro sign U+00B5. No inequality, formula, percentile label, or approximation prefix was inserted into `Latency`.
3. Recheck dimensional arithmetic: `4/4.45 = 0.8989 ns`; `12/4.45 = 2.6966 ns`; `47/4.45 = 10.5618 ns`; `15/4.45 = 3.3708 ns`; `19/4.45 = 4.2697 ns`; `47/4.45 + 74 = 84.5618 ns`. Stored values are rounded, not exact bounds.
4. Recheck `1000/250e6 = 4 us`; `2000*8/1e9 = 16 us`; `2048*8/1e9 = 16.384 us`; `2000*8/10e9 = 1.6 us`; `1e6/6.8e9 = 147.0588 us`. One MiB at that rate would be 154.2024 us, not the decimal-MB row value. The old 50 us implied 20 GB/s, inconsistent with the PM9A3 claim.
5. Recheck `60000/7200/2 = 4.1667 ms` only as uniform-phase mean rotational wait. Do not change the row's seek value to this result or derive total I/O latency from it.
6. Run repository schema validation, calc tests, and relevant data/search tests. Changed numeric examples are intentional; row identities and unit shapes must remain compatible. No production benchmark or SLO acceptance can be inferred from these tests.

Residual risk: consumers that discard `Notes` and `Hardware Era` will still see 13 unverified numeric assumptions and a same-region S3 row whose exact scope is unresolved. Fixing that representation would require a schema/consumer change outside this task. Do not treat retained stale numbers as verified defaults or calculate service capacity from inverse latency when concurrency is unspecified.

[zen3]: https://www.7-cpu.com/cpu/Zen3.html
[mutex]: https://preshing.com/20111124/always-use-a-lightweight-mutex/
[context]: https://eli.thegreenplace.net/2018/measuring-context-switching-and-memory-overheads-for-linux-threads/
[snappy]: https://github.com/google/snappy/blob/main/README.md
[rdma]: https://github.com/linux-rdma/perftest
[pm9a3]: https://semiconductor.samsung.com/ssd/datacenter-ssd/pm9a3/
[serialization]: https://www.cisco.com/c/en/us/support/docs/voice/voice-quality/5125-delay-details.html
[redis]: https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/benchmarks/
[pm893]: https://semiconductor.samsung.com/ssd/datacenter-ssd/pm893/
[az]: https://docs.aws.amazon.com/whitepapers/latest/aws-fault-isolation-boundaries/availability-zones.html
[postgres]: https://www.postgresql.org/docs/current/pgbench.html
[kafka]: https://kafka.apache.org/41/configuration/producer-configs/
[hdd]: https://www.seagate.com/tech-insights/choosing-high-performance-storage-is-not-about-rpm-anymore-master-ti/
[tls]: https://www.rfc-editor.org/rfc/rfc8446.html#section-2
[dynamo]: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TroubleshootingLatency.html
[s3]: https://docs.aws.amazon.com/AmazonS3/latest/userguide/optimizing-performance.html
[dns]: https://developers.google.com/speed/public-dns/docs/performance
[tcp]: https://www.rfc-editor.org/rfc/rfc9293.html#section-3.5
[azure]: https://learn.microsoft.com/en-us/azure/networking/azure-network-latency