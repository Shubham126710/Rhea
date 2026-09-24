# Product Requirements Document (PRD)
## Dual-Layer GNN Fake News Detection — Research Demonstration Platform

**Status:** Approved — Architecture.md may now begin.
**Companion research work:** "A Dual-Layer Graph Neural Network with LLM-Grounded Explanations for Cross-Domain Fake News Detection"

---

## 1. Purpose and Scope

This document defines what the system must do. It intentionally avoids describing *how* the system is built — technology choices, service boundaries, schemas, and infrastructure are the subject of the forthcoming Architecture.md, which may not begin until this PRD is reviewed and accepted.

The system has two coexisting identities:

1. **A public-facing application** that lets a user submit or search content and receive a Fake/Real verdict, supporting evidence, a rendered dual-layer graph, and an LLM-grounded explanation.
2. **A reproducible research pipeline** (training, baselines, ablations, cross-domain and early-detection evaluation) that produces the model the application serves. The research pipeline is not exposed through the application's UI beyond the metadata described in Section 6.

The application is a demonstration and inference platform. It is not a training UI, a baseline-comparison tool, or a research dataset browser.

---

## 2. Goals and Non-Goals

**Goals**
- Let any member of the public create an account and submit content to receive a defensible, explained verdict. Analysis submission requires an authenticated account — the platform is publicly accessible for signup, not open to anonymous, unauthenticated inference.
- Make the dual-layer graph (propagation + interaction) a visible, explorable part of the result — this is the project's core research contribution and must not be hidden behind an internal abstraction.
- Keep the model's prediction and the LLM's explanation strictly separated: the model predicts, the LLM explains only what the model produced.
- Support a real account system (signup, login, session, history, deletion) appropriate to a final-year-project-grade public deployment.
- Reuse computation and explanations across equivalent submissions without leaking any user's private data to another user.
- Never overstate what the system knows: uncertain, low-evidence, or uncalibrated outputs must be visibly labeled as such, not smoothed over.

**Non-Goals (v1)**
- No in-app training, baseline selection, or experiment configuration for end users.
- No user-vs-user comparison, leaderboard, or personalization based on submission accuracy.
- No mobile-optimized experience (responsive-safe only).
- No microservice decomposition; no distributed infrastructure beyond what moderate public traffic requires.
- No vector database, knowledge base, or retrieval layer — not justified by any current requirement.
- No Early Detection Mode exposed to users.

---

## 3. Users and Access

- **Audience:** the project team, evaluators/examiners, and any member of the public who receives the deployed URL.
- **Roles (RBAC):** at minimum, a normal authenticated user and an admin/research role. Roles are system/admin-assigned; users cannot self-select a privileged role at signup.
- **Scale assumption:** small to moderate public usage. The system must still implement genuine session handling, rate limiting, validation, and error handling — these are not deferred as "premature" for this scale.

---

## 4. Functional Requirements

### 4.1 Authentication & Accounts
- Signup requires email, display name, and password only. No institutional fields, no self-selected role.
- Password strength is shown live during signup (indicator + requirement checklist). Passwords are hashed with Argon2id or equivalent; plaintext is never stored.
- Email verification is supported but does not block ordinary use; it may be required for sensitive operations.
- Sessions are server-managed with secure, HttpOnly, SameSite cookies; explicit logout is provided; "remember this device" is supported.
- Password reset uses short-lived, single-use, securely generated tokens invalidated after use.
- After 5 failed login attempts, further attempts are throttled for approximately 20 minutes.
- Users can delete their own account with explicit confirmation; deletion invalidates all sessions.
- Signup and password-reset responses never reveal whether a given email is registered (generic confirmation message in both cases).

### 4.2 Dashboard & Navigation
- Authenticated layout: a three-part workspace — history (left), active analysis workspace (center), contextual controls (right) — in the spirit of familiar chat-tool layouts.
- All navigation sections (Home, Analyze, Search, History, Model/Evidence, Profile, Help, Settings) must be real, functional sections in v1. No placeholder or non-functional navigation items.
- New users see an honest empty state with a clear call to action to run their first analysis. No fabricated or demo history is inserted into a real account.

