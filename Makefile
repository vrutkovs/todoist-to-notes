# Todoist to Obsidian Notes - Development Makefile
#
# This Makefile provides common development tasks for the project

.PHONY: help install install-dev test test-cov lint format type-check clean build run-example setup init

# Default target
help:
	@echo "Available targets:"
	@echo "  setup          - Complete project setup (install deps, init config)"
	@echo "  install        - Install project dependencies"
	@echo "  install-dev    - Install development dependencies"
	@echo "  init           - Initialize configuration (.env file)"
	@echo "  test           - Run tests"
	@echo "  test-cov       - Run tests with coverage report"
	@echo "  lint           - Run linting (flake8)"
	@echo "  format         - Format code (black, isort)"
	@echo "  format-check   - Check code formatting without applying changes"
	@echo "  type-check     - Run type checking (mypy)"
	@echo "  clean          - Clean build artifacts and cache files"
	@echo "  build          - Build the package"
	@echo "  run-example    - Run the example usage script"
	@echo "  cli-help       - Show CLI help"
	@echo "  cli-test       - Test CLI connection"
	@echo "  cli-projects   - List Todoist projects"
	@echo "  cli-export     - Run example export"

# Setup targets
setup: install-dev init
	@echo "✅ Project setup complete!"
	@echo "Next steps:"
	@echo "  1. Edit .env file and add your Todoist API token"
	@echo "  2. Run 'make cli-test' to verify connection"
	@echo "  3. Run 'make cli-export' to test export"

install:
	uv sync

install-dev:
	uv sync --dev

init:
	uv run todoist-to-notes init

# Testing targets
test:
	uv run pytest tests/ -v

test-cov:
	uv run pytest tests/ -v --cov=src/todoist_to_notes --cov-report=html --cov-report=term

# Code quality targets
lint:
	uv run flake8 src/ tests/ examples/

format:
	uv run isort src/ tests/ examples/
	uv run black src/ tests/ examples/

format-check:
	uv run isort --check-only src/ tests/ examples/
	uv run black --check src/ tests/ examples/

type-check:
	uv run mypy src/

# Quality check - run all checks
check: format-check lint type-check test
	@echo "✅ All quality checks passed!"

# Build and distribution
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	uv build

# Example and CLI targets
run-example:
	@echo "Running example usage script..."
	@echo "Make sure you have set TODOIST_API_TOKEN in .env file"
	cd examples && uv run python example_usage.py

cli-help:
	uv run todoist-to-notes --help

cli-test:
	uv run todoist-to-notes test

cli-projects:
	uv run todoist-to-notes list-projects

cli-export:
	@echo "Running example export to ./example_output/"
	uv run todoist-to-notes export --output-dir ./example_output --tag-prefix "example"

# Development helpers
dev-server:
	@echo "Starting development environment..."
	@echo "Use 'uv run python' to start Python with the project installed"

install-global:
	uv tool install .

uninstall-global:
	uv tool uninstall todoist-to-notes

# Release helpers (for maintainers)
version-patch:
	@echo "Current version: $(shell grep __version__ src/todoist_to_notes/__about__.py)"
	@echo "Bump patch version and update __about__.py manually"

version-minor:
	@echo "Current version: $(shell grep __version__ src/todoist_to_notes/__about__.py)"
	@echo "Bump minor version and update __about__.py manually"

version-major:
	@echo "Current version: $(shell grep __version__ src/todoist_to_notes/__about__.py)"
	@echo "Bump major version and update __about__.py manually"

# Documentation
docs-serve:
	@echo "README.md contains the main documentation"
	@echo "Examples are in examples/ directory"
	@echo "Usage guide: examples/USAGE_GUIDE.md"

# Docker targets (future enhancement)
docker-build:
	@echo "Docker support not implemented yet"

docker-run:
	@echo "Docker support not implemented yet"
