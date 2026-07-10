# Safety and security

## Threat model

SignalDesk assumes request text and external-provider output are untrusted. It protects a demo environment against accidental data egress, malformed model output, permissive browser access, and unnoticed audit-row modification. It does not claim protection against a compromised host, database administrator, or authenticated insider because authentication and authorization are outside the current demo scope.

## Data-flow controls

### Before external analysis

- Email addresses, phone numbers, and payment-card-like sequences are replaced with typed placeholders.
- Redaction runs on both the description and requester name.
- Only bounded local policy excerpts are sent as grounding context.
- System instructions explicitly delimit request and policy data from instructions.

Pattern matching can miss names, addresses, account identifiers, and unusual formats. Production use would require organization-specific DLP or NER, field minimization, retention rules, and provider data-processing agreements.

### After external analysis

- The provider must return strict JSON schema output.
- Unknown fields are rejected.
- String lengths and enum values are bounded.
- Priority must match an explicit risk-score band.
- Citation identifiers come from local retrieval, not provider-generated policy references.
- Upstream errors become generic `503` responses. Tokens and raw provider bodies are not returned.
- Retry count and timeout are bounded.

## Human authority

Analysis creates recommendations only. Separate decision endpoints require an actor and note. Reviewers can approve, reject, or override category and priority. No downstream operational action is executed.

## Browser boundary

- CORS uses configured origins, `GET`, `POST`, and `OPTIONS` only.
- Allowed request headers are `Content-Type` and `Authorization`.
- Credentialed CORS is disabled.
- WebSocket handshakes reject untrusted origins.
- API and WebSocket URLs are explicit build/runtime configuration.

## Audit integrity

Audit events are ordered per case and linked through SHA-256 hashes over canonical event data. A verification endpoint recomputes the chain, rejects missing history, and reports the first invalid event. SQLAlchemy hooks prevent updates and deletes through normal ORM use; the PostgreSQL migration adds a database trigger that rejects row mutations.

This mechanism is **tamper-evident**, not immutable. A privileged operator could disable database controls and rewrite all rows and hashes. Stronger production controls could include restricted trigger ownership, signed checkpoints, external transparency storage, and independent log export.

## Secrets and dependencies

- `.env`, private keys, local databases, caches, and build outputs are ignored.
- `.env.example` contains placeholders and development-only defaults.
- GitHub Actions scans tracked files with `detect-secrets`.
- `pip-audit` and `npm audit` run in CI.
- Container images declare unprivileged runtime users.
- No credential appears in evaluation or smoke-test artifacts.

## Required controls before real deployment

1. OIDC or SSO authentication.
2. Role-based authorization and tenant isolation.
3. CSRF and session strategy appropriate to the identity provider.
4. A managed secrets store and rotated production credentials.
5. TLS termination and restrictive security headers at the edge.
6. Rate limiting, abuse monitoring, and request-size limits at the proxy.
7. Organization-specific data classification and retention policy.
8. Database least privilege, encrypted backups, and recovery tests.
9. Centralized logs, metrics, traces, and alerting.
10. Formal provider privacy, residency, and retention review.

## Security verification

Backend tests cover PII replacement, provider schema failures, safe missing-key handling, WebSocket origin rejection, hash-chain verification, tampering detection, missing-history detection, and ORM append-only protection. When green, the CI Compose job exercises bilingual decisions, citations, WebSockets, and audit-chain verification against PostgreSQL.
