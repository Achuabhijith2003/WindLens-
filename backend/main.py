"""FastAPI entry point for WindLens Backend."""

import sys
import types
from pathlib import Path

# Ensure 'backend' package resolves cleanly whether run from repository root or inside backend/
_HERE = Path(__file__).resolve().parent
_PARENT = _HERE.parent

if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

if "backend" not in sys.modules:
    try:
        import backend  # noqa: F401
    except ModuleNotFoundError:
        backend_pkg = types.ModuleType("backend")
        backend_pkg.__path__ = [str(_HERE)]
        sys.modules["backend"] = backend_pkg

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router

app = FastAPI(
    title="WindLens",
    version="0.2.0",
    description="UK Wind Generation Forecast Selection and Accuracy Engine (Phase 2)",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for local development with React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routes under /api as specified
app.include_router(router, prefix="/api", tags=["WindLens API"])
# Also include at root so /health, /overview, etc. can be queried directly
app.include_router(router, tags=["Root Endpoints"])


@app.get("/", tags=["Root"])
def root():
    return {
        "app": "WindLens",
        "version": "0.2.0",
        "description": "GB Wind Forecast Accuracy Engine (January 2026 Analysis)",
        "endpoints": [
            "/api/health",
            "/api/overview?date=YYYY-MM-DD",
            "/api/timeseries?date=YYYY-MM-DD&cutoff=day_ahead_1700",
            "/api/accuracy?from=YYYY-MM-DD&to=YYYY-MM-DD&cutoff=day_ahead_1700",
        ],
        "docs": "/docs",
    }

