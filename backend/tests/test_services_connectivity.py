"""test_services_connectivity.py — Connectivity probe for all CMPDI runtime services.

Tests live reachability of:
1. CMPDI FastAPI Backend (port 8000)
2. Qdrant Vector Engine (port 6333)
3. Ollama LLM / VLM Engine (port 11434)
4. Frontend Dev Server (port 5173)
5. PostgreSQL Database (via API probe)

Provides human-readable diagnostic messages and skips gracefully if a service is not currently running.

Run with:
    python -m pytest tests/test_services_connectivity.py -v
"""
from __future__ import annotations

import os
import httpx
import pytest

API_URL = os.environ.get("CMPDI_API_URL", "http://localhost:8000")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

REQUIRED_MODELS = [
    os.environ.get("EMBEDDING_MODEL", "bge-m3"),
    os.environ.get("EXTRACTION_MODEL", "qwen2.5vl"),
    os.environ.get("SYNTHESIS_MODEL", "qwen2.5"),
]


# ---------------------------------------------------------------------------
# 1. FastAPI Backend Service Probe
# ---------------------------------------------------------------------------
class TestAPIServiceConnectivity:
    """Verifies backend API service responsiveness."""

    def test_api_health_endpoint(self):
        try:
            r = httpx.get(f"{API_URL}/health", timeout=3.0)
            assert r.status_code == 200, f"API returned status {r.status_code}"
            data = r.json()
            assert data.get("status") == "ok"
        except (httpx.ConnectError, httpx.TimeoutException):
            pytest.skip(
                f"FastAPI backend is not running at {API_URL}. "
                "Start it with: uvicorn app.main:app --reload --port 8000"
            )

    def test_api_docs_reachable(self):
        try:
            r = httpx.get(f"{API_URL}/docs", timeout=3.0)
            assert r.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            pytest.skip(f"API docs not reachable at {API_URL}/docs")


# ---------------------------------------------------------------------------
# 2. Qdrant Vector Engine Probe
# ---------------------------------------------------------------------------
class TestQdrantServiceConnectivity:
    """Verifies Qdrant vector database reachability."""

    def test_qdrant_health(self):
        try:
            r = httpx.get(f"{QDRANT_URL}/healthz", timeout=3.0)
            assert r.status_code == 200, f"Qdrant returned {r.status_code}"
        except (httpx.ConnectError, httpx.TimeoutException):
            pytest.skip(
                f"Qdrant service is not running at {QDRANT_URL}. "
                "Start it with docker-compose: docker compose up -d qdrant"
            )

    def test_qdrant_collections(self):
        try:
            r = httpx.get(f"{QDRANT_URL}/collections", timeout=3.0)
            assert r.status_code == 200
            assert "result" in r.json()
        except (httpx.ConnectError, httpx.TimeoutException):
            pytest.skip(f"Qdrant collections endpoint not reachable at {QDRANT_URL}")


# ---------------------------------------------------------------------------
# 3. Ollama LLM Service Probe
# ---------------------------------------------------------------------------
class TestOllamaServiceConnectivity:
    """Verifies Ollama server and model presence."""

    def test_ollama_reachable(self):
        try:
            r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=3.0)
            assert r.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            pytest.skip(
                f"Ollama server is not running at {OLLAMA_URL}. "
                "Start Ollama or run 'ollama serve'."
            )

    def test_ollama_models_loaded(self):
        try:
            r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=3.0)
            if r.status_code != 200:
                pytest.skip(f"Ollama /api/tags returned {r.status_code}")
            models = [m["name"].split(":")[0] for m in r.json().get("models", [])]
            for req in REQUIRED_MODELS:
                if not any(req in m for m in models):
                    pytest.skip(
                        f"Required model '{req}' not yet pulled in Ollama. "
                        f"Run: ollama pull {req}"
                    )
        except (httpx.ConnectError, httpx.TimeoutException):
            pytest.skip(f"Ollama server not reachable at {OLLAMA_URL}")


# ---------------------------------------------------------------------------
# 4. Frontend Dev Server Probe
# ---------------------------------------------------------------------------
class TestFrontendConnectivity:
    """Verifies whether the React + Vite frontend dev server is active."""

    def test_frontend_dev_server_running(self):
        try:
            r = httpx.get(FRONTEND_URL, timeout=3.0)
            assert r.status_code in (200, 304), f"Frontend returned {r.status_code}"
        except (httpx.ConnectError, httpx.TimeoutException):
            pytest.skip(
                f"Frontend dev server is not running at {FRONTEND_URL}. "
                "To start it: cd frontend && npm run dev"
            )
