"""Todoist API client using the official todoist-api-python library."""

import logging
import os
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field
from todoist_api_python.api import TodoistAPI
from todoist_api_python.models import Comment as TodoistAPIComment
from todoist_api_python.models import Project as TodoistAPIProject
from todoist_api_python.models import Task as TodoistAPITask

logger = logging.getLogger(__name__)


class TodoistProject(BaseModel):
    """Represents a Todoist project."""

    id: str
    name: str
    color: str
    is_shared: bool = False
    url: str = ""

    @classmethod
    def from_api_project(cls, api_project: TodoistAPIProject) -> "TodoistProject":
        """Create TodoistProject from the API project object."""
        return cls(
            id=api_project.id,
            name=api_project.name,
            color=api_project.color,
            is_shared=api_project.is_shared,
            url=api_project.url,
        )


class TodoistTask(BaseModel):
    """Represents a Todoist task."""

    id: str
    content: str
    description: str = ""
    project_id: str
    section_id: str | None = None
    parent_id: str | None = None
    order: int
    priority: int = 1
    labels: list[str] = Field(default_factory=list)
    due: dict[str, Any] | None = None
    url: str = ""
    comment_count: int = 0
    is_completed: bool = False
    created_at: str
    creator_id: str = ""
    assignee_id: str | None = None
    assigner_id: str | None = None

    @property
    def due_date(self) -> str | None:
        """Extract due date as string if available."""
        if self.due and "date" in self.due:
            date_value = self.due["date"]
            return str(date_value) if date_value is not None else None
        return None

    @property
    def priority_text(self) -> str:
        """Convert priority number to text."""
        priority_map = {4: "High", 3: "Medium", 2: "Low", 1: "None"}
        return priority_map.get(self.priority, "None")

    @classmethod
    def from_api_task(
        cls, api_task: TodoistAPITask, is_completed: bool = False
    ) -> "TodoistTask":
        """Create TodoistTask from the API task object."""
        # Convert due object to dict if present
        due_dict = None
        if api_task.due:
            due_dict = {
                "date": api_task.due.date,
                "string": getattr(api_task.due, "string", ""),
                "datetime": getattr(api_task.due, "datetime", None),
                "timezone": getattr(api_task.due, "timezone", None),
                "is_recurring": getattr(api_task.due, "is_recurring", False),
            }

        return cls(
            id=api_task.id,
            content=api_task.content,
            description=api_task.description or "",
            project_id=api_task.project_id,
            section_id=api_task.section_id,
            parent_id=api_task.parent_id,
            order=api_task.order,
            priority=api_task.priority,
            labels=api_task.labels or [],
            due=due_dict,
            url=api_task.url,
            comment_count=0,  # Not available in REST API v2
            is_completed=is_completed,  # Can be set based on API source
            created_at=str(api_task.created_at),
            creator_id=api_task.creator_id or "",
            assignee_id=api_task.assignee_id,
            assigner_id=api_task.assigner_id,
        )


class TodoistComment(BaseModel):
    """Represents a comment on a Todoist task."""

    id: str
    task_id: str
    content: str
    posted_at: str
    attachment: dict[str, Any] | None = None

    @classmethod
    def from_api_comment(cls, api_comment: TodoistAPIComment) -> "TodoistComment":
        """Create TodoistComment from the API comment object."""
        # Convert attachment if present
        attachment_dict = None
        if hasattr(api_comment, "attachment") and api_comment.attachment:
            attachment_dict = {
                "file_name": getattr(api_comment.attachment, "file_name", None),
                "file_type": getattr(api_comment.attachment, "file_type", None),
                "file_url": getattr(api_comment.attachment, "file_url", None),
                "resource_type": getattr(api_comment.attachment, "resource_type", None),
            }

        return cls(
            id=api_comment.id,
            task_id=getattr(api_comment, "task_id", ""),
            content=api_comment.content,
            posted_at=str(getattr(api_comment, "posted_at", "")),
            attachment=attachment_dict,
        )


class TodoistAPIError(Exception):
    """Custom exception for Todoist API errors."""

    pass


