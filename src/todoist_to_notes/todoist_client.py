"""Todoist API client for fetching tasks and projects."""

import logging
import os
from typing import Any, Dict, List, Optional

import requests
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TodoistProject(BaseModel):
    """Represents a Todoist project."""

    id: str
    name: str
    color: str
    is_favorite: bool = False
    is_shared: bool = False
    url: str = ""


class TodoistTask(BaseModel):
    """Represents a Todoist task."""

    id: str
    content: str
    description: str = ""
    project_id: str
    section_id: Optional[str] = None
    parent_id: Optional[str] = None
    order: int
    priority: int = 1
    labels: List[str] = Field(default_factory=list)
    due: Optional[Dict[str, Any]] = None
    url: str = ""
    comment_count: int = 0
    is_completed: bool = False
    created_at: str
    creator_id: str = ""
    assignee_id: Optional[str] = None
    assigner_id: Optional[str] = None

    @property
    def due_date(self) -> Optional[str]:
        """Extract due date as string if available."""
        if self.due and "date" in self.due:
            return self.due["date"]
        return None

    @property
    def priority_text(self) -> str:
        """Convert priority number to text."""
        priority_map = {4: "High", 3: "Medium", 2: "Low", 1: "None"}
        return priority_map.get(self.priority, "None")


class TodoistComment(BaseModel):
    """Represents a comment on a Todoist task."""

    id: str
    task_id: str
    content: str
    posted_at: str
    attachment: Optional[Dict[str, Any]] = None


class TodoistAPIError(Exception):
    """Custom exception for Todoist API errors."""

    pass


class TodoistClient:
    """Client for interacting with the Todoist REST API."""

    BASE_URL = "https://api.todoist.com/rest/v2"

    def __init__(self, api_token: Optional[str] = None):
        """Initialize the Todoist client.

        Args:
            api_token: Todoist API token. If not provided, will try to get from environment.
        """
        self.api_token = api_token or os.getenv("TODOIST_API_TOKEN")
        if not self.api_token:
            raise TodoistAPIError(
                "Todoist API token is required. Set TODOIST_API_TOKEN "
                "environment variable or pass it directly to the constructor."
            )

        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make a request to the Todoist API.

        Args:
            method: HTTP method
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments to pass to requests

        Returns:
            JSON response data

        Raises:
            TodoistAPIError: If the API request fails
        """
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()

            if response.status_code == 204:  # No content
                return None

            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise TodoistAPIError(f"Failed to make request to {url}: {e}")

    def get_projects(self) -> List[TodoistProject]:
        """Fetch all projects.

        Returns:
            List of TodoistProject objects
        """
        logger.info("Fetching projects from Todoist")
        data = self._make_request("GET", "/projects")
        return [TodoistProject(**project) for project in data]

    def get_tasks(
        self, project_id: Optional[str] = None, filter_expr: Optional[str] = None
    ) -> List[TodoistTask]:
        """Fetch tasks, optionally filtered by project or filter expression.

        Args:
            project_id: Optional project ID to filter tasks
            filter_expr: Optional Todoist filter expression

        Returns:
            List of TodoistTask objects
        """
        params = {}
        if project_id:
            params["project_id"] = project_id
        if filter_expr:
            params["filter"] = filter_expr

        logger.info(f"Fetching tasks from Todoist with params: {params}")
        data = self._make_request("GET", "/tasks", params=params)
        return [TodoistTask(**task) for task in data]

    def get_task_comments(self, task_id: str) -> List[TodoistComment]:
        """Fetch comments for a specific task.

        Args:
            task_id: The task ID to fetch comments for

        Returns:
            List of TodoistComment objects
        """
        logger.info(f"Fetching comments for task {task_id}")
        data = self._make_request("GET", f"/comments?task_id={task_id}")
        return [TodoistComment(**comment) for comment in data]

    def get_completed_tasks(
        self,
        project_id: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[TodoistTask]:
        """Fetch completed tasks.

        Args:
            project_id: Optional project ID to filter tasks
            since: Optional ISO date string for start of range
            until: Optional ISO date string for end of range

        Returns:
            List of completed TodoistTask objects
        """
        # Note: This requires the sync API endpoint which has different
        # authentication. For now, we'll use a filter to get completed tasks
        # from today
        filter_expr = "completed today"
        if project_id:
            # Get project name first to build filter
            projects = self.get_projects()
            project_name = next((p.name for p in projects if p.id == project_id), None)
            if project_name:
                filter_expr = f"completed today & #{project_name}"

        return self.get_tasks(filter_expr=filter_expr)

    def test_connection(self) -> bool:
        """Test the API connection and authentication.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            self.get_projects()
            logger.info("Successfully connected to Todoist API")
            return True
        except TodoistAPIError as e:
            logger.error(f"Failed to connect to Todoist API: {e}")
            return False
