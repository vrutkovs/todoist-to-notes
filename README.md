# Todoist to Obsidian Notes Exporter

Export your Todoist tasks as beautifully formatted Obsidian-compatible markdown notes with full metadata, tags, and cross-linking support.

## Features

- 🚀 **Fast UV-based Python project** - Modern dependency management and packaging
- 📝 **Rich Markdown Export** - Tasks exported as fully-featured Obsidian notes
- 🏷️ **Smart Tagging** - Automatic tags for projects, priorities, labels, and status
- 🗂️ **Project Organization** - Optional folder structure matching your Todoist projects
- 💬 **Comment Support** - Include task comments in exported notes
- 🔗 **Cross-linking** - Automatic links between related notes and projects
- ⚡ **CLI Interface** - Easy-to-use command line with rich output
- 🎯 **Flexible Filtering** - Export specific projects or use Todoist filter expressions
- 📊 **Export Summaries** - Automatic index generation for easy navigation

## Installation

### Prerequisites

- Python 3.13 or higher
- UV package manager (recommended) or pip
- Pre-commit hooks (automatically installed via `make setup`)

### Install UV (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install the Package

#### Option 1: From Source (Development)

```bash
git clone https://github.com/vrutkovs/todoist-to-notes.git
cd todoist-to-notes
uv sync --dev
```

#### Option 2: Install Directly with UV

```bash
uv tool install todoist-to-notes
```

#### Option 3: Using pip

```bash
pip install todoist-to-notes
```

## Quick Start

### 1. Get Your Todoist API Token

