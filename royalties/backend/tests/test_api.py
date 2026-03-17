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
    """Tests for POST /api/auth/register, /login, /me."""

    @pytest.mark.asyncio
    async def test_register_new_user(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/register",
            json={"nickname": "tester", "password": "secret"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["user"]["nickname"] == "tester"
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_rejected(self, client: AsyncClient):
        await client.post(
            "/api/auth/register",
            json={"nickname": "alice", "password": "pass1"},
        )
        resp = await client.post(
            "/api/auth/register",
            json={"nickname": "alice", "password": "pass2"},
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient):
        await client.post(
            "/api/auth/register",
            json={"nickname": "bob", "password": "mypassword"},
        )
        resp = await client.post(
            "/api/auth/login",
            json={"nickname": "bob", "password": "mypassword"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post(
            "/api/auth/register",
            json={"nickname": "carol", "password": "rightpass"},
        )
        resp = await client.post(
            "/api/auth/login",
            json={"nickname": "carol", "password": "wrongpass"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_me_authenticated(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/auth/me")
        assert resp.status_code == 200
        assert resp.json()["nickname"] == "testuser"

    @pytest.mark.asyncio
    async def test_me_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_nickname_rejected(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/register",
            json={"nickname": "", "password": "pass"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_short_password_rejected(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/register",
            json={"nickname": "shortpw", "password": "ab"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Upload endpoints
# ---------------------------------------------------------------------------
class TestUploadEndpoints:
    """Tests for POST /api/uploads/ and GET /api/uploads/{id}."""

    @pytest.mark.asyncio
    async def test_upload_csv(self, auth_client: AsyncClient, fixtures_dir: Path):
        csv_path = fixtures_dir / "valid_statement.csv"
        with open(csv_path, "rb") as f:
            resp = await auth_client.post(
                "/api/uploads/",
                files={"file": ("valid_statement.csv", f, "text/csv")},
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["filename"] == "valid_statement.csv"
        assert data["file_format"] == "csv"
        assert data["row_count"] == 3

    @pytest.mark.asyncio
    async def test_upload_json_file(self, auth_client: AsyncClient, fixtures_dir: Path):
        json_path = fixtures_dir / "valid_statement.json"
        with open(json_path, "rb") as f:
            resp = await auth_client.post(
                "/api/uploads/",
                files={"file": ("valid_statement.json", f, "application/json")},
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["file_format"] == "json"
        assert data["row_count"] == 2

    @pytest.mark.asyncio
    async def test_upload_unsupported_extension(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/uploads/",
            files={"file": ("test.txt", b"hello world", "text/plain")},
        )
        assert resp.status_code == 400
        assert "not allowed" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_unauthenticated(self, client: AsyncClient):
        resp = await client.post(
            "/api/uploads/",
            files={"file": ("test.csv", b"a,b\n1,2", "text/csv")},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_upload(self, auth_client: AsyncClient, fixtures_dir: Path):
        csv_path = fixtures_dir / "valid_statement.csv"
        with open(csv_path, "rb") as f:
            upload_resp = await auth_client.post(
                "/api/uploads/",
                files={"file": ("valid_statement.csv", f, "text/csv")},
            )
        upload_id = upload_resp.json()["upload_id"]

        resp = await auth_client.get(f"/api/uploads/{upload_id}")
        assert resp.status_code == 200
        assert resp.json()["upload_id"] == upload_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_upload(self, auth_client: AsyncClient):
        resp = await auth_client.get(f"/api/uploads/{uuid.uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Validation endpoints
# ---------------------------------------------------------------------------
class TestValidationEndpoints:
    """Tests for validation run lifecycle."""

    @pytest_asyncio.fixture
    async def uploaded_csv(self, auth_client: AsyncClient, fixtures_dir: Path) -> dict:
        """Upload a CSV and return the upload_id."""
        csv_path = fixtures_dir / "valid_statement.csv"
        with open(csv_path, "rb") as f:
            upload_resp = await auth_client.post(
                "/api/uploads/",
                files={"file": ("valid_statement.csv", f, "text/csv")},
            )
        return {"upload_id": upload_resp.json()["upload_id"]}

    @pytest.mark.asyncio
    async def test_trigger_validation(self, auth_client: AsyncClient, uploaded_csv: dict):
        upload_id = uploaded_csv["upload_id"]
        resp = await auth_client.post(f"/api/validations/{upload_id}/run")
        assert resp.status_code == 201
        data = resp.json()
        assert "validation_id" in data
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_validation_results(self, auth_client: AsyncClient, uploaded_csv: dict):
        upload_id = uploaded_csv["upload_id"]
        trigger_resp = await auth_client.post(f"/api/validations/{upload_id}/run")
        validation_id = trigger_resp.json()["validation_id"]

        resp = await auth_client.get(f"/api/validations/{validation_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert "summary" in data
        assert "issues" in data

    @pytest.mark.asyncio
    async def test_get_validation_issues_paginated(
        self, auth_client: AsyncClient, uploaded_csv: dict
    ):
        upload_id = uploaded_csv["upload_id"]
        trigger_resp = await auth_client.post(f"/api/validations/{upload_id}/run")
        validation_id = trigger_resp.json()["validation_id"]

        resp = await auth_client.get(f"/api/validations/{validation_id}/issues?page=1&size=10")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_trigger_with_specific_rules(
        self, auth_client: AsyncClient, uploaded_csv: dict
    ):
        upload_id = uploaded_csv["upload_id"]
        resp = await auth_client.post(
            f"/api/validations/{upload_id}/run",
            json={"rules": ["missing_titles", "invalid_rates"]},
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_trigger_nonexistent_upload(self, auth_client: AsyncClient):
        resp = await auth_client.post(f"/api/validations/{uuid.uuid4()}/run")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_validation(self, auth_client: AsyncClient):
        resp = await auth_client.get(f"/api/validations/{uuid.uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_validation_unauthenticated(self, client: AsyncClient):
        resp = await client.post(f"/api/validations/{uuid.uuid4()}/run")
        assert resp.status_code == 401


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
