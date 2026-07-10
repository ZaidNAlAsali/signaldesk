# Architecture

## System boundaries

SignalDesk has three runtime services in the Compose path:

1. **Web**: a statically optimized Next.js interface. It calls the API from the browser and subscribes to case events over WebSockets.
2. **API**: a FastAPI application containing workflow validation, provider orchestration, local retrieval, and persistence boundaries.
3. **Database**: PostgreSQL in Compose and SQLite for local development and isolated tests.

The repository deliberately avoids a separate vector database, task queue, or microservice layer. The current workload does not justify that operational complexity.

## Request lifecycle

1. `POST /api/cases` validates and persists the request.
2. The repository appends `case.created` to the case's audit chain.
3. The WebSocket manager broadcasts a case-created event.
4. `POST /api/cases/{id}/analyze` loads policies from the relational store.
5. The analyzer redacts email, phone, and payment-card patterns.
6. Local retrieval scores policy sections using text overlap plus language and category preferences.
7. Deterministic mode applies transparent rules. External mode sends only redacted text and bounded policy context to the configured endpoint.
8. External JSON is validated against a strict schema and cross-field risk invariants.
9. The analysis and redaction metadata are persisted, followed by `analysis.completed` in the hash chain.
10. A reviewer approves, rejects, or overrides through the decision endpoint. The resulting decision and audit event commit in one transaction.

## Provider boundary

`Analyzer` is the application interface. Implementations return the same `AnalysisResult` regardless of transport:

- `DemoAnalyzer`: local deterministic classification and retrieval.
- `OpenAIAnalyzer`: supports Responses API and OpenAI-compatible Chat Completions transports.

The adapter owns endpoint details, retries, response extraction, schema validation, and safe exception translation. API routes do not parse provider-specific responses.

## Persistence and migrations

SQLAlchemy models are the runtime persistence layer. Alembic owns production schema changes. The API container runs `alembic upgrade head` before Uvicorn starts.

Audit sequences have a unique `(case_id, sequence)` constraint. PostgreSQL provides the primary Compose verification path. Concurrent append conflicts surface as transaction errors rather than silently creating duplicate sequence numbers. A higher-throughput production version would lock the case row or maintain an atomic per-case counter.

## Tamper-evident audit chain

Each audit hash covers a canonical serialization of:

- case identifier
- event sequence
- event type
- actor
- payload
- timestamp
- previous event hash

Changing any stored field breaks that event and all following links. The verification endpoint reports the first invalid event. ORM hooks reject normal update and delete operations, but this does not make the table immutable. A privileged database operator can rewrite an entire chain.

## Real-time behavior

The server stores active WebSocket connections in-process. Clients send heartbeats and reconnect after disconnection. This is sufficient for a single API process. Horizontal scaling would require a shared event bus such as PostgreSQL `LISTEN/NOTIFY`, Redis, or a managed pub/sub service.

## Deliberate trade-offs

- **Local keyword retrieval instead of embeddings:** deterministic, inspectable, fast, and credential-free for a small policy corpus.
- **Single service instead of microservices:** preserves transactional consistency between workflow state and audit events.
- **Pattern PII detection instead of NER:** reproducible and dependency-light, but incomplete for names, addresses, and contextual identifiers.
- **Application hash chain instead of append-only infrastructure:** demonstrates detection and verification without claiming regulatory immutability.
- **No authentication in the demo:** keeps scope focused on decision workflows. This is the largest gap before any real deployment.
