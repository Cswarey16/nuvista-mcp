# NuVista Haven MCP server ("AI front desk")

Model Context Protocol server that lets AI assistants answer, from live data:
- what NuVista Haven properties exist → `search_properties`
- what's free on given dates → `check_availability` (Hospitable calendars)
- what's the price → `get_quote` (nightly rates × nights + cleaning fee)
- where to book direct → `get_booking_link` (nuvistahaven.com)

## Security model

- **Read-only by construction.** `hospitable_client.py` exposes exactly one
  HTTP verb (GET) against an allow-list of read paths (`/user`,
  `/properties`, `/reservations`). There are no POST/PUT/PATCH/DELETE
  methods anywhere — even though the token may carry write scopes, this
  code cannot mutate anything in Hospitable.
- **Token handling.** The Hospitable Personal Access Token is read ONLY
  from the `HOSPITABLE_API_TOKEN` environment variable. It is never
  hardcoded, never logged, never written to disk.

## Setup

```bash
cd ~/workspace/nuvista-mcp
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## Run

```bash
# local testing (stdio)
HOSPITABLE_API_TOKEN=<token> ./venv/bin/python server.py

# public hosting (Streamable HTTP)
HOSPITABLE_API_TOKEN=<token> ./venv/bin/python server.py --http --port 8000
```

## Tests (mocked, no token needed)

```bash
./venv/bin/python test_server.py
```

## One-time: map Hospitable property IDs

`properties.py` holds the 12 canonical properties with best-effort
Hospitable name guesses (7 strong, 5 guesses — see `guess_confidence`).
With a live token, run the matcher and confirm each mapping by hand,
then fill in `hospitable_id` per property:

```bash
HOSPITABLE_API_TOKEN=<token> ./venv/bin/python - <<'EOF'
import sys; sys.path.insert(0, '.')
from hospitable_client import HospitableClient
from logic import build_id_mapping
import json
print(json.dumps(build_id_mapping(HospitableClient()), indent=2))
EOF
```

Entries with `"needs_human_confirm": true` must be verified before use —
`check_availability`/`get_quote` refuse to run for unmapped properties.

## Known API gaps / assumptions (verify against live API)

1. **Calendar query params**: `get_calendar` sends `start_date`/`end_date`
   (the Hospitable convention used by `/reservations`). If the endpoint
   ignores them, availability windows may be wrong — verify on first live run.
2. **Cleaning fee**: not part of the calendar day object. `get_quote`
   probes the property record for common fee shapes; if absent, the total
   is explicitly marked `total_is_partial_estimate: true` — never silently zero.
3. **Booking-link date params**: date pre-fill via query string on
   nuvistahaven.com is unverified, so `get_booking_link` returns the plain
   property URL (no fabricated params).
4. **Reservations cross-check**: `list_reservations` is implemented but the
   calendar is the source of truth; reservations are not currently consulted.

## Files

- `server.py` — FastMCP server, 4 tools, stdio + Streamable HTTP
- `logic.py` — tool logic (testable without MCP)
- `hospitable_client.py` — GET-only Hospitable Public API v2 client
- `properties.py` — canonical 12-property registry + Hospitable mapping
- `test_server.py` — mock-based tests
