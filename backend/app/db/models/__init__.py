"""
Import every model module here so app/db/base.py's Base.metadata is
fully populated for Alembic autogenerate and for create_all in tests.
"""
from app.db.models.analysis import Analysis  # noqa: F401
from app.db.models.analysis_reference import AnalysisReference  # noqa: F401
from app.db.models.auth_session import AuthSession  # noqa: F401
from app.db.models.password_reset_token import PasswordResetToken  # noqa: F401
from app.db.models.rate_limit_event import RateLimitEvent  # noqa: F401
from app.db.models.user import User  # noqa: F401
