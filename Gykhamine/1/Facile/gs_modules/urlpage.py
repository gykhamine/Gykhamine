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

class URLPage(GenPage):
    def __init__(self):
        super().__init__("URLs")
        self.form_box.append(self._section("NAMESPACE (optionnel)"))
        self.e_appname = entry("namespace (ex: articles)", "")
        self.e_appname.connect("changed", self._gen)
        self.form_box.append(self.e_appname)
        self.form_box.append(self._section("CHEMINS URL"))
        self.entries = []
        self.paths_box = vbox(4)
        self.form_box.append(self.paths_box)
        self.form_box.append(btn("➕ Ajouter un Chemin", "suggested-action", self._add_path))
        # URL types expliqués
        info = Gtk.Label(wrap=True, xalign=0)
        info.set_markup(
            "<small><b>Syntaxe des paramètres URL :</b>\n"
            "• <tt>&lt;int:pk&gt;</tt> — entier (clé primaire)\n"
            "• <tt>&lt;str:slug&gt;</tt> — texte\n"
            "• <tt>&lt;uuid:uid&gt;</tt> — UUID\n"
            "• <tt>&lt;path:fichier&gt;</tt> — chemin fichier</small>"
        )
        margins(info, 6, 0)
        self.form_box.append(info)
        # Raccourcis CRUD
        self.form_box.append(self._section("GÉNÉRATION CRUD RAPIDE"))
        g = Gtk.Grid(); g.set_column_spacing(8); g.set_row_spacing(4)
        self.e_crud_model = entry("nom_modele", "article")
        g.attach(lbl("Nom du modèle:"), 0, 0, 1, 1)
        g.attach(self.e_crud_model, 1, 0, 1, 1)
        self.form_box.append(g)
        self.form_box.append(btn("⚡ Générer URLs CRUD Complètes", "suggested-action", self._gen_crud))
        self._add_path("", "accueil", "home", "Page d'accueil")
        self._add_path("articles/", "article_list", "article-list", "Liste des articles")
        self._gen()

    def _add_path(self, path="", view="", name="", comment=""):
        row = vbox(3)
        row.add_css_class("field-row")
        r1 = hbox(6)
        e_path    = entry("chemin/", path); e_path.set_width_chars(20)
        e_view    = entry("nom_vue",  view); e_view.set_width_chars(18)
        e_name    = entry("nom-url",  name); e_name.set_width_chars(16)
        b = btn("✕","destructive-action",
                lambda w: (self.paths_box.remove(row), self._gen()))
        for w in (e_path, e_view, e_name):
            w.connect("changed", self._gen)
        r1.append(lbl("path:"))
        r1.append(e_path)
        r1.append(lbl("vue:"))
        r1.append(e_view)
        r1.append(lbl("name:"))
        r1.append(e_name)
        r1.append(b)
        row.append(r1)
        r2 = hbox(6)
        e_comment = entry("commentaire", comment); e_comment.set_hexpand(True)
        e_comment.connect("changed", self._gen)
        r2.append(lbl("# commentaire:"))
        r2.append(e_comment)
        row.append(r2)
        row._widgets = (e_path, e_view, e_name, e_comment)
        self.paths_box.append(row)
        self._gen()

    def _gen_crud(self, *_):
        name = self.e_crud_model.get_text().strip() or "article"
        crud_paths = [
            (f"{name}s/",                f"{name}_list",   f"{name}-list",   f"Liste des {name}s"),
            (f"{name}s/nouveau/",        f"{name}_create", f"{name}-create", f"Créer {name}"),
            (f"{name}s/<int:pk>/",       f"{name}_detail", f"{name}-detail", f"Détail {name}"),
            (f"{name}s/<int:pk>/modifier/",f"{name}_update",f"{name}-update",f"Modifier {name}"),
            (f"{name}s/<int:pk>/supprimer/",f"{name}_delete",f"{name}-delete",f"Supprimer {name}"),
            (f"{name}s/dashboard/",      f"{name}_dashboard",f"{name}-dashboard",f"Dashboard {name}"),
        ]
        # Vider les chemins existants
        child = self.paths_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.paths_box.remove(child)
            child = nxt
        for p, v, n, c in crud_paths:
            self._add_path(p, v, n, c)
        self._gen()

    def _gen(self, *_):
        entries = []
        child = self.paths_box.get_first_child()
        while child:
            if hasattr(child, '_widgets'):
                e_p, e_v, e_n, e_c = child._widgets
                entries.append({
                    'path': e_p.get_text(),
                    'view': e_v.get_text(),
                    'name': e_n.get_text(),
                    'comment': e_c.get_text(),
                })
            child = child.get_next_sibling()
        self.set_code(Gen.urls(entries, self.e_appname.get_text()))