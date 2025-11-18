import os

APP_NAME = "EliteBackup"
VERSION = "1.6.0"  # modular refactor

CONFIG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), APP_NAME)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
HELP_PATH = os.path.join(CONFIG_DIR, "help.md")

HELP_DEFAULT = """# Elite Dangerous Backup — User Guide

> **Purpose:** Safely back up your Elite Dangerous saves and configs to a USB drive (or any folder) as either a **ZIP archive** or a **mirror** (optionally **incremental**).

---

## Quick Start
- **Pick Sources:** Choose up to three folders (Browse… or paste).
- **Choose Mode:**
  - **ZIP Archive** → one `.zip` with everything.
  - **Mirror** → normal folders.
    - **Incremental** → skips files that haven’t changed (size + modified time).
- **Select Destination:** Choose your USB drive from the list or **Browse…** to any folder.
- **Start Backup:** Click **Start Backup** and watch the progress & log.

---

## Typical Source Folders (per user)
- `%USERPROFILE%\\Saved Games\\Frontier Developments\\Elite Dangerous`
- `%LOCALAPPDATA%\\Frontier Developments`
- `%LOCALAPPDATA%\\Frontier_Developments`

> These are auto-detected on first run. You can change them anytime.

---

## What Gets Created
- **ZIP mode:**  
  `EliteDangerousBackup_<COMPUTERNAME>_<YYYYmmdd_HHMMSS>.zip`
- **Mirror mode:**  
  `EliteDangerousBackup_<COMPUTERNAME>_<YYYYmmdd_HHMMSS>\\`  
  with `backup_log.txt`.

---

## Incremental (Mirror)
Matches by **size** and **modified time** (±1s).

---

## Where Config & Guide Live
- **Config:** `%LOCALAPPDATA%\\EliteBackup\\config.json`
- **Guide:**  `%LOCALAPPDATA%\\EliteBackup\\help.md`

---

Fly safe, CMDR. o7
"""
