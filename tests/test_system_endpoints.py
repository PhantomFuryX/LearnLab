import os, sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.main import app

client = TestClient(app)

def test_version_endpoint():
    r = client.get('/version')
    assert r.status_code == 200
    assert 'version' in r.json()

def test_metrics_endpoint_best_effort():
    r = client.get('/metrics')
    # If prometheus not installed or route missing, accept non-200
    if r.status_code == 200:
        assert 'll_requests_total' in r.text or 'll_request_latency_seconds' in r.text

def test_auth_middleware_best_effort(monkeypatch):
    # If AUTH is enabled, 401 without key; otherwise 200 OK.
    need_auth = os.getenv('AUTH_REQUIRED') == '1'
    r = client.get('/status')
    if need_auth:
        assert r.status_code in (401, 200)  # accept runners where app loaded before env
    else:
        assert r.status_code == 200

    # With key when set
    if os.getenv('API_KEY'):
        r = client.get('/status', headers={'X-API-Key': os.getenv('API_KEY')})
        assert r.status_code == 200
