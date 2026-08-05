"""Gestionnaire DB (admin complet) : projets récents, mémoire (memory), configuration
(table config) et fichier de log — la base système gy_studio.db, pas la base du projet
Django (voir _show_db_stats dans control_panel.py pour celle-ci)."""
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Pango

from ..config import global_log, set_margins
from ..database import (
    get_recent_projects_full, delete_recent_project, clear_recent_projects,
    get_memory_entries, get_memory_count, delete_memory_entry, clear_memory,
    get_config_entries, delete_config_entry,
    get_log_tail, get_log_size, clear_log_file,
)


def _row_box(children, spacing=8):
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=spacing)
    for c in children:
        box.append(c)
    return box


def _ellipsized_label(text, xalign=0, css=None, hexpand=False):
    lbl = Gtk.Label(label=text)
    lbl.set_xalign(xalign)
    lbl.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
    lbl.set_hexpand(hexpand)
    if css:
        lbl.add_css_class(css)
    return lbl


class RecentProjectsSection(Gtk.Box):
    """Liste des projets récents (table recent_projects) avec suppression individuelle."""

    def __init__(self, get_config, on_changed, show_toast):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.get_config, self.on_changed, self.show_toast = get_config, on_changed, show_toast

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.lbl_count = Gtk.Label(label="0 projet(s)"); self.lbl_count.add_css_class("dim-label"); self.lbl_count.set_hexpand(True); self.lbl_count.set_xalign(0)
        btn_clear = Gtk.Button(label="🗑 Tout effacer"); btn_clear.add_css_class("ctrl-btn-warn")
        btn_clear.connect("clicked", self._on_clear_all)
        header.append(self.lbl_count); header.append(btn_clear)
        self.append(header)

        scroll = Gtk.ScrolledWindow(); scroll.set_vexpand(True); scroll.set_min_content_height(320)
        self.list_box = Gtk.ListBox(); self.list_box.add_css_class("file-list")
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll.set_child(self.list_box)
        self.append(scroll)

    def refresh(self):
        while (child := self.list_box.get_first_child()):
            self.list_box.remove(child)
        entries = get_recent_projects_full(self.get_config())
        self.lbl_count.set_text(f"{len(entries)} projet(s)")
        if not entries:
            row = Gtk.ListBoxRow(); row.set_selectable(False)
            lbl = Gtk.Label(label="Aucun projet récent enregistré."); lbl.add_css_class("dim-label"); lbl.set_xalign(0)
            set_margins(lbl, 8); row.set_child(lbl)
            self.list_box.append(row)
            return
        for entry in entries:
            row = Gtk.ListBoxRow(); row.set_selectable(False)
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2); set_margins(inner, 6)
            top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            icon = "📁" if entry["exists"] else "⚠️"
            lbl_path = _ellipsized_label(f"{icon} {entry['path']}", hexpand=True)
            if not entry["exists"]:
                lbl_path.add_css_class("dim-label")
                lbl_path.set_tooltip_text("Ce chemin n'existe plus sur le disque")
            btn_del = Gtk.Button(label="🗑"); btn_del.add_css_class("flat"); btn_del.set_tooltip_text("Retirer des récents")
            btn_del.connect("clicked", self._on_delete, entry["id"])
            top.append(lbl_path); top.append(btn_del)
            lbl_date = Gtk.Label(label=f"Ouvert le {entry['opened_at'][:19]}"); lbl_date.add_css_class("dim-label"); lbl_date.set_xalign(0)
            inner.append(top); inner.append(lbl_date)
            row.set_child(inner)
            self.list_box.append(row)

    def _on_delete(self, _btn, project_id):
        if delete_recent_project(self.get_config(), project_id):
            self.show_toast("🗑 Projet retiré des récents")
            self.refresh()
            if self.on_changed: self.on_changed()
        else:
            self.show_toast("❌ Échec de la suppression")

    def _on_clear_all(self, *_):
        if clear_recent_projects(self.get_config()):
            self.show_toast("🗑 Liste des projets récents vidée")
            self.refresh()
            if self.on_changed: self.on_changed()
        else:
            self.show_toast("❌ Échec du vidage")


