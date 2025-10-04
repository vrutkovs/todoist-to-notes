"""Tests for Todoist client functionality."""

from unittest.mock import Mock, patch

import pytest

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
            "attachment": None,
        }
        comment = TodoistComment(**data)
        assert comment.id == "789"
        assert comment.task_id == "456"
        assert comment.content == "This is a comment"

    def test_todoist_project_from_api_project(self):
        """Test creating TodoistProject from API project object."""
        # Mock API project object
        api_project = Mock()
        api_project.id = "123"
        api_project.name = "Test Project"
        api_project.color = "red"
        api_project.is_shared = False
        api_project.url = "https://todoist.com/showProject?id=123"

        project = TodoistProject.from_api_project(api_project)
        assert project.id == "123"
        assert project.name == "Test Project"
        assert project.color == "red"
        assert project.is_shared is False
        assert project.url == "https://todoist.com/showProject?id=123"

    def test_todoist_task_from_api_task(self):
        """Test creating TodoistTask from API task object."""
        # Mock API task object
        api_task = Mock()
        api_task.id = "456"
        api_task.content = "Test Task"
        api_task.description = "Test description"
        api_task.project_id = "123"
        api_task.section_id = None
        api_task.parent_id = None
        api_task.order = 1
        api_task.priority = 3
        api_task.labels = ["urgent", "work"]
        api_task.url = "https://todoist.com/showTask?id=456"
        api_task.comment_count = 2
        api_task.is_completed = False
        api_task.created_at = "2024-01-10T10:00:00Z"
        api_task.creator_id = "user123"
        api_task.assignee_id = None
        api_task.assigner_id = None

        # Mock due object
        api_task.due = Mock()
        api_task.due.date = "2024-01-15"
        api_task.due.string = "tomorrow"
        api_task.due.datetime = None
        api_task.due.timezone = None
        api_task.due.is_recurring = False

        task = TodoistTask.from_api_task(api_task)
        assert task.id == "456"
        assert task.content == "Test Task"
        assert task.priority == 3
        assert task.due_date == "2024-01-15"

    def test_todoist_comment_from_api_comment(self):
        """Test creating TodoistComment from API comment object."""
        # Mock API comment object
        api_comment = Mock()
        api_comment.id = "789"
        api_comment.task_id = "456"
        api_comment.content = "This is a comment"
        api_comment.posted_at = "2024-01-11T15:30:00Z"
        api_comment.attachment = None

        comment = TodoistComment.from_api_comment(api_comment)
        assert comment.id == "789"
        assert comment.task_id == "456"
        assert comment.content == "This is a comment"
        assert comment.posted_at == "2024-01-11T15:30:00Z"
        assert comment.attachment is None

    def test_todoist_comment_from_api_comment_with_null_task_id(self):
        """Test creating TodoistComment from API comment object with null task_id (project comment)."""
        # Mock API comment object for project comment
        api_comment = Mock()
        api_comment.id = "789"
        api_comment.task_id = None  # Project comments have null task_id
        api_comment.content = "This is a project comment"
        api_comment.posted_at = "2024-01-11T15:30:00Z"
        api_comment.attachment = None

        comment = TodoistComment.from_api_comment(api_comment)
        assert comment.id == "789"
        assert comment.task_id == ""  # Should convert None to empty string
        assert comment.content == "This is a project comment"
        assert comment.posted_at == "2024-01-11T15:30:00Z"
        assert comment.attachment is None

    def test_todoist_comment_from_api_comment_with_attachment(self):
        """Test creating TodoistComment from API comment object with attachment."""
        # Mock API comment object with attachment
        api_comment = Mock()
        api_comment.id = "789"
        api_comment.task_id = "456"
        api_comment.content = "This is a comment with attachment"
        api_comment.posted_at = "2024-01-11T15:30:00Z"

        # Mock attachment
        mock_attachment = Mock()
        mock_attachment.file_name = "document.pdf"
        mock_attachment.file_type = "application/pdf"
        mock_attachment.file_url = "https://example.com/document.pdf"
        mock_attachment.resource_type = "file"
        api_comment.attachment = mock_attachment

        comment = TodoistComment.from_api_comment(api_comment)
        assert comment.id == "789"
        assert comment.task_id == "456"
        assert comment.content == "This is a comment with attachment"
        assert comment.posted_at == "2024-01-11T15:30:00Z"
        assert comment.attachment is not None
        assert comment.attachment["file_name"] == "document.pdf"
        assert comment.attachment["file_type"] == "application/pdf"
        assert comment.attachment["file_url"] == "https://example.com/document.pdf"
        assert comment.attachment["resource_type"] == "file"


