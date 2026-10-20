"""
This module contains the service functions for the 'athletes' endpoint.
"""

import psycopg2
from dotenv import load_dotenv
from fastapi import HTTPException
from psycopg2.extras import RealDictCursor
from unidecode import unidecode

from mypacer_api.core import database, scrapper

load_dotenv()

ATHLETE_COLUMNS = "id, ffa_id, name, url, birth_date, license_id, sexe, nationality"

# Index btree text_pattern_ops (idx_athletes_normalized_name_prefix) : parcours
# ordonné, quelques ms même pour « mar » qui matche ~60 000 noms en flou.
PREFIX_QUERY = f"""
SELECT {ATHLETE_COLUMNS}, similarity(normalized_name, %s) AS score
FROM athletes
WHERE normalized_name LIKE %s
ORDER BY normalized_name USING ~<~
LIMIT %s
"""


def _like_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def get_athletes_from_db(name: str, limit: int = 25, offset: int = 0) -> list:
    """
    Retrieves athletes information from the PostgreSQL database based on the provided athlete name.

    This function uses optimized trigram indexes on normalized_name for fast fuzzy matching.
    The search query is normalized using the database's normalize_text() function for
    accent-insensitive and case-insensitive matching.

    Args:
        name (str): The name of the athlete to search for.
        limit (int): Maximum number of results to return (default: 25).
        offset (int): Number of results to skip for pagination (default: 0).

    Returns:
        List of dictionaries containing athlete data, ordered by relevance (similarity score).
    """
    conn = None
    cursor = None

    try:
        # Get connection from pool
        conn = database.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Normalize search query (same logic as database normalize_text function)
        normalized_query = " ".join(unidecode(name).lower().strip().split())
        query_parts = normalized_query.split()
        if not query_parts:
            return []

        # Saisie courte ou nom de famille : les noms commençant par la saisie
        # suffisent à remplir la page, sans le tri flou qui relit chaque match.
        if offset == 0:
            cursor.execute(
                PREFIX_QUERY,
                [normalized_query, _like_escape(normalized_query) + "%", limit],
            )
            results = cursor.fetchall()
            if len(results) == limit:
                return results

        # Each word must be found in the normalized_name (AND logic)
        where_clause = " AND ".join(["normalized_name ILIKE %s" for _ in query_parts])

        # Optimized query using:
        # 1. normalized_name (indexed with GIN trigram)
        # 2. similarity() function for ranking
        # 3. ILIKE operator (uses trigram index when available)
        query = f"""
        SELECT
            {ATHLETE_COLUMNS},
            similarity(normalized_name, %s) AS score
        FROM athletes
        WHERE {where_clause}
        ORDER BY score DESC, name
        LIMIT %s OFFSET %s
        """

        # Prepare search patterns for ILIKE (% wildcards for fuzzy matching)
        search_patterns = [f"%{_like_escape(part)}%" for part in query_parts]

        # Add the full normalized query for similarity calculation
        params = [normalized_query] + search_patterns + [limit, offset]

        cursor.execute(query, params)
        results = cursor.fetchall()

    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=500, detail=f"Database error: {str(exc)}"
        ) from exc
    finally:
        if cursor:
            cursor.close()
        if conn:
            # Return connection to pool instead of closing it
            database.release_connection(conn)

    return results


def get_athlete_records(ident) -> dict:
    """
    Retrieves athlete records from the 'athle.fr' website based on the provided athlete ID.

    Args:
        ident (str): The ID of the athlete to search for.

    Returns:
        dict: A dictionary containing the athlete's records for various disciplines and distances.
    """
    conn = None
    cursor = None

    try:
        # Get connection from pool
        conn = database.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
        SELECT url
        FROM athletes
        WHERE id = %s
        LIMIT 1
        """

        cursor.execute(query, (ident,))
        result = cursor.fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Athlete not found.")

        url = result["url"]

    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=500, detail=f"Database error: {str(exc)}"
        ) from exc
    finally:
        if cursor:
            cursor.close()
        if conn:
            # Return connection to pool instead of closing it
            database.release_connection(conn)

    if not url:
        raise HTTPException(status_code=404, detail="Athlete URL not found.")

    # Scrape athlete records from FFA website
    return scrapper.scrap_athlete_records(url)
