# Interview guide

## Thirty-second explanation

SignalDesk is a bilingual operations decision console. It receives English or Arabic requests, redacts common PII, retrieves relevant local policy passages, and produces structured triage through either deterministic rules or a schema-constrained external model. A human approves, rejects, or overrides the recommendation. Every transition is stored in a per-case hash chain and queue updates stream over WebSockets.

## Architecture choices to defend

### Why not build a chatbot?

The core business object is a request with state, evidence, ownership, and a decision. A queue-and-workspace interface exposes those operational constraints more clearly than conversational history.

### Why keep deterministic mode?

It makes the project runnable without a paid key, gives tests a stable oracle, and provides a fallback when the provider is unavailable. It also separates product workflow quality from model availability.

### Why retrieve policies before calling the provider?

The application owns the policy corpus and citation identifiers. Retrieval limits context size and prevents the provider from inventing citations. The model produces triage language, while the application attaches only locally retrieved evidence.

### Why validate model output twice?

JSON schema constrains generation, but the application still treats the response as untrusted. Pydantic enforces types and lengths, and a model-level validator checks that priority agrees with the risk-score band.

### Why call the audit log tamper-evident instead of immutable?

Hashes reveal row modifications because each event commits to the prior hash. They do not stop a privileged administrator from rebuilding the whole chain. True immutability needs external trust or stronger infrastructure controls.

### Why PostgreSQL plus SQLite?

SQLite keeps local development and tests lightweight. PostgreSQL is the Compose target and exercises the migration path and relational constraints under a production-grade database.

### Why one backend service?

Analysis, workflow state, decision records, and audit events need consistent transactions. Splitting them now would create distributed consistency and deployment costs without enough load or organizational need.

## Evidence to quote accurately

- Backend CI runs pytest and enforces at least 80% measured application coverage.
- Frontend CI runs tests, linting, type checking, dependency auditing, and a production build.
- The 24-case authored bilingual regression suite passed all documented category, priority, policy, and redaction expectations.
- The local deterministic benchmark measured 917.64 median operations per second, 0.961 ms p50, and 1.6796 ms p99 over 5,000 operations on the documented development laptop.
- GitHub Models was called live with two synthetic English and Arabic requests using strict structured output.

Always describe the 24-case result as a regression suite, not model accuracy. Always scope the benchmark to in-process deterministic analysis. Never imply production users, operational impact, or public deployment unless those facts later become true.

## Failure modes and next changes

- **Provider outage:** deterministic mode remains available; external mode returns a bounded safe error after retries.
- **Malformed provider response:** validation rejects it and no analysis is persisted.
- **PII miss:** pattern redaction is incomplete; production would add organization-specific DLP and data minimization.
- **Concurrent audit append:** the unique sequence constraint prevents duplicates; production scale would lock the case row or use an atomic counter.
- **Multiple API replicas:** the in-memory WebSocket manager would need shared pub/sub.
- **Privileged database rewrite:** the audit chain can be rebuilt; signed external checkpoints would strengthen detection.
- **Unauthorized access:** there is no authentication in this demo, so it must not be internet-exposed as-is.

## Useful walkthrough

1. Open an untriaged English outage and run analysis.
2. Explain the risk score, recommendation, and English incident citation.
3. Show an Arabic access request and the RTL content plus Arabic least-privilege citation.
4. Approve one request, reject another, and override the Arabic request's priority.
5. Open audit history and explain sequence, previous hash, current hash, and verification status.
6. Point to deterministic mode, then the external-provider contract test and live synthetic smoke artifact.
7. Finish with CI, Compose/PostgreSQL, and the known limitations rather than claiming production readiness.
