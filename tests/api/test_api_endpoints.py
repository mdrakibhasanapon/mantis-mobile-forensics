import pytest
from fastapi.testclient import TestClient
from mmf_api.main import app
from mmf_core.security.protection import SESSION_TOKEN_ENV_VAR
import os

client = TestClient(app)

def test_api_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["app"] == "Mantis Mobile Forensics (MMF)"
    assert data["status"] == "healthy"

def test_api_case_creation_and_listing(tmp_path):
    os.environ[SESSION_TOKEN_ENV_VAR] = "TEST_TOKEN_123"
    headers = {"X-MMF-Session-Token": "TEST_TOKEN_123"}
    
    # Unauthorized test
    unauth_resp = client.get("/cases", headers={"X-MMF-Session-Token": "BAD"})
    assert unauth_resp.status_code == 401

    # Authorized creation test
    create_payload = {
        "case_number": "CASE-API-001",
        "title": "API Test Case",
        "investigator": "Forensic Analyst",
        "agency": "State Police"
    }
    create_resp = client.post("/cases", json=create_payload, headers=headers)
    assert create_resp.status_code == 200
    case_data = create_resp.json()
    assert case_data["case_number"] == "CASE-API-001"

    # List cases
    list_resp = client.get("/cases", headers=headers)
    assert list_resp.status_code == 200
    cases = list_resp.json()
    assert any(c["case_number"] == "CASE-API-001" for c in cases)

def test_api_device_status(tmp_path):
    headers = {"X-MMF-Session-Token": "TEST_TOKEN_123"}
    resp = client.get("/devices/status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "adb" in data
    assert "supported_methods" in data
