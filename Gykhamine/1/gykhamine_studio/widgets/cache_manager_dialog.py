"""Gestionnaire du cache IA : consulter et vider les 3 tables de cache alimentées
par ai_engine.py (commandes shell générées, blocs de code générés, processus JSON
générés par l'Élaborateur)."""
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Pango

from ..config import global_log, set_margins
from ..database import (
    AI_CACHE_TABLES, get_cache_stats, get_cache_entries, clear_cache_table,
    clear_all_ai_cache, delete_cache_entry, update_cache_entry,
)


class CacheTableSection(Gtk.Box):
    """Une section pour une table de cache : compteur, aperçu des dernières entrées, bouton Vider."""

    def __init__(self, table: str, meta: dict, on_cleared, show_toast):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.table = table
        self.meta = meta
        self.on_cleared = on_cleared
        self.show_toast = show_toast
        self.add_css_class("block-card")
        set_margins(self, 10)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.lbl_title = Gtk.Label(label=meta["label"]); self.lbl_title.add_css_class("heading"); self.lbl_title.set_xalign(0); self.lbl_title.set_hexpand(True)
        self.lbl_count = Gtk.Label(label="0 entrée(s)"); self.lbl_count.add_css_class("dim-label")
        btn_clear = Gtk.Button(label="🗑 Vider"); btn_clear.add_css_class("ctrl-btn-warn")
        btn_clear.connect("clicked", self._on_clear)
        header.append(self.lbl_title); header.append(self.lbl_count); header.append(btn_clear)
        self.append(header)

        self.preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.append(self.preview_box)

    def refresh(self, count: int, entries: list):
        self.lbl_count.set_text(f"{count} entrée(s)")
        while (child := self.preview_box.get_first_child()):
            self.preview_box.remove(child)
        # Chaque occurrence en cache est listée individuellement (plus
        # seulement un aperçu des 5 dernières) : on peut la voir en entier,
        # la modifier, ou la supprimer une par une, sans vider toute la table.
        for entry in entries:
            self.preview_box.append(self._build_entry_row(entry))
        if not entries:
            lbl = Gtk.Label(label="Aucune entrée en cache."); lbl.set_xalign(0); lbl.add_css_class("dim-label")
            self.preview_box.append(lbl)

    def _build_entry_row(self, entry: dict) -> Gtk.Box:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.add_css_class("cache-entry-row")

        preview = (entry["content"] or "").replace("\n", " ").strip()
        if len(preview) > 90:
            preview = preview[:90] + "…"
        lbl = Gtk.Label(label=f"• {preview}  ({entry['created_at'][:19]})")
        lbl.set_xalign(0); lbl.set_hexpand(True)
        lbl.set_ellipsize(Pango.EllipsizeMode.END); lbl.add_css_class("dim-label")
        row.append(lbl)

        btn_edit = Gtk.Button(); btn_edit.set_child(Gtk.Image.new_from_icon_name("document-edit-symbolic"))
        btn_edit.add_css_class("block-action-btn")
        btn_edit.set_tooltip_text("Voir / modifier cette entrée")
        btn_edit.connect("clicked", lambda *_: self._open_edit_popover(btn_edit, entry))
        row.append(btn_edit)

        btn_del = Gtk.Button(); btn_del.set_child(Gtk.Image.new_from_icon_name("user-trash-symbolic"))
        btn_del.add_css_class("block-action-btn")
        btn_del.set_tooltip_text("Supprimer cette entrée")
        btn_del.connect("clicked", lambda *_: self._on_delete_entry(entry))
        row.append(btn_del)

        return row

    def _open_edit_popover(self, anchor: Gtk.Widget, entry: dict):
        """Popover d'édition : montre le contenu COMPLET de l'occurrence (pas
        le résumé tronqué de la liste), modifiable puis enregistrable — ne
        touche qu'à CETTE entrée, identifiée par son intent_hash."""
        popover = Gtk.Popover()
        popover.set_parent(anchor)
        popover.set_size_request(420, 320)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        set_margins(box, 10)

        scroll = Gtk.ScrolledWindow(); scroll.set_vexpand(True); scroll.set_hexpand(True)
        text_view = Gtk.TextView(); text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_view.set_monospace(True)
        text_view.get_buffer().set_text(entry["content"] or "")
        scroll.set_child(text_view)
        box.append(scroll)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, halign=Gtk.Align.END)
        btn_cancel = Gtk.Button(label="Annuler")
        btn_cancel.connect("clicked", lambda *_: popover.popdown())
        btn_save = Gtk.Button(label="💾 Enregistrer", css_classes=["suggested-action"])

        def _on_save(*_):
            buf = text_view.get_buffer()
            new_text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
            if update_cache_entry(self.table, entry["intent_hash"], new_text):
                self.show_toast(f"💾 Entrée « {self.meta['label']} » modifiée")
                popover.popdown()
                if self.on_cleared:  # même callback que pour un vidage : recharge la liste
                    self.on_cleared()
            else:
                self.show_toast("❌ Échec de la modification")

        btn_save.connect("clicked", _on_save)
        btn_box.append(btn_cancel)
        btn_box.append(btn_save)
        box.append(btn_box)

        popover.set_child(box)
        popover.popup()

    def _on_delete_entry(self, entry: dict):
        if delete_cache_entry(self.table, entry["intent_hash"]):
            self.show_toast(f"🗑 Entrée « {self.meta['label']} » supprimée")
            if self.on_cleared:
                self.on_cleared()
        else:
            self.show_toast("❌ Échec de la suppression de l'entrée")

    def _on_clear(self, *_):
        if clear_cache_table(self.table):
            self.show_toast(f"🗑 Cache « {self.meta['label']} » vidé")
            if self.on_cleared:
                self.on_cleared()
        else:
            self.show_toast("❌ Échec du vidage du cache")


