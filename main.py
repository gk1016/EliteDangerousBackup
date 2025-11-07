#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Elite Dangerous Backup (GUI) — v1.5 (Themes!)
- Self-contained (stdlib only), Windows 11 friendly (Tkinter)
- Three themes: Elite (orange/black), Dark, Light — switch anytime (Theme button)
- Theme saved to config.json
- User-configurable 3 source paths (saved to JSON config)
- Destination: auto-detect removable drives or browse to any folder
- Modes:
    * ZIP mode: one .zip archive (DEFLATED)
    * Mirror mode: copy folders (preserve timestamps)
        - Optional Incremental: skip unchanged files (size & mtime ±1s)
- Threaded worker, progress bar, live log, cancel, long-path support, error logging
- Help system:
    * Static help.md stored with config.json (auto-created, editable)
    * Help menu + Help button with lightweight Markdown-ish renderer
    * “Open Config Folder” & “About”

Config directory: %LOCALAPPDATA%\\EliteBackup
Config file:      %LOCALAPPDATA%\\EliteBackup\\config.json
Help file:        %LOCALAPPDATA%\\EliteBackup\\help.md
"""

import os
import sys
import json
import shutil
import threading
import queue
import ctypes
from ctypes import wintypes
from datetime import datetime
import traceback
import zipfile
import re

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont

# ---------------- App constants & paths ----------------
APP_NAME = "EliteBackup"
CONFIG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), APP_NAME)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
HELP_PATH = os.path.join(CONFIG_DIR, "help.md")
VERSION = "1.5"

# ---------------- Default User Guide content ----------------
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
  with `backup_log.txt` (lists COPY/SKIP entries and any errors).

---

## Incremental Behavior (Mirror)
“Unchanged” means **destination file exists** and matches **size** and **modified time** (±1s).  
This is fast and reliable for game saves/configs.

---

## Where Config & Guide Live
- **Config:** `%LOCALAPPDATA%\\EliteBackup\\config.json`
- **Guide:**  `%LOCALAPPDATA%\\EliteBackup\\help.md`  ← *edit me anytime!*

You can open the config folder via **Help → Open Config Folder**.

---

## Restoring (Manual)
- **ZIP:** Extract, then copy desired files back to the original folders.
- **Mirror:** Files are already in a normal tree—copy back as needed.

---

## Troubleshooting
- If a source folder doesn’t exist, it’s **skipped** and noted in the log.
- If your USB doesn’t appear, click **Refresh Drives** or use **Browse…** to pick the destination explicitly.
- Permission errors? Ensure the drive/folder is writable.

---

## Tips
- Keep **Incremental** on for faster regular backups.
- Turn **ZIP** on for a single-file backup you can stash or upload.

Fly safe, CMDR. o7
"""

# ---------------- Helpers: config, help, DPI ----------------
def ensure_config_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)

def ensure_help_file():
    ensure_config_dir()
    if not os.path.exists(HELP_PATH) or os.path.getsize(HELP_PATH) == 0:
        with open(HELP_PATH, "w", encoding="utf-8") as f:
            f.write(HELP_DEFAULT)

def load_config():
    try:
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if isinstance(cfg, dict):
                return cfg
    except Exception:
        pass
    return {}

def save_config(cfg: dict):
    ensure_config_dir()
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    os.replace(tmp, CONFIG_PATH)

def default_sources():
    userprofile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    localapp = os.environ.get("LOCALAPPDATA", os.path.join(userprofile, "AppData", "Local"))
    saved_games = os.path.join(userprofile, "Saved Games")
    return [
        os.path.join(saved_games, "Frontier Developments", "Elite Dangerous"),
        os.path.join(localapp, "Frontier Developments"),
        os.path.join(localapp, "Frontier_Developments"),
    ]

def get_config_with_defaults():
    cfg = load_config()
    if "sources" not in cfg or not isinstance(cfg.get("sources"), list) or len(cfg["sources"]) != 3:
        cfg["sources"] = default_sources()
    if "zip_mode" not in cfg:
        cfg["zip_mode"] = False
    if "incremental" not in cfg:
        cfg["incremental"] = True
    if "theme" not in cfg:
        cfg["theme"] = "elite"  # 'elite' | 'dark' | 'light'
    return cfg

