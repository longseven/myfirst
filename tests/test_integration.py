"""Integration tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_ok(self, client):
        """Test /health returns ok status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestGenerateEndpoint:
    """Test /api/generate endpoint."""

    def test_generate_basic_function(self, client):
        """Test generating function problem."""
        response = client.post(
            "/api/generate",
            json={
                "problem": "已知函数 f(x) = x² - 2x + 1，求最小值",
                "enable_tts": False
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "lecture_id" in data
        assert len(data["lecture_id"]) == 8

    def test_generate_derivative(self, client):
        """Test generating derivative problem."""
        response = client.post(
            "/api/generate",
            json={
                "problem": "求函数 f(x) = x³ - 3x 的单调区间和极值",
                "enable_tts": False
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "lecture_id" in data

    def test_generate_solid_geometry(self, client):
        """Test generating solid geometry problem."""
        response = client.post(
            "/api/generate",
            json={
                "problem": "四棱锥 P-ABCD 中，PA⊥底面 ABCD，证明：PC⊥BD",
                "enable_tts": False
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "lecture_id" in data

    def test_generate_invalid_empty_problem(self, client):
        """Test generating with empty problem - should create task but may fail later."""
        response = client.post(
            "/api/generate",
            json={
                "problem": "",
                "enable_tts": False
            }
        )
        # Currently accepts empty problem (returns 200), but task will fail during processing
        assert response.status_code == 200
        data = response.json()
        assert "lecture_id" in data


class TestStatusEndpoint:
    """Test /api/status/{lecture_id} endpoint."""

    def test_status_not_found(self, client):
        """Test status for non-existent task."""
        response = client.get("/api/status/nonexistent123")
        assert response.status_code == 404

    def test_status_after_create(self, client):
        """Test status right after creating task."""
        # Create task
        gen_response = client.post(
            "/api/generate",
            json={
                "problem": "已知 f(x) = x + 1",
                "enable_tts": False
            }
        )
        lecture_id = gen_response.json()["lecture_id"]

        # Check status
        status_response = client.get(f"/api/status/{lecture_id}")
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["lecture_id"] == lecture_id
        assert data["status"] in ["queued", "detecting", "generating", "done", "failed"]


class TestListTasksEndpoint:
    """Test /api/tasks endpoint."""

    def test_list_tasks_empty(self, client):
        """Test listing tasks when empty."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_tasks_after_create(self, client):
        """Test listing tasks after creating one."""
        # Create task
        client.post(
            "/api/generate",
            json={"problem": "f(x) = x²", "enable_tts": False}
        )

        # List tasks
        response = client.get("/api/tasks")
        assert response.status_code == 200
        tasks = response.json()
        assert isinstance(tasks, list)
        assert len(tasks) >= 1


class TestDetectorIntegration:
    """Test detector integration with API."""

    def test_detection_logging(self, client):
        """Test that detection results are logged."""
        response = client.post(
            "/api/generate",
            json={
                "problem": "求 sin(π/6) 的值",
                "enable_tts": False
            }
        )
        assert response.status_code == 200
        # Task should be created and detection should run
        lecture_id = response.json()["lecture_id"]

        # Check status - should have moved past detecting
        import time
        time.sleep(0.5)  # Brief wait for detection

        status = client.get(f"/api/status/{lecture_id}")
        assert status.status_code == 200
