"""Command-line interface for Todoist to Obsidian Notes exporter."""

import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .core import export_tasks_internal
from .obsidian_exporter import ExportConfig
from .scheduler import ScheduledSync
from .todoist_client import TodoistAPIError, TodoistClient

# Load environment variables from .env file
_ = load_dotenv()

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
@click.version_option(package_name="todoist-to-notes")
def cli(verbose: bool) -> None:
    """Export Todoist tasks as Obsidian-compatible markdown notes."""
    setup_logging(verbose)


@cli.command()
@click.option(
    "--api-token",
    "-t",
    envvar="TODOIST_API_TOKEN",
    help="Todoist API token (or set TODOIST_API_TOKEN env var)",
)
def test(api_token: str | None) -> None:
    """Test connection to Todoist API."""
    if not api_token:
        console.print(
            "[red]Error:[/red] Todoist API token is required. "
            + "Set TODOIST_API_TOKEN environment variable or use "
            + "--api-token option."
        )
        sys.exit(1)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            _ = progress.add_task("Testing connection...", total=None)

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
def list_projects(api_token: str | None) -> None:
    """List all projects in your Todoist account."""
    if not api_token:
        console.print(
            "[red]Error:[/red] Todoist API token is required. "
            + "Set TODOIST_API_TOKEN environment variable or use "
            + "--api-token option."
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
        table.add_column("Shared", justify="center")

        for project in projects:
            table.add_row(
                project.id,
                project.name,
                project.color,
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
    envvar="EXPORT_OUTPUT_DIR",
    default=Path.cwd() / "obsidian_export",
    help="Output directory for exported notes (or set EXPORT_OUTPUT_DIR env var)",
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
    "--include-completed",
    "-c",
    is_flag=True,
    envvar="EXPORT_INCLUDE_COMPLETED",
    help="Include completed tasks in export (or set EXPORT_INCLUDE_COMPLETED env var)",
)
@click.option(
    "--no-comments",
    is_flag=True,
    help="Skip exporting task comments",
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
    api_token: str | None,
    project_id: str | None,
    project_name: str | None,
    include_completed: bool,
    no_comments: bool,
    tag_prefix: str,
    filter: str | None,
) -> int | None:
    """Export Todoist tasks as Obsidian markdown notes."""
    if not api_token:
        console.print(
            "[red]Error:[/red] Todoist API token is required. "
            + "Set TODOIST_API_TOKEN environment variable or use "
            + "--api-token option."
        )
        sys.exit(1)

    try:
        # Initialize client
        client = TodoistClient(api_token)

        # Determine include_comments logic
        # Priority: --no-comments flag > EXPORT_INCLUDE_COMMENTS env var > default (True)
        should_include_comments = True
        if no_comments:
            should_include_comments = False
        elif os.getenv("EXPORT_INCLUDE_COMMENTS"):
            should_include_comments = os.getenv("EXPORT_INCLUDE_COMMENTS").lower() in (
                "true",
                "1",
                "yes",
            )

        # Configure exporter
        config = ExportConfig(
            output_dir=output_dir,
            include_completed=include_completed,
            include_comments=should_include_comments,
            tag_prefix=tag_prefix,
        )

        # Use the core export function
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            _ = progress.add_task("Exporting tasks...", total=None)

            total_exported = export_tasks_internal(
                client=client,
                export_config=config,
                project_id=project_id,
                project_name=project_name,
                filter_expr=filter,
                include_completed=include_completed,
            )

        # Show summary
        summary = Panel.fit(
            "[green]✅ Export completed successfully![/green]\n\n"
            + f"Exported: {total_exported} tasks\n"
            + f"Output directory: {output_dir.absolute()}\n\n"
            + "Included completed tasks: "
            + f"{'Yes' if include_completed else 'No'}\n"
            + f"Included comments: {'Yes' if not no_comments else 'No'}",
            title="Export Summary",
            border_style="green",
        )
        console.print(summary)

        return total_exported

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
def init(output_dir: Path) -> None:
    """Initialize configuration by creating a .env file template."""
    env_path = output_dir / ".env"

    if env_path.exists() and not click.confirm(
        f".env file already exists at {env_path}. Overwrite?"
    ):
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
# EXPORT_TAG_PREFIX=todoist
"""

    with open(env_path, "w") as f:
        _ = f.write(env_content)

    console.print(f"[green]✅ Created .env template at {env_path}[/green]")
    console.print("\nNext steps:")
    console.print("1. Edit the .env file and add your Todoist API token")
    console.print("2. Get your token from: https://todoist.com/prefs/integrations")
    console.print("3. Run 'todoist-to-notes test' to verify your setup")
    console.print("4. Run 'todoist-to-notes export' to start exporting your tasks")


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
    "--tag-prefix",
    default="todoist",
    help="Prefix for generated tags (default: todoist)",
)
@click.option(
    "--filter",
    "-f",
    help="Todoist filter expression (e.g., 'today', 'overdue', '@urgent')",
)
@click.option(
    "--interval",
    type=int,
    default=15,
    help="Sync interval in minutes (default: 15)",
)
@click.option(
    "--time",
    "sync_time",
    help="Daily sync time in HH:MM format (e.g., '09:00')",
)
@click.option(
    "--once",
    is_flag=True,
    help="Run sync once immediately and exit",
)
@click.option(
    "--no-status",
    is_flag=True,
    help="Don't show live status display",
)
def schedule(
    output_dir: Path,
    api_token: str | None,
    project_id: str | None,
    project_name: str | None,
    include_completed: bool,
    no_comments: bool,
    tag_prefix: str,
    filter: str | None,
    interval: int,
    sync_time: str | None,
    once: bool,
    no_status: bool,
) -> None:
    """Run scheduled sync of Todoist tasks to Obsidian notes."""
    if not api_token:
        console.print(
            "[red]Error:[/red] Todoist API token is required. "
            + "Set TODOIST_API_TOKEN environment variable or use "
            + "--api-token option."
        )
        sys.exit(1)

    # Configure export
    config = ExportConfig(
        output_dir=output_dir,
        include_completed=include_completed,
        include_comments=not no_comments,
        tag_prefix=tag_prefix,
    )

    # Initialize scheduled sync
    try:
        sync = ScheduledSync(
            api_token=api_token,
            export_config=config,
            project_id=project_id,
            project_name=project_name,
            filter_expr=filter,
            include_completed=include_completed,
        )

        if once:
            # Run once and exit
            success = sync.run_once_now()
            sys.exit(0 if success else 1)

        # Setup schedule
        if sync_time:
            _ = sync.run_at(sync_time)
            console.print(f"[green]📅 Scheduled daily sync at {sync_time}[/green]")
        else:
            _ = sync.run_every(interval, "minutes")
            console.print(f"[green]⏰ Scheduled sync every {interval} minutes[/green]")

        # Start the scheduler
        sync.start(show_status=not no_status)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if logging.getLogger().level == logging.DEBUG:
            console.print_exception()
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
