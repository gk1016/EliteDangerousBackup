import tkinter as tk
from tkinter import ttk

THEMES = {
    "elite": {
        "bg": "#0b0b0b", "fg": "#ff9d00", "muted": "#c07a00",
        "widget_bg": "#111111",
        "entry_bg": "#000000", "entry_fg": "#f0f0f0",
        "button_bg": "#1a1a1a", "button_fg": "#ffd27a",
        "accent": "#ff9d00", "accent_fg": "#111111",
        "progress_trough": "#1a1a1a", "progress_bar": "#ff9d00",
        "text_bg": "#000000", "text_fg": "#ff9d00",
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

    root.configure(bg=bg)
    try:
        style.theme_use("clam")
    except Exception:
        pass

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
    style.configure("TEntry", fieldbackground=ebg, foreground=efg, background=wbg)

    style.configure("TProgressbar", troughcolor=trough, background=pbar, bordercolor=trough, lightcolor=pbar, darkcolor=pbar)

    # tk menus & combobox popdown listbox
    root.option_add("*Menu.background", menu_bg)
    root.option_add("*Menu.foreground", menu_fg)
    root.option_add("*Menu.activeBackground", accent)
    root.option_add("*Menu.activeForeground", theme["accent_fg"])
    root.option_add("*TCombobox*Listbox.background", ebg)
    root.option_add("*TCombobox*Listbox.foreground", efg)
    root.option_add("*TCombobox*Listbox.selectBackground", select_bg)
    root.option_add("*TCombobox*Listbox.selectForeground", select_fg)

    def style_text_widget(widget: tk.Text):
        try:
            widget.configure(bg=tbg, fg=tfg, insertbackground=tfg,
                             selectbackground=select_bg, selectforeground=select_fg,
                             highlightthickness=1, highlightbackground=theme["border"],
                             highlightcolor=accent, relief="flat")
        except Exception:
            pass

    def style_entry_widget(widget: tk.Entry):
        try:
            widget.configure(bg=ebg, fg=efg, insertbackground=efg,
                             selectbackground=select_bg, selectforeground=select_fg,
                             highlightthickness=1, highlightbackground=theme["border"],
                             highlightcolor=accent, relief="flat")
        except Exception:
            pass

    root._theme_helpers = {"style_text": style_text_widget, "style_entry": style_entry_widget}
    restyle_everything(root)

def _iter_widgets(widget):
    yield widget
    for child in widget.winfo_children():
        yield from _iter_widgets(child)

def restyle_everything(root: tk.Misc):
    helpers = getattr(root, "_theme_helpers", {})
    style_text = helpers.get("style_text")
    style_entry = helpers.get("style_entry")
    for w in _iter_widgets(root):
        try:
            klass = w.winfo_class()
        except Exception:
            continue
        if klass == "Text" and style_text:
            style_text(w)
        elif klass == "Entry" and style_entry:
            style_entry(w)

def apply_theme_to_toplevel(win: tk.Toplevel):
    restyle_everything(win)
