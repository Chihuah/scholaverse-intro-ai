"""Shared pytest fixtures for the Scholaverse test suite."""

import asyncio
from collections.abc import AsyncGenerator

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from main import app

# ---------------------------------------------------------------------------
# Async engine & session fixtures (in-memory SQLite)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture()
async def async_engine():
    """Create a fresh in-memory async engine per test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async session that rolls back after each test."""
    session_factory = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture()
async def client(
    async_engine, db_session: AsyncSession
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTPX async client wired to the FastAPI app with test DB override."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    # Override the middleware session factory to use the test DB
    test_session_factory = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    app.state.session_factory = test_session_factory

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
    app.state.session_factory = None


# ---------------------------------------------------------------------------
# Convenience / data fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    """Mock Cloudflare Zero Trust authentication header."""
    return {"cf-access-authenticated-user-email": "test@example.com"}


@pytest.fixture()
def sample_student_data() -> dict:
    """Sample student registration payload."""
    return {
        "student_id": "411234567",
        "name": "測試同學",
        "email": "test@example.com",
    }
