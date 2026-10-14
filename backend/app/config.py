from __future__ import annotations

import os
from pathlib import Path

APP_VERSION = "1.0.0"
BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("DATAQUEST_DATA_DIR", BACKEND_DIR / "runtime")).resolve()
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "dataquest.sqlite3"
DEMO_DIR = BACKEND_DIR / "data" / "demo"
MAX_UPLOAD_BYTES = int(os.getenv("DATAQUEST_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
DEFAULT_ROW_LIMIT = int(os.getenv("DATAQUEST_ROW_LIMIT", "100000"))
DEFAULT_SAMPLE_LIMIT = int(os.getenv("DATAQUEST_SAMPLE_LIMIT", "500"))
ALLOWED_ORIGINS = [
    value.strip()
    for value in os.getenv(
        "DATAQUEST_ALLOWED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173"
    ).split(",")
    if value.strip()
]


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

