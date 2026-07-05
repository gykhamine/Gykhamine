"""Module généré automatiquement depuis gy.py"""
import time, threading
from pathlib import Path
import gi
gi.require_version("GLib", "2.0")
from gi.repository import GLib
from .config import global_log

#  FILE WATCHER - Amélioré avec détection fine et debounce
# ═══════════════════════════════════════════════════════════════════════
class FileWatcher(threading.Thread):
    def __init__(self, root_path, callback_on_change):
        super().__init__(daemon=True)
        self.root_path = Path(root_path)
        self.callback = callback_on_change
        self.running = True
        self.snapshot = {}
        self._debounce_timer = None
        self._debounce_interval = 0.8  # seconds
        self._pending_change = False
        self._update_snapshot()

    def _update_snapshot(self):
        self.snapshot = {}
        if self.root_path.exists():
            try:
                for p in self.root_path.rglob('*'):
                    if p.is_file():
                        try:
                                if p.suffix not in ('.bak', '.tmp'):
                                    self.snapshot[str(p)] = p.stat().st_mtime
                        except (PermissionError, OSError):
                            pass
            except (PermissionError, OSError) as e:
                global_log(f"⚠️ Erreur scan watcher: {e}")

    def _schedule_refresh(self):
        """Planifie un rafraîchissement avec debounce pour éviter les refreshs multiples."""
        self._pending_change = True
        if self._debounce_timer is None:
            self._debounce_timer = threading.Timer(self._debounce_interval, self._do_refresh)
            self._debounce_timer.daemon = True
            self._debounce_timer.start()

    def _do_refresh(self):
        """Exécute le rafraîchissement après le debounce."""
        self._debounce_timer = None
        if self._pending_change and self.running:
            self._pending_change = False
            try:
                GLib.idle_add(self.callback)
            except Exception:
                pass

    def run(self):
        while self.running:
            time.sleep(1.0)  # Check every second (faster response)
            if not self.running:
                break
            if not self.root_path.exists():
                continue
            
            current_files = {}
            changed = False
            try:
                for p in self.root_path.rglob('*'):
                    if p.is_file():
                        try:
                            if p.suffix in ('.bak', '.tmp'):
                                continue
                            mtime = p.stat().st_mtime
                            current_files[str(p)] = mtime
                            old_mtime = self.snapshot.get(str(p))
                            if old_mtime is None or old_mtime != mtime:
                                changed = True
                        except (PermissionError, OSError):
                            pass
            except (PermissionError, OSError):
                pass
            
            # Check for deleted files
            if set(current_files.keys()) != set(self.snapshot.keys()):
                changed = True
            
            if changed:
                self.snapshot = current_files
                self._schedule_refresh()

    def stop(self):
        """Arrête le watcher proprement."""
        self.running = False
        if self._debounce_timer:
            self._debounce_timer.cancel()
            self._debounce_timer = None

# ═══════════════════════════════════════════════════════════════════════
