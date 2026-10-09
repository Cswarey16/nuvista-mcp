"""Tool logic for the NuVista Haven MCP server.

Pure functions taking a HospitableClient — no MCP machinery here, so this
is unit-testable with a mocked client.
"""

from __future__ import annotations

from datetime import date, timedelta

from hospitable_client import HospitableClient, parse_api_date
from properties import PROPERTIES, UnknownPropertyError, resolve_property


# ----------------------------------------------------------------------
# search_properties
# ----------------------------------------------------------------------
def search_properties_logic(
    query: str = "", area: str = "", min_sleeps: int = 0
) -> list[dict]:
    """Filter the 12 canonical properties. No API call needed."""
    q = (query or "").lower().strip()
    a = (area or "").lower().strip()
    out = []
    for p in PROPERTIES:
        if q and q not in p["name"].lower() and q not in p["key"].replace("-", " ") and q not in p["area"].lower():
            continue
        if a and a not in p["area"].lower():
            continue
        if min_sleeps and (p["sleeps"] or 0) < min_sleeps:
            continue
        out.append(
            {
                "name": p["name"],
                "area": p["area"],
                "url": p["url"],
                "sleeps": p["sleeps"],
                "bedrooms": p["bedrooms"],
            }
        )
    return out


# ----------------------------------------------------------------------
# check_availability
# ----------------------------------------------------------------------
def _nights(check_in: date, check_out: date) -> list[str]:
    days = []
    d = check_in
    while d < check_out:
        days.append(d.isoformat())
        d += timedelta(days=1)
    return days


def check_availability_logic(
    client: HospitableClient, prop_ref: str, check_in: str, check_out: str
) -> dict:
    """True/false availability for a date range, from the Hospitable calendar.

    Rules enforced: every night must exist in the calendar response and be
    marked available; arrival day must allow check-in; departure day must
    allow check-out (where the calendar reports it); min_stay respected.
    """
    prop = resolve_property(prop_ref)
    if not prop.get("hospitable_id"):
        return {
            "property": prop["name"],
            "available": None,
            "error": (
                "Hospitable property ID is not mapped yet for this listing. "
                "Run the ID-mapping step (see README) with a live API token, "
                "then retry."
            ),
        }

    ci = parse_api_date(check_in)
    co = parse_api_date(check_out)
    if co <= ci:
        return {"property": prop["name"], "available": None,
                "error": "check_out must be after check_in (YYYY-MM-DD)."}
    if ci < date.today():
        return {"property": prop["name"], "available": None,
                "error": "check_in is in the past."}

    nights = _nights(ci, co)
    days = {d.get("date"): d for d in client.get_calendar(prop["hospitable_id"], check_in, check_out)}

    reasons: list[str] = []
    for n in nights:
        day = days.get(n)
        if day is None:
            reasons.append(f"{n}: no calendar data returned for this date")
            continue
        status = day.get("status", {}) or {}
        if not status.get("available"):
            reasons.append(f"{n}: not available ({status.get('reason', 'no reason given')})")

    first = days.get(check_in)
    if first and first.get("closed_for_checkin"):
        reasons.append(f"{check_in}: closed for check-in")
    last = days.get(check_out)
    if last and last.get("closed_for_checkout"):
        reasons.append(f"{check_out}: closed for check-out")

    min_stays = [d.get("min_stay") or 0 for d in (days.get(n) for n in nights) if d]
    if min_stays and max(min_stays) > len(nights):
        reasons.append(
            f"minimum stay is {max(min_stays)} nights, requested {len(nights)}"
        )

    return {
        "property": prop["name"],
        "check_in": check_in,
        "check_out": check_out,
        "nights": len(nights),
        "available": not reasons,
        "reasons": reasons,
    }


# ----------------------------------------------------------------------
# get_quote
# ----------------------------------------------------------------------
def _find_cleaning_fee_cents(property_payload: dict) -> int | None:
    """Look for a cleaning fee in the property record.

    The Hospitable calendar day object carries nightly price only; the
    cleaning fee is NOT part of it. This probes common shapes of the
    property payload — returns None when the API does not expose it.
    """
    if not isinstance(property_payload, dict):
        return None
    for key in ("cleaning_fee", "cleaningFee", "cleaning_fee_cents"):
        val = property_payload.get(key)
        if isinstance(val, dict) and isinstance(val.get("amount"), (int, float)):
            return int(val["amount"])
        if isinstance(val, (int, float)):
            return int(val)
    fees = property_payload.get("fees") or property_payload.get("extra_fees") or []
    if isinstance(fees, list):
        for fee in fees:
            if not isinstance(fee, dict):
                continue
            label = str(fee.get("type", "") + fee.get("name", "") + fee.get("label", "")).lower()
            if "clean" in label and isinstance(fee.get("amount"), (int, float)):
                return int(fee["amount"])
    return None


