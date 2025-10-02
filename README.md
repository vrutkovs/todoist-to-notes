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

- Python 3.8 or higher
- UV package manager (recommended) or pip

### Install UV (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install the Package

#### Option 1: From Source (Development)

```bash
git clone https://github.com/username/todoist-to-notes.git
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

## Usage Examples

### Export All Tasks with Comments

```bash
todoist-to-notes export \
  --output-dir ~/obsidian-vault/todoist/ \
  --include-completed \
  --tag-prefix "task"
```

### Export Today's Tasks Only

```bash
todoist-to-notes export \
  --filter "today" \
  --output-dir ~/obsidian-vault/daily/ \
  --no-project-folders
```

### Export Specific Project

```bash
# By project name
todoist-to-notes export --project-name "Personal"

# By project ID (get ID with list-projects command)
todoist-to-notes export --project-id "123456789"
```

### List All Your Projects

```bash
todoist-to-notes list-projects
```

## Command Reference

### `todoist-to-notes export`

Export Todoist tasks as Obsidian markdown notes.

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

**Examples:**

```bash
# Export everything to default location
todoist-to-notes export

# Export with custom settings
todoist-to-notes export -o ~/vault/tasks --include-completed --tag-prefix "todo"

# Export using filter
todoist-to-notes export -f "p1 | p2" --no-project-folders
```

### `todoist-to-notes test`

Test connection to Todoist API.

```bash
todoist-to-notes test
```

### `todoist-to-notes list-projects`

List all projects in your Todoist account.

```bash
todoist-to-notes list-projects
```

### `todoist-to-notes init`

Initialize configuration by creating a `.env` file template.

```bash
todoist-to-notes init
```

## Output Structure

### With Project Folders (Default)

```
obsidian_export/
├── Todoist_Export_Index.md          # Master index
├── Personal/
│   ├── README.md                     # Project index
│   ├── Buy_groceries_123.md
│   └── Call_dentist_456.md
├── Work/
│   ├── README.md
│   ├── Finish_report_789.md
│   └── Team_meeting_prep_012.md
└── Inbox/
    ├── README.md
    └── Random_idea_345.md
```

### Without Project Folders

```
obsidian_export/
├── Todoist_Export_Index.md
├── Buy_groceries_123.md
├── Call_dentist_456.md
├── Finish_report_789.md
└── Team_meeting_prep_012.md
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

## Metadata

- **Project**: [[Personal]]
- **Priority**: Low
- **Due Date**: 2024-01-16
- **Labels**: #shopping, #errands
- **Created**: 2024-01-15T10:30:00Z
- **Todoist URL**: [Open in Todoist](https://todoist.com/showTask?id=123456789)

## Comments

### Comment - 2024-01-15

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

You can use any Todoist filter expression with the `--filter` option:

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

## Development

### Setup Development Environment

```bash
git clone https://github.com/username/todoist-to-notes.git
cd todoist-to-notes

# Install with development dependencies
uv sync --dev
```

### Run Tests

```bash
uv run pytest
```

### Code Formatting

```bash
uv run black src/
uv run isort src/
```

### Type Checking

```bash
uv run mypy src/
```

### Build Package

```bash
uv build
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

### Debug Mode

Run with verbose logging:

```bash
todoist-to-notes -v export
```

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Todoist](https://todoist.com/) for the excellent API
- [Obsidian](https://obsidian.md/) for the amazing note-taking app
- [UV](https://github.com/astral-sh/uv) for modern Python package management
- [Rich](https://github.com/Textualize/rich) for beautiful CLI output