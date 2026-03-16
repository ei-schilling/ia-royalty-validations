"""Shared pytest fixtures for the Royalty Statement Validator test suite."""

import os
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base
from app.db.database import get_db
from app.main import app

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session():
    """Provide a clean database session for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSession() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """Provide an HTTP test client with database dependency override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_csv(fixtures_dir: Path) -> Path:
    """Path to a valid sample CSV fixture."""
    return fixtures_dir / "valid_statement.csv"


@pytest.fixture
def sample_pdf() -> Path:
    """Path to the real Schilling PDF."""
    pdf = Path(__file__).parent.parent.parent.parent / "baseDocs" / "10564_Royaltyafregning.pdf"
    if pdf.exists():
        return pdf
    pytest.skip("Real PDF not available")


@pytest.fixture
def upload_dir(tmp_path: Path) -> Path:
    """Provide a temporary upload directory."""
    d = tmp_path / "uploads"
    d.mkdir()
    return d
