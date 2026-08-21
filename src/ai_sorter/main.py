"""AI-Sorter application entry point."""

from __future__ import annotations

import sys

from .app import Application
from .core.paths import AppPaths, detect_app_root


def main() -> int:
    """Start AI-Sorter and return the process exit code."""
    paths = AppPaths(detect_app_root())
    application = Application(paths)
    try:
        return application.start()
    except Exception as exc:  # Boundary: convert unexpected startup errors into a useful CLI/GUI-safe exit.
        print(f"AI-Sorter could not start: {exc}", file=sys.stderr)
        return 1
    finally:
        application.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
