# PROPAGATE — MASTER BUILD SPECIFICATION

> **Release candidate after final consolidation audit.**
>
> This document is the operational implementation specification. It is not a replacement for the approved source documents; it consolidates them for implementation and preserves unresolved items as explicit open decisions.

**Document:** `PROPAGATE_MASTER_BUILD.md`  
**Purpose:** Consolidated implementation authority for the Propagate VS Code/Claude build.  
**Status:** Pre-implementation consolidation.  
**Source documents:** `PRD.md`, `Architecture.md`, `Phases.md`, `Rules.md`, plus the frozen Stitch reference package.  
**Implementation state:** No production application has been built yet.

---

# 0. EXECUTION DIRECTIVE

You are implementing an already-designed system.

Do **not** treat the source material as a loose collection of ideas from which to redesign the product. The product direction, system architecture, engineering constraints, and implementation sequence have already been established.

Your job is to:

1. implement the system exactly within the approved product and architecture boundaries;
2. preserve the documented terminology and contracts;
3. implement work phase-by-phase;
4. validate each phase against its explicit exit gate;
5. stop at every hard exit gate;
6. never silently invent requirements, architecture, schema, product behavior, or research methodology;
7. raise a decision when implementation exposes a genuine gap or contradiction rather than resolving it through unilateral redesign.

The frozen Stitch package is a **visual/UX reference only**. Do not copy its HTML into production, do not treat its generated implementation as architecture, and do not reopen Stitch for design amendments.

The implementation agent is not the architect.

---

# 1. AUTHORITY AND PRECEDENCE

The following hierarchy governs interpretation:

## 1.1 Product truth — PRD

`PRD.md` defines **what Propagate must do**: product scope, users, functional requirements, non-functional requirements, research-facing constraints, and non-goals.

The PRD is approved.

## 1.2 System truth — Architecture

`Architecture.md` defines **how the approved product is structured**: modules, technology choices, database shape, API design, cross-cutting mechanisms, frontend architecture, security implementation, research environment, testing architecture, and deployment topology.

Architecture is approved.

## 1.3 Implementation discipline — Rules

`Rules.md` defines **how code is allowed to be written**. It does not introduce product or architectural decisions.

Where Rules appears to introduce a new product or architecture decision, treat that as a conflict requiring review rather than as an automatic requirement.

## 1.4 Execution control — Phases

`Phases.md` defines **when and in what sequence the system is implemented**, including explicit exit gates.

No phase is complete merely because its code exists. Its exit gate must pass.

## 1.5 Visual/UX reference — Stitch

Stitch defines **visual and experiential reference**, not product authority, architecture, schema, API behavior, or implementation source.

If Stitch conflicts with PRD, Architecture, Rules, or Phases, the governing documents win.

## 1.6 This Master Build Specification

This document consolidates the above into an operational instruction for the implementation agent.

## 1.7 Locked invariants

The following invariants are implementation locks. They are not suggestions and must not be reinterpreted by an implementation agent:

1. `analyses.id` is the sole cross-table analysis identity.
2. The composite version tuple is a UNIQUE deduplication constraint, not an identity.
3. `content_hash` is derived from canonical normalized extracted content after shared preprocessing.
4. `input_type` is not part of content identity.
5. The GNN/ML inference layer determines the prediction; the LLM only explains structured evidence.
6. The LLM cannot modify the verdict or raw model score.
7. Analysis references are private user relationships to computational analyses.
8. Analyses are private by default.
9. Uploaded files are never promoted to the shared pool.
10. Missing graph/evidence data must never be fabricated.
11. Production loads an exact versioned model artifact; never an implicit “latest” artifact.
12. The frozen Stitch package is visual/UX reference only and is never a production source of code or architecture.
13. Implementation proceeds phase-by-phase and stops at each hard exit gate.
14. An unspecified requirement is not permission to invent a product, architecture, schema, or research decision.

If another section appears to conflict with one of these invariants, stop and resolve the conflict against the governing source documents before implementation.

It does not authorize silent changes to the approved PRD or Architecture.

If this document contains an accidental conflict with an approved source document, the approved source document wins and the inconsistency must be surfaced and corrected.

---

# 2. PROJECT IDENTITY

## 2.1 Product

**Propagate — Dual-Layer GNN Fake News Detection Research Demonstration Platform**

## 2.2 Product identities

Propagate has two coexisting identities:

1. A public-facing application where authenticated users submit or search content and receive a Fake/Real verdict, supporting evidence, a rendered dual-layer graph, and an LLM-grounded explanation.
2. A reproducible research pipeline covering training, baselines, ablations, cross-domain evaluation, and early-detection evaluation.

The research pipeline produces the model served by the application. It is not exposed as a training UI, baseline-comparison tool, or research dataset browser.

## 2.3 Product character

Propagate is an inference and demonstration platform, not a research experiment-control interface.

---

# 3. STITCH IS FROZEN — HARD PROHIBITION

The Stitch package is frozen.

The implementation agent must not:

