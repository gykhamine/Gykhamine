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

class TemplatePage(GenPage):
    def __init__(self):
        super().__init__("Template")
        # Onglets internes
        notebook = Gtk.Notebook()
        notebook.set_vexpand(True)
        # TAB 1 — base.html
        tab_base = self._build_base_tab()
        notebook.append_page(tab_base, lbl("🏠 base.html"))
        # TAB 2 — Template enfant
        tab_child = self._build_child_tab()
        notebook.append_page(tab_child, lbl("📄 Page Enfant"))
        # TAB 3 — Éditeur Visuel (NOUVEAU)
        tab_visual = self._build_visual_editor_tab()
        notebook.append_page(tab_visual, lbl("🎨 Éditeur Visuel"))
        # TAB 4 — JS Snippets
        tab_js = self._build_js_tab()
        notebook.append_page(tab_js, lbl("⚡ JS Réutilisable (25)"))
        # TAB 5 — Tags & Filtres
        tab_tags = self._build_tags_tab()
        notebook.append_page(tab_tags, lbl("🏷️ Tags & Filtres Django"))
        # Note: remplace le form_box par notebook dans le panneau gauche
        # On doit reconstruire le layout
        # Récupérer la form_scroll et y mettre le notebook
        child = self.get_first_child()  # form_scroll
        if child:
            child.set_child(notebook)
        self._gen_base()
        self._gen_child()

    def _build_base_tab(self):
        box = vbox(10)
        margins(box, 12, 12)
        box.append(lbl("CONFIGURATION base.html", "section-title"))
        g = Gtk.Grid(); g.set_column_spacing(10); g.set_row_spacing(6)
        self.e_base_title  = entry("", "MonSite GCI")
        self.e_base_color  = entry("", "#0d3b6e")
        self.chk_chart     = Gtk.CheckButton.new_with_label("Inclure Chart.js")
        g.attach(lbl("Titre du site:"), 0,0,1,1); g.attach(self.e_base_title, 1,0,1,1)
        g.attach(lbl("Couleur principale:"), 0,1,1,1); g.attach(self.e_base_color, 1,1,1,1)
        g.attach(lbl("Options:"), 0,2,1,1); g.attach(self.chk_chart, 1,2,1,1)
        box.append(g)
        b = btn("🔄 Générer base.html", "suggested-action", self._gen_base)
        box.append(b)
        for w in (self.e_base_title, self.e_base_color, self.chk_chart):
            sig = "toggled" if isinstance(w, Gtk.CheckButton) else "changed"
            w.connect(sig, self._gen_base)
        return scroll_wrap(box)

    def _build_child_tab(self):
        box = vbox(10)
        margins(box, 12, 12)
        box.append(lbl("TEMPLATE ENFANT", "section-title"))
        g = Gtk.Grid(); g.set_column_spacing(10); g.set_row_spacing(6)
        self.e_child_name  = entry("", "article")
        self.e_child_base  = entry("", "base.html")
        self.c_child_type  = combo([
            ("entrer",    "Formulaire Entrée"),
            ("liste",     "Liste Tableau"),
            ("dashboard", "Tableau de bord"),
        ])
        self.e_child_model_var = entry("", "objet")
        g.attach(lbl("Nom (module):"), 0,0,1,1); g.attach(self.e_child_name, 1,0,1,1)
        g.attach(lbl("Hérite de:"),    0,1,1,1); g.attach(self.e_child_base,  1,1,1,1)
        g.attach(lbl("Type de page:"), 0,2,1,1); g.attach(self.c_child_type,  1,2,1,1)
        g.attach(lbl("Variable modèle:"), 0,3,1,1); g.attach(self.e_child_model_var, 1,3,1,1)
        box.append(g)
        box.append(btn("🔄 Générer Template", "suggested-action", self._gen_child))
        for w in (self.e_child_name, self.e_child_base, self.c_child_type, self.e_child_model_var):
            sig = "changed"
            w.connect(sig, self._gen_child)
        return scroll_wrap(box)

    def _build_visual_editor_tab(self):
        """Constructeur d'éditeur visuel pour ajouter des éléments HTML/Django"""
        box = vbox(10)
        margins(box, 12, 12)
        box.append(lbl("ÉDITEUR VISUEL DE TEMPLATE", "section-title"))
        box.append(lbl("Cliquez sur les boutons pour ajouter du code dans l'aperçu", "heading-orange"))
        # Grille de boutons d'éléments
        grid_elements = Gtk.Grid()
        grid_elements.set_column_spacing(8)
        grid_elements.set_row_spacing(8)
        elements = [
            ("div", "📦 Div"), ("section", "📑 Section"), ("article", "📰 Article"),
            ("h1", "H1"), ("h2", "H2"), ("h3", "H3"),
            ("p", "¶ Paragraphe"), ("a", "🔗 Lien"), ("button", "🔘 Bouton"),
            ("img", "🖼️ Image"), ("video", "🎥 Vidéo"), ("form", "📝 Formulaire"),
            ("input", "⌨️ Input"), ("table", "📊 Tableau"), ("ul", "• Liste"),
        ]
        for i, (tag, label) in enumerate(elements):
            b = btn(label, None, self._insert_html_tag(tag))
            grid_elements.attach(b, i%4, i//4, 1, 1)
        box.append(grid_elements)
        box.append(Gtk.Separator())
        # Section Tags Django
        box.append(lbl("TAGS DJANGO RAPIDES", "section-title"))
        grid_tags = Gtk.Grid()
        grid_tags.set_column_spacing(8)
        grid_tags.set_row_spacing(8)
        tags = [
            ("{% csrf_token %}", "🔒 CSRF"),
            ("{% load static %}", "📂 Load Static"),
            ("{% url 'home' %}", "🔗 URL"),
            ("{{ variable }}", "📦 Variable"),
            ("{% if condition %}", "❓ If"),
            ("{% for item in list %}", "🔄 For"),
            ("{% block content %}", "🧱 Block"),
            ("{% extends 'base.html' %}", "🏠 Extends"),
        ]
        for i, (code, label) in enumerate(tags):
            b = btn(label, None, self._insert_text(code))
            grid_tags.attach(b, i%4, i//4, 1, 1)
        box.append(grid_tags)
        box.append(Gtk.Separator())
        # Instructions
        info = lbl("Le code généré apparaîtra dans la zone de droite. Utilisez les onglets 'Page Enfant' pour la structure globale.", "heading-blue")
        info.set_wrap(True)
        box.append(info)
        return scroll_wrap(box)

    def _insert_html_tag(self, tag):
        def _do(*_):
            current = self.get_code()
            snippet = ""
            if tag == 'img':
                snippet = f'<img src="{{% static \'images/photo.jpg\' %}}" alt="Description" class="img-fluid">'
            elif tag == 'video':
                snippet = f'<video controls width="100%">\n<source src="{{% static \'videos/clip.mp4\' %}}" type="video/mp4">\n</video>'
            elif tag == 'form':
                snippet = f'<form method="post">\n{{% csrf_token %}}\n<!-- Champs ici -->\n<button type="submit">Envoyer</button>\n</form>'
            elif tag == 'input':
                snippet = f'<input type="text" name="champ" class="form-control" placeholder="Saisir...">'
            elif tag == 'table':
                snippet = f'<table class="table">\n<thead>\n<tr><th>Col 1</th><th>Col 2</th></tr>\n</thead>\n<tbody>\n<tr><td>Donnée 1</td><td>Donnée 2</td></tr>\n</tbody>\n</table>'
            elif tag == 'ul':
                snippet = f'<ul>\n<li>Élément 1</li>\n<li>Élément 2</li>\n</ul>'
            elif tag == 'a':
                snippet = f'<a href="{{% url \'home\' %}}" class="btn btn-primary">Lien</a>'
            elif tag == 'button':
                snippet = f'<button type="button" class="btn btn-success">Bouton</button>'
            else:
                snippet = f'<{tag}>\nContenu...\n</{tag}>'
            # Ajouter à la fin ou remplacer si vide
            if not current.strip():
                self.set_code(snippet)
            else:
                self.set_code(current + "\n" + snippet)
        return _do

    def _insert_text(self, text):
        def _do(*_):
            current = self.get_code()
            if not current.strip():
                self.set_code(text)
            else:
                self.set_code(current + "\n" + text)
        return _do

    def _build_js_tab(self):
        box = vbox(8)
        margins(box, 10, 10)
        box.append(lbl("SÉLECTIONNER LES FONCTIONNALITÉS JS À INCLURE", "section-title"))
        box.append(lbl("→ Le code sera généré dans un {% block extra_js %}"))
        self.js_checks = {}
        grid = Gtk.Grid()
        grid.set_column_spacing(8)
        grid.set_row_spacing(4)
        for i, (key, (label, _)) in enumerate(Gen.JS_SNIPPETS.items()):
            chk = Gtk.CheckButton.new_with_label(label)
            chk.connect("toggled", self._gen_js)
            self.js_checks[key] = chk
            grid.attach(chk, i%2, i//2, 1, 1)
        box.append(grid)
        box.append(Gtk.Separator())
        box.append(lbl("→ Résultat copié via le bouton 📋 Copier en haut", "section-title"))
        return scroll_wrap(box)

    def _build_tags_tab(self):
        box = vbox(8)
        margins(box, 10, 10)
        nb2 = Gtk.Notebook()
        # Sous-tab Tags
        tags_box = vbox(4)
        margins(tags_box, 8, 8)
        tags_box.append(lbl("TAGS DJANGO DISPONIBLES — Cliquer pour insérer dans l'aperçu", "section-title"))
        for tag_id, tag_str in Gen.DJANGO_TAGS:
            row = hbox(8)
            row.add_css_class("logic-block")
            row.append(lbl(f"<tt>{tag_str}</tt>"))
            b = btn("📋 Insérer", None, self._insert_text(tag_str))
            b.set_hexpand(False)
            row.append(b)
            tags_box.append(row)
        nb2.append_page(scroll_wrap(tags_box), lbl("Tags"))
        # Sous-tab Filtres
        filters_box = vbox(4)
        margins(filters_box, 8, 8)
        filters_box.append(lbl("FILTRES DJANGO — Utilisation : {{ variable|filtre }}", "section-title"))
        for fid, fdesc in Gen.DJANGO_FILTERS:
            if not fid: continue
            row = hbox(8)
            row.add_css_class("logic-block")
            row.append(lbl(f"<tt>{fid}</tt> — {fdesc}"))
            b = btn("📋 Insérer", None, self._insert_text(fid))
            row.append(b)
            filters_box.append(row)
        nb2.append_page(scroll_wrap(filters_box), lbl("Filtres"))
        # Sous-tab CSS
        css_box = vbox(4)
        margins(css_box, 8, 8)
        css_box.append(lbl("100 PROPRIÉTÉS CSS LES PLUS UTILISÉES", "section-title"))
        grid_css = Gtk.Grid()
        grid_css.set_column_spacing(8)
        grid_css.set_row_spacing(3)
        for i, prop in enumerate(Gen.CSS_PROPERTIES):
            grid_css.attach(lbl(f"<tt>{prop}</tt>"), i%3, i//3, 1, 1)
        css_box.append(grid_css)
        nb2.append_page(scroll_wrap(css_box), lbl("CSS"))
        box.append(nb2)
        return box

    def _copy_tag(self, text):
        def _do(*_):
            clip = Gdk.Display.get_default().get_clipboard()
            clip.set(text)
        return _do

    def _gen_base(self, *_):
        code = Gen.base_html(
            title         = self.e_base_title.get_text() or "MonSite",
            theme_color   = self.e_base_color.get_text() or "#0d3b6e",
            include_chart = self.chk_chart.get_active(),
        )
        self.set_code(code)

    def _gen_child(self, *_):
        code = Gen.child_template(
            name         = self.e_child_name.get_text() or "module",
            base         = self.e_child_base.get_text() or "base.html",
            template_type= self.c_child_type.get_active_id() or "liste",
            model_var    = self.e_child_model_var.get_text() or "objet",
        )
        self.set_code(code)

    def _gen_js(self, *_):
        lines = ["{% block extra_js %}", "<script>",
                 "document.addEventListener('DOMContentLoaded', function() {"]
        for key, chk in self.js_checks.items():
            if chk.get_active():
                _, code = Gen.JS_SNIPPETS[key]
                lines.append(f"\n// {key.upper()}")
                lines.append(code)
        lines += ["});", "</script>", "{% endblock %}"]
        self.set_code('\n'.join(lines))