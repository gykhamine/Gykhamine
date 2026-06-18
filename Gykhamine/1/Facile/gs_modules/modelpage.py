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

class ModelPage(GenPage):
    def __init__(self):
        super().__init__("Modèle")
        # 1. IDENTITÉ
        self.form_box.append(self._section("IDENTITÉ DU MODÈLE"))
        g = Gtk.Grid()
        g.set_column_spacing(10); g.set_row_spacing(8)
        self.entry_table = entry("ma_table", "article")
        self.entry_table.connect("changed", self._gen)
        g.attach(lbl("Nom de la table/classe:"), 0,0,1,1)
        g.attach(self.entry_table, 1,0,1,1)
        self.form_box.append(g)
        # 2. CHAMPS (Dynamiques)
        self.form_box.append(self._section("CHAMPS DU MODÈLE"))
        self.fields_box = vbox(4)
        self.form_box.append(self.fields_box)
        self.form_box.append(btn("➕ Ajouter un Champ", "suggested-action", self._add_field))
        # 3. LOGIQUE MÉTIER (clean method)
        self.form_box.append(self._section("RÈGLES DE VALIDATION (clean)"))
        self.logic_box = vbox(4)
        self.form_box.append(self.logic_box)
        self.form_box.append(btn("➕ Ajouter une Règle", None, self._add_logic))
        # Init
        self._add_field()
        self._gen()

    def _add_field(self, *_):
        # Correction GTK4: pas de get_children()
        idx = 0
        child = self.fields_box.get_first_child()
        while child:
            idx += 1
            child = child.get_next_sibling()
        row = vbox(4)
        row.add_css_class("field-row")
        # Ligne 1 : nom + type
        r1 = hbox(6)
        e_name = entry("nom_du_champ")
        e_name.set_width_chars(16)
        c_type = combo(Gen.FIELD_TYPES)
        c_type.set_size_request(200, -1)
        btn_del = btn("✕", "destructive-action")
        r1.append(e_name)
        r1.append(c_type)
        r1.append(btn_del)
        row.append(r1)
        # Options communes (null, blank, unique, default)
        r2 = hbox(8)
        chk_null   = Gtk.CheckButton.new_with_label("null")
        chk_blank  = Gtk.CheckButton.new_with_label("blank")
        chk_unique = Gtk.CheckButton.new_with_label("unique")
        chk_index  = Gtk.CheckButton.new_with_label("db_index")
        e_default  = entry("défaut", "", False)
        e_default.set_width_chars(10)
        e_default.set_placeholder_text("default=")
        for w in (chk_null, chk_blank, chk_unique, chk_index):
            r2.append(w)
        r2.append(lbl("défaut:"))
        r2.append(e_default)
        row.append(r2)
        # Options verbeux
        r3 = hbox(6)
        e_verbose = entry("Libellé lisible", "", True)
        e_help    = entry("Texte d'aide", "", True)
        r3.append(lbl("verbose:"))
        r3.append(e_verbose)
        r3.append(lbl("help:"))
        r3.append(e_help)
        row.append(r3)
        # Stockage des widgets pour la génération
        row._widgets = {
            'name': e_name, 'type': c_type,
            'null': chk_null, 'blank': chk_blank, 'unique': chk_unique, 'index': chk_index,
            'default': e_default, 'verbose': e_verbose, 'help': e_help,
        }
        # Signaux
        for w in (e_name, c_type, chk_null, chk_blank, chk_unique, chk_index, e_default, e_verbose, e_help):
            sig = "toggled" if isinstance(w, Gtk.CheckButton) else "changed"
            w.connect(sig, self._gen)
        btn_del.connect("clicked", lambda w: (self.fields_box.remove(row), self._gen()))
        self.fields_box.append(row)
        self._gen()

    def _add_logic(self, *_):
        row = hbox(6)
        row.add_css_class("logic-block")
        actions = [
            ("required",           "Champ Obligatoire"),
            ("min_value",          "Valeur Minimale"),
            ("max_value",          "Valeur Maximale"),
            ("min_length",         "Longueur Minimale"),
            ("positive",           "Valeur Positive"),
            ("date_future",        "Date dans le Futur"),
            ("conditional_required","Requis si autre champ"),
        ]
        c_action = combo(actions)
        e_field  = entry("champ")
        e_field.set_width_chars(14)
        e_value  = entry("valeur")
        e_value.set_width_chars(10)
        btn_del  = btn("✕", "destructive-action")
        row._widgets = (c_action, e_field, e_value)
        for w in (c_action, e_field, e_value):
            sig = "changed"
            w.connect(sig, self._gen)
        btn_del.connect("clicked", lambda w: (self.logic_box.remove(row), self._gen()))
        row.append(c_action)
        row.append(lbl("champ:"))
        row.append(e_field)
        row.append(lbl("val:"))
        row.append(e_value)
        row.append(btn_del)
        self.logic_box.append(row)
        self._gen()

    def _gen(self, *_):
        table_name = self.entry_table.get_text().strip() or "ma_table"
        fields = []
        child = self.fields_box.get_first_child()
        while child:
            if hasattr(child, '_widgets'):
                w = child._widgets
                name = w['name'].get_text().strip()
                ftype_id = w['type'].get_active_id() or "CharField"
                if name:
                    opts = {
                        'null':    w['null'].get_active(),
                        'blank':   w['blank'].get_active(),
                        'unique':  w['unique'].get_active(),
                        'db_index':w['index'].get_active(),
                        'default': w['default'].get_text().strip(),
                        'verbose': w['verbose'].get_text().strip(),
                        'help_text': w['help'].get_text().strip(),
                    }
                    fields.append({'name': name, 'type': ftype_id, 'opts': opts})
            child = child.get_next_sibling()
        logic = []
        child = self.logic_box.get_first_child()
        while child:
            if hasattr(child, '_widgets'):
                c_action, e_field, e_value = child._widgets
                logic.append({
                    'action': c_action.get_active_id(),
                    'field':  e_field.get_text(),
                    'value':  e_value.get_text(),
                })
            child = child.get_next_sibling()
        self.set_code(Gen.model(table_name, fields, logic))