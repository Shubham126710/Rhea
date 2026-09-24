"""
ML Inference module.

Responsibility (Architecture.md §2): loads an exact versioned model
artifact (never an implicit "latest") and runs
text encoder -> propagation GNN -> interaction GNN -> fusion ->
classification head, returning verdict, raw score, and attribution
data actually produced by the model (Master Build §10, attribution
honesty).

Not implemented yet — built out in Phase 4, after the model artifact
exists from Phase 3.
"""
