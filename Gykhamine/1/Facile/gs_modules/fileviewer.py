import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, Gio
import sys, os

from .utils import (
    CSS, lbl, btn, combo, entry, hbox, vbox, 
    scroll_wrap, margins, Gen
)

class FileViewer(Gtk.Box):
    def __init__(self, path):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_vexpand(True)
        self.set_hexpand(True)
        buf = Gtk.TextBuffer()
        tv = Gtk.TextView(buffer=buf)
        tv.set_editable(False)
        tv.set_monospace(True)
        tv.add_css_class("code-area")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                buf.set_text(f.read())
        except Exception as ex:
            buf.set_text(f"Impossible de lire le fichier:\n{ex}")
        self.append(scroll_wrap(tv))