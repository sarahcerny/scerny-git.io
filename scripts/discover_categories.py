"""Explore the Census MRTS endpoint to choose retail categories.

Run from the repository root:
    uv run python scripts/discover_categories.py

This script only explores. It makes three small requests and saves nothing.
The API key is read from census_key.txt, which must be listed in .gitignore.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://api.census.gov/data/timeseries/eits/mrts"
KEY_FILE = Path("census_key.txt")
USER_AGENT = (
    "STAT386-StudentProject/1.0 "
    "(educational data collection; limited requests; scerny@byu.edu)"
)
TIMEOUT_SECONDS = 30
POLITE_DELAY_SECONDS = 1.0

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def read_key() -> str:
    """Read the API key from a local file that is not committed to GitHub."""
    if not KEY_FILE.exists():
        raise RuntimeError(f"Create {KEY_FILE} containing only your Census API key.")
    key = KEY_FILE.read_text().strip()
    if not key:
        raise RuntimeError(f"{KEY_FILE} is empty.")
    return key


def fetch_json(session: requests.Session, url: str, params: dict) -> object:
    """Fetch JSON and fail clearly. Error messages leave out the key."""
    try:
        response = session.get(url, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as exc:
        raise RuntimeError(
            f"Request to {url} failed with status {exc.response.status_code}"
        ) from None
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError(
            f"Request to {url} failed: {type(exc).__name__}"
        ) from None


def show_variables(session: requests.Session, key: str) -> dict:
    """Print every variable the dataset offers."""
    data = fetch_json(session, f"{BASE_URL}/variables.json", {"key": key})
    variables = data["variables"]
    print("VARIABLES:")
    for name, info in variables.items():
        print(f"  {name:25s} {info.get('label', '')}")

    # Some datasets list allowed values for a variable. Print them if present.
    category_info = variables.get("category_code", {})
    if "values" in category_info:
        print("\nCATEGORY VALUES (from variables.json):")
        print(category_info["values"])
    return variables


def sample_pull(session: requests.Session, key: str, variables: dict) -> pd.DataFrame:
    """Pull a small recent sample to see real values for each field."""
    wanted = [
        "cell_value",
        "data_type_code",
        "category_code",
        "seasonally_adj",
        "time_slot_id",
    ]
    fields = [name for name in wanted if name in variables]
    params = {
        "get": ",".join(fields),
        "for": "us:*",
        "time": "from 2023-01",
        "key": key,
    }
    rows = fetch_json(session, BASE_URL, params)
    return pd.DataFrame(rows[1:], columns=rows[0])


def main() -> None:
    key = read_key()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    logging.info("Fetching variable list")
    variables = show_variables(session, key)

    time.sleep(POLITE_DELAY_SECONDS)
    logging.info("Fetching a small sample")
    df = sample_pull(session, key, variables)

    print("\nSAMPLE SHAPE:", df.shape)
    print(df.head())

    for column in ["data_type_code", "seasonally_adj", "category_code"]:
        if column in df.columns:
            print(f"\nUnique {column}:", sorted(df[column].unique()))


if __name__ == "__main__":
    main()