def get_quote_logic(
    client: HospitableClient,
    prop_ref: str,
    check_in: str,
    check_out: str,
    guests: int = 2,
) -> dict:
    """Nightly rate x nights + cleaning fee.

    Nightly rates come from the Hospitable calendar (amounts are in cents).
    If the API does not expose the cleaning fee, it is reported as unknown
    and the total is explicitly marked as a partial estimate — never silently
    treated as zero.
    """
    avail = check_availability_logic(client, prop_ref, check_in, check_out)
    if avail.get("error"):
        return {"property": avail["property"], "error": avail["error"]}
    if not avail["available"]:
        return {
            "property": avail["property"],
            "check_in": check_in,
            "check_out": check_out,
            "error": "Not available for these dates: " + "; ".join(avail["reasons"]),
        }

    prop = resolve_property(prop_ref)
    days = {d.get("date"): d for d in client.get_calendar(prop["hospitable_id"], check_in, check_out)}
    nightly: list[dict] = []
    for n in _nights(parse_api_date(check_in), parse_api_date(check_out)):
        price = (days[n].get("price") or {})
        cents = price.get("amount")
        if cents is None:
            return {
                "property": prop["name"],
                "error": f"No nightly price returned for {n}; cannot quote.",
            }
        nightly.append({"date": n, "amount_cents": int(cents)})

    subtotal_cents = sum(n["amount_cents"] for n in nightly)
    currency = ((days[nightly[0]["date"]].get("price") or {}).get("currency")) or "USD"

    cleaning_cents = _find_cleaning_fee_cents(client.get_property(prop["hospitable_id"]))
    total_cents = subtotal_cents + (cleaning_cents or 0)

    def dollars(c: int) -> float:
        return round(c / 100, 2)

    return {
        "property": prop["name"],
        "check_in": check_in,
        "check_out": check_out,
        "nights": len(nightly),
        "guests": guests,
        "nightly_rates": [
            {"date": n["date"], "amount": dollars(n["amount_cents"])} for n in nightly
        ],
        "nightly_subtotal": dollars(subtotal_cents),
        "cleaning_fee": dollars(cleaning_cents) if cleaning_cents is not None else None,
        "cleaning_fee_note": (
            "included from Hospitable property record"
            if cleaning_cents is not None
            else "NOT exposed by the Hospitable API — add the property's cleaning fee manually"
        ),
        "total": dollars(total_cents),
        "total_is_partial_estimate": cleaning_cents is None,
        "currency": currency,
    }


# ----------------------------------------------------------------------
# get_booking_link
# ----------------------------------------------------------------------
# Date query-param support on nuvistahaven.com property pages: UNVERIFIED
# (2026-10-09). Until confirmed, return the plain property URL — never
# fabricate query params the site may ignore.
def get_booking_link_logic(
    prop_ref: str, check_in: str = "", check_out: str = ""
) -> dict:
    prop = resolve_property(prop_ref)
    return {
        "property": prop["name"],
        "booking_url": prop["url"],
        "note": (
            "Direct booking page for this property. Date pre-fill via query "
            "params is not confirmed on nuvistahaven.com, so dates are not "
            "appended — the guest picks dates on the page."
            if (check_in or check_out)
            else "Direct booking page for this property."
        ),
    }


# ----------------------------------------------------------------------
# ID mapping helper (run once with a live token; see README)
# ----------------------------------------------------------------------
def build_id_mapping(client: HospitableClient) -> list[dict]:
    """Match Hospitable API properties to the 12 canonical ones.

    Matches on public_name (fallback: name), case-insensitive. Returns a
    report of strong/weak/unmatched entries — the caller writes the
    confirmed UUIDs into properties.py.
    """
    api_props = client.list_properties()
    report = []
    for p in PROPERTIES:
        best, best_score = None, 0
        for ap in api_props:
            for field in ("public_name", "name"):
                cand = str(ap.get(field) or "")
                if not cand:
                    continue
                # crude overlap score on significant words
                pw = {w for w in p["name"].lower().replace("|", " ").split() if len(w) > 3}
                cw = {w for w in cand.lower().replace("|", " ").split() if len(w) > 3}
                score = len(pw & cw)
                if score > best_score:
                    best, best_score = ap, score
        report.append(
            {
                "canonical": p["name"],
                "guess": p["hospitable_guess"],
                "api_match": (best.get("public_name") or best.get("name")) if best else None,
                "api_id": best.get("id") if best else None,
                "word_overlap": best_score,
                "needs_human_confirm": best_score < 2,
            }
        )
    return report
