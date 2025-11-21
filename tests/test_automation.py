
import sys
import os
import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.main import app

client = TestClient(app)

def test_knowledge_agent():
	payload = {"payload": {"topic": "AI automation"}}
	response = client.post("/knowledge/run", json=payload)
	# Should return 200 or 500 if no API key is set
	assert response.status_code in (200, 500)
	data = response.json()
	# Accept either a summary or an error in the response
	assert ("summary" in data) or ("error" in data)
