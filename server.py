"""NuVista Haven MCP server ("AI front desk").

Exposes NuVista Haven vacation rentals to AI assistants:
  - search_properties — find rentals by keyword, area, sleeps
  - check_availability — live availability from Hospitable calendars
  - get_quote — nightly rates x nights + cleaning fee
  - get_booking_link — direct booking URL on nuvistahaven.com

Run locally (stdio, for testing):
    ./venv/bin/python server.py

Run for public hosting (Streamable HTTP):
    ./venv/bin/python server.py --http [--port 8000]

The Hospitable token comes ONLY from the HOSPITABLE_API_TOKEN environment
variable. The client is GET-only by construction (see hospitable_client.py).
"""

from __future__ import annotations

import sys

from fastmcp import FastMCP

import logic
from hospitable_client import HospitableAuthError, HospitableClient
from properties import UnknownPropertyError

mcp = FastMCP("nuvista-haven")

_client: HospitableClient | None = None


def _get_client() -> HospitableClient:
    global _client
    if _client is None:
        _client = HospitableClient()  # reads HOSPITABLE_API_TOKEN
    return _client


@mcp.tool()
def search_properties(query: str = "", area: str = "", min_sleeps: int = 0) -> list[dict]:
    """Search NuVista Haven vacation rentals.

    Args:
        query: keyword matched against property names (e.g. "farmhouse", "hot tub").
        area: filter by area text (e.g. "Lancaster", "Poconos", "Sarasota").
        min_sleeps: only properties sleeping at least this many guests.
    """
    return logic.search_properties_logic(query=query, area=area, min_sleeps=min_sleeps)


@mcp.tool()
def check_availability(property: str, check_in: str, check_out: str) -> dict:
    """Check live availability for a property over a date range.

    Args:
        property: property name or keyword (e.g. "Farmhouse Haven", "pickleball").
        check_in: arrival date, YYYY-MM-DD.
        check_out: departure date, YYYY-MM-DD.
    """
    try:
        return logic.check_availability_logic(_get_client(), property, check_in, check_out)
    except UnknownPropertyError as e:
        return {"available": None, "error": str(e)}
    except HospitableAuthError as e:
        return {"available": None, "error": str(e)}


@mcp.tool()
def get_quote(property: str, check_in: str, check_out: str, guests: int = 2) -> dict:
    """Quote a stay: nightly rate x nights + cleaning fee.

    Nightly rates are live from Hospitable. If the cleaning fee is not
    exposed by the API, the total is marked as a partial estimate.
    """
    try:
        return logic.get_quote_logic(_get_client(), property, check_in, check_out, guests)
    except UnknownPropertyError as e:
        return {"error": str(e)}
    except HospitableAuthError as e:
        return {"error": str(e)}


@mcp.tool()
def get_property_details(property: str) -> dict:
    """Facts about a property: bedrooms, sleeps, bathrooms, amenities, highlights.

    Answers "does it have a hot tub?", "how many bedrooms?", etc.
    Facts come from nuvistahaven.com; unknown values are null, never guessed.
    """
    try:
        return logic.get_property_details_logic(property)
    except UnknownPropertyError as e:
        return {"error": str(e)}


@mcp.tool()
def get_booking_link(property: str, check_in: str = "", check_out: str = "") -> dict:
    """Direct booking URL on nuvistahaven.com for a property."""
    try:
        return logic.get_booking_link_logic(property, check_in, check_out)
    except UnknownPropertyError as e:
        return {"error": str(e)}


if __name__ == "__main__":
    if "--http" in sys.argv:
        import os
        port = int(os.environ.get("PORT", "8000"))
        for i, a in enumerate(sys.argv):
            if a == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
        # CORS so browser-based clients (e.g. a website chat preview) can
        # call the public endpoint. The API is read-only and unauthenticated
        # by design, so this exposes nothing new.
        from starlette.middleware.cors import CORSMiddleware

        app = mcp.http_app()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["POST", "GET", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["mcp-session-id"],
        )
        import uvicorn

        # 0.0.0.0 so the host (Render/Fly/etc.) can route public traffic in.
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        mcp.run()
