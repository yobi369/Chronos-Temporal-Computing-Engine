# Distributed event ingestion and causal reconciliation

DistributedEvent carries an origin and Lamport timestamp around an existing immutable Event. reconcile_events deduplicates identical IDs, rejects conflicting duplicates and missing parents, then emits a deterministic topological ordering. Lamport/origin/time/sequence/ID provide a deterministic tie-break among currently causally ready events.

This is a merge protocol for already-collected batches, not network execution, consensus, leader election, exactly-once delivery, global wall-clock ordering, or partition tolerance. A production distributed engine still needs authenticated identities, durable inbox/outbox, retry/idempotency policy, membership epochs, transport security, partition ownership and an explicit conflict policy for concurrent writes.
