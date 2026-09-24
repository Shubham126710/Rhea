"""
LLM Adapter module.

Responsibility (Architecture.md §2): provider-abstracted interface
(Gemini Flash primary) that builds a structured-evidence payload,
calls the LLM, validates the response against a schema, and
rejects/regenerates on violation. Structurally forbidden from writing
to analyses.verdict or analyses.raw_score (Rules.md §1 Rule 5 — the
GNN predicts, the LLM only explains).

Not implemented yet — built out in Phase 6.
"""
