"""Tests for Todoist client functionality."""

from unittest.mock import Mock, patch

import pytest
import requests

from src.todoist_client import (
    TodoistAPIError,
    TodoistClient,
    TodoistComment,
    TodoistProject,
    TodoistTask,
)


class TestTodoistModels:
    """Test Pydantic models for Todoist data."""

    def test_todoist_project_creation(self):
        """Test creating a TodoistProject from data."""
        data = {
            "id": "123",
            "name": "Test Project",
            "color": "red",
            "is_shared": False,
            "url": "https://todoist.com/showProject?id=123",
        }
        project = TodoistProject(**data)
        assert project.id == "123"
        assert project.name == "Test Project"
        assert project.is_shared is False

    def test_todoist_task_creation(self):
        """Test creating a TodoistTask from data."""
        data = {
            "id": "456",
            "content": "Test Task",
            "description": "Test description",
            "project_id": "123",
            "order": 1,
            "priority": 3,
            "labels": ["urgent", "work"],
            "due": {"date": "2024-01-15"},
            "url": "https://todoist.com/showTask?id=456",
            "comment_count": 2,
            "is_completed": False,
            "created_at": "2024-01-10T10:00:00Z",
        }
        task = TodoistTask(**data)
        assert task.id == "456"
        assert task.content == "Test Task"
        assert task.priority == 3
        assert task.priority_text == "Medium"
        assert task.due_date == "2024-01-15"

    def test_todoist_task_priority_text(self):
        """Test priority text conversion."""
        task_data = {
            "id": "1",
            "content": "Task",
            "project_id": "123",
            "order": 1,
            "created_at": "2024-01-10T10:00:00Z",
        }

        # Test different priorities
        priorities = {4: "High", 3: "Medium", 2: "Low", 1: "None"}
        for priority, expected_text in priorities.items():
            task_data["priority"] = priority
            task = TodoistTask(**task_data)
            assert task.priority_text == expected_text

    def test_todoist_comment_creation(self):
        """Test creating a TodoistComment from data."""
        data = {
            "id": "789",
            "task_id": "456",
            "content": "This is a comment",
            "posted_at": "2024-01-11T15:30:00Z",
        }
        comment = TodoistComment(**data)
        assert comment.id == "789"
        assert comment.task_id == "456"
        assert comment.content == "This is a comment"


