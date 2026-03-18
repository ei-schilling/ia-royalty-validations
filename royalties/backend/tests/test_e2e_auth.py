"""End-to-end tests for the authentication system (register, login, logout, protected routes)."""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient


class TestRegisterFlow:
    """E2E tests for user registration."""

    @pytest.mark.asyncio
    async def test_register_creates_user_and_returns_token(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/register",
            json={"nickname": "newuser", "password": "securepass"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["nickname"] == "newuser"
        assert "user_id" in data["user"]
        assert "created_at" in data["user"]

    @pytest.mark.asyncio
    async def test_register_token_is_valid_for_me_endpoint(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/register",
            json={"nickname": "regme", "password": "pass1234"},
        )
        token = resp.json()["access_token"]

        me_resp = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["nickname"] == "regme"

    @pytest.mark.asyncio
    async def test_register_duplicate_nickname_returns_409(self, client: AsyncClient):
        await client.post(
            "/api/auth/register",
            json={"nickname": "dupeuser", "password": "pass1"},
        )
        resp = await client.post(
            "/api/auth/register",
            json={"nickname": "dupeuser", "password": "pass2"},
        )
        assert resp.status_code == 409
        assert "taken" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_empty_nickname_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/register",
            json={"nickname": "", "password": "pass1234"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_password_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/register",
            json={"nickname": "shortpw", "password": "ab"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_missing_password_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/register",
            json={"nickname": "nopw"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_long_nickname_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/register",
            json={"nickname": "x" * 101, "password": "pass1234"},
        )
        assert resp.status_code == 422


class TestLoginFlow:
    """E2E tests for user login."""

    @pytest_asyncio.fixture
    async def registered_user(self, client: AsyncClient):
        """Register a user to test login against."""
        resp = await client.post(
            "/api/auth/register",
            json={"nickname": "loginuser", "password": "correctpass"},
        )
        return resp.json()

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, registered_user: dict):
        resp = await client.post(
            "/api/auth/login",
            json={"nickname": "loginuser", "password": "correctpass"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["nickname"] == "loginuser"
        # Token should match the same user
        assert data["user"]["user_id"] == registered_user["user"]["user_id"]

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, registered_user: dict):
        resp = await client.post(
            "/api/auth/login",
            json={"nickname": "loginuser", "password": "wrongpass"},
        )
        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/login",
            json={"nickname": "ghost_user", "password": "whatever"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_token_works_for_protected_endpoints(
        self, client: AsyncClient, registered_user: dict
    ):
        login_resp = await client.post(
            "/api/auth/login",
            json={"nickname": "loginuser", "password": "correctpass"},
        )
        token = login_resp.json()["access_token"]

        # Test /me
        me_resp = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["nickname"] == "loginuser"

    @pytest.mark.asyncio
    async def test_login_empty_credentials_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/login",
            json={"nickname": "", "password": ""},
        )
        assert resp.status_code == 422


class TestMeEndpoint:
    """E2E tests for GET /api/auth/me."""

    @pytest.mark.asyncio
    async def test_me_without_token_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_me_with_invalid_token_returns_401(self, client: AsyncClient):
        resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_me_with_expired_format_token_returns_401(self, client: AsyncClient):
        resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ4In0.fake"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_me_returns_correct_user_data(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["nickname"] == "testuser"
        assert "user_id" in data
        assert "created_at" in data


class TestProtectedEndpoints:
    """E2E tests ensuring all protected endpoints reject unauthenticated requests."""

    @pytest.mark.asyncio
    async def test_upload_without_auth_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/uploads/",
            files={"file": ("test.csv", b"col1,col2\n1,2", "text/csv")},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_upload_without_auth_returns_401(self, client: AsyncClient):
        resp = await client.get(f"/api/uploads/{uuid.uuid4()}")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_trigger_validation_without_auth_returns_401(self, client: AsyncClient):
        resp = await client.post(f"/api/validations/{uuid.uuid4()}/run")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_validation_without_auth_returns_401(self, client: AsyncClient):
        resp = await client.get(f"/api/validations/{uuid.uuid4()}")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_issues_without_auth_returns_401(self, client: AsyncClient):
        resp = await client.get(f"/api/validations/{uuid.uuid4()}/issues")
        assert resp.status_code == 401


class TestFullAuthenticatedFlow:
    """E2E test for the complete flow: register → login → upload → validate → view results."""

    @pytest.mark.asyncio
    async def test_complete_flow(self, client: AsyncClient, fixtures_dir):
        # 1. Register
        reg_resp = await client.post(
            "/api/auth/register",
            json={"nickname": "flow_user", "password": "flowpass"},
        )
        assert reg_resp.status_code == 201
        token = reg_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Verify identity
        me_resp = await client.get("/api/auth/me", headers=headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["nickname"] == "flow_user"

        # 3. Upload a file
        csv_path = fixtures_dir / "valid_statement.csv"
        with open(csv_path, "rb") as f:
            upload_resp = await client.post(
                "/api/uploads/",
                files={"file": ("valid_statement.csv", f, "text/csv")},
                headers=headers,
            )
        assert upload_resp.status_code == 201
        upload_id = upload_resp.json()["upload_id"]

        # 4. Trigger validation
        val_resp = await client.post(
            f"/api/validations/{upload_id}/run", headers=headers
        )
        assert val_resp.status_code == 201
        validation_id = val_resp.json()["validation_id"]

        # 5. Get results
        results_resp = await client.get(
            f"/api/validations/{validation_id}", headers=headers
        )
        assert results_resp.status_code == 200
        data = results_resp.json()
        assert data["status"] == "completed"
        assert "summary" in data
        assert "issues" in data

        # 6. Get issues
        issues_resp = await client.get(
            f"/api/validations/{validation_id}/issues", headers=headers
        )
        assert issues_resp.status_code == 200
        assert isinstance(issues_resp.json(), list)

    @pytest.mark.asyncio
    async def test_register_then_logout_then_protected_fails(self, client: AsyncClient):
        """Simulates logout: after removing the token, protected endpoints fail."""
        # Register and get a token
        reg_resp = await client.post(
            "/api/auth/register",
            json={"nickname": "logout_user", "password": "logoutpass"},
        )
        token = reg_resp.json()["access_token"]

        # Works with token
        me_resp = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert me_resp.status_code == 200

        # "Logout" = remove token, should fail
        me_resp = await client.get("/api/auth/me")
        assert me_resp.status_code == 401

    @pytest.mark.asyncio
    async def test_two_users_have_separate_uploads(self, client: AsyncClient, fixtures_dir):
        """Two users register and upload files independently."""
        # User A
        resp_a = await client.post(
            "/api/auth/register",
            json={"nickname": "user_a", "password": "pass_a"},
        )
        token_a = resp_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # User B
        resp_b = await client.post(
            "/api/auth/register",
            json={"nickname": "user_b", "password": "pass_b"},
        )
        token_b = resp_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Both upload
        csv_path = fixtures_dir / "valid_statement.csv"
        with open(csv_path, "rb") as f:
            upload_a = await client.post(
                "/api/uploads/",
                files={"file": ("a.csv", f, "text/csv")},
                headers=headers_a,
            )
        assert upload_a.status_code == 201

        with open(csv_path, "rb") as f:
            upload_b = await client.post(
                "/api/uploads/",
                files={"file": ("b.csv", f, "text/csv")},
                headers=headers_b,
            )
        assert upload_b.status_code == 201

        # Different upload IDs
        assert upload_a.json()["upload_id"] != upload_b.json()["upload_id"]


class TestHealthEndpointPublic:
    """Health endpoint should remain public (no auth required)."""

    @pytest.mark.asyncio
    async def test_health_no_auth_required(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
