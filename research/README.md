# Propagate — Phase 3 Research Pipeline

Implements Architecture.md §9's research environment: dataset acquisition,
baselines, the dual-layer GNN, training/checkpointing, and evaluation.

## Read this before trusting any claim in this codebase

Every module's docstring states, explicitly, which of these three
categories it falls into:

1. **Executed and tested for real in this sandbox.** torch, torch_geometric,
   and sentence-transformers are genuinely installed here (confirmed by
   direct execution, not assumed) — real tensor ops, real RGCNConv message
   passing, real forward/backward passes, real optimizer steps, real
   checkpoint writes to disk. All of this runs against **synthetic data**
   shaped to match UPFD's documented/verified structure — not real UPFD data.
2. **Structurally validated only.** Code that is syntactically correct and
   has been reviewed against documented assumptions, but has not itself
   been executed (this category has shrunk a lot since torch turned out to
   be available — check each module's docstring for what's actually left
   here).
3. **Blocked by this sandbox's network egress**, confirmed by direct
   attempts, not inferred: downloading real UPFD data (Google Drive) and
   downloading pretrained sentence-transformers weights (huggingface.co)
   both fail with a 403 in this environment. Every place this matters is
   called out explicitly (`data/upfd_loader.py`, `encoders/content_encoder.py`).

**202/202 tests pass. Ruff clean.** But "tests pass" only means what the
tests actually check — for the torch-dependent modules, that's "runs
correctly on synthetic data shaped like the real thing," not "has been
validated against real UPFD data" or "produces a useful classifier." Both
of those require an environment with working access to Google Drive and
HuggingFace — Colab or Kaggle, per Decision 4.

## Two real bugs ML-integrity testing caught

Both fixed, not papered over — see git history / the Phase 3 report for
detail:

1. `graph/build_graph.py`'s `add_relation_types()` didn't validate that a
   graph's label was 0/1. Fixed: raises `ValueError` on anything else.
2. `train/trainer.py`'s `train_dual_layer_gnn()` originally took a
   pre-built model, which meant `torch.manual_seed()` ran *after* the
   model's weights were already randomly initialized — so "reproducible"
   runs with the same seed produced different results. Fixed: it now
   takes a `model_factory` callable, guaranteeing the seed is set before
   any weights are created.

## Layout (Architecture.md §9)

```
propagate_research/       # the actual library code
  data/upfd_loader.py      # dataset acquisition + label-polarity sanity check
  graph/relations.py       # direct-share/inherited-share split (pure logic, no torch)
  graph/build_graph.py     # wraps relations.py into a PyG Data object
  models/dual_layer_gnn.py # R-GCN based dual-relation model
  models/baselines.py      # TF-IDF+LR, TF-IDF+RF (real), Text-Encoder+MLP (real MLP head)
  encoders/content_encoder.py  # frozen sentence-transformers wrapper (baseline-only)
  train/checkpointing.py   # framework-agnostic save/load/resume
  train/trainer.py         # training loop orchestration
  evaluate/metrics.py      # full Batch K metric suite
  evaluate/calibration.py  # Brier score, reliability diagram, ECE, temperature scaling
  evaluate/early_detection.py  # BFS-order structural proxy (see Finding B below)
  artifacts/packaging.py   # Architecture.md §9 model artifact manifest
  config/schema.py         # experiment YAML config validation

experiments/
  configs/                # the five configs Architecture.md §9 names
  run_experiment.py        # one-command entry point (Batch T)

datasets/, model_checkpoints/, evaluation/  # empty, populated at runtime
tests/unit/                # CPU + torch-executable unit tests
tests/ml_integrity/        # Architecture.md §10's "ML integrity" test level
```

## Key verified design decisions (see the Phase 3 report for full detail)

- **Root-first indexing**: every UPFD graph's news/root node is local index
  0; edges touching it are `direct_share`, edges between two non-root nodes
  are `inherited_share`. This is UPFD's own documented edge-construction
  semantics, not an invented split.
- **Root/leaf feature-width consistency**: UPFD gives every node (root
  included) the same feature width per feature type — structurally
  inferred from the loader's one-npz-per-feature-type design, not
  confirmed by inspecting real tensor values (blocked). `feature: bert` is
  the default, specifically to avoid the unresolved ambiguity around what
  the `"profile"`/`"content"` feature types' root-node semantics actually
  are.
- **Label polarity is unverified**, mitigated with a plausibility check
  against the paper's published per-domain fake/real counts
  (`assert_label_polarity_plausible`), not trusted blindly.
- **Early-detection curves are a structural (BFS-order) approximation**,
  not literal wall-clock time — UPFD's public release doesn't retain
  per-node timestamps. Every artifact this produces must be labeled as
  such wherever reported.
- **No train/test re-splitting** — UPFD's own `train_idx`/`val_idx`/
  `test_idx` are used as-is, matching the literature's benchmark protocol
  (Decision 1). Verified by `tests/ml_integrity/test_integrity.py`'s
  `test_upfd_official_splits_are_used_not_resplit`, which statically checks
  no splitting function is called anywhere in this package.

## What this sandbox could NOT verify

- Real UPFD tensors (shape, actual label polarity, actual feature values)
- Real pretrained encoder output (sentence-transformers weight download)
- Multi-epoch convergence / actual model quality on real data
- GPU execution (no CUDA here — code is device-agnostic by construction,
  untested on CUDA)

All of the above require an environment with real internet access —
Colab or Kaggle, per Decision 4 — and should be the first thing verified
there, before trusting any reported metric as real.
