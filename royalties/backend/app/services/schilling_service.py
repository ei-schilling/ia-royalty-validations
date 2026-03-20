"""Schilling ERP document fetching service.

Downloads documents from the Schilling API.  The backend authenticates directly
with Schilling using its own credentials (configured via environment variables)
so that it obtains an independent session token.
"""

import logging
import re
from typing import Any

import httpx

from app.config import settings

log = logging.getLogger(__name__)

# Timeout budget for Schilling API calls
_CONNECT_TIMEOUT = 10.0
_READ_TIMEOUT = 60.0


class SchillingFetchError(Exception):
    """Raised when a document cannot be fetched from Schilling."""

    def __init__(self, message: str, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


def _derive_auth_url(api_url: str) -> str:
    """Derive the authentication base URL from a company-scoped API URL.

    Example:
        "https://sch-test.local.schilling.dk/ws/company1"
        → "https://sch-test.local.schilling.dk/ws"
    """
    # Strip /company{N} suffix to get the /ws base
    return re.sub(r"/company\d+$", "", api_url.rstrip("/"))


def _make_client(base_url: str) -> httpx.AsyncClient:
    """Create an httpx client with appropriate SSL and timeout settings."""
    timeout = httpx.Timeout(
        connect=_CONNECT_TIMEOUT,
        read=_READ_TIMEOUT,
        write=_CONNECT_TIMEOUT,
        pool=_CONNECT_TIMEOUT,
    )
    verify_ssl = not any(
        domain in base_url for domain in (".local.", "localhost", "127.0.0.1")
    )
    return httpx.AsyncClient(timeout=timeout, verify=verify_ssl)


async def _authenticate(client: httpx.AsyncClient, ws_base: str) -> str:
    """Login to Schilling and return a session token.

    Raises SchillingFetchError on failure.
    """
    username = settings.schilling_username
    password = settings.schilling_password
    if not username or not password:
        raise SchillingFetchError(
            "Schilling credentials not configured (SCHILLING_USERNAME / SCHILLING_PASSWORD)",
            error_code="SCHILLING_AUTH_FAILED",
        )

    try:
        resp = await client.post(
            f"{ws_base}/authenticate/Login",
            json={"username": username, "password": password},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json;enums=expand",
            },
        )
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise SchillingFetchError(
            f"Cannot connect to Schilling for authentication: {exc}",
            error_code="SCHILLING_AUTH_FAILED",
        )

    if resp.status_code != 200:
        raise SchillingFetchError(
            f"Schilling Login returned HTTP {resp.status_code}",
            error_code="SCHILLING_AUTH_FAILED",
        )

    data = resp.json()
    if not data.get("success"):
        error_msg = data.get("error", "Unknown authentication error")
        raise SchillingFetchError(
            f"Schilling Login failed: {error_msg}",
            error_code="SCHILLING_AUTH_FAILED",
        )

    token = data.get("result")
    if not token:
        raise SchillingFetchError(
            "Schilling Login returned no token",
            error_code="SCHILLING_AUTH_FAILED",
        )

    log.info("Successfully authenticated with Schilling")
    return token


async def _logout(client: httpx.AsyncClient, ws_base: str, token: str) -> None:
    """Best-effort logout from Schilling."""
    try:
        await client.post(
            f"{ws_base}/authenticate/Logout",
            json={"token": token},
            headers={
                "Content-Type": "application/json",
                "X-Schilling-Token": token,
            },
        )
        log.debug("Logged out from Schilling")
    except Exception:
        log.debug("Schilling logout failed (non-critical)")


async def fetch_document_from_schilling(
    document_id: int,
    schilling_token: str,
    company_id: int,
    base_url: str,
) -> tuple[bytes, dict[str, Any]]:
    """Download a PDF document from the Schilling document management API.

    The backend authenticates with its own credentials (ignoring the
    ``schilling_token`` passed by the frontend) to guarantee a valid session.

    Returns:
        (pdf_bytes, metadata_dict) where metadata may contain filename, size, etc.

    Raises:
        SchillingFetchError with appropriate error_code on failure.
    """
    ws_base = _derive_auth_url(base_url)

    async with _make_client(base_url) as client:
        # ── 0. Authenticate with Schilling ──
        token = await _authenticate(client, ws_base)

        try:
            headers = {
                "X-Schilling-Token": token,
                "X-Schilling-Language": "da",
                "Accept": "application/json;enums=expand",
            }

            # ── 1. Fetch document metadata (optional, best-effort) ──
            metadata: dict[str, Any] = {}
            try:
                meta_resp = await client.get(
                    f"{base_url}/schilling/documentmanagement/Document/{document_id}",
                    headers=headers,
                )
                if meta_resp.status_code == 200:
                    meta_json = meta_resp.json()
                    result = meta_json.get("result", meta_json)
                    metadata = {
                        "filename": result.get("Name", result.get("FileName", f"document_{document_id}.pdf")),
                        "document_type": result.get("DocumentType", ""),
                        "description": result.get("Description", ""),
                    }
            except Exception:
                metadata = {"filename": f"document_{document_id}.pdf"}

            # ── 2. Download the actual document PDF ──
            try:
                download_resp = await client.get(
                    f"{base_url}/schilling/documentmanagement/Document/{document_id}/Download",
                    headers=headers,
                )
            except httpx.ConnectError:
                raise SchillingFetchError(
                    f"Cannot connect to Schilling API at {base_url}",
                    error_code="SCHILLING_FETCH_FAILED",
                )
            except httpx.TimeoutException:
                raise SchillingFetchError(
                    "Schilling API request timed out",
                    error_code="SCHILLING_FETCH_FAILED",
                )

            if download_resp.status_code == 401:
                raise SchillingFetchError(
                    "Schilling token is invalid or expired",
                    error_code="SCHILLING_AUTH_FAILED",
                )
            if download_resp.status_code == 404:
                raise SchillingFetchError(
                    f"Document {document_id} not found in Schilling",
                    error_code="SCHILLING_FETCH_FAILED",
                )
            if download_resp.status_code != 200:
                detail = ""
                try:
                    detail = download_resp.json().get("error", download_resp.text[:200])
                except Exception:
                    detail = download_resp.text[:200]
                log.warning(
                    "Schilling download failed: HTTP %s - %s",
                    download_resp.status_code,
                    detail,
                )
                raise SchillingFetchError(
                    f"Schilling API returned HTTP {download_resp.status_code}: {detail}",
                    error_code="SCHILLING_FETCH_FAILED",
                )

            pdf_bytes = download_resp.content
            if not pdf_bytes:
                raise SchillingFetchError(
                    f"Schilling returned empty document for ID {document_id}",
                    error_code="SCHILLING_FETCH_FAILED",
                )

            metadata["size_bytes"] = len(pdf_bytes)
            if "filename" not in metadata:
                metadata["filename"] = f"document_{document_id}.pdf"

            return pdf_bytes, metadata

        finally:
            # ── 3. Always logout to release the session ──
            await _logout(client, ws_base, token)
