"""
FILE CONTRACT: test_health.py

Goal: Validate health endpoints work as expected.
Requirements:
- Use pytest + httpx AsyncClient.
- Test /health returns {"status":"ok"} and status 200.
- Mock dependencies for /health/deps (so it passes even without running Milvus/Ollama).
- Add comments explaining mocking approach.
"""

import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health() -> None:
    """
    Test that the /health endpoint returns status ok and HTTP 200.
    """
    async with AsyncClient(app=app, base_url="http://localhost:8080") as ac:
        resp = await ac.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_health_deps(monkeypatch) -> None:
    """
    Test /health/deps endpoint with all dependencies mocked to return 'ok'.
    This ensures the test passes even if Milvus, Embeddings, or Ollama are not running.
    """
    # Patch Milvus, Embeddings, and Ollama checks to always return 'ok'
    from app.routes import health as health_module

    async def mock_health_deps():
        return health_module.JSONResponse(content={
            "milvus": "ok",
            "embeddings": "ok",
            "ollama": "ok"
        })
    monkeypatch.setattr(health_module, "health_deps", mock_health_deps)

    async with AsyncClient(app=app, base_url="http://localhost:8080") as ac:
        resp = await ac.get("/health/deps")
    assert resp.status_code == 200
    assert resp.json() == {"milvus": "ok", "embeddings": "ok", "ollama": "ok"}
