import queue
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from constants import VERSION, HELP_PATH
from config import (
    ensure_config_dir, ensure_help_file, get_config_with_defaults,
    save_config, read_help_text, default_sources
)
from theme import apply_theme, apply_theme_to_toplevel, THEME_ORDER, restyle_everything
from windows import list_removable_drives, win_longpath
from markdown import render_markdown
from backup import BackupWorker

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

        self.style = ttk.Style()
        apply_theme(self, self.style, self.theme_var.get())

        self._build_menu()
        self._create_widgets()
        self._apply_mode_rules()
        self.after(100, self._poll_queue)

    # Menubar
    def _build_menu(self):
        m = tk.Menu(self); self.config(menu=m)
        help_menu = tk.Menu(m, tearoff=0)
        help_menu.add_command(label="User Guide", command=self._show_help)
        help_menu.add_command(label="Open Config Folder", command=self._open_config_folder)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._show_about)
        m.add_cascade(label="Help", menu=help_menu)

    # UI
    def _create_widgets(self):
        padding = {"padx": 10, "pady": 6}
        frm = ttk.Frame(self); frm.pack(fill="both", expand=True)

        title_row = ttk.Frame(frm); title_row.grid(row=0, column=0, columnspan=5, sticky="ew")
        ttk.Label(title_row, text="Elite Dangerous Backup", font=("Segoe UI", 14, "bold")).pack(side="left", padx=10, pady=8)
        ttk.Button(title_row, text="Theme", command=self._cycle_theme).pack(side="right", padx=(6,10), pady=8)
        ttk.Button(title_row, text="Help", command=self._show_help).pack(side="right", padx=10, pady=8)

        ttk.Label(frm, text="Select the three source folders to back up:").grid(row=1, column=0, columnspan=5, sticky="w", **padding)
        self._add_source_row(frm, row=2, label="Source 1:", var=self.source_vars[0])
        self._add_source_row(frm, row=3, label="Source 2:", var=self.source_vars[1])
        self._add_source_row(frm, row=4, label="Source 3:", var=self.source_vars[2])

        btn_bar = ttk.Frame(frm); btn_bar.grid(row=5, column=0, columnspan=5, sticky="w", padx=10, pady=(0,10))
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

        btn_frame = ttk.Frame(frm); btn_frame.grid(row=14, column=0, columnspan=5, sticky="e", padx=10, pady=(0,10))
        self.btn_start = ttk.Button(btn_frame, text="Start Backup", command=self._start_backup)
        self.btn_start.grid(row=0, column=0, padx=5)
        self.btn_cancel = ttk.Button(btn_frame, text="Cancel", command=self._cancel_backup, state="disabled")
        self.btn_cancel.grid(row=0, column=1, padx=5)

        frm.grid_rowconfigure(13, weight=1)
        frm.grid_columnconfigure(2, weight=1); frm.grid_columnconfigure(3, weight=1); frm.grid_columnconfigure(4, weight=1)

        restyle_everything(self)

    def _add_source_row(self, parent, row, label, var):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=10, pady=4)
        entry = ttk.Entry(parent, textvariable=var)
        entry.grid(row=row, column=1, columnspan=3, sticky="ew", padx=(0,6))
        ttk.Button(parent, text="Browse…", command=lambda v=var: self._browse_source(v)).grid(row=row, column=4, sticky="e", padx=10)

    # Theme
    def _cycle_theme(self):
        from theme import THEME_ORDER, apply_theme, restyle_everything
        current = self.theme_var.get()
        idx = THEME_ORDER.index(current) if current in THEME_ORDER else 0
        new_theme = THEME_ORDER[(idx + 1) % len(THEME_ORDER)]
        self.theme_var.set(new_theme)
        cfg = get_config_with_defaults()
        cfg["theme"] = new_theme
        cfg["sources"] = [v.get().strip() for v in self.source_vars]
        cfg["zip_mode"] = bool(self.zip_var.get())
        cfg["incremental"] = bool(self.incr_var.get())
        save_config(cfg)
        apply_theme(self, self.style, new_theme)
        restyle_everything(self)
        self._log(f"Theme set to: {new_theme.capitalize()}")

    # Mode
    def _apply_mode_rules(self):
        if self.zip_var.get():
            self.chk_incr.state(["disabled"])
        else:
            self.chk_incr.state(["!disabled"])

    def _on_zip_toggle(self):
        self._apply_mode_rules(); self._save_paths()

    def _on_incr_toggle(self):
        self._save_paths()

    # Sources
    def _browse_source(self, var):
        d = filedialog.askdirectory(title="Choose source folder")
        if d:
            var.set(d); self._save_paths()

    def _save_paths(self):
        cfg = get_config_with_defaults()
        cfg["sources"] = [v.get().strip() for v in self.source_vars]
        cfg["zip_mode"] = bool(self.zip_var.get())
        cfg["incremental"] = bool(self.incr_var.get())
        cfg["theme"] = self.theme_var.get()
        save_config(cfg); self._log("Configuration saved.")

    def _reset_defaults(self):
        defs = default_sources()
        for i in range(3):
            self.source_vars[i].set(defs[i] if i < len(defs) else "")
        self._save_paths(); self._log("Reset to detected defaults and saved.")

    # Destination
    def _refresh_drives(self):
        drives = list_removable_drives()
        if not drives:
            self.drive_combo["values"] = []; self.drive_var.set("")
        else:
            self.drive_combo["values"] = drives
            if not self.drive_var.get() and drives: self.drive_var.set(drives[0])

    def _browse_dest(self):
        d = filedialog.askdirectory(title="Choose destination folder (USB or other)")
        if d:
            self.drive_var.set(""); self.dest_dir_var.set(d); self._log(f"Destination folder selected: {d}")

    def _get_destination_root(self):
        if self.dest_dir_var.get(): return self.dest_dir_var.get()
        drive = self.drive_var.get()
        if drive and os.path.isdir(drive): return drive
        return None

    # Backup flow
    def _start_backup(self):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Busy", "A backup is already running."); return

        self._save_paths()
        dest_root = self._get_destination_root()
        if not dest_root:
            messagebox.showerror("No destination", "Select a USB drive or choose a destination folder with Browse…"); return
        if not os.access(dest_root, os.W_OK):
            messagebox.showerror("Permission", f"Cannot write to destination: {dest_root}"); return

        sources = [v.get().strip() for v in self.source_vars]
        if not any(sources):
            messagebox.showerror("No sources", "Please provide at least one source folder."); return

        self.log_text.delete("1.0", "end")
        self.progress["value"] = 0; self.progress["maximum"] = 100
        self.btn_start.configure(state="disabled"); self.btn_cancel.configure(state="normal")

        zip_mode = bool(self.zip_var.get()); incremental = bool(self.incr_var.get())
        self.worker = BackupWorker(sources, dest_root, self.ui_queue, zip_mode=zip_mode, incremental=incremental)
        self.worker.start()
        mode_str = "ZIP archive" if zip_mode else ("Incremental mirror" if incremental else "Full mirror")
        self._log(f"Starting backup to: {dest_root}  |  Mode: {mode_str}")

    def _cancel_backup(self):
        if self.worker and self.worker.is_alive():
            self.worker.stop_flag = True; self._log("Cancel requested; stopping soon…")

    # Help/About
    def _show_help(self):
        text = read_help_text()
        win = tk.Toplevel(self)
        win.title("User Guide — Elite Dangerous Backup"); win.geometry("820x700"); win.minsize(640, 480)

        topbar = ttk.Frame(win); topbar.pack(fill="x")
        ttk.Button(topbar, text="Edit help.md", command=self._edit_help_file).pack(side="left", padx=8, pady=6)
        ttk.Button(topbar, text="Open Config Folder", command=self._open_config_folder).pack(side="left", padx=6, pady=6)
        ttk.Label(topbar, text=HELP_PATH).pack(side="right", padx=8)

        frame = ttk.Frame(win); frame.pack(fill="both", expand=True, padx=8, pady=8)
        txt = tk.Text(frame, wrap="word", borderwidth=0, highlightthickness=0); txt.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(frame, orient="vertical", command=txt.yview); sb.pack(side="right", fill="y")
        txt.configure(yscrollcommand=sb.set)

        from markdown import render_markdown
        render_markdown(txt, text)
        apply_theme_to_toplevel(win)

    def _edit_help_file(self):
        ensure_help_file()
        try:
            os.startfile(HELP_PATH)
        except Exception as e:
            messagebox.showerror("Open Failed", f"Could not open help file:\n{e}")

    def _open_config_folder(self):
        ensure_config_dir()
        try:
            os.startfile(os.path.dirname(HELP_PATH))
        except Exception as e:
            messagebox.showerror("Open Failed", f"Could not open folder:\n{e}")

    def _show_about(self):
        messagebox.showinfo("About",
            "Elite Dangerous Backup\n"
            f"Version {VERSION}\n\n"
            "Back up your ED saves/configs to a ZIP or mirror folder.\n"
            "Switchable themes: Elite, Dark, Light (saved to config).\n"
            "Help lives next to config.json and is user-editable.\n\n"
            "Crafted by your favorite beer-can AI. 🍺"
        )

    # UI pump
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
                    self.btn_start.configure(state="normal"); self.btn_cancel.configure(state="disabled")
                    out = payload; self._log(f"Finished. Output:\n{out}")
                    messagebox.showinfo("Backup Complete", f"Backup finished.\n\nOutput:\n{out}")
                elif msg_type == "failed":
                    self.btn_start.configure(state="normal"); self.btn_cancel.configure(state="disabled")
                    err = payload; messagebox.showerror("Backup Failed", f"An error occurred:\n\n{err}")
                elif msg_type == "cancelled":
                    self.btn_start.configure(state="normal"); self.btn_cancel.configure(state="disabled")
                    self._log("Cancelled."); messagebox.showinfo("Cancelled", "Backup cancelled.")
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _log(self, text):
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
