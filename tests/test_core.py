"""Tests for core functionality."""

from unittest.mock import Mock, patch

import pytest

from src.core import export_tasks_internal
from src.obsidian_exporter import ExportConfig
from src.todoist_client import (
    TodoistAPIError,
    TodoistClient,
    TodoistProject,
    TodoistTask,
)


class TestExportTasksInternal:
    """Test export_tasks_internal functionality."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Todoist client."""
        client = Mock(spec=TodoistClient)
        return client

    @pytest.fixture
    def export_config(self, tmp_path):
        """Create export configuration."""
        return ExportConfig(
            output_dir=tmp_path,
            include_completed=False,
            include_comments=False,
            tag_prefix="",
        )

    @pytest.fixture
    def mock_project(self):
        """Create a mock project."""
        return TodoistProject(
            id="123",
            name="Test Project",
            color="red",
            is_shared=False,
            url="https://example.com/project/123",
        )

    @pytest.fixture
    def mock_task(self):
        """Create a mock task."""
        return TodoistTask(
            id="456",
            content="Test Task",
            description="Test description",
            project_id="123",
            section_id=None,
            parent_id=None,
            order=1,
            priority=3,
            labels=["test"],
            due=None,
            url="https://example.com/task/456",
            is_completed=False,
            created_at="2024-01-01T00:00:00Z",
            creator_id="user123",
            assignee_id=None,
            assigner_id=None,
        )

    @pytest.fixture
    def mock_completed_task(self):
        """Create a mock completed task."""
        return TodoistTask(
            id="789",
            content="Completed Task",
            description="Completed task description",
            project_id="123",
            section_id=None,
            parent_id=None,
            order=2,
            priority=2,
            labels=["done"],
            due=None,
            url="https://example.com/task/789",
            is_completed=True,
            created_at="2024-01-01T00:00:00Z",
            creator_id="user123",
            assignee_id=None,
            assigner_id=None,
        )

    def test_export_tasks_basic(
        self, mock_client, export_config, mock_project, mock_task
    ):
        """Test basic task export without completed tasks."""
        # Setup mocks
        mock_client.get_projects.return_value = [mock_project]
        mock_client.get_sections.return_value = []
        mock_client.get_tasks.return_value = [mock_task]

        # Mock the exporter
        with patch("src.core.ObsidianExporter") as mock_exporter_class:
            mock_exporter = Mock()
            mock_exporter_class.return_value = mock_exporter

            result = export_tasks_internal(
                client=mock_client,
                export_config=export_config,
                include_completed=False,
            )

            # Verify calls
            mock_client.get_projects.assert_called_once()
            mock_client.get_tasks.assert_called_once_with(
                project_id=None, filter_expr=None
            )
            mock_client.get_completed_tasks.assert_not_called()

            # Verify export
            mock_exporter.export_task.assert_called_once_with(
                mock_task, mock_project, None, [], None
            )
            assert result == 1

    def test_export_tasks_with_completed(
        self, mock_client, export_config, mock_project, mock_task, mock_completed_task
    ):
        """Test task export including completed tasks."""
        # Setup mocks
        mock_client.get_projects.return_value = [mock_project]
        mock_client.get_sections.return_value = []
        mock_client.get_tasks.return_value = [mock_task]
        mock_client.get_completed_tasks.return_value = [mock_completed_task]

        # Mock the exporter
        with patch("src.core.ObsidianExporter") as mock_exporter_class:
            mock_exporter = Mock()
            mock_exporter_class.return_value = mock_exporter

            result = export_tasks_internal(
                client=mock_client,
                export_config=export_config,
                include_completed=True,
            )

            # Verify calls
            mock_client.get_projects.assert_called_once()
            mock_client.get_tasks.assert_called_once_with(
                project_id=None, filter_expr=None
            )
            mock_client.get_completed_tasks.assert_called_once_with(project_id=None)

            # Verify both tasks were exported
            assert mock_exporter.export_task.call_count == 2
            assert result == 2

    def test_export_tasks_with_completed_duplicate_prevention(
        self, mock_client, export_config, mock_project, mock_task
    ):
        """Test that duplicate tasks are not added when fetching completed tasks."""
        # Create a task that appears in both regular and completed lists
        duplicate_task = TodoistTask(
            id="456",  # Same ID as mock_task
            content="Test Task (completed version)",
            description="Test description",
            project_id="123",
            section_id=None,
            parent_id=None,
            order=1,
            priority=3,
            labels=["test"],
            due=None,
            url="https://example.com/task/456",
            is_completed=True,  # This one is marked completed
            created_at="2024-01-01T00:00:00Z",
            creator_id="user123",
            assignee_id=None,
            assigner_id=None,
        )

        # Setup mocks - same task appears in both lists
        mock_client.get_projects.return_value = [mock_project]
        mock_client.get_sections.return_value = []
        mock_client.get_tasks.return_value = [mock_task]
        mock_client.get_completed_tasks.return_value = [duplicate_task]

        # Mock the exporter
        with patch("src.core.ObsidianExporter") as mock_exporter_class:
            mock_exporter = Mock()
            mock_exporter_class.return_value = mock_exporter

            result = export_tasks_internal(
                client=mock_client,
                export_config=export_config,
                include_completed=True,
            )

            # Verify only one task was exported (no duplicates)
            mock_exporter.export_task.assert_called_once()
            assert result == 1

    def test_export_tasks_with_project_filter(
        self, mock_client, export_config, mock_project, mock_task, mock_completed_task
    ):
        """Test task export with project filter and completed tasks."""
        # Setup mocks
        mock_client.get_projects.return_value = [mock_project]
        mock_client.get_sections.return_value = []
        mock_client.get_tasks.return_value = [mock_task]
        mock_client.get_completed_tasks.return_value = [mock_completed_task]

        # Mock the exporter
        with patch("src.core.ObsidianExporter") as mock_exporter_class:
            mock_exporter = Mock()
            mock_exporter_class.return_value = mock_exporter

            result = export_tasks_internal(
                client=mock_client,
                export_config=export_config,
                project_id="123",
                include_completed=True,
            )

            # Verify calls with project filter
            mock_client.get_tasks.assert_called_once_with(
                project_id="123", filter_expr=None
            )
            mock_client.get_completed_tasks.assert_called_once_with(project_id="123")

            assert result == 2

    def test_export_tasks_completed_fetch_error(
        self, mock_client, export_config, mock_project, mock_task
    ):
        """Test that export continues if fetching completed tasks fails."""
        # Setup mocks
        mock_client.get_projects.return_value = [mock_project]
        mock_client.get_sections.return_value = []
        mock_client.get_tasks.return_value = [mock_task]
        mock_client.get_completed_tasks.side_effect = TodoistAPIError(
            "Failed to fetch completed tasks"
        )

        # Mock the exporter
        with patch("src.core.ObsidianExporter") as mock_exporter_class:
            mock_exporter = Mock()
            mock_exporter_class.return_value = mock_exporter

            result = export_tasks_internal(
                client=mock_client,
                export_config=export_config,
                include_completed=True,
            )

            # Verify that regular task export still happened
            mock_exporter.export_task.assert_called_once_with(
                mock_task, mock_project, None, [], None
            )
            assert result == 1

    def test_export_tasks_by_project_name(
        self, mock_client, export_config, mock_project, mock_task
    ):
        """Test task export by project name with completed tasks."""
        # Setup mocks
        mock_client.get_projects.return_value = [mock_project]
        mock_client.get_sections.return_value = []
        mock_client.get_tasks.return_value = [mock_task]
        mock_client.get_completed_tasks.return_value = []

        # Mock the exporter
        with patch("src.core.ObsidianExporter") as mock_exporter_class:
            mock_exporter = Mock()
            mock_exporter_class.return_value = mock_exporter

            result = export_tasks_internal(
                client=mock_client,
                export_config=export_config,
                project_name="Test Project",
                include_completed=True,
            )

            # Verify calls with resolved project ID
            mock_client.get_tasks.assert_called_once_with(
                project_id="123", filter_expr=None
            )
            mock_client.get_completed_tasks.assert_called_once_with(project_id="123")

            assert result == 1

    def test_export_tasks_only_completed_tasks(
        self, mock_client, export_config, mock_project, mock_completed_task
    ):
        """Test export when only completed tasks are available."""
        # Setup mocks
        mock_client.get_projects.return_value = [mock_project]
        mock_client.get_sections.return_value = []
        mock_client.get_tasks.return_value = []
        mock_client.get_completed_tasks.return_value = [mock_completed_task]

        # Mock the exporter
        with patch("src.core.ObsidianExporter") as mock_exporter_class:
            mock_exporter = Mock()
            mock_exporter_class.return_value = mock_exporter

            result = export_tasks_internal(
                client=mock_client,
                export_config=export_config,
                include_completed=True,
            )

            # Should export the completed task
            mock_exporter.export_task.assert_called_once_with(
                mock_completed_task, mock_project, None, [], None
            )
            assert result == 1

    def test_export_tasks_no_tasks_found(
        self, mock_client, export_config, mock_project
    ):
        """Test export when no tasks are found."""
        # Setup mocks
        mock_client.get_projects.return_value = [mock_project]
        mock_client.get_sections.return_value = []
        mock_client.get_tasks.return_value = []
        mock_client.get_completed_tasks.return_value = []

        result = export_tasks_internal(
            client=mock_client,
            export_config=export_config,
            include_completed=True,
        )

        # Should still call get_completed_tasks to check for completed tasks
        mock_client.get_completed_tasks.assert_called_once_with(project_id=None)
        assert result == 0

    def test_export_tasks_with_comments_ignores_comment_count(
        self, mock_client, export_config, mock_project
    ):
        """Test that comments are fetched regardless of comment_count value."""
        # Enable comments in export config
        export_config.include_comments = True

        # Create a task with comment_count = 0 (unreliable)
        task_with_zero_comment_count = TodoistTask(
            id="456",
            content="Task with zero comment_count",
            description="Test description",
            project_id="123",
            section_id=None,
            parent_id=None,
            order=1,
            priority=3,
            labels=["test"],
            due=None,
            url="https://example.com/task/456",
            is_completed=False,
            created_at="2024-01-01T00:00:00Z",
            creator_id="user123",
            assignee_id=None,
            assigner_id=None,
        )

        # Mock comments that should be fetched despite comment_count=0
        mock_comments = [
            Mock(
                id="comment1", content="First comment", posted_at="2024-01-01T10:00:00Z"
            ),
            Mock(
                id="comment2",
                content="Second comment",
                posted_at="2024-01-01T11:00:00Z",
            ),
        ]

        # Setup mocks
        mock_client.get_projects.return_value = [mock_project]
        mock_client.get_sections.return_value = []
        mock_client.get_tasks.return_value = [task_with_zero_comment_count]
        mock_client.get_task_comments.return_value = mock_comments

        # Mock the exporter
        with patch("src.core.ObsidianExporter") as mock_exporter_class:
            mock_exporter = Mock()
            mock_exporter_class.return_value = mock_exporter

            result = export_tasks_internal(
                client=mock_client,
                export_config=export_config,
                include_completed=False,
            )

            # Verify that get_task_comments was called despite comment_count=0
            mock_client.get_task_comments.assert_called_once_with("456")

            # Verify task was exported with comments
            mock_exporter.export_task.assert_called_once_with(
                task_with_zero_comment_count, mock_project, mock_comments, [], None
            )
            assert result == 1

    def test_export_tasks_comments_disabled(
        self, mock_client, export_config, mock_project, mock_task
    ):
        """Test that comments are not fetched when disabled in config."""
        # Comments are disabled by default in export_config
        assert export_config.include_comments is False

        # Setup mocks
        mock_client.get_projects.return_value = [mock_project]
        mock_client.get_sections.return_value = []
        mock_client.get_tasks.return_value = [mock_task]

        # Mock the exporter
        with patch("src.core.ObsidianExporter") as mock_exporter_class:
            mock_exporter = Mock()
            mock_exporter_class.return_value = mock_exporter

            result = export_tasks_internal(
                client=mock_client,
                export_config=export_config,
                include_completed=False,
            )

            # Verify that get_task_comments was NOT called
            mock_client.get_task_comments.assert_not_called()

            # Verify task was exported without comments (None)
            mock_exporter.export_task.assert_called_once_with(
                mock_task, mock_project, None, [], None
            )
            assert result == 1

    def test_export_tasks_with_section(self, mock_client, export_config, mock_project):
        """Test task export with section information."""
        from src.todoist_client import TodoistSection

        # Create a mock section
        mock_section = TodoistSection(
            id="section_123", project_id="123", name="Important Tasks", order=1
        )

        # Create a task with section_id
        task_with_section = TodoistTask(
            id="456",
            content="Test Task with Section",
            description="Test description",
            project_id="123",
            section_id="section_123",
            parent_id=None,
            order=1,
            priority=3,
            labels=["test"],
            due=None,
            url="https://example.com/task/456",
            is_completed=False,
            created_at="2024-01-01T00:00:00Z",
            creator_id="user123",
            assignee_id=None,
            assigner_id=None,
        )

        # Setup mocks
        mock_client.get_projects.return_value = [mock_project]
        mock_client.get_sections.return_value = [mock_section]
        mock_client.get_tasks.return_value = [task_with_section]

        # Mock the exporter
        with patch("src.core.ObsidianExporter") as mock_exporter_class:
            mock_exporter = Mock()
            mock_exporter_class.return_value = mock_exporter

            result = export_tasks_internal(
                client=mock_client,
                export_config=export_config,
                include_completed=False,
            )

            # Verify calls
            mock_client.get_sections.assert_called_once()

            # Verify export with section
            mock_exporter.export_task.assert_called_once_with(
                task_with_section, mock_project, None, [], mock_section
            )
            assert result == 1
