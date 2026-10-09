"""Mock-based tests for the NuVista Haven MCP server.

No real API calls, no token needed. Run:
    ./venv/bin/python test_server.py
"""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx

import logic
from hospitable_client import HospitableAPIError, HospitableAuthError, HospitableClient
from properties import PROPERTIES, UnknownPropertyError, resolve_property

# ----------------------------------------------------------------------
# Mock API
# ----------------------------------------------------------------------
MOCK_UUIDS = {p["key"]: f"uuid-{i:02d}" for i, p in enumerate(PROPERTIES)}
for p in PROPERTIES:
    p["hospitable_id"] = MOCK_UUIDS[p["key"]]  # test-local ID mapping

recorded: list[tuple[str, str]] = []
calendar_overrides: dict = {}


def _mock_days(start: str, end: str) -> list[dict]:
    d0 = date.fromisoformat(start) - timedelta(days=2)
    d1 = date.fromisoformat(end) + timedelta(days=2)
    days = []
    d = d0
    while d <= d1:
        iso = d.isoformat()
        ov = calendar_overrides.get(iso, {})
        days.append(
            {
                "date": iso,
                "day": d.strftime("%A").upper(),
                "min_stay": ov.get("min_stay", 2),
                "status": {
                    "reason": ov.get("reason", "AVAILABLE"),
                    "available": ov.get("available", True),
                },
                "price": {
                    "amount": ov.get("amount", 15000),
                    "currency": "USD",
                    "formatted": "$150.00",
                },
                "closed_for_checkin": ov.get("closed_for_checkin", False),
                "closed_for_checkout": ov.get("closed_for_checkout", False),
            }
        )
        d += timedelta(days=1)
    return days


def _handler(request: httpx.Request) -> httpx.Response:
    recorded.append((request.method, request.url.path))
    path = request.url.path
    if path == "/v2/user":
        return httpx.Response(200, json={"data": {"id": 1}})
    if path == "/v2/properties":
        data = [
            {
                "id": MOCK_UUIDS[p["key"]],
                "name": p["hospitable_guess"],
                "public_name": p["hospitable_guess"],
            }
            for p in PROPERTIES
        ]
        return httpx.Response(200, json={"data": data, "meta": {"last_page": 1}})
    if path.startswith("/v2/properties/") and path.endswith("/calendar"):
        params = dict(request.url.params)
        return httpx.Response(
            200, json={"data": _mock_days(params["start_date"], params["end_date"])}
        )
    if path.startswith("/v2/properties/"):
        return httpx.Response(200, json={"data": {"id": "x", "name": "X"}})
    if path == "/v2/reservations":
        return httpx.Response(200, json={"data": []})
    return httpx.Response(404, json={"message": "not found"})


def _client() -> HospitableClient:
    return HospitableClient(token="dummy-test-token", transport=httpx.MockTransport(_handler))


def _reset():
    recorded.clear()
    calendar_overrides.clear()


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_search_all():
    _reset()
    res = logic.search_properties_logic()
    assert len(res) == 12, f"expected 12, got {len(res)}"
    assert all(r["url"].startswith("https://nuvistahaven.com/properties/") for r in res)


def test_search_query():
    _reset()
    res = logic.search_properties_logic(query="farm")
    names = {r["name"] for r in res}
    assert names == {
        "Thunder Manor Farmstead Retreat",
        "Cozy Farmland Retreat Minutes to Sight & Sound",
        "Stay on a Farm · Buggy Rides, Goats & Chickens",
        "Lancaster Family Farmhouse Haven",
        "Private Tiny Home Surrounded by Farmland w/ Hot Tub",
    }, names


def test_search_area():
    _reset()
    assert len(logic.search_properties_logic(area="sarasota")) == 1
    assert len(logic.search_properties_logic(area="lancaster")) == 5


def test_search_min_sleeps():
    _reset()
    res = logic.search_properties_logic(min_sleeps=8)
    assert {r["name"] for r in res} == {
        "Pickleball Court & Game Room Retreat",
        "Lancaster Family Farmhouse Haven",
        "Stay on a Farm \u00b7 Buggy Rides, Goats & Chickens",
    }


