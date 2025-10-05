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

        # Should use full original content as title
        assert (
            'title: "Check [GitHub Repository](https://github.com/user/repo) for updates"'
            in frontmatter
        )
        # No original_title field should be present
        assert "original_title:" not in frontmatter

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

        # Should use original content in the heading
        assert (
            "# ⬜ Read [Python Documentation](https://docs.python.org) thoroughly"
            in content
        )
        # Should have original title in frontmatter
        assert (
            'title: "Read [Python Documentation](https://docs.python.org) thoroughly"'
            in content
        )

    def test_get_output_path_basic(self, exporter, sample_task, sample_project):
        """Test getting output path for basic task."""
        path = exporter.get_output_path(sample_task, sample_project)

        assert path.name == "456.md"
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

        # Should use task ID for filename
        assert path.name == "789.md"

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

        # Should use task ID for filename
        assert path.name == "999.md"

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

        # File should be named after task ID
        assert output_path.name == "888.md"

        # Content should use original content in heading
        content = output_path.read_text(encoding="utf-8")
        assert (
            "# ⬜ Review [Project Documentation](https://docs.example.com)" in content
        )
        assert (
            'title: "Review [Project Documentation](https://docs.example.com)"'
            in content
        )
        # No original_title field should be present
        assert "original_title:" not in content

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

    def test_format_yaml_string_with_double_quotes(self, exporter):
        """Test YAML string formatting with double quotes."""
        result = exporter.format_yaml_string('Read "The Great Gatsby" book')
        assert result == "'Read \"The Great Gatsby\" book'"

    def test_format_yaml_string_with_single_quotes(self, exporter):
        """Test YAML string formatting with single quotes."""
        result = exporter.format_yaml_string("Check John's email")
        assert result == '"Check John\'s email"'

    def test_format_yaml_string_with_both_quotes(self, exporter):
        """Test YAML string formatting with both quote types."""
        result = exporter.format_yaml_string(
            'Review "Project Alpha" and John\'s feedback'
        )
        assert result == '"Review \\"Project Alpha\\" and John\'s feedback"'

    def test_format_yaml_string_with_special_chars(self, exporter):
        """Test YAML string formatting with special characters."""
        result = exporter.format_yaml_string("Text with\nnewlines and\ttabs")
        assert result == '"Text with\\nnewlines and\\ttabs"'

    def test_frontmatter_quote_escaping(self, exporter, sample_project):
        """Test that quotes in titles are properly escaped in frontmatter."""
        import yaml

        task_with_quotes = TodoistTask(
            id="quote_test",
            content='Read "The Great Gatsby" today',
            description="",
            project_id="123",
            order=1,
            priority=1,
            labels=[],
            comment_count=0,
            is_completed=False,
            created_at="2024-01-01T10:00:00Z",
        )

        frontmatter = exporter.format_frontmatter(task_with_quotes, sample_project)

        # Extract YAML content between --- markers
        lines = frontmatter.split("\n")
        yaml_content = "\n".join(lines[1:-2])  # Remove opening/closing ---

        # Should parse as valid YAML
        parsed = yaml.safe_load(yaml_content)
        assert isinstance(parsed, dict)
        assert parsed["title"] == 'Read "The Great Gatsby" today'

    def test_format_frontmatter_with_section(
        self, exporter, sample_task, sample_project
    ):
        """Test formatting frontmatter with section information."""
        from src.todoist_client import TodoistSection

        # Create a mock section
        section = TodoistSection(
            id="section_123", project_id="123", name="Important Tasks", order=1
        )

        frontmatter = exporter.format_frontmatter(sample_task, sample_project, section)

        assert 'section: "Important Tasks"' in frontmatter
        assert 'section_id: "section_123"' in frontmatter

    def test_format_frontmatter_without_section(
        self, exporter, sample_task, sample_project
    ):
        """Test formatting frontmatter without section information."""
        frontmatter = exporter.format_frontmatter(sample_task, sample_project)

        assert "section:" not in frontmatter
        assert "section_id:" not in frontmatter

    def test_format_task_content_with_section(
        self, exporter, sample_task, sample_project
    ):
        """Test formatting task content with section information."""
        from src.todoist_client import TodoistSection

        # Create a mock section
        section = TodoistSection(
            id="section_456", project_id="123", name="Development Tasks", order=2
        )

        content = exporter.format_task_content(
            sample_task, sample_project, None, None, section
        )

        assert 'section: "Development Tasks"' in content
        assert 'section_id: "section_456"' in content
