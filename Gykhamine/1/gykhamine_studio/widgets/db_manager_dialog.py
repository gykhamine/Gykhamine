"""
Gestionnaire de base de données interne (DBManagerDialog).

Ce module est entièrement indépendant du système de Runtime (runtime.py) :
aucun import croisé, aucun état partagé. Chaque ouverture du dialogue lit
une copie fraîche de la configuration et de la base.

Architecture : chaque ligne de table est représentée par un vrai objet
GObject (DBRow) stocké dans un Gio.ListStore, conformément à l'API GTK4
Gtk.ColumnView - pas d'index de position bricolé.
"""
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gio", "2.0")
gi.require_version("GObject", "2.0")
from gi.repository import Gtk, Adw, GLib, Gio, GObject
from ..config import global_log, set_margins
from ..database import (
    list_db_tables, get_table_schema, get_table_rows, get_table_primary_key,
    insert_table_row, update_table_row, delete_table_row, truncate_table,
)


class DBRow(GObject.Object):
    def __init__(self, data: dict):
        super().__init__()
        self.data = data


class DBManagerDialog(Gtk.Window):
    def __init__(self, parent, config: dict):
        super().__init__(title="Gestionnaire de base de données")
        self.set_transient_for(parent)
        self.set_modal(False)
        self.set_default_size(950, 620)
        self.config = dict(config)
        self.current_table = None
        self.current_schema = []
        self._all_rows = []

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        set_margins(root, 10)
        self.set_child(root)

        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        top_bar.append(Gtk.Label(label="Table :", css_classes=["heading"]))

        tables = list_db_tables(self.config) or []
        self.table_combo = Gtk.DropDown.new_from_strings(tables or ["(aucune table)"])
        self.table_combo.connect("notify::selected", self._on_table_selected)
        top_bar.append(self.table_combo)

        btn_refresh = Gtk.Button(label="🔄 Actualiser")
        btn_refresh.connect("clicked", lambda *_: self._refresh_current_table())
        top_bar.append(btn_refresh)

        spacer = Gtk.Box(hexpand=True)
        top_bar.append(spacer)

        btn_add = Gtk.Button(label="➕ Ajouter une ligne")
        btn_add.add_css_class("suggested-action")
        btn_add.connect("clicked", self._on_add_row)
        top_bar.append(btn_add)

        btn_reset = Gtk.Button(label="🗑 Réinitialiser la table")
        btn_reset.add_css_class("destructive-action")
        btn_reset.connect("clicked", self._on_reset_table)
        top_bar.append(btn_reset)

        root.append(top_bar)

        # ── Barre de recherche : filtre les lignes affichées et permet de
        # sauter directement à une ligne précise (par valeur de n'importe
        # quelle colonne, pas seulement la clé primaire).
        search_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Rechercher une ligne (toutes colonnes)…")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        search_bar.append(self.search_entry)
        self.search_status_lbl = Gtk.Label(label="", css_classes=["dim-label"])
        search_bar.append(self.search_status_lbl)
        root.append(search_bar)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.column_view = Gtk.ColumnView()
        self.column_view.add_css_class("data-table")
        self.list_store = Gio.ListStore.new(DBRow)
        self.selection_model = Gtk.SingleSelection(model=self.list_store)
        self.selection_model.connect("notify::selected", self._on_row_selection_changed)
        self.column_view.set_model(self.selection_model)
        scroll.set_child(self.column_view)
        root.append(scroll)

        row_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.btn_edit = Gtk.Button(label="✏️ Modifier la ligne sélectionnée")
        self.btn_edit.set_sensitive(False)
        self.btn_edit.connect("clicked", self._on_edit_selected)
        self.btn_delete = Gtk.Button(label="🗑 Supprimer la ligne sélectionnée")
        self.btn_delete.add_css_class("destructive-action")
        self.btn_delete.set_sensitive(False)
        self.btn_delete.connect("clicked", self._on_delete_selected)
        row_actions.append(self.btn_edit)
        row_actions.append(self.btn_delete)
        root.append(row_actions)

        self.status_lbl = Gtk.Label(label="", xalign=0, css_classes=["dim-label"])
        root.append(self.status_lbl)

        if tables:
            self.current_table = tables[0]
            self._refresh_current_table()

    def _on_table_selected(self, dropdown, _pspec):
        idx = dropdown.get_selected()
        model = dropdown.get_model()
        if model is None or idx == Gtk.INVALID_LIST_POSITION:
            return
        table_name = model.get_string(idx)
        if table_name == "(aucune table)":
            return
        self.current_table = table_name
        self._refresh_current_table()

    def _refresh_current_table(self):
        if not self.current_table:
            return
        self.current_schema = get_table_schema(self.config, self.current_table)
        rows = get_table_rows(self.config, self.current_table)
        self._all_rows = rows  # copie complète, non filtrée, pour la recherche
        self._populate_columns()
        query = self.search_entry.get_text().strip() if hasattr(self, "search_entry") else ""
        self._apply_search_filter(query)
        self.status_lbl.set_text(f"{len(rows)} ligne(s) — table « {self.current_table} »")

    def _populate_columns(self):
        columns = self.column_view.get_columns()
        while columns.get_n_items() > 0:
            self.column_view.remove_column(columns.get_item(0))

        for col_name, _type, is_pk in self.current_schema:
            factory = Gtk.SignalListItemFactory()
            factory.connect("setup", self._on_cell_setup)
            factory.connect("bind", self._make_bind_fn(col_name))
            title = f"🔑 {col_name}" if is_pk else col_name
            column = Gtk.ColumnViewColumn(title=title, factory=factory)
            column.set_expand(True)
            self.column_view.append_column(column)

    def _on_cell_setup(self, factory, list_item):
        list_item.set_child(Gtk.Label(xalign=0))

    def _make_bind_fn(self, col_name):
        def _bind(factory, list_item):
            db_row = list_item.get_item()
            if db_row is None:
                return
            value = db_row.data.get(col_name, "")
            text = "" if value is None else str(value)
            if len(text) > 120:
                text = text[:120] + "…"
            list_item.get_child().set_text(text)
        return _bind

    def _on_search_changed(self, entry):
        self._apply_search_filter(entry.get_text().strip())

    def _apply_search_filter(self, query: str):
        """Filtre les lignes affichées en fonction du texte recherché, en
        cherchant dans TOUTES les colonnes de chaque ligne (pas seulement la
        clé primaire). Permet de retrouver directement une ligne précise
        sans avoir à parcourir toute la table visuellement."""
        if not query:
            filtered = self._all_rows
            self.search_status_lbl.set_text("")
        else:
            q = query.lower()
            filtered = [
                row for row in self._all_rows
                if any(q in str(v).lower() for v in row.values() if v is not None)
            ]
            self.search_status_lbl.set_text(f"{len(filtered)} résultat(s) sur {len(self._all_rows)}")
        self._populate_rows(filtered)

    def _populate_rows(self, rows: list):
        self.list_store.remove_all()
        for row_dict in rows:
            self.list_store.append(DBRow(row_dict))
        self.btn_edit.set_sensitive(False)
        self.btn_delete.set_sensitive(False)

    def _on_row_selection_changed(self, selection, _pspec):
        idx = selection.get_selected()
        has_selection = idx != Gtk.INVALID_LIST_POSITION
        self.btn_edit.set_sensitive(has_selection)
        self.btn_delete.set_sensitive(has_selection)

    def _get_selected_row(self):
        idx = self.selection_model.get_selected()
        if idx == Gtk.INVALID_LIST_POSITION:
            return None
        db_row = self.selection_model.get_item(idx)
        return db_row.data if db_row else None

    def _open_row_form(self, title: str, initial: dict, on_confirm):
        dialog = Gtk.Dialog(title=title, transient_for=self, modal=True)
        dialog.set_default_size(420, 100)
        content = dialog.get_content_area()
        content.set_spacing(8)
        set_margins(content, 12)

        entries = {}
        for col_name, _type, is_pk in self.current_schema:
            label = f"{col_name} (clé primaire)" if is_pk else col_name
            content.append(Gtk.Label(label=label, xalign=0))
            entry = Gtk.Entry()
            entry.set_text(str(initial.get(col_name, "")) if initial.get(col_name) is not None else "")
            content.append(entry)
            entries[col_name] = entry

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_cancel = Gtk.Button(label="Annuler")
        btn_confirm = Gtk.Button(label="✅ Valider")
        btn_confirm.add_css_class("suggested-action")
        btn_box.append(btn_cancel)
        btn_box.append(btn_confirm)
        content.append(btn_box)

        def on_ok(*_):
            values = {k: e.get_text() for k, e in entries.items()}
            on_confirm(values)
            dialog.destroy()

        btn_confirm.connect("clicked", on_ok)
        btn_cancel.connect("clicked", lambda *_: dialog.destroy())
        dialog.present()

    def _on_add_row(self, *_):
        if not self.current_table:
            return self._show_error("Sélectionnez d'abord une table")

        def on_confirm(values):
            ok = insert_table_row(self.config, self.current_table, values)
            if ok:
                self._refresh_current_table()
            else:
                self._show_error("Échec de l'insertion (voir les logs)")

        self._open_row_form(f"Ajouter une ligne — {self.current_table}", {}, on_confirm)

    def _on_edit_selected(self, *_):
        row = self._get_selected_row()
        if row is None:
            return
        pk_column = get_table_primary_key(self.config, self.current_table)
        if not pk_column:
            return self._show_error("Cette table n'a pas de clé primaire : modification impossible.")
        pk_value = row.get(pk_column)

        def on_confirm(values):
            values_without_pk = {k: v for k, v in values.items() if k != pk_column}
            ok = update_table_row(self.config, self.current_table, pk_column, pk_value, values_without_pk)
            if ok:
                self._refresh_current_table()
            else:
                self._show_error("Échec de la mise à jour (voir les logs)")

        self._open_row_form(f"Modifier — {self.current_table}", row, on_confirm)

    def _on_delete_selected(self, *_):
        row = self._get_selected_row()
        if row is None:
            return
        pk_column = get_table_primary_key(self.config, self.current_table)
        if not pk_column:
            return self._show_error("Cette table n'a pas de clé primaire : suppression impossible.")
        pk_value = row.get(pk_column)

        confirm = Gtk.Dialog(title="Confirmer la suppression", transient_for=self, modal=True)
        confirm.set_default_size(360, 120)
        content = confirm.get_content_area()
        content.set_spacing(8)
        set_margins(content, 12)
        content.append(Gtk.Label(label=f"Supprimer la ligne « {pk_value} » ?", xalign=0))
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_cancel = Gtk.Button(label="Annuler")
        btn_delete = Gtk.Button(label="🗑 Supprimer")
        btn_delete.add_css_class("destructive-action")
        btn_box.append(btn_cancel)
        btn_box.append(btn_delete)
        content.append(btn_box)

        def on_ok(*_):
            ok = delete_table_row(self.config, self.current_table, pk_column, pk_value)
            confirm.destroy()
            if ok:
                self._refresh_current_table()
            else:
                self._show_error("Échec de la suppression (voir les logs)")

        btn_delete.connect("clicked", on_ok)
        btn_cancel.connect("clicked", lambda *_: confirm.destroy())
        confirm.present()

    def _on_reset_table(self, *_):
        """Vide entièrement la table courante (remise à 0). Opération
        irréversible : demande à l'utilisateur de retaper le nom exact de la
        table pour confirmer, plutôt qu'un simple Oui/Non, pour limiter le
        risque de clic accidentel sur une action aussi destructive."""
        if not self.current_table:
            return self._show_error("Sélectionnez d'abord une table")

        confirm = Gtk.Dialog(title="Confirmer la réinitialisation", transient_for=self, modal=True)
        confirm.set_default_size(420, 180)
        content = confirm.get_content_area()
        content.set_spacing(8)
        set_margins(content, 12)
        content.append(Gtk.Label(
            label=f"Ceci supprimera TOUTES les {len(self._all_rows)} ligne(s) de la table « {self.current_table} ».\nCette action est irréversible.",
            xalign=0, wrap=True,
        ))
        content.append(Gtk.Label(label=f"Tapez « {self.current_table} » pour confirmer :", xalign=0, margin_top=8))
        entry_confirm = Gtk.Entry()
        content.append(entry_confirm)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_cancel = Gtk.Button(label="Annuler")
        btn_reset = Gtk.Button(label="🗑 Réinitialiser")
        btn_reset.add_css_class("destructive-action")
        btn_reset.set_sensitive(False)
        btn_box.append(btn_cancel)
        btn_box.append(btn_reset)
        content.append(btn_box)

        def on_entry_changed(*_):
            btn_reset.set_sensitive(entry_confirm.get_text().strip() == self.current_table)
        entry_confirm.connect("changed", on_entry_changed)

        def on_ok(*_):
            ok = truncate_table(self.config, self.current_table)
            confirm.destroy()
            if ok:
                self.search_entry.set_text("")
                self._refresh_current_table()
            else:
                self._show_error("Échec de la réinitialisation (voir les logs)")

        btn_reset.connect("clicked", on_ok)
        btn_cancel.connect("clicked", lambda *_: confirm.destroy())
        confirm.present()

    def _show_error(self, message: str):
        self.status_lbl.set_text(f"❌ {message}")
        global_log(f"❌ DBManager: {message}")