def test_availability_free():
    _reset()
    r = logic.check_availability_logic(_client(), "pickleball", "2027-03-10", "2027-03-13")
    assert r["available"] is True, r
    assert r["nights"] == 3


def test_availability_blocked_night():
    _reset()
    calendar_overrides["2027-03-11"] = {"available": False, "reason": "BOOKED"}
    r = logic.check_availability_logic(_client(), "pickleball", "2027-03-10", "2027-03-13")
    assert r["available"] is False, r
    assert any("2027-03-11" in x for x in r["reasons"]), r["reasons"]


def test_availability_min_stay():
    _reset()
    calendar_overrides["2027-03-10"] = {"min_stay": 5}
    r = logic.check_availability_logic(_client(), "pickleball", "2027-03-10", "2027-03-13")
    assert r["available"] is False, r
    assert any("minimum stay" in x for x in r["reasons"]), r["reasons"]


def test_availability_closed_checkin():
    _reset()
    calendar_overrides["2027-03-10"] = {"closed_for_checkin": True}
    r = logic.check_availability_logic(_client(), "pickleball", "2027-03-10", "2027-03-13")
    assert r["available"] is False, r


def test_quote_math_and_partial_total():
    _reset()
    r = logic.get_quote_logic(_client(), "thunder manor farmstead", "2027-04-01", "2027-04-04")
    assert r["nightly_subtotal"] == 450.0, r
    assert r["cleaning_fee"] is None, r
    assert r["total"] == 450.0, r
    assert r["total_is_partial_estimate"] is True, r
    assert "NOT exposed" in r["cleaning_fee_note"], r


def test_quote_unavailable_dates():
    _reset()
    calendar_overrides["2027-04-02"] = {"available": False, "reason": "BOOKED"}
    r = logic.get_quote_logic(_client(), "thunder manor farmstead", "2027-04-01", "2027-04-04")
    assert "error" in r and "Not available" in r["error"], r


def test_cleaning_fee_shapes():
    assert logic._find_cleaning_fee_cents({"cleaning_fee": {"amount": 25000}}) == 25000
    assert logic._find_cleaning_fee_cents({"fees": [{"type": "cleaning", "amount": 20000}]}) == 20000
    assert logic._find_cleaning_fee_cents({}) is None
    assert logic._find_cleaning_fee_cents({"fees": "n/a"}) is None


def test_booking_link():
    _reset()
    r = logic.get_booking_link_logic("thunder manor farmstead", "2027-04-01", "2027-04-04")
    assert r["booking_url"] == "https://nuvistahaven.com/properties/thunder-manor-farmstead-retreat/", r
    assert "?" not in r["booking_url"]  # no fabricated query params


def test_unknown_property():
    _reset()
    try:
        resolve_property("nonexistent xyz")
        raise AssertionError("should have raised")
    except UnknownPropertyError:
        pass


def test_client_is_get_only():
    _reset()
    for verb in ("post", "put", "patch", "delete", "head", "options"):
        assert not hasattr(HospitableClient, verb), f"HospitableClient must not have .{verb}()"
    c = _client()
    c.check_auth()
    c.list_properties()
    assert recorded, "expected some requests"
    assert all(m == "GET" for m, _ in recorded), recorded


def test_property_list_cached():
    _reset()
    c = _client()
    c.list_properties()
    c.list_properties()
    calls = [p for m, p in recorded if p == "/v2/properties"]
    assert len(calls) == 1, f"expected 1 API call, got {len(calls)}"


def test_auth_missing_raises():
    _reset()
    saved = os.environ.pop("HOSPITABLE_API_TOKEN", None)
    try:
        try:
            HospitableClient()
            raise AssertionError("should have raised")
        except HospitableAuthError:
            pass
    finally:
        if saved is not None:
            os.environ["HOSPITABLE_API_TOKEN"] = saved


def test_allowlist_blocks_unknown_paths():
    _reset()
    c = _client()
    try:
        c._get("/admin/wipe-everything")
        raise AssertionError("should have raised")
    except HospitableAPIError:
        pass


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]


if __name__ == "__main__":
    failed = 0
    for t in TESTS:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(TESTS) - failed}/{len(TESTS)} passed")
    sys.exit(1 if failed else 0)
