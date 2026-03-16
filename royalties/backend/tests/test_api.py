"""Tests for the REST API endpoints (auth, uploads, validations)."""

import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------
class TestAuthEndpoints:
    """Tests for POST /api/auth/identify."""

    @pytest.mark.asyncio
    async def test_create_new_user(self, client: AsyncClient):
        resp = await client.post("/api/auth/identify", json={"nickname": "tester"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["nickname"] == "tester"
        assert "user_id" in data

    @pytest.mark.asyncio
    async def test_identify_existing_user_returns_same(self, client: AsyncClient):
        resp1 = await client.post("/api/auth/identify", json={"nickname": "alice"})
        resp2 = await client.post("/api/auth/identify", json={"nickname": "alice"})
        assert resp1.json()["user_id"] == resp2.json()["user_id"]

    @pytest.mark.asyncio
    async def test_empty_nickname_rejected(self, client: AsyncClient):
        resp = await client.post("/api/auth/identify", json={"nickname": ""})
        assert resp.status_code == 422  # Pydantic validation error


# ---------------------------------------------------------------------------
# Upload endpoints
# ---------------------------------------------------------------------------
class TestUploadEndpoints:
    """Tests for POST /api/uploads/ and GET /api/uploads/{id}."""

    @pytest_asyncio.fixture
    async def user_id(self, client: AsyncClient) -> uuid.UUID:
        resp = await client.post("/api/auth/identify", json={"nickname": "uploader"})
        return resp.json()["user_id"]

    @pytest.mark.asyncio
    async def test_upload_csv(self, client: AsyncClient, user_id: str, fixtures_dir: Path):
        csv_path = fixtures_dir / "valid_statement.csv"
        with open(csv_path, "rb") as f:
            resp = await client.post(
                "/api/uploads/",
                files={"file": ("valid_statement.csv", f, "text/csv")},
                data={"user_id": user_id},
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["filename"] == "valid_statement.csv"
        assert data["file_format"] == "csv"
        assert data["row_count"] == 3

    @pytest.mark.asyncio
    async def test_upload_json_file(self, client: AsyncClient, user_id: str, fixtures_dir: Path):
        json_path = fixtures_dir / "valid_statement.json"
        with open(json_path, "rb") as f:
            resp = await client.post(
                "/api/uploads/",
                files={"file": ("valid_statement.json", f, "application/json")},
                data={"user_id": user_id},
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["file_format"] == "json"
        assert data["row_count"] == 2

    @pytest.mark.asyncio
    async def test_upload_unsupported_extension(self, client: AsyncClient, user_id: str):
        resp = await client.post(
            "/api/uploads/",
            files={"file": ("test.txt", b"hello world", "text/plain")},
            data={"user_id": user_id},
        )
        assert resp.status_code == 400
        assert "not allowed" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_nonexistent_user(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            "/api/uploads/",
            files={"file": ("test.csv", b"a,b\n1,2", "text/csv")},
            data={"user_id": fake_id},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_upload(self, client: AsyncClient, user_id: str, fixtures_dir: Path):
        csv_path = fixtures_dir / "valid_statement.csv"
        with open(csv_path, "rb") as f:
            upload_resp = await client.post(
                "/api/uploads/",
                files={"file": ("valid_statement.csv", f, "text/csv")},
                data={"user_id": user_id},
            )
        upload_id = upload_resp.json()["upload_id"]

        resp = await client.get(f"/api/uploads/{upload_id}")
        assert resp.status_code == 200
        assert resp.json()["upload_id"] == upload_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_upload(self, client: AsyncClient):
        resp = await client.get(f"/api/uploads/{uuid.uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Validation endpoints
# ---------------------------------------------------------------------------
class TestValidationEndpoints:
    """Tests for validation run lifecycle."""

    @pytest_asyncio.fixture
    async def uploaded_csv(self, client: AsyncClient, fixtures_dir: Path) -> dict:
        """Create a user and upload a CSV, returning both IDs."""
        user_resp = await client.post("/api/auth/identify", json={"nickname": "validator"})
        user_id = user_resp.json()["user_id"]

        csv_path = fixtures_dir / "valid_statement.csv"
        with open(csv_path, "rb") as f:
            upload_resp = await client.post(
                "/api/uploads/",
                files={"file": ("valid_statement.csv", f, "text/csv")},
                data={"user_id": user_id},
            )
        return {"user_id": user_id, "upload_id": upload_resp.json()["upload_id"]}

    @pytest.mark.asyncio
    async def test_trigger_validation(self, client: AsyncClient, uploaded_csv: dict):
        upload_id = uploaded_csv["upload_id"]
        resp = await client.post(f"/api/validations/{upload_id}/run")
        assert resp.status_code == 201
        data = resp.json()
        assert "validation_id" in data
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_validation_results(self, client: AsyncClient, uploaded_csv: dict):
        upload_id = uploaded_csv["upload_id"]
        trigger_resp = await client.post(f"/api/validations/{upload_id}/run")
        validation_id = trigger_resp.json()["validation_id"]

        resp = await client.get(f"/api/validations/{validation_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert "summary" in data
        assert "issues" in data

    @pytest.mark.asyncio
    async def test_get_validation_issues_paginated(self, client: AsyncClient, uploaded_csv: dict):
        upload_id = uploaded_csv["upload_id"]
        trigger_resp = await client.post(f"/api/validations/{upload_id}/run")
        validation_id = trigger_resp.json()["validation_id"]

        resp = await client.get(f"/api/validations/{validation_id}/issues?page=1&size=10")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_trigger_with_specific_rules(self, client: AsyncClient, uploaded_csv: dict):
        upload_id = uploaded_csv["upload_id"]
        resp = await client.post(
            f"/api/validations/{upload_id}/run",
            json={"rules": ["missing_titles", "invalid_rates"]},
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_trigger_nonexistent_upload(self, client: AsyncClient):
        resp = await client.post(f"/api/validations/{uuid.uuid4()}/run")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_validation(self, client: AsyncClient):
        resp = await client.get(f"/api/validations/{uuid.uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------
class TestHealthEndpoint:
    """Tests for the health check."""

    @pytest.mark.asyncio
    async def test_health_ok(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
