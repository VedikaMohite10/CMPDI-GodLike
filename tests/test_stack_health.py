"""test_stack_health.py — Service reachability + external network audit.

Verifies:
  1. API /health returns 200 with status=ok
  2. Postgres is reachable (via API's DB-dependent endpoint)
  3. Qdrant is reachable on port 6333
  4. Ollama is reachable on port 11434 and each required model is present
  5. External network audit: all HTTP calls in the app code target only local hosts
"""
from __future__ import annotations

import ast
import os
import re
import socket
from pathlib import Path

import httpx
import pytest

BASE_URL = os.environ.get("CMPDI_API_URL", "http://localhost:8000")
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")

REQUIRED_MODELS = [
    os.environ.get("EMBEDDING_MODEL",  "bge-m3"),
    os.environ.get("EXTRACTION_MODEL", "qwen2.5vl"),
    os.environ.get("SYNTHESIS_MODEL",  "qwen2.5"),
]

APP_DIR = Path(__file__).parent.parent / "app"


# ---------------------------------------------------------------------------
# 1. API health
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestAPIHealth:
    def test_health_endpoint_returns_200(self):
        r = httpx.get(f"{BASE_URL}/health", timeout=10)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_health_reports_status_ok(self):
        r = httpx.get(f"{BASE_URL}/health", timeout=10)
        data = r.json()
        assert data.get("status") == "ok", f"Expected status=ok, got: {data}"

    def test_health_includes_version(self):
        r = httpx.get(f"{BASE_URL}/health", timeout=10)
        assert "version" in r.json(), "Health response missing 'version' field"

    def test_postgres_reachable_via_api(self):
        """If Postgres is down, /documents will return 500 or 503."""
        r = httpx.get(f"{BASE_URL}/documents?page_size=1", timeout=15)
        assert r.status_code in (200, 404), (
            f"Unexpected status {r.status_code} — Postgres may be down: {r.text[:200]}"
        )


# ---------------------------------------------------------------------------
# 2. Qdrant reachability
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestQdrantHealth:
    def test_qdrant_reachable(self):
        try:
            r = httpx.get(f"{QDRANT_URL}/healthz", timeout=5)
            assert r.status_code == 200, f"Qdrant /healthz returned {r.status_code}"
        except httpx.ConnectError:
            pytest.fail(f"Qdrant not reachable at {QDRANT_URL}")

    def test_qdrant_collections_endpoint(self):
        """Qdrant REST API /collections responds."""
        try:
            r = httpx.get(f"{QDRANT_URL}/collections", timeout=5)
            assert r.status_code == 200
            assert "result" in r.json()
        except httpx.ConnectError:
            pytest.fail(f"Qdrant /collections not reachable at {QDRANT_URL}")


# ---------------------------------------------------------------------------
# 3. Ollama reachability + model presence
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.llm
class TestOllamaHealth:
    def _get_models(self) -> list[str]:
        r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        assert r.status_code == 200, f"Ollama /api/tags returned {r.status_code}"
        return [m["name"].split(":")[0] for m in r.json().get("models", [])]

    def test_ollama_reachable(self):
        try:
            r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=10)
            assert r.status_code == 200
        except httpx.ConnectError:
            pytest.fail(f"Ollama not reachable at {OLLAMA_URL}")

    @pytest.mark.parametrize("model", REQUIRED_MODELS)
    def test_required_model_present(self, model: str):
        models = self._get_models()
        assert any(model in m for m in models), (
            f"Required model '{model}' not found in Ollama. "
            f"Available: {models}. Run: ollama pull {model}"
        )

    def test_ollama_generate_trivial_call(self):
        """Verify Ollama responds to a minimal /api/generate call."""
        r = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": REQUIRED_MODELS[-1], "prompt": "Say: ok", "stream": False},
            timeout=60,
        )
        assert r.status_code == 200
        assert "response" in r.json()


