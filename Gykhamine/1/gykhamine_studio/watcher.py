"""Module généré automatiquement depuis gy.py"""
import time, threading
from pathlib import Path
import gi
gi.require_version("GLib", "2.0")
from gi.repository import GLib
from .config import global_log

#  FILE WATCHER
# ═══════════════════════════════════════════════════════════════════════
class FileWatcher(threading.Thread):
    def __init__(self, root_path, callback_on_change):
        super().__init__(daemon=True)
        self.root_path = Path(root_path)
        self.callback = callback_on_change
        self.running = True
        self.snapshot = {}
        self._update_snapshot()

    def _update_snapshot(self):
        self.snapshot = {}
        if self.root_path.exists():
            for p in self.root_path.rglob('*'):
                if p.is_file():
                    try: self.snapshot[str(p)] = p.stat().st_mtime
                    except Exception as e:
                        global_log(f"⚠️ Erreur dans gy.py: {type(e).__name__} - {e}")
    def run(self):
        while self.running:
            time.sleep(1.5)
            if not self.root_path.exists(): continue
            current_files = {}
            changed = False
            for p in self.root_path.rglob('*'):
                if p.is_file():
                    try:
                        mtime = p.stat().st_mtime
                        current_files[str(p)] = mtime
                        if str(p) not in self.snapshot or self.snapshot[str(p)] != mtime: changed = True
                    except Exception as e:
                        global_log(f"⚠️ Erreur dans gy.py: {type(e).__name__} - {e}")
            if set(current_files.keys()) != set(self.snapshot.keys()): changed = True
            if changed:
                self.snapshot = current_files
                GLib.idle_add(self.callback)

# ═══════════════════════════════════════════════════════════════════════
