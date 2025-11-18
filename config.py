import json
import os
from constants import CONFIG_DIR, CONFIG_PATH, HELP_PATH, HELP_DEFAULT

def ensure_config_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)

def ensure_help_file():
    ensure_config_dir()
    if not os.path.exists(HELP_PATH) or os.path.getsize(HELP_PATH) == 0:
        with open(HELP_PATH, "w", encoding="utf-8") as f:
            f.write(HELP_DEFAULT)

def default_sources():
    userprofile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    localapp = os.environ.get("LOCALAPPDATA", os.path.join(userprofile, "AppData", "Local"))
    saved_games = os.path.join(userprofile, "Saved Games")
    return [
        os.path.join(saved_games, "Frontier Developments", "Elite Dangerous"),
        os.path.join(localapp, "Frontier Developments"),
        os.path.join(localapp, "Frontier_Developments"),
    ]

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

def get_config_with_defaults():
    cfg = load_config()
    if "sources" not in cfg or not isinstance(cfg.get("sources"), list) or len(cfg["sources"]) != 3:
        cfg["sources"] = default_sources()
    cfg.setdefault("zip_mode", False)
    cfg.setdefault("incremental", True)
    cfg.setdefault("theme", "elite")  # elite | dark | light
    return cfg

def read_help_text():
    ensure_help_file()
    try:
        with open(HELP_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"(Unable to load help.md: {e})"