- modify Stitch;
- regenerate Stitch screens;
- request a new Stitch design;
- treat Stitch-generated HTML/CSS as production source;
- infer backend/data behavior from visual artifacts;
- use Stitch to resolve conflicts with the approved specifications.

Stitch may only be consulted as a visual/UX reference.

# 4. LOCKED PRODUCT REQUIREMENTS

The following are binding product requirements derived from the approved PRD.

## 3.1 Accounts and authentication

- Public signup is available.
- Analysis submission requires authentication.
- Signup requires email, display name, and password only.
- No institutional fields at signup.
- No self-selected privileged role.
- Password strength is displayed live.
- Passwords use Argon2id or equivalent and are never stored in plaintext.
- Email verification is supported but does not block ordinary use; it may be required for sensitive operations.
- Sessions are server-managed using secure, HttpOnly, SameSite cookies.
- Explicit logout exists.
- Remember-device is supported.
- Password reset uses short-lived, single-use secure tokens.
- After five failed login attempts, login attempts are throttled for approximately twenty minutes.
- Users can delete their own account.
- Account deletion invalidates sessions.
- Signup and password-reset responses must not reveal whether an email is registered.

## 3.2 Workspace and navigation

Authenticated users receive a three-part workspace:

- history on the left;
- active analysis workspace in the center;
- contextual controls on the right.

The following eight sections are real, functional v1 sections:

1. Home
2. Analyze
3. Search
4. History
5. Model/Evidence
6. Profile
7. Help
8. Settings

No fake navigation or placeholder sections are permitted.

New accounts show an honest empty state. Do not insert fabricated/demo history into real accounts.

## 3.3 Analysis inputs

A single unified analysis flow accepts:

- pasted raw text;
- URL;
- `.txt` file;
- `.pdf` file.

URL extraction is server-side.

Extraction uncertainty must be communicated.

Retrieval failure must produce a useful fallback path rather than leaving the user stuck.

When propagation/interaction data is unavailable, use a content-only path and state the limitation explicitly. Never fabricate graph data.

Equivalent duplicate submissions reuse compatible computation.

A new analysis is required when prediction-relevant versions change.

## 3.4 Processing

Analysis is asynchronous.

The client must never present a frozen loading screen as the complete processing experience.

Processing continues if the user navigates away.

Defined stages include:

`extracting_content → preparing_features → building_graph → running_model → generating_explanation → finalizing → complete`

Cancellation is a SHOULD-level feature where technically feasible.

## 3.5 Results

The primary verdict is:

- Fake
- Real

Confidence is:

- High
- Moderate
- Low

Confidence bands must be derived from documented validation/calibration procedures, not arbitrary UI thresholds.

A raw numeric score is exposed only in an advanced view.

Call the score a **probability** only when the underlying model has been validated as calibrated. Otherwise call it a **model confidence score**.

Evidence availability modifies how confidence is communicated. For example:

> High model confidence · Limited evidence

Two explanation depths exist:

- Standard
- Deep Dive

Deep Dive may expose attribution/importance information only where the actual model architecture supports it.

Attribution is not causal proof.

The explanation structure is:

1. Verdict
2. Confidence
3. Why this result
4. Supporting signals
5. Graph insights, when available
6. Uncertainty/limitations
7. Optional Technical Deep Dive

The LLM may explain only evidence produced by the analysis pipeline.

Uncertainty and missing-data states must be visible.

Regular users see basic reproducibility metadata:

- timestamp;
- model/version;
- input mode;
- available data layers.

Admin/research roles may see deeper technical metadata.

## 3.6 Graph

The dual-layer graph is visible by default on results where meaningful graph information exists.

It combines:

- Propagation relationships
- Interaction relationships

Controls include:

- Propagation
- Interaction
- Both

The server filters/ranks a representative subset.

The client performs graph layout/rendering.

The system may expose more graph data up to "show all" when manageable.

Unavailable layers are explicitly labeled.

Never fabricate missing graph structure.

## 3.7 Search and history

History displays:

- title/snippet;
- verdict;
- date.

Search covers:

- the user's private history;
- explicitly shareable analyses.

It must never expose another user's private analyses or metadata.

## 3.8 Privacy and reuse

The computational result and the user's private relationship to that result are separate concepts.

`analyses` represents the computational artifact.

`analysis_references` represents the private user-to-analysis relationship.

Submitted content is private by default.

Only content satisfying the explicit backend sharing rule may enter the shared pool.

A duplicate match never promotes private content to shared.

Uploaded files never enter the shared pool.

When a user matches an existing shared analysis, the user receives a private reference to that shared result and no private data belonging to another user.

Compatible cached explanations may be reused.

Private analyses are removed with account deletion.

Legitimately shared computational resources survive deletion without user-identifying ownership linkage.

---

# 5. NON-GOALS — DO NOT BUILD

The following are explicitly outside v1:

