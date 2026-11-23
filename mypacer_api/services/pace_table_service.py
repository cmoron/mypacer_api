"""
This module contains the pace table service, which is responsible for generating a pace table.
"""

from fastapi import HTTPException

from mypacer_api.core import calculator

# Simple cache for pace table results
# Key: (min_pace, max_pace, increment, tuple of distances)
# Value: calculated pace table
_pace_table_cache: dict = {}
_MAX_CACHE_SIZE = 100

# Le calcul tourne dans la boucle d'événements de l'unique worker : une plage
# non bornée fige toute l'API (recherche et /health compris). Le front demande
# au plus 511 lignes (10'00 → 1'30 par pas de 1 s).
MAX_ROWS = 1000
MAX_DISTANCES = 100


def _get_cache_key(
    min_pace: int, max_pace: int, increment: int, distances: list
) -> tuple:
    """
    Create a hashable cache key from the parameters.

    Args:
        min_pace: Minimum pace in seconds per kilometer
        max_pace: Maximum pace in seconds per kilometer
        increment: Increment in seconds per kilometer
        distances: List of distances in meters

    Returns:
        Tuple that can be used as a dictionary key
    """
    return (min_pace, max_pace, increment, tuple(sorted(distances)))


def get_pace_table(
    min_pace: int, max_pace: int, increment: int, distances: list = []
) -> list:
    """
    Get a pace table for a given range of paces and increment.
    Results are cached to improve performance for repeated requests.

    Args:
    min_pace (int): The minimum pace in seconds per kilometer.
    max_pace (int): The maximum pace in seconds per kilometer.
    increment (int): The increment in seconds per kilometer.
    distances (list): A list of distances in meters

    Returns:
    List[Dict]: A list of dictionaries where each dictionary represents a row in the pace table,
    with keys being the distances and values being the calculated times.
    """
    if max_pace > min_pace:
        raise HTTPException(
            status_code=400, detail="Minimum pace must be more than maximum pace."
        )

    rows = (min_pace - max_pace) // increment + 1 if increment > 0 else 0
    if rows > MAX_ROWS or len(distances) > MAX_DISTANCES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Requested table is too large (max {MAX_ROWS} rows, "
                f"{MAX_DISTANCES} distances)."
            ),
        )

    # Check cache first
    cache_key = _get_cache_key(min_pace, max_pace, increment, distances)
    if cache_key in _pace_table_cache:
        return _pace_table_cache[cache_key]

    # Calculate if not in cache
    result = calculator.calculate_pace_table(min_pace, max_pace, increment, distances)

    # Store in cache (with simple size limit)
    if len(_pace_table_cache) >= _MAX_CACHE_SIZE:
        # Remove oldest entry (first key)
        _pace_table_cache.pop(next(iter(_pace_table_cache)))

    _pace_table_cache[cache_key] = result

    return result
