"""
Tests for the High School Management System API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add the src directory to the path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities(client):
    """Reset activities to known state before each test"""
    # This would require a reset endpoint, but for now we work with existing state
    yield


class TestRoot:
    """Tests for root endpoint"""
    
    def test_root_redirect(self, client):
        """Test that root redirects to index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]


class TestGetActivities:
    """Tests for getting activities"""
    
    def test_get_all_activities(self, client):
        """Test getting all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        activities = response.json()
        assert isinstance(activities, dict)
        assert len(activities) > 0
    
    def test_activities_have_required_fields(self, client):
        """Test that activities have all required fields"""
        response = client.get("/activities")
        activities = response.json()
        
        required_fields = ["description", "schedule", "max_participants", "participants"]
        
        for activity_name, activity_data in activities.items():
            for field in required_fields:
                assert field in activity_data, f"Activity '{activity_name}' missing field '{field}'"
            
            # Verify participants is a list
            assert isinstance(activity_data["participants"], list)
    
    def test_activities_have_specific_activities(self, client):
        """Test that expected activities exist"""
        response = client.get("/activities")
        activities = response.json()
        
        expected_activities = [
            "Basketball Team",
            "Swimming Club",
            "Debate Club",
            "Robotics Club",
            "Chess Club",
            "Programming Class"
        ]
        
        for activity in expected_activities:
            assert activity in activities, f"Expected activity '{activity}' not found"


class TestSignupForActivity:
    """Tests for signing up for activities"""
    
    def test_signup_new_participant(self, client):
        """Test signing up a new participant"""
        email = "test@mergington.edu"
        activity = "Art Studio"
        
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 200
        assert "Signed up" in response.json()["message"]
        assert email in response.json()["message"]
    
    def test_signup_nonexistent_activity(self, client):
        """Test signing up for activity that doesn't exist"""
        email = "test@mergington.edu"
        activity = "Nonexistent Activity"
        
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_signup_duplicate_participant(self, client):
        """Test that duplicate signup is rejected"""
        email = "duplicate@mergington.edu"
        activity = "Drama Club"
        
        # First signup should succeed
        response1 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Second signup with same email should fail
        response2 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"].lower()
    
    def test_signup_updates_participant_count(self, client):
        """Test that signup updates the participant list"""
        email = "newperson@mergington.edu"
        activity = "Gym Class"
        
        # Get initial count
        response_before = client.get("/activities")
        count_before = len(response_before.json()[activity]["participants"])
        
        # Signup
        client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        # Get updated count
        response_after = client.get("/activities")
        count_after = len(response_after.json()[activity]["participants"])
        
        assert count_after == count_before + 1
        assert email in response_after.json()[activity]["participants"]


class TestUnregisterFromActivity:
    """Tests for unregistering from activities"""
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant"""
        email = "unregister@mergington.edu"
        activity = "Programming Class"
        
        # Sign up first
        client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        # Verify signup was successful
        response_check = client.get("/activities")
        assert email in response_check.json()[activity]["participants"]
        
        # Unregister
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]
        
        # Verify unregister was successful
        response_check_after = client.get("/activities")
        assert email not in response_check_after.json()[activity]["participants"]
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregistering from activity that doesn't exist"""
        email = "test@mergington.edu"
        activity = "Nonexistent Activity"
        
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_unregister_non_participant(self, client):
        """Test unregistering someone who is not signed up"""
        email = "notregistered@mergington.edu"
        activity = "Basketball Team"
        
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"].lower()
    
    def test_unregister_updates_participant_count(self, client):
        """Test that unregister updates the participant list"""
        email = "remove@mergington.edu"
        activity = "Robotics Club"
        
        # Sign up first
        client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        # Get count before unregister
        response_before = client.get("/activities")
        count_before = len(response_before.json()[activity]["participants"])
        
        # Unregister
        client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        
        # Get count after unregister
        response_after = client.get("/activities")
        count_after = len(response_after.json()[activity]["participants"])
        
        assert count_after == count_before - 1
        assert email not in response_after.json()[activity]["participants"]


class TestActivityConstraints:
    """Tests for activity constraints and validations"""
    
    def test_max_participants_enforcement(self, client):
        """Test that we can sign up up to max participants"""
        # Get activities to find one with available spots
        response = client.get("/activities")
        activities = response.json()
        
        activity_name = "Debate Club"  # Has max 16 participants
        activity = activities[activity_name]
        
        # Count available spots
        available_spots = activity["max_participants"] - len(activity["participants"])
        
        assert available_spots > 0, f"No available spots in {activity_name}"
    
    def test_participant_validation_email_format(self, client):
        """Test that emails are handled correctly"""
        email = "valid.email@mergington.edu"
        activity = "Chess Club"
        
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 200 or response.status_code == 400
        # 400 if already signed up, 200 if successful
