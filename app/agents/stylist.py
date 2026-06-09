"""
stylist.py
----------
Advanced Stylist Agent for Drape Fashion AI.

Provides outfit recommendations based on:
  - Body shape classification
  - Occasion (casual, formal, party, work, date)
  - Season (spring, summer, autumn, winter)
  - Color tone preference (warm, cool, neutral)
  - Budget tier (budget, mid, luxury)

Returns ranked outfits with confidence scores, color palettes,
accessory pairings, and styling tips.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Literal, Optional


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

BodyShape = Literal["Pear", "Hourglass", "Rectangle", "Inverted Triangle", "Apple"]
Occasion  = Literal["casual", "formal", "party", "work", "date"]
Season    = Literal["spring", "summer", "autumn", "winter"]
ColorTone = Literal["warm", "cool", "neutral"]
Budget    = Literal["budget", "mid", "luxury"]


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class OutfitRecommendation:
    name: str
    description: str
    occasion_tags: list[Occasion]
    season_tags: list[Season]
    color_palette: list[str]
    accessories: list[str]
    styling_tips: list[str]
    confidence_score: float          # 0.0 – 1.0
    price_tier: Budget
    brand_suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "occasions": self.occasion_tags,
            "seasons": self.season_tags,
            "color_palette": self.color_palette,
            "accessories": self.accessories,
            "styling_tips": self.styling_tips,
            "confidence_score": round(self.confidence_score, 2),
            "price_tier": self.price_tier,
            "brand_suggestions": self.brand_suggestions,
        }


@dataclass
class StylistResponse:
    body_shape: BodyShape
    occasion: Occasion
    season: Season
    top_picks: list[OutfitRecommendation]
    general_tips: list[str]
    avoid_list: list[str]

    def to_dict(self) -> dict:
        return {
            "body_shape": self.body_shape,
            "occasion": self.occasion,
            "season": self.season,
            "top_picks": [o.to_dict() for o in self.top_picks],
            "general_tips": self.general_tips,
            "avoid_list": self.avoid_list,
        }


# ---------------------------------------------------------------------------
# Master outfit catalogue (body-shape → outfits)
# ---------------------------------------------------------------------------

_CATALOGUE: dict[BodyShape, list[OutfitRecommendation]] = {

    # ── Pear ──────────────────────────────────────────────────────────────
    "Pear": [
        OutfitRecommendation(
            name="A-line Midi Dress",
            description="Flares gracefully from the waist, balancing wider hips.",
            occasion_tags=["casual", "date", "party"],
            season_tags=["spring", "summer"],
            color_palette=["Blush Pink", "Ivory", "Soft Lavender"],
            accessories=["Delicate gold necklace", "Block-heel sandals", "Structured tote"],
            styling_tips=[
                "Choose a bold-print or bright top to draw eyes upward.",
                "Opt for darker shades on the bottom half.",
                "A belted waist emphasizes your natural hourglass potential.",
            ],
            confidence_score=0.95,
            price_tier="mid",
            brand_suggestions=["Anthropologie", "ASOS", "Reformation"],
        ),
        OutfitRecommendation(
            name="Fit-and-Flare Cocktail Dress",
            description="Fitted bodice that flares at the hips — a pear's best friend.",
            occasion_tags=["party", "date", "formal"],
            season_tags=["autumn", "winter"],
            color_palette=["Deep Burgundy", "Forest Green", "Midnight Navy"],
            accessories=["Statement earrings", "Pointed-toe heels", "Clutch bag"],
            styling_tips=[
                "Keep embellishments on the neckline to draw attention upward.",
                "Avoid heavy pleating at the hip.",
            ],
            confidence_score=0.92,
            price_tier="mid",
            brand_suggestions=["BCBGMAXAZRIA", "Phase Eight", "Ted Baker"],
        ),
        OutfitRecommendation(
            name="Off-Shoulder Blouse + Wide-Leg Trousers",
            description="Broadens the shoulder line to balance the hip-heavy silhouette.",
            occasion_tags=["work", "casual"],
            season_tags=["spring", "summer", "autumn"],
            color_palette=["Crisp White", "Camel", "Terracotta"],
            accessories=["Hoop earrings", "Loafers", "Leather belt"],
            styling_tips=[
                "Tuck in the blouse fully to highlight the waist.",
                "Choose trousers in a muted tone to minimise the lower half.",
            ],
            confidence_score=0.88,
            price_tier="budget",
            brand_suggestions=["Zara", "H&M", "Mango"],
        ),
        OutfitRecommendation(
            name="Wrap Dress",
            description="Creates a V-neckline and ties at the waist — incredibly flattering.",
            occasion_tags=["casual", "date", "work"],
            season_tags=["spring", "summer"],
            color_palette=["Sage Green", "Dusty Rose", "Cobalt Blue"],
            accessories=["Dainty bracelet", "Wedge sandals", "Mini crossbody bag"],
            styling_tips=[
                "Floral or geometric prints work beautifully in this silhouette.",
                "Layer with a denim jacket for a casual day look.",
            ],
            confidence_score=0.90,
            price_tier="budget",
            brand_suggestions=["Diane von Furstenberg", "Whistles", "& Other Stories"],
        ),
    ],

    # ── Hourglass ─────────────────────────────────────────────────────────
    "Hourglass": [
        OutfitRecommendation(
            name="Bodycon Midi Dress",
            description="Contours every curve and celebrates the balanced silhouette.",
            occasion_tags=["party", "date"],
            season_tags=["spring", "summer", "autumn"],
            color_palette=["Classic Black", "Crimson Red", "Champagne Gold"],
            accessories=["Strappy heels", "Clutch", "Drop earrings"],
            styling_tips=[
                "Opt for jersey or bandage fabric for structure.",
                "A slit adds movement without losing the silhouette.",
            ],
            confidence_score=0.97,
            price_tier="mid",
            brand_suggestions=["Hervé Léger", "Reiss", "Karen Millen"],
        ),
        OutfitRecommendation(
            name="Belted Trench Coat Outfit",
            description="A cinched trench over tailored trousers highlights the waist.",
            occasion_tags=["work", "formal", "casual"],
            season_tags=["autumn", "winter", "spring"],
            color_palette=["Camel", "Warm Beige", "Chocolate Brown"],
            accessories=["Leather ankle boots", "Silk scarf", "Structured handbag"],
            styling_tips=[
                "Always belt the trench — even loosely — to define the waist.",
                "Tuck in a fitted turtleneck underneath for polish.",
            ],
            confidence_score=0.93,
            price_tier="mid",
            brand_suggestions=["Burberry", "Max Mara", "AllSaints"],
        ),
        OutfitRecommendation(
            name="High-Waist Jeans + Fitted Crop Top",
            description="The classic duo that frames an hourglass perfectly.",
            occasion_tags=["casual", "date"],
            season_tags=["spring", "summer"],
            color_palette=["Denim Blue", "White", "Coral"],
            accessories=["Sneakers or heeled mules", "Simple gold chain", "Mini bag"],
            styling_tips=[
                "Go for a straight-leg or slim-fit jean — avoid low-rise.",
                "A crop top ends right at the high waist for maximum effect.",
            ],
            confidence_score=0.91,
            price_tier="budget",
            brand_suggestions=["Levi's", "Topshop", "AGOLDE"],
        ),
    ],

    # ── Rectangle ─────────────────────────────────────────────────────────
    "Rectangle": [
        OutfitRecommendation(
            name="Ruffle-Detail Dress",
            description="Ruffles and layers create the illusion of curves.",
            occasion_tags=["party", "casual", "date"],
            season_tags=["spring", "summer"],
            color_palette=["Pastel Yellow", "Baby Blue", "Peach"],
            accessories=["Platform sandals", "Layered necklaces", "Woven bag"],
            styling_tips=[
                "Look for ruffles at the bust or hips to add volume.",
                "A peplum hem is your best friend.",
            ],
            confidence_score=0.89,
            price_tier="budget",
            brand_suggestions=["Free People", "Zara", "Shein Studio"],
        ),
        OutfitRecommendation(
            name="Layered Co-ord Set",
            description="Mixing textures and layers creates the depth of a curvier figure.",
            occasion_tags=["casual", "work"],
            season_tags=["autumn", "winter"],
            color_palette=["Mustard Yellow", "Rust Orange", "Olive"],
            accessories=["Chunky belt", "Knee-high boots", "Oversized tote"],
            styling_tips=[
                "Use a thick belt to carve out a waist.",
                "Mixing prints adds visual interest and dimension.",
            ],
            confidence_score=0.85,
            price_tier="mid",
            brand_suggestions=["& Other Stories", "Cos", "Whistles"],
        ),
        OutfitRecommendation(
            name="Blazer + Straight Trouser Power Suit",
            description="Structured suiting elongates and adds definition.",
            occasion_tags=["formal", "work"],
            season_tags=["autumn", "winter", "spring"],
            color_palette=["Charcoal", "Slate Grey", "Powder Blue"],
            accessories=["Pointed-toe heels", "Minimal watch", "Envelope clutch"],
            styling_tips=[
                "Opt for a slightly oversized blazer for a trendy look.",
                "Pinstripes add vertical length.",
            ],
            confidence_score=0.87,
            price_tier="mid",
            brand_suggestions=["Arket", "Toteme", "Theory"],
        ),
    ],

    # ── Inverted Triangle ─────────────────────────────────────────────────
    "Inverted Triangle": [
        OutfitRecommendation(
            name="Flared Maxi Skirt + Simple Fitted Top",
            description="Volume on the bottom softens broad shoulders.",
            occasion_tags=["casual", "date", "party"],
            season_tags=["spring", "summer"],
            color_palette=["Teal", "Sand", "Terracotta"],
            accessories=["Espadrille wedges", "Pendant necklace", "Raffia bag"],
            styling_tips=[
                "Keep tops simple and avoid heavy shoulder detail.",
                "Opt for prints or embellishments on the skirt.",
            ],
            confidence_score=0.93,
            price_tier="budget",
            brand_suggestions=["Mango", "Zara", "Reformation"],
        ),
        OutfitRecommendation(
            name="Wide-Leg Palazzo Pants + Tucked Tank",
            description="Palazzo pants widen the hip line for a balanced look.",
            occasion_tags=["casual", "work", "date"],
            season_tags=["spring", "summer", "autumn"],
            color_palette=["Ivory", "Navy", "Warm Tan"],
            accessories=["Flat sandals", "Hoop earrings", "Belt bag"],
            styling_tips=[
                "Tuck in the tank to avoid adding bulk to the top.",
                "Choose fluid, draping fabrics for elegant movement.",
            ],
            confidence_score=0.90,
            price_tier="budget",
            brand_suggestions=["H&M", "ASOS", "John Lewis"],
        ),
    ],

    # ── Apple ─────────────────────────────────────────────────────────────
    "Apple": [
        OutfitRecommendation(
            name="Empire-Waist Tunic Dress",
            description="Gathers under the bust and flows freely — elegant and comfortable.",
            occasion_tags=["casual", "date", "party"],
            season_tags=["spring", "summer"],
            color_palette=["Burgundy", "Deep Teal", "Black"],
            accessories=["Flat sandals", "Long pendant", "Structured clutch"],
            styling_tips=[
                "Empire lines are your most flattering silhouette.",
                "V-necks elongate and slim the neckline area.",
            ],
            confidence_score=0.91,
            price_tier="mid",
            brand_suggestions=["Boden", "Seasalt", "M&S"],
        ),
        OutfitRecommendation(
            name="Dark-Wash Bootcut Jeans + Flowy Blouse",
            description="Dark denim slims the leg, flowy top skims the midsection.",
            occasion_tags=["casual", "work"],
            season_tags=["autumn", "winter", "spring"],
            color_palette=["Deep Indigo", "Crisp White", "Soft Grey"],
            accessories=["Block-heel boots", "Layer necklaces", "Leather tote"],
            styling_tips=[
                "Keep tops untucked or half-tucked to skim rather than cling.",
                "Avoid cropped tops unless layered with an open cardigan.",
            ],
            confidence_score=0.87,
            price_tier="budget",
            brand_suggestions=["J.Crew", "Gap", "Marks & Spencer"],
        ),
    ],
}


# ---------------------------------------------------------------------------
# General tips & avoid lists per body shape
# ---------------------------------------------------------------------------

_GENERAL_TIPS: dict[BodyShape, list[str]] = {
    "Pear":              ["Embrace bold necklines.", "Use bright colours above the waist.", "Structured shoulders balance the hips."],
    "Hourglass":         ["Always define the waist.", "Avoid boxy or shapeless cuts.", "Celebrate your proportions — you suit almost everything."],
    "Rectangle":         ["Create the illusion of curves with ruching and ruffles.", "Use belts to define a waist.", "Experiment with volume and layering."],
    "Inverted Triangle": ["Balance broad shoulders with volume below the waist.", "Skip shoulder pads and boat necks.", "Wide-leg trousers are your superpower."],
    "Apple":             ["Elongate the torso with V-necks and vertical lines.", "Empire-waist styles skim beautifully.", "Dark, continuous tones create a streamlined look."],
}

_AVOID_LIST: dict[BodyShape, list[str]] = {
    "Pear":              ["Pleated trousers", "Tight pencil skirts in bright colours", "Low-rise jeans"],
    "Hourglass":         ["Shapeless smocks", "Super-baggy trousers", "Boxy boyfriend blazers"],
    "Rectangle":         ["Straight-cut sack dresses", "Monochrome without a waist break", "Dropped-waist silhouettes"],
    "Inverted Triangle": ["Boat-neck or off-shoulder tops", "Shoulder-padded blazers", "Puff sleeves"],
    "Apple":             ["High-waist trousers with a tucked top", "Belted waists at the natural waist", "Clingy jersey on the torso"],
}


# ---------------------------------------------------------------------------
# Seasonal colour adjustments
# ---------------------------------------------------------------------------

_SEASONAL_PALETTE_BOOST: dict[Season, list[str]] = {
    "spring":  ["Blush", "Mint", "Lemon", "Lilac", "Sky Blue"],
    "summer":  ["Coral", "Aqua", "Hot Pink", "Sunshine Yellow", "White"],
    "autumn":  ["Rust", "Mustard", "Chocolate", "Forest Green", "Burgundy"],
    "winter":  ["Midnight Blue", "Crimson", "Emerald", "Charcoal", "Silver"],
}


# ---------------------------------------------------------------------------
# Main StylistAgent class
# ---------------------------------------------------------------------------

class StylistAgent:
    """
    Advanced styling agent.

    Usage
    -----
    agent = StylistAgent()
    response = agent.recommend(
        body_shape="Pear",
        occasion="party",
        season="winter",
        color_tone="cool",
        budget="mid",
        top_n=3,
    )
    print(response.to_dict())
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def recommend(
        self,
        body_shape: BodyShape,
        occasion: Occasion,
        season: Season,
        color_tone: ColorTone = "neutral",
        budget: Budget = "mid",
        top_n: int = 3,
    ) -> StylistResponse:
        """
        Return the top N outfit recommendations for the given profile.

        Parameters
        ----------
        body_shape  : Classified body shape string.
        occasion    : Target occasion.
        season      : Current or target season.
        color_tone  : User's preferred colour warmth.
        budget      : Price tier preference.
        top_n       : Maximum number of outfits to return (default 3).

        Returns
        -------
        StylistResponse dataclass with ranked picks.
        """
        if body_shape not in _CATALOGUE:
            raise ValueError(
                f"Unknown body shape '{body_shape}'. "
                f"Valid options: {list(_CATALOGUE.keys())}"
            )

        catalogue = _CATALOGUE[body_shape]

        # Step 1 – score every outfit for this request
        scored: list[tuple[float, OutfitRecommendation]] = []
        for outfit in catalogue:
            score = self._score_outfit(outfit, occasion, season, color_tone, budget)
            scored.append((score, outfit))

        # Step 2 – sort descending by adjusted score
        scored.sort(key=lambda x: x[0], reverse=True)

        # Step 3 – slice top_n and attach adjusted confidence
        top_picks: list[OutfitRecommendation] = []
        for rank, (score, outfit) in enumerate(scored[:top_n]):
            # Clone to avoid mutating the catalogue
            pick = OutfitRecommendation(
                name=outfit.name,
                description=outfit.description,
                occasion_tags=outfit.occasion_tags,
                season_tags=outfit.season_tags,
                color_palette=self._season_boosted_palette(outfit.color_palette, season),
                accessories=outfit.accessories,
                styling_tips=outfit.styling_tips,
                confidence_score=min(score, 1.0),
                price_tier=outfit.price_tier,
                brand_suggestions=outfit.brand_suggestions,
            )
            top_picks.append(pick)

        return StylistResponse(
            body_shape=body_shape,
            occasion=occasion,
            season=season,
            top_picks=top_picks,
            general_tips=_GENERAL_TIPS.get(body_shape, []),
            avoid_list=_AVOID_LIST.get(body_shape, []),
        )

    def get_all_shapes(self) -> list[str]:
        """Return all supported body shapes."""
        return list(_CATALOGUE.keys())

    def get_catalogue_size(self, body_shape: BodyShape) -> int:
        """Return number of outfits available for a given body shape."""
        return len(_CATALOGUE.get(body_shape, []))

    # ------------------------------------------------------------------ #
    # Internal scoring logic                                               #
    # ------------------------------------------------------------------ #

    def _score_outfit(
        self,
        outfit: OutfitRecommendation,
        occasion: Occasion,
        season: Season,
        color_tone: ColorTone,
        budget: Budget,
    ) -> float:
        score = outfit.confidence_score  # base

        # Occasion match (±0.15)
        if occasion in outfit.occasion_tags:
            score += 0.15
        else:
            score -= 0.10

        # Season match (±0.10)
        if season in outfit.season_tags:
            score += 0.10
        else:
            score -= 0.05

        # Budget match (±0.08)
        if outfit.price_tier == budget:
            score += 0.08
        elif self._budget_adjacent(outfit.price_tier, budget):
            score += 0.03
        else:
            score -= 0.05

        # Colour tone alignment (±0.05)
        score += self._color_tone_bonus(outfit.color_palette, color_tone)

        # Small random tie-breaker so the same score always shuffles pleasantly
        score += self._rng.uniform(0, 0.02)

        return score

    @staticmethod
    def _budget_adjacent(outfit_budget: Budget, requested: Budget) -> bool:
        tiers: list[Budget] = ["budget", "mid", "luxury"]
        try:
            diff = abs(tiers.index(outfit_budget) - tiers.index(requested))
            return diff == 1
        except ValueError:
            return False

    @staticmethod
    def _color_tone_bonus(palette: list[str], tone: ColorTone) -> float:
        warm_keywords = {"rust", "orange", "red", "warm", "coral", "camel", "terracotta", "gold", "mustard", "burgundy"}
        cool_keywords = {"blue", "navy", "mint", "lavender", "purple", "cool", "grey", "silver", "teal", "sage"}
        neutral_keywords = {"black", "white", "ivory", "beige", "nude", "cream", "sand", "charcoal"}

        palette_lower = " ".join(palette).lower()

        if tone == "warm":
            return 0.05 if any(w in palette_lower for w in warm_keywords) else 0.0
        elif tone == "cool":
            return 0.05 if any(w in palette_lower for w in cool_keywords) else 0.0
        else:  # neutral
            return 0.05 if any(w in palette_lower for w in neutral_keywords) else 0.0

    @staticmethod
    def _season_boosted_palette(palette: list[str], season: Season) -> list[str]:
        """Append one seasonally appropriate accent colour to the palette."""
        boosts = _SEASONAL_PALETTE_BOOST.get(season, [])
        if boosts:
            accent = boosts[hash(tuple(palette)) % len(boosts)]
            if accent not in palette:
                return palette + [f"{accent} (seasonal accent)"]
        return palette


# ---------------------------------------------------------------------------
# Convenience function (backward-compatible with simple usage)
# ---------------------------------------------------------------------------

def get_style_recommendations(
    body_shape: BodyShape,
    occasion: Occasion = "casual",
    season: Season = "spring",
) -> list[dict]:
    """
    Lightweight wrapper for quick, non-class usage.

    Returns a list of outfit dicts for the given body shape / occasion / season.
    """
    agent = StylistAgent()
    response = agent.recommend(body_shape=body_shape, occasion=occasion, season=season)
    return [pick.to_dict() for pick in response.top_picks]


# Alias — keeps main.py imports working
recommend_styles = get_style_recommendations