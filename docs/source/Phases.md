# Phases.md
## Implementation Roadmap — Dual-Layer GNN Fake News Detection System

**Status:** Draft for review.
**Depends on:** PRD.md (Approved), Architecture.md (Approved), Rules.md (pending approval alongside this document).

Each phase has a concrete exit gate. A phase is not "done enough" — it either passes its gate or it isn't complete. Phases are ordered so nothing is built on top of an unverified assumption from an earlier phase.

---

## Phase 0 — Foundations
**Goal:** the skeleton exists, deployable, before any real feature is built on it.

- Repo structure matching Architecture.md §2 modules (Auth, Analysis Orchestration, Shared Preprocessing, ML Inference, Graph Processor, LLM Adapter) as real (empty-but-real) Python packages — no ghost folders per Rules.md §1.
- FastAPI app skeleton, PostgreSQL + Redis provisioned (dev environment), base schema from Architecture.md §4 migrated.
- CI pipeline running (lint, type-check, empty test suite passing) on push.
- Netlify + Render environments stood up, talking to each other over HTTPS with CORS configured per Architecture.md §8.

**Exit gate:** an empty "hello" request round-trips frontend → backend → DB → response, deployed, over HTTPS, in CI.

---

## Phase 1 — Authentication & Accounts
**Goal:** PRD §4.1 fully implemented and independently testable, before anything is gated behind it.

- Signup, login, logout, password reset, account deletion endpoints.
- Argon2id hashing, live password-strength UI, server-managed sessions (secure/HttpOnly/SameSite cookies), remember-device.
- Failed-login throttling (5 attempts / ~20 min), generic enumeration-safe responses on signup/reset.
- RBAC roles present in schema and enforced at the API layer (even though only `user`/`admin` are meaningfully exercised yet).

**Exit gate:** full E2E path signup → login → logout → password reset → account deletion passes (Rules.md §5); unit + integration tests for Auth module pass; no plaintext password ever appears in logs (manually verified once, then covered by a test that scans log output in CI).

---

## Phase 2 — Shared Preprocessing (offline + online entry points)
**Goal:** one canonical preprocessing codebase exists before either the research pipeline or the live submission flow depends on it, preventing the drift Rules.md §2 warns against.

- Content extraction/cleaning/normalization logic, with the two entry points (offline dataset, online submission) sharing the same core functions.
- `content_hash` canonicalization implemented exactly as specified in Architecture.md §4 (post-normalization text, input_type-independent).
- URL fetch + extraction, with SSRF protection (Architecture.md §6.7), retry-then-fallback error handling (PRD §4.3).
- File upload handling (.txt/.pdf): MIME/size/structure validation before parsing (Rules.md §6).

**Exit gate:** identical canonical output for (a) a pasted article, (b) the same article fetched by URL, (c) the same article uploaded as .txt — verified by a test asserting equal `content_hash` across all three inputs; malformed/unfetchable URL and malformed file cases each produce the correct user-facing fallback, not a silent failure.

---

## Phase 3 — Research Pipeline: Dataset, Baselines, Dual-Layer GNN
**Goal:** the model that Phase 4 will serve actually exists, trained and evaluated, in the research environment (Architecture.md §9) — entirely separate from production code.

- Dataset acquisition/licensing verification (FakeNewsNet candidate — confirm per PRD §6/Architecture §12 before locking).
- Baselines implemented: TF-IDF+LR, TF-IDF+RF, Text-Encoder+MLP (Batch J).
- Dual-layer GNN implemented per the locked architecture (Content Encoder → Propagation GNN + Interaction GNN → Fusion → Classification Head), using the compact pretrained text encoder (Batch I).
- Cross-domain zero-shot evaluation (PolitiFact↔GossipCop, Batch L), full metric suite (Batch K: Accuracy/Precision/Recall/F1/ROC-AUC/PR-AUC/Specificity/confusion matrix, per-domain and aggregate).
- Calibration assessment (reliability diagram, Brier score, temperature scaling if needed) — this determines whether `is_calibrated_prob` can ever be `true` for this model version.
- Confidence-band thresholds fixed from validation data (Batch K), not tuned to flatter results.
- Ablation study (LR/RF/MLP/Content+Propagation/Content+Interaction/Full model) to demonstrate the interaction layer's contribution.
- Early-detection robustness curve (fraction-of-observed-propagation, Batch M) — research artifact only, not wired to any product feature.
- One-command reproduction script (`experiments/run_experiment.py --config ...`) regenerating all of the above (Batch T).
- Model artifact packaged per Architecture.md §9: checkpoint + preprocessing/model/encoder config + `model_version` + `dataset_version` + git commit + seed.

