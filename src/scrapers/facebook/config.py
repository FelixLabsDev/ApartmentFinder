from __future__ import annotations

# ---------------------------------------------------------------------------
# Facebook Marketplace GraphQL API configuration
# ---------------------------------------------------------------------------

# GraphQL endpoint
GRAPHQL_URL = "https://www.facebook.com/api/graphql/"

# Marketplace listing page URL templates
MARKETPLACE_BASE_URL = "https://www.facebook.com/marketplace/{location_id}/propertyrentals/"
LISTING_URL_TEMPLATE = "https://www.facebook.com/marketplace/item/{listing_id}/"

# Known doc_id values for marketplace search queries.
# These are reverse-engineered from browser requests and may rotate over time.
# Multiple are listed so the scraper can try fallbacks.
GRAPHQL_DOC_IDS: list[str] = [
    "7829008030469734",
    "6453001778117254",
    "7110390322362492",
]

# Category ID for property rentals on Facebook Marketplace
PROPERTY_RENTAL_CATEGORY_ID = "798714733491569"

# ---------------------------------------------------------------------------
# Facebook Marketplace location IDs for Israeli cities
# These are extracted from marketplace URLs:
#   https://www.facebook.com/marketplace/<location_id>/propertyrentals/
# ---------------------------------------------------------------------------
LOCATION_IDS: dict[str, str] = {
    "tel-aviv": "110884905606138",
    "jerusalem": "110678868950682",
    "haifa": "112902008724498",
    "beer-sheva": "111775322171092",
    "netanya": "109622669057538",
    "rishon-lezion": "112481982097845",
    "petah-tikva": "105752366115674",
    "ashdod": "108131452544222",
    "herzliya": "107903829228927",
    "raanana": "111289202216277",
    "kfar-saba": "108022365878917",
    "rehovot": "115005278508694",
    "ramat-gan": "108227295863957",
    "bat-yam": "110586618963960",
    "holon": "104115342949579",
    "modiin": "116312541709670",
    "givatayim": "104637542901850",
}

# Default search radius in km
DEFAULT_RADIUS_KM = 10

# ---------------------------------------------------------------------------
# Required request headers to mimic a real browser session
# ---------------------------------------------------------------------------
GRAPHQL_HEADERS: dict[str, str] = {
    "Accept": "*/*",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://www.facebook.com",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "X-FB-Friendly-Name": "CometMarketplaceSearchContentContainerQuery",
    "X-FB-LSD": "",  # Filled at runtime from page token
}

# ---------------------------------------------------------------------------
# Field-name mapping from Facebook listing data → ListingCreate booleans
# Facebook uses attributes/tags on listings for property features
# ---------------------------------------------------------------------------
FEATURE_KEYWORDS: dict[str, str] = {
    "parking": "has_parking",
    "חניה": "has_parking",
    "מעלית": "has_elevator",
    "elevator": "has_elevator",
    "מרפסת": "has_balcony",
    "balcony": "has_balcony",
    "מיזוג": "has_air_conditioning",
    "air conditioning": "has_air_conditioning",
    "ממ\"ד": "has_mamad",
    "mamad": "has_mamad",
    "נגיש": "is_accessible",
    "accessible": "is_accessible",
    "מרוהט": "is_furnished",
    "furnished": "is_furnished",
    "סורגים": "has_bars",
    "bars": "has_bars",
    "מחסן": "has_storage",
    "storage": "has_storage",
    "חיות": "pet_friendly",
    "pet": "pet_friendly",
}
