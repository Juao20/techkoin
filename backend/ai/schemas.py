"""Pydantic schemas: the only shapes the language model is allowed to answer with."""

from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["smartphone", "tablet", "laptop", "desktop"]
Condition = Literal["new_sealed", "new_open", "refurbished", "used"]
Grade = Literal["A", "B", "C"]
Usage = Literal[
    "office", "study", "dev", "gaming", "creative", "battery", "everyday", "photo", "business"
]
Keyboard = Literal["azerty", "qwerty", "qwertz"]
Tier = Literal["cheap", "mid", "premium"]


class SearchIntent(BaseModel):
    """F1: a free text request turned into the filters the search already understands."""

    category: Category | None = None
    brands: list[str] = Field(default_factory=list)
    price_min: int | None = Field(default=None, ge=0)
    price_max: int | None = Field(default=None, ge=0)
    city: str | None = None
    condition: list[Condition] = Field(default_factory=list)
    grade: list[Grade] = Field(default_factory=list)
    ram_min: int | None = Field(default=None, ge=0, le=256)
    storage_min: int | None = Field(default=None, ge=0, le=16384)
    usage: Usage | None = None
    keyboard: Keyboard | None = None
    tier: Tier | None = None  # « pas cher », « milieu de gamme », « premium »
    other_terms: list[str] = Field(default_factory=list, max_length=6)
    confidence: float = Field(default=0.0, ge=0, le=1)


class ListingText(BaseModel):
    """F2: a title, a description and three highlights written from the listing's own data."""

    title: str = Field(max_length=70)
    description: str
    highlights: list[str] = Field(min_length=3, max_length=3)


class VoiceFields(BaseModel):
    """F3: what the seller said, as form fields to validate one by one."""

    model_text: str | None = None
    category: Category | None = None
    storage_gb: int | None = Field(default=None, ge=0, le=16384)
    ram_gb: int | None = Field(default=None, ge=0, le=256)
    battery_health_pct: int | None = Field(default=None, ge=1, le=100)
    condition_type: Condition | None = None
    grade: Grade | None = None
    accessories: list[str] = Field(default_factory=list)
    color: str | None = None
    price_fcfa: int | None = Field(default=None, ge=0)
    defects: str | None = None


class AssistantAnswer(BaseModel):
    """F4: an answer drawn only from the listing, or an admission that the data is missing."""

    answer: str
    information_missing: bool = False
    suggested_seller_question: str | None = None


class CompareVerdict(BaseModel):
    class PerListing(BaseModel):
        listing_id: int
        best_for: str
        verdict_line: str

    winner_listing_id: int
    summary: str
    reasons: list[str] = Field(max_length=4)
    warnings: list[str] = Field(default_factory=list, max_length=3)
    per_listing: list[PerListing]


class RiskSignal(BaseModel):
    """F6: extra risk points suggested by reading the listing text. Never blocks on its own."""

    risk: int = Field(ge=0, le=25)
    signals: list[str] = Field(default_factory=list, max_length=5)
