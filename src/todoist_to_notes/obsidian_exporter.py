"""Export Todoist tasks as Obsidian-compatible markdown notes."""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

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
    template_path: Optional[Path] = None


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

    def sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use as a filename.

        Args:
            name: The original name

        Returns:
            Sanitized filename
        """
        # Replace invalid characters with underscores
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", name)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r"_+", "_", sanitized)
        # Remove leading/trailing underscores and spaces
        sanitized = sanitized.strip("_ ")
        # Limit length to avoid filesystem issues
        if len(sanitized) > 200:
            sanitized = sanitized[:200].rstrip("_")
        return sanitized or "untitled"

    def format_tags(self, task: TodoistTask, project: TodoistProject) -> List[str]:
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

        # Basic metadata
        frontmatter.append(f'title: "{task.content}"')
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
        comments: Optional[List[TodoistComment]] = None,
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

        # Metadata section
        content.append("## Metadata")
        content.append("")
        content.append(f"- **Project**: [[{self.sanitize_filename(project.name)}]]")
        content.append(f"- **Priority**: {task.priority_text}")

        if task.due_date:
            content.append(f"- **Due Date**: {task.due_date}")

        if task.labels:
            labels_links = [f"#{label.replace(' ', '-')}" for label in task.labels]
            content.append(f"- **Labels**: {', '.join(labels_links)}")

        content.append(f"- **Created**: {task.created_at}")

        if task.url:
            content.append(f"- **Todoist URL**: [Open in Todoist]({task.url})")

        content.append("")

        # Comments section
        if comments and self.config.include_comments:
            content.append("## Comments")
            content.append("")

            for comment in comments:
                comment_date = comment.posted_at[:10]  # Extract date part
                content.append(f"### Comment - {comment_date}")
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

        # Generate filename from task content
        filename = self.sanitize_filename(task.content)

        # Add task ID to avoid conflicts
        filename = f"{filename}_{task.id}"

        return output_dir / f"{filename}.md"

    def export_task(
        self,
        task: TodoistTask,
        project: TodoistProject,
        comments: Optional[List[TodoistComment]] = None,
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

    def export_project_index(
        self, project: TodoistProject, task_files: List[Path]
    ) -> Optional[Path]:
        """Create an index note for a project.

        Args:
            project: The project
            task_files: List of task file paths in this project

        Returns:
            Path to the created index file
        """
        if not self.config.create_project_folders:
            return None

        project_dir = self.output_dir / self.sanitize_filename(project.name)
        index_path = project_dir / "README.md"

        content = []
        content.append("---")
        content.append(f'title: "{project.name} - Project Index"')
        content.append(f'todoist_project_id: "{project.id}"')
        content.append(f'project_color: "{project.color}"')
        content.append(f"is_favorite: {str(project.is_favorite).lower()}")
        content.append(
            f'tags: ["{self.config.tag_prefix}", "{self.config.tag_prefix}/project"]'
        )
        content.append("---")
        content.append("")
        content.append(f"# {project.name}")
        content.append("")
        content.append(
            f"This is the project index for **{project.name}** from Todoist."
        )
        content.append("")

        if task_files:
            content.append("## Tasks")
            content.append("")
            for task_file in sorted(task_files):
                task_name = task_file.stem.rsplit("_", 1)[0].replace("_", " ")
                content.append(f"- [[{task_file.stem}|{task_name}]]")
            content.append("")

        content.append("---")
        content.append("")
        content.append(f"#{self.config.tag_prefix} #{self.config.tag_prefix}/project")

        with open(index_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))

        logger.info(f"Created project index for '{project.name}' at {index_path}")
        return index_path

    def create_master_index(
        self, projects: List[TodoistProject], exported_counts: Dict[str, int]
    ) -> Path:
        """Create a master index of all exported projects and tasks.

        Args:
            projects: List of all projects
            exported_counts: Dict mapping project IDs to task counts

        Returns:
            Path to the master index file
        """
        index_path = self.output_dir / "Todoist_Export_Index.md"

        content = []
        content.append("---")
        content.append('title: "Todoist Export Index"')
        content.append(f'export_date: "{datetime.now().isoformat()}"')
        content.append(
            f'tags: ["{self.config.tag_prefix}", "{self.config.tag_prefix}/index"]'
        )
        content.append("---")
        content.append("")
        content.append("# Todoist Export Index")
        content.append("")
        content.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        total_tasks = sum(exported_counts.values())
        content.append(f"**Total Projects**: {len(projects)}")
        content.append(f"**Total Tasks Exported**: {total_tasks}")
        content.append("")

        if projects:
            content.append("## Projects")
            content.append("")

            for project in sorted(projects, key=lambda p: p.name):
                task_count = exported_counts.get(project.id, 0)
                if self.config.create_project_folders:
                    project_link = (
                        f"[[{self.sanitize_filename(project.name)}/"
                        f"README|{project.name}]]"
                    )
                else:
                    project_link = project.name

                content.append(f"- {project_link} ({task_count} tasks)")

            content.append("")

        content.append("## Usage")
        content.append("")
        content.append("This export includes:")
        content.append(
            f"- {'✅' if self.config.include_completed else '❌'} Completed tasks"
        )
        content.append(
            f"- {'✅' if self.config.include_comments else '❌'} Task comments"
        )
        content.append(
            f"- {'✅' if self.config.create_project_folders else '❌'} Project folders"
        )
        content.append("")

        content.append("---")
        content.append("")
        content.append(f"#{self.config.tag_prefix} #{self.config.tag_prefix}/index")

        with open(index_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))

        logger.info(f"Created master index at {index_path}")
        return index_path
