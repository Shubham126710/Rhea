# Architecture.md
## Dual-Layer GNN Fake News Detection — System Architecture

**Status:** Approved — analysis_id/composite-key refinement and content_hash canonicalization definition incorporated. Implementation (Phases.md / Rules.md) may now begin.
**Depends on:** PRD.md (Approved). This document specifies *how* the requirements in PRD.md are implemented — technology choices, service boundaries, schemas, and infrastructure.

---

## 1. System Overview

A modular monolith backend serving a decoupled frontend, backed by a relational database and a cache/rate-limit layer, with ML inference and LLM explanation as internal modules of the same backend service (not separate microservices) for v1.

```
                 ┌─────────────────┐
                 │  Netlify (SPA)  │
                 └────────┬────────┘
                          │ HTTPS, REST /api/v1
                          ▼
                 ┌─────────────────────────────────────┐
                 │         Backend API (Render)         │
                 │  ┌─────────┐ ┌──────────────────┐    │
                 │  │  Auth   │ │ Analysis          │    │
                 │  │ /RBAC   │ │ Orchestration     │    │
                 │  └─────────┘ └──────────────────┘    │
                 │  ┌─────────┐ ┌──────────────────┐    │
                 │  │ Shared  │ │ ML Inference      │    │
                 │  │Preproc. │ │ (Text+Graph GNN)  │    │
                 │  └─────────┘ └──────────────────┘    │
                 │  ┌─────────┐ ┌──────────────────┐    │
                 │  │ Graph   │ │ LLM Adapter       │    │
                 │  │Processor│ │ (Gemini Flash)    │    │
                 │  └─────────┘ └──────────────────┘    │
                 └───────┬───────────────────┬──────────┘
                         ▼                   ▼
                 ┌───────────────┐   ┌───────────────┐
                 │  PostgreSQL   │   │     Redis      │
                 │ (system of    │   │ (cache, rate   │
                 │   record)     │   │  limit, jobs)  │
                 └───────────────┘   └───────────────┘

  Separate, offline: Research environment (datasets/, experiments/,
  model checkpoints/, evaluation artifacts/) — not the production DB.
```

**Why a modular monolith, not microservices:** PRD scope is a single moderate-traffic public deployment for an FYP. Splitting Auth/Analysis/ML/LLM/Graph into separate services now would add network hops, deployment surfaces, and failure modes with no corresponding requirement. Internal module boundaries (below) keep the option to extract a service later — most likely ML inference, if it becomes the throughput bottleneck — without a rewrite.

---

## 2. Backend Modules

| Module | Responsibility |
|---|---|
| **Auth** | Signup, login, session issuance/validation, password reset, account deletion, RBAC role checks |
| **Analysis Orchestration** | Owns the async analysis lifecycle: accept submission → dispatch to preprocessing/ML/graph/LLM → persist result → serve status/result |
| **Shared Preprocessing** | Single codebase, two entry points: offline (training data) and online (live submissions). Content extraction, cleaning, tokenization/encoding prep |
| **ML Inference** | Loads a versioned model artifact; runs text encoder → propagation GNN → interaction GNN → fusion → classification head; returns verdict, raw score, attribution data |
| **Graph Processor** | Server-side filtering/ranking of the full graph into a compact, representative subset for transmission; never computes visual layout (client does that) |
| **LLM Adapter** | Provider-abstracted interface; builds structured-evidence payload, calls Gemini Flash, validates response against schema, rejects/regenerates on violation |

Each module is a Python package with a defined interface; Analysis Orchestration is the only module allowed to call the others directly, preventing tangled cross-module dependencies.

---

## 3. Technology Stack

| Concern | Choice | Rationale |
|---|---|---|
| Backend language/framework | Python (FastAPI) | Same language as the ML pipeline; avoids a second stack for a thin API layer; async-native, fits the polling/status endpoints |
| Frontend | React SPA, deployed to Netlify | Per PRD; three-pane workspace, client-side graph rendering |
| Database | PostgreSQL | Per locked Batch N decision; relational fits users/sessions/analyses/permissions well; `pgvector` extension available later if a genuine retrieval need emerges (not used now) |
| Cache / rate limiting / job coordination | Redis | Session-adjacent short-window state, rate-limit counters, in-flight/duplicate-request collapsing |
| ML framework | PyTorch | Standard for GNN implementations (PyTorch Geometric) |
| Text encoder | Pretrained compact sentence/document transformer (e.g., a lightweight `sentence-transformers` model) | Locked Batch I decision: no training-from-scratch, no full LLM fine-tuning |
| LLM provider | Google Gemini API (Flash-class), behind an adapter interface | Locked Batch G decision; Grok as a documented alternative, not wired as primary |
| Backend hosting | Render | Locked Batch R decision |
| Frontend hosting | Netlify | Locked Batch R decision |
| CI/CD | GitHub Actions: test → build → deploy on push | Locked Batch R decision |

