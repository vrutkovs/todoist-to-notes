"""Export Todoist tasks as Obsidian-compatible markdown notes."""

import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from .todoist_client import TodoistComment, TodoistProject, TodoistTask

logger = logging.getLogger(__name__)


@dataclass
class ExportConfig:
    """Configuration for the export process."""

    output_dir: Path
    create_project_folders: bool = True
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
        self.config = config
        self.output_dir = Path(config.output_dir)
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

    def format_frontmatter(self, task: TodoistTask, project: TodoistProject) -> str:
        """Generate YAML frontmatter for a task.

        Args:
            task: The Todoist task
            project: The project the task belongs to

        Returns:
            YAML frontmatter as string
        """
        frontmatter = ["---"]

        # Extract link title if present
        link_title = self.extract_link_title(task.content)
        display_title = link_title if link_title else task.content

        # Basic metadata
        frontmatter.append(f'title: "{display_title}"')
        if link_title:
            frontmatter.append(f'original_title: "{task.content}"')
        frontmatter.append(f'todoist_id: "{task.id}"')
        frontmatter.append(f'project: "{project.name}"')
        frontmatter.append(f'project_id: "{project.id}"')
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
    ) -> str:
        """Format a task as markdown content.

        Args:
            task: The Todoist task
            project: The project the task belongs to
            comments: Optional list of comments

        Returns:
            Formatted markdown content
        """
        content = []

        # Add frontmatter
        content.append(self.format_frontmatter(task, project))

        # Task title - use link title if available
        link_title = self.extract_link_title(task.content)
        display_title = link_title if link_title else task.content
        status_icon = "✅" if task.is_completed else "⬜"
        content.append(f"# {status_icon} {display_title}")
        content.append("")

        # Task description
        if task.description:
            content.append("## Description")
            content.append("")
            content.append(task.description)
            content.append("")

        # Comments section
        if comments and self.config.include_comments:
            content.append("## Comments")
            content.append("")

            for comment in comments:
                # Format datetime without timezone
                comment_datetime = comment.posted_at.replace("Z", "").replace("T", " ")
                if "." in comment_datetime:
                    comment_datetime = comment_datetime.split(".")[0]
                content.append(f"### Comment - {comment_datetime}")
                content.append("")
                content.append(comment.content)
                content.append("")

        # Tags
        tags = self.format_tags(task, project)
        if tags:
            content.append("---")
            content.append("")
            content.append(" ".join(tags))

        return "\n".join(content)

    def get_output_path(self, task: TodoistTask, project: TodoistProject) -> Path:
        """Determine the output path for a task note.

        Args:
            task: The Todoist task
            project: The project the task belongs to

        Returns:
            Path where the note should be saved
        """
        if self.config.create_project_folders:
            project_dir = self.output_dir / self.sanitize_filename(project.name)
            project_dir.mkdir(exist_ok=True)
            output_dir = project_dir
        else:
            output_dir = self.output_dir

        # Generate filename from task content (use link title if available)
        link_title = self.extract_link_title(task.content)
        title_for_filename = link_title if link_title else task.content
        filename = self.sanitize_filename(title_for_filename)

        # Add task ID to avoid conflicts
        filename = f"{filename}_{task.id}"

        return output_dir / f"{filename}.md"

    def export_task(
        self,
        task: TodoistTask,
        project: TodoistProject,
        comments: list[TodoistComment] | None = None,
    ) -> Path:
        """Export a single task as a markdown note.

        Args:
            task: The Todoist task to export
            project: The project the task belongs to
            comments: Optional comments for the task

        Returns:
            Path to the created note file
        """
        output_path = self.get_output_path(task, project)

        # Skip if completed and not including completed tasks
        if task.is_completed and not self.config.include_completed:
            logger.debug(f"Skipping completed task: {task.content}")
            return output_path

        content = self.format_task_content(task, project, comments)

        # Write the file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Exported task '{task.content}' to {output_path}")
        return output_path
