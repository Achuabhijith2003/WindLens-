"""Vercel Serverless Function entrypoint for FastAPI backend."""

import os
import sys
from pathlib import Path

# Add repository root to sys.path so 'backend' package is resolvable
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.main import app