- in-app training;
- baseline selection;
- experiment configuration for end users;
- leaderboard;
- user-vs-user comparison;
- personalization based on accuracy;
- mobile-optimized experience;
- microservice decomposition;
- distributed infrastructure beyond moderate public traffic needs;
- vector database;
- knowledge base;
- retrieval layer;
- Early Detection Mode for users;
- end-user domain labels such as GossipCop/PolitiFact resemblance;
- in-product baseline comparison;
- user accuracy scoring.

Do not create UI, routes, schema, or architecture for these unless the governing documents are explicitly changed and re-approved.

---

# 6. SYSTEM ARCHITECTURE

## 5.1 Topology

The v1 system is a **modular monolith backend with a decoupled React frontend**.

Production shape:

- React SPA → Netlify
- HTTPS REST `/api/v1`
- FastAPI backend → Render
- PostgreSQL → system of record
- Redis → cache, rate limiting, job coordination
- ML inference and LLM explanation remain internal modules of the backend
- Research environment remains separate from production

Do not split v1 into microservices.

## 5.2 Backend modules

The backend contains these real modules:

1. Auth
2. Analysis Orchestration
3. Shared Preprocessing
4. ML Inference
5. Graph Processor
6. LLM Adapter

Responsibilities:

### Auth

Signup, login, session issuance/validation, password reset, deletion, RBAC.

### Analysis Orchestration

Owns the analysis lifecycle and is the only module allowed to call the other modules directly.

### Shared Preprocessing

One codebase with offline and online entry points.

### ML Inference

Loads exact versioned model artifacts and returns prediction information.

### Graph Processor

Filters/ranks graph data for transmission.

It never computes screen layout.

### LLM Adapter

Receives structured evidence, calls Gemini Flash through an adapter, validates the structured response, and rejects/regenerates invalid responses.

## 5.3 Module boundary

Only Analysis Orchestration may directly call:

- Auth
- Shared Preprocessing
- ML Inference
- Graph Processor
- LLM Adapter

Do not bypass module boundaries.

---

# 7. TECHNOLOGY STACK

Binding architecture choices:

| Concern | Choice |
|---|---|
| Backend | Python + FastAPI |
| Frontend | React SPA |
| Frontend hosting | Netlify |
| Backend hosting | Render |
| Database | PostgreSQL |
| Cache/job/rate limit | Redis |
| ML | PyTorch / PyTorch Geometric |
| Text encoder | Compact pretrained sentence/document transformer |
| LLM | Google Gemini Flash-class through adapter |
| CI/CD | GitHub Actions |
| Testing | pytest + Playwright |

`pgvector` may exist as an available PostgreSQL extension but is not used for v1 retrieval.

Grok is a documented LLM alternative, not the primary wired provider.

---

# 8. DATA MODEL

## 7.1 Users

Core fields:

- UUID id
- unique CITEXT email
- display name
- Argon2id password hash
- role: `user | admin | research`
- email verification timestamp
- created timestamp
- deleted timestamp

Roles are system/admin assigned.

## 7.2 Sessions

Sessions contain:

- UUID id
- user_id
- session token hash
- created_at
- expires_at
- remember_device
- revoked_at

Raw session tokens are not stored.

## 7.3 Password reset tokens

Fields include:

- id
- user_id
- token_hash
- expires_at
- used_at

Tokens are short-lived and single-use.

## 7.4 Analyses

`analyses` is the reusable computational artifact.

Binding conceptual fields:

- `id` — UUID primary key
- `content_hash`
- `input_type`
- `source_url`
- `title`
- `content_reference`
- `verdict`
- `raw_score`
- `confidence_band`
- `is_calibrated_prob`
- `model_version`
- `dataset_version`
- `preprocessing_version`
- `graph_construction_version`
- `calibration_version`
- `evidence`
- `explanation`
- `graph_reference`
- `propagation_available`
- `interaction_available`
- `processing_status`
- `visibility`
- `metadata`
- timestamps

`processing_status`:

- pending
- processing
- complete
- failed

`visibility`:

- private
- shared

## 7.5 Analysis references

`analysis_references` is the private relationship:

- id
- user_id
- analysis_id
- created_at

History is queried through this relationship.

It is always private to the user even when the referenced analysis is shared.

## 7.6 Rate limit events

Optional PostgreSQL backstop:

- id
- user_id
- kind
- window_start
- count

Redis remains primary.

---

# 9. DEDUPLICATION AND CONTENT IDENTITY

This is a locked architectural rule.

## 8.1 Primary identity

`analyses.id` is the sole cross-table analysis identity.

It is the UUID primary key.

No other module or table may use the version tuple as an identity.

## 8.2 Deduplication key

The uniqueness check uses:

`content_hash + model_version + preprocessing_version + graph_construction_version + calibration_version`

This is a UNIQUE constraint, not a primary key.

## 8.3 content_hash

`content_hash` is calculated from:

> the fully extracted and normalized text after the shared preprocessing pipeline has run.

Therefore:

- pasted text;
- fetched URL;
- `.txt`;
- `.pdf`;

may resolve to the same canonical content and therefore the same hash if extraction produces the same canonical text.

