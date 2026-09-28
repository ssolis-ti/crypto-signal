# Feature Specification: Pin Direct Dependencies for Reproducible Builds

**Feature Branch**: `main` (Spec Kit feature directory: `specs/008-pin-dependencies`)

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "Dejar el bot pulido y operable para despliegue." Part of deployment
readiness: `app/requirements-step-1.txt` and `app/requirements-step-2.txt` use unbounded `>=` pins
for every direct dependency (`ccxt>=4.0.0`, `pandas>=2.0.0`, `python-telegram-bot>=21.0`, etc.) —
exactly the pattern Constitution Principle VII closes off ("Python dependencies... MUST use exact or
narrowly-bounded version pins... once a version is confirmed working, so a rebuild cannot silently
pull a breaking release"). Today's `Dockerfile` does `COPY ./app` then `pip install` at image-build
time with no lockfile, so a rebuild on a different day can silently resolve different (potentially
breaking) versions of every direct and transitive dependency — a real risk for an unattended
production deployment about to go live.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A rebuild today or in six months installs the same, already-tested versions (Priority: P1)

**Why this priority**: This is the actual deployment-readiness risk: the versions currently proven by
88/88 passing tests (`crypto-signal:dev`, built 2026-09-28) are not guaranteed to be what the next
`docker build` resolves once any upstream package ships a new release.

**Independent Test**: Pin every direct dependency in both requirements files to its exact
currently-installed, currently-tested version; rebuild the Docker image from scratch
(`--no-cache`); confirm the full test suite still passes unchanged against the freshly-built image.

**Acceptance Scenarios**:

1. **Given** `app/requirements-step-1.txt` and `app/requirements-step-2.txt`, **When** inspected,
   **Then** every direct dependency uses `==` with the exact version currently proven by the test
   suite (no bare `>=` remaining on a direct dependency).
2. **Given** a from-scratch, no-cache image rebuild, **When** the full test suite runs inside it,
   **Then** all tests pass with no version-related failures.

### Edge Cases

- Transitive dependencies (e.g. `numpy`'s own sub-dependencies) are NOT individually pinned by this
  feature — Principle VII's text specifically scopes the requirement to "direct dependencies," and a
  full transitive lockfile is a larger, separate tooling decision (e.g. `pip-compile`) not requested
  here.
- `TA-lib` (PyPI package name, lowercase-sensitive in the requirements file) resolves to the
  `TA-Lib` distribution; the exact installed version is pinned by its version string, not by
  re-casing the package name (avoids an unrelated, unrequested change).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every direct dependency listed in `app/requirements-step-1.txt` MUST be pinned with
  `==` to its exact version as currently installed and tested in the `crypto-signal:dev` image.
- **FR-002**: Every direct dependency listed in `app/requirements-step-2.txt` MUST be pinned with
  `==` to its exact version as currently installed and tested in the `crypto-signal:dev` image.
- **FR-003**: No dependency's pinned version MUY differ from what is already installed and passing
  in the current image — this feature pins the status quo, it does not upgrade or downgrade anything.
- **FR-004**: After pinning, a from-scratch (`--no-cache`) Docker image rebuild MUST succeed and the
  full existing test suite MUST pass unchanged inside it.

### Key Entities

- **`app/requirements-step-1.txt`**: pre-TA-Lib-compilation base deps (`numpy`, `Cython`).
- **`app/requirements-step-2.txt`**: main application deps (14 direct packages).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `grep ">=" app/requirements-step-1.txt app/requirements-step-2.txt` returns zero
  matches after this feature.
- **SC-002**: A `--no-cache` rebuild of the Docker image completes successfully.
- **SC-003**: The full test suite (88 tests as of slice 007) passes unchanged inside the freshly
  rebuilt image.

## Assumptions

- The versions currently installed in `crypto-signal:dev` (built 2026-09-28, exercised by all of
  slices 001-007's test runs) are the correct ones to pin — they are the only versions this project
  has actually been validated against.