class MemorySection(Gtk.Box):
    """Liste des entrées de la table memory (historique d'édition par bloc/fichier)."""

    def __init__(self, get_config, show_toast):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.get_config, self.show_toast = get_config, show_toast

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.lbl_count = Gtk.Label(label="0 entrée(s)"); self.lbl_count.add_css_class("dim-label"); self.lbl_count.set_hexpand(True); self.lbl_count.set_xalign(0)
        btn_clear = Gtk.Button(label="🗑 Tout effacer"); btn_clear.add_css_class("ctrl-btn-warn")
        btn_clear.connect("clicked", self._on_clear_all)
        header.append(self.lbl_count); header.append(btn_clear)
        self.append(header)

        scroll = Gtk.ScrolledWindow(); scroll.set_vexpand(True); scroll.set_min_content_height(320)
        self.list_box = Gtk.ListBox(); self.list_box.add_css_class("file-list")
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll.set_child(self.list_box)
        self.append(scroll)

    def refresh(self):
        while (child := self.list_box.get_first_child()):
            self.list_box.remove(child)
        config = self.get_config()
        total = get_memory_count(config)
        entries = get_memory_entries(config, limit=200)
        self.lbl_count.set_text(f"{total} entrée(s) — {len(entries)} affichée(s)")
        if not entries:
            row = Gtk.ListBoxRow(); row.set_selectable(False)
            lbl = Gtk.Label(label="Aucune entrée en mémoire."); lbl.add_css_class("dim-label"); lbl.set_xalign(0)
            set_margins(lbl, 8); row.set_child(lbl)
            self.list_box.append(row)
            return
        for entry in entries:
            row = Gtk.ListBoxRow(); row.set_selectable(False)
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2); set_margins(inner, 6)
            top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            title = f"{entry['action']} · {entry['file_path']}" + (f" [{entry['block_name']}]" if entry['block_name'] else "")
            lbl_title = _ellipsized_label(title, hexpand=True)
            btn_del = Gtk.Button(label="🗑"); btn_del.add_css_class("flat"); btn_del.set_tooltip_text("Supprimer cette entrée")
            btn_del.connect("clicked", self._on_delete, entry["id"])
            top.append(lbl_title); top.append(btn_del)
            lbl_sub = Gtk.Label(label=f"📦 {entry['project']}  •  {entry['ts'][:19]}"); lbl_sub.add_css_class("dim-label"); lbl_sub.set_xalign(0)
            inner.append(top); inner.append(lbl_sub)
            row.set_child(inner)
            self.list_box.append(row)

    def _on_delete(self, _btn, entry_id):
        if delete_memory_entry(self.get_config(), entry_id):
            self.show_toast("🗑 Entrée supprimée")
            self.refresh()
        else:
            self.show_toast("❌ Échec de la suppression")

    def _on_clear_all(self, *_):
        if clear_memory(self.get_config()):
            self.show_toast("🗑 Mémoire entièrement vidée")
            self.refresh()
        else:
            self.show_toast("❌ Échec du vidage")


class ConfigSection(Gtk.Box):
    """Liste brute des clés/valeurs stockées dans la table config (persistées en base,
    en plus/à la place des valeurs par défaut de DEFAULT_CONFIG)."""

    def __init__(self, get_config, show_toast):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.get_config, self.show_toast = get_config, show_toast

        hint = Gtk.Label(label="Clés persistées en base (settings). Supprimer une clé la fait revenir à sa valeur par défaut.")
        hint.add_css_class("dim-label"); hint.set_xalign(0); hint.set_wrap(True)
        self.append(hint)

        self.lbl_count = Gtk.Label(label="0 clé(s)"); self.lbl_count.add_css_class("dim-label"); self.lbl_count.set_xalign(0)
        self.append(self.lbl_count)

        scroll = Gtk.ScrolledWindow(); scroll.set_vexpand(True); scroll.set_min_content_height(300)
        self.list_box = Gtk.ListBox(); self.list_box.add_css_class("file-list")
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll.set_child(self.list_box)
        self.append(scroll)

    def refresh(self):
        while (child := self.list_box.get_first_child()):
            self.list_box.remove(child)
        entries = get_config_entries(self.get_config())
        self.lbl_count.set_text(f"{len(entries)} clé(s)")
        if not entries:
            row = Gtk.ListBoxRow(); row.set_selectable(False)
            lbl = Gtk.Label(label="Aucune clé personnalisée en base."); lbl.add_css_class("dim-label"); lbl.set_xalign(0)
            set_margins(lbl, 8); row.set_child(lbl)
            self.list_box.append(row)
            return
        for entry in entries:
            row = Gtk.ListBoxRow(); row.set_selectable(False)
            inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8); set_margins(inner, 6)
            val_preview = (entry["value"] or "").replace("\n", " ")
            if len(val_preview) > 60: val_preview = val_preview[:60] + "…"
            lbl = _ellipsized_label(f"{entry['key']} = {val_preview}", hexpand=True)
            btn_del = Gtk.Button(label="🗑"); btn_del.add_css_class("flat"); btn_del.set_tooltip_text("Supprimer cette clé")
            btn_del.connect("clicked", self._on_delete, entry["key"])
            inner.append(lbl); inner.append(btn_del)
            row.set_child(inner)
            self.list_box.append(row)

    def _on_delete(self, _btn, key):
        if delete_config_entry(self.get_config(), key):
            self.show_toast(f"🗑 Clé « {key} » supprimée")
            self.refresh()
        else:
            self.show_toast("❌ Échec de la suppression")


