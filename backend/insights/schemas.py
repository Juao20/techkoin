"""Shapes the language model may answer with for the Pro analyses (spec 10.3)."""

from typing import Literal

from pydantic import BaseModel, Field


class DemandAdvice(BaseModel):
    """P1: purchase recommendations written from the radar table."""

    recommendations: list[str] = Field(min_length=1, max_length=3)


class ListingNote(BaseModel):
    listing_id: int
    note: str


class ListingNotes(BaseModel):
    """P2 and P3: one short explanation per listing."""

    items: list[ListingNote]


class ReportText(BaseModel):
    """P4: the weekly summary and the three priority actions."""

    summary: str
    actions: list[str] = Field(min_length=1, max_length=3)


class CompetitionAction(BaseModel):
    kind: Literal["price", "warranty", "photos", "accessories", "description"]
    text: str


class CompetitionAnswer(BaseModel):
    """P7: why a buyer would pick the competing listings, and what to do about it."""

    why_them: str
    actions: list[CompetitionAction] = Field(min_length=1, max_length=4)