**Exit gate:** `run_experiment.py` reproduces reported metrics from a clean checkout; a versioned model artifact exists with every field Architecture.md §9 requires; calibration verdict (calibrated or not) is documented and becomes the initial value of `is_calibrated_prob` for this model version.

---

## Phase 4 — ML Inference & Graph Processing (production modules)
**Goal:** the Phase 3 artifact is servable in production, behind the module boundary Architecture.md §2 defines.

- ML Inference module: loads the exact `model_version` artifact (no implicit "latest," per Rules.md §4), runs the full forward pass, returns verdict + raw score + attribution data.
- Content-only fallback path: graceful degradation when propagation/interaction data is unavailable (PRD §4.3), with `propagation_available`/`interaction_available` flags set honestly.
- Graph Processor module: server-side filtering/ranking into a compact representative subset (Architecture.md §6, no server-side layout computation per Rules.md §2).
- Attribution honesty constraint enforced in code: attention/node/edge scores only surfaced where the actual architecture produces them (PRD §4.5 revision 6) — no fabricated values to fill UI fields.

**Exit gate:** given a Phase 3 model artifact and a test article, the module returns a correctly-shaped `PredictionResult` (verdict, score, confidence band via the fixed thresholds, attribution data, graph subset) in isolation, without the API or frontend involved — proving the clean interface Architecture.md §2/§11 relies on for future extraction.

---

## Phase 5 — Analysis Orchestration & Async Pipeline
**Goal:** PRD §4.3/§4.4 end-to-end — submission through to a stored result — wired together for the first time.

- `POST /analyses` → job enqueue → status polling → result endpoints (Architecture.md §5), using the staged progress reporting from Architecture.md §6.3.
- Duplicate detection/reuse against the composite UNIQUE constraint (Architecture.md §4/§6.2), referencing `analyses.id` only (Rules.md §2).
- Visibility-promotion policy (Architecture.md §6.1) implemented as its own testable function — private-by-default, explicit rule for shared eligibility, conservative on ambiguity.
- `analysis_references` creation on both fresh analyses and reused-duplicate cases.
- Redis-backed rate limiting / concurrency limits (Architecture.md §6.6) enforced server-side.
- (SHOULD) Analysis cancellation endpoint (PRD §4.4 revision 8).

**Exit gate:** submitting the same article twice (once as pasted text, once by URL) produces one `analyses` row and two private `analysis_references`; submitting it a third time after bumping `preprocessing_version` in a test produces a second `analyses` row — proving the versioned-identity rule from Rules.md §4 actually holds in the running system.

---

## Phase 6 — LLM Explanation Layer
**Goal:** PRD §4.5/§Batch G wired in as a strictly downstream, optional-for-availability stage.

