import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, Gio
import sys, os

from .utils import (
    CSS, lbl, btn, combo, entry, hbox, vbox, 
    scroll_wrap, margins, Gen
)
from .genpage import GenPage

class AdminPage(GenPage):
    def __init__(self):
        super().__init__("Admin")
        self.form_box.append(self._section("MODÈLE"))
        self.e_model = entry("NomModele", "Article")
        self.e_model.connect("changed", self._gen)
        self.form_box.append(self.e_model)
        # Listes dynamiques (list_display, list_filter, etc.)
        for (attr, section, default) in [
            ('e_list_display', "LIST_DISPLAY (colonnes affichées)", "['__str__', 'id']"),
            ('e_list_filter',  "LIST_FILTER (filtres latéraux)",     "['actif']"),
            ('e_search',       "SEARCH_FIELDS (champs recherche)",   "['nom', 'email']"),
            ('e_readonly',     "READONLY_FIELDS",                    "['created_at']"),
        ]:
            self.form_box.append(self._section(section))
            box_attr = vbox(3)
            setattr(self, f"{attr}_box", box_attr)
            self.form_box.append(box_attr)
            # Ajouter le bouton d'ajout
            btn_add = btn("➕ Ajouter", None, lambda w, b=box_attr, d=default: (self._add_simple_row(b, d), self._gen()))
            self.form_box.append(btn_add)
            # Initialiser avec la valeur par défaut
            self._add_simple_row(box_attr, default)
        # Actions personnalisées
        self.form_box.append(self._section("ACTIONS ADMIN PERSONNALISÉES"))
        self.actions_box = vbox(4)
        self.form_box.append(self.actions_box)
        self.form_box.append(btn("➕ Ajouter une Action", None, self._add_action))
        # Logique save_model
        self.form_box.append(self._section("LOGIQUE SAVE_MODEL"))
        self.logic_box = vbox(4)
        self.form_box.append(self.logic_box)
        self.form_box.append(btn("➕ Ajouter Logique", None, self._add_logic))
        self._gen()

    def _add_simple_row(self, box, default=""):
        row = hbox(6)
        row.add_css_class("field-row")
        e = entry("", default)
        e.connect("changed", self._gen)
        b = btn("✕", "destructive-action",
                lambda w: (box.remove(row), self._gen()))
        row.append(e); row.append(b)
        box.append(row)

    def _add_action(self, *_):
        row = hbox(6)
        row.add_css_class("logic-block")
        types = [
            ("activate",   "Activer sélection"),
            ("deactivate", "Désactiver sélection"),
            ("export_csv", "Exporter CSV"),
            ("message",    "Afficher message"),
        ]
        c_type = combo(types)
        e_fn   = entry("nom_fonction"); e_fn.set_width_chars(15)
        e_desc = entry("Description action"); e_desc.set_hexpand(True)
        b = btn("✕","destructive-action",
                lambda w: (self.actions_box.remove(row), self._gen()))
        row._widgets = (c_type, e_fn, e_desc)
        for w in (c_type, e_fn, e_desc):
            w.connect("changed", self._gen)
        row.append(c_type); row.append(e_fn); row.append(e_desc); row.append(b)
        self.actions_box.append(row)
        self._gen()

    def _add_logic(self, *_):
        row = hbox(6)
        row.add_css_class("logic-block")
        actions = [
            ("set_user","Assigner utilisateur courant"),
            ("log_save","Journaliser la sauvegarde"),
        ]
        c = combo(actions)
        e = entry("nom_champ"); e.set_width_chars(15)
        b = btn("✕","destructive-action",
                lambda w: (self.logic_box.remove(row), self._gen()))
        row._widgets = (c, e)
        c.connect("changed", self._gen); e.connect("changed", self._gen)
        row.append(c); row.append(e); row.append(b)
        self.logic_box.append(row)
        self._gen()

    def _collect_simple_rows(self, box):
        """Collecte les valeurs des entrées simples dans une boîte."""
        result = []
        child = box.get_first_child()
        while child:
            if isinstance(child, Gtk.Box):
                c = child.get_first_child()
                while c:
                    if isinstance(c, Gtk.Entry):
                        v = c.get_text().strip()
                        if v: result.append(v)
                    c = c.get_next_sibling()
            child = child.get_next_sibling()
        return result

    def _gen(self, *_):
        model = self.e_model.get_text() or "MonModele"
        # Récupérer les listes
        list_display = str(self._collect_simple_rows(self.e_list_display_box))
        list_filter = str(self._collect_simple_rows(self.e_list_filter_box))
        search_fields = str(self._collect_simple_rows(self.e_search_box))
        readonly_fields = str(self._collect_simple_rows(self.e_readonly_box))
        # Actions
        actions = []
        child = self.actions_box.get_first_child()
        while child:
            if hasattr(child, '_widgets'):
                c_t, e_f, e_d = child._widgets
                actions.append({'type': c_t.get_active_id(), 'fn': e_f.get_text(), 'desc': e_d.get_text()})
            child = child.get_next_sibling()
        # Logique
        logic = []
        child = self.logic_box.get_first_child()
        while child:
            if hasattr(child, '_widgets'):
                c, e = child._widgets
                logic.append({'action': c.get_active_id(), 'field': e.get_text()})
            child = child.get_next_sibling()
        self.set_code(Gen.admin(
            model          = model,
            list_display   = list_display if list_display != "[]" else "['__str__']",
            list_filter    = list_filter if list_filter != "[]" else "[]",
            search_fields  = search_fields if search_fields != "[]" else "[]",
            readonly_fields= readonly_fields if readonly_fields != "[]" else "[]",
            logic          = logic,
            actions        = actions,
        ))