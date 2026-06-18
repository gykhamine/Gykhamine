import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, Gio
import sys, os

from .utils import (
    CSS, lbl, btn, combo, entry, hbox, vbox, 
    scroll_wrap, margins, Gen
)
from .modelpage import ModelPage
from .viewpage import ViewPage
from .formpage import FormPage
from .adminpage import AdminPage
from .settingspage import SettingsPage
from .urlpage import URLPage
from .templatepage import TemplatePage
from .fileexplorer import FileExplorer
from .fileviewer import FileViewer

class GSApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.gci.gs.generator",
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.connect("activate", self._activate)

    def _activate(self, app):
        # CSS global
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title("GS — Gykhamine Studio Extension | Django 6.0.5 No-Code Generator")
        self.win.set_default_size(1600, 950)
        # ── HeaderBar ──
        header = Adw.HeaderBar()
        logo = Gtk.Label(label="⚡ GS — Django 6.0.5 Generator")
        logo.add_css_class("heading-blue")
        header.set_title_widget(logo)
        self.btn_copy = Gtk.Button(label="📋 Copier le Code")
        self.btn_copy.add_css_class("copy-btn")
        self.btn_copy.connect("clicked", self._copy)
        header.pack_end(self.btn_copy)
        # ── Layout principal ──
        root = hbox(0)
        # Panneau gauche — Explorateur
        self.explorer = FileExplorer(self._file_selected)
        root.append(self.explorer)
        root.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        # Zone centrale — Barre de navigation + contenu
        center = vbox(0)
        center.set_vexpand(True)
        center.set_hexpand(True)
        # Navigation par onglets
        nav = hbox(2)
        nav.add_css_class("nav-bar")
        margins(nav, 4, 6)
        self.pages = {
            "📦 Modèle":    ModelPage,
            "👁️ Vue":       ViewPage,
            "📝 Formulaire":FormPage,
            "⚙️ Admin":     AdminPage,
            "🔧 Settings":  SettingsPage,
            "🔗 URLs":      URLPage,
            "🖼️ Templates": TemplatePage,
        }
        self.current_widget = None
        self.content_area   = vbox(0)
        self.content_area.set_vexpand(True)
        self.content_area.set_hexpand(True)
        for label, cls in self.pages.items():
            b = Gtk.Button(label=label)
            b.connect("clicked", self._switch, cls)
            nav.append(b)
        center.append(nav)
        center.append(Gtk.Separator())
        center.append(self.content_area)
        root.append(center)
        # Layout vertical : header + root
        main_box = vbox(0)
        main_box.append(header)
        main_box.append(root)
        self.win.set_content(main_box)
        # Page par défaut
        self._switch(None, ModelPage)
        self.win.present()

    def _switch(self, btn, cls):
        child = self.content_area.get_first_child()
        while child:
            self.content_area.remove(child)
            child = self.content_area.get_first_child()
        self.current_widget = cls()
        self.content_area.append(self.current_widget)

    def _copy(self, *_):
        if self.current_widget and isinstance(self.current_widget, GenPage):
            code = self.current_widget.get_code()
            Gdk.Display.get_default().get_clipboard().set(code)
            original = self.btn_copy.get_label()
            self.btn_copy.set_label("✅ Copié !")
            from gi.repository import GLib
            GLib.timeout_add(2000, lambda: self.btn_copy.set_label(original))

    def _file_selected(self, path):
        # Afficher le fichier en lecture seule
        child = self.content_area.get_first_child()
        while child:
            self.content_area.remove(child)
            child = self.content_area.get_first_child()
        self.current_widget = FileViewer(path)
        self.content_area.append(self.current_widget)