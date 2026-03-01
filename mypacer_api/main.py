"""
The Running Pace Table API is a FastAPI application designed to calculate running paces for
various distances.  This API  takes input  parameters  like minimum pace, maximum pace, and
increment step, and returns a table of  estimated running times for official race distances.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mypacer_api.models import TableParameters
from mypacer_api.services import athletes_service, database_service, pace_table_service

app = FastAPI()

# CORS only needed for local development (Vite dev server on different port)
# In production, API is served via /api reverse proxy (same origin = no CORS needed)
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """
    Basic health check endpoint.

    Returns:
        dict: Status indicating the API is alive and responding.

    This endpoint is used for:
    - Docker/Kubernetes liveness probes
    - Load balancer health checks
    - Monitoring systems
    """
    return {"status": "healthy", "service": "mypacer-api"}


@app.get("/health/ready")
def readiness_check():
    """
    Readiness check endpoint with database connectivity verification.

    Returns:
        dict: Status indicating the API is ready to handle requests.

    Raises:
        HTTPException: If the database is unreachable (503 Service Unavailable).

    This endpoint verifies:
    - API is running
    - Database connection is available
    """
    try:
        # Try to get database status to verify DB connection
        db_status = database_service.get_database_status()
        return {
            "status": "ready",
            "service": "mypacer-api",
            "database": "connected",
            "athletes_count": db_status.get("nb_athletes", 0),
        }
    except Exception as e:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail=f"Service not ready: Database connection failed - {str(e)}",
        )


@app.post("/generate_table")
async def generate_table(params: TableParameters):
    """
    Endpoint to generate a table of paces for various official race distances.

    Args:
    params (TableParameters): The pace parameters for generating the table.

    Raises:
    HTTPException: If the minimum pace is greater than the maximum pace.

    Returns:
    List[Dict]: A table of calculated times for each distance at each pace.
    """
    return pace_table_service.get_pace_table(
        params.min_pace, params.max_pace, params.increment, params.distances
    )


@app.get("/get_athletes")
def get_athletes(name: str, limit: int = 25, offset: int = 0):
    """
    Retrieves athlete information from the local database based on the provided athlete name.

    This endpoint uses optimized trigram indexes for fast fuzzy matching and supports pagination.
    Results are ordered by relevance (similarity score).

    Args:
        name (str): The name of the athlete to search for.
        limit (int): Maximum number of results to return (default: 25, max: 100).
        offset (int): Number of results to skip for pagination (default: 0).

    Returns:
        List[dict]: A list of athlete dictionaries containing:
            - id: Athlete identifier
            - ffa_id: FFA unique identifier
            - name: Athlete name
            - url: Link to FFA records page
            - birth_date: Date of birth
            - license_id: FFA license number
            - sexe: Gender (M/F)
            - nationality: Nationality code
            - score: Relevance score (0-1)

    Examples:
        GET /get_athletes?name=John Doe
        GET /get_athletes?name=John Doe&limit=10&offset=0
    """
    # Limit validation
    if limit > 100:
        limit = 100
    if limit < 1:
        limit = 1
    if offset < 0:
        offset = 0

    return athletes_service.get_athletes_from_db(name, limit=limit, offset=offset)


@app.get("/get_athletes_from_db")
def get_athletes_from_db(name: str, limit: int = 25, offset: int = 0):
    """
    Retrieves athlete information from the local database based on the provided athlete name.

    This is an alias for /get_athletes endpoint for backward compatibility.

    Args:
        name (str): The name of the athlete to search for.
        limit (int): Maximum number of results to return (default: 25, max: 100).
        offset (int): Number of results to skip for pagination (default: 0).

    Returns:
        List[dict]: A list of athlete dictionaries.
    """
    # Limit validation
    if limit > 100:
        limit = 100
    if limit < 1:
        limit = 1
    if offset < 0:
        offset = 0

    return athletes_service.get_athletes_from_db(name, limit=limit, offset=offset)


@app.get("/get_athlete_records")
def get_athlete_records(ident) -> dict:
    """
    Retrieves athlete records from the 'bases.athle.fr' website based on the provided athlete ID.

    Args:
    ident (str): The ID of the athlete to search for.

    Returns:
    dict: A dictionary containing the athlete's records for various disciplines and distances.
    """
    return athletes_service.get_athlete_records(ident)


@app.get("/database_status")
def database_status():
    """
    Endpoint to retrieve information about the database state, including
    the number of clubs, the number of athletes, and the date of the last update.

    Returns:
        dict: A dictionary containing the number of clubs, number of athletes,
              and the date of the last update.
    """
    return database_service.get_database_status()
