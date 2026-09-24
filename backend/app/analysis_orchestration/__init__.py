"""
Analysis Orchestration module.

Responsibility (Architecture.md §2): owns the async analysis
lifecycle end-to-end — accept submission, dispatch to preprocessing/
ML/graph/LLM, persist result, serve status/result. This is the ONLY
module permitted to call the other five backend modules directly
(Architecture.md §2, Rules.md §2 "Module isolation").

Not implemented yet — built out starting Phase 5.
"""