def read_help_text():
    ensure_help_file()
    try:
        with open(HELP_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"(Unable to load help.md: {e})"

def _enable_high_dpi():
    """Best-effort DPI awareness on Windows across versions."""
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.windll.user32
        DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)
        if hasattr(user32, "SetProcessDpiAwarenessContext"):
            if user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2):
                return
    except Exception:
        pass
    try:
        shcore = getattr(ctypes.windll, "shcore", None)
        if shcore and hasattr(shcore, "SetProcessDpiAwareness"):
            shcore.SetProcessDpiAwareness(2)  # per-monitor
            return
    except Exception:
        pass
    try:
        user32 = ctypes.windll.user32
        if hasattr(user32, "SetProcessDPIAware"):
            user32.SetProcessDPIAware()
    except Exception:
        pass

# ---------------- Windows drive enumeration ----------------
DRIVE_REMOVABLE = 2
GetLogicalDrives = ctypes.windll.kernel32.GetLogicalDrives
GetDriveTypeW = ctypes.windll.kernel32.GetDriveTypeW
GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
GetDriveTypeW.restype = wintypes.UINT

def list_drives():
    drives = []
    bitmask = GetLogicalDrives()
    for i in range(26):
        if bitmask & (1 << i):
            letter = f"{chr(ord('A') + i)}:\\"
            dtype = GetDriveTypeW(letter)
            drives.append((letter, dtype))
    return drives

def list_removable_drives():
    return [d for d, t in list_drives() if t == DRIVE_REMOVABLE]

# ---------------- Path & file helpers ----------------
def win_longpath(p: str) -> str:
    if p.startswith("\\\\?\\") or p.startswith("\\\\"):
        return p
    if len(p) >= 240:
        return "\\\\?\\" + os.path.abspath(p)
    return p

def iter_files_under(root_dir):
    for base, dirs, files in os.walk(root_dir):
        for f in files:
            src = os.path.join(base, f)
            rel = os.path.relpath(src, root_dir)
            yield src, rel

def count_total_files(existing_sources):
    total = 0
    for s in existing_sources:
        for _ in iter_files_under(s):
            total += 1
    return total

def safe_makedirs(path):
    os.makedirs(path, exist_ok=True)

def is_unchanged(src_file, dst_file, mtime_slop=1.0):
    try:
        if not os.path.exists(dst_file):
            return False
        s_stat = os.stat(src_file)
        d_stat = os.stat(dst_file)
        if s_stat.st_size != d_stat.st_size:
            return False
        return abs(s_stat.st_mtime - d_stat.st_mtime) <= mtime_slop
    except Exception:
        return False

# ---------------- Markdown-ish renderer (help view) ----------------
def render_markdown(text_widget: tk.Text, md: str):
    text_widget.config(state="normal")
    text_widget.delete("1.0", "end")

    base = tkfont.nametofont("TkDefaultFont")
    h1 = tkfont.Font(family=base.cget("family"), size=base.cget("size")+6, weight="bold")
    h2 = tkfont.Font(family=base.cget("family"), size=base.cget("size")+3, weight="bold")
    codef = tkfont.Font(family="Consolas", size=base.cget("size"))

    text_widget.tag_configure("h1", font=h1, spacing1=8, spacing3=6)
    text_widget.tag_configure("h2", font=h2, spacing1=6, spacing3=4)
    text_widget.tag_configure("p", spacing1=2, spacing3=6)
    text_widget.tag_configure("li", lmargin1=24, lmargin2=24, spacing3=2)
    text_widget.tag_configure("code", font=codef)
    text_widget.tag_configure("codeblock", font=codef, background="#f5f5f5",
                               lmargin1=12, lmargin2=12, spacing1=4, spacing3=6)
    text_widget.tag_configure("hr", spacing1=8, spacing3=8)

    lines = md.splitlines()
    i = 0
    in_code = False
    code_buf = []
    inline_code_re = re.compile(r"`([^`]+)`")

    def flush_codeblock():
        if code_buf:
            text_widget.insert("end", "\n".join(code_buf) + "\n", ("codeblock",))
            code_buf.clear()

    while i < len(lines):
        line = lines[i]

        if line.strip().startswith("```"):
            if in_code:
                in_code = False
                flush_codeblock()
            else:
                in_code = True
            i += 1
            continue

        if in_code:
            code_buf.append(line)
            i += 1
            continue

        if line.strip() == "---":
            text_widget.insert("end", "────────────────────────────────\n", ("hr",))
            i += 1
            continue

        if line.startswith("# "):
            text_widget.insert("end", line[2:].strip() + "\n", ("h1",))
            i += 1
            continue
        if line.startswith("## "):
            text_widget.insert("end", line[3:].strip() + "\n", ("h2",))
            i += 1
            continue

        stripped = line.lstrip()
        if stripped.startswith("- ") or stripped.startswith("* "):
            content = stripped[2:]
            pos = 0
            while True:
                m = inline_code_re.search(content, pos)
                if not m:
                    text_widget.insert("end", "• " + content[pos:] + "\n", ("li",))
                    break
                if m.start() > pos:
                    text_widget.insert("end", "• " + content[pos:m.start()], ("li",))
                text_widget.insert("end", m.group(1), ("li", "code"))
                pos = m.end()
                if pos >= len(content):
                    text_widget.insert("end", "\n", ("li",))
                    break
            i += 1
            continue

        if stripped.startswith("> "):
            text_widget.insert("end", stripped + "\n", ("p",))
            i += 1
            continue

        if not line.strip():
            text_widget.insert("end", "\n", ("p",))
            i += 1
            continue

        content = line
        last = 0
        while True:
            m = inline_code_re.search(content, last)
            if not m:
                text_widget.insert("end", content[last:] + "\n", ("p",))
                break
            if m.start() > last:
                text_widget.insert("end", content[last:m.start()], ("p",))
            text_widget.insert("end", m.group(1), ("p", "code"))
            last = m.end()
        i += 1

    text_widget.config(state="disabled")

