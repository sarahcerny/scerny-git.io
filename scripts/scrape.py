"""Merge raw Census sales and Open-Meteo weather into one analysis dataset.

Run from the repository root:
    uv run python scripts/scrape.py

Reads data/raw/census_raw.csv and data/raw/weather_raw.csv (left unchanged)
and writes data/processed/retail_weather.csv with one row per month per
store category.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

CENSUS_RAW = Path("data/raw/census_raw.csv")
WEATHER_RAW = Path("data/raw/weather_raw.csv")
OUTPUT = Path("data/processed/retail_weather.csv")

# Check these labels against the Census documentation before publishing.
CATEGORY_NAMES = {
    448: "Clothing",
    451: "Sporting goods, hobby, books",
    444: "Building materials and garden",
    452: "General merchandise",
    445: "Food and beverage",
}
HOLIDAY_MONTHS = [11, 12]  # November and December shopping season
EXPECTED_ROWS = 600

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def clean_census(raw: pd.DataFrame) -> pd.DataFrame:
    """Keep the needed Census columns and add year, month, and a readable name."""
    df = raw[["time", "category_code", "cell_value"]].copy()
    df["year"] = df["time"].str[:4].astype(int)
    df["month"] = df["time"].str[5:7].astype(int)
    df["category"] = df["category_code"].map(CATEGORY_NAMES)
    df = df.rename(columns={"cell_value": "sales_millions"})
    return df[["year", "month", "category", "sales_millions"]]


def monthly_weather(raw: pd.DataFrame) -> pd.DataFrame:
    """Collapse daily weather into one row per month."""
    df = raw.copy()
    df["year"] = df["time"].str[:4].astype(int)
    df["month"] = df["time"].str[5:7].astype(int)
    monthly = df.groupby(["year", "month"], as_index=False).agg(
        avg_temp_f=("temperature_2m_mean", "mean"),
        total_precip_in=("precipitation_sum", "sum"),
    )
    monthly["avg_temp_f"] = monthly["avg_temp_f"].round(1)
    monthly["total_precip_in"] = monthly["total_precip_in"].round(2)
    return monthly


def validate(df: pd.DataFrame) -> None:
    """Fail loudly if the merged dataset is not what we expect."""
    assert len(df) == EXPECTED_ROWS, f"Expected {EXPECTED_ROWS} rows, got {len(df)}"
    assert not df.isna().any().any(), f"Missing values:\n{df.isna().sum()}"
    assert not df.duplicated(["year", "month", "category"]).any(), "Duplicate rows"
    assert df["category"].nunique() == 5, "Expected 5 categories"
    counts = df.groupby("category").size()
    assert (counts == 120).all(), f"Month counts are off:\n{counts}"
    assert df["month"].between(1, 12).all(), "Month out of range"
    assert (df["sales_millions"] > 0).all(), "Non-positive sales"
    print("All checks passed")


def main() -> None:
    census = clean_census(pd.read_csv(CENSUS_RAW))
    weather = monthly_weather(pd.read_csv(WEATHER_RAW))

    # how="left" keeps every sales row. The validation catches any weather gap.
    df = census.merge(weather, on=["year", "month"], how="left")
    df["holiday_flag"] = df["month"].isin(HOLIDAY_MONTHS).astype(int)
    df = df.sort_values(["category", "year", "month"]).reset_index(drop=True)

    validate(df)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT, index=False)
    logging.info("Saved %s rows and %s columns to %s", len(df), df.shape[1], OUTPUT)
    print(df.head())


if __name__ == "__main__":
    main()