
import sys
import os
import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.main import app

client = TestClient(app)

def test_root():
	response = client.get("/")
	assert response.status_code == 200
	assert "Welcome" in response.json().get("message", "")

def test_status():
	response = client.get("/status")
	assert response.status_code == 200
	assert response.json()["status"] == "ok"

def test_llm_endpoint():
	payload = {"prompt": "Hello, world!"}
	response = client.post("/chat/llm", json=payload)
	# Should return 200 or 500 if no API key is set
	assert response.status_code in (200, 500)
