"""
One-command reproduction entry point (Phases.md Batch T / Architecture.md
§9's experiments/run_experiment.py).

STATUS: the CLI parsing, config loading, and dispatch logic below are
genuinely executable and tested (tests/unit/test_run_experiment.py)
using the two real sklearn baselines end-to-end. dual_gnn is wired to
real UPFD data loading + training + evaluation (_run_dual_gnn) --
exercised so far only via a small real-data smoke run (see the Phase
3 report for exact results), not the full 100-epoch experiment.
text_mlp has smoke-test dispatch too (mirrors baseline_lr/
baseline_rf's synthetic-data smoke test); its network-dependent
encoding step is untested here (huggingface.co blocked in this
sandbox) but has been confirmed working in the Windows/Colab
environment (real all-MiniLM-L6-v2 weights, real 384-d embeddings).
cross_domain_eval now dispatches to _run_cross_domain, which runs
BOTH directions (Phases.md's "PolitiFact<->GossipCop") and never
trains on the target domain -- see _evaluate_dual_gnn. Ablation
variants (full/propagation_only/interaction_only) are wired via the
`ablation` hyperparameter, applied through graph/build_graph.py's
apply_ablation() before batching -- real edges are removed from the
model's input, not weights zeroed after the fact.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # so `propagate_research` imports work
from propagate_research.artifacts.packaging import (  # noqa: E402
    build_manifest,
    get_git_commit,
    save_manifest,
)
from propagate_research.config.schema import ExperimentConfig, load_config  # noqa: E402
from propagate_research.evaluate.metrics import compute_metrics  # noqa: E402
from propagate_research.models.baselines import (  # noqa: E402
    TextEncoderMLPBaseline,
    TfidfLogisticRegressionBaseline,
    TfidfRandomForestBaseline,
)

DEFAULT_UPFD_ROOT = "/content/upfd_data"  # verified Colab default; override via PROPAGATE_UPFD_ROOT


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Propagate Phase 3 experiment runner")
    parser.add_argument("--config", required=True, help="Path to a YAML experiment config")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate the config, print the resolved plan, and exit "
        "without loading any dataset or training anything.",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run on a tiny synthetic dataset (no real UPFD download) to verify "
        "the pipeline executes end-to-end. For baseline_lr/baseline_rf/text_mlp -- "
        "dual_gnn smoke-testing is exercised directly in its own test suite "
        "(test_trainer.py), not through this CLI.",
    )
    return parser


def _build_baseline(config: ExperimentConfig):
    hyperparameters = dict(config.hyperparameters)
    if "ngram_range" in hyperparameters:
        # YAML has no tuple type -- [1, 2] loads as a list, but sklearn
        # requires ngram_range specifically as a tuple. Converting here
        # rather than silently accepting a list that sklearn would
        # reject at fit() time with a much less obvious error.
        hyperparameters["ngram_range"] = tuple(hyperparameters["ngram_range"])

    if config.model_type == "baseline_lr":
        return TfidfLogisticRegressionBaseline(random_state=config.seed, **hyperparameters)
    if config.model_type == "baseline_rf":
        return TfidfRandomForestBaseline(random_state=config.seed, **hyperparameters)
    if config.model_type == "text_mlp":
        # epochs/lr are fit()-time parameters, not constructor kwargs
        # (see baselines.py's TextEncoderMLPBaseline.fit signature) --
        # only encoder_name/hidden_dim go to the constructor here.
        constructor_kwargs = {
            k: v for k, v in hyperparameters.items() if k in ("encoder_name", "hidden_dim")
        }
        return TextEncoderMLPBaseline(random_state=config.seed, **constructor_kwargs)
    raise ValueError(
        f"_build_baseline only handles baseline_lr/baseline_rf/text_mlp, "
        f"got {config.model_type!r}"
    )


def _run_baseline_smoke_test(config: ExperimentConfig) -> dict:
    """A tiny synthetic in-memory dataset -- proves the CLI's dispatch
    -> fit -> predict -> metrics -> artifact-packaging path genuinely
    executes, without needing real UPFD article text. For text_mlp,
    this still requires the real sentence-transformers encoder to
    reach huggingface.co -- network-blocked in this sandbox (fails
    cleanly there, confirmed working in Windows/Colab per the Phase 3
    report), unlike baseline_lr/baseline_rf which have no network
    dependency at all."""
    fake_texts = [
        "Shocking secret doctors don't want revealed, share now",
        "You won't believe this one weird trick",
        "Anonymous insider confirms wild conspiracy",
        "Miracle cure big pharma is hiding from you",
    ]
    real_texts = [
        "The senate voted on the appropriations bill today",
        "Quarterly revenue matched analyst forecasts",
        "The research was published in a peer-reviewed journal",
        "City council approved the infrastructure budget",
    ]
    texts = fake_texts + real_texts
    labels = [1] * len(fake_texts) + [0] * len(real_texts)

    model = _build_baseline(config)
    if config.model_type == "text_mlp":
        hp = config.hyperparameters
        model.fit(texts, labels, epochs=hp.get("epochs", 50), lr=hp.get("lr", 0.01))
    else:
        model.fit(texts, labels)
    preds = model.predict(texts)
    probs = model.predict_proba(texts)
    report = compute_metrics(labels, preds, probs)
    return report.as_dict()


def _load_relation_graphs(
    dataset_root: str, dataset_name: str, feature: str, split: str, ablation: str
):
    """UPFD split -> add_relation_types -> apply_ablation, for every
    graph in the split. Shared by both same-domain training/eval
    (_train_dual_gnn/_evaluate_dual_gnn) and cross-domain zero-shot
    evaluation (_run_cross_domain), so both paths build graphs
    identically -- no separate "cross-domain" graph-construction code
    path to drift from the ordinary one."""
    from propagate_research.data.upfd_loader import UPFDLoadConfig, load_upfd_split
    from propagate_research.graph.build_graph import add_relation_types, apply_ablation

    upfd_config = UPFDLoadConfig(root=dataset_root, name=dataset_name, feature=feature)
    ds = load_upfd_split(upfd_config, split)
    graphs = [
        apply_ablation(add_relation_types(ds[i], root_index=0), ablation) for i in range(len(ds))
    ]
    return ds, graphs


def _train_dual_gnn(config: ExperimentConfig, *, dataset_name: str | None = None):
    """Loads dataset_name's train split (defaults to config.dataset --
    the single-domain case), builds relation-typed + ablated graphs,
    trains a fresh DualLayerGNN. Returns (model, gnn_config,
    in_channels, history, dataset_name_used, ablation).

    Does NOT evaluate or package a manifest -- see _evaluate_dual_gnn
    and the two callers (_run_dual_gnn, _run_cross_domain) for that,
    so training and evaluation stay separately reusable.
    """
    from propagate_research.models.dual_layer_gnn import (
        DualLayerGNNConfig,
        build_dual_layer_gnn,
    )
    from propagate_research.train.checkpointing import CheckpointManager
    from propagate_research.train.trainer import TrainConfig, train_dual_layer_gnn
    from torch_geometric.loader import DataLoader

    hp = config.hyperparameters
    dataset_name = dataset_name or config.dataset
    ablation = hp.get("ablation", "full")
    dataset_root = os.environ.get("PROPAGATE_UPFD_ROOT", DEFAULT_UPFD_ROOT)
    batch_size = hp.get("batch_size", 128)

    train_ds, train_graphs = _load_relation_graphs(
        dataset_root, dataset_name, config.feature, "train", ablation
    )
    val_ds, val_graphs = _load_relation_graphs(
        dataset_root, dataset_name, config.feature, "val", ablation
    )

    train_batches = list(DataLoader(train_graphs, batch_size=batch_size, shuffle=True))
    val_batches = list(DataLoader(val_graphs, batch_size=batch_size, shuffle=False))

    in_channels = train_batches[0].x.shape[1]  # derived from real data, not hardcoded

    gnn_config = DualLayerGNNConfig(
        in_channels=in_channels,
        hidden_channels=hp.get("hidden_channels", 128),
        num_relations=hp.get("num_relations", 2),
        dropout=hp.get("dropout", 0.3),
    )

    def model_factory():
        return build_dual_layer_gnn(gnn_config)

    train_config = TrainConfig(
        epochs=hp.get("epochs", 100),
        lr=hp.get("lr", 0.001),
        checkpoint_every=hp.get("checkpoint_every", 1),
        seed=config.seed,
    )

    run_id = f"{config.model_type}-{dataset_name}-{config.feature}-{ablation}"
    ckpt = CheckpointManager(config.checkpoint_dir, run_id=run_id)

    print(f"Training {run_id}: {len(train_ds)} train graphs, {len(val_ds)} val graphs, "
          f"in_channels={in_channels}, epochs={train_config.epochs}, ablation={ablation}")
    model, history = train_dual_layer_gnn(
        model_factory, train_batches, val_batches, train_config, ckpt
    )

    for epoch_metrics in history:
        print(f"  epoch {epoch_metrics['epoch']}: "
              f"train_loss={epoch_metrics['train_loss']:.4f} "
              f"val_loss={epoch_metrics['val_loss']:.4f} "
              f"val_accuracy={epoch_metrics['val_accuracy']:.4f}")

    checkpoint_filename = None
    if history:
        checkpoint_filename = f"epoch_{history[-1]['epoch']}.pt"

    return (
        model, gnn_config, in_channels, history, run_id,
        dataset_name, ablation, checkpoint_filename,
    )


def _evaluate_dual_gnn(model, config: ExperimentConfig, dataset_name: str, split: str = "val"):
    """Eval-mode inference pass over dataset_name's `split`, collecting
    per-sample y_true/y_pred/y_score -> compute_metrics. NEVER trains
    (no optimizer, no backward pass, no gradient tracking) -- this is
    the only mechanism _run_cross_domain uses to touch the target
    domain, so target-domain data can never leak into training.
    """
    import torch
    from torch_geometric.loader import DataLoader

    hp = config.hyperparameters
    ablation = hp.get("ablation", "full")
    dataset_root = os.environ.get("PROPAGATE_UPFD_ROOT", DEFAULT_UPFD_ROOT)
    batch_size = hp.get("batch_size", 128)

    _ds, graphs = _load_relation_graphs(dataset_root, dataset_name, config.feature, split, ablation)
    batches = list(DataLoader(graphs, batch_size=batch_size, shuffle=False))

    model.eval()
    y_true, y_pred, y_score = [], [], []
    device = next(model.parameters()).device
    with torch.no_grad():
        for batch in batches:
            batch = batch.to(device)
            logits = model(batch.x, batch.edge_index, batch.edge_type, batch.batch, batch.ptr)
            probs = torch.sigmoid(logits)
            preds = (probs >= 0.5).long()
            y_true.extend(batch.y.long().tolist())
            y_pred.extend(preds.tolist())
            y_score.extend(probs.tolist())

    return compute_metrics(y_true, y_pred, y_score)


def _package_manifest(
    *, run_id, config, in_channels, gnn_config, checkpoint_filename, metrics_summary,
    extra_preprocessing=None,
):
    try:
        git_commit = get_git_commit(str(Path(__file__).parent.parent.parent))
    except RuntimeError as exc:
        print(f"(artifact packaging skipped: {exc})", file=sys.stderr)
        return None

    preprocessing_config = {"feature": config.feature}
    if extra_preprocessing:
        preprocessing_config.update(extra_preprocessing)

    manifest = build_manifest(
        model_version=run_id,
        dataset_version=f"{config.dataset}-upfd-real",
        git_commit=git_commit,
        seed=config.seed,
        preprocessing_config=preprocessing_config,
        model_config={
            "in_channels": in_channels,
            "hidden_channels": gnn_config.hidden_channels,
            "num_relations": gnn_config.num_relations,
            "dropout": gnn_config.dropout,
        },
        encoder_config={"type": "upfd_native", "feature": config.feature},
        checkpoint_filename=checkpoint_filename or "model.pt",
        metrics_summary=metrics_summary,
    )
    manifest_path = save_manifest(manifest, Path(config.output_dir) / run_id)
    print(f"Artifact manifest written: {manifest_path}")
    return manifest_path


def _run_dual_gnn(config: ExperimentConfig) -> int:
    """Single-domain case (config.cross_domain_eval is False): train
    on config.dataset's train split, evaluate on its own val split.
    Uses only existing components (data/upfd_loader.py,
    graph/build_graph.py, models/dual_layer_gnn.py, train/trainer.py,
    train/checkpointing.py, evaluate/metrics.py,
    artifacts/packaging.py).
    """
    (
        model, gnn_config, in_channels, _history, run_id,
        dataset_name, ablation, checkpoint_filename,
    ) = _train_dual_gnn(config)

    metrics_report = _evaluate_dual_gnn(model, config, dataset_name, "val")
    print(f"Validation metrics (real UPFD {dataset_name} val split, ablation={ablation}):")
    for key, value in metrics_report.as_dict().items():
        print(f"  {key}: {value}")

    _package_manifest(
        run_id=run_id,
        config=config,
        in_channels=in_channels,
        gnn_config=gnn_config,
        checkpoint_filename=checkpoint_filename,
        metrics_summary=metrics_report.as_dict(),
        extra_preprocessing={"ablation": ablation},
    )
    return 0


_DOMAIN_PAIR = ("politifact", "gossipcop")


def _other_domain(name: str) -> str:
    if name not in _DOMAIN_PAIR:
        raise ValueError(f"Cross-domain evaluation only supports {_DOMAIN_PAIR}, got {name!r}")
    return _DOMAIN_PAIR[1] if name == _DOMAIN_PAIR[0] else _DOMAIN_PAIR[0]


def _run_cross_domain(config: ExperimentConfig) -> int:
    """Phases.md Batch L: "Cross-domain zero-shot evaluation
    (PolitiFact<->GossipCop)" -- the "<->" is read literally as both
    directions, not one (see the Phase 3 report's methodology-decision
    section). Runs BOTH:
      1. train on PolitiFact -> zero-shot eval on GossipCop
      2. train on GossipCop -> zero-shot eval on PolitiFact
    config.dataset selects which direction runs first; both always
    run regardless (the field is not silently ignored -- it just
    doesn't gate which directions happen, since Batch L requires
    both).

    Zero-shot means exactly what _evaluate_dual_gnn already guarantees
    structurally: it never trains, never takes a backward pass, and is
    the ONLY place target-domain data is touched -- so target-domain
    leakage into training is prevented by construction, not by
    discipline alone. Official train/val/test splits are used as-is
    (via _load_relation_graphs -> load_upfd_split), never re-split.
    """
    first_source = config.dataset
    second_source = _other_domain(first_source)
    directions = [(first_source, second_source), (second_source, first_source)]

    for source, target in directions:
        print(f"Cross-domain direction: train={source} -> zero-shot eval={target}")
        (
            model, gnn_config, in_channels, _history, run_id,
            _ds, ablation, checkpoint_filename,
        ) = _train_dual_gnn(config, dataset_name=source)

        source_metrics = _evaluate_dual_gnn(model, config, source, "val")
        target_metrics = _evaluate_dual_gnn(model, config, target, "val")

        print(f"  source-domain ({source}) val metrics: {source_metrics.as_dict()}")
        print(f"  target-domain ({target}) zero-shot metrics: {target_metrics.as_dict()}")

        cross_run_id = f"crossdomain-{source}-to-{target}-{config.feature}-{ablation}"
        _package_manifest(
            run_id=cross_run_id,
            config=config,
            in_channels=in_channels,
            gnn_config=gnn_config,
            checkpoint_filename=checkpoint_filename,
            metrics_summary={
                "source_domain": source,
                "target_domain": target,
                "source_val_metrics": source_metrics.as_dict(),
                "target_zero_shot_metrics": target_metrics.as_dict(),
            },
            extra_preprocessing={"ablation": ablation, "cross_domain": True},
        )

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = load_config(args.config)

    if args.dry_run:
        print(f"Config OK: {args.config}")
        print(f"  model_type: {config.model_type}")
        print(f"  dataset: {config.dataset}")
        print(f"  feature: {config.feature}")
        print(f"  seed: {config.seed}")
        print(f"  cross_domain_eval: {config.cross_domain_eval}")
        return 0

    if args.smoke_test:
        if config.model_type not in ("baseline_lr", "baseline_rf", "text_mlp"):
            print(
                f"--smoke-test via this CLI only supports baseline_lr/baseline_rf/"
                f"text_mlp (got {config.model_type!r}) -- see module docstring for "
                f"why dual_gnn is smoke-tested through its own test suite instead.",
                file=sys.stderr,
            )
            return 1
        metrics = _run_baseline_smoke_test(config)
        print("Smoke test metrics (synthetic data, NOT a real result):")
        for key, value in metrics.items():
            print(f"  {key}: {value}")

        try:
            git_commit = get_git_commit(str(Path(__file__).parent.parent.parent))
        except RuntimeError as exc:
            print(f"(artifact packaging skipped: {exc})", file=sys.stderr)
            return 0

        encoder_config = (
            {"type": "sentence-transformers", "model_name": config.hyperparameters.get(
                "encoder_name", "all-MiniLM-L6-v2"
            )}
            if config.model_type == "text_mlp"
            else {"type": "tfidf"}
        )
        manifest = build_manifest(
            model_version=f"{config.model_type}-smoketest",
            dataset_version=f"{config.dataset}-synthetic-smoketest",
            git_commit=git_commit,
            seed=config.seed,
            preprocessing_config={},
            model_config=config.hyperparameters,
            encoder_config=encoder_config,
            metrics_summary=metrics,
        )
        manifest_path = save_manifest(manifest, Path(config.checkpoint_dir) / "smoketest")
        print(f"Artifact manifest written: {manifest_path}")
        return 0

    if config.model_type == "dual_gnn":
        if config.cross_domain_eval:
            return _run_cross_domain(config)
        return _run_dual_gnn(config)

    if config.cross_domain_eval and config.model_type != "dual_gnn":
        # cross_domain_eval only means something for the GNN -- an
        # invalid combination should fail clearly rather than silently
        # running an ordinary baseline_lr/baseline_rf/text_mlp
        # experiment as if the flag had no effect.
        print(
            f"cross_domain_eval=True is only meaningful for model_type='dual_gnn' "
            f"(got {config.model_type!r}). Refusing to silently ignore the flag.",
            file=sys.stderr,
        )
        return 1

    print(
        f"Full (non-smoke-test) runs for model_type={config.model_type!r} require "
        "real UPFD data and/or real pretrained encoder weights, both "
        "network-blocked in this sandbox (see module docstring). Use --dry-run "
        "to validate a config, or --smoke-test (baseline_lr/baseline_rf only) "
        "to exercise the full pipeline end-to-end on synthetic data.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
