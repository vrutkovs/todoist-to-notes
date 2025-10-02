"""Command-line interface for Todoist to Obsidian Notes exporter."""

import logging
import sys
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .obsidian_exporter import ExportConfig, ObsidianExporter
from .todoist_client import TodoistAPIError, TodoistClient

# Load environment variables from .env file
load_dotenv()

console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.version_option()
def cli(verbose: bool):
    """Export Todoist tasks as Obsidian-compatible markdown notes."""
    setup_logging(verbose)


@cli.command()
@click.option(
    "--api-token",
    "-t",
    envvar="TODOIST_API_TOKEN",
    help="Todoist API token (or set TODOIST_API_TOKEN env var)",
)
def test(api_token: Optional[str]):
    """Test connection to Todoist API."""
    if not api_token:
        console.print(
            "[red]Error:[/red] Todoist API token is required. "
            "Set TODOIST_API_TOKEN environment variable or use "
            "--api-token option."
        )
        sys.exit(1)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Testing connection...", total=None)

            client = TodoistClient(api_token)
            if client.test_connection():
                console.print(
                    "[green]✅ Successfully connected to Todoist API![/green]"
                )

                # Show some basic info
                projects = client.get_projects()
                console.print(f"Found {len(projects)} projects in your account.")

    except TodoistAPIError as e:
        console.print(f"[red]❌ Connection failed:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--api-token",
    "-t",
    envvar="TODOIST_API_TOKEN",
    help="Todoist API token (or set TODOIST_API_TOKEN env var)",
)
def list_projects(api_token: Optional[str]):
    """List all projects in your Todoist account."""
    if not api_token:
        console.print(
            "[red]Error:[/red] Todoist API token is required. "
            "Set TODOIST_API_TOKEN environment variable or use "
            "--api-token option."
        )
        sys.exit(1)

    try:
        client = TodoistClient(api_token)
        projects = client.get_projects()

        if not projects:
            console.print("No projects found in your account.")
            return

        table = Table(title="Todoist Projects")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Color", style="green")
        table.add_column("Favorite", justify="center")
        table.add_column("Shared", justify="center")

        for project in projects:
            table.add_row(
                project.id,
                project.name,
                project.color,
                "⭐" if project.is_favorite else "",
                "🔗" if project.is_shared else "",
            )

        console.print(table)

    except TodoistAPIError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    default=Path.cwd() / "obsidian_export",
    help="Output directory for exported notes",
)
@click.option(
    "--api-token",
    "-t",
    envvar="TODOIST_API_TOKEN",
    help="Todoist API token (or set TODOIST_API_TOKEN env var)",
)
@click.option("--project-id", "-p", help="Export only tasks from specific project ID")
@click.option("--project-name", help="Export only tasks from specific project name")
@click.option(
    "--include-completed", "-c", is_flag=True, help="Include completed tasks in export"
)
@click.option("--no-comments", is_flag=True, help="Skip exporting task comments")
@click.option(
    "--no-project-folders",
    is_flag=True,
    help="Don't create separate folders for each project",
)
@click.option(
    "--tag-prefix",
    default="todoist",
    help="Prefix for generated tags (default: todoist)",
)
@click.option(
    "--filter",
    "-f",
    help="Todoist filter expression (e.g., 'today', 'overdue', '@urgent')",
)
def export(
    output_dir: Path,
    api_token: Optional[str],
    project_id: Optional[str],
    project_name: Optional[str],
    include_completed: bool,
    no_comments: bool,
    no_project_folders: bool,
    tag_prefix: str,
    filter: Optional[str],
):
    """Export Todoist tasks as Obsidian markdown notes."""
    if not api_token:
        console.print(
            "[red]Error:[/red] Todoist API token is required. "
            "Set TODOIST_API_TOKEN environment variable or use "
            "--api-token option."
        )
        sys.exit(1)

    try:
        # Initialize client
        client = TodoistClient(api_token)

        # Get projects
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Fetching projects...", total=None)
            projects = client.get_projects()
            projects_dict = {p.id: p for p in projects}

        # Filter by project if specified
        target_project_id = project_id
        if project_name and not project_id:
            matching_projects = [
                p for p in projects if p.name.lower() == project_name.lower()
            ]
            if not matching_projects:
                console.print(f"[red]Error:[/red] Project '{project_name}' not found.")
                available = ", ".join([p.name for p in projects])
                console.print(f"Available projects: {available}")
                sys.exit(1)
            target_project_id = matching_projects[0].id

        # Configure exporter
        config = ExportConfig(
            output_dir=output_dir,
            create_project_folders=not no_project_folders,
            include_completed=include_completed,
            include_comments=not no_comments,
            tag_prefix=tag_prefix,
        )
        exporter = ObsidianExporter(config)

        # Get tasks
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Fetching tasks...", total=None)
            tasks = client.get_tasks(project_id=target_project_id, filter_expr=filter)

        if not tasks:
            console.print("No tasks found matching the specified criteria.")
            return

        console.print(f"Found {len(tasks)} tasks to export.")

        # Export tasks
        exported_counts = {}
        total_exported = 0

        with Progress(console=console) as progress:
            export_task = progress.add_task("Exporting tasks...", total=len(tasks))

            for task in tasks:
                project = projects_dict.get(task.project_id)
                if not project:
                    console.print(
                        f"[yellow]Warning:[/yellow] Project not found for "
                        f"task: {task.content}"
                    )
                    progress.advance(export_task)
                    continue

                # Get comments if enabled
                comments = None
                if config.include_comments and task.comment_count > 0:
                    try:
                        comments = client.get_task_comments(task.id)
                    except TodoistAPIError as e:
                        console.print(
                            f"[yellow]Warning:[/yellow] Failed to get comments "
                            f"for task '{task.content}': {e}"
                        )

                # Export task
                try:
                    exporter.export_task(task, project, comments)

                    # Update counts
                    if project.id not in exported_counts:
                        exported_counts[project.id] = 0
                    exported_counts[project.id] += 1
                    total_exported += 1

                except Exception as e:
                    console.print(
                        f"[red]Error exporting task '{task.content}':[/red] {e}"
                    )

                progress.advance(export_task)

        # Create project indices if using project folders
        if config.create_project_folders:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Creating project indices...", total=None)

                for project_id, count in exported_counts.items():
                    if count > 0:
                        project = projects_dict[project_id]
                        project_dir = output_dir / exporter.sanitize_filename(
                            project.name
                        )
                        task_files = list(project_dir.glob("*.md"))
                        task_files = [f for f in task_files if f.name != "README.md"]
                        exporter.export_project_index(project, task_files)

        # Create master index
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Creating master index...", total=None)
            relevant_projects = [
                p for p in projects if exported_counts.get(p.id, 0) > 0
            ]
            exporter.create_master_index(relevant_projects, exported_counts)

        # Show summary
        summary = Panel.fit(
            f"[green]✅ Export completed successfully![/green]\n\n"
            f"Exported: {total_exported} tasks\n"
            f"Projects: {len(exported_counts)}\n"
            f"Output directory: {output_dir.absolute()}\n\n"
            f"Included completed tasks: "
            f"{'Yes' if include_completed else 'No'}\n"
            f"Included comments: {'Yes' if not no_comments else 'No'}\n"
            f"Created project folders: "
            f"{'Yes' if not no_project_folders else 'No'}",
            title="Export Summary",
            border_style="green",
        )
        console.print(summary)

    except TodoistAPIError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        if logging.getLogger().level == logging.DEBUG:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Directory where to create the .env file",
)
def init(output_dir: Path):
    """Initialize configuration by creating a .env file template."""
    env_path = output_dir / ".env"

    if env_path.exists():
        if not click.confirm(f".env file already exists at {env_path}. Overwrite?"):
            console.print("Initialization cancelled.")
            return

    env_content = """# Todoist to Obsidian Notes Exporter Configuration
#
# Get your Todoist API token from: https://todoist.com/prefs/integrations
TODOIST_API_TOKEN=your_token_here

# Optional: Default export settings
# EXPORT_OUTPUT_DIR=./obsidian_export
# EXPORT_INCLUDE_COMPLETED=false
# EXPORT_INCLUDE_COMMENTS=true
# EXPORT_CREATE_PROJECT_FOLDERS=true
# EXPORT_TAG_PREFIX=todoist
"""

    with open(env_path, "w") as f:
        f.write(env_content)

    console.print(f"[green]✅ Created .env template at {env_path}[/green]")
    console.print("\nNext steps:")
    console.print("1. Edit the .env file and add your Todoist API token")
    console.print("2. Get your token from: https://todoist.com/prefs/integrations")
    console.print("3. Run 'todoist-to-notes test' to verify your setup")
    console.print("4. Run 'todoist-to-notes export' to start exporting your tasks")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