class TestTodoistClient:
    """Test TodoistClient functionality."""

    @patch.dict("os.environ", {"TODOIST_API_TOKEN": "test_token"})
    def test_client_initialization_with_env_var(self):
        """Test client initialization with environment variable."""
        client = TodoistClient()
        assert client.api_token == "test_token"
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "Bearer test_token"

    def test_client_initialization_with_token(self):
        """Test client initialization with direct token."""
        client = TodoistClient(api_token="direct_token")
        assert client.api_token == "direct_token"
        assert client.headers["Authorization"] == "Bearer direct_token"

    def test_client_initialization_no_token(self):
        """Test client initialization fails without token."""
        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(TodoistAPIError, match="API token is required"),
        ):
            TodoistClient()

    @pytest.fixture
    def mock_client(self):
        """Create a mock client for testing."""
        return TodoistClient(api_token="test_token")

    def test_make_request_success(self, mock_client):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}

        with patch.object(mock_client.session, "request", return_value=mock_response):
            result = mock_client._make_request("GET", "/test")
            assert result == {"test": "data"}

    def test_make_request_no_content(self, mock_client):
        """Test API request with 204 No Content response."""
        mock_response = Mock()
        mock_response.status_code = 204

        with patch.object(mock_client.session, "request", return_value=mock_response):
            result = mock_client._make_request("GET", "/test")
            assert result is None

    def test_make_request_failure(self, mock_client):
        """Test failed API request."""
        with (
            patch.object(
                mock_client.session,
                "request",
                side_effect=requests.exceptions.RequestException("Network error"),
            ),
            pytest.raises(TodoistAPIError, match="Failed to make request"),
        ):
            mock_client._make_request("GET", "/test")

    def test_get_projects(self, mock_client):
        """Test getting projects."""
        mock_projects_data = [
            {
                "id": "123",
                "name": "Project 1",
                "color": "red",
                "is_shared": False,
                "url": "",
            },
            {
                "id": "456",
                "name": "Project 2",
                "color": "blue",
                "is_shared": True,
                "url": "",
            },
        ]

        with patch.object(
            mock_client, "_make_request", return_value=mock_projects_data
        ):
            projects = mock_client.get_projects()
            assert len(projects) == 2
            assert isinstance(projects[0], TodoistProject)
            assert projects[0].name == "Project 1"
            assert projects[1].is_shared is True

    def test_get_tasks(self, mock_client):
        """Test getting tasks."""
        mock_tasks_data = [
            {
                "id": "789",
                "content": "Task 1",
                "description": "",
                "project_id": "123",
                "order": 1,
                "priority": 1,
                "labels": [],
                "comment_count": 0,
                "is_completed": False,
                "created_at": "2024-01-10T10:00:00Z",
                "url": "",
                "creator_id": "",
            }
        ]

        with patch.object(mock_client, "_make_request", return_value=mock_tasks_data):
            tasks = mock_client.get_tasks()
            assert len(tasks) == 1
            assert isinstance(tasks[0], TodoistTask)
            assert tasks[0].content == "Task 1"

    def test_get_tasks_with_project_filter(self, mock_client):
        """Test getting tasks filtered by project."""
        with patch.object(
            mock_client, "_make_request", return_value=[]
        ) as mock_request:
            mock_client.get_tasks(project_id="123")
            mock_request.assert_called_once_with(
                "GET", "/tasks", params={"project_id": "123"}
            )

    def test_get_tasks_with_filter_expression(self, mock_client):
        """Test getting tasks with filter expression."""
        with patch.object(
            mock_client, "_make_request", return_value=[]
        ) as mock_request:
            mock_client.get_tasks(filter_expr="today")
            mock_request.assert_called_once_with(
                "GET", "/tasks", params={"filter": "today"}
            )

    def test_get_task_comments(self, mock_client):
        """Test getting task comments."""
        mock_comments_data = [
            {
                "id": "comment1",
                "task_id": "789",
                "content": "First comment",
                "posted_at": "2024-01-11T10:00:00Z",
            },
            {
                "id": "comment2",
                "task_id": "789",
                "content": "Second comment",
                "posted_at": "2024-01-11T11:00:00Z",
            },
        ]

        with patch.object(
            mock_client, "_make_request", return_value=mock_comments_data
        ):
            comments = mock_client.get_task_comments("789")
            assert len(comments) == 2
            assert isinstance(comments[0], TodoistComment)
            assert comments[0].content == "First comment"

    def test_test_connection_success(self, mock_client):
        """Test successful connection test."""
        with patch.object(mock_client, "get_projects", return_value=[]):
            assert mock_client.test_connection() is True

    def test_test_connection_failure(self, mock_client):
        """Test failed connection test."""
        with patch.object(
            mock_client,
            "get_projects",
            side_effect=TodoistAPIError("Connection failed"),
        ):
            assert mock_client.test_connection() is False


class TestTodoistClientIntegration:
    """Integration tests for TodoistClient (requires network/mocking)."""

    def test_url_construction(self):
        """Test that URLs are constructed correctly."""
        client = TodoistClient(api_token="test")

        # Test that the base URL is used correctly
        with patch.object(client.session, "request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_request.return_value = mock_response

            client._make_request("GET", "/projects")

            # Check that the full URL was constructed correctly
            args, kwargs = mock_request.call_args
            assert args[1] == "https://api.todoist.com/rest/v2/projects"

    def test_headers_are_set(self):
        """Test that headers are set correctly."""
        client = TodoistClient(api_token="test_token")

        expected_headers = {
            "Authorization": "Bearer test_token",
            "Content-Type": "application/json",
        }

        for key, value in expected_headers.items():
            assert client.headers[key] == value
            assert client.session.headers[key] == value