`input_type` is not part of content identity.

The hash represents the actual analyzed canonical text, not nominal source identity.

## 8.4 Version invalidation

Any change to a prediction-relevant version invalidates compatible reuse.

Version dimensions:

- `model_version`
- `preprocessing_version`
- `graph_construction_version`
- `calibration_version`

Do not use an implicit "latest" model.

---

# 10. ML INFERENCE CONTRACT

## 9.1 Boundary

The ML system predicts.

The LLM explains.

The LLM must be structurally incapable of changing:

- verdict;
- raw score.

Any path allowing LLM output to influence classification is a severity-1 defect.

## 9.2 Model pipeline

The architecture is:

`Content Encoder → Propagation GNN + Interaction GNN → Fusion → Classification Head`

The text encoder is a compact pretrained sentence/document transformer.

## 9.3 Prediction result

The ML Inference module must expose a clean contract containing, as applicable:

- verdict;
- raw score;
- confidence band;
- attribution/importance signals actually produced by the model;
- graph information required by downstream graph processing;
- evidence information;
- version metadata.

The production data class/schema is binding to the approved Architecture/source contract. If the exact shape is not present in the implementation materials available to the agent, mark it as an OPEN DECISION and stop before inventing a new contract.

## 9.4 Content-only fallback

If propagation/interaction data does not exist:

- do not fabricate it;
- set availability flags honestly;
- produce the supported content-only result;
- communicate the limitation to the user.

## 9.5 Attribution honesty

Only expose:

- attention;
- node importance;
- edge importance;
- feature contributions;

when the implemented model genuinely produces the relevant signal.

Never fabricate attribution fields for UI completeness.

---

# 11. RESEARCH PIPELINE

Research is separate from the production application.

Research environment contains:

- datasets
- experiments
- model checkpoints
- evaluation artifacts

Production does not contain raw research datasets or intermediate research artifacts.

A promoted model artifact crosses the boundary.

The research plan includes:

- dataset acquisition/licensing verification;
- TF-IDF + Logistic Regression baseline;
- TF-IDF + Random Forest baseline;
- text encoder + MLP baseline;
- dual-layer GNN;
- cross-domain zero-shot evaluation;
- full metric suite;
- calibration assessment;
- confidence-band threshold determination;
- ablation study;
- early-detection robustness curve;
- one-command reproduction;
- versioned model artifact.

Early detection is a research artifact only.

The specific dataset remains subject to the licensing/completeness verification identified by the source documents.

Do not silently lock a dataset if the source documents leave it open.

---

# 12. GRAPH CONSTRUCTION AND PROCESSING

The graph pipeline must distinguish:

- propagation layer;
- interaction layer.

The Graph Processor is responsible for server-side:

- filtering;
- ranking;
- representative subset selection.

The server does **not** compute:

- x/y coordinates;
- screen positions;
- visual layout.

The React client performs layout/rendering.

The client receives only the graph data required for the visualization.

Large graphs must be reduced server-side before transmission.

---

# 13. VISIBILITY / SHARING LOGIC

## 12.1 Default

Every new analysis begins:

`visibility = private`

## 12.2 Shared eligibility

The current Architecture defines a conservative backend rule.

A submission may become shared only when:

- input is URL or text from a publicly fetchable article;
- it is not an uploaded file;
- extraction does not detect user-specific/personal markers.

Ambiguity defaults to private.

## 12.3 Timing

The visibility decision happens once for a new non-duplicate analysis at write time.

It is not repeatedly re-evaluated.

## 12.4 Uploaded files

Uploaded files are never eligible for the shared pool.

## 12.5 Tunability

The exact denylist/allowlist and visibility policy details are an implementation open item and must remain configurable/tunable.

Do not invent a more expansive sharing policy.

---

# 14. ASYNC ANALYSIS PIPELINE

Canonical lifecycle:

1. authenticated user submits content;
2. backend validates input;
3. content is extracted;
4. content is normalized;
5. canonical hash is produced;
6. compatible analysis is checked;
7. if compatible analysis exists, create a new private reference and reuse it;
8. otherwise enqueue analysis;
9. preprocessing/features are prepared;
10. graph is constructed;
11. ML prediction runs;
12. graph is filtered;
13. primary prediction is persisted;
14. optional LLM explanation is generated;
15. final state is persisted;
16. user receives the result through the reference they own.

Status stages:

`extracting_content`
`preparing_features`
`building_graph`
`running_model`
`generating_explanation`
`finalizing`
`complete`

The LLM stage must never block the primary prediction from being available.

---

# 15. LLM EXPLANATION CONTRACT

The LLM receives structured evidence produced by the analysis pipeline.

It does not independently determine:

- Fake/Real;
- model score;
- confidence;
- graph facts.

The adapter:

1. builds structured evidence payload;
2. calls Gemini Flash;
3. validates the structured response;
4. rejects/regenerates schema-invalid responses;
5. stores the explanation only after validation.

Explanation reuse follows the same compatible version tuple as analysis reuse.

