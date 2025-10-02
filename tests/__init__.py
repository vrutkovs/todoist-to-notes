"""Tests for todoist-to-notes package."""

import sys
from pathlib import Path

# Add the src directory to the Python path for testing
test_dir = Path(__file__).parent
project_root = test_dir.parent
src_dir = project_root / "src"

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