---

## 4. Database Schema (PostgreSQL)

Core tables only; exact column types/constraints are implementation detail, but the shape below is binding.

```sql
users (
  id                UUID PRIMARY KEY,
  email             CITEXT UNIQUE NOT NULL,
  display_name      TEXT NOT NULL,
  password_hash     TEXT NOT NULL,        -- Argon2id
  role              TEXT NOT NULL DEFAULT 'user',  -- 'user' | 'admin' | 'research'
  email_verified_at TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at        TIMESTAMPTZ           -- soft-delete marker; see §6.5
)

sessions (
  id            UUID PRIMARY KEY,
  user_id       UUID REFERENCES users(id) ON DELETE CASCADE,
  session_token_hash TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at    TIMESTAMPTZ NOT NULL,
  remember_device BOOLEAN NOT NULL DEFAULT false,
  revoked_at    TIMESTAMPTZ
)

password_reset_tokens (
  id          UUID PRIMARY KEY,
  user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
  token_hash  TEXT NOT NULL,
  expires_at  TIMESTAMPTZ NOT NULL,
  used_at     TIMESTAMPTZ
)

analyses (                                -- the reusable computational artifact
  id                    UUID PRIMARY KEY,  -- generated analysis_id; all other tables/modules reference this, never the composite tuple
  content_hash          TEXT NOT NULL,     -- normalized content hash, indexed
  input_type            TEXT NOT NULL,     -- 'text' | 'url' | 'file'
  source_url            TEXT,
  title                 TEXT,
  content_reference     TEXT NOT NULL,     -- pointer to stored/normalized content
  verdict               TEXT NOT NULL,     -- 'fake' | 'real'
  raw_score             NUMERIC,
  confidence_band       TEXT NOT NULL,     -- 'high' | 'moderate' | 'low'
  is_calibrated_prob    BOOLEAN NOT NULL DEFAULT false,
  model_version         TEXT NOT NULL,
  dataset_version       TEXT,
  preprocessing_version TEXT NOT NULL,
  graph_construction_version TEXT NOT NULL,
  calibration_version   TEXT NOT NULL,
  evidence              JSONB NOT NULL,    -- structured evidence passed to the LLM
  explanation           JSONB,             -- validated structured explanation (nullable while pending)
  graph_reference       TEXT,              -- pointer to filtered graph payload
  propagation_available BOOLEAN NOT NULL DEFAULT false,
  interaction_available BOOLEAN NOT NULL DEFAULT false,
  processing_status     TEXT NOT NULL,     -- 'pending' | 'processing' | 'complete' | 'failed'
  visibility            TEXT NOT NULL DEFAULT 'private',  -- 'private' | 'shared'
  metadata              JSONB NOT NULL DEFAULT '{}',
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE (content_hash, model_version, preprocessing_version,
          graph_construction_version, calibration_version)
  -- this composite is the deduplication/identity check: "have we already computed
  -- this exact compatible analysis?" It is NOT the primary key — id is, and every
  -- other table/module (analysis_references, LLM explanation lookups, graph/result
  -- fetches, history) references analyses.id, never the composite tuple directly.
)
-- What gets hashed into content_hash (must be exact, not "the general idea"):
-- the FULLY EXTRACTED AND NORMALIZED TEXT after the shared preprocessing pipeline
-- has run (§6.2 below) — i.e. the same canonical text that is actually fed to the
-- text encoder. This means: a URL and a hand-pasted copy of the same article
-- normalize to the same hash (same analyzed content -> correct reuse), while a
-- .txt upload and a .pdf upload of the same article also normalize to the same
-- hash, PROVIDED extraction produces the same canonical text from both. input_type
-- is stored for display/audit purposes but is deliberately NOT part of the
-- uniqueness identity, because it describes how the content arrived, not what was
-- analyzed. If two submissions with different input_type ever produce different
-- extracted text for what a human would call "the same article" (e.g. a PDF with
-- OCR noise vs. a clean URL fetch), they are correctly treated as different
-- analyses under this rule — content_hash reflects the actual analyzed bytes, not
-- the source's nominal identity.

analysis_references (                     -- private relationship: user ↔ analysis
  id           UUID PRIMARY KEY,
  user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
  analysis_id  UUID REFERENCES analyses(id) ON DELETE RESTRICT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
  -- this table is what a user's "History" queries; it is always private to the user,
  -- regardless of the referenced analysis's visibility
)

rate_limit_events (                        -- optional Postgres backstop; Redis is primary
  id        UUID PRIMARY KEY,
  user_id   UUID REFERENCES users(id),
  kind      TEXT NOT NULL,
  window_start TIMESTAMPTZ NOT NULL,
  count     INT NOT NULL
)
```

