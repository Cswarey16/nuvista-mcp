"""Canonical registry of the 12 live NuVista Haven properties.

Source of truth for names/areas/URLs: https://nuvistahaven.com/llms.txt
(read 2026-10-09). Sleeps/bedrooms only where stated on the site — unknown
values are None, never guessed.

HOSPITABLE MAPPING (UNVERIFIED — fill in from the API):
  Each entry has `hospitable_id` (the API UUID, None until resolved) and
  `hospitable_guess` (best-effort name match against the 15 Hospitable
  listings, marked strong/guess). Run `python -m nuvista_mcp.map_ids`
  (see README) with a live token to resolve IDs via public_name matching.
"""

PROPERTIES: list[dict] = [
    {
        "key": "upper-woods-cabin",
        "name": "Upper Woods Cabin | 34-Acre Retreat",
        "area": "Honesdale, PA (Poconos)",
        "url": "https://nuvistahaven.com/properties/upper-woods-cabin-34-acre-retreat-honesdale-pa/",
        "sleeps": None,
        "bedrooms": 3,
        "hospitable_guess": "Upper Woods Cabin | 34-Acre Retreat, Honesdale PA",
        "guess_confidence": "strong",
        "hospitable_id": "52a3fdd3-cced-4f2d-af3d-a6cdfeb8c5db",
    },
    {
        "key": "pickleball-retreat",
        "name": "Pickleball Court & Game Room Retreat",
        "area": "Newport, PA (Perry County)",
        "url": "https://nuvistahaven.com/properties/pickleball-court-game-room-retreat-newport-pa/",
        "sleeps": 9,
        "bedrooms": 3,
        "hospitable_guess": "Pickleball Court + Game Room Retreat | Fire Pit & Big Deck in Newport, PA",
        "guess_confidence": "strong",
        "hospitable_id": "d47f5109-b230-4d7d-8068-c35ff2702b06",
    },
    {
        "key": "sunny-pinecraft",
        "name": "Sunny Pinecraft Retreat",
        "area": "Sarasota, FL (Pinecraft)",
        "url": "https://nuvistahaven.com/properties/sunny-pinecraft-retreat/",
        "sleeps": 4,
        "bedrooms": 2,
        "hospitable_guess": "Sunny Pinecraft Retreat",
        "guess_confidence": "strong",
        "hospitable_id": "9211ef14-dee8-49ba-a27f-761e93f1f43c",
    },
    {
        "key": "farmhouse-haven",
        "name": "Lancaster Family Farmhouse Haven",
        "area": "Bird in Hand, PA (Lancaster County)",
        "url": "https://nuvistahaven.com/properties/lancaster-family-farmhouse-haven/",
        "sleeps": 11,
        "bedrooms": None,
        "hospitable_guess": "The Farmhouse",
        "guess_confidence": "guess",
        "hospitable_id": "bb5bdd41-f98c-46b4-bcd5-57f31a6daf04",
    },
    {
        "key": "thunder-manor",
        "name": "Thunder Manor Farmstead Retreat",
        "area": "Lakewood, PA (Wayne County)",
        "url": "https://nuvistahaven.com/properties/thunder-manor-farmstead-retreat/",
        "sleeps": None,
        "bedrooms": None,
        "hospitable_guess": "Thunder Manor Farmstead Retreat",
        "guess_confidence": "strong",
        "hospitable_id": "0d16e901-216b-4237-8dc5-cfc063a0762d",
    },
    {
        "key": "pondview-apartment",
        "name": "Pondview Apartment at Thunder Manor",
        "area": "Lakewood, PA (Wayne County)",
        "url": "https://nuvistahaven.com/properties/pondview-apartment-at-thunder-manor/",
        "sleeps": None,
        "bedrooms": None,
        "hospitable_guess": "Pondview Apartment at Thunder Manor",
        "guess_confidence": "strong",
        "hospitable_id": "21a228e6-e80b-4d75-999a-e6f1c44921c5",
    },
    {
        "key": "kayak-haven",
        "name": "Kayak Haven at the Lakefront",
        "area": "Pine Grove, PA (Schuylkill County)",
        "url": "https://nuvistahaven.com/properties/kayak-haven-at-the-lakefront/",
        "sleeps": None,
        "bedrooms": None,
        "hospitable_guess": "Sunrise Lake",
        "guess_confidence": "guess",
        "hospitable_id": "05e2057b-338b-4d50-baec-ca4a58a726af",
    },
    {
        "key": "cozy-farmland",
        "name": "Cozy Farmland Retreat Minutes to Sight & Sound",
        "area": "Ronks, PA (Lancaster County)",
        "url": "https://nuvistahaven.com/properties/cozy-farmland-retreat-minutes-to-sight-sound/",
        "sleeps": None,
        "bedrooms": None,
        "hospitable_guess": "Cozy Farmland Retreat Minutes to Sight & Sound",
        "guess_confidence": "strong",
        "hospitable_id": "e7280133-dd12-4660-9ed1-c8e4d007ffad",
    },
    {
        "key": "tiny-home",
        "name": "Private Tiny Home Surrounded by Farmland w/ Hot Tub",
        "area": "Gordonville, PA (Lancaster County)",
        "url": "https://nuvistahaven.com/properties/private-tiny-home-surrounded-by-farmland-w-hottub/",
        "sleeps": None,
        "bedrooms": 1,
        "hospitable_guess": "The Berry House",
        "guess_confidence": "guess",
        "hospitable_id": "d1ddd9ad-3884-43f9-8473-c41dfedbc5b9",
    },
    {
        "key": "stay-on-a-farm",
        "name": "Stay on a Farm \u00b7 Buggy Rides, Goats & Chickens",
        "area": "Bird in Hand, PA (Lancaster County)",
        "url": "https://nuvistahaven.com/properties/stay-on-a-farm-%C2%B7-buggy-rides-goats-chickens/",
        "sleeps": 8,
        "bedrooms": 4,
        "hospitable_guess": "The Farmstead Hideaway",
        "guess_confidence": "guess",
        "hospitable_id": "c1ee6b56-cdc4-4aeb-81d8-da875b27c74f",
    },
    {
        "key": "calamus-run",
        "name": "Calamus Run Meadow Retreat",
        "area": "Ronks, PA (Lancaster County)",
        "url": "https://nuvistahaven.com/properties/calamus-run-meadow-retreat/",
        "sleeps": None,
        "bedrooms": None,
        "hospitable_guess": "Calamus Run Meadow Retreat",
        "guess_confidence": "strong",
        "hospitable_id": "bac8e2b0-ebd8-4ad6-ac36-d12f3f61c7c7",
    },
    {
        "key": "parkesburg-townhome",
        "name": "Cozy Parkesburg Townhome Retreat",
        "area": "Parkesburg, PA",
        "url": "https://nuvistahaven.com/properties/cozy-parkesburg-townhome-retreat/",
        "sleeps": None,
        "bedrooms": None,
        "hospitable_guess": "Main Street Haven",
        "guess_confidence": "guess",
        "hospitable_id": "9d61d3ff-15ff-4512-a86d-0372638c62dc",
    },
]


class UnknownPropertyError(Exception):
    pass


def resolve_property(ref: str) -> dict:
    """Match a user-supplied name/key to a canonical property.

    Case-insensitive substring match against key, name, and area.
    Raises UnknownPropertyError listing valid names on ambiguity/no-match.
    """
    q = (ref or "").strip().lower()
    if not q:
        raise UnknownPropertyError("Empty property reference.")
    exact = [p for p in PROPERTIES if p["key"] == q]
    if exact:
        return exact[0]
    hits = [p for p in PROPERTIES if q in p["name"].lower() or q in p["key"].replace("-", " ")]
    if len(hits) == 1:
        return hits[0]
    names = ", ".join(p["name"] for p in PROPERTIES)
    if not hits:
        raise UnknownPropertyError(f"No property matches {ref!r}. Choose from: {names}")
    raise UnknownPropertyError(f"{ref!r} is ambiguous ({', '.join(h['name'] for h in hits)}). Be more specific.")


def property_needs_hospitable_id(prop: dict) -> bool:
    return not prop.get("hospitable_id")