- LLM Adapter: structured-evidence request → Gemini Flash → schema-validated structured response → reject/regenerate on violation (Architecture.md §5).
- Explanation reuse tied to the same version tuple as analysis reuse (Architecture.md §6.4) — never regenerated for a compatible cached result.
- Async, non-blocking: prediction result is servable and displayed with "Generating explanation..." while pending, "Explanation unavailable — Retry" (rate-limited retry) on failure (PRD §4.5).
- Token/length/concurrency budget enforcement (Architecture.md §6.6).
- Structural check (Rules.md §1 Rule #5): automated test asserting no code path in the LLM Adapter writes to `analyses.verdict` or `analyses.raw_score`.

**Exit gate:** killing the LLM API mid-request (simulated) still leaves a complete, correct prediction result visible to the user; a duplicate-analysis request never triggers a second LLM call; the structural boundary test from Rules.md §1 passes in CI.

---

## Phase 7 — Frontend: Dashboard, Analyze/Search, Results, Graph
**Goal:** PRD §4.2/§4.6/§4.7 — the actual product surface.

- Three-pane dashboard, all 8 nav sections real and functional (PRD §4.2).
- Unified Analyze flow (text/URL/file) with live status polling.
- Search covering private history + permitted shared analyses only (PRD §4.7).
- Result view: structured explanation layout, confidence band + evidence-availability combined display ("High model confidence · Limited evidence" pattern), two-level (standard/deep-dive) evidence.
- Combined graph visualization with Propagation/Interaction/Both toggles, client-side layout on server-filtered data (Architecture.md §7), explicit "layer unavailable" states.
- Empty/first-use states, light/dark theme, WCAG AA basics (Architecture.md §7).

**Exit gate:** full E2E suite (Architecture.md §10) passes: signup → login → submit (each input type) → progress → result → graph interaction → history → logout.

---

## Phase 8 — Admin/Research Views & Metadata
**Goal:** PRD §4.5's RBAC-gated transparency layer.

- Regular-user result metadata (timestamp, model/version, input mode, data-layer availability) — already present from Phase 4-7; this phase adds the admin/research-only deeper metadata views and endpoints (Architecture.md §5 `/admin`, `/research` routes).
- Aggregate evaluation-summary endpoint surfacing Phase 3 metrics without exposing raw research artifacts.

**Exit gate:** a `user`-role account gets 403 on admin/research endpoints; an `admin`-role account sees the deeper metadata correctly sourced from the model artifact's recorded versions.

---

## Phase 9 — Hardening & Launch Readiness
**Goal:** the non-functional requirements (PRD §5, Architecture §8) are verified, not assumed.

- Full security pass: CORS, CSP/HSTS/security headers, secrets audit, SSRF test cases, file-upload attack cases (decompression bombs, malformed PDFs, oversized uploads).
- Load/rate-limit verification under simulated moderate concurrent usage.
- Account-deletion correctness re-verified against Architecture.md §6.5 with real data (private analyses gone, shared analyses' references gone, `analyses` rows for shared content intact and never exposed as belonging to the deleted user).
- CI/CD deploy pipeline exercised end-to-end (GitHub Actions → Render/Netlify).
- Final documentation-code consistency check (Rules.md §7): any drift between what's built and PRD.md/Architecture.md is resolved before launch, one direction or the other.

**Exit gate:** all four testing levels (Architecture.md §10) green in CI; a dry-run production deploy succeeds; sign-off checklist against PRD.md Sections 4-6 completed item by item.

---

## Dependency Summary

```
Phase 0 (foundations)
   ↓
Phase 1 (auth) ──────────────┐
   ↓                         │
Phase 2 (shared preprocessing)│
   ↓                         │
Phase 3 (research: dataset → model artifact)   [can run parallel to 1/2 after Phase 0]
   ↓                         │
Phase 4 (ML inference + graph, serving Phase 3's artifact)
   ↓                         │
Phase 5 (analysis orchestration, needs 1+2+4)◄─┘
   ↓
Phase 6 (LLM explanation, needs 5)
   ↓
Phase 7 (frontend, needs 5+6)
   ↓
Phase 8 (admin/research views, needs 7)
   ↓
Phase 9 (hardening & launch)
```

Phase 3 (research pipeline) can proceed in parallel with Phases 1-2 once Phase 0 is done — it has no dependency on Auth or the live API. This is deliberate: the research contribution (the actual academic work) doesn't need to wait on product plumbing.

---

## Approval

Pending review.