# ---------------- THEME ENGINE ----------------
THEMES = {
    "elite": {
        "bg": "#0b0b0b", "fg": "#ff9d00", "muted": "#c07a00",
        "widget_bg": "#111111", "entry_bg": "#151515", "entry_fg": "#f0f0f0",
        "button_bg": "#1a1a1a", "button_fg": "#ffd27a",
        "accent": "#ff9d00", "accent_fg": "#111111",
        "progress_trough": "#1a1a1a", "progress_bar": "#ff9d00",
        "text_bg": "#0e0e0e", "text_fg": "#f5f5f5",
        "border": "#333333", "select_bg": "#222222", "select_fg": "#ffffff",
        "menu_bg": "#111111", "menu_fg": "#ff9d00"
    },
    "dark": {
        "bg": "#1e1e1e", "fg": "#eaeaea", "muted": "#bdbdbd",
        "widget_bg": "#252526", "entry_bg": "#2d2d30", "entry_fg": "#f0f0f0",
        "button_bg": "#2d2d30", "button_fg": "#ffffff",
        "accent": "#6aa0ff", "accent_fg": "#0d1117",
        "progress_trough": "#2b2b2b", "progress_bar": "#6aa0ff",
        "text_bg": "#1f1f1f", "text_fg": "#f0f0f0",
        "border": "#3a3a3a", "select_bg": "#3a3f44", "select_fg": "#ffffff",
        "menu_bg": "#252526", "menu_fg": "#eaeaea"
    },
    "light": {
        "bg": "#fafafa", "fg": "#111111", "muted": "#444444",
        "widget_bg": "#ffffff", "entry_bg": "#ffffff", "entry_fg": "#000000",
        "button_bg": "#f1f1f1", "button_fg": "#111111",
        "accent": "#0d6efd", "accent_fg": "#ffffff",
        "progress_trough": "#e9ecef", "progress_bar": "#0d6efd",
        "text_bg": "#ffffff", "text_fg": "#000000",
        "border": "#dddddd", "select_bg": "#cce5ff", "select_fg": "#000000",
        "menu_bg": "#ffffff", "menu_fg": "#111111"
    },
}
THEME_ORDER = ["elite", "dark", "light"]