**Analysis result vs. user history** (PRD §4.8): `analyses` is the shared computational artifact; `analysis_references` is the private, per-user pointer to it. Search and History query `analysis_references` joined to `analyses`, filtered by `visibility = 'shared' OR analyses.id IN (user's own analysis_references)`. This directly implements the PRD's separation and makes account deletion mechanical (§6.5 below).

Research data (datasets, experiments, checkpoints, evaluation artifacts) lives outside this schema entirely, in the separate research environment described in §9.

---

## 5. API Design

Base path: `/api/v1/`. REST, polling-based async flow (no WebSockets in v1; SSE is a documented future option, not built now).

```
POST   /api/v1/auth/signup
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/password-reset/request
POST   /api/v1/auth/password-reset/confirm
DELETE /api/v1/auth/account

POST   /api/v1/analyses                 → 202 Accepted, { analysis_reference_id, status: "pending" }
GET    /api/v1/analyses/{ref_id}/status → { status: "processing", stage: "building_graph", ... }
GET    /api/v1/analyses/{ref_id}        → full result (verdict, confidence, evidence, graph_summary, explanation, metadata)
DELETE /api/v1/analyses/{ref_id}        → (SHOULD) cancel if still processing, per PRD §4.4 cancellation requirement

GET    /api/v1/search?q=...             → user's private history + permitted shared analyses only
GET    /api/v1/history                  → user's analysis_references, paginated

GET    /api/v1/admin/analyses/{id}/metadata   → RBAC-gated: dataset_version, model config, eval info
GET    /api/v1/research/evaluation-summary    → RBAC-gated: aggregate metrics, not raw research artifacts
```

Every response referencing an `analysis` resolves through the user's own `analysis_reference` — a user never receives another user's reference ID, and the shared `analyses.id` is never directly exposed as a browsable/enumerable endpoint. This is the concrete mechanism for PRD §4.8's "no access to another user's private metadata."

---

## 6. Cross-Cutting Mechanisms

### 6.1 Visibility enforcement (PRD open item, resolved here)
A submitted analysis is `visibility = 'private'` by default. It is promoted to `'shared'` only when a backend-side rule evaluates true at *write time* — before the row is ever committed as shared — based on:
- input_type is `'url'` or `'text'` sourced from a publicly-fetchable article (not an uploaded file — files are never eligible, per PRD §4.3/4.8), and
- content extraction did not detect user-specific/personal markers (this check is deliberately conservative: default to private on ambiguity).

This rule lives in Analysis Orchestration, runs once per new (non-duplicate) analysis, and is never re-evaluated retroactively — an analysis's visibility does not change after creation except via the anonymization path in §6.5.

### 6.2 Duplicate detection & reuse
Content is normalized (whitespace/casing/boilerplate-stripped) via the shared preprocessing pipeline and hashed into `content_hash` — see the canonicalization note under §4's `analyses` table for exactly what is hashed. A new submission first checks `analyses` for a row matching the `(content_hash, model_version, preprocessing_version, graph_construction_version, calibration_version)` unique constraint. On match: create a new private `analysis_references` row pointing at the existing row's `analyses.id` (the actual primary key — the composite tuple is used only for the lookup, never stored or referenced elsewhere as an identity); skip the pipeline entirely. On no match: run the full pipeline and insert a new `analyses` row, generating a fresh `id`. This implements PRD §4.3's revised condition precisely — any versioned stage changing invalidates reuse, not just the model.

