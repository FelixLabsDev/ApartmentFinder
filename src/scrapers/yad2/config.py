from __future__ import annotations

# Yad2 API endpoint (JSON, no anti-bot)
FEED_API_URL = "https://www.yad2.co.il/api/pre-load/getFeedIndex/realestate/rent"

# HTML page URL (has anti-bot protection)
HTML_BASE_URL = "https://www.yad2.co.il/realestate/rent"

# Anti-bot detection marker
ANTIBOT_MARKER = "Are you for real"

# Listing detail URL template
LISTING_URL_TEMPLATE = "https://www.yad2.co.il/realestate/item/{token}"

# Hebrew -> PropertyType mapping
PROPERTY_TYPE_MAP: dict[str, str] = {
    "דירה": "apartment",
    "דירת גן": "garden_apartment",
    "בית פרטי/קוטג'": "house",
    "קוטג'": "house",
    "פנטהאוז": "penthouse",
    "סטודיו/לופט": "studio",
    "דופלקס": "duplex",
    "דירת גג": "roof_apartment",
    "יחידת דיור": "unit",
}

# Internal property type -> Yad2 API property code
PROPERTY_TYPE_CODES: dict[str, str] = {
    "apartment": "1",
    "garden_apartment": "3",
    "house": "11",
    "penthouse": "5",
    "studio": "6",
    "duplex": "7",
    "roof_apartment": "39",
    "unit": "25",
}

# Feature text fields -> boolean feature flags
FEATURE_TEXT_FIELDS: dict[str, str] = {
    "Parking_text": "has_parking",
    "Elevator_text": "has_elevator",
    "Porch_text": "has_balcony",        # "אין" = no balcony
    "AirConditioner_text": "has_air_conditioning",
    "mamad_text": "has_mamad",
    "handicapped_text": "is_accessible",
    "Furniture_text": "is_furnished",
    "Grating_text": "has_bars",
    "storeroom_text": "has_storage",
    "PetsInHouse_text": "pet_friendly",
}

# Yad2 city codes (most common Israeli cities)
CITY_CODES: dict[str, str] = {
    "tel-aviv": "5000",
    "jerusalem": "3000",
    "haifa": "4000",
    "beer-sheva": "7900",
    "netanya": "7400",
    "rishon-lezion": "8300",
    "petah-tikva": "7900",
    "ashdod": "70",
    "herzliya": "6400",
    "raanana": "8600",
    "kfar-saba": "6300",
    "rehovot": "8400",
    "modiin": "1247",
    "givatayim": "6300",
    "ramat-gan": "8600",
    "bat-yam": "2100",
    "holon": "6600",
}