def apply_theme(root: tk.Tk, style: ttk.Style, theme_key: str):
    theme = THEMES.get(theme_key, THEMES["elite"])
    bg = theme["bg"]; fg = theme["fg"]; accent = theme["accent"]
    wbg = theme["widget_bg"]; ebg = theme["entry_bg"]; efg = theme["entry_fg"]
    bbg = theme["button_bg"]; bfg = theme["button_fg"]
    tbg = theme["text_bg"]; tfg = theme["text_fg"]
    trough = theme["progress_trough"]; pbar = theme["progress_bar"]
    select_bg = theme["select_bg"]; select_fg = theme["select_fg"]
    menu_bg = theme["menu_bg"]; menu_fg = theme["menu_fg"]

    # Root background
    root.configure(bg=bg)

    # Use ttk 'clam' theme as base for consistent colorability
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # Global defaults
    style.configure(".", background=wbg, foreground=fg)
    style.configure("TFrame", background=wbg)
    style.configure("TLabelframe", background=wbg, foreground=fg)
    style.configure("TLabelframe.Label", background=wbg, foreground=fg)
    style.configure("TLabel", background=wbg, foreground=fg)
    style.configure("TButton", background=bbg, foreground=bfg, bordercolor=theme["border"])
    style.map("TButton", background=[("active", accent)], foreground=[("active", theme["accent_fg"])])
    style.configure("TCheckbutton", background=wbg, foreground=fg)
    style.configure("TMenubutton", background=bbg, foreground=bfg)
    style.configure("TCombobox", fieldbackground=ebg, foreground=efg, background=wbg, arrowcolor=fg)
    style.map("TCombobox", fieldbackground=[("readonly", ebg)], foreground=[("readonly", efg)], background=[("readonly", wbg)])
    style.configure("TProgressbar", troughcolor=trough, background=pbar, bordercolor=trough, lightcolor=pbar, darkcolor=pbar)

    # Menu colors (tk-only)
    root.option_add("*Menu.background", menu_bg)
    root.option_add("*Menu.foreground", menu_fg)
    root.option_add("*Menu.activeBackground", accent)
    root.option_add("*Menu.activeForeground", theme["accent_fg"])

    # For classic tk widgets we create helpers:
    def style_text_widget(widget: tk.Text):
        widget.configure(bg=tbg, fg=tfg, insertbackground=fg, selectbackground=select_bg, selectforeground=select_fg, highlightthickness=0)

    def style_entry_widget(widget: tk.Entry):
        widget.configure(bg=ebg, fg=efg, insertbackground=efg, highlightthickness=1, highlightbackground=theme["border"], highlightcolor=accent, selectbackground=select_bg, selectforeground=select_fg)

    # store for reuse
    root._theme_helpers = {"style_text": style_text_widget, "style_entry": style_entry_widget}

def restyle_children(root: tk.Misc):
    """Apply theme to dynamic widgets like Text/Entry created after theme switch."""
    helpers = getattr(root, "_theme_helpers", {})
    style_text = helpers.get("style_text")
    style_entry = helpers.get("style_entry")
    for w in root.winfo_children():
        # Recurse
        restyle_children(w)
        # Per-type tweaks
        if isinstance(w, tk.Text) and style_text:
            style_text(w)
        if isinstance(w, tk.Entry) and style_entry:
            style_entry(w)

def apply_theme_to_toplevel(win: tk.Toplevel):
    """Apply theme to help window after creation."""
    root = win.master
    style_text = getattr(root, "_theme_helpers", {}).get("style_text")
    for w in win.winfo_children():
        if isinstance(w, tk.Text) and style_text:
            style_text(w)
        # Recurse for frames
        for c in w.winfo_children():
            if isinstance(c, tk.Text) and style_text:
                style_text(c)