class LogsSection(Gtk.Box):
    """Aperçu (tail) du fichier de log et bouton pour le vider."""

    def __init__(self, get_config, show_toast):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.get_config, self.show_toast = get_config, show_toast

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.lbl_size = Gtk.Label(label="0 Ko"); self.lbl_size.add_css_class("dim-label"); self.lbl_size.set_hexpand(True); self.lbl_size.set_xalign(0)
        btn_clear = Gtk.Button(label="🗑 Vider le log"); btn_clear.add_css_class("ctrl-btn-warn")
        btn_clear.connect("clicked", self._on_clear)
        header.append(self.lbl_size); header.append(btn_clear)
        self.append(header)

        scroll = Gtk.ScrolledWindow(); scroll.set_vexpand(True); scroll.set_min_content_height(320)
        self.text_view = Gtk.TextView(); self.text_view.set_editable(False); self.text_view.set_monospace(True)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scroll.set_child(self.text_view)
        self.append(scroll)

    def refresh(self):
        config = self.get_config()
        size = get_log_size(config)
        self.lbl_size.set_text(f"{size / 1024:.1f} Ko — dernières 300 lignes")
        tail = get_log_tail(config, max_lines=300)
        self.text_view.get_buffer().set_text(tail or "Fichier de log vide.")

    def _on_clear(self, *_):
        if clear_log_file(self.get_config()):
            self.show_toast("🗑 Fichier de log vidé")
            self.refresh()
        else:
            self.show_toast("❌ Échec du vidage du log")


class DbManagerDialog(Gtk.Window):
    """Fenêtre d'administration complète de la base système (gy_studio.db) :
    projets récents, mémoire, configuration persistée et fichier de log."""

    def __init__(self, parent, get_config, show_toast=None, on_recent_changed=None):
        super().__init__(title="🗄 Gestionnaire DB")
        self.set_transient_for(parent)
        self.set_default_size(680, 620)
        # La fenêtre construit sa propre Adw.HeaderBar juste en dessous : sans
        # set_decorated(False), GTK affiche EN PLUS sa barre de titre système
        # avec le même texte -> double titre superposé.
        self.set_decorated(False)
        self.set_resizable(True)
        self.add_css_class("rounded-dialog")
        self.get_config = get_config
        self.show_toast = show_toast or (lambda msg: None)
        self.on_recent_changed = on_recent_changed

        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        header = Adw.HeaderBar()
        # Sans décoration système, il faut demander explicitement les boutons
        # réduire/agrandir/fermer sur notre barre custom (voir cache_manager_dialog.py).
        header.set_show_end_title_buttons(True)
        header.set_decoration_layout("minimize,maximize,close")
        btn_refresh = Gtk.Button(label="🔄"); btn_refresh.set_tooltip_text("Actualiser")
        btn_refresh.connect("clicked", lambda *_: self._reload())
        header.pack_end(btn_refresh)
        root_box.append(header)

        # Barre d'onglets (même pattern que file_panel.py : boutons + Gtk.Stack)
        nav_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        set_margins(nav_bar, 8)
        self.stack = Gtk.Stack(); self.stack.set_vexpand(True)
        set_margins(self.stack, 14)

        self.recent_section = RecentProjectsSection(get_config, self._on_recent_changed, self.show_toast)
        self.memory_section = MemorySection(get_config, self.show_toast)
        self.config_section = ConfigSection(get_config, self.show_toast)
        self.logs_section = LogsSection(get_config, self.show_toast)

        self.stack.add_titled(self.recent_section, "recent", "🕒 Récents")
        self.stack.add_titled(self.memory_section, "memory", "🧠 Mémoire")
        self.stack.add_titled(self.config_section, "config", "⚙️ Config")
        self.stack.add_titled(self.logs_section, "logs", "📜 Logs")

        for name, label in [("recent", "🕒 Récents"), ("memory", "🧠 Mémoire"), ("config", "⚙️ Config"), ("logs", "📜 Logs")]:
            btn = Gtk.Button(label=label); btn.add_css_class("flat"); btn.set_hexpand(True)
            btn.connect("clicked", lambda _b, n=name: self.stack.set_visible_child_name(n))
            nav_bar.append(btn)

        root_box.append(nav_bar)
        root_box.append(self.stack)
        self.set_child(root_box)

        self._reload()

    def _reload(self):
        self.recent_section.refresh()
        self.memory_section.refresh()
        self.config_section.refresh()
        self.logs_section.refresh()

    def _on_recent_changed(self):
        if self.on_recent_changed:
            self.on_recent_changed()
