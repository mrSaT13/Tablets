"""App-wide constants and paths.

Fixes one of the old bugs: the database used to live in the current
working directory (``medisafe_mvp.db``), so data was lost/duplicated
depending on where the .exe was started from. Now it lives in a
per-user data directory.
"""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "Tablets"
LEGACY_DB_NAMES = ("medisafe_mvp.db",)
DB_FILE_NAME = "tablets.db"


def get_app_dir() -> Path:
    """Return a writable per-user directory for the app."""
    # Allow override (useful for tests).
    override = os.environ.get("TABLETS_DATA_DIR")
    if override:
        path = Path(override).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path
    # Windows: %APPDATA%/Tablets, POSIX: ~/.local/share/tablets
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
        path = base / APP_NAME
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
        path = base / "tablets"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_db_path() -> Path:
    override = os.environ.get("TABLETS_DB_PATH")
    if override:
        return Path(override).expanduser()
    app_dir = get_app_dir()
    db_path = app_dir / DB_FILE_NAME
    # One-time migration from the legacy name/location.
    if not db_path.exists():
        for legacy in LEGACY_DB_NAMES:
            for candidate in (Path.cwd() / legacy, app_dir / legacy):
                if candidate.exists():
                    try:
                        import shutil

                        shutil.copy2(candidate, db_path)
                    except OSError:
                        pass
                    break
            if db_path.exists():
                break
    return db_path


def get_export_dir() -> Path:
    """Exports (CSV/PDF) go to Documents/Tablets by default."""
    docs = Path.home() / "Documents" / APP_NAME
    try:
        docs.mkdir(parents=True, exist_ok=True)
        return docs
    except OSError:
        fallback = get_app_dir()
        return fallback
