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

class FormPage(GenPage):
    def __init__(self):
        super().__init__("Formulaire")
        self.form_box.append(self._section("MODÈLE LIÉ"))
        self.e_model = entry("NomModele", "Article")
        self.e_model.connect("changed", self._gen)
        self.form_box.append(self.e_model)
        # Champs sélectionnés
        self.form_box.append(self._section("CHAMPS À INCLURE"))
        chk_all = Gtk.CheckButton.new_with_label("Tous les champs (__all__)")
        chk_all.set_active(True)
        self.chk_all = chk_all
        chk_all.connect("toggled", self._toggle_all_fields)
        chk_all.connect("toggled", self._gen)
        self.form_box.append(chk_all)
        self.fields_box = vbox(3)
        self.form_box.append(self.fields_box)
        self.form_box.append(btn("➕ Ajouter un Champ", None, self._add_field_row))
        # Widgets personnalisés
        self.form_box.append(self._section("WIDGETS PERSONNALISÉS"))
        self.widgets_box = vbox(4)
        self.form_box.append(self.widgets_box)
        self.form_box.append(btn("➕ Personnaliser un Widget", None, self._add_widget))
        # Logique
        self.form_box.append(self._section("RÈGLES DE VALIDATION"))
        self.logic_box = vbox(4)
        self.form_box.append(self.logic_box)
        self.form_box.append(btn("➕ Ajouter Règle", None, self._add_logic))
        self._gen()

    def _toggle_all_fields(self, chk):
        self.fields_box.set_visible(not chk.get_active())

    def _add_field_row(self, *_):
        row = hbox(6)
        row.add_css_class("field-row")
        e = entry("nom_champ")
        e.connect("changed", self._gen)
        b = btn("✕", "destructive-action",
                lambda w: (self.fields_box.remove(row), self._gen()))
        row.append(e); row.append(b)
        self.fields_box.append(row)
        self._gen()

    def _add_widget(self, *_):
        row = hbox(6)
        row.add_css_class("logic-block")
        widget_types = [
            ("TextInput","TextInput"), ("Textarea","Textarea"),
            ("Select","Select"), ("CheckboxInput","CheckboxInput"),
            ("DateInput","DateInput"), ("DateTimeInput","DateTimeInput"),
            ("NumberInput","NumberInput"), ("EmailInput","EmailInput"),
            ("URLInput","URLInput"), ("PasswordInput","PasswordInput"),
            ("FileInput","FileInput"), ("HiddenInput","HiddenInput"),
        ]
        e_field = entry("champ")
        e_field.set_width_chars(12)
        c_widget = combo(widget_types)
        e_attrs  = entry("{'class':'form-control'}")
        b = btn("✕", "destructive-action",
                lambda w: (self.widgets_box.remove(row), self._gen()))
        row._widgets = (e_field, c_widget, e_attrs)
        for w in (e_field, c_widget, e_attrs):
            sig = "changed"
            w.connect(sig, self._gen)
        b.connect("clicked", lambda w: (self.widgets_box.remove(row), self._gen()))
        row.append(lbl("champ:")); row.append(e_field)
        row.append(lbl("widget:")); row.append(c_widget)
        row.append(lbl("attrs:")); row.append(e_attrs)
        row.append(b)
        self.widgets_box.append(row)
        self._gen()

    def _add_logic(self, *_):
        row = hbox(6)
        row.add_css_class("logic-block")
        actions = [
            ("required",       "Champ Obligatoire"),
            ("min_length",     "Longueur Minimale"),
            ("match_fields",   "Correspondance Champs"),
            ("email_domain",   "Domaine Email"),
            ("numeric_only",   "Numérique seulement"),
            ("positive",       "Valeur Positive"),
        ]
        c_action = combo(actions)
        e_field  = entry("champ"); e_field.set_width_chars(12)
        e_value  = entry("valeur"); e_value.set_width_chars(10)
        b = btn("✕", "destructive-action",
                lambda w: (self.logic_box.remove(row), self._gen()))
        row._widgets = (c_action, e_field, e_value)
        for w in (c_action, e_field, e_value):
            w.connect("changed", self._gen)
        row.append(c_action); row.append(lbl("champ:")); row.append(e_field)
        row.append(lbl("val:")); row.append(e_value); row.append(b)
        self.logic_box.append(row)
        self._gen()

    def _gen(self, *_):
        model = self.e_model.get_text() or "MonModele"
        all_f = self.chk_all.get_active()
        # Champs sélectionnés
        selected = []
        child = self.fields_box.get_first_child()
        while child:
            if isinstance(child, Gtk.Box):
                c = child.get_first_child()
                while c:
                    if isinstance(c, Gtk.Entry):
                        v = c.get_text().strip()
                        if v: selected.append(v)
                    c = c.get_next_sibling()
            child = child.get_next_sibling()
        # Widgets
        widgets = []
        child = self.widgets_box.get_first_child()
        while child:
            if hasattr(child, '_widgets'):
                e_f, c_w, e_a = child._widgets
                widgets.append({'field': e_f.get_text(), 'widget': c_w.get_active_id(), 'attrs': e_a.get_text()})
            child = child.get_next_sibling()
        # Logique
        logic = []
        child = self.logic_box.get_first_child()
        while child:
            if hasattr(child, '_widgets'):
                c_a, e_f, e_v = child._widgets
                logic.append({'action': c_a.get_active_id(), 'field': e_f.get_text(), 'value': e_v.get_text()})
            child = child.get_next_sibling()
        self.set_code(Gen.form(model, all_f, selected, logic, widgets))