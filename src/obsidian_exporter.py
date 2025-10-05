"""Export Todoist tasks as Obsidian-compatible markdown notes."""

import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from .todoist_client import TodoistComment, TodoistProject, TodoistSection, TodoistTask

logger = logging.getLogger(__name__)


@dataclass
class ExportConfig:
    """Configuration for the export process."""

    output_dir: Path
    include_completed: bool = False
    include_comments: bool = True
    date_format: str = "%Y-%m-%d"
    time_format: str = "%H:%M"
    tag_prefix: str = "todoist"
    priority_as_tags: bool = True
    labels_as_tags: bool = True
    template_path: Path | None = None


class ObsidianExporter:
    """Export Todoist tasks as Obsidian markdown notes."""

    def __init__(self, config: ExportConfig):
        """Initialize the exporter with configuration.

        Args:
            config: Export configuration
        """
        self.config: ExportConfig = config
        self.output_dir: Path = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_link_title(self, text: str) -> str | None:
        """Extract the title from a markdown link if present.

        Args:
            text: Text that may contain a markdown link

        Returns:
            Link title if found, None otherwise
        """
        # Match markdown link format [title](url)
        link_match = re.search(r"\[([^\]]+)\]\([^)]+\)", text)
        if link_match:
            return link_match.group(1).strip()
        return None

    def sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use as a filename.

        Args:
            name: The original name

        Returns:
            Sanitized filename with only ASCII characters
        """
        # Convert to ASCII, removing non-ASCII characters
        ascii_name = unicodedata.normalize("NFKD", name)
        ascii_name = ascii_name.encode("ascii", "ignore").decode("ascii")

        # Replace invalid characters with underscores
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", ascii_name)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r"_+", "_", sanitized)
        # Remove leading/trailing underscores and spaces
        sanitized = sanitized.strip("_ ")
        # Limit length to avoid filesystem issues
        if len(sanitized) > 200:
            sanitized = sanitized[:200].rstrip("_")
        return sanitized or "untitled"

    def format_yaml_string(self, value: str) -> str:
        """Format a string value for safe YAML output.

        Uses single quotes when possible, double quotes with escaping when necessary.

        Args:
            value: String value to format

        Returns:
            Properly formatted YAML string value with quotes
        """
        # If the string contains single quotes but no double quotes, use double quotes
        if "'" in value and '"' not in value:
            return f'"{value}"'

        # If the string contains double quotes but no single quotes, use single quotes
        if '"' in value and "'" not in value:
            return f"'{value}'"

        # If the string contains both types of quotes or special chars, use double quotes with escaping
        if (
            '"' in value
            or "'" in value
            or "\n" in value
            or "\t" in value
            or "\\" in value
        ):
            # Escape backslashes first
            escaped = value.replace("\\", "\\\\")
            # Escape double quotes
            escaped = escaped.replace('"', '\\"')
            # Escape newlines and tabs
            escaped = escaped.replace("\n", "\\n")
            escaped = escaped.replace("\t", "\\t")
            return f'"{escaped}"'

        # For simple strings, use double quotes
        return f'"{value}"'

    def format_tags(self, task: TodoistTask, project: TodoistProject) -> list[str]:
        """Generate tags for a task.

        Args:
            task: The Todoist task
            project: The project the task belongs to

        Returns:
            List of tags
        """
        tags = []

        # Add base tag
        tags.append(f"#{self.config.tag_prefix}")

        # Add project tag
        project_tag = self.sanitize_filename(project.name.lower().replace(" ", "-"))
        tags.append(f"#{self.config.tag_prefix}/{project_tag}")

        # Add priority tags
        if self.config.priority_as_tags and task.priority > 1:
            priority_name = task.priority_text.lower()
            tags.append(f"#{self.config.tag_prefix}/priority/{priority_name}")

        # Add label tags
        if self.config.labels_as_tags:
            for label in task.labels:
                label_tag = self.sanitize_filename(label.lower().replace(" ", "-"))
                tags.append(f"#{self.config.tag_prefix}/label/{label_tag}")

        # Add status tag
        status = "completed" if task.is_completed else "active"
        tags.append(f"#{self.config.tag_prefix}/status/{status}")

        return tags

    def format_frontmatter(
        self,
        task: TodoistTask,
        project: TodoistProject,
        section: TodoistSection | None = None,
    ) -> str:
        """Generate YAML frontmatter for a task.

        Args:
            task: The Todoist task
            project: The project the task belongs to
            section: The section the task belongs to (optional)

        Returns:
            YAML frontmatter as string
        """
        frontmatter = ["---"]

        # Basic metadata
        frontmatter.append(f"title: {self.format_yaml_string(task.content)}")
        frontmatter.append(f"todoist_id: {self.format_yaml_string(task.id)}")
        frontmatter.append(f"project: {self.format_yaml_string(project.name)}")
        frontmatter.append(f'project_id: "{project.id}"')

        # Section
        if section:
            frontmatter.append(f"section: {self.format_yaml_string(section.name)}")
            frontmatter.append(f'section_id: "{section.id}"')
        frontmatter.append(f'created: "{task.created_at}"')

        # Due date
        if task.due_date:
            frontmatter.append(f'due_date: "{task.due_date}"')

        # Priority
        frontmatter.append(f"priority: {task.priority}")
        frontmatter.append(f'priority_text: "{task.priority_text}"')

        # Labels
        if task.labels:
            labels_str = '", "'.join(task.labels)
            frontmatter.append(f'labels: ["{labels_str}"]')

        # Status
        frontmatter.append(f"completed: {str(task.is_completed).lower()}")

        # URL
        if task.url:
            frontmatter.append(f'todoist_url: "{task.url}"')

        # Tags
        tags = self.format_tags(task, project)
        if tags:
            tags_str = '", "'.join(tag.lstrip("#") for tag in tags)
            frontmatter.append(f'tags: ["{tags_str}"]')

        frontmatter.append("---")
        frontmatter.append("")

        return "\n".join(frontmatter)

    def format_task_content(
        self,
        task: TodoistTask,
        project: TodoistProject,
        comments: list[TodoistComment] | None = None,
        child_tasks: list[TodoistTask] | None = None,
        section: TodoistSection | None = None,
    ) -> str:
        """Format a task as markdown content.

        Args:
            task: The Todoist task
            project: The project the task belongs to
            comments: Optional list of comments
            child_tasks: Optional list of child tasks to include as checkboxes
            section: The section the task belongs to (optional)

        Returns:
            Formatted markdown content
        """
        content = []

        # Add frontmatter
        content.append(self.format_frontmatter(task, project, section))

        # Task title
        status_icon = "✅" if task.is_completed else "⬜"
        content.append(f"# {status_icon} {task.content}")
        content.append("")

        # Task description
        if task.description:
            content.append("## Description")
            content.append("")
            content.append(task.description)
            content.append("")

        # Child tasks as checkboxes
        if child_tasks:
            content.append("## Subtasks")
            content.append("")

            for child_task in sorted(child_tasks, key=lambda t: t.order):
                checkbox = "[x]" if child_task.is_completed else "[ ]"
                content.append(f"- {checkbox} {child_task.content}")

            content.append("")

        # Comments section
        if comments and self.config.include_comments:
            content.append("## Comments")
            content.append("")
            for comment in comments:
                # Format datetime as \"1 Jan 14:50\"
                # Example: \"2024-01-11T15:30:00Z\" -> \"11 Jan 15:30\"\n
                dt_object = datetime.fromisoformat(
                    comment.posted_at.replace("Z", "+00:00")
                )
                formatted_datetime = dt_object.strftime("%d %b %H:%M")
                content.append(f"* {formatted_datetime} - {comment.content}")

        return "\n".join(content)

    def get_output_path(self, task: TodoistTask, project: TodoistProject) -> Path:  # noqa: ARG002
        """Determine the output path for a task note.

        Args:
            task: The Todoist task
            project: The project the task belongs to

        Returns:
            Path where the note should be saved
        """
        output_dir = self.output_dir

        # Use task ID as filename
        filename = task.id

        return output_dir / f"{filename}.md"

    def export_task(
        self,
        task: TodoistTask,
        project: TodoistProject,
        comments: list[TodoistComment] | None = None,
        child_tasks: list[TodoistTask] | None = None,
        section: TodoistSection | None = None,
    ) -> Path:
        """Export a single task as a markdown note.

        Args:
            task: The Todoist task to export
            project: The project the task belongs to
            comments: Optional comments for the task
            child_tasks: Optional list of child tasks to include as checkboxes
            section: The section the task belongs to (optional)

        Returns:
            Path to the created note file
        """
        output_path = self.get_output_path(task, project)

        # Skip if completed and not including completed tasks
        if task.is_completed and not self.config.include_completed:
            logger.debug(f"Skipping completed task: {task.content}")
            return output_path

        # Check if file already exists and preserve user content after ---
        existing_user_content = ""
        if output_path.exists():
            try:
                with open(output_path, encoding="utf-8") as f:
                    existing_content = f.read()

                # Find content after the last --- separator that isn't part of frontmatter
                lines = existing_content.split("\n")

                # Find all --- separators
                separators = []
                for i, line in enumerate(lines):
                    if line.strip() == "---":
                        separators.append(i)

                # If we have at least 2 separators (frontmatter start/end),
                # look for additional separators that might indicate user content
                if len(separators) >= 3:
                    # The third separator (index 2) marks the start of user content
                    user_content_start = separators[2] + 1
                    user_lines = lines[user_content_start:]

                    # Only preserve if there's actual content
                    if user_lines and any(line.strip() for line in user_lines):
                        existing_user_content = "\n".join(user_lines)
                        if existing_user_content.strip():
                            existing_user_content = (
                                "\n\n---\n\n" + existing_user_content
                            )
                            logger.debug(
                                f"Preserved user content for task '{task.content}'"
                            )

            except Exception as e:
                logger.warning(f"Failed to read existing file {output_path}: {e}")

        # Generate new content
        new_content = self.format_task_content(
            task, project, comments, child_tasks, section
        )

        # Combine with preserved user content
        final_content = new_content + existing_user_content

        # Write the file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_content)

        logger.info(f"Exported task '{task.content}' to {output_path}")
        return output_path
