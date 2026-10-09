"""Integration tests for all FastAPI endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True
    assert data["model_loaded"] is True
    assert data["total_historical_matches"] == 1090


def test_get_teams_endpoint(client: TestClient) -> None:
    response = client.get("/api/teams?active_only=true")
    assert response.status_code == 200
    teams = response.json()
    assert len(teams) == 10
    names = {t["name"] for t in teams}
    assert "Chennai Super Kings" in names
    assert "Mumbai Indians" in names
    assert "Royal Challengers Bengaluru" in names


def test_get_venues_endpoint(client: TestClient) -> None:
    response = client.get("/api/venues")
    assert response.status_code == 200
    venues = response.json()
    assert len(venues) >= 15
    venue_names = {v["name"] for v in venues}
    assert "Mumbai" in venue_names
    assert "Chennai" in venue_names
    assert "Bengaluru" in venue_names


def test_predict_and_history_persistence(client: TestClient) -> None:
    payload = {
        "team1": "Chennai Super Kings",
        "team2": "Mumbai Indians",
        "venue": "Chennai",
        "toss_winner": "Chennai Super Kings",
        "toss_decision": "field",
        "season": 2026,
    }
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 200
    pred = response.json()
    assert pred["prediction_id"] is not None
    assert pred["team1"] == "Chennai Super Kings"
    assert pred["team2"] == "Mumbai Indians"
    assert 0 < pred["team1_win_prob"] < 100
    assert abs((pred["team1_win_prob"] + pred["team2_win_prob"]) - 100.0) <= 0.1
    assert len(pred["explanations"]) >= 5

    # Verify prediction was persisted in GET /api/history
    hist_resp = client.get("/api/history?limit=10")
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert any(item["id"] == pred["prediction_id"] for item in history)


def test_predict_validation_errors(client: TestClient) -> None:
    # Same team1 and team2 should fail validation
    bad_payload = {
        "team1": "Chennai Super Kings",
        "team2": "Chennai Super Kings",
        "venue": "Chennai",
        "toss_winner": "Chennai Super Kings",
        "toss_decision": "field",
        "season": 2026,
    }
    resp = client.post("/api/predict", json=bad_payload)
    assert resp.status_code == 422

    # Toss winner not in (team1, team2) should fail validation
    bad_toss = {
        "team1": "Chennai Super Kings",
        "team2": "Mumbai Indians",
        "venue": "Chennai",
        "toss_winner": "Kolkata Knight Riders",
        "toss_decision": "field",
        "season": 2026,
    }
    resp2 = client.post("/api/predict", json=bad_toss)
    assert resp2.status_code == 422


def test_head_to_head_endpoint(client: TestClient) -> None:
    resp = client.get(
        "/api/stats/head-to-head",
        params={"team1": "Chennai Super Kings", "team2": "Mumbai Indians"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_matches"] >= 30
    assert data["team1_wins"] + data["team2_wins"] == data["total_matches"]
    assert len(data["recent_matches"]) > 0


def test_dashboard_analytics_endpoint(client: TestClient) -> None:
    resp = client.get("/api/stats/analytics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["total_matches"] == 1090
    assert len(data["team_standings"]) == 10
    assert len(data["season_trends"]) == 17
    assert "models_compared" in data["model_performance"]
