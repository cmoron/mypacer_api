"""
This module contains functions that interact with the database.
"""

import psycopg2
from dotenv import load_dotenv

from mypacer_api.core import database

load_dotenv()


def get_database_status():
    """
    Retrieves information about the database, including the number of clubs,
    the number of athletes, and the date of the last update.

    Returns:
        dict: A dictionary containing the number of clubs, number of athletes,
              and the date of the last update.
    """
    conn = None
    cursor = None

    try:
        # Get connection from pool
        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM clubs;")
        num_clubs = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM athletes;")
        num_athletes = cursor.fetchone()[0]

        cursor.execute("""
        SELECT GREATEST(
            MAX(last_vacuum),
            MAX(last_autovacuum),
            MAX(last_analyze),
            MAX(last_autoanalyze)
        ) AS last_update
        FROM pg_stat_all_tables
        WHERE relname = 'athletes';
        """)
        last_update = cursor.fetchone()[0]

        return {
            "num_clubs": num_clubs,
            "num_athletes": num_athletes,
            "last_update": last_update,
        }
    except psycopg2.Error as exc:
        raise exc
    finally:
        if cursor:
            cursor.close()
        if conn:
            # Return connection to pool instead of closing it
            database.release_connection(conn)
