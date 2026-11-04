# Benchmark reproduction protocol

CI runs the paired scheduler microbenchmark on separate GitHub-hosted Linux, macOS and Windows runner VMs (Python 3.12), and uploads a machine-labelled JSON artifact for each operating system. Each run records environment metadata, raw paired samples, alternating execution order and a seeded bootstrap interval for the paired median difference.

These hosted VMs provide cross-platform runner replication, not independent third-party laboratories or a guarantee of distinct physical hardware. Virtualized CPU scheduling, noisy neighbours, thermal and power management, filesystem and runtime differences can affect results. The baseline is a reference implementation, not a production competitor. Do not pool measurements across OSes as though they were identically distributed. For stronger claims, repeat on independently administered physical machines and preserve the raw artifacts and exact revision.
