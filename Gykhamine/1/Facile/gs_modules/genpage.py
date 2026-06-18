import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, Gio
import sys, os

from .utils import (
    CSS, lbl, btn, combo, entry, hbox, vbox, 
    scroll_wrap, margins, Gen
)

class GenPage(Gtk.Box):
    def __init__(self, title):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.set_vexpand(True)
        # Panneau gauche — Formulaire
        self.form_box = vbox(10)
        margins(self.form_box, 12, 12)
        form_scroll = scroll_wrap(self.form_box)
        form_scroll.set_size_request(440, -1)
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        # Panneau droit — Aperçu code
        self.code_buf = Gtk.TextBuffer()
        self.code_view = Gtk.TextView(buffer=self.code_buf)
        self.code_view.set_editable(False)
        self.code_view.set_monospace(True)
        self.code_view.add_css_class("code-area")
        code_scroll = scroll_wrap(self.code_view)
        self.append(form_scroll)
        self.append(sep)
        self.append(code_scroll)

    def set_code(self, code):
        self.code_buf.set_text(code)

    def get_code(self):
        return self.code_buf.get_text(
            self.code_buf.get_start_iter(),
            self.code_buf.get_end_iter(), True)

    def _section(self, text):
        l = lbl(text, "section-title")
        margins(l, 4, 0)
        return l

    def _collect_box_entries(self, box):
        """Parcourir un vbox et retourner le texte de chaque Entry trouvée."""
        result = []
        child = box.get_first_child()
        while child:
            if isinstance(child, Gtk.Entry):
                v = child.get_text().strip()
                if v: result.append(v)
            elif isinstance(child, Gtk.Box):
                # cherche dans les enfants directs
                c = child.get_first_child()
                while c:
                    if isinstance(c, Gtk.Entry):
                        v = c.get_text().strip()
                        if v: result.append(v)
                    c = c.get_next_sibling()
            child = child.get_next_sibling()
        return result

    def _add_removable_entry(self, parent_box, default="", gen_callback=None):
        row = hbox(6)
        row.add_css_class("field-row")
        e = entry(text=default)
        if gen_callback: e.connect("changed", gen_callback)
        b = btn("✕", "destructive-action",
                lambda w: (parent_box.remove(row), gen_callback() if gen_callback else None))
        row.append(e)
        row.append(b)
        parent_box.append(row)
        return e