# ---------------------------------------------------------------------------
# 4. External network audit (static codebase analysis — no stack required)
# ---------------------------------------------------------------------------
class TestExternalNetworkAudit:
    """Verify no code in app/ makes calls to non-local hosts.

    This is a static analysis check — it parses the source AST to find
    string literals that look like external HTTP URLs.
    """

    ALLOWED_HOSTS = {
        "localhost",
        "127.0.0.1",
        "host.docker.internal",  # used in docker-compose for Ollama
        "0.0.0.0",
    }

    # Env-var names that configure host addresses (any value is OK, checked at runtime)
    ALLOWED_ENV_PATTERNS = re.compile(
        r"(OLLAMA_BASE_URL|QDRANT_HOST|DATABASE_URL|POSTGRES_HOST)", re.IGNORECASE
    )

    def _collect_string_literals(self, py_file: Path) -> list[str]:
        try:
            tree = ast.parse(py_file.read_text(errors="replace"))
        except SyntaxError:
            return []
        return [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]

    def test_no_hardcoded_external_urls_in_app(self):
        """No string literal in app/ starts with https:// or http:// pointing
        to a non-local host."""
        violations: list[str] = []
        for py_file in APP_DIR.rglob("*.py"):
            for s in self._collect_string_literals(py_file):
                m = re.match(r"https?://([^/:]+)", s)
                if not m:
                    continue
                host = m.group(1)
                if host not in self.ALLOWED_HOSTS:
                    violations.append(f"{py_file.relative_to(APP_DIR)}: {s!r}")

        assert not violations, (
            "EXTERNAL NETWORK AUDIT FAILED — hardcoded non-local URLs found:\n"
            + "\n".join(f"  {v}" for v in violations)
            + "\n\nAll API calls must go through settings.OLLAMA_BASE_URL / settings.QDRANT_URL "
            "so they can be overridden for on-premise deployment."
        )

    def test_no_requests_library_used(self):
        """The `requests` library must not be used in app/ — only httpx (async).

        `requests` is synchronous and would block the event loop.
        """
        violations: list[str] = []
        for py_file in APP_DIR.rglob("*.py"):
            try:
                src = py_file.read_text(errors="replace")
            except Exception:
                continue
            if re.search(r"\bimport requests\b", src):
                violations.append(str(py_file.relative_to(APP_DIR)))

        assert not violations, (
            "Found `import requests` in app/ (sync HTTP blocks event loop):\n"
            + "\n".join(f"  {v}" for v in violations)
        )

    def test_config_uses_env_for_service_urls(self):
        """app/config.py must configure all external service URLs via env vars,
        not hardcoded strings."""
        config_file = APP_DIR / "config.py"
        assert config_file.exists(), "app/config.py not found"
        src = config_file.read_text()
        # OLLAMA_BASE_URL and DATABASE_URL must be configurable
        assert "OLLAMA_BASE_URL" in src, "OLLAMA_BASE_URL missing from app/config.py"
        assert "DATABASE_URL" in src, "DATABASE_URL missing from app/config.py"

    def test_ollama_calls_use_settings_url(self):
        """All Ollama HTTP calls must use settings.OLLAMA_BASE_URL, not a literal."""
        violations: list[str] = []
        for py_file in APP_DIR.rglob("*.py"):
            src = py_file.read_text(errors="replace")
            # If file makes HTTP calls to Ollama...
            if "11434" in src or "ollama" in src.lower():
                # It must reference settings, not a hardcoded URL
                has_hardcoded = re.search(r'"http://localhost:11434"', src)
                has_settings = "settings." in src or "get_settings" in src or "OLLAMA_BASE_URL" in src
                if has_hardcoded and not has_settings:
                    violations.append(str(py_file.relative_to(APP_DIR)))
        assert not violations, (
            "Hardcoded Ollama URL found without settings reference:\n"
            + "\n".join(f"  {v}" for v in violations)
        )
