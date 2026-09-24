"""
Shared test fixtures.

Integration tests run against a real Postgres instance (the same
docker-compose service used for local dev, or the postgres service
container in CI) — never sqlite or a mock — because the schema uses
Postgres-specific types (CITEXT, JSONB, UUID) and Rules.md §3.4/§5
treat the Architecture.md schema as binding, not illustrative.

IMPORTANT — schema comes from Alembic, not from this fixture. An
earlier version of this fixture called Base.metadata.create_all() /
drop_all(), which regenerates schema straight from the ORM's own type
inference rather than from alembic/versions/0001_base_schema.py. That
silently diverged from the real migration (a naive-vs-timezone-aware
datetime mismatch was found this way, undetected, because the
create_all()-generated columns didn't match what `alembic upgrade
head` actually produces). Tests must run against the exact schema
production gets, so this fixture assumes migrations have already been
applied (`alembic upgrade head` — already a required step before
`pytest` in PHASE0_SETUP.md and .github/workflows/ci.yml) and does
not create or drop any schema itself.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db.models  # noqa: F401
from app.core.config import get_settings
from app.db.session import get_db
from app.main import app


@pytest.fixture(scope="session")
def db_engine():
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """
    Phase 0's version of this fixture assumed application code never
    calls session.commit() (true for the health check). Phase 1's
    auth service genuinely needs to commit (a session must survive
    past the request that created it). A plain outer-transaction
    rollback pattern breaks under that: commit() would end the real
    transaction early and leak data between tests.

    join_transaction_mode="create_savepoint" (SQLAlchemy 2.0's
    documented pattern for this exact situation) makes session.commit()
    release/reopen a SAVEPOINT instead, so the outer transaction stays
    open until this fixture rolls it back — full isolation regardless
    of how much the code under test commits.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection,
        join_transaction_mode="create_savepoint",
    )
    session = TestingSessionLocal()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    # base_url is https, not the TestClient default http://testserver.
    # Phase 1's session cookies are correctly marked Secure (Rules.md
    # §11 — never weaken this for local-dev convenience), and a
    # Secure cookie is dropped by any HTTP client's cookie jar
    # (including httpx's, which backs TestClient) when the scheme is
    # plain http. Real deployments are always https (Netlify/Render);
    # this makes the test client match that instead of quietly
    # disabling Secure to make cookies "work" in tests.
    with TestClient(app, base_url="https://testserver") as c:
        yield c
    app.dependency_overrides.clear()
