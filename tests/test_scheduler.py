"""Tests for scheduler functionality."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.obsidian_exporter import ExportConfig
from src.scheduler import ScheduledSync
from src.todoist_client import TodoistAPIError, TodoistClient


class TestScheduledSync:
    """Test ScheduledSync functionality."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Todoist client."""
        client = Mock(spec=TodoistClient)
        client.get_projects.return_value = []
        client.get_tasks.return_value = []
        return client

    @pytest.fixture
    def export_config(self, tmp_path):
        """Create test export configuration."""
        return ExportConfig(
            output_dir=tmp_path,
            create_project_folders=False,
            include_completed=False,
            include_comments=True,
            tag_prefix="test",
        )

    @pytest.fixture
    def scheduled_sync(self, mock_client, export_config):
        """Create a ScheduledSync instance for testing."""
        with patch("src.scheduler.TodoistClient", return_value=mock_client):
            sync = ScheduledSync(
                api_token="test_token",
                export_config=export_config,
            )
            sync.client = mock_client
            return sync

    def test_initialization(self, export_config):
        """Test ScheduledSync initialization."""
        with patch("src.scheduler.TodoistClient") as mock_client_class:
            sync = ScheduledSync(
                api_token="test_token",
                export_config=export_config,
                project_id="123",
                project_name="Test Project",
                filter_expr="today",
                include_completed=True,
            )

            mock_client_class.assert_called_once_with("test_token")
            assert sync.api_token == "test_token"
            assert sync.export_config == export_config
            assert sync.project_id == "123"
            assert sync.project_name == "Test Project"
            assert sync.filter_expr == "today"
            assert sync.include_completed is True
            assert sync.sync_count == 0
            assert sync.last_sync is None
            assert sync.is_running is False

    @patch("src.scheduler.export_tasks_internal")
    def test_sync_tasks_success(self, mock_export, scheduled_sync):
        """Test successful sync operation."""
        mock_export.return_value = 5

        result = scheduled_sync.sync_tasks()

        assert result is True
        assert scheduled_sync.sync_count == 1
        assert scheduled_sync.last_sync is not None
        assert isinstance(scheduled_sync.last_sync, datetime)

        mock_export.assert_called_once_with(
            client=scheduled_sync.client,
            export_config=scheduled_sync.export_config,
            project_id=None,
            project_name=None,
            filter_expr=None,
            include_completed=False,
        )

    @patch("src.scheduler.export_tasks_internal")
    def test_sync_tasks_api_error(self, mock_export, scheduled_sync):
        """Test sync with Todoist API error."""
        mock_export.side_effect = TodoistAPIError("API Error")

        result = scheduled_sync.sync_tasks()

        assert result is False
        assert scheduled_sync.sync_count == 0
        assert scheduled_sync.last_sync is None

    @patch("src.scheduler.export_tasks_internal")
    def test_sync_tasks_general_error(self, mock_export, scheduled_sync):
        """Test sync with general error."""
        mock_export.side_effect = Exception("General Error")

        result = scheduled_sync.sync_tasks()

        assert result is False
        assert scheduled_sync.sync_count == 0
        assert scheduled_sync.last_sync is None

    @patch("src.scheduler.schedule")
    def test_run_every_minutes(self, mock_schedule, scheduled_sync):
        """Test scheduling sync every N minutes."""
        mock_schedule.every.return_value.minutes.do = Mock()

        result = scheduled_sync.run_every(15, "minutes")

        assert result == scheduled_sync
        mock_schedule.every.assert_called_once_with(15)
        mock_schedule.every.return_value.minutes.do.assert_called_once()

    @patch("src.scheduler.schedule")
    def test_run_every_hours(self, mock_schedule, scheduled_sync):
        """Test scheduling sync every N hours."""
        mock_schedule.every.return_value.hours.do = Mock()

        result = scheduled_sync.run_every(2, "hours")

        assert result == scheduled_sync
        mock_schedule.every.assert_called_once_with(2)
        mock_schedule.every.return_value.hours.do.assert_called_once()

    @patch("src.scheduler.schedule")
    def test_run_every_invalid_unit(self, _mock_schedule, scheduled_sync):
        """Test scheduling with invalid time unit."""
        with pytest.raises(ValueError, match="Unsupported time unit: invalid"):
            scheduled_sync.run_every(15, "invalid")

    @patch("src.scheduler.schedule")
    def test_run_at(self, mock_schedule, scheduled_sync):
        """Test scheduling sync at specific time."""
        mock_schedule.every.return_value.day.at = Mock()

        result = scheduled_sync.run_at("09:00")

        assert result == scheduled_sync
        mock_schedule.every.assert_called_once()
        mock_schedule.every.return_value.day.at.assert_called_once_with("09:00")

    @patch("src.scheduler.export_tasks_internal")
    def test_run_once_now(self, mock_export, scheduled_sync):
        """Test running sync once immediately."""
        mock_export.return_value = 3

        result = scheduled_sync.run_once_now()

        assert result is True
        assert scheduled_sync.sync_count == 1
        mock_export.assert_called_once()

    @patch("src.scheduler.schedule")
    def test_stop(self, mock_schedule, scheduled_sync):
        """Test stopping the scheduler."""
        scheduled_sync.is_running = True
        mock_schedule.clear = Mock()

        scheduled_sync.stop()

        assert scheduled_sync.is_running is False
        mock_schedule.clear.assert_called_once()

    def test_signal_handler(self, scheduled_sync):
        """Test signal handler calls stop method."""
        with patch.object(scheduled_sync, "stop") as mock_stop:
            scheduled_sync._signal_handler(2, None)
            mock_stop.assert_called_once()

    @patch("src.scheduler.schedule")
    def test_create_status_panel(self, mock_schedule, scheduled_sync):
        """Test creating status panel."""
        scheduled_sync.is_running = True
        scheduled_sync.sync_count = 5
        scheduled_sync.last_sync = datetime(2024, 1, 15, 10, 30, 0)

        mock_schedule.next_run.return_value = datetime(2024, 1, 15, 11, 0, 0)

        panel = scheduled_sync._create_status_panel()

        assert panel.title == "Todoist Sync Status"
        assert "🟢 Running" in str(panel.renderable)
        assert "Sync count: 5" in str(panel.renderable)
        assert "2024-01-15 10:30:00" in str(panel.renderable)

    @patch("src.scheduler.schedule")
    def test_create_status_panel_stopped(self, mock_schedule, scheduled_sync):
        """Test creating status panel when stopped."""
        scheduled_sync.is_running = False
        mock_schedule.next_run.return_value = None

        panel = scheduled_sync._create_status_panel()

        assert "🔴 Stopped" in str(panel.renderable)
        assert "Last sync: Never" in str(panel.renderable)
