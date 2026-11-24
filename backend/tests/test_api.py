"""
tests/test_api.py
Integrasi test endpoint FastAPI (tanpa database, tanpa file nyata).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)  # type: ignore[call-arg]

# ----- Fixtures -----

@pytest.fixture
def session_token():
    response = client.post("/api/v1/session")
    assert response.status_code == 200
    return response.json()["session_token"]


@pytest.fixture
def job_id(session_token):
    response = client.post(
        "/api/v1/jobs",
        json={"doc_type": "makalah", "standard_mode": "satu"},
        headers={"X-Session-Token": session_token},
    )
    assert response.status_code == 202
    return response.json()["job_id"]


# ----- Tests -----

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_session():
    response = client.post("/api/v1/session")
    assert response.status_code == 200
    data = response.json()
    assert "session_token" in data
    assert len(data["session_token"]) == 64


def test_create_job(session_token):
    response = client.post(
        "/api/v1/jobs",
        json={"doc_type": "laporan", "standard_mode": "campuran"},
        headers={"X-Session-Token": session_token},
    )
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"


def test_get_job_status(session_token, job_id):
    response = client.get(
        f"/api/v1/jobs/{job_id}/status",
        headers={"X-Session-Token": session_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id


def test_wrong_session_token(job_id):
    response = client.get(
        f"/api/v1/jobs/{job_id}/status",
        headers={"X-Session-Token": "wrong_token"},
    )
    assert response.status_code == 403


def test_resolve_rules():
    response = client.post(
        "/api/v1/rules/resolve",
        json={"doc_type": "makalah"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "resolved_rules" in data
    assert "halaman" in data["resolved_rules"]


def test_compatibility_check():
    response = client.post(
        "/api/v1/rules/compatibility",
        json={
            "doc_type": "laporan",
            "overrides": {
                "sitasi": {"gaya": "IEEE"},
                "daftar_pustaka": {"gaya": "APA7"},
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["has_errors"] is True


def test_rule_summary():
    response = client.post(
        "/api/v1/rules/summary",
        json={"doc_type": "makalah"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert len(data["summary"]) > 0


def test_delete_job(session_token, job_id):
    response = client.delete(
        f"/api/v1/jobs/{job_id}",
        headers={"X-Session-Token": session_token},
    )
    assert response.status_code == 204

    # Job seharusnya sudah hilang
    response = client.get(
        f"/api/v1/jobs/{job_id}/status",
        headers={"X-Session-Token": session_token},
    )
    assert response.status_code == 404


def test_upload_unsupported_format(session_token, job_id):
    response = client.post(
        f"/api/v1/jobs/{job_id}/upload",
        files={"file": ("test.txt", b"isi teks", "text/plain")},
        headers={"X-Session-Token": session_token},
    )
    assert response.status_code == 415
