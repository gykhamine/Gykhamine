"""Runtime — carte des actions utilisateur + automatisation au démarrage."""
import json, threading
from pathlib import Path
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib
from .config import set_margins, global_log
from .database import load_config, save_config

# ─── Actions enregistrables ────────────────────────────────────────────
# Chaque action est : {"id": str, "label": str, "callback_name": str}
# L'app enregistre ses actions via RuntimeManager.register_action()
# ──────────────────────────────────────────────────────────────────────

class RuntimeManager:
    """Gère la carte des actions et les runtimes d'automatisation."""

    def __init__(self):
        self._actions: dict[str, callable] = {}  # id -> callable
        self._action_labels: dict[str, str] = {}  # id -> label lisible
        self._runtimes: list[dict] = []  # [{"name": str, "steps": [action_id...]}]
        self._auto_runtime: str | None = None  # nom du runtime auto
        self._load()

    # ── Enregistrement d'actions ───────────────────────────────────────
    def register_action(self, action_id: str, label: str, callback: callable):
        self._actions[action_id] = callback
        self._action_labels[action_id] = label

    # ── Persistance ────────────────────────────────────────────────────
    def _db_path(self) -> Path:
        cfg = load_config()
        db = Path(cfg.get("db_path", Path.home() / ".gykhamine_studio.db"))
        return db.parent / "gykhamine_runtimes.json"

    def _load(self):
        try:
            p = self._db_path()
            if p.exists():
                data = json.loads(p.read_text())
                self._runtimes = data.get("runtimes", [])
                self._auto_runtime = data.get("auto_runtime")
        except Exception as e:
            global_log(f"⚠️ Runtime load error: {e}")

    def _save(self):
        try:
            p = self._db_path()
            p.write_text(json.dumps({
                "runtimes": self._runtimes,
                "auto_runtime": self._auto_runtime
            }, ensure_ascii=False, indent=2))
        except Exception as e:
            global_log(f"⚠️ Runtime save error: {e}")

    # ── Exécution ──────────────────────────────────────────────────────
    def run(self, runtime_name: str, log_cb=None):
        rt = next((r for r in self._runtimes if r["name"] == runtime_name), None)
        if not rt:
            if log_cb: log_cb(f"❌ Runtime '{runtime_name}' introuvable")
            return
        def _exec():
            for step_id in rt.get("steps", []):
                cb = self._actions.get(step_id)
                label = self._action_labels.get(step_id, step_id)
                if cb:
                    try:
                        if log_cb: GLib.idle_add(log_cb, f"▶ {label}")
                        GLib.idle_add(cb)
                    except Exception as e:
                        if log_cb: GLib.idle_add(log_cb, f"❌ {label}: {e}")
                else:
                    if log_cb: GLib.idle_add(log_cb, f"⚠ Action inconnue: {step_id}")
        threading.Thread(target=_exec, daemon=True).start()

    def run_auto(self, log_cb=None):
        if self._auto_runtime:
            self.run(self._auto_runtime, log_cb)

    # ── Accesseurs ─────────────────────────────────────────────────────
    def get_runtimes(self) -> list[dict]:
        return list(self._runtimes)

    def get_auto_runtime(self) -> str | None:
        return self._auto_runtime

    def set_auto_runtime(self, name: str | None):
        self._auto_runtime = name
        self._save()

    def add_runtime(self, name: str, steps: list[str]):
        self._runtimes = [r for r in self._runtimes if r["name"] != name]
        self._runtimes.append({"name": name, "steps": steps})
        self._save()

    def delete_runtime(self, name: str):
        self._runtimes = [r for r in self._runtimes if r["name"] != name]
        if self._auto_runtime == name:
            self._auto_runtime = None
        self._save()

    def get_available_actions(self) -> dict[str, str]:
        return dict(self._action_labels)


