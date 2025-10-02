"""Core functionality for Todoist to Obsidian Notes exporter."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from .obsidian_exporter import ExportConfig, ObsidianExporter
from .todoist_client import TodoistAPIError, TodoistClient

logger = logging.getLogger(__name__)


def export_tasks_internal(
    client: TodoistClient,
    export_config: ExportConfig,
    project_id: str | None = None,
    project_name: str | None = None,
    filter_expr: str | None = None,
    include_completed: bool = False,
) -> int:
    """Internal function to export tasks without CLI dependencies.

    Args:
        client: Initialized Todoist client
        export_config: Export configuration
        project_id: Optional project ID filter
        project_name: Optional project name filter
        filter_expr: Optional Todoist filter expression
        include_completed: Whether to include completed tasks

    Returns:
        Number of tasks exported

    Raises:
        TodoistAPIError: If API operations fail
    """
    # Get projects
    projects = client.get_projects()
    projects_dict = {p.id: p for p in projects}

    # Resolve project name to ID if needed
    target_project_id = project_id
    if project_name and not project_id:
        matching_projects = [
            p for p in projects if p.name.lower() == project_name.lower()
        ]
        if not matching_projects:
            raise TodoistAPIError(f"Project '{project_name}' not found")
        target_project_id = matching_projects[0].id

    # Get tasks
    tasks = client.get_tasks(project_id=target_project_id, filter_expr=filter_expr)

    if not tasks:
        logger.info("No tasks found matching the specified criteria")
        return 0

    # Initialize exporter
    exporter = ObsidianExporter(export_config)

    # Export tasks
    exported_count = 0
    for task in tasks:
        project = projects_dict.get(task.project_id)
        if not project:
            logger.warning(f"Project not found for task: {task.content}")
            continue

        # Skip completed tasks if not including them
        if task.is_completed and not include_completed:
            continue

        # Get comments if enabled
        comments = None
        if export_config.include_comments and task.comment_count > 0:
            try:
                comments = client.get_task_comments(task.id)
            except TodoistAPIError as e:
                logger.warning(f"Failed to get comments for task '{task.content}': {e}")

        # Export the task
        try:
            exporter.export_task(task, project, comments)
            exported_count += 1
        except Exception as e:
            logger.error(f"Failed to export task '{task.content}': {e}")

    logger.info(f"Exported {exported_count} tasks to {export_config.output_dir}")
    return exported_count
