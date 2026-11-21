import os
import stat
from dataclasses import dataclass, field

from phosh_toolkit.settings import JsonStore, app_dir


@dataclass
class Account:
    name: str = ""
    networks: list = field(default_factory=list)


def test_app_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert app_dir("cache", "myapp") == tmp_path / "myapp"


def test_round_trip_and_unknown_keys(tmp_path):
    store = JsonStore(tmp_path / "a" / "account.json", Account, 2)
    assert store.load() == Account()
    store.save(Account("robin", ["Home"]))
    text = store.path.read_text()
    assert '"version": 2' in text
    store.path.write_text(text.replace('"name"', '"old": 1, "name"'))
    assert store.load() == Account("robin", ["Home"])


def test_broken_file_is_kept(tmp_path):
    store = JsonStore(tmp_path / "account.json", Account)
    store.path.write_text("{broken")
    assert store.load() == Account()
    assert (tmp_path / "account.bad").read_text() == "{broken"


def test_account_file_is_private(tmp_path):
    """The file names addresses and user names: readable by the user
    only, whatever the umask; a file of an older version is tightened
    when it is read."""
    path = tmp_path / "app" / "account.json"
    store = JsonStore(path, Account)
    old = os.umask(0o022)
    try:
        store.save(Account())
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        path.chmod(0o644)
        store.load()
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        store.save(Account())
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    finally:
        os.umask(old)
