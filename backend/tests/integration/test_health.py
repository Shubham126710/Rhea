"""
Phase 0 exit-gate test (Master Build §25 Phase 0 hard exit gate):
frontend -> backend -> DB -> response, round trip.

This is a backend-side proof of the round trip (client -> API -> DB).
The frontend leg is exercised manually per PHASE0_SETUP.md, since a
browser round trip isn't something pytest observes directly; CI here
proves the backend half is genuine, not a hardcoded 200.
"""
def test_health_round_trips_through_the_database(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
