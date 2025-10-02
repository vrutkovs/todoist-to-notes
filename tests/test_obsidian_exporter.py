"""Tests for Obsidian exporter functionality."""

import re

import pytest

from src.obsidian_exporter import ExportConfig, ObsidianExporter
from src.todoist_client import TodoistProject, TodoistTask


class TestObsidianExporter:
    """Test ObsidianExporter functionality."""

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
    def exporter(self, export_config):
        """Create ObsidianExporter instance."""
        return ObsidianExporter(export_config)

    @pytest.fixture
    def sample_project(self):
        """Create a sample Todoist project."""
        return TodoistProject(
            id="123",
            name="Test Project",
            color="blue",
            is_shared=False,
            url="",
        )

    @pytest.fixture
    def sample_task(self):
        """Create a sample Todoist task."""
        return TodoistTask(
            id="456",
            content="Sample task content",
            description="Task description",
            project_id="123",
            order=1,
            priority=2,
            labels=["test", "example"],
            due={"date": "2024-01-15"},
            comment_count=1,
            is_completed=False,
            created_at="2024-01-10T10:00:00Z",
            url="https://todoist.com/showTask?id=456",
        )

    def test_extract_link_title_with_link(self, exporter):
        """Test extracting title from markdown link."""
        text_with_link = "Check out [GitHub](https://github.com) for projects"
        result = exporter.extract_link_title(text_with_link)
        assert result == "GitHub"

    def test_extract_link_title_with_complex_link(self, exporter):
        """Test extracting title from complex markdown link."""
        text_with_link = (
            "Read the [API Documentation](https://api.example.com/docs) carefully"
        )
        result = exporter.extract_link_title(text_with_link)
        assert result == "API Documentation"

    def test_extract_link_title_with_multiple_links(self, exporter):
        """Test extracting title from text with multiple links (returns first)."""
        text_with_links = (
            "Visit [Google](https://google.com) and [GitHub](https://github.com)"
        )
        result = exporter.extract_link_title(text_with_links)
        assert result == "Google"

    def test_extract_link_title_no_link(self, exporter):
        """Test extracting title from text without markdown link."""
        text_without_link = "Just a regular task without any links"
        result = exporter.extract_link_title(text_without_link)
        assert result is None

    def test_extract_link_title_malformed_link(self, exporter):
        """Test extracting title from malformed markdown link."""
        malformed_links = [
            "Check [incomplete link",
            "Another (missing bracket) link",
            "[](empty title)",
            "[title]()",
        ]
        for text in (
            malformed_links
        ):  # All should return None since regex requires non-empty title
            result = exporter.extract_link_title(text)
            assert result is None

    def test_sanitize_filename_basic(self, exporter):
        """Test basic filename sanitization."""
        filename = exporter.sanitize_filename("Simple Task")
        assert filename == "Simple Task"

    def test_sanitize_filename_invalid_characters(self, exporter):
        """Test sanitizing filename with invalid characters."""
        filename = exporter.sanitize_filename('Task with <invalid> "chars" | *?')
        assert filename == "Task with _invalid_ _chars"

    def test_sanitize_filename_non_ascii(self, exporter):
        """Test sanitizing filename with non-ASCII characters."""
        test_cases = [
            ("Tâsk wïth accénts", "Task with accents"),
            ("Задача на русском", ""),  # Cyrillic should be removed
            ("タスク in Japanese", " in Japanese"),  # Japanese should be removed
            ("Café münü", "Cafe munu"),
            ("naïve résumé", "naive resume"),
        ]

        for input_text, expected in test_cases:
            result = exporter.sanitize_filename(input_text)
            # Remove multiple underscores and trim
            expected_clean = re.sub(r"_+", "_", expected).strip("_ ")
            if not expected_clean:
                expected_clean = "untitled"
            assert result == expected_clean

    def test_sanitize_filename_long_name(self, exporter):
        """Test sanitizing very long filename."""
        long_name = "A" * 250  # Very long name
        result = exporter.sanitize_filename(long_name)
        assert len(result) <= 200

    def test_sanitize_filename_empty(self, exporter):
        """Test sanitizing empty filename."""
        result = exporter.sanitize_filename("")
        assert result == "untitled"

    def test_sanitize_filename_only_invalid(self, exporter):
        """Test sanitizing filename with only invalid characters."""
        result = exporter.sanitize_filename("????")
        assert result == "untitled"

    def test_format_frontmatter_basic(self, exporter, sample_task, sample_project):
        """Test formatting frontmatter for basic task."""
        frontmatter = exporter.format_frontmatter(sample_task, sample_project)

        assert 'title: "Sample task content"' in frontmatter
        assert 'todoist_id: "456"' in frontmatter
        assert 'project: "Test Project"' in frontmatter
        assert "priority: 2" in frontmatter
        assert 'labels: ["test", "example"]' in frontmatter
        assert 'due_date: "2024-01-15"' in frontmatter
        assert "original_title" not in frontmatter

    def test_format_frontmatter_with_link(self, exporter, sample_project):
        """Test formatting frontmatter for task with markdown link."""
        task_with_link = TodoistTask(
            id="789",
            content="Check [GitHub Repository](https://github.com/user/repo) for updates",
            description="",
            project_id="123",
            order=1,
            priority=1,
            labels=[],
            comment_count=0,
            is_completed=False,
            created_at="2024-01-10T10:00:00Z",
        )

        frontmatter = exporter.format_frontmatter(task_with_link, sample_project)

        assert 'title: "GitHub Repository"' in frontmatter
        assert (
            'original_title: "Check [GitHub Repository](https://github.com/user/repo) for updates"'
            in frontmatter
        )

    def test_format_task_content_with_link(self, exporter, sample_project):
        """Test formatting task content with markdown link."""
        task_with_link = TodoistTask(
            id="789",
            content="Read [Python Documentation](https://docs.python.org) thoroughly",
            description="Important for the project",
            project_id="123",
            order=1,
            priority=1,
            labels=[],
            comment_count=0,
            is_completed=False,
            created_at="2024-01-10T10:00:00Z",
        )

        content = exporter.format_task_content(task_with_link, sample_project)

        # Should use link title in the heading
        assert "# ⬜ Python Documentation" in content
        # Should have original title in frontmatter
        assert (
            'original_title: "Read [Python Documentation](https://docs.python.org) thoroughly"'
            in content
        )

    def test_get_output_path_basic(self, exporter, sample_task, sample_project):
        """Test getting output path for basic task."""
        path = exporter.get_output_path(sample_task, sample_project)

        assert path.name == "Sample task content_456.md"
        assert path.parent == exporter.output_dir

    def test_get_output_path_with_link(self, exporter, sample_project):
        """Test getting output path for task with markdown link."""
        task_with_link = TodoistTask(
            id="789",
            content="Visit [Google Homepage](https://www.google.com) daily",
            description="",
            project_id="123",
            order=1,
            priority=1,
            labels=[],
            comment_count=0,
            is_completed=False,
            created_at="2024-01-10T10:00:00Z",
        )

        path = exporter.get_output_path(task_with_link, sample_project)

        # Should use link title for filename
        assert path.name == "Google Homepage_789.md"

    def test_get_output_path_non_ascii(self, exporter, sample_project):
        """Test getting output path with non-ASCII characters."""
        task_with_unicode = TodoistTask(
            id="999",
            content="Créer une tâche spéciale",
            description="",
            project_id="123",
            order=1,
            priority=1,
            labels=[],
            comment_count=0,
            is_completed=False,
            created_at="2024-01-10T10:00:00Z",
        )

        path = exporter.get_output_path(task_with_unicode, sample_project)

        # Should convert to ASCII
        assert path.name == "Creer une tache speciale_999.md"

    def test_export_task_creates_file(self, exporter, sample_task, sample_project):
        """Test that export_task actually creates a file."""
        output_path = exporter.export_task(sample_task, sample_project)

        assert output_path.exists()
        assert output_path.is_file()

        # Check file content
        content = output_path.read_text(encoding="utf-8")
        assert "# ⬜ Sample task content" in content
        assert 'title: "Sample task content"' in content

    def test_export_task_with_link_creates_correct_file(self, exporter, sample_project):
        """Test that export_task with link creates correctly named file."""
        task_with_link = TodoistTask(
            id="888",
            content="Review [Project Documentation](https://docs.example.com)",
            description="",
            project_id="123",
            order=1,
            priority=1,
            labels=[],
            comment_count=0,
            is_completed=False,
            created_at="2024-01-10T10:00:00Z",
        )

        output_path = exporter.export_task(task_with_link, sample_project)

        # File should be named after link title
        assert output_path.name == "Project Documentation_888.md"

        # Content should use link title in heading
        content = output_path.read_text(encoding="utf-8")
        assert "# ⬜ Project Documentation" in content
        assert 'title: "Project Documentation"' in content
        assert (
            'original_title: "Review [Project Documentation](https://docs.example.com)"'
            in content
        )

    def test_format_tags(self, exporter, sample_task, sample_project):
        """Test formatting tags for tasks."""
        tags = exporter.format_tags(sample_task, sample_project)

        expected_tags = [
            "#test",
            "#test/test-project",
            "#test/priority/low",
            "#test/label/test",
            "#test/label/example",
            "#test/status/active",
        ]

        assert all(tag in tags for tag in expected_tags)
