import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, Gio
import sys, os

from .utils import (
    CSS, lbl, btn, combo, entry, hbox, vbox, 
    scroll_wrap, margins, Gen
)

class FileExplorer(Gtk.Box):
    def __init__(self, on_select):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.on_select = on_select
        self.add_css_class("file-panel")
        self.set_size_request(220, -1)
        hdr = hbox(6)
        margins(hdr, 8, 8)
        hdr.append(lbl("📂 PROJET", "heading-blue"))
        self.append(hdr)
        btn_open = btn("Ouvrir Dossier", None, self._open)
        margins(btn_open, 4, 8)
        self.append(btn_open)
        self.tree_store = Gtk.TreeStore(str, str, bool)
        self.tree_view  = Gtk.TreeView(model=self.tree_store)
        self.tree_view.set_headers_visible(False)
        renderer = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn("", renderer, text=0)
        self.tree_view.append_column(col)
        self.tree_view.connect("row-activated", self._activated)
        self.append(scroll_wrap(self.tree_view))

    def _open(self, *_):
        Gtk.FileDialog(title="Ouvrir un projet Django").select_folder(None, None, self._loaded)

    def _loaded(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                from pathlib import Path
                self._fill(Path(folder.get_path()), None)
        except: pass

    def _fill(self, directory, parent_iter):
        self.tree_store.clear()
        self._add_dir(directory, None)

    def _add_dir(self, directory, parent):
        from pathlib import Path
        try:
            entries = sorted(directory.iterdir(), key=lambda p:(not p.is_dir(), p.name.lower()))
            for e in entries:
                if e.name in ('__pycache__','.git','venv','.venv','node_modules'): continue
                icon = "📁" if e.is_dir() else "📄"
                it = self.tree_store.append(parent, [f"{icon} {e.name}", str(e), e.is_dir()])
                if e.is_dir(): self._add_dir(e, it)
        except: pass

    def _activated(self, tv, path, col):
        m = tv.get_model()
        it = m.get_iter(path)
        fp = m.get_value(it, 1)
        is_dir = m.get_value(it, 2)
        if is_dir:
            if tv.row_expanded(path): tv.collapse_row(path)
            else: tv.expand_row(path, False)
        else:
            if self.on_select: self.on_select(fp)