If the LLM is unavailable:

- prediction remains available;
- UI reports explanation unavailable;
- retry is possible subject to rate limits.

The LLM adapter must not write to `analyses.verdict` or `analyses.raw_score`.

---

# 16. API CONTRACT

Base path:

`/api/v1/`

The v1 design is REST + polling.

No WebSockets.

SSE is a future option and is not built now.

## Authentication

- `POST /api/v1/auth/signup`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/password-reset/request`
- `POST /api/v1/auth/password-reset/confirm`
- `DELETE /api/v1/auth/account`

## Analysis

- `POST /api/v1/analyses`
- `GET /api/v1/analyses/{ref_id}/status`
- `GET /api/v1/analyses/{ref_id}`
- `DELETE /api/v1/analyses/{ref_id}` — SHOULD support cancellation while processing

Submission returns `202 Accepted` with an analysis reference and pending status.

## Search/history

- `GET /api/v1/search?q=...`
- `GET /api/v1/history`

Search is restricted to:

- the user's private history;
- permitted shared analyses.

## Admin/research

- `GET /api/v1/admin/analyses/{id}/metadata`
- `GET /api/v1/research/evaluation-summary`

These routes are RBAC gated.

## Reference security

User-facing analysis operations resolve through the user's private `analysis_reference`.

Do not expose a browsable/enumerable shared `analyses.id` endpoint.

---

# 17. AUTHENTICATION AND RBAC

Roles:

- `user`
- `admin`
- `research`

A user cannot self-select a privileged role.

RBAC is enforced at the API layer.

Authentication state is maintained through the server-managed session cookie.

The frontend must never store raw session credentials.

Account deletion must invalidate sessions and correctly remove private analysis relationships.

---

# 18. FRONTEND / UX ARCHITECTURE

## 17.1 Framework

React SPA.

## 17.2 Workspace

Three panes:

- History
- Analysis Workspace
- Contextual Controls

## 17.3 Navigation

All eight required sections are functional.

Do not create speculative component scaffolding for future features.

## 17.4 State

Server state such as:

- analysis status;
- analysis results;
- history;

must derive from backend/query/fetch state.

Do not duplicate backend truth into drifting ad hoc local state.

## 17.5 Graph

Client receives server-filtered graph data and performs layout/rendering.

## 17.6 Themes/accessibility

Build from the beginning:

- light/dark theme;
- visible focus states;
- semantic controls;
- keyboard navigation;
- sufficient contrast;
- accessible graph summary alternative;
- critical information not dependent on tooltips.

## 17.7 Stitch reference

The frozen Stitch package should be consulted for:

- visual language;
- screen composition;
- navigation feel;
- component appearance;
- empty/loading/result states;
- terminology where consistent with the approved product requirements.

It must not override product or architecture rules.

Do not copy Stitch HTML directly.

---

# 19. ERROR, EMPTY, LOADING, AND UNCERTAINTY STATES

These are first-class product states.

Required examples include:

## Authentication

- invalid credentials;
- throttled login;
- generic signup/reset confirmation;
- invalid/expired reset token;
- account deletion confirmation.

## Submission

- malformed URL;
- inaccessible URL;
- paywall;
- extraction uncertainty;
- malformed file;
- oversized file;
- unsupported file;
- SSRF rejection;
- retry/fallback to manual text/file input.

## Processing

- pending;
- processing by meaningful stage;
- failed;
- optional cancellation;
- completed after navigating away.

## Results

- high/moderate/low confidence;
- limited evidence;
- content-only analysis;
- propagation unavailable;
- interaction unavailable;
- explanation pending;
- explanation unavailable;
- technical deep dive;
- uncertainty/limitations.

Never hide missing evidence through subtle visual styling alone.

---

# 20. SECURITY REQUIREMENTS

Mandatory:

- Argon2id password hashing;
- no password logging;
- no plaintext credentials;
- generic account-enumeration-safe responses;
- restricted CORS;
- secure HttpOnly SameSite cookies;
- HTTPS;
- CSP;
- HSTS where appropriate;
- security headers;
- secret management through environment variables;
- no secrets in frontend bundles;
- SSRF protection;
- redirect revalidation;
- MIME validation;
- upload size limits;
- PDF structure validation;
- malformed-file rejection;
- decompression-bomb protection;
- uploaded content treated as inert data;
- backend-enforced rate limiting;
- LLM token/length/concurrency controls;
- concurrency controls for analyses.

Every server-side URL fetch must pass SSRF protection.

Every upload must be validated before parsing.

---

# 21. RATE AND COST CONTROL

Redis-backed controls include:

- analyses per hour per user;
- LLM tokens per day;
- concurrent in-flight analyses.

Limits are configuration, not hardcoded.

LLM explanation length and token budgets are enforced server-side.

Frontend hiding of a feature is never considered rate limiting.

---

# 22. TESTING REQUIREMENTS

Four testing levels are mandatory.

## 21.1 Unit

Cover:

- preprocessing;
- graph construction;
- auth utilities;
- confidence-band calculation;
- duplicate hashing;
- evidence mapping.

## 21.2 Integration

Cover:

- API endpoints;
- database;
- Redis;
- authentication;
- async analysis lifecycle;
- LLM adapter;
- LLM failure fallback.

## 21.3 ML integrity

Cover:

- train/test leakage;
- label validation;
- feature shape;
- graph integrity;
- missing-data fallback;
- reproducible seeding;
- model artifact loading.

## 21.4 E2E

Cover:

`signup → login → submit → progress → result → history → logout`

The final frontend phase extends this to include:

- each input type;
- graph interaction.

No production deployment occurs without the required E2E suite passing.

---

# 23. VERSIONING DISCIPLINE

The following are independent version dimensions:

- `model_version`
- `preprocessing_version`
- `graph_construction_version`
- `calibration_version`

Rules:

- preprocessing changes bump preprocessing version;
- graph construction changes bump graph construction version;
- calibration changes bump calibration version;
- model artifacts use exact model version;
- production never implicitly loads "latest";
- CI must detect versioned-module changes without corresponding version bumps.

A checkpoint does not become production-eligible until required ML integrity tests pass.

---

# 24. DATABASE / MIGRATION RULES

- PostgreSQL schema follows Architecture.
- Migrations are reversible.
- Do not silently alter binding schema.
- If a schema change contradicts Architecture, update/re-approve Architecture before implementing the change.
- `analyses.id` remains the only cross-table analysis identity.
- The composite version tuple remains a uniqueness/deduplication mechanism only.

---

# 25. PHASED IMPLEMENTATION PLAN

The implementation is phase-gated.

## Phase 0 — Foundations

Build:

- repository structure;
- real backend modules;
- FastAPI skeleton;
- PostgreSQL;
- Redis;
- base schema;
- CI;
- Render environment;
- Netlify environment;
- HTTPS/CORS wiring.

### Hard exit gate

An empty "hello" request must round-trip:

`frontend → backend → DB → response`

over HTTPS and pass in CI.

Stop.

---

## Phase 1 — Authentication & Accounts

Build:

- signup;
- login;
- logout;
- password reset;
- account deletion;
- Argon2id;
- password strength UI;
- secure sessions;
- remember-device;
- failed-login throttling;
- generic enumeration-safe responses;
- RBAC enforcement.

### Hard exit gate

Full E2E:

`signup → login → logout → password reset → account deletion`

plus Auth unit/integration tests and verification that plaintext passwords never appear in logs.

Stop.

---

## Phase 2 — Shared Preprocessing

Build:

- canonical content extraction;
- cleaning;
- normalization;
- offline entry point;
- online entry point;
- canonical hash;
- URL retrieval;
- SSRF protection;
- retry/fallback behavior;
- `.txt` validation;
- `.pdf` validation.

### Hard exit gate

The same article supplied as:

- pasted text;
- URL;
- `.txt`;

must produce equal canonical output/hash where extraction is equivalent.

Malformed/unfetchable inputs must produce correct fallback behavior.

Stop.

---

## Phase 3 — Research Pipeline

Build:

- verified/licensed dataset;
- LR baseline;
- RF baseline;
- text MLP baseline;
- dual-layer GNN;
- cross-domain evaluation;
- metrics;
- calibration;
- confidence thresholds;
- ablations;
- early-detection robustness;
- reproduction script;
- versioned model artifact.

### Hard exit gate

A clean checkout must reproduce the reported metrics.

A complete model artifact must exist with:

- checkpoint;
- config;
- model version;
- dataset version;
- commit;
- seed.

Calibration status must be documented.

Stop.

---

## Phase 4 — ML Inference & Graph Processing

Build:

- exact model artifact loading;
- inference interface;
- content-only fallback;
- graph filtering/ranking;
- attribution honesty enforcement.

### Hard exit gate

Given a Phase 3 artifact and test article, the module independently returns a correctly shaped prediction result without API/frontend involvement.

Stop.

---

## Phase 5 — Analysis Orchestration

Build:

- submission;
- job enqueue;
- status polling;
- result endpoint;
- duplicate detection;
- version-aware reuse;
- visibility promotion;
- analysis references;
- rate limiting;
- concurrency limits;
- optional cancellation.

### Hard exit gate

Submitting the same article:

1. once as pasted text;
2. once by URL;

must produce:

- one `analyses` row;
- two private `analysis_references`.

After bumping `preprocessing_version`, a subsequent submission must create a second `analyses` row.

Stop.

---

## Phase 6 — LLM Explanation

Build:

- structured evidence request;
- Gemini Flash adapter;
- schema validation;
- reject/regenerate invalid response;
- explanation reuse;
- non-blocking explanation;
- retry behavior;
- budget enforcement;
- structural GNN/LLM boundary test.

### Hard exit gate

When the LLM is killed mid-request:

- prediction remains complete and visible.

A duplicate analysis must not make a second LLM call.

Boundary test passes in CI.

Stop.

---

## Phase 7 — Frontend Product Surface

Build:

- three-pane dashboard;
- all eight navigation sections;
- unified Analyze flow;
- text/URL/file input;
- status polling;
- Search;
- History;
- result presentation;
- confidence/evidence display;
- standard/deep-dive views;
- graph;
- graph toggles;
- unavailable-layer states;
- empty/first-use states;
- light/dark theme;
- accessibility basics.

### Hard exit gate

Full E2E:

`signup → login → submit each input type → progress → result → graph interaction → history → logout`

Stop.

---

## Phase 8 — Admin / Research Views

Build:

- admin/research metadata endpoints;
- deeper model metadata;
- evaluation summary;
- RBAC protection.

### Hard exit gate

A `user` gets 403 on admin/research endpoints.

An `admin` can see deeper metadata sourced from the recorded model artifact versions.

Stop.

---

## Phase 9 — Hardening & Launch

Build/verify:

- security pass;
- CORS;
- CSP/HSTS;
- secret audit;
- SSRF tests;
- upload attack tests;
- load/rate-limit tests;
- deletion correctness;
- deployment pipeline;
- documentation-code consistency.

### Hard exit gate

All four testing levels are green.

A production dry run succeeds.

PRD Sections 4–6 are signed off item-by-item.

Stop.

---

# 26. PHASE DEPENDENCY MODEL

Dependency order:

`Phase 0`
↓
`Phase 1` + `Phase 2`
↓
`Phase 3` may proceed in parallel with Phases 1–2 after Phase 0
↓
`Phase 4`
↓
`Phase 5`
↓
`Phase 6`
↓
`Phase 7`
↓
`Phase 8`
↓
`Phase 9`

Phase 5 requires:

- Auth;
- preprocessing;
- ML/graph serving.

Do not jump ahead and create fake dependencies or placeholders to make a later phase appear complete.

---

# 27. ENGINEERING NON-NEGOTIABLES

Every phase follows these rules.

## Rule 1 — No ghost folders/files

Every file and directory must have a justified responsibility.

No speculative architecture folders.

## Rule 2 — No fake functionality

Forbidden:

- hardcoded predictions;
- fabricated confidence;
- mocked LLM responses presented as real;
- placeholder graph data;
- fake endpoints returning 200;
- fake completed states.

A feature is either genuinely implemented or not implemented.

## Rule 3 — No premature abstraction

Do not introduce factories/plugin systems/interfaces merely for hypothetical future implementations.

Use abstraction where an explicit second concrete implementation exists or where Architecture explicitly requires provider abstraction.

The LLM adapter is provider-abstracted because provider swapping is an explicit architectural requirement.

## Rule 4 — No silent scope expansion

If implementation exposes a requirement not covered by the governing documents:

**stop and raise it.**

Especially do not unilaterally alter:

- visibility;
- privacy;
- RBAC;
- GNN/LLM boundary;
- schema;
- architecture.

## Rule 5 — GNN predicts, LLM explains

This is a structural code boundary.

## Rule 6 — Every claim has a traceable source

Do not label an output as a calibrated probability unless the current model version has actually passed calibration validation.

---

# 28. THINGS THE IMPLEMENTATION AGENT MUST NOT INVENT

Do not invent:

- product features;
- navigation sections;
- database relationships;
- user roles;
- sharing policies beyond the approved visibility mechanism;
- model predictions;
- confidence values;
- attribution values;
- graph structure;
- causal claims;
- calibrated probabilities;
- research conclusions;
- dataset choice when licensing/completeness remains open;
- undocumented APIs;
- microservices;
- vector retrieval;
- user accuracy metrics;
- Early Detection Mode;
- model-comparison UI.

If something is necessary but unspecified, classify it as:

1. implementation detail safely derivable from an approved contract; or
2. an open decision requiring explicit resolution.

Never disguise category 2 as category 1.

---

# 29. OPEN-DECISION / STOP PROTOCOL

When implementation encounters something that is not explicitly specified:

### Step 1 — Check whether it is mechanically implied

If the behavior is directly required by an existing binding contract and does not introduce a new product, architecture, schema, security, privacy, or research decision, implement the smallest compliant behavior.

### Step 2 — Check for an existing open item

If the source documents already identify the matter as an open/tunable implementation item, do not convert it into a new fixed architectural decision. Use configuration where the architecture explicitly calls for tunability.

### Step 3 — Escalate genuine ambiguity

If the decision would introduce or change:

- product behavior;
- architecture;
- database schema;
- API contract;
- privacy/visibility policy;
- RBAC;
- ML methodology;
- research dataset/evaluation methodology;
- security boundary;

**STOP before implementation.**

Report the issue using:

```text
OPEN DECISION
Location:
Source requirement:
Observed ambiguity/conflict:
Why implementation is blocked:
Options:
Recommended option (if useful):
Required approval:
```

The implementation agent must not silently select an option merely because it is convenient.

# 30. STITCH REFERENCE MAPPING

The Stitch package is frozen.

The previously reviewed reference package contains the visual/reference screens for areas including:

- signup;
- verification;
- password reset;
- workspace states;
- processing;
- results;
- search;
- settings.

Use those references to reproduce the intended visual/interaction language where consistent with the approved product specification.

Do not:

- copy Stitch-generated HTML;
- copy its application architecture;
- infer backend behavior from visual appearance;
- treat an omitted screen as permission to omit a required PRD section;
- reopen Stitch for amendments.

The product requirements and architecture remain authoritative.

---

# 31. IMPLEMENTATION WORKFLOW

For every phase:

## Step A — Read authority

Before coding, inspect:

- this Master Build Specification;
- relevant PRD requirements;
- relevant Architecture section;
- relevant Rules;
- current phase definition.

## Step B — Inspect repository

Determine what actually exists.

Do not assume a previous phase exists merely because a document says it should.

## Step C — State exact scope

Identify:

- files/modules to add or modify;
- contracts affected;
- tests required;
- exit gate.

## Step D — Implement only that scope

Do not opportunistically implement future phases.

## Step E — Test continuously

Run targeted tests first, then phase-level tests.

## Step F — Validate against source

Check implementation against:

- PRD;
- Architecture;
- Rules;
- phase gate.

## Step G — Report

Provide:

- what was implemented;
- files changed;
- tests run;
- results;
- unresolved issues;
- exit-gate status.

## Step H — Stop

If the hard exit gate passes, stop.

Do not automatically begin the next phase.

If it fails, do not claim completion.

---

# 32. GIT / VERSION CONTROL RULES

The source documents establish GitHub Actions CI/CD and model artifact traceability.

Implementation must preserve:

- reproducible commits;
- model artifact → commit traceability;
- dataset version traceability;
- seed traceability;
- versioned prediction-relevant modules;
- CI validation.

Do not commit:

- secrets;
- API keys;
- database credentials;
- session signing keys;
- local `.env` files.

A versioned module change without the required version bump must fail CI.

---

# 33. DEFINITION OF DONE

A feature is done only when:

1. it is genuinely implemented;
2. it is consistent with PRD;
3. it is consistent with Architecture;
4. it obeys Rules;
5. it belongs to the current phase;
6. tests cover the required behavior;
7. the phase exit gate passes;
8. no known silent scope drift remains.

A visual approximation without functioning backing behavior is not done.

A backend endpoint without real implementation is not done.

A passing happy path with security/validation omitted is not done.

A feature that contradicts the governing documents is not done.

---

# 34. OPEN ITEMS THAT REMAIN OPEN

The consolidation does **not** silently close the following source-documented open items:

1. Exact visibility denylist/allowlist rules.
2. Exact Redis rate-limit thresholds.
3. Specific client-side graph rendering library.
4. Final research dataset confirmation and licensing/completeness verification.

These should be resolved at the appropriate implementation/research point.

They are not permission to redesign the surrounding architecture.

---

# 35. CONSOLIDATION DECISIONS

The following are explicit operational interpretations for the implementation agent:

## 33.1 Approved documents outrank drafts

PRD and Architecture are marked approved.

Phases and Rules are marked draft for review in their source files.

However, this Master Build Specification preserves their stated sequencing and engineering discipline as the intended implementation workflow. If a draft item contradicts an approved product/architecture decision, the approved decision wins.

## 33.2 Architecture open items remain open

An item listed as an Architecture implementation open item is not an architectural hole to be filled creatively.

Implement only when its phase requires it, using the constraints already documented.

## 33.3 Stitch is not a competing source of truth

Stitch is visual reference.

It cannot override requirements, architecture, security, data privacy, or implementation sequencing.

## 33.4 No implementation before foundations

The implementation starts with Phase 0.

Do not create the full application immediately and retrofit phases afterward.

---

# 36. INITIAL EXECUTION INSTRUCTION

At the start of implementation:

**Do not build the entire application.**

First:

1. inspect the repository;
2. establish the project structure required by Architecture;
3. implement **Phase 0 only**;
4. create the real module boundaries;
5. provision/configure the development database and Redis;
6. create the base migration;
7. establish CI;
8. establish frontend/backend development connectivity;
9. verify the Phase 0 hello round-trip;
10. report the Phase 0 exit-gate result;
11. stop.

Do not begin Phase 1 automatically.

---

# 37. FINAL OPERATING PRINCIPLE

Propagate is being built as an already-designed system.

The implementation agent must preserve this chain:

**Product truth**
→ PRD

**System truth**
→ Architecture

**Engineering discipline**
→ Rules

**Execution control**
→ Phases

**Visual reference**
→ frozen Stitch package

**Operational implementation authority**
→ this Master Build Specification

The goal is not to make the code "look like a prototype."

The goal is to produce the system that the specifications describe, with its research integrity, privacy boundaries, model/LLM separation, reproducibility, security, and user-facing behavior intact.

**Implement deliberately. Validate continuously. Stop at the gate. Never invent around ambiguity.**
