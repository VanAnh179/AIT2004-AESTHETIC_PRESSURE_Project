"""
compute_ap_scores.py
--------------------
Tinh diem AP (Aesthetic Pressure) tu du lieu tuong tac 3 nguon:
- Facebook  : reactions + share
- Instagram : reactions
- Shopee    : stars (quy doi tu avg_stars * total_review)

Output:
    data/processed/interaction_ap_scores.csv
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler


@dataclass(frozen=True)
class APWeights:
    """Trong so AP, uu tien Facebook reactions va share."""

    reactions: float = 1.00
    share: float = 1.20
    stars: float = 0.85
    angry: float = 1.10


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

FB_CSV = RAW_DIR / "facebook" / "raw_fb_data.csv"
IG_CSV = RAW_DIR / "instagram" / "raw_ig_data.csv"
SHOPEE_CSV = RAW_DIR / "shopee" / "banner_summary.csv"

OUTPUT_CSV = PROCESSED_DIR / "interaction_ap_scores.csv"


def safe_numeric(series: pd.Series) -> pd.Series:
    """Convert ve float, loi se thanh 0."""
    return pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)


def nan_series(df: pd.DataFrame) -> pd.Series:
    return pd.Series(np.nan, index=df.index, dtype="float64")


def numeric_from_candidates(df: pd.DataFrame, candidates: list[str]) -> pd.Series:
    for col in candidates:
        if col in df.columns:
            return safe_numeric(df[col])
    return nan_series(df)


def load_facebook(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    reactions = numeric_from_candidates(df, ["total_react", "reactions"])
    share = numeric_from_candidates(df, ["share_count", "share"])
    react_angry = numeric_from_candidates(df, ["react_angry", "angry_count"])
    out = pd.DataFrame(
        {
            "img_id": df["img_id"].astype(str),
            "source": "facebook",
            "fanpage": df.get("fanpage", "").astype(str),
            "reactions": reactions,
            "share": share,
            "react_angry": react_angry,
            "avg_stars": nan_series(df),
            "total_review": nan_series(df),
        }
    )
    return out


def load_instagram(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    reactions = numeric_from_candidates(df, ["total_react", "reactions"])
    out = pd.DataFrame(
        {
            "img_id": df["img_id"].astype(str),
            "source": "instagram",
            "fanpage": df.get("fanpage", "").astype(str),
            "reactions": reactions,
            "share": nan_series(df),
            "react_angry": nan_series(df),
            "avg_stars": nan_series(df),
            "total_review": nan_series(df),
        }
    )
    return out


def load_shopee(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    avg_stars = numeric_from_candidates(df, ["avg_stars", "rating_avg", "avg_rating"])
    total_review = numeric_from_candidates(
        df, ["total_review", "review_count", "rating_count"]
    )
    out = pd.DataFrame(
        {
            "img_id": df["image_id"].astype(str),
            "source": "shopee",
            "fanpage": df.get("shop", "").astype(str),
            "reactions": nan_series(df),
            "share": nan_series(df),
            "react_angry": nan_series(df),
            "avg_stars": avg_stars,
            "total_review": total_review,
        }
    )
    return out


def compute_ap(df: pd.DataFrame, weights: APWeights) -> pd.DataFrame:
    """
    Cong thuc AP:
        stars_equiv = total_review * (avg_stars / 5)
        diem_ap_luc_tho =
            w_r * log1p(reactions) +
            w_s * log1p(share) +
            w_t * log1p(stars_equiv) -
            w_a * log1p(react_angry)

    Dung log1p de giam chenh lech gia tri lon nho giua cac nguon.
    """
    out = df.copy()
    out["stars_equivalent"] = out["total_review"] * (out["avg_stars"] / 5.0)

    reactions_value = out["reactions"].fillna(0.0)
    share_value = out["share"].fillna(0.0)
    react_angry_value = out["react_angry"].fillna(0.0)
    stars_equiv_value = out["stars_equivalent"].fillna(0.0)

    out["angry_ratio"] = np.where(
        reactions_value > 0,
        react_angry_value / reactions_value,
        0.0,
    )

    # Source-aware weighting:
    # - Chi tinh cac thanh phan co that o tung nguon.
    # - Chia cho tong trong so active de tranh nhiu khi metric khong ton tai.
    #   (vd Instagram khong co share, Shopee khong co reactions/share)
    has_reactions = out["reactions"].notna().astype(float)
    has_share = out["share"].notna().astype(float)
    has_stars = (out["avg_stars"].notna() & out["total_review"].notna()).astype(float)
    has_angry = out["react_angry"].notna().astype(float)

    positive_weight_sum = (
        has_reactions * weights.reactions
        + has_share * weights.share
        + has_stars * weights.stars
    )
    negative_weight_sum = has_angry * weights.angry

    positive_score = (
        has_reactions * weights.reactions * np.log1p(reactions_value)
        + has_share * weights.share * np.log1p(share_value)
        + has_stars * weights.stars * np.log1p(stars_equiv_value)
    )
    negative_score = has_angry * weights.angry * np.log1p(react_angry_value)

    out["ap_positive_normalized"] = np.where(
        positive_weight_sum > 0,
        positive_score / positive_weight_sum,
        0.0,
    )
    out["ap_negative_normalized"] = np.where(
        negative_weight_sum > 0,
        negative_score / negative_weight_sum,
        0.0,
    )
    out["diem_ap_luc_tho"] = out["ap_positive_normalized"] - out["ap_negative_normalized"]
    out["ap_sentiment_adjusted"] = out["diem_ap_luc_tho"] * (1.0 - out["angry_ratio"])

    # Task 3: Khoi tao va goi MinMaxScaler tu scikit-learn
    scaler_raw = MinMaxScaler(feature_range=(0, 1))
    scaler_sent = MinMaxScaler(feature_range=(0, 1))
    out["diem_ap_luc_chuan_hoa"] = scaler_raw.fit_transform(out[["diem_ap_luc_tho"]])
    out["ap_sentiment_adjusted_chuan_hoa"] = scaler_sent.fit_transform(
        out[["ap_sentiment_adjusted"]]
    )

    out["ap_formula"] = (
        "AP_raw = source_aware_norm(pos) - source_aware_norm(neg), "
        "pos={reactions,share,stars_equiv}, neg={react_angry}"
    )
    return out


def main(output_csv: Path) -> None:
    fb = load_facebook(FB_CSV)
    ig = load_instagram(IG_CSV)
    shopee = load_shopee(SHOPEE_CSV)

    merged = pd.concat([fb, ig, shopee], ignore_index=True)
    weights = APWeights()
    scored = compute_ap(merged, weights)

    keep_cols = [
        "img_id",
        "source",
        "fanpage",
        "reactions",
        "share",
        "react_angry",
        "angry_ratio",
        "avg_stars",
        "total_review",
        "stars_equivalent",
        "ap_positive_normalized",
        "ap_negative_normalized",
        "diem_ap_luc_tho",
        "diem_ap_luc_chuan_hoa",
        "ap_sentiment_adjusted",
        "ap_sentiment_adjusted_chuan_hoa",
        "ap_formula",
    ]
    scored = scored[keep_cols].sort_values(["source", "img_id"]).reset_index(drop=True)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    scored.to_csv(output_csv, index=False, encoding="utf-8-sig", float_format="%.6f")

    print("=" * 70)
    print(f"Done. Exported AP scores: {output_csv}")
    print(f"Rows: {len(scored)} | Columns: {len(scored.columns)}")
    print(
        "Source rows: "
        f"facebook={len(scored[scored['source']=='facebook'])}, "
        f"instagram={len(scored[scored['source']=='instagram'])}, "
        f"shopee={len(scored[scored['source']=='shopee'])}"
    )
    print("=" * 70)
    print(scored.head(8).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tinh diem AP tho + chuan hoa MinMax")
    parser.add_argument("--output", type=Path, default=OUTPUT_CSV)
    args = parser.parse_args()
    main(args.output)
