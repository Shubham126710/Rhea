"""Domain exceptions — kept separate from FastAPI's HTTPException so
service.py stays framework-agnostic (matches app/auth/exceptions.py)."""


class AnalysisNotFound(Exception):
    pass


class AnalysisNotCancellable(Exception):
    def __init__(self, current_status: str):
        self.current_status = current_status
        super().__init__(f"Cannot cancel an analysis with status {current_status!r}")


class ConcurrentAnalysisLimitExceeded(Exception):
    def __init__(self, limit: int):
        self.limit = limit
        super().__init__(f"Too many analyses already in progress (limit: {limit})")


class ExplanationNotRetryable(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
