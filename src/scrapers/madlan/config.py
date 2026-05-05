from __future__ import annotations

# Madlan search page base URL
SEARCH_BASE_URL = "https://www.madlan.co.il/listings"

# Listing detail URL template
LISTING_URL_TEMPLATE = "https://www.madlan.co.il/listings/{listing_id}"

# Hebrew -> PropertyType mapping (Madlan uses Hebrew property type labels)
PROPERTY_TYPE_MAP: dict[str, str] = {
    "דירה": "apartment",
    "דירת גן": "garden_apartment",
    "בית פרטי": "house",
    "קוטג'": "house",
    "פנטהאוז": "penthouse",
    "סטודיו": "studio",
    "לופט": "studio",
    "דופלקס": "duplex",
    "דירת גג": "roof_apartment",
    "יחידת דיור": "unit",
    "מיני פנטהאוז": "penthouse",
}

# City name mappings: internal slug -> Madlan Hebrew search term
# Madlan uses Hebrew city names in the URL `term` parameter
CITY_SEARCH_TERMS: dict[str, str] = {
    "tel-aviv": "תל-אביב-יפו",
    "jerusalem": "ירושלים",
    "haifa": "חיפה",
    "beer-sheva": "באר-שבע",
    "netanya": "נתניה",
    "rishon-lezion": "ראשון-לציון",
    "petah-tikva": "פתח-תקווה",
    "ashdod": "אשדוד",
    "herzliya": "הרצליה",
    "raanana": "רעננה",
    "kfar-saba": "כפר-סבא",
    "rehovot": "רחובות",
    "modiin": "מודיעין-מכבים-רעות",
    "givatayim": "גבעתיים",
    "ramat-gan": "רמת-גן",
    "bat-yam": "בת-ים",
    "holon": "חולון",
    "ashkelon": "אשקלון",
    "hadera": "חדרה",
    "bnei-brak": "בני-ברק",
    "lod": "לוד",
    "ramla": "רמלה",
    "nahariya": "נהריה",
    "kiryat-ata": "קריית-אתא",
    "rosh-haayin": "ראש-העין",
    "hod-hasharon": "הוד-השרון",
    "yavne": "יבנה",
    "even-yehuda": "אבן-יהודה",
}

# City bounding boxes (south-west lat/lng, north-east lat/lng)
# Format: "min_lng,min_lat,max_lng,max_lat"
CITY_BBOXES: dict[str, str] = {
    "tel-aviv": "34.74200,32.02900,34.81500,32.14600",
    "jerusalem": "35.12900,31.73100,35.26900,31.83500",
    "haifa": "34.94700,32.77300,35.04200,32.83500",
    "beer-sheva": "34.73700,31.22300,34.84800,31.28900",
    "netanya": "34.83100,32.30100,34.88200,32.35200",
    "rishon-lezion": "34.73500,31.94100,34.81100,31.99700",
    "petah-tikva": "34.85100,32.07100,34.91700,32.11500",
    "ashdod": "34.61200,31.77200,34.67400,31.82100",
    "herzliya": "34.76800,32.14900,34.82700,32.17600",
    "raanana": "34.85300,32.17100,34.88800,32.19700",
    "kfar-saba": "34.88200,32.16400,34.92400,32.19300",
    "rehovot": "34.78300,31.87800,34.82600,31.91300",
    "modiin": "34.98200,31.87200,35.03400,31.92600",
    "givatayim": "34.80700,32.06300,34.82200,32.07600",
    "ramat-gan": "34.79700,32.06000,34.83100,32.10200",
    "bat-yam": "34.73200,32.00700,34.76600,32.03300",
    "holon": "34.76200,32.00100,34.80600,32.03100",
}