# ─── Dialog d'édition Runtime ──────────────────────────────────────────
class RuntimeDialog(Gtk.Dialog):
    def __init__(self, parent, runtime_manager: RuntimeManager, log_cb=None):
        super().__init__(title="⚡ Runtimes", transient_for=parent)
        self.rm = runtime_manager
        self.log_cb = log_cb
        self.add_css_class("rounded-dialog")
        self.set_default_size(600, 480)

        content = self.get_content_area()
        content.set_spacing(8)
        set_margins(content, 12)

        # ── Split : liste runtimes | éditeur ──
        split = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        split.set_vexpand(True)

        # Liste des runtimes
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        left.set_size_request(180, -1)
        left.append(Gtk.Label(label="Runtimes", xalign=0, css_classes=["heading"]))

        scroll_rt = Gtk.ScrolledWindow()
        scroll_rt.set_vexpand(True)
        scroll_rt.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._rt_list = Gtk.ListBox()
        self._rt_list.add_css_class("boxed-list")
        self._rt_list.connect("row-selected", self._on_rt_selected)
        scroll_rt.set_child(self._rt_list)
        left.append(scroll_rt)

        btn_add_rt = Gtk.Button(label="➕ Nouveau runtime")
        btn_add_rt.add_css_class("flat")
        btn_add_rt.connect("clicked", self._new_runtime)
        left.append(btn_add_rt)

        split.append(left)
        split.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        # Éditeur du runtime sélectionné
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        right.set_hexpand(True)

        self._rt_name_entry = Gtk.Entry()
        self._rt_name_entry.set_placeholder_text("Nom du runtime")
        right.append(self._rt_name_entry)

        right.append(Gtk.Label(label="Étapes (actions utilisateur) :", xalign=0))

        # Étapes sélectionnées
        scroll_steps = Gtk.ScrolledWindow()
        scroll_steps.set_vexpand(True)
        self._steps_list = Gtk.ListBox()
        self._steps_list.add_css_class("boxed-list")
        scroll_steps.set_child(self._steps_list)
        right.append(scroll_steps)

        # Ajouter une étape
        action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._action_combo = Gtk.ComboBoxText()
        for aid, alabel in sorted(self.rm.get_available_actions().items(), key=lambda x: x[1]):
            self._action_combo.append(aid, alabel)
        self._action_combo.set_hexpand(True)
        btn_add_step = Gtk.Button(label="＋")
        btn_add_step.connect("clicked", self._add_step)
        action_row.append(self._action_combo)
        action_row.append(btn_add_step)
        right.append(action_row)

        # Boutons
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Runtime auto
        self._auto_check = Gtk.CheckButton(label="Auto au démarrage")
        self._auto_check.set_hexpand(True)
        btn_row.append(self._auto_check)

        btn_save_rt = Gtk.Button(label="💾 Sauvegarder")
        btn_save_rt.add_css_class("suggested-action")
        btn_save_rt.connect("clicked", self._save_runtime)
        btn_del_rt = Gtk.Button(label="🗑")
        btn_del_rt.add_css_class("destructive-action")
        btn_del_rt.connect("clicked", self._delete_runtime)

        btn_run = Gtk.Button(label="▶ Lancer")
        btn_run.add_css_class("suggested-action")
        btn_run.connect("clicked", self._run_selected)

        btn_row.append(btn_del_rt)
        btn_row.append(btn_save_rt)
        btn_row.append(btn_run)
        right.append(btn_row)

        split.append(right)
        content.append(split)

        self._current_steps: list[str] = []
        self._refresh_rt_list()

    def _refresh_rt_list(self):
        while child := self._rt_list.get_first_child():
            self._rt_list.remove(child)
        auto = self.rm.get_auto_runtime()
        for rt in self.rm.get_runtimes():
            lbl = f"{'⭐ ' if rt['name'] == auto else ''}{rt['name']}"
            row = Gtk.ListBoxRow()
            row._rt_name = rt["name"]
            row.set_child(Gtk.Label(label=lbl, xalign=0, margin_start=8, margin_top=4, margin_bottom=4))
            self._rt_list.append(row)

    def _on_rt_selected(self, lb, row):
        if not row: return
        name = row._rt_name
        rt = next((r for r in self.rm.get_runtimes() if r["name"] == name), None)
        if not rt: return
        self._rt_name_entry.set_text(name)
        self._current_steps = list(rt.get("steps", []))
        self._refresh_steps()
        self._auto_check.set_active(self.rm.get_auto_runtime() == name)

    def _refresh_steps(self):
        while child := self._steps_list.get_first_child():
            self._steps_list.remove(child)
        actions = self.rm.get_available_actions()
        for i, step_id in enumerate(self._current_steps):
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            set_margins(box, 4)
            lbl = Gtk.Label(label=actions.get(step_id, step_id), xalign=0, hexpand=True)
            btn_rm = Gtk.Button(label="✕")
            btn_rm.add_css_class("flat")
            idx = i
            btn_rm.connect("clicked", lambda _, i=idx: self._remove_step(i))
            box.append(lbl)
            box.append(btn_rm)
            row.set_child(box)
            self._steps_list.append(row)

    def _add_step(self, *_):
        aid = self._action_combo.get_active_id()
        if aid:
            self._current_steps.append(aid)
            self._refresh_steps()

    def _remove_step(self, idx: int):
        if 0 <= idx < len(self._current_steps):
            self._current_steps.pop(idx)
            self._refresh_steps()

    def _new_runtime(self, *_):
        self._rt_name_entry.set_text("Nouveau runtime")
        self._current_steps = []
        self._refresh_steps()
        self._auto_check.set_active(False)

    def _save_runtime(self, *_):
        name = self._rt_name_entry.get_text().strip()
        if not name: return
        self.rm.add_runtime(name, list(self._current_steps))
        if self._auto_check.get_active():
            self.rm.set_auto_runtime(name)
        elif self.rm.get_auto_runtime() == name:
            self.rm.set_auto_runtime(None)
        self._refresh_rt_list()

    def _delete_runtime(self, *_):
        name = self._rt_name_entry.get_text().strip()
        if name:
            self.rm.delete_runtime(name)
            self._rt_name_entry.set_text("")
            self._current_steps = []
            self._refresh_steps()
            self._refresh_rt_list()

    def _run_selected(self, *_):
        name = self._rt_name_entry.get_text().strip()
        if name:
            self.rm.run(name, self.log_cb)
