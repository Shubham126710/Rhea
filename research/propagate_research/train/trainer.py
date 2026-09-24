"""
Training orchestration for the dual-layer GNN (models/dual_layer_gnn.py),
wired to train/checkpointing.py for Decision 4's resumability
requirement.

STATUS: genuinely executable and tested here on SYNTHETIC data (torch
+ torch_geometric confirmed working, real forward/backward passes, real
optimizer steps, real checkpoint writes to disk) -- see
tests/unit/test_trainer.py and tests/ml_integrity/test_integrity.py.
NOT verified: training on real UPFD data (network-blocked),
multi-epoch convergence behavior on a real dataset, GPU execution (no
CUDA here). A short synthetic run completing without error and
producing a saved, reloadable, bit-for-bit reproducible checkpoint is
a real infrastructure check; it says nothing about whether the model
learns anything useful on real data.

CORRECTED DURING ML-INTEGRITY TESTING: this function originally took a
pre-built `model` argument. An integrity test caught that this made
seeded reproducibility silently false (the model's random init
happened before this function's torch.manual_seed() call, outside its
control). Fixed by taking a `model_factory` callable instead -- see
train_dual_layer_gnn()'s docstring.

Device-agnostic by construction (Decision 4): every torch call below
uses whatever `device` is passed in, defaulting to CPU. Running on a
CUDA device (Colab/Kaggle) requires no code change here, only passing
device=torch.device("cuda") -- untested since no CUDA is available in
this sandbox, but no CPU-only assumption is hardcoded.
"""
from dataclasses import dataclass

from propagate_research.train.checkpointing import CheckpointManager


@dataclass(frozen=True)
class TrainConfig:
    epochs: int
    lr: float = 0.001
    checkpoint_every: int = 1  # Decision 4: checkpoint periodically, not just at the end
    seed: int = 42


def train_dual_layer_gnn(
    model_factory,
    train_batches: list,
    val_batches: list,
    config: TrainConfig,
    checkpoint_manager: CheckpointManager,
    *,
    device=None,
):
    """`model_factory`: a zero-argument callable returning a fresh,
    UNTRAINED DualLayerGNN instance (e.g.
    `lambda: build_dual_layer_gnn(gnn_config)`), NOT a pre-built model.

    This is deliberate, not a style preference: an integrity test
    (tests/ml_integrity/test_integrity.py,
    test_training_run_reproducible_with_fixed_seed) caught a real bug
    in an earlier version of this function that accepted a pre-built
    model directly -- torch.manual_seed(config.seed) was called
    *after* the model's weights had already been randomly initialized
    by the caller, so two "reproducible" runs with the same seed
    produced different initial weights and therefore different final
    weights. Taking a factory lets this function guarantee
    manual_seed() runs strictly before model construction, every time,
    regardless of what the caller does -- removing the footgun instead
    of just documenting it.

    `train_batches`/`val_batches`: lists of PyG Batch objects, each
    with .x, .edge_index, .edge_type, .batch, .ptr, .y (graph-level
    0/1 labels). Resumes automatically from `checkpoint_manager`'s
    latest checkpoint if one exists -- callers don't need separate
    resume logic; starting a run and resuming an interrupted one are
    the same call. Note: on resume, model_factory is still called (to
    get a module to load the checkpoint's state into) but its random
    initialization is immediately overwritten by the checkpoint's
    saved weights, so reproducibility of a resumed run depends on the
    checkpoint, not on model_factory's own randomness.

    Returns (model, history) where history is a list of per-epoch
    dicts with train_loss/val_loss/val_accuracy -- not a
    MetricReport (evaluate/metrics.py) for the full suite; callers
    should run evaluate.metrics.compute_metrics separately on the
    trained model's predictions for the full Batch K suite.
    """
    import torch
    import torch.nn.functional as F

    device = device or torch.device("cpu")
    torch.manual_seed(config.seed)  # MUST precede model construction -- see docstring
    model = model_factory().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.lr)

    start_epoch = 0
    resumed = checkpoint_manager.resume(model=model, optimizer=optimizer)
    if resumed is not None:
        start_epoch = resumed.epoch + 1

    history = []
    for epoch in range(start_epoch, config.epochs):
        model.train()
        train_losses = []
        for batch in train_batches:
            batch = batch.to(device)
            optimizer.zero_grad()
            logits = model(batch.x, batch.edge_index, batch.edge_type, batch.batch, batch.ptr)
            loss = F.binary_cross_entropy_with_logits(logits, batch.y.float())
            loss.backward()
            optimizer.step()
            train_losses.append(loss.item())

        model.eval()
        val_losses = []
        correct = 0
        total = 0
        with torch.no_grad():
            for batch in val_batches:
                batch = batch.to(device)
                logits = model(batch.x, batch.edge_index, batch.edge_type, batch.batch, batch.ptr)
                loss = F.binary_cross_entropy_with_logits(logits, batch.y.float())
                val_losses.append(loss.item())
                preds = (torch.sigmoid(logits) >= 0.5).long()
                correct += (preds == batch.y.long()).sum().item()
                total += batch.y.shape[0]

        epoch_metrics = {
            "epoch": epoch,
            "train_loss": sum(train_losses) / len(train_losses) if train_losses else float("nan"),
            "val_loss": sum(val_losses) / len(val_losses) if val_losses else float("nan"),
            "val_accuracy": correct / total if total > 0 else float("nan"),
        }
        history.append(epoch_metrics)

        if (epoch + 1) % config.checkpoint_every == 0:
            checkpoint_manager.save(
                epoch=epoch,
                model=model,
                optimizer=optimizer,
                metrics=epoch_metrics,
            )

    return model, history
