from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_validate_entry_returns_a_valid_event() -> None:
    response = client.post(
        "/v1/entries/validate",
        json={
            "activity_key": "running",
            "activity": "running",
            "date": "2026-09-11",
            "observations": [
                {
                    "metric_key": "distance",
                    "value": 45,
                    "unit": "km",
                },
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["activity_key"] == "running"
    assert response.json()["activity"] == "running"
    assert len(response.json()["observations"]) == 1


def test_validate_entry_rejects_an_invalid_unit() -> None:
    response = client.post(
        "/v1/entries/validate",
        json={
            "activity_key": "swimming",
            "activity": "swimming",
            "date": "2026-09-11",
            "observations": [
                {
                    "metric_key": "distance",
                    "value": 1000,
                    "unit": "km",
                }
            ],
        },
    )

    assert response.status_code == 200
