# Distributed worker protocol

Chronos includes a working asynchronous worker message path:
- HMAC-SHA256 authenticated JSON envelopes;
- authenticated acknowledgements tied to message IDs;
- size-bounded newline framing;
- durable SQLite WAL inbox and outbox tables with FULL synchronous mode;
- persistent deduplication and conflicting-message-ID rejection;
- exponential retry backoff after network failures;
- handler registration and explicit inbox processing.

## Delivery semantics

The sender removes an outbox record only after receiving a valid authenticated acknowledgement. The receiver durably records an inbox message before acknowledging it. Duplicate delivery of the same ID and body is acknowledged without inserting a second inbox row. Reuse of an ID with different content is rejected.

Inbox processing is at-least-once: a process may terminate after a handler performs its side effect but before the processed marker is committed. Handlers must therefore be idempotent or implement their own transactional outbox/inbox boundary. This protocol does not promise exactly-once side effects.

## Security and fault model

HMAC authenticates integrity and possession of a shared secret; it does not encrypt traffic. Configure TLS through the supplied SSL contexts on untrusted networks, provision secrets securely, and rotate them operationally. This first worker protocol does not implement consensus, membership epochs, leader election, state partitioning, quorum writes, automatic conflict resolution or Byzantine fault tolerance. A partition leaves messages in the durable outbox for retry when connectivity returns.
