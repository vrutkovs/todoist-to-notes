"""Scheduler for periodic sync of Todoist tasks to Obsidian notes."""

import logging
import signal
import time
from datetime import datetime

import schedule
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from .core import export_tasks_internal
from .obsidian_exporter import ExportConfig
from .todoist_client import TodoistAPIError, TodoistClient

logger = logging.getLogger(__name__)
console = Console()


class ScheduledSync:
    """Manages scheduled synchronization of Todoist tasks."""

    def __init__(
        self,
        api_token: str,
        export_config: ExportConfig,
        project_id: str | None = None,
        project_name: str | None = None,
        filter_expr: str | None = None,
        include_completed: bool = False,
    ):
        """Initialize the scheduled sync.

        Args:
            api_token: Todoist API token
            export_config: Export configuration
            project_id: Optional project ID filter
            project_name: Optional project name filter
            filter_expr: Optional Todoist filter expression
            include_completed: Whether to include completed tasks
        """
        self.api_token = api_token
        self.export_config = export_config
        self.project_id = project_id
        self.project_name = project_name
        self.filter_expr = filter_expr
        self.include_completed = include_completed

        self.client = TodoistClient(api_token)
        self.last_sync: datetime | None = None
        self.sync_count = 0
        self.is_running = False

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum: int, _frame) -> None:
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()

    def sync_tasks(self) -> bool:
        """Perform a single sync operation.

        Returns:
            True if sync was successful, False otherwise
        """
        try:
            start_time = datetime.now()

            logger.info("Starting scheduled sync...")
            console.print(
                f"[blue]🔄 Starting sync at {start_time.strftime('%Y-%m-%d %H:%M:%S')}[/blue]"
            )

            # Perform the export
            exported_count = export_tasks_internal(
                client=self.client,
                export_config=self.export_config,
                project_id=self.project_id,
                project_name=self.project_name,
                filter_expr=self.filter_expr,
                include_completed=self.include_completed,
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.last_sync = end_time
            self.sync_count += 1

            logger.info(
                f"Sync completed successfully in {duration:.2f}s, exported {exported_count} tasks"
            )
            console.print(
                f"[green]✅ Sync completed in {duration:.2f}s - "
                f"Exported {exported_count} tasks[/green]"
            )

            return True

        except TodoistAPIError as e:
            logger.error(f"Todoist API error during sync: {e}")
            console.print(f"[red]❌ Todoist API error: {e}[/red]")
            return False

        except Exception as e:
            logger.error(f"Unexpected error during sync: {e}")
            console.print(f"[red]❌ Sync failed: {e}[/red]")
            return False

    def _create_status_panel(self) -> Panel:
        """Create a status panel for the live display."""
        status_text = Text()

        # Status indicator
        if self.is_running:
            status_text.append("🟢 Running", style="green bold")
        else:
            status_text.append("🔴 Stopped", style="red bold")

        status_text.append(f"\nSync count: {self.sync_count}")

        if self.last_sync:
            status_text.append(
                f"\nLast sync: {self.last_sync.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            status_text.append("\nLast sync: Never")

        # Next scheduled sync
        next_run = schedule.next_run()
        if next_run:
            status_text.append(f"\nNext sync: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

        # Configuration summary
        status_text.append(f"\nOutput: {self.export_config.output_dir}")

        if self.project_name:
            status_text.append(f"\nProject: {self.project_name}")
        elif self.project_id:
            status_text.append(f"\nProject ID: {self.project_id}")

        if self.filter_expr:
            status_text.append(f"\nFilter: {self.filter_expr}")

        status_text.append(f"\nInclude completed: {self.include_completed}")

        return Panel(
            status_text,
            title="Todoist Sync Status",
            border_style="blue",
            padding=(1, 2),
        )

    def run_every(self, interval: int, unit: str = "minutes") -> "ScheduledSync":
        """Schedule the sync to run at regular intervals.

        Args:
            interval: How often to run (e.g., 15)
            unit: Time unit ('minutes', 'hours', 'seconds')

        Returns:
            Self for method chaining
        """
        if unit == "minutes":
            schedule.every(interval).minutes.do(self.sync_tasks)
        elif unit == "hours":
            schedule.every(interval).hours.do(self.sync_tasks)
        elif unit == "seconds":
            schedule.every(interval).seconds.do(self.sync_tasks)
        else:
            raise ValueError(f"Unsupported time unit: {unit}")

        logger.info(f"Scheduled sync every {interval} {unit}")
        return self

    def run_at(self, time_str: str) -> "ScheduledSync":
        """Schedule the sync to run at a specific time daily.

        Args:
            time_str: Time in HH:MM format (e.g., "09:00")

        Returns:
            Self for method chaining
        """
        schedule.every().day.at(time_str).do(self.sync_tasks)
        logger.info(f"Scheduled daily sync at {time_str}")
        return self

    def run_once_now(self) -> bool:
        """Run a single sync immediately.

        Returns:
            True if sync was successful
        """
        console.print("[yellow]Running immediate sync...[/yellow]")
        return self.sync_tasks()

    def start(self, show_status: bool = True) -> None:
        """Start the scheduler and run indefinitely.

        Args:
            show_status: Whether to show live status display
        """
        self.is_running = True

        console.print("[green]🚀 Starting Todoist sync scheduler...[/green]")
        console.print("[yellow]Press Ctrl+C to stop[/yellow]")

        # Run initial sync if scheduled
        if schedule.jobs:
            console.print("[blue]Running initial sync...[/blue]")
            self.sync_tasks()

        if show_status:
            try:
                with Live(self._create_status_panel(), refresh_per_second=1) as live:
                    while self.is_running:
                        schedule.run_pending()
                        live.update(self._create_status_panel())
                        time.sleep(1)
            except KeyboardInterrupt:
                self.stop()
        else:
            try:
                while self.is_running:
                    schedule.run_pending()
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stop()

    def stop(self) -> None:
        """Stop the scheduler."""
        self.is_running = False
        schedule.clear()
        console.print("[red]🛑 Scheduler stopped[/red]")
        logger.info("Scheduler stopped")
