"""test_dependencies.py — Verification of Python packages, system binaries, frontend, and configuration.

Run with:
    python -m pytest tests/test_dependencies.py -v
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"


# ---------------------------------------------------------------------------
# 1. Python Environment & Platform
# ---------------------------------------------------------------------------
class TestPythonEnvironment:
    """Verifies runtime Python environment suitability."""

    def test_python_version_compatible(self):
        """Project requires Python >= 3.10."""
        major, minor = sys.version_info[:2]
        assert (major, minor) >= (3, 10), (
            f"Python {major}.{minor} detected. Minimum required version is 3.10."
        )

    def test_python_64bit(self):
        """Verifies 64-bit Python architecture (required for numpy/scipy/torch)."""
        import struct
        bits = struct.calcsize("P") * 8
        assert bits == 64, f"Expected 64-bit Python, got {bits}-bit"


# ---------------------------------------------------------------------------
# 2. Python Package Dependencies (from requirements.txt)
# ---------------------------------------------------------------------------
class TestPythonPackages:
    """Verifies all Python packages from requirements.txt are importable and functional."""

    @pytest.mark.parametrize(
        "module_name,package_name",
        [
            ("fastapi", "FastAPI web framework"),
            ("uvicorn", "ASGI web server"),
            ("python_multipart", "python-multipart file upload handler"),
            ("sqlalchemy", "SQLAlchemy ORM"),
            ("asyncpg", "PostgreSQL async driver"),
            ("pydantic", "Pydantic data validation"),
            ("pydantic_settings", "Pydantic settings management"),
            ("aiofiles", "Asynchronous file I/O"),
            ("filetype", "MIME type sniffing library"),
            ("pdf2image", "PDF rasterization wrapper"),
            ("PIL", "Pillow image library"),
            ("docx", "python-docx document parser"),
            ("openpyxl", "OpenPyXL spreadsheet parser"),
            ("httpx", "HTTPX async HTTP client"),
            ("qdrant_client", "Qdrant vector database client"),
            ("numpy", "NumPy array computation"),
        ],
    )
    def test_core_dependencies_present(self, module_name: str, package_name: str):
        """Core server and data processing dependencies must be installed."""
        try:
            mod = importlib.import_module(module_name)
            assert mod is not None
        except ImportError as e:
            pytest.fail(f"Missing required dependency: '{module_name}' ({package_name}). Run: pip install {module_name} (Error: {e})")

    @pytest.mark.parametrize(
        "module_name,package_name",
        [
            ("alembic", "Database migration tool"),
            ("pdfplumber", "Digital PDF text/table extraction"),
            ("pytesseract", "Tesseract OCR python wrapper"),
            ("reportlab", "ReportLab PDF generator"),
            ("matplotlib", "Matplotlib chart rendering"),
            ("sklearn", "Scikit-Learn ML / HDBSCAN clustering"),
            ("jose", "python-jose JWT security"),
            ("passlib", "Passlib password hashing"),
            ("statsmodels", "Statsmodels forecasting / ARIMA"),
            ("slowapi", "SlowAPI rate limiter"),
            ("limits", "Limits backend for rate limiter"),
        ],
    )
    def test_extended_phase_dependencies(self, module_name: str, package_name: str):
        """Phases 2-5 extended dependencies (skips gracefully with actionable error if still installing)."""
        try:
            mod = importlib.import_module(module_name)
            assert mod is not None
        except ImportError:
            pytest.fail(
                f"Missing Phase dependency: '{module_name}' ({package_name}). "
                f"Run: pip install -r requirements.txt"
            )


# ---------------------------------------------------------------------------
# 3. External System Tooling (CLI Binaries)
# ---------------------------------------------------------------------------
class TestSystemTools:
    """Verifies presence of system binaries (Node.js, npm, Docker, Tesseract, Poppler)."""

    def test_nodejs_installed(self):
        """Node.js is needed for frontend development."""
        node_path = shutil.which("node")
        if not node_path:
            pytest.fail("Node.js is not found in PATH. Please install Node.js (https://nodejs.org).")
        res = subprocess.run([node_path, "--version"], capture_output=True, text=True)
        assert res.returncode == 0
        assert res.stdout.strip().startswith("v")

    def test_npm_installed(self):
        """npm is needed for managing frontend dependencies."""
        npm_path = shutil.which("npm") or shutil.which("npm.cmd")
        if not npm_path:
            pytest.fail("npm is not found in PATH.")
        res = subprocess.run([npm_path, "--version"], capture_output=True, text=True)
        assert res.returncode == 0
        assert len(res.stdout.strip()) > 0

    def test_poppler_or_pdf_tools(self):
        """Checks for pdftoppm (poppler-utils) used for rasterizing scanned PDFs."""
        pdftoppm_path = shutil.which("pdftoppm")
        # Soft warning: on Windows poppler might be in a custom path or Docker
        if not pdftoppm_path:
            pytest.skip(
                "pdftoppm (poppler-utils) not detected in system PATH. "
                "Digital PDFs and docx work fine; scanned PDF OCR requires poppler or Docker container."
            )

    def test_tesseract_ocr_available(self):
        """Checks if Tesseract OCR binary is installed on the host."""
        tesseract_path = shutil.which("tesseract")
        common_win_paths = [
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        ]
        found = tesseract_path or any(p.exists() for p in common_win_paths)
        if not found:
            pytest.skip(
                "tesseract binary not found in PATH or standard Program Files. "
                "Install Tesseract OCR if local OCR of scanned documents is needed on Windows, or use Docker."
            )


# ---------------------------------------------------------------------------
# 4. Frontend Project Sanity
# ---------------------------------------------------------------------------
class TestFrontendIntegrity:
    """Verifies that the React + Vite frontend directory and files are intact."""

    def test_frontend_directory_exists(self):
        assert FRONTEND_DIR.exists(), f"Frontend directory not found at {FRONTEND_DIR}"

    def test_package_json_valid(self):
        pkg_path = FRONTEND_DIR / "package.json"
        assert pkg_path.exists(), "frontend/package.json missing"
        with open(pkg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "dependencies" in data
        assert "react" in data["dependencies"]
        assert "vite" in data.get("devDependencies", {})

    def test_vite_config_exists(self):
        assert (FRONTEND_DIR / "vite.config.js").exists(), "frontend/vite.config.js missing"

    def test_index_html_exists(self):
        assert (FRONTEND_DIR / "index.html").exists(), "frontend/index.html missing"

    def test_src_directory_structure(self):
        src = FRONTEND_DIR / "src"
        assert src.exists()
        assert (src / "App.jsx").exists()
        assert (src / "main.jsx").exists()
        assert (src / "components").exists()
        assert (src / "pages").exists()

    def test_node_modules_present(self):
        """Verifies frontend dependencies are installed."""
        node_modules = FRONTEND_DIR / "node_modules"
        assert node_modules.exists(), (
            "frontend/node_modules not found. Run 'cd frontend && npm install'"
        )


# ---------------------------------------------------------------------------
# 5. Configuration & Environment Variables
# ---------------------------------------------------------------------------
class TestEnvironmentConfiguration:
    """Verifies project configuration settings and directories."""

    def test_env_example_has_all_keys(self):
        env_example = ROOT_DIR / ".env.example"
        assert env_example.exists(), ".env.example is missing"
        content = env_example.read_text(encoding="utf-8")
        expected_keys = [
            "POSTGRES_USER",
            "POSTGRES_DB",
            "QDRANT_HTTP_PORT",
            "OLLAMA_BASE_URL",
            "OCR_ENGINE",
            "MAX_FILE_SIZE_MB",
        ]
        for key in expected_keys:
            assert key in content, f".env.example is missing '{key}' definition"

    def test_storage_directories_exist_or_creatable(self):
        storage_dir = ROOT_DIR / "storage"
        docs_dir = storage_dir / "documents"
        imgs_dir = storage_dir / "images"
        docs_dir.mkdir(parents=True, exist_ok=True)
        imgs_dir.mkdir(parents=True, exist_ok=True)
        assert docs_dir.is_dir()
        assert imgs_dir.is_dir()
