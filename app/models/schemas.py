"""
models/schemas.py
-----------------
Pydantic data models for Drape Fashion AI.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------

class UserProfile(BaseModel):
    bust: float
    waist: float
    hip: float

    height: float = 0.0
    weight: float = 0.0

    budget: str = "mid"   # "budget" | "mid" | "luxury"

    color: Optional[str] = None
    occasion: str = "casual"


# ---------------------------------------------------------------------------
# Product (from collectors)
# ---------------------------------------------------------------------------

class Product(BaseModel):
    id: int
    name: str
    price: float

    image: Optional[str] = None
    brand: Optional[str] = None
    color: Optional[str] = None
    category: Optional[str] = None


# ---------------------------------------------------------------------------
# Recommendation sub-models
# ---------------------------------------------------------------------------

class BodyAnalysis(BaseModel):
    """Derived body metrics from raw measurements."""
    body_type: str
    bust: float
    waist: float
    hip: float
    waist_to_hip_ratio: float
    bmi_category: str
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None


class StylingProfile(BaseModel):
    """Context used to drive style selection."""
    occasion: str
    season: str
    color_tone: str               # "warm" | "cool" | "neutral"
    budget: str                   # "budget" | "mid" | "luxury"
    color_preference: Optional[str] = None


class OutfitDetail(BaseModel):
    """One ranked outfit recommendation with full metadata."""
    rank: int
    name: str
    description: str
    occasions: list[str]
    seasons: list[str]
    color_palette: list[str]
    accessories: list[str]
    styling_tips: list[str]
    confidence_score: float = Field(ge=0.0, le=1.0)
    price_tier: str
    brand_suggestions: list[str] = []


# ---------------------------------------------------------------------------
# Top-level Recommendation response
# ---------------------------------------------------------------------------

class Recommendation(BaseModel):
    """Full recommendation response returned by RecommendationService."""
    body_analysis: BodyAnalysis
    styling_profile: StylingProfile
    outfit_picks: list[OutfitDetail]
    general_tips: list[str]
    avoid_list: list[str]
    generated_at: str

    # backward-compat helpers so old code using .recommended_styles still works
    @property
    def recommended_styles(self) -> list[str]:
        return [o.name for o in self.outfit_picks]

    @property
    def body_type(self) -> str:
        return self.body_analysis.body_type
