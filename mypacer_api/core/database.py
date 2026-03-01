"""
Database connection pooling for PostgreSQL.

This module provides a connection pool to avoid creating
a new database connection for each request, significantly
improving performance.
"""

import atexit
import os

from dotenv import load_dotenv
from psycopg2 import pool

load_dotenv()

# Connection pool configuration
MIN_CONNECTIONS = 2
MAX_CONNECTIONS = 20

# Global connection pool
_connection_pool = None


def get_connection_pool():
    """
    Get or create the global PostgreSQL connection pool.

    Returns:
        SimpleConnectionPool: The connection pool instance.
    """
    global _connection_pool

    if _connection_pool is None:
        db_config = {
            "dbname": os.getenv("POSTGRES_DB"),
            "user": os.getenv("POSTGRES_USER"),
            "password": os.getenv("POSTGRES_PASSWORD"),
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": os.getenv("POSTGRES_PORT", "5432"),
        }

        _connection_pool = pool.ThreadedConnectionPool(
            MIN_CONNECTIONS, MAX_CONNECTIONS, **db_config
        )

    return _connection_pool


def get_connection():
    """
    Get a connection from the pool.

    Returns:
        psycopg2.connection: A database connection from the pool.
    """
    pool_instance = get_connection_pool()
    return pool_instance.getconn()


def release_connection(conn):
    """
    Release a connection back to the pool.

    Args:
        conn: The connection to release.
    """
    pool_instance = get_connection_pool()
    pool_instance.putconn(conn)


def close_all_connections():
    """
    Close all connections in the pool.
    Called automatically on application shutdown.
    """
    global _connection_pool
    if _connection_pool is not None:
        _connection_pool.closeall()
        _connection_pool = None


# Register cleanup function to run on application exit
atexit.register(close_all_connections)
