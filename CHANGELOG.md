# Changelog

## 0.3.0 - 2026-07-12

### Changed

- Rebuilt the frontend as a distinctive human decision room with a dispatch ledger and case dossier rather than a generic corporate dashboard.
- Replaced the sidebar and metric-card grid with an editorial masthead, connected queue pulse, evidence-forward reading path, and explicit human-control section.
- Introduced a tactile cobalt, paper, tomato, sun, and sage visual system with responsive compact layouts and reduced-motion support.
- Clarified that displayed risk is the analysis risk and that the demo model may recommend but cannot approve.
- Improved Arabic and mixed-direction presentation across request titles, descriptions, citations, and requester metadata.
- Added explicit queue filter state, selected-case state, labeled search, keyboard modal dismissal, initial dialog focus, and background-scroll containment.
- Expanded the public interface gallery with decision, Arabic, request-intake, and compact-window screenshots.

### Verified

- Frontend unit and interaction tests, ESLint, TypeScript, and production build.
- Backend lint, tests with coverage threshold, migrations, deterministic evaluation, dependency audits, bilingual regression suite, and HTTP/WebSocket workflow smoke.
- Production-like PostgreSQL Compose workflow in CI.