### 6.3 Async processing
`POST /analyses` enqueues a job (Redis-backed queue, e.g. RQ or Celery+Redis) and returns immediately. Status endpoint reads job/analysis state. Stages reported: `extracting_content → preparing_features → building_graph → running_model → generating_explanation → finalizing → complete`. Processing continues if the client disconnects; result lands in `analyses`/`analysis_references` regardless.

### 6.4 LLM explanation reuse
Explanation generation is keyed to the same composite version tuple as duplicate detection (§6.2) — if a compatible `analyses` row already has a non-null `explanation`, it's served as-is. A version change on any prediction-relevant stage invalidates both the analysis and its explanation together, never the explanation alone.

### 6.5 Account deletion
On delete: user's `sessions` and `password_reset_tokens` cascade-delete (FK ON DELETE CASCADE). For `analysis_references` owned by the user: rows pointing to `visibility = 'private'` analyses are deleted, and the now-orphaned private `analyses` rows are deleted too (nothing else can reference a private analysis). Rows pointing to `visibility = 'shared'` analyses: the `analysis_references` row is deleted, but the `analyses` row itself is untouched — it was never linked to the user's identity in the first place beyond that reference, so no anonymization step is even needed on the `analyses` table itself. `users.deleted_at` is set (soft delete) to satisfy any audit/session-invalidation timing needs before hard deletion completes.

**Phase 1 actual implementation, reconciled here per Rules.md §7 (audit finding, 2026-08-28):** Phase 1 has no `analyses`/`analysis_references` tables populated yet (those arrive with Analysis Orchestration), so the cascade behavior above is not yet meaningfully exercisable. What Phase 1 actually does on delete: sets `users.deleted_at` (soft delete, as this section already specified), explicitly revokes (not deletes) all `sessions` rows for the user, and explicitly deletes any outstanding `password_reset_tokens` rows for the user. The user row itself is never hard-deleted in Phase 1 — there is no scheduled job or manual process yet that performs the "hard deletion completes" step this section refers to, since no job-scheduling infrastructure exists before Phase 5/6. `confirm_password_reset` independently checks `deleted_at` before honoring any token, so a deleted account cannot be reactivated via an outstanding reset token even before the explicit token cleanup was added. The FK-cascade hard-delete design above remains the intended eventual behavior once account-deletion becomes a hard delete in a later phase; this note exists so the gap between this document and Phase 1's code is explicit rather than silent.

### 6.5a Login/signup throttling (Phase 1, distinct from §6.6)
Failed-login throttling (PRD Batch B: 5 attempts / ~20 minutes) is implemented against PostgreSQL's `rate_limit_events` table, not Redis, keyed by a SHA-256 hash of the attempted email (not `user_id`, so throttling behaves identically whether or not the account exists — this keeps the mechanism itself from becoming an enumeration oracle). This is intentionally separate from §6.6's Redis-backed sliding-window limiters, which govern analysis submission and LLM cost control and require Redis wiring that doesn't exist before Phase 5/6. Whether login throttling should eventually move to Redis once it's wired in for other purposes, or remain a permanently separate Postgres-based mechanism, is an open question, not decided by this note.

### 6.6 Rate limiting & cost control
Redis-backed sliding-window counters per `user_id` for: analyses submitted per hour, LLM tokens consumed per day, concurrent in-flight analyses. Enforced in Analysis Orchestration and LLM Adapter, not the frontend. Limits are configuration, not hardcoded, so they can be tuned without a deploy.

### 6.7 SSRF protection for URL fetching
URL fetch requests are validated against a denylist of private/internal IP ranges (RFC1918, loopback, link-local) before the backend makes the request; redirects are re-validated at each hop, not just the original URL.

---

## 7. Frontend Architecture

