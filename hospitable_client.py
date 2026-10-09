"""Read-only client for the Hospitable Public API v2.

SECURITY MODEL — READ-ONLY BY CONSTRUCTION:
  * Base URL: https://public.api.hospitable.com/v2
  * Auth: Personal Access Token in the `Authorization: Bearer <token>` header.
    The token is read ONLY from the HOSPITABLE_API_TOKEN environment variable.
    It is never logged, printed, or written to disk by this module.
  * This client exposes exactly ONE HTTP method: GET. There are no
    post/put/patch/delete methods anywhere in this file, so even though the
    token may carry write scopes in Hospitable, this code is incapable of
    mutating anything (no calendar updates, no messages, no reservations).

Docs: https://developer.hospitable.com/ (Public API V2)
"""

from __future__ import annotations

import os
from datetime import date, datetime

import httpx

BASE_URL = "https://public.api.hospitable.com/v2"
TOKEN_ENV_VAR = "HOSPITABLE_API_TOKEN"
PROPERTY_CACHE_TTL_SECONDS = 3600  # refresh property list hourly


class HospitableAuthError(Exception):
    """Raised when no API token is available."""


class HospitableAPIError(Exception):
    """Raised when the Hospitable API returns an error."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class HospitableClient:
    """GET-only client for Hospitable Public API v2."""

    # Explicit allow-list: the only paths this client will ever request.
    # Anything else raises, so a bug can never wander into a mutating endpoint.
    _ALLOWED_PATH_PREFIXES = (
        "/user",
        "/properties",
        "/reservations",
    )

    def __init__(self, token: str | None = None, transport: httpx.BaseTransport | None = None):
        self._token = token or os.environ.get(TOKEN_ENV_VAR)
        if not self._token:
            raise HospitableAuthError(
                f"No Hospitable token found. Set the {TOKEN_ENV_VAR} environment "
                "variable to a Hospitable Personal Access Token (read scope is enough)."
            )
        self._http = httpx.Client(base_url=BASE_URL, transport=transport, timeout=30.0)
        self._properties_cache: list[dict] | None = None
        self._properties_cached_at: float = 0.0

    # ------------------------------------------------------------------
    # Internal: the single HTTP primitive. GET only — there is no other.
    # ------------------------------------------------------------------
    def _get(self, path: str, params: dict | None = None) -> dict | list:
        if not path.startswith(self._ALLOWED_PATH_PREFIXES):
            raise HospitableAPIError(f"Refusing to call non-allow-listed path: {path}")
        # NOTE: self._http.get — GET is the only verb used anywhere in this file.
        resp = self._http.get(path, params=params, headers=self._auth_headers())
        if resp.status_code == 401:
            raise HospitableAuthError("Hospitable rejected the token (401). Check HOSPITABLE_API_TOKEN.")
        if resp.status_code == 429:
            raise HospitableAPIError("Hospitable rate limit hit (429). Back off and retry.", 429)
        if resp.status_code >= 400:
            raise HospitableAPIError(
                f"Hospitable API error {resp.status_code}: {resp.text[:300]}", resp.status_code
            )
        return resp.json()

    def _auth_headers(self) -> dict:
        # The token value is used here and nowhere else. Never log it.
        return {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}

    # ------------------------------------------------------------------
    # Public read API
    # ------------------------------------------------------------------
    def check_auth(self) -> dict:
        """GET /user — verifies the token works. Returns the user payload."""
        data = self._get("/user")
        return data.get("data", data) if isinstance(data, dict) else data

    def list_properties(self, force_refresh: bool = False) -> list[dict]:
        """GET /properties — cached in memory for PROPERTY_CACHE_TTL_SECONDS."""
        import time

        now = time.time()
        if (
            not force_refresh
            and self._properties_cache is not None
            and (now - self._properties_cached_at) < PROPERTY_CACHE_TTL_SECONDS
        ):
            return self._properties_cache

        props: list[dict] = []
        page = 1
        while True:
            data = self._get("/properties", params={"page": page, "per_page": 100})
            if isinstance(data, dict):
                batch = data.get("data", [])
                meta = data.get("meta", {})
                last_page = meta.get("last_page", 1)
            elif isinstance(data, list):
                batch, last_page = data, 1
            else:
                batch, last_page = [], 1
            props.extend(batch)
            if page >= last_page:
                break
            page += 1

        self._properties_cache = props
        self._properties_cached_at = now
        return props

    def get_property(self, property_uuid: str) -> dict:
        """GET /properties/{uuid} — full property record."""
        data = self._get(f"/properties/{property_uuid}")
        return data.get("data", data) if isinstance(data, dict) else data

    def get_calendar(self, property_uuid: str, start: str, end: str) -> list[dict]:
        """GET /properties/{uuid}/calendar — per-day availability + nightly price.

        NOTE: start_date/end_date query params are the documented Hospitable
        convention (same as /reservations). If the endpoint ignores them and
        returns a default window, callers must verify coverage of the requested
        range — see logic.py.
        """
        data = self._get(
            f"/properties/{property_uuid}/calendar",
            params={"start_date": start, "end_date": end},
        )
        # Real shape (verified 2026-10-09): {"data": {"listing_id": ...,
        #   "provider": ..., "start_date": ..., "end_date": ...,
        #   "days": [{date, day, min_stay, closed_for_checkin,
        #             closed_for_checkout, status: {reason...}, ...}]}, ...}
        # Be liberal: accept {"days": [...]}, {"data": {"days": [...]}},
        # or a bare list.
        if isinstance(data, dict):
            inner = data.get("data", data)
            if isinstance(inner, dict):
                return inner.get("days", [])
            return inner if isinstance(inner, list) else []
        return data if isinstance(data, list) else []

    def list_reservations(
        self, property_uuids: list[str], start: str, end: str
    ) -> list[dict]:
        """GET /reservations — accepted reservations overlapping a window.

        Used as a cross-check; the calendar remains the source of truth.
        """
        params = {
            "properties[]": property_uuids,
            "start_date": start,
            "end_date": end,
            "date_query": "checkin",
            "status[]": ["accepted"],
            "per_page": 100,
            "include": "properties",
        }
        data = self._get("/reservations", params=params)
        if isinstance(data, dict):
            return data.get("data", [])
        return data if isinstance(data, list) else []


def parse_api_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise HospitableAPIError(
            f"Bad date {value!r}: use YYYY-MM-DD."
        )
