<!--
Sync Impact Report
- Version change: (none) → 1.0.0
- Modified principles: n/a (initial ratification)
- Added sections: Core Principles (I-VII), Security & Data Handling, Development Workflow,
  Governance
- Removed sections: none
- Templates requiring updates: .specify/templates/* — not yet reviewed against this
  constitution; flag for check during next /speckit-plan run
- Follow-up TODOs:
  - TODO(RATIFICATION_DATE): confirmed as 2026-09-28 (date this constitution was first drafted
    and adopted by the operator for the `main` branch effort). No earlier ratification exists.
This report is scratch material for human review and should be removed once the amendment
is reviewed and committed.
-->

# Crypto-Signal Constitution

## Core Principles

### I. Read-Only, No Custody (NON-NEGOTIABLE)
This project is a technical-analysis alerting bot, not a trading bot. It MUST NOT hold, request,
or accept exchange API keys, secret keys, or any credential capable of placing orders,
withdrawing funds, or modifying account state. All exchange access is limited to public market
data (OHLCV, tickers, order books) via CCXT with `enableRateLimit` honored. Any future feature
that would require trading credentials MUST be rejected at the specification stage, not deferred
to implementation.
*Rationale*: the project's entire value is generating signals a human reviews; introducing
custody or order-placement capability changes its risk profile from "informational" to
"financial," which is out of scope and explicitly not wanted by the operator.

### II. No Repaint (NON-NEGOTIABLE)
Indicator and signal calculations MUST use only fully closed candles. The most recent
(in-progress) candle for the configured `candle_period` MUST be excluded from any indicator
computation, hot/cold threshold check, or score calculation before it closes. A signal that
would disappear or flip if recomputed one tick later is a defect, not an acceptable tradeoff.
*Rationale*: repainting produces alerts that are not reproducible and erodes trust in every
downstream feature (scoring, market context, notifications) built on top of the signal.

### III. Validate Before You Trust a Heuristic
Any scoring, weighting, or classification heuristic (including but not limited to
`SignalEnhancer`'s 0-100 score and quality tiers A+/A/B/C) MUST be validated against historical
market data — showing that higher-scored signals actually perform better on some measurable
forward-looking outcome — before it is allowed to gate which alerts reach the user (e.g. via
`min_quality` filters or smart-notification detail thresholds). Until validated, a heuristic MAY
ship as informational-only (visible in the message, not used to suppress alerts). Validation
results and methodology MUST be recorded alongside the feature that introduces or changes the
heuristic.
*Rationale*: hand-tuned weights (e.g. `btc_weight`, `structure_weight`, `rsi_weight`) look
reasonable but are unverified opinion until tested; suppressing signals based on an unverified
score can hide the exact information the user needs.

### IV. Secrets Never Enter Version Control or the Image
Credentials (Telegram bot token, chat ID, and any future notifier credential) MUST be supplied
only via environment variables at runtime (`.env`, loaded through `env_file` in
`docker-compose.yml`). `config.yml` MUST NOT contain live credentials when committed; the
repository MUST only ever track `config.yml.example` / `config-clean.yml` as templates.
`config.yml` and `.env` MUST remain in `.gitignore`. The Docker image MUST NOT `COPY` a
credential-bearing file into any layer.
*Rationale*: this is a personal financial-adjacent tool; a leaked token allows an attacker to
impersonate the bot's alerts or exhaust its Telegram rate limits, and a leaked chat ID enables
spam/phishing targeting the operator.

### V. UTC Internally, Local Time Only at Presentation
All timestamp handling, comparisons, and storage internal to data collection, indicator
calculation, and correlation/context analysis MUST use UTC (timezone-aware datetimes). Local
timezone conversion (`settings.timezone`, e.g. `America/Santiago`) MUST happen only at the
final notification-rendering step, never earlier in the pipeline.
*Rationale*: mixing naive local time with exchange UTC timestamps (as found in the current
`analyzers/utils.py` datetime handling) causes silent off-by-hours bugs in indicator windows and
in correlation with market context, which are hard to detect because they don't crash.

### VI. Tests Guard the Core Pipeline
`analysis/` (`MarketContext`, `SignalEnhancer`, `StrategyAnalyzer`), `data/` (`DataManager`,
`DataCache`, `PairResolver`), and `notifications/` (queue, smart manager, builder, core) MUST
have automated tests covering: normal operation, at least one edge case (empty/partial exchange
data, rate-limit/network error, malformed config), and the specific regression each bug fix
addresses. A bug fix MUST include a test that fails before the fix and passes after
(`speckit-bug-fix` / `speckit-bug-test` flow). New features in these packages MUST NOT ship
without tests in the same change.
*Rationale*: these packages are the "god nodes" of the dependency graph (confirmed via Graphify:
`IndicatorUtils`, `Notifier`, `SignalEnhancer`, `MarketContext` are the most-connected
abstractions) — a defect here propagates to every indicator and every notification channel.

### VII. Dependencies Are Pinned, Debug Logging Is Not Permanent
Python dependencies in `requirements-step-1.txt` / `requirements-step-2.txt` MUST use exact or
narrowly-bounded version pins (no bare `>=` for direct dependencies) once a version is confirmed
working, so a rebuild cannot silently pull a breaking release. Debug-only `logger.debug`/print
statements added to diagnose a specific issue MUST be removed or demoted before the change is
merged to `main`; permanent operational logging MUST use the project's structured logger
(`structlog`) at an appropriate level (`info`/`warning`/`error`), not ad-hoc debug prints left
over from investigation.
*Rationale*: the current `requirements-step-2.txt` (`ccxt>=4.0.0`, `pandas>=2.0.0`, etc.) and
several commits titled `debug: ...` on `experimental/correlation` are exactly the pattern this
principle closes off going forward.

## Security & Data Handling

- No exchange trading credentials anywhere in this repository, ever (see Principle I).
- Telegram token/chat ID: environment variables only (see Principle IV); the operator configures
  them locally via `.env`, never pasted into chat, issues, or commit messages.
- Third-party code (forked libraries, copy-pasted indicator implementations) MUST be reviewed for
  unsafe patterns (`eval`, `exec`, unchecked `subprocess`, unpinned remote downloads such as the
  current `wget` of TA-Lib source in the Dockerfile) before being merged; unsafe patterns found
  MUST be fixed or the change MUST be rejected.
- Generated artifacts (Graphify's `graphify-out/`, Spec Kit's local feature-pointer state) are
  local tooling output, not project data, and MUST stay out of version control.

## Development Workflow

- Every feature or fix on `main` goes through the Spec Kit flow appropriate to its type:
  `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement` →
  `/speckit-converge` for features; `/speckit-bug-assess` → `/speckit-bug-fix` →
  `/speckit-bug-test` for defects. Skipping stages is permitted only for trivial, reviewed-inline
  changes (typo fixes, comment updates) that touch no logic in `analysis/`, `data/`, or
  `notifications/`.
- Each change is scoped to one bounded slice (e.g. "remove repaint from RSI/MACD indicators," not
  "rewrite the indicator layer"). Full-system rewrites are decomposed into sequential specs.
- Before implementing against existing code, the relevant Graphify graph (`graphify update .`)
  SHOULD be refreshed so plans account for the current dependency structure, especially for
  changes touching a god node (Principle VI's list).
- Commit messages follow Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`),
  consistent with existing history on `develop`/`experimental/correlation`.

## Governance

This constitution supersedes prior informal practice for the `main` branch. Amendments require:
1. A proposed diff to `.specify/memory/constitution.md` with a Sync Impact Report (as produced by
   `/speckit-constitution`).
2. Operator review and explicit approval before the amendment is committed.
3. A version bump following semantic versioning: MAJOR for removing or redefining a principle,
   MINOR for adding a principle or materially expanding guidance, PATCH for wording/clarity fixes.

All `/speckit-plan` and `/speckit-analyze` runs MUST verify the proposed design against these
principles; a plan that conflicts with a NON-NEGOTIABLE principle (I or II) MUST be rejected and
reworked, not annotated as an accepted exception. Complexity introduced beyond what a principle
requires MUST be justified in the plan's rationale.

**Version**: 1.0.0 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-09-28
