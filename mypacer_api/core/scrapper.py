"""
Module containing functions for scraping running records from the World Athletics website.
"""

import re
from typing import Dict

import requests
from bs4 import BeautifulSoup as bs
from fastapi import HTTPException


def ba_convert_time_to_seconds(time_str: str) -> float:
    """
    Convert a time string in the format HHhmm'ss, mm'ss, mm'ss"cc or ss"cc to seconds.

    Args:
    time_str (str): The time string to convert.

    Returns:
    float: The number of seconds represented by the time string.
    """
    time_str = time_str.replace("''", '"')
    time_str = time_str.split(" ")[
        0
    ]  # Remove any additional information after the time
    if not time_str:
        return 0

    total_seconds = 0.0

    # If the time string is in the format HHhmm'ss
    if "h" in time_str and "'" in time_str and '"' in time_str:
        hours, rest = time_str.split("h")
        minutes, seconds = rest.split("'")
        seconds = seconds.replace('"', "")
        total_seconds = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
    # If the time string is in the format mm'ss or mm'ss"cc
    elif "'" in time_str and '"' in time_str:
        # Split the time string into minutes and seconds
        minutes, seconds = time_str.split("'")
        seconds, centiseconds = seconds.split('"')
        if centiseconds:
            seconds = f"{seconds}.{centiseconds}"

        # Calculate the total seconds
        total_seconds = float(minutes) * 60.0 + float(seconds)
    elif '"' in time_str:
        # Convert the time string to a float and multiply by 100 to get the number of centiseconds
        seconds, centiseconds = time_str.split('"')
        # Calculate the total seconds
        total_seconds = float(seconds) + float(centiseconds) / 100.0
    else:
        total_seconds = -1
    return float(total_seconds)


def parse_bases_athle_record_page(soup: bs) -> Dict[float, float]:
    """
    Function to extract athlete data from a record page using BeautifulSoup.

    Args:
    soup (BeautifulSoup): The BeautifulSoup object containing the record page.

    Returns:
    dict: A dictionary containing athlete data, including the athlete's name,
    """

    section = soup.find("section", attrs={"data-content": "section_5"})

    if not section:
        return {}

    # Find the table with class 'linedRed' or 'base-table'
    table = section.find("table", class_="linedRed") or section.find(
        "table", class_=re.compile(r"\bbase-table\b")
    )

    if not table:
        return {}

    # Distance mapping in meters
    distances: dict[str, float] = {
        "100m": 100,
        "100m Piste Courte": 100,
        "200m": 200,
        "200m Piste Courte": 200,
        "400m": 400,
        "400m Piste Courte": 400,
        "800m": 800,
        "800m Piste Courte": 800,
        "1 000m": 1000,
        "1000m Piste Courte": 1000,
        "1 500m": 1500,
        "1 500m Piste Courte": 1500,
        "Mile": 1609.34,
        "Mile Piste Courte": 1609.34,
        "3 000m": 3000,
        "3 000m Piste Courte": 3000,
        "5 000m": 5000,
        "5 Km Route": 5000,
        "10 Km Route": 10000,
        "20 Km Route": 20000,
        "1/2 Marathon": 21097,
        "Marathon": 42195,
    }

    # Extract athlete records
    athlete_records: Dict[float, float] = {}
    for row in table.find_all("tr", recursive=False):
        classes: str | list[str] = row.get("class", None) or []

        # Skip detail rows
        if "detail-row" in classes:
            continue
        cols = row.find_all("td", recursive=False)

        # Skip rows that do not have at least 2 columns
        if len(cols) < 2:
            continue

        # Get event and performance from the first two columns
        event = cols[0].get_text(strip=True)
        performance = cols[1].get_text(strip=True)

        event_key = distances.get(event)

        # Skip if event is not recognized
        if not event_key:
            continue

        perf_seconds = ba_convert_time_to_seconds(performance)

        # Skip if performance could not be converted
        if perf_seconds <= 0:
            continue

        # Store the best performance for each event
        prev = athlete_records.get(event_key)
        athlete_records[event_key] = min(prev, perf_seconds) if prev else perf_seconds

    return athlete_records


def scrap_athlete_records(url: str) -> Dict[float, float]:
    """
    Function to scrape athlete data from the 'bases.athle.fr' website.

    Args:
    html (str): The HTML content of the athlete record page.

    Returns:
    dict: A dictionary containing athlete data, including the athlete's name,
    """
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        soup = bs(response.text, "html.parser")
        return parse_bases_athle_record_page(soup)
    raise HTTPException(
        status_code=response.status_code, detail="Failed to make an external request"
    )