class TodoistClient:
    """Client for interacting with the Todoist REST API using the official library."""

    def __init__(self, api_token: str | None = None):
        """Initialize the Todoist client.

        Args:
            api_token: Todoist API token. If not provided, will try to get from environment.
        """
        self.api_token: str | None = api_token or os.getenv("TODOIST_API_TOKEN")
        if not self.api_token:
            raise TodoistAPIError(
                "Todoist API token is required. Set TODOIST_API_TOKEN "
                + "environment variable or pass it directly to the constructor."
            )

        try:
            self._api = TodoistAPI(self.api_token)
        except Exception as e:
            logger.error(f"Failed to initialize Todoist API client: {e}")
            raise TodoistAPIError(
                f"Failed to initialize Todoist API client: {e}"
            ) from e

    def get_projects(self) -> list[TodoistProject]:
        """Fetch all projects.

        Returns:
            List of TodoistProject objects

        Raises:
            TodoistAPIError: If the API request fails
        """
        try:
            logger.info("Fetching projects from Todoist")
            api_projects_paginator = self._api.get_projects()
            # Convert paginator to list by iterating through all results
            all_projects = []
            for projects_page in api_projects_paginator:
                for project in projects_page:
                    all_projects.append(TodoistProject.from_api_project(project))
            return all_projects
        except Exception as e:
            logger.error(f"Failed to fetch projects: {e}")
            raise TodoistAPIError(f"Failed to fetch projects: {e}") from e

    def get_tasks(
        self, project_id: str | None = None, filter_expr: str | None = None
    ) -> list[TodoistTask]:
        """Fetch tasks, optionally filtered by project or filter expression.

        Args:
            project_id: Optional project ID to filter tasks
            filter_expr: Optional Todoist filter expression

        Returns:
            List of TodoistTask objects

        Raises:
            TodoistAPIError: If the API request fails
        """
        try:
            params = {}
            if project_id:
                params["project_id"] = project_id
            if filter_expr:
                params["filter"] = filter_expr

            logger.info(f"Fetching tasks from Todoist with params: {params}")

            if filter_expr:
                # Use the filter_tasks method for filter expressions
                api_tasks_paginator = self._api.filter_tasks(query=filter_expr)
            elif project_id:
                # Use the project_id parameter
                api_tasks_paginator = self._api.get_tasks(project_id=project_id)
            else:
                # Get all tasks
                api_tasks_paginator = self._api.get_tasks()

            # Convert paginator to list by iterating through all results
            all_tasks = []
            for tasks_page in api_tasks_paginator:
                for task in tasks_page:
                    all_tasks.append(TodoistTask.from_api_task(task))
            return all_tasks
        except Exception as e:
            logger.error(f"Failed to fetch tasks: {e}")
            raise TodoistAPIError(f"Failed to fetch tasks: {e}") from e

    def get_task_comments(self, task_id: str) -> list[TodoistComment]:
        """Fetch comments for a specific task.

        Args:
            task_id: The task ID to fetch comments for

        Returns:
            List of TodoistComment objects

        Raises:
            TodoistAPIError: If the API request fails
        """
        try:
            logger.info(f"Fetching comments for task {task_id}")
            # The get_comments method returns an iterator that yields pages of comments
            comments_iterator = self._api.get_comments(task_id=task_id)

            all_comments = []
            for comments_page in comments_iterator:
                for comment in comments_page:
                    all_comments.append(TodoistComment.from_api_comment(comment))

            return all_comments
        except Exception as e:
            logger.error(f"Failed to fetch comments for task {task_id}: {e}")
            raise TodoistAPIError(
                f"Failed to fetch comments for task {task_id}: {e}"
            ) from e

    def get_completed_tasks(
        self,
        project_id: str | None = None,
    ) -> list[TodoistTask]:
        """Fetch completed tasks.

        Args:
            project_id: Optional project ID to filter tasks

        Returns:
            List of completed TodoistTask objects

        Note:
            This fetches completed tasks from today using the official
            get_completed_tasks_by_completion_date API method.
        """
        try:
            # Get tasks completed today
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)

            logger.info(f"Fetching completed tasks from {today} to {tomorrow}")

            # Build filter query if project_id is specified
            filter_query = None
            if project_id:
                # Get project name first to build filter
                projects = self.get_projects()
                project_name = next(
                    (p.name for p in projects if p.id == project_id), None
                )
                if project_name:
                    filter_query = f"#{project_name}"

            # Use the official completed tasks API
            api_tasks_paginator = self._api.get_completed_tasks_by_completion_date(
                since=today, until=tomorrow, filter_query=filter_query
            )

            all_tasks = []
            for tasks_page in api_tasks_paginator:
                for task in tasks_page:
                    # Mark these tasks as completed since they come from completed tasks API
                    task_data = TodoistTask.from_api_task(task, is_completed=True)
                    all_tasks.append(task_data)
            return all_tasks
        except Exception as e:
            logger.error(f"Failed to fetch completed tasks: {e}")
            raise TodoistAPIError(f"Failed to fetch completed tasks: {e}") from e

    def test_connection(self) -> bool:
        """Test the API connection and authentication.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            _ = self.get_projects()
            logger.info("Successfully connected to Todoist API")
            return True
        except TodoistAPIError as e:
            logger.error(f"Failed to connect to Todoist API: {e}")
            return False