1. Go to [Todoist Integrations](https://todoist.com/prefs/integrations)
2. Scroll down to "API token" section
3. Copy your token

### 2. Initialize Configuration

```bash
todoist-to-notes init
```

This creates a `.env` file template. Edit it and add your API token:

```bash
# Edit the .env file
TODOIST_API_TOKEN=your_actual_token_here
```

### 3. Test Your Connection

```bash
todoist-to-notes test
```

### 4. Export Your Tasks

```bash
# Basic export - exports all active tasks to ./obsidian_export/
todoist-to-notes export

# Export to specific directory
todoist-to-notes export -o ~/Documents/MyVault/TodoistImport/

# Include completed tasks
todoist-to-notes export --include-completed

# Export specific project only
todoist-to-notes export --project-name "Work"

# Use Todoist filters
todoist-to-notes export --filter "today | overdue"
```

## Basic Usage

```bash
# Export all tasks once
todoist-to-notes export

# Export with custom options
todoist-to-notes export --filter "today" --include-completed

# Schedule automatic sync every 15 minutes
todoist-to-notes schedule

# Schedule daily sync at 9:00 AM
todoist-to-notes schedule --time "09:00"

# Run sync once and exit
todoist-to-notes schedule --once
```

## Command Reference

### `todoist-to-notes export`

Export Todoist tasks as Obsidian markdown notes (one-time export).

**Options:**

- `-o, --output-dir PATH` - Output directory (default: `./obsidian_export/`)
- `-t, --api-token TEXT` - Todoist API token (or set `TODOIST_API_TOKEN` env var)
- `-p, --project-id TEXT` - Export only tasks from specific project ID
- `--project-name TEXT` - Export only tasks from specific project name
- `-c, --include-completed` - Include completed tasks in export
- `--no-comments` - Skip exporting task comments
- `--no-project-folders` - Don't create separate folders for each project
- `--tag-prefix TEXT` - Prefix for generated tags (default: `todoist`)
- `-f, --filter TEXT` - Todoist filter expression

### `todoist-to-notes schedule`

Run scheduled sync of Todoist tasks to Obsidian notes.

**Options:**

All export options plus:

- `--interval INTEGER` - Sync interval in minutes (default: 15)
- `--time TEXT` - Daily sync time in HH:MM format (e.g., '09:00')
- `--once` - Run sync once immediately and exit
- `--no-status` - Don't show live status display

**Examples:**

```bash
# Schedule sync every 30 minutes
todoist-to-notes schedule --interval 30

# Schedule daily sync at 8:30 AM
todoist-to-notes schedule --time "08:30"

# Schedule with filters and custom output
todoist-to-notes schedule --filter "today | overdue" --output-dir ~/vault/tasks/

# Run once with scheduling options
todoist-to-notes schedule --once --project-name "Work"
```



### `todoist-to-notes test`

Test connection to Todoist API.

### `todoist-to-notes list-projects`

List all projects in your Todoist account.

### `todoist-to-notes init`

Initialize configuration by creating a .env file template.

## Output Structure

### With Project Folders (Default)

```
obsidian_export/
├── Personal/
│   ├── Buy_groceries_123.md
│   └── Call_dentist_456.md
├── Work/
│   ├── Finish_report_789.md
│   └── Team_meeting_prep_012.md
└── Inbox/
    └── Random_idea_345.md
```

## Scheduling Features

### Automatic Sync
The scheduler runs continuously and syncs your tasks at specified intervals:

- **Interval-based**: Sync every N minutes/hours
- **Time-based**: Sync daily at a specific time
- **Live status**: Real-time display of sync status and next run time
- **Graceful shutdown**: Ctrl+C for clean exit

### Use Cases

**Continuous Integration:**
```bash
# Keep Obsidian vault in sync every 15 minutes
todoist-to-notes schedule --interval 15 --output-dir ~/obsidian-vault/todoist/
```

**Daily Planning:**
```bash
# Sync today's tasks every morning at 8:00 AM
todoist-to-notes schedule --time "08:00" --filter "today"
```

**Project Monitoring:**
```bash
# Monitor specific project every 5 minutes
todoist-to-notes schedule --interval 5 --project-name "Important Project"
```

## Note Format

Each exported task becomes a markdown note with:

### YAML Frontmatter

```yaml
---
title: "Buy groceries"
todoist_id: "123456789"
project: "Personal"
project_id: "987654321"
created: "2024-01-15T10:30:00Z"
due_date: "2024-01-16"
priority: 2
priority_text: "Low"
labels: ["shopping", "errands"]
completed: false
todoist_url: "https://todoist.com/showTask?id=123456789"
tags: ["todoist", "todoist/personal", "todoist/label/shopping"]
---
```

### Main Content

```markdown
# ⬜ Buy groceries

## Description

Need to pick up items for the week:
- Milk
- Bread
- Fruits

## Comments

### Comment - 2024-01-15 10:30:00

Don't forget organic milk this time!

---

#todoist #todoist/personal #todoist/status/active #todoist/label/shopping
```

## Configuration

### Environment Variables

Create a `.env` file in your project directory:

```bash
# Required
TODOIST_API_TOKEN=your_token_here

# Optional defaults
EXPORT_OUTPUT_DIR=./obsidian_export
EXPORT_INCLUDE_COMPLETED=false
EXPORT_INCLUDE_COMMENTS=true
EXPORT_CREATE_PROJECT_FOLDERS=true
EXPORT_TAG_PREFIX=todoist
```

### Todoist Filters

You can use any Todoist filter expression with both `export` and `schedule` commands:

- `today` - Today's tasks
- `overdue` - Overdue tasks
- `p1` - Priority 1 tasks
- `@urgent` - Tasks with "urgent" label
- `assigned to: me` - Tasks assigned to you
- `#Work` - Tasks in Work project
- `due: 7 days` - Tasks due in next 7 days
- `created: 1 week` - Tasks created in last week

Combine filters with `&` (AND) and `|` (OR):
- `today | overdue` - Today's or overdue tasks
- `p1 & #Work` - High priority tasks in Work project

### Scheduling with Filters

```bash
# Keep urgent tasks synced every 5 minutes
todoist-to-notes schedule --interval 5 --filter "p1 | overdue"

# Daily sync of today's tasks at 7 AM
todoist-to-notes schedule --time "07:00" --filter "today"
```

## Development

### Development

```bash
git clone https://github.com/vrutkovs/todoist-to-notes.git
cd todoist-to-notes
make setup  # Install deps, setup, and pre-commit hooks
make check  # Run tests and quality checks (ruff + pytest)
make build  # Build package
```

## Troubleshooting

### Common Issues

**"API token is required" error:**
- Make sure you've set `TODOIST_API_TOKEN` environment variable
- Or use `--api-token` option directly
- Check that your token is valid at [Todoist Integrations](https://todoist.com/prefs/integrations)

**"Connection failed" error:**
- Check your internet connection
- Verify your API token is correct
- Try running `todoist-to-notes test` to diagnose

**Empty export:**
- Check that you have tasks matching your criteria
- Try without filters first: `todoist-to-notes export`
- Use `--include-completed` if you only have completed tasks

**Permission errors:**
- Make sure you have write permissions to the output directory
- Try a different output directory: `todoist-to-notes export -o ~/Desktop/export/`

**Scheduler not stopping:**
- Use Ctrl+C to gracefully stop the scheduler
- If it doesn't respond, use `kill -TERM <pid>` from another terminal

**Scheduler missing syncs:**
- Check system time and timezone settings
- Ensure the machine doesn't go to sleep during scheduled times
- Use interval-based scheduling for more reliable syncing

### Debug Mode

Run with verbose logging:

```bash
todoist-to-notes -v export
todoist-to-notes -v schedule --interval 1  # Debug scheduling
```

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Todoist](https://todoist.com/) for the excellent API
- [Obsidian](https://obsidian.md/) for the amazing note-taking app
- [UV](https://github.com/astral-sh/uv) for modern Python package management
- [Rich](https://github.com/Textualize/rich) for beautiful CLI output
