"""
Integration tests for Phase 2 Planner + Calendar
Run with: pytest tests/test_planner_integration.py -v
"""

import pytest
import json
from datetime import datetime
from typing import Dict, Any

# Fixtures

@pytest.fixture
def sample_user():
    """Sample user for testing"""
    return {
        "user_id": "test_user_123",
        "email": "test@example.com",
        "scopes": ["query"],
        "roles": ["user"],
    }

@pytest.fixture
def sample_plan_request() -> Dict[str, Any]:
    """Sample plan creation request"""
    return {
        "goal": "Master agentic AI in 4 weeks",
        "skill_level": "intermediate",
        "hours_per_week": 5,
        "duration_weeks": 4,
        "topics": ["agent architectures", "tool use", "agentic loops"],
        "include_past_summaries": False,
    }

@pytest.fixture
def sample_progress_request() -> Dict[str, Any]:
    """Sample module progress request"""
    return {
        "status": "completed",
        "time_spent_hours": 5.5,
        "quiz_score": 85.0,
        "notes": "Great module, learned a lot",
    }

# ============================================================================
# UNIT TESTS
# ============================================================================

def test_planner_agent_import():
    """Test that PlannerAgent imports correctly"""
    try:
        from backend.core.agents.planner_agent import PlannerAgent
        assert PlannerAgent is not None
    except ImportError as e:
        pytest.fail(f"Failed to import PlannerAgent: {e}")

def test_models_import():
    """Test that models import correctly"""
    try:
        from backend.core.models_planner import (
            CreatePlanRequest,
            PlanResponse,
            ModuleProgressRequest,
            ProgressResponse,
        )
        assert all([CreatePlanRequest, PlanResponse, ModuleProgressRequest, ProgressResponse])
    except ImportError as e:
        pytest.fail(f"Failed to import models: {e}")

def test_create_plan_request_validation():
    """Test CreatePlanRequest validation"""
    from backend.core.models_planner import CreatePlanRequest
    
    # Valid request
    req = CreatePlanRequest(
        goal="Learn AI",
        skill_level="intermediate",
        hours_per_week=5,
        duration_weeks=4,
        topics=["AI", "ML"],
    )
    assert req.goal == "Learn AI"
    assert req.hours_per_week == 5

def test_create_plan_request_invalid():
    """Test CreatePlanRequest with invalid data"""
    from backend.core.models_planner import CreatePlanRequest
    from pydantic import ValidationError
    
    with pytest.raises(ValidationError):
        CreatePlanRequest(
            goal="Learn AI",
            skill_level="invalid_level",  # Invalid enum
            hours_per_week=5,
            duration_weeks=4,
            topics=["AI"],
        )

# ============================================================================
# INTEGRATION TESTS (requires MongoDB + running API)
# ============================================================================

@pytest.mark.integration
def test_create_learning_plan_endpoint(client, sample_user, sample_plan_request):
    """Test POST /api/v1/plans endpoint"""
    # Mock authentication
    headers = {"Authorization": f"Bearer {create_test_token(sample_user)}"}
    
    response = client.post(
        "/api/v1/plans",
        json=sample_plan_request,
        headers=headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "plan_id" in data
    assert data["plan_title"]
    assert data["total_hours_estimated"] == 20  # 5 hours/week * 4 weeks

@pytest.mark.integration
def test_get_learning_plan_endpoint(client, sample_user, plan_id):
    """Test GET /api/v1/plans/{plan_id} endpoint"""
    headers = {"Authorization": f"Bearer {create_test_token(sample_user)}"}
    
    response = client.get(
        f"/api/v1/plans/{plan_id}",
        headers=headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["_id"] == plan_id
    assert data["user_id"] == sample_user["user_id"]

@pytest.mark.integration
def test_list_user_plans_endpoint(client, sample_user):
    """Test GET /api/v1/plans endpoint"""
    headers = {"Authorization": f"Bearer {create_test_token(sample_user)}"}
    
    response = client.get(
        "/api/v1/plans?status=active&limit=10",
        headers=headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "plans" in data
    assert "count" in data

@pytest.mark.integration
def test_mark_module_complete_endpoint(client, sample_user, plan_id, module_id, sample_progress_request):
    """Test PATCH /api/v1/plans/{plan_id}/modules/{module_id} endpoint"""
    headers = {"Authorization": f"Bearer {create_test_token(sample_user)}"}
    
    response = client.patch(
        f"/api/v1/plans/{plan_id}/modules/{module_id}",
        json=sample_progress_request,
        headers=headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["plan_id"] == plan_id
    assert len(data["completed_modules"]) > 0

@pytest.mark.integration
def test_get_progress_endpoint(client, sample_user, plan_id):
    """Test GET /api/v1/plans/{plan_id}/progress endpoint"""
    headers = {"Authorization": f"Bearer {create_test_token(sample_user)}"}
    
    response = client.get(
        f"/api/v1/plans/{plan_id}/progress",
        headers=headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "plan_id" in data
    assert "completed_modules" in data
    assert "completion_percentage" in data

@pytest.mark.integration
def test_create_reminder_endpoint(client, sample_user, plan_id):
    """Test POST /api/v1/plans/{plan_id}/reminders endpoint"""
    headers = {"Authorization": f"Bearer {create_test_token(sample_user)}"}
    
    reminder_request = {
        "type": "email",
        "schedule": "every_sunday_19:00",
        "enabled": True,
    }
    
    response = client.post(
        f"/api/v1/plans/{plan_id}/reminders",
        json=reminder_request,
        headers=headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "reminder_id" in data
    assert data["type"] == "email"

@pytest.mark.integration
def test_export_calendar_endpoint(client, plan_id, ical_token):
    """Test GET /api/v1/plans/{plan_id}/calendar.ics endpoint"""
    response = client.get(
        f"/api/v1/plans/{plan_id}/calendar.ics?token={ical_token}",
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/calendar"
    assert b"BEGIN:VCALENDAR" in response.content

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_test_token(user: Dict[str, Any]) -> str:
    """Create a test JWT token"""
    from backend.utils.auth import create_access_token
    return create_access_token(
        user["user_id"],
        user["email"],
        user["scopes"],
        user["roles"],
    )

# ============================================================================
# CONFTEST FIXTURES (if using pytest conftest)
# ============================================================================

# Add this to conftest.py:
# @pytest.fixture
# def client():
#     """FastAPI test client"""
#     from fastapi.testclient import TestClient
#     from backend.main import app
#     return TestClient(app)
#
# @pytest.fixture(scope="session")
# def setup_test_db():
#     """Setup test MongoDB database"""
#     # Create separate test database
#     # Yield for tests
#     # Cleanup after tests
#     pass
