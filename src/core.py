"""Core functionality for Todoist to Obsidian Notes exporter."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from .obsidian_exporter import ExportConfig, ObsidianExporter
from .todoist_client import TodoistAPIError, TodoistClient, TodoistTask

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

    # Get completed tasks if requested
    if include_completed:
        try:
            completed_tasks = client.get_completed_tasks(project_id=target_project_id)
            # Merge completed tasks with regular tasks, avoiding duplicates
            task_ids = {task.id for task in tasks}
            for completed_task in completed_tasks:
                if completed_task.id not in task_ids:
                    tasks.append(completed_task)
            logger.info(f"Added {len(completed_tasks)} completed tasks")
        except TodoistAPIError as e:
            logger.warning(f"Failed to fetch completed tasks: {e}")

    if not tasks:
        logger.info("No tasks found matching the specified criteria")
        return 0

    # Group tasks by parent/child relationship
    parent_tasks = []
    child_tasks_by_parent: dict[str, list[TodoistTask]] = {}

    for task in tasks:
        if task.parent_id:
            # This is a child task
            if task.parent_id not in child_tasks_by_parent:
                child_tasks_by_parent[task.parent_id] = []
            child_tasks_by_parent[task.parent_id].append(task)
        else:
            # This is a parent task (or standalone task)
            parent_tasks.append(task)

    # Initialize exporter
    exporter = ObsidianExporter(export_config)

    # Export only parent tasks (standalone tasks and parents with children)
    exported_count = 0
    for task in parent_tasks:
        project = projects_dict.get(task.project_id)
        if not project:
            logger.warning(f"Project not found for task: {task.content}")
            continue

        # Skip completed tasks if not including them
        if task.is_completed and not include_completed:
            continue

        # Get child tasks for this parent
        child_tasks = child_tasks_by_parent.get(task.id, [])

        # Get comments if enabled
        comments = None
        if export_config.include_comments:
            try:
                comments = client.get_task_comments(task.id)
                if comments:
                    logger.info(
                        f"Fetched {len(comments)} comments for task '{task.content}'"
                    )
            except TodoistAPIError as e:
                logger.warning(f"Failed to get comments for task '{task.content}': {e}")

        # Export the task with its child tasks
        try:
            exporter.export_task(task, project, comments, child_tasks)
            exported_count += 1
        except Exception as e:
            logger.error(f"Failed to export task '{task.content}': {e}")

    logger.info(f"Exported {exported_count} tasks to {export_config.output_dir}")
    return exported_count