- React SPA, three-pane workspace layout (history / analysis workspace / contextual controls) per PRD §4.2.
- Graph visualization: receives the server-filtered graph payload (§4.6) and performs layout/rendering client-side (e.g., a force-directed or canvas-based graph library appropriate for the expected node/edge counts); server never computes screen coordinates.
- State: analysis status polling on a short interval while `status != complete`, backing off or stopping on `failed`/`complete`.
- Auth state via httpOnly session cookie; frontend never handles raw credentials beyond the login/signup form submission itself.
- Light/dark theme, WCAG AA basics (focus states, semantic controls, non-tooltip-only critical info, accessible graph summary alternative) built in from the start, not retrofitted.

---

## 8. Security Implementation

- Argon2id password hashing; generic responses on signup/reset regardless of email existence (PRD §4.1).
- CORS restricted to the Netlify production origin + localhost dev origins; no wildcard with credentials.
- All file uploads: MIME-type validated, size-capped, PDF structure validated, rejected on malformation; uploaded HTML/JS content is never executed, only parsed as inert text/data.
- Secrets (DB credentials, Gemini API key, session signing key) via environment variables — `.env` locally (gitignored), Render's environment variable store in production. Never shipped to the frontend bundle.
- HTTPS enforced, secure/HttpOnly/SameSite cookies, CSP, HSTS, X-Content-Type-Options, Referrer-Policy, frame-ancestors protection.

---

## 9. Research Environment (Separate from Production)

```
research/
  datasets/            # per source license terms; not copied into production DB
  experiments/
    configs/           # baseline_lr.yaml, baseline_rf.yaml, text_mlp.yaml, dual_gnn.yaml, cross_domain.yaml
    run_experiment.py  # one-command reproduction entry point
  model_checkpoints/   # versioned: dualgnn-v1.0.0 etc., each with config + git commit + seed
  evaluation/
    metrics/
    predictions/
    figures/           # reliability diagrams, calibration plots, confusion matrices
```

A promoted model artifact (checkpoint + all versioned config, per PRD §6) is the only thing that crosses from this environment into the production ML Inference module. Raw datasets, intermediate experiment artifacts, and baseline models never enter production.

---

## 10. Testing Architecture

| Level | Scope | Tooling |
|---|---|---|
| Unit | preprocessing, graph construction, auth utilities, confidence-band calculation, duplicate hashing, evidence mapping | pytest |
| Integration | API endpoints, DB, Redis, auth flow, async analysis lifecycle, LLM adapter fallback path | pytest + test DB/Redis instances |
| ML integrity | no train/test leakage, label validation, feature shape checks, graph integrity, missing-data fallback behavior, reproducible seeding, model-artifact loading | pytest, run against research checkpoints |
| E2E | signup → login → submit analysis → progress → result → history → logout | Playwright |

CI (GitHub Actions): lint + type-check + unit + integration on every push; E2E on merge to main before deploy.

---

## 11. Deployment Topology

- **Environments:** development, production. No mandatory staging (PRD scope).
- **Frontend:** Netlify, auto-deploy from main.
- **Backend:** Render, single service running all backend modules (§2); PostgreSQL and Redis as managed Render add-ons or equivalent.
- **CI/CD:** GitHub Actions — test → build → deploy on push to main.
- **Extraction path (not built now, kept open):** if ML inference becomes the throughput bottleneck, it can be pulled into its own Render service behind an internal API, since Analysis Orchestration already treats ML Inference as a module with a defined interface rather than inline code.

---

## 12. Open Items for Implementation Phase

- Exact denylist/allowlist rules for the visibility-promotion check (§6.1) — this is a tunable policy, not a fixed algorithm, and may need adjustment once real submissions are observed.
- Exact Redis rate-limit thresholds (requests/hour, token budget/day) — set conservatively at launch, tunable via config.
- Choice of specific client-side graph rendering library, chosen during implementation against actual expected node/edge counts from real data.
- Final research dataset confirmation (FakeNewsNet candidate) — licensing/completeness verification per PRD §6, tracked in the research environment, not this document.

---

## 13. Approval

Reviewed and approved, with one refinement incorporated: `analysis_id` (UUID) is the actual primary key on `analyses`; the five-value version tuple is a UNIQUE constraint used only for deduplication lookups, never stored or referenced as an identity elsewhere (§4, §6.2). The exact canonicalization behind `content_hash` — fully extracted and normalized text, post-preprocessing, regardless of original input_type — is now specified explicitly to prevent ambiguity between differently-sourced submissions of "the same" content. Implementation planning (Phases.md / Rules.md) may now begin.
