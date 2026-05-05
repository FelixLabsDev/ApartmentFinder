from __future__ import annotations

from enum import StrEnum


class Source(StrEnum):
    YAD2 = "yad2"
    FACEBOOK = "facebook"
    TELEGRAM = "telegram"
    MADLAN = "madlan"


class PropertyType(StrEnum):
    APARTMENT = "apartment"
    HOUSE = "house"
    PENTHOUSE = "penthouse"
    GARDEN_APARTMENT = "garden_apartment"
    STUDIO = "studio"
    DUPLEX = "duplex"
    ROOF_APARTMENT = "roof_apartment"
    UNIT = "unit"
    OTHER = "other"


class Currency(StrEnum):
    ILS = "ILS"
    USD = "USD"
