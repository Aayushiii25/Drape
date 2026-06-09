"""
services/recommendation.py
---------------------------
Advanced RecommendationService for Drape Fashion AI.

Orchestrates body-shape classification, outfit scoring, colour palette
selection, and accessory pairing into a single rich RecommendationResult.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from agents.body_shape import classify_body_shape
from agents.stylist import StylistAgent
from models.schemas import (
    Recommendation,
    OutfitDetail,
    BodyAnalysis,
    StylingProfile,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _current_season() -> str:
    """Detect the approximate season from the current month."""
    month = datetime.now().month
    if month in (3, 4, 5):
        return "spring"
    elif month in (6, 7, 8):
        return "summer"
    elif month in (9, 10, 11):
        return "autumn"
    else:
        return "winter"


def _bmi_category(weight_kg: float, height_cm: float) -> str:
    if height_cm <= 0 or weight_kg <= 0:
        return "unknown"
    bmi = weight_kg / ((height_cm / 100) ** 2)
    if bmi < 18.5:
        return "underweight"
    elif bmi < 25:
        return "normal"
    elif bmi < 30:
        return "overweight"
    else:
        return "obese"


def _waist_to_hip_ratio(waist: float, hip: float) -> float:
    if hip == 0:
        return 0.0
    return round(waist / hip, 3)


def _infer_color_tone(color_pref: Optional[str]) -> str:
    warm = {"red", "orange", "yellow", "warm", "coral", "peach", "gold", "brown", "rust"}
    cool = {"blue", "purple", "green", "cool", "mint", "lavender", "navy", "grey", "silver"}
    if color_pref and color_pref.lower() in warm:
        return "warm"
    elif color_pref and color_pref.lower() in cool:
        return "cool"
    return "neutral"


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------

class RecommendationService:
    """
    Full-pipeline recommendation engine.

    Usage
    -----
    service = RecommendationService()

    result = service.generate_recommendation(
        bust=34, waist=28, hip=42,
        height=165, weight=60,
        occasion="party",
        color_preference="cool",
        budget="mid",
        top_n=3,
    )

    print(result.model_dump())
    """

    def __init__(self) -> None:
        self._stylist = StylistAgent(seed=42)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def generate_recommendation(
        self,
        bust: float,
        waist: float,
        hip: float,
        height: float = 0.0,
        weight: float = 0.0,
        occasion: str = "casual",
        color_preference: Optional[str] = None,
        budget: str = "mid",
        top_n: int = 3,
    ) -> Recommendation:
        """
        Generate a full fashion recommendation for the given body measurements.

        Parameters
        ----------
        bust, waist, hip      : Measurements in inches.
        height                : Height in cm (optional, used for BMI/proportion).
        weight                : Weight in kg (optional, used for BMI).
        occasion              : Target styling occasion.
        color_preference      : Raw colour string (e.g. "blue", "warm").
        budget                : "budget" | "mid" | "luxury".
        top_n                 : Number of outfit picks to return.

        Returns
        -------
        Recommendation Pydantic model.
        """
        # ── 1. Body analysis ──────────────────────────────────────────
        body_type   = classify_body_shape(bust=bust, waist=waist, hip=hip)
        whr         = _waist_to_hip_ratio(waist, hip)
        bmi_cat     = _bmi_category(weight, height)
        color_tone  = _infer_color_tone(color_preference)
        season      = _current_season()

        body_analysis = BodyAnalysis(
            body_type=body_type,
            bust=bust,
            waist=waist,
            hip=hip,
            waist_to_hip_ratio=whr,
            bmi_category=bmi_cat,
            height_cm=height if height else None,
            weight_kg=weight if weight else None,
        )

        # ── 2. Styling profile ────────────────────────────────────────
        styling_profile = StylingProfile(
            occasion=occasion,
            season=season,
            color_tone=color_tone,
            budget=budget,
            color_preference=color_preference,
        )

        # ── 3. Stylist agent → ranked outfits ────────────────────────
        valid_occasions = {"casual", "formal", "party", "work", "date"}
        valid_budgets   = {"budget", "mid", "luxury"}

        safe_occasion = occasion if occasion in valid_occasions else "casual"
        safe_budget   = budget   if budget   in valid_budgets   else "mid"

        stylist_response = self._stylist.recommend(
            body_shape=body_type,
            occasion=safe_occasion,
            season=season,
            color_tone=color_tone,
            budget=safe_budget,
            top_n=top_n,
        )

        # ── 4. Map to OutfitDetail schema ─────────────────────────────
        outfit_details: list[OutfitDetail] = []
        for rank, pick in enumerate(stylist_response.top_picks, start=1):
            outfit_details.append(
                OutfitDetail(
                    rank=rank,
                    name=pick.name,
                    description=pick.description,
                    occasions=pick.occasion_tags,
                    seasons=pick.season_tags,
                    color_palette=pick.color_palette,
                    accessories=pick.accessories,
                    styling_tips=pick.styling_tips,
                    confidence_score=pick.confidence_score,
                    price_tier=pick.price_tier,
                    brand_suggestions=pick.brand_suggestions,
                )
            )

        # ── 5. Assemble final recommendation ─────────────────────────
        return Recommendation(
            body_analysis=body_analysis,
            styling_profile=styling_profile,
            outfit_picks=outfit_details,
            general_tips=stylist_response.general_tips,
            avoid_list=stylist_response.avoid_list,
            generated_at=datetime.now().isoformat(),
        )

    # ------------------------------------------------------------------ #
    # Convenience helpers                                                  #
    # ------------------------------------------------------------------ #

    def quick_recommend(self, bust: float, waist: float, hip: float) -> dict:
        """Minimal wrapper — returns a plain dict for quick scripts."""
        result = self.generate_recommendation(bust=bust, waist=waist, hip=hip)
        return result.model_dump()
