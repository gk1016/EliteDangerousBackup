# Elite Dangerous Backup (GUI)

Back up your Elite Dangerous saves and config files with a simple, fast GUI.  
Choose a USB (or any folder), pick **ZIP** or **Mirror** mode, optionally turn on **Incremental**, and press **Start**.  
Includes a built-in **User Guide**, **theme switcher** (Elite/Dark/Light), and robust logging—without freezing your UI.

> ✅ **Officially supported:** Windows 10/11  
> ⚠️ **Linux:** see “Linux notes (experimental)” below

---

## Features

- **One-click backup** of up to **three user-chosen source folders**
- **ZIP archive** mode (single `.zip`) or **Mirror** mode (preserves folder structure)
- **Incremental** (Mirror) — skips unchanged files (size + mtime, ±1s)
- **USB drive picker** (Windows), or **Browse…** any destination folder
- **Live log**, progress bar, and cancelable background worker
- Handles **long paths** on Windows (`\\?\` prefix)
- **Help** menu with editable `help.md` stored next to your config
- **Themes:** Elite (black/amber), Dark, Light — preference saved to config

---

## Default backup sources

By default, the app detects the typical Elite Dangerous folders for the current user:

- `%USERPROFILE%\Saved Games\Frontier Developments\Elite Dangerous`
- `%LOCALAPPDATA%\Frontier Developments`
- `%LOCALAPPDATA%\Frontier_Developments`

You can edit these paths in the GUI and save them to config.

---


### Optional: build a standalone EXE

pip install pyinstaller
pyinstaller --noconfirm --windowed --name "EliteDangerousBackup" elite_backup_gui.py

---

## Quick usage guide

  Launch the app.
  
  Select sources (3 fields) or keep the defaults.
  
  Choose ZIP (single file) or Mirror.
  
  Turn Incremental ON (Mirror) to skip unchanged files.
  
  Pick a destination (USB via dropdown or Browse…).
  
  Click Start Backup.
  
  Use Theme to cycle Elite → Dark → Light (your choice is saved).
  
  Open Help → User Guide anytime for an in-app reference.

---

### License

MIT — free for all Commanders.
Fly safe, back up often, and remember: beer is technically a coolant.

---

## File locations

| Type | Path |
|------|------|
| **Config** | `%LOCALAPPDATA%\EliteBackup\config.json` |
| **User Guide** | `%LOCALAPPDATA%\EliteBackup\help.md` |
| **Backups (ZIP)** | `EliteDangerousBackup_<COMPUTERNAME>_<YYYYmmdd_HHMMSS>.zip` |
| **Backups (Mirror)** | `EliteDangerousBackup_<COMPUTERNAME>_<YYYYmmdd_HHMMSS>\` (includes `backup_log.txt`) |

---

## Windows installation

### Prerequisites
- Windows 10/11
- **Python 3.10+**
- Tkinter (included with standard Python on Windows)

---

### Run from source

```powershell
git clone https://github.com/<your-username>/EliteDangerousBackup.git
cd EliteDangerousBackup
python -m venv .venv
.\.venv\Scripts\activate
python elite_backup_gui.py




