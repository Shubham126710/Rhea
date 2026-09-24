# Rules.md
## Engineering Discipline for the Dual-Layer GNN Fake News Detection System

**Status:** Draft for review.
**Depends on:** PRD.md (Approved), Architecture.md (Approved). This document governs *how code gets written* — it does not introduce new product or architectural decisions; anything here that looks like a new decision is a bug in this document, not a new requirement.

---

## 1. Non-Negotiables

These apply to every line of code, every PR, every phase, with no exceptions granted for deadline pressure:

1. **No ghost folders / no ghost files.** Every directory, module, and file must trace to a specific responsibility named in Architecture.md §2 or an explicit requirement in PRD.md. If you can't point to which section justifies a folder's existence, delete the folder.
2. **No fake functionality.** No hardcoded predictions, no fabricated confidence scores, no mocked LLM responses shipped as if real, no placeholder graph data, no "TODO: implement later" endpoints that return 200. A feature is either genuinely implemented or it does not exist yet — it is never simulated to look finished.
3. **No premature abstraction.** Don't introduce an interface, factory, or plugin system for a single implementation "in case we need another one later." Extract abstractions when a second concrete case actually exists, not before.
4. **No silent scope expansion.** If implementation reveals a need not covered by PRD.md/Architecture.md, that's a flag to raise, not a decision to make unilaterally mid-code. Small clarifications are fine; anything touching visibility, privacy, RBAC, or the GNN/LLM boundary goes back for explicit sign-off.
5. **The GNN predicts, the LLM explains — this boundary is enforced in code, not just convention.** LLM Adapter code must be structurally incapable of writing to `analyses.verdict` or `analyses.raw_score`. If a code review finds a path where the LLM's output could influence the classification, that is a severity-1 defect regardless of how it got there.
6. **Every claim needs a traceable source.** Confidence bands, "high confidence" labels, and calibration language are only used where the underlying calculation actually supports them (Architecture.md §4, `is_calibrated_prob`). If calibration hasn't been validated for the current model version, the code must render "model confidence score," never "probability" — this is enforced by the flag on the row, not by remembering to phrase things correctly in the UI layer.

---

## 2. Architectural Boundaries (enforced, not just documented)

- **Module isolation:** Only Analysis Orchestration may call Auth, Shared Preprocessing, ML Inference, Graph Processor, or LLM Adapter directly (Architecture.md §2). No module reaches across another module's boundary "just this once" to save a function call. If two modules seem to need to talk directly, that's a design smell to raise, not route around.
- **Preprocessing is one codebase, two entry points** (Architecture.md, Batch I). A bug fix to content-cleaning logic must be made once and apply to both the offline training pipeline and the online inference pipeline. Two divergent preprocessing implementations is a defect, not a shortcut.
- **`analyses.id` is the only cross-table analysis identity.** Code must never construct or compare the five-value version tuple as a stand-in identity outside the single UNIQUE-constraint lookup in Analysis Orchestration's duplicate-check function (Architecture.md §4, §6.2).
- **Graph layout never happens server-side.** The Graph Processor module returns filtered/ranked graph data only — node/edge lists, scores, metadata. If a PR adds x/y coordinates to that payload, that's out of scope for the module and goes back.
- **Rate limiting and validation are backend-enforced, full stop.** A frontend-only rate limit or a client-side-only file-size check is not a substitute for the backend check — it's a UX nicety on top of one.

---

## 3. Coding Standards

### 3.1 General (SOLID, applied pragmatically)
- Single Responsibility: a function or class does one thing named accurately by its name. If you need "and" to describe what it does, split it.
- Dependency Inversion where it earns its keep: the LLM Adapter is provider-abstracted (Architecture.md §3) *because* provider-swapping is an explicit requirement. Don't apply the same pattern to, say, the password hasher, where there's no stated need to swap Argon2id for something else.
- Prefer composition over inheritance for pipeline stages (preprocessing → encoding → graph construction → fusion → classification) — each stage is a callable with a defined input/output contract, not a subclass hierarchy.

### 3.2 Python (backend/ML)
- Type hints on all public function signatures.
- Pydantic models (or equivalent) for every API request/response body and every LLM structured-output schema (Architecture.md §5, PRD.md §4.5) — schema validation is not optional glue code, it's the mechanism that enforces Rule #6 above.
- No bare `except:` — catch specific exceptions; a caught-and-swallowed error around LLM calls or DB writes is exactly the kind of silent failure Rule #2 exists to prevent.

### 3.3 React/Frontend
- Components map to the three-pane workspace and eight nav sections (PRD.md §4.2) — no speculative component scaffolding for sections not yet built.
- Server state (analysis status, results, history) lives in query/fetch state, not duplicated into ad hoc local state that can drift from the backend's truth.
- No hardcoded copy implying functionality that doesn't exist yet (e.g., a "Compare Models" button with no backing endpoint) — see Rule #2.

### 3.4 Database
- Every migration is reversible.
- No schema change that contradicts Architecture.md §4 without that document being updated and re-approved first — the schema in Architecture.md is binding, not illustrative.

---

## 4. Versioning Discipline

Per Architecture.md §4/§6.2, four independent version dimensions exist: `model_version`, `preprocessing_version`, `graph_construction_version`, `calibration_version`. Rules:

- Any code change to preprocessing logic bumps `preprocessing_version`. Same for graph construction and calibration logic. This is not optional or "only for big changes" — the versioning exists precisely so small changes are tracked too.
- A model artifact is only ever loaded by its exact `model_version` string; there is no "latest" implicit loading path in production code.
- CI includes a check that a code change touching a versioned module without a corresponding version bump fails the build.

---

## 5. Testing Discipline

Per Architecture.md §10 — four levels are mandatory, not aspirational:

- No PR merges without unit tests for new logic in preprocessing, graph construction, auth, confidence calculation, duplicate hashing, or evidence mapping.
- ML integrity tests (no train/test leakage, reproducible seeding, model-loading correctness) run against every promoted checkpoint before it's eligible for production use — a checkpoint without passing integrity tests does not get a `model_version` string assigned.
- The E2E suite (signup → login → submit → progress → result → history → logout) must pass before any deploy to production.
- Coverage thresholds apply to the modules named in Architecture.md §2, not to the codebase as a uniform percentage — 100% coverage on trivial getters is not the goal; correctness on the modules that enforce Rule #6 and the GNN/LLM boundary is.

---

## 6. Security Rules (non-negotiable, per Architecture.md §8)

- Passwords: Argon2id only, never logged, never included in any error message or debug output.
- No secret (API key, DB credential, session signing key) ever appears in a commit, a log line, or a frontend bundle. A leaked secret is treated as compromised and rotated immediately, not "probably fine since it's a demo."
- Every server-side URL fetch goes through the SSRF-protection check (Architecture.md §6.7) with no bypass path for "trusted" internal calls.
- Every uploaded file goes through MIME/size/structure validation before touching any parsing library — no parsing-then-validating.

---

## 7. Documentation-Code Consistency

- If code diverges from PRD.md or Architecture.md during implementation, one of two things happens: the code is fixed to match the document, or the document is updated and re-approved. Code and documentation silently drifting apart is treated as a defect in the process, not a normal outcome of implementation.
- Inline comments explain *why*, not *what* — the code should already say what it does.

---

## 8. Approval

Pending review. Phases.md sequencing assumes these rules are accepted as-is.
