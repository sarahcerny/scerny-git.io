"""Collect daily weather for Salt Lake City from the Open-Meteo archive API.

Run from the repository root:
    uv run python scripts/fetch_weather.py

Pulls daily mean temperature and total precipitation for January 2016 through
December 2025 and saves the values before any cleaning or monthly averaging.
No API key is needed (free for non-commercial use, data licensed CC BY 4.0).
Weather data by Open-Meteo.com
"""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
OUTPUT = Path("data/raw/weather_raw.csv")
USER_AGENT = (
    "STAT386-StudentProject/1.0 "
    "(educational data collection; limited requests; sarahmcerny@byu.edu)"
)
TIMEOUT_SECONDS = 30

LATITUDE = 40.76  # Salt Lake City
LONGITUDE = -111.89
START = "2016-01-01"
END = "2025-12-31"
EXPECTED_DAYS = 3653  # 10 years, including leap days in 2016, 2020, 2024

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def fetch_json(session: requests.Session, params: dict) -> dict:
    """Fetch JSON and fail clearly, including the server's message."""
    try:
        response = session.get(BASE_URL, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as exc:
        raise RuntimeError(
            f"Request failed with status {exc.response.status_code}: "
            f"{exc.response.text[:300]}"
        ) from None
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError(f"Request failed: {type(exc).__name__}") from None


def fetch_weather(session: requests.Session) -> pd.DataFrame:
    """Pull daily mean temperature and precipitation for the full date range."""
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": START,
        "end_date": END,
        "daily": "temperature_2m_mean,precipitation_sum",
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch",
        "timezone": "America/Denver",
    }
    data = fetch_json(session, params)
    if "daily" not in data:
        raise RuntimeError(f"Unexpected response. Keys: {list(data.keys())}")
    return pd.DataFrame(data["daily"])


def validate(df: pd.DataFrame) -> None:
    """Fail loudly if the pull is not what we expect."""
    assert len(df) == EXPECTED_DAYS, f"Expected {EXPECTED_DAYS} days, got {len(df)}"
    assert not df["time"].duplicated().any(), "Duplicate dates"
    assert df["time"].min() == START and df["time"].max() == END, "Date range is off"
    missing = df[["temperature_2m_mean", "precipitation_sum"]].isna().sum()
    print("Missing values per column:\n", missing)
    assert missing.sum() == 0, "Weather data has missing values"
    print("All checks passed")


def main() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    logging.info("Fetching daily weather %s to %s", START, END)
    df = fetch_weather(session)
    df["latitude"] = LATITUDE
    df["longitude"] = LONGITUDE
    df["retrieved"] = date.today().isoformat()

    validate(df)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT, index=False)
    logging.info("Saved %s raw rows to %s", len(df), OUTPUT)


if __name__ == "__main__":
    main()