class TestTodoistClient:
    """Test TodoistClient functionality."""

    @patch.dict("os.environ", {"TODOIST_API_TOKEN": "test_token"})
    @patch("src.todoist_client.TodoistAPI")
    def test_client_initialization_with_env_var(self, mock_api_class):
        """Test client initialization with environment variable."""
        mock_api_instance = Mock()
        mock_api_class.return_value = mock_api_instance

        client = TodoistClient()
        assert client.api_token == "test_token"
        mock_api_class.assert_called_once_with("test_token")

    @patch("src.todoist_client.TodoistAPI")
    def test_client_initialization_with_token(self, mock_api_class):
        """Test client initialization with direct token."""
        mock_api_instance = Mock()
        mock_api_class.return_value = mock_api_instance

        client = TodoistClient(api_token="direct_token")
        assert client.api_token == "direct_token"
        mock_api_class.assert_called_once_with("direct_token")

    def test_client_initialization_no_token(self):
        """Test client initialization fails without token."""
        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(TodoistAPIError, match="API token is required"),
        ):
            TodoistClient()

    @patch("src.todoist_client.TodoistAPI")
    def test_client_initialization_api_failure(self, mock_api_class):
        """Test client initialization fails when API initialization fails."""
        mock_api_class.side_effect = Exception("API initialization failed")

        with pytest.raises(
            TodoistAPIError, match="Failed to initialize Todoist API client"
        ):
            TodoistClient(api_token="test_token")

    @pytest.fixture
    def mock_client(self):
        """Create a mock client for testing."""
        with patch("src.todoist_client.TodoistAPI") as mock_api_class:
            mock_api_instance = Mock()
            mock_api_class.return_value = mock_api_instance
            client = TodoistClient(api_token="test_token")
            client._api = mock_api_instance
            return client

    def test_get_projects(self, mock_client):
        """Test getting projects."""
        # Mock API project objects
        mock_project = Mock()
        mock_project.id = "123"
        mock_project.name = "Project 1"
        mock_project.color = "red"
        mock_project.is_shared = False
        mock_project.url = ""

        # Mock the paginator by making it iterable with pages of projects
        mock_client._api.get_projects.return_value = iter([[mock_project]])

        projects = mock_client.get_projects()
        assert len(projects) == 1
        assert isinstance(projects[0], TodoistProject)
        assert projects[0].name == "Project 1"

    def test_get_projects_failure(self, mock_client):
        """Test getting projects with API failure."""
        mock_client._api.get_projects.side_effect = Exception("API Error")

        with pytest.raises(TodoistAPIError, match="Failed to fetch projects"):
            mock_client.get_projects()

    def test_get_tasks(self, mock_client):
        """Test getting tasks."""
        # Mock API task object
        mock_task = Mock()
        mock_task.id = "789"
        mock_task.content = "Task 1"
        mock_task.description = ""
        mock_task.project_id = "123"
        mock_task.section_id = None
        mock_task.parent_id = None
        mock_task.order = 1
        mock_task.priority = 1
        mock_task.labels = []
        mock_task.due = None
        mock_task.url = ""
        mock_task.comment_count = 0
        mock_task.is_completed = False
        mock_task.created_at = "2024-01-10T10:00:00Z"
        mock_task.creator_id = ""
        mock_task.assignee_id = None
        mock_task.assigner_id = None

        # Mock the paginator by making it iterable with pages of tasks
        mock_client._api.get_tasks.return_value = iter([[mock_task]])

        tasks = mock_client.get_tasks()
        assert len(tasks) == 1
        assert isinstance(tasks[0], TodoistTask)
        assert tasks[0].content == "Task 1"

    def test_get_tasks_with_project_filter(self, mock_client):
        """Test getting tasks filtered by project."""
        mock_client._api.get_tasks.return_value = iter([[]])

        mock_client.get_tasks(project_id="123")
        mock_client._api.get_tasks.assert_called_once_with(project_id="123")

    def test_get_tasks_with_filter_expression(self, mock_client):
        """Test getting tasks with filter expression."""
        mock_client._api.filter_tasks.return_value = iter([[]])

        mock_client.get_tasks(filter_expr="today")
        mock_client._api.filter_tasks.assert_called_once_with(query="today")

    def test_get_tasks_failure(self, mock_client):
        """Test getting tasks with API failure."""
        mock_client._api.get_tasks.side_effect = Exception("API Error")

        with pytest.raises(TodoistAPIError, match="Failed to fetch tasks"):
            mock_client.get_tasks()

    def test_get_task_comments(self, mock_client):
        """Test getting task comments."""
        # Mock API comment object
        mock_comment = Mock()
        mock_comment.id = "comment1"
        mock_comment.task_id = "789"
        mock_comment.content = "First comment"
        mock_comment.posted_at = "2024-01-11T10:00:00Z"
        mock_comment.attachment = None

        # Mock the iterator that yields pages of comments
        mock_client._api.get_comments.return_value = [[mock_comment]]

        comments = mock_client.get_task_comments("789")
        assert len(comments) == 1
        assert isinstance(comments[0], TodoistComment)
        assert comments[0].content == "First comment"
        assert comments[0].task_id == "789"
        assert comments[0].posted_at == "2024-01-11T10:00:00Z"

    def test_get_task_comments_failure(self, mock_client):
        """Test getting task comments with API failure."""
        mock_client._api.get_comments.side_effect = Exception("API Error")

        with pytest.raises(TodoistAPIError, match="Failed to fetch comments for task"):
            mock_client.get_task_comments("789")

    def test_get_task_comments_comprehensive(self, mock_client):
        """Test comprehensive comment fetching with multiple comments and edge cases."""
        # Mock multiple API comment objects
        comment1 = Mock()
        comment1.id = "comment1"
        comment1.task_id = "789"
        comment1.content = "First comment"
        comment1.posted_at = "2024-01-11T10:00:00Z"
        comment1.attachment = None

        comment2 = Mock()
        comment2.id = "comment2"
        comment2.task_id = "789"
        comment2.content = "Second comment with attachment"
        comment2.posted_at = "2024-01-11T11:00:00Z"

        # Mock attachment for second comment
        mock_attachment = Mock()
        mock_attachment.file_name = "document.pdf"
        mock_attachment.file_type = "application/pdf"
        mock_attachment.file_url = "https://example.com/document.pdf"
        mock_attachment.resource_type = "file"
        comment2.attachment = mock_attachment

        comment3 = Mock()
        comment3.id = "comment3"
        comment3.task_id = None  # Project comment case
        comment3.content = "Project comment"
        comment3.posted_at = "2024-01-11T12:00:00Z"
        comment3.attachment = None

        # Mock the iterator that yields pages of comments
        mock_client._api.get_comments.return_value = [[comment1, comment2], [comment3]]

        comments = mock_client.get_task_comments("789")

        # Verify we got all comments
        assert len(comments) == 3

        # Verify first comment
        assert comments[0].id == "comment1"
        assert comments[0].task_id == "789"
        assert comments[0].content == "First comment"
        assert comments[0].posted_at == "2024-01-11T10:00:00Z"
        assert comments[0].attachment is None

        # Verify second comment with attachment
        assert comments[1].id == "comment2"
        assert comments[1].task_id == "789"
        assert comments[1].content == "Second comment with attachment"
        assert comments[1].posted_at == "2024-01-11T11:00:00Z"
        assert comments[1].attachment is not None
        assert comments[1].attachment["file_name"] == "document.pdf"
        assert comments[1].attachment["file_type"] == "application/pdf"
        assert comments[1].attachment["file_url"] == "https://example.com/document.pdf"
        assert comments[1].attachment["resource_type"] == "file"

        # Verify third comment (project comment with None task_id)
        assert comments[2].id == "comment3"
        assert comments[2].task_id == ""  # Should be converted to empty string
        assert comments[2].content == "Project comment"
        assert comments[2].posted_at == "2024-01-11T12:00:00Z"
        assert comments[2].attachment is None

    def test_get_task_comments_empty_response(self, mock_client):
        """Test getting task comments when no comments exist."""
        # Mock empty iterator
        mock_client._api.get_comments.return_value = [[]]

        comments = mock_client.get_task_comments("789")
        assert len(comments) == 0
        assert isinstance(comments, list)

    def test_get_completed_tasks(self, mock_client):
        """Test getting completed tasks."""
        mock_client._api.get_completed_tasks_by_completion_date.return_value = iter(
            [[]]
        )

        # Mock get_projects for project name lookup
        with patch.object(mock_client, "get_projects", return_value=[]):
            mock_client.get_completed_tasks()
            # Verify the method was called with datetime parameters
            mock_client._api.get_completed_tasks_by_completion_date.assert_called_once()
            call_args = (
                mock_client._api.get_completed_tasks_by_completion_date.call_args
            )
            assert call_args.kwargs["filter_query"] is None
            assert "since" in call_args.kwargs
            assert "until" in call_args.kwargs

    def test_get_completed_tasks_with_project(self, mock_client):
        """Test getting completed tasks with project filter."""
        # Mock project with proper attributes
        mock_project = Mock()
        mock_project.id = "123"
        mock_project.name = "Test Project"
        mock_project.color = "red"
        mock_project.is_shared = False
        mock_project.url = ""

        mock_client._api.get_completed_tasks_by_completion_date.return_value = iter(
            [[]]
        )

        with patch.object(
            mock_client,
            "get_projects",
            return_value=[TodoistProject.from_api_project(mock_project)],
        ):
            mock_client.get_completed_tasks(project_id="123")
            # Verify the method was called with project filter
            call_args = (
                mock_client._api.get_completed_tasks_by_completion_date.call_args
            )
            assert call_args.kwargs["filter_query"] == "#Test Project"
            assert "since" in call_args.kwargs
            assert "until" in call_args.kwargs

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

    @patch("src.todoist_client.TodoistAPI")
    def test_api_initialization(self, mock_api_class):
        """Test that the API is initialized correctly."""
        mock_api_instance = Mock()
        mock_api_class.return_value = mock_api_instance

        client = TodoistClient(api_token="test_token")

        # Check that the API was initialized with the correct token
        mock_api_class.assert_called_once_with("test_token")
        assert client._api == mock_api_instance
