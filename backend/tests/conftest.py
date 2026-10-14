from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_RUNTIME = Path(__file__).resolve().parents[1] / ".test-runtime"
os.environ["DATAQUEST_DATA_DIR"] = str(TEST_RUNTIME)

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def demo(client: TestClient):
    response = client.post("/api/v1/demo")
    assert response.status_code == 201, response.text
    return response.json()