# ---------------- Backup worker ----------------
class BackupWorker(threading.Thread):
    def __init__(self, sources, dest_root, ui_queue, zip_mode=False, incremental=True):
        super().__init__(daemon=True)
        self.sources = sources
        self.dest_root = dest_root
        self.ui_queue = ui_queue
        self.zip_mode = zip_mode
        self.incremental = incremental if not zip_mode else False
        self.stop_flag = False
        self.errors = []

    def log(self, msg):
        self.ui_queue.put(("log", msg))

    def set_progress(self, done, total):
        self.ui_queue.put(("progress", (done, total)))

    def _mk_backup_target(self):
        computer = os.environ.get("COMPUTERNAME", "UNKNOWNPC")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.zip_mode:
            return os.path.join(self.dest_root, f"EliteDangerousBackup_{computer}_{ts}.zip")
        else:
            dst = os.path.join(self.dest_root, f"EliteDangerousBackup_{computer}_{ts}")
            safe_makedirs(dst)
            return dst

    def run(self):
        try:
            existing = [s for s in self.sources if s and os.path.isdir(s)]
            missing = [s for s in self.sources if not s or not os.path.isdir(s)]
            for m in missing:
                self.log(f"[WARN] Source not found or unset (skipping): {m}")

            total_files = count_total_files(existing)
            self.set_progress(0, max(total_files, 1))
            target = self._mk_backup_target()

            if self.zip_mode:
                self._run_zip(existing, target, total_files)
            else:
                self._run_mirror(existing, target, total_files)

            if self.errors:
                self.log(f"Completed with {len(self.errors)} error(s). See log for details.")
            else:
                self.log("Backup completed successfully. No errors reported.")
            self.ui_queue.put(("done", target))
        except KeyboardInterrupt:
            self.log("Backup cancelled by user.")
            self.ui_queue.put(("cancelled", None))
        except Exception as e:
            tb = traceback.format_exc()
            self.log(f"Fatal error: {e}\n{tb}")
            self.ui_queue.put(("failed", str(e)))

    # ---- ZIP mode ----
    def _run_zip(self, existing_sources, archive_path, total_files):
        self.log(f"ZIP mode: {archive_path}")
        log_lines = []
        count = 0
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for src_root in existing_sources:
                parent = os.path.basename(os.path.dirname(src_root))
                leaf = os.path.basename(src_root)
                tagged_base = f"{parent}__{leaf}" if parent else leaf
                self.log(f"Zipping: {src_root} -> /{tagged_base}/")
                for src_file, rel_path in iter_files_under(src_root):
                    if self.stop_flag:
                        raise KeyboardInterrupt
                    arcname = os.path.join(tagged_base, rel_path).replace("\\", "/")
                    try:
                        zf.write(win_longpath(src_file), arcname)
                        log_lines.append(f"ZIP: {src_file} -> {arcname}")
                    except Exception as e:
                        err = f"[ERROR] ZIP {src_file} -> {arcname}: {e}"
                        self.errors.append(err)
                        log_lines.append(err)
                        self.log(err)
                    count += 1
                    if count % 5 == 0 or count == total_files:
                        self.set_progress(count, max(total_files, 1))
            zf.writestr("backup_log.txt", "\n".join(log_lines))

    # ---- Mirror mode (with optional incremental) ----
    def _run_mirror(self, existing_sources, backup_dir, total_files):
        self.log(f"Mirror mode: {backup_dir}")
        log_path = os.path.join(backup_dir, "backup_log.txt")
        done = 0
        with open(log_path, "w", encoding="utf-8") as lf:
            lf.write(f"Elite Dangerous Backup Log (Mirror) - {datetime.now().isoformat()}\n")
            lf.write(f"Destination: {backup_dir}\n")
            lf.write(f"Incremental: {'ON' if self.incremental else 'OFF'}\n\n")
            for src_root in existing_sources:
                parent = os.path.basename(os.path.dirname(src_root))
                leaf = os.path.basename(src_root)
                tagged_base = f"{parent}__{leaf}" if parent else leaf
                dest_base = os.path.join(backup_dir, tagged_base)
                self.log(f"Copying: {src_root} -> {dest_base}")
                safe_makedirs(dest_base)
                for src_file, rel_path in iter_files_under(src_root):
                    if self.stop_flag:
                        raise KeyboardInterrupt
                    dest_file = os.path.join(dest_base, rel_path)
                    dest_dir = os.path.dirname(dest_file)
                    try:
                        if self.incremental and os.path.exists(dest_file) and is_unchanged(src_file, dest_file):
                            lf.write(f"SKIP: {src_file}\n")
                        else:
                            safe_makedirs(dest_dir)
                            shutil.copy2(win_longpath(src_file), win_longpath(dest_file))
                            lf.write(f"COPY: {src_file} -> {dest_file}\n")
                    except Exception as e:
                        err = f"[ERROR] {src_file} -> {dest_file}: {e}"
                        self.errors.append(err)
                        lf.write(err + "\n")
                        self.log(err)
                    done += 1
                    if done % 5 == 0 or done == total_files:
                        self.set_progress(done, max(total_files, 1))