### 4.3 Submitting Content for Analysis
- A user may submit content as pasted raw text, a URL, or an uploaded file (.txt/.pdf), through one unified submission flow.
- URL content is fetched and extracted automatically server-side. If extraction is uncertain, the UI communicates this clearly rather than silently proceeding.
- If retrieval fails (paywall, 404, malformed URL, JS-heavy page, etc.), the system retries automatically where appropriate, then presents a clear error with a fallback to manual text entry or file upload. The user is never left stuck with no path forward.
- Analysis must work whether or not real propagation/interaction data exists for the submitted content. When such structure is unavailable, the system uses a content-only fallback path and states this limitation explicitly in the result — it never fabricates missing graph structure.
- Submitting content that is a duplicate (by content, not merely title) of an already-analyzed item reuses an existing compatible result rather than reprocessing. A fresh analysis is required when the content has materially changed or when any prediction-relevant model, preprocessing, graph-construction, feature, or calibration version has changed.

### 4.4 Processing Experience
- Analysis runs asynchronously. On submission, the user receives immediate confirmation and a live status view; they are never shown a frozen loading screen.
- If the user navigates away, processing continues server-side and the completed result is available later from History.
- Progress is communicated through defined stages (e.g., extracting content, preparing features, building graph, running model, generating explanation, finalizing result, complete) where technically meaningful.
- **(SHOULD, not MUST)** Users should be able to cancel an analysis that is still processing where cancellation is technically possible, preventing unnecessary downstream processing and API expenditure where feasible.

### 4.5 Result Presentation
- The primary verdict is Fake or Real, shown with a categorical confidence band (High/Moderate/Low). The band shall be determined by a documented thresholding/calibration procedure established from validation data and versioned alongside the model — never arbitrary UI values, and thresholds shall not be selected merely to produce visually appealing or balanced categories.
- A raw numeric score is available in an advanced view. It is labeled a "probability" only if the underlying model has been validated as calibrated; otherwise it is labeled a "model confidence score."
- Confidence display accounts for evidence availability: a high raw score produced without full graph data is shown as something like "High model confidence · Limited evidence," never simply "High confidence."
- Two explanation depths are provided:
  - **Standard view:** human-readable evidence and reasoning suitable for a general user.
  - **Deep-dive view:** technical detail — node/edge importance, attention weights (where the architecture produces meaningful ones), feature contributions. These are explicitly labeled as model attribution/importance signals, not causal proof. Deep-dive attribution shall expose only attribution/importance signals that are actually supported by the implemented model architecture; the system shall not fabricate attention weights, node importance, or feature contributions merely to populate the interface.
- The explanation follows a fixed structure: Verdict → Confidence → Why this result (summary) → Supporting signals (bullets) → Graph insights (if available) → Uncertainty/limitations → optional Technical Deep Dive.
- The LLM explains only what the analysis pipeline actually produced; it never introduces evidence the pipeline did not supply.
- Uncertainty and missing-data conditions are shown as explicit, visible states (e.g., "Low confidence," "Content-only analysis," "Propagation data unavailable") rather than implied through visual de-emphasis alone. Where relevant, optional next steps are offered (provide more content, search for related information, continue with available evidence) without any promise of a better result.
- Regular users see basic reproducibility metadata on a result: timestamp, model/version identifier, input mode, and which data layers were available. Deeper technical metadata (dataset version, model configuration, feature pipeline version, evaluation info, debug attribution) is visible to the admin/research role only.

### 4.6 Graph Visualization
- The dual-layer graph is rendered for the user by default, as a filtered, representative subset of the most relevant nodes and edges (not the full raw graph, which may be very large).
- Propagation and interaction relationships are shown in one combined graph, visually distinguished (edge style/color + legend), with toggles for Propagation / Interaction / Both.
- Controls allow expanding to see more of the graph, up to "show all" when the graph size is manageable; low-relevance portions collapse by default.
- If a layer's underlying data is unavailable for a given submission, the UI states this explicitly rather than omitting it silently or fabricating a graph.

### 4.7 Search & History
- History shows, at a glance, a title/snippet, verdict, and date for each past analysis; clicking opens the full result.
- Search covers the user's own private history plus analyses that are explicitly marked shareable — never every analysis ever submitted by anyone, and never another user's private analyses or metadata.

