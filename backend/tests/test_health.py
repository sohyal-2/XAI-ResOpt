import httpx
import pytest

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint_reports_real_dependency_state() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")

    assert response.status_code in {200, 503}
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["database"] in {"ok", "error"}
    assert body["redis"] in {"ok", "error"}
    if response.status_code == 503:
        assert body["status"] == "degraded"
        assert body["details"]
        return

    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["redis"] == "ok"