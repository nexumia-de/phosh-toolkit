"""An app's files: XDG directories and a JSON file holding one dataclass
(the account). No GTK."""
import json
import os
from dataclasses import asdict
from pathlib import Path

_XDG = {"config": ("XDG_CONFIG_HOME", ".config"),
        "data": ("XDG_DATA_HOME", ".local/share"),
        "cache": ("XDG_CACHE_HOME", ".cache")}


def app_dir(kind, app):
    """$XDG_<KIND>_HOME/<app> for kind "config", "data" or "cache"; in the
    Flatpak these point into the app's own directory."""
    env, default = _XDG[kind]
    base = os.environ.get(env) or str(Path.home() / default)
    return Path(base) / app


class JsonStore:
    """Loads and saves a dataclass `cls` as {"version": …, "account": …}.
    Unknown keys are dropped; a broken file is kept as .bad and a fresh
    object returned. The file is readable by the user only (mode 600): it
    holds no secrets, but addresses and user names."""

    def __init__(self, path, cls, version=1):
        self.path = Path(path)
        self.cls = cls
        self.version = version

    def load(self):
        try:
            # Files of versions that wrote with the default umask.
            os.chmod(self.path, 0o600)
        except OSError:
            pass
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return self.cls()
        except (OSError, ValueError):
            # Keep the broken file for a bug report and start over.
            self.path.replace(self.path.with_suffix(".bad"))
            return self.cls()
        known = self.cls.__dataclass_fields__
        return self.cls(**{k: v for k, v in data.get("account", {}).items()
                           if k in known})

    def save(self, obj):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        text = json.dumps({"version": self.version, "account": asdict(obj)},
                          indent=1)
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            # A .tmp left behind by an older version keeps its mode.
            os.fchmod(fd, 0o600)
            f.write(text)
        tmp.replace(self.path)
