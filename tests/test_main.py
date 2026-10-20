from fastapi.testclient import TestClient

from mypacer_api.main import app

client = TestClient(app)


def test_health_check():
    """Test the /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "mypacer-api"}


def test_generate_table_success():
    """Test the /generate_table endpoint with valid parameters."""
    payload = {"min_pace": 300, "max_pace": 240, "increment": 10}
    response = client.post("/generate_table", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "pace" in data[0]
    assert data[0]["pace"] == 300


def test_generate_table_invalid_pace_range():
    """Test /generate_table when min_pace is less than max_pace."""
    payload = {"min_pace": 240, "max_pace": 300, "increment": 10}
    response = client.post("/generate_table", json=payload)
    assert response.status_code == 400
    assert "Minimum pace must be more than maximum pace" in response.json()["detail"]


def test_get_athletes_from_db(mocker):
    """Test the /get_athletes_from_db endpoint, mocking the service layer."""
    mock_data = [{"id": "123", "name": "Test Athlete"}]
    mocker.patch(
        "mypacer_api.services.athletes_service.get_athletes_from_db",
        return_value=mock_data,
    )

    response = client.get("/get_athletes_from_db?name=test")
    assert response.status_code == 200
    assert response.json() == mock_data


def test_get_athlete_records(mocker):
    """Test the /get_athlete_records endpoint, mocking the service layer."""
    mock_data = {"800m": 120.5}
    mocker.patch(
        "mypacer_api.services.athletes_service.get_athlete_records",
        return_value=mock_data,
    )

    response = client.get("/get_athlete_records?ident=123456")
    assert response.status_code == 200
    assert response.json() == mock_data


def test_database_status(mocker):
    """Test the /database_status endpoint, mocking the service layer."""
    mock_data = {"num_clubs": 10, "num_athletes": 100, "last_update": "2025-01-01"}
    mocker.patch(
        "mypacer_api.services.database_service.get_database_status_cached",
        return_value=mock_data,
    )
    response = client.get("/database_status")
    assert response.status_code == 200
    assert response.json() == mock_data