class CacheManagerDialog(Gtk.Window):
    """Fenêtre listant les 3 tables de cache IA, avec vidage individuel ou global."""

    def __init__(self, parent, show_toast=None):
        super().__init__(title="🧠 Gestionnaire du Cache IA")
        self.set_transient_for(parent)
        self.set_default_size(640, 520)
        # La fenêtre construit sa propre Adw.HeaderBar juste en dessous : sans
        # set_decorated(False), GTK affiche EN PLUS sa barre de titre système
        # avec le même texte -> double titre superposé.
        self.set_decorated(False)
        self.set_resizable(True)
        self.add_css_class("rounded-dialog")
        self.show_toast = show_toast or (lambda msg: None)

        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        header = Adw.HeaderBar()
        # Sans décoration système, il faut demander explicitement les boutons
        # réduire/agrandir/fermer sur notre barre custom, sinon seule la fermeture
        # est proposée (ou rien du tout) et la fenêtre reste bloquée à sa taille
        # par défaut — on est obligé de passer par le plein écran général de l'appli.
        header.set_show_end_title_buttons(True)
        header.set_decoration_layout("minimize,maximize,close")
        btn_clear_all = Gtk.Button(label="🗑 Tout vider"); btn_clear_all.add_css_class("destructive-action")
        btn_clear_all.connect("clicked", self._on_clear_all)
        header.pack_end(btn_clear_all)
        btn_refresh = Gtk.Button(label="🔄"); btn_refresh.set_tooltip_text("Actualiser")
        btn_refresh.connect("clicked", lambda *_: self._reload())
        header.pack_end(btn_refresh)
        root_box.append(header)

        scroll = Gtk.ScrolledWindow(); scroll.set_vexpand(True); scroll.set_hexpand(True)
        self.sections_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        set_margins(self.sections_box, 14)
        scroll.set_child(self.sections_box)
        root_box.append(scroll)

        self.set_child(root_box)

        self.sections = {}
        for table, meta in AI_CACHE_TABLES.items():
            section = CacheTableSection(table, meta, on_cleared=self._reload, show_toast=self.show_toast)
            self.sections[table] = section
            self.sections_box.append(section)

        self._reload()

    def _reload(self):
        stats = get_cache_stats()
        for table, section in self.sections.items():
            entries = get_cache_entries(table, limit=50)
            section.refresh(stats.get(table, 0), entries)

    def _on_clear_all(self, *_):
        if clear_all_ai_cache():
            self.show_toast("🗑 Tout le cache IA a été vidé")
            self._reload()
        else:
            self.show_toast("❌ Échec du vidage complet du cache")