### 4.8 Data Sharing, Privacy, and Reuse
- **Analysis result** (the computed verdict, evidence, graph, and explanation) and **user history/reference** (a private link between a user and a result) are distinct concepts throughout the system.
- Submitted content is private by default. Only content meeting an explicit, backend-enforced shareable/public-content rule may become part of the shared/global pool that duplicate detection and global search draw from. A duplicate match alone never promotes private content into that pool.
- Uploaded files are private by default and participate only in the uploading user's own history and duplicate detection, not the shared pool, regardless of hash matches.
- If a user submits content that matches an existing shared analysis, they receive their own private history reference to that shared result; they gain no access to any other user's private data.
- A cached LLM explanation is reused whenever a shared analysis is reused, provided it was generated from the same model version and the same evidence. A changed model or evidence version triggers a fresh explanation.
- Private analyses remain private and are deleted with the user's account. Analyses legitimately admitted to the shared pool are retained as shared computational resources and have all user-identifying ownership/linkage removed upon account deletion.

### 4.9 What Is Explicitly Not Built
- No leaderboard, per-user accuracy display, or user-to-user comparison of any kind.
- No in-product mode for selecting or comparing baseline models (LR/RF/MLP) — these exist only in the research/evaluation environment.
- No in-product "Early Detection Mode" — early-detection evaluation (using fraction-of-observed-propagation as its operational definition) is a research/paper robustness exercise only, and is meaningless for arbitrary user submissions that lack real propagation history.
- No domain label (e.g., "resembles GossipCop") shown to the end user — domain is a research/evaluation construct only.

---

## 5. Non-Functional Requirements

- **Security:** account-enumeration protection on signup/reset; explicit CORS restricted to the production frontend origin and local dev origins; sanitization and validation of all submitted content (HTML sanitization, MIME validation, file-size limits, malformed-file rejection, decompression-bomb protection); SSRF protection on server-side URL fetching; secrets never exposed to the frontend; standard hardening (HTTPS, secure cookies, CSP, HSTS where appropriate, relevant security headers).
- **Rate/cost control:** backend-enforced (not merely UI-hidden) per-user rate limits, token budgets for LLM calls, explanation length limits, concurrency limits, and overall API budget protection, since LLM calls carry real per-request cost on a public deployment.
- **Reliability:** the primary prediction (verdict, confidence, evidence, graph, metadata) is never blocked on LLM availability. LLM failure or timeout degrades to a visible "explanation unavailable — retry" state without hiding the rest of the result.
- **Accessibility:** basic WCAG AA practices — keyboard navigation, visible focus states, sufficient contrast, semantic controls, an accessible alternative/summary for the graph visualization, and not relying on tooltips as the sole source of critical information.
- **Performance/UX under scale:** large graphs shall be reduced and ranked server-side before transmission; the client shall perform interactive layout, rendering, and progressive visualization of the returned graph subset, without unnecessary data being shipped to the client.
- **Honesty under uncertainty:** the system must never present a calibrated-probability claim, a causal-evidence claim, or a complete-graph claim that isn't actually true of the underlying computation for that specific result.

---

## 6. Research Pipeline Requirements (for platform context, not user-facing)

These items constrain what the application must be able to consume and display, without dictating research methodology in this document:

- The system requires an appropriately licensed research dataset providing article content and, where available, propagation/user-interaction structure suitable for graph-based analysis. (The specific dataset is confirmed in Architecture/research documentation after licensing and completeness verification — not locked here.)
- The trained model must expose, per prediction: a verdict, a confidence signal, graph-based evidence (when available), and attribution information suitable for the Deep Dive view.
- The model's confidence output must be evaluated for calibration before any "probability" language is used anywhere in the product.
- Cross-domain generalization and evaluation of graph-based explanation faithfulness are research objectives the platform is intended to showcase; early-detection robustness is supporting evidence only and is never presented as a head-to-head claim against unrelated architectures evaluated under different conditions. The specific faithfulness evaluation methodology is specified in Architecture/research documentation, not committed to here.
- Model artifacts must be versioned (model version, dataset version, code commit, seed) so that every displayed result can be traced to the exact model and data that produced it.

---

## 7. Open Items Deferred to Architecture.md

- The concrete mechanism for deciding whether a given piece of content qualifies for the shared/global pool (Section 4.8).
- Concrete schema, storage technology, and service boundaries.
- Concrete backend/frontend hosting, API versioning mechanics, and CI/CD pipeline.
- Concrete testing framework wiring and coverage thresholds.
- Final specific research dataset selection and licensing confirmation.

---

## 8. Approval

Reviewed and approved, with 8 revisions incorporated (duplicate-reuse versioning condition, confidence-band calibration wording, server/client graph rendering split, account-deletion wording, mandatory authentication for analysis submission, attribution-honesty constraint, faithfulness-metric wording, and a SHOULD-level analysis-cancellation requirement). Architecture.md work may now begin.
