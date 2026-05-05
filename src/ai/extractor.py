from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field

from src.config import get_settings

logger = logging.getLogger(__name__)

# Fields that should be highlighted red when missing (core + details)
REQUIRED_FIELDS = [
    "price",
    "rooms",
    "city",
    "area_sqm",
    "floor",
    "street",
    "neighborhood",
    "entry_date",
]

EXTRACTION_PROMPT = """\
You are analyzing a Facebook Marketplace apartment rental listing. Extract structured information from the listing text below.

Return a JSON object with these fields (use null for any field you cannot determine):

{
  "price": <number or null>,
  "currency": "ILS" or "USD",
  "rooms": <number or null, e.g. 2.5>,
  "city": <string or null>,
  "neighborhood": <string or null>,
  "street": <string or null>,
  "house_number": <string or null>,
  "floor": <integer or null>,
  "total_floors": <integer or null>,
  "area_sqm": <number or null>,
  "entry_date": <string "YYYY-MM-DD" or null>,
  "description": <string summary or null>,
  "property_type": <one of "apartment","house","penthouse","garden_apartment","studio","duplex","roof_apartment","unit","other" or null>,
  "has_parking": <boolean or null>,
  "has_elevator": <boolean or null>,
  "has_balcony": <boolean or null>,
  "has_air_conditioning": <boolean or null>,
  "has_mamad": <boolean or null>,
  "is_accessible": <boolean or null>,
  "is_furnished": <boolean or null>,
  "has_bars": <boolean or null>,
  "has_storage": <boolean or null>,
  "pet_friendly": <boolean or null>,
  "contact_name": <string or null>,
  "contact_phone": <string or null>
}

Notes:
- Prices in Israel are typically in ILS (shekels). If the price is in dollars, set currency to "USD".
- "mamad" is a reinforced safe room required in Israeli apartments.
- If the text is in Hebrew, still extract the information and transliterate city/street names to English.
- Only include information you can confidently extract from the text. Use null for anything uncertain.

Listing text:
"""


@dataclass
class ExtractionResult:
    extracted_fields: dict
    guessed_fields: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)


async def extract_listing_fields(page_text: str, title: str = "") -> ExtractionResult:
    """Use LiteLLM to extract structured listing fields from raw page text."""
    import litellm

    settings = get_settings()

    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key

    full_text = f"Title: {title}\n\n{page_text}" if title else page_text

    try:
        response = await litellm.acompletion(
            model=settings.ai_model,
            messages=[
                {"role": "user", "content": EXTRACTION_PROMPT + full_text[:4000]}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        content = response.choices[0].message.content
        extracted = json.loads(content)
    except Exception as exc:
        logger.error("AI extraction failed: %s", exc)
        return ExtractionResult(
            extracted_fields={},
            guessed_fields=[],
            missing_required=list(REQUIRED_FIELDS),
        )

    # Determine which required fields are present vs missing
    guessed_fields = []
    missing_required = []

    for f in REQUIRED_FIELDS:
        val = extracted.get(f)
        if val is not None:
            guessed_fields.append(f)
        else:
            missing_required.append(f)

    return ExtractionResult(
        extracted_fields=extracted,
        guessed_fields=guessed_fields,
        missing_required=missing_required,
    )