# ---------------- GUI ----------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Elite Dangerous Backup v{VERSION}")
        self.geometry("880x780")
        self.minsize(860, 760)

        ensure_config_dir()
        ensure_help_file()

        self.ui_queue = queue.Queue()
        self.worker = None

        cfg = get_config_with_defaults()
        self.source_vars = [tk.StringVar(value=cfg["sources"][0]),
                            tk.StringVar(value=cfg["sources"][1]),
                            tk.StringVar(value=cfg["sources"][2])]
        self.zip_var = tk.BooleanVar(value=cfg.get("zip_mode", False))
        self.incr_var = tk.BooleanVar(value=cfg.get("incremental", True))
        self.theme_var = tk.StringVar(value=cfg.get("theme", "elite"))
        self.dest_dir_var = tk.StringVar()
        self.drive_var = tk.StringVar()

        # Theme/style
        self.style = ttk.Style()
        apply_theme(self, self.style, self.theme_var.get())

        self._build_menu()
        self._create_widgets()
        self._apply_mode_rules()
        self.after(100, self._poll_queue)

    # ----- Menubar -----
    def _build_menu(self):
        m = tk.Menu(self)
        self.config(menu=m)
        help_menu = tk.Menu(m, tearoff=0)
        help_menu.add_command(label="User Guide", command=self._show_help)
        help_menu.add_command(label="Open Config Folder", command=self._open_config_folder)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._show_about)
        m.add_cascade(label="Help", menu=help_menu)

    # ----- UI -----
    def _create_widgets(self):
        padding = {"padx": 10, "pady": 6}
        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True)

        title_row = ttk.Frame(frm)
        title_row.grid(row=0, column=0, columnspan=5, sticky="ew")
        ttk.Label(title_row, text="Elite Dangerous Backup", font=("Segoe UI", 14, "bold")).pack(side="left", padx=10, pady=8)
        ttk.Button(title_row, text="Theme", command=self._cycle_theme).pack(side="right", padx=(6,10), pady=8)
        ttk.Button(title_row, text="Help", command=self._show_help).pack(side="right", padx=10, pady=8)

        ttk.Label(frm, text="Select the three source folders to back up:").grid(row=1, column=0, columnspan=5, sticky="w", **padding)
        self._add_source_row(frm, row=2, label="Source 1:", var=self.source_vars[0])
        self._add_source_row(frm, row=3, label="Source 2:", var=self.source_vars[1])
        self._add_source_row(frm, row=4, label="Source 3:", var=self.source_vars[2])

        btn_bar = ttk.Frame(frm)
        btn_bar.grid(row=5, column=0, columnspan=5, sticky="w", padx=10, pady=(0,10))
        ttk.Button(btn_bar, text="Save Paths", command=self._save_paths).grid(row=0, column=0, padx=(0,6))
        ttk.Button(btn_bar, text="Reset to Defaults", command=self._reset_defaults).grid(row=0, column=1, padx=6)

        ttk.Separator(frm, orient="horizontal").grid(row=6, column=0, columnspan=5, sticky="ew", **padding)

        mode_frame = ttk.LabelFrame(frm, text="Backup Options")
        mode_frame.grid(row=7, column=0, columnspan=5, sticky="ew", padx=10, pady=(0,10))
        self.chk_zip = ttk.Checkbutton(mode_frame, text="Create ZIP archive (single .zip file)", variable=self.zip_var, command=self._on_zip_toggle)
        self.chk_zip.grid(row=0, column=0, sticky="w", padx=10, pady=6)
        self.chk_incr = ttk.Checkbutton(mode_frame, text="Incremental copy (skip unchanged files)", variable=self.incr_var, command=self._on_incr_toggle)
        self.chk_incr.grid(row=1, column=0, sticky="w", padx=10, pady=6)

        ttk.Separator(frm, orient="horizontal").grid(row=8, column=0, columnspan=5, sticky="ew", **padding)

        ttk.Label(frm, text="Destination (USB) drive:").grid(row=9, column=0, sticky="w", **padding)
        self.drive_combo = ttk.Combobox(frm, textvariable=self.drive_var, state="readonly", width=18)
        self.drive_combo.grid(row=9, column=1, sticky="w")
        ttk.Button(frm, text="Refresh Drives", command=self._refresh_drives).grid(row=9, column=2, sticky="w", padx=6)
        ttk.Button(frm, text="Browse…", command=self._browse_dest).grid(row=9, column=3, sticky="e", padx=10)

        self._refresh_drives()

        ttk.Separator(frm, orient="horizontal").grid(row=10, column=0, columnspan=5, sticky="ew", **padding)

        self.progress = ttk.Progressbar(frm, orient="horizontal", mode="determinate")
        self.progress.grid(row=11, column=0, columnspan=5, sticky="ew", padx=10)

        ttk.Label(frm, text="Log:").grid(row=12, column=0, sticky="w", **padding)
        self.log_text = tk.Text(frm, height=16, wrap="word")
        self.log_text.grid(row=13, column=0, columnspan=5, sticky="nsew", padx=10, pady=(0,10))

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=14, column=0, columnspan=5, sticky="e", padx=10, pady=(0,10))
        self.btn_start = ttk.Button(btn_frame, text="Start Backup", command=self._start_backup)
        self.btn_start.grid(row=0, column=0, padx=5)
        self.btn_cancel = ttk.Button(btn_frame, text="Cancel", command=self._cancel_backup, state="disabled")
        self.btn_cancel.grid(row=0, column=1, padx=5)

        frm.grid_rowconfigure(13, weight=1)
        frm.grid_columnconfigure(2, weight=1)
        frm.grid_columnconfigure(3, weight=1)
        frm.grid_columnconfigure(4, weight=1)

        # Finish initial theming on widgets that Tk won't auto-style
        restyle_children(self)

    def _add_source_row(self, parent, row, label, var):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=10, pady=4)
        entry = ttk.Entry(parent, textvariable=var)
        entry.grid(row=row, column=1, columnspan=3, sticky="ew", padx=(0,6))
        ttk.Button(parent, text="Browse…", command=lambda v=var: self._browse_source(v)).grid(row=row, column=4, sticky="e", padx=10)

    # ----- Theme logic -----
    def _cycle_theme(self):
        current = self.theme_var.get()
        idx = THEME_ORDER.index(current) if current in THEME_ORDER else 0
        new_theme = THEME_ORDER[(idx + 1) % len(THEME_ORDER)]
        self.theme_var.set(new_theme)
        # Persist
        cfg = get_config_with_defaults()
        cfg["theme"] = new_theme
        cfg["sources"] = [v.get().strip() for v in self.source_vars]
        cfg["zip_mode"] = bool(self.zip_var.get())
        cfg["incremental"] = bool(self.incr_var.get())
        save_config(cfg)
        # Apply
        apply_theme(self, self.style, new_theme)
        restyle_children(self)
        self._log(f"Theme set to: {new_theme.capitalize()}")

    # ----- Mode logic -----
    def _apply_mode_rules(self):
        if self.zip_var.get():
            self.chk_incr.state(["disabled"])
        else:
            self.chk_incr.state(["!disabled"])

    def _on_zip_toggle(self):
        self._apply_mode_rules()
        self._save_paths()

    def _on_incr_toggle(self):
        self._save_paths()

    # ----- Source handling -----
    def _browse_source(self, var):
        d = filedialog.askdirectory(title="Choose source folder")
        if d:
            var.set(d)
            self._save_paths()

    def _save_paths(self):
        cfg = get_config_with_defaults()
        cfg["sources"] = [v.get().strip() for v in self.source_vars]
        cfg["zip_mode"] = bool(self.zip_var.get())
        cfg["incremental"] = bool(self.incr_var.get())
        cfg["theme"] = self.theme_var.get()
        save_config(cfg)
        self._log("Configuration saved.")

    def _reset_defaults(self):
        defs = default_sources()
        for i in range(3):
            self.source_vars[i].set(defs[i] if i < len(defs) else "")
        self._save_paths()
        self._log("Reset to detected defaults and saved.")

    # ----- Destination handling -----
    def _refresh_drives(self):
        drives = list_removable_drives()
        if not drives:
            self.drive_combo["values"] = []
            self.drive_var.set("")
        else:
            self.drive_combo["values"] = drives
            if not self.drive_var.get() and drives:
                self.drive_var.set(drives[0])

    def _browse_dest(self):
        d = filedialog.askdirectory(title="Choose destination folder (USB or other)")
        if d:
            self.drive_var.set("")
            self.dest_dir_var.set(d)
            self._log(f"Destination folder selected: {d}")

    def _get_destination_root(self):
        if self.dest_dir_var.get():
            return self.dest_dir_var.get()
        drive = self.drive_var.get()
        if drive and os.path.isdir(drive):
            return drive
        return None

    # ----- Backup flow -----
    def _start_backup(self):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Busy", "A backup is already running.")
            return

        self._save_paths()

        dest_root = self._get_destination_root()
        if not dest_root:
            messagebox.showerror("No destination", "Select a USB drive or choose a destination folder with Browse…")
            return
        if not os.access(dest_root, os.W_OK):
            messagebox.showerror("Permission", f"Cannot write to destination: {dest_root}")
            return

        sources = [v.get().strip() for v in self.source_vars]
        if not any(sources):
            messagebox.showerror("No sources", "Please provide at least one source folder.")
            return

        self.log_text.delete("1.0", "end")
        self.progress["value"] = 0
        self.progress["maximum"] = 100
        self.btn_start.configure(state="disabled")
        self.btn_cancel.configure(state="normal")

        zip_mode = bool(self.zip_var.get())
        incremental = bool(self.incr_var.get())

        self.worker = BackupWorker(sources, dest_root, self.ui_queue, zip_mode=zip_mode, incremental=incremental)
        self.worker.start()
        mode_str = "ZIP archive" if zip_mode else ("Incremental mirror" if incremental else "Full mirror")
        self._log(f"Starting backup to: {dest_root}  |  Mode: {mode_str}")

    def _cancel_backup(self):
        if self.worker and self.worker.is_alive():
            self.worker.stop_flag = True
            self._log("Cancel requested; stopping soon…")

    # ----- Help / About / Config folder -----
    def _show_help(self):
        text = read_help_text()
        win = tk.Toplevel(self)
        win.title("User Guide — Elite Dangerous Backup")
        win.geometry("820x700")
        win.minsize(640, 480)

        topbar = ttk.Frame(win)
        topbar.pack(fill="x")
        ttk.Button(topbar, text="Edit help.md", command=self._edit_help_file).pack(side="left", padx=8, pady=6)
        ttk.Button(topbar, text="Open Config Folder", command=self._open_config_folder).pack(side="left", padx=6, pady=6)
        ttk.Label(topbar, text=HELP_PATH).pack(side="right", padx=8)

        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True, padx=8, pady=8)

        txt = tk.Text(frame, wrap="word", borderwidth=0, highlightthickness=0)
        txt.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(frame, orient="vertical", command=txt.yview)
        sb.pack(side="right", fill="y")
        txt.configure(yscrollcommand=sb.set)

        render_markdown(txt, text)
        apply_theme_to_toplevel(win)  # style help window with current theme

    def _edit_help_file(self):
        ensure_help_file()
        try:
            os.startfile(HELP_PATH)  # Windows: open in default editor (Notepad)
        except Exception as e:
            messagebox.showerror("Open Failed", f"Could not open help file:\n{e}")

    def _open_config_folder(self):
        ensure_config_dir()
        try:
            os.startfile(CONFIG_DIR)  # Windows Explorer
        except Exception as e:
            messagebox.showerror("Open Failed", f"Could not open folder:\n{e}")

    def _show_about(self):
        messagebox.showinfo(
            "About",
            f"Elite Dangerous Backup v{VERSION}\n\n"
            "Back up your ED saves/configs to a ZIP or mirror folder.\n"
            "Switchable themes: Elite, Dark, Light (saved to config).\n"
            "Help lives next to config.json and is user-editable.\n\n"
            "Crafted by your favorite beer-can AI. 🍺"
        )

    # ----- UI plumbing -----
    def _poll_queue(self):
        try:
            while True:
                msg_type, payload = self.ui_queue.get_nowait()
                if msg_type == "log":
                    self._log(payload)
                elif msg_type == "progress":
                    done, total = payload
                    pct = 0 if total == 0 else int(done * 100 / total)
                    self.progress["value"] = pct
                elif msg_type == "done":
                    self.btn_start.configure(state="normal")
                    self.btn_cancel.configure(state="disabled")
                    out = payload
                    self._log(f"Finished. Output:\n{out}")
                    messagebox.showinfo("Backup Complete", f"Backup finished.\n\nOutput:\n{out}")
                elif msg_type == "failed":
                    self.btn_start.configure(state="normal")
                    self.btn_cancel.configure(state="disabled")
                    err = payload
                    messagebox.showerror("Backup Failed", f"An error occurred:\n\n{err}")
                elif msg_type == "cancelled":
                    self.btn_start.configure(state="normal")
                    self.btn_cancel.configure(state="disabled")
                    self._log("Cancelled.")
                    messagebox.showinfo("Cancelled", "Backup cancelled.")
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _log(self, text):
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")

# ---------------- main ----------------
if __name__ == "__main__":
    _enable_high_dpi()
    app = App()
    app.mainloop()
