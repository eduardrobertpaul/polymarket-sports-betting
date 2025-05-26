from app.web import app


async def _noop_async(*args, **kwargs):
    return []


def test_index_route() -> None:
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Select a Fixture" in resp.data


def test_recommendation_route_html(monkeypatch) -> None:
    # Patch Polymarket + provider fetchers to avoid network and event-loop clash
    monkeypatch.setattr("app.web.routes.fetch_market_probs", _noop_async)
    monkeypatch.setattr("app.web.routes.get_active_providers", lambda: {})

    client = app.test_client()
    resp = client.get("/fixture/123/recommendation")
    assert resp.status_code == 200
    assert b"Recommendation" in resp.data
