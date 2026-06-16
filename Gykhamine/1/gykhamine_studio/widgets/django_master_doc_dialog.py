"""Module généré automatiquement depuis widgets.py - Classe DjangoMasterDocDialog"""
"""Module généré automatiquement depuis gy.py"""
import os, sys, re, subprocess, threading, shutil, json, zipfile, csv, tempfile
from pathlib import Path
from datetime import datetime
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk, Pango, GtkSource
from ..config import global_log, DEFAULT_CONFIG, VERSION, set_margins
from ..parser import parse_blocks
from ..ai_engine import BlockAIEngine, AIModificationDialog, LlamaSetupDialog, LogAnalyzerDialog, AICmdGeneratorDialog, GitManagerDialog, BusinessProcessDialog
from ..terminal_tty import NativeTtyTerminal
from ..database import load_config, save_config, memory_record, add_recent_project, get_recent_projects, is_port_in_use, find_free_port, kill_process_on_port, _get_db_path, log_to_file

#  WIDGETS
# ═══════════════════════════════════════════════════════════════════════
TYPE_ICONS = {"import": "📦", "class": "🏛", "function": "⚡", "separator": "─", "comment": "💬", "other": "▪", "template": "🌐", "template_part": "🌐", "django_block": "🧩", "style": "🎨", "style_rule": "🎨", "script": "⚙️", "script_block": "⚡", "c_block": "⚙️"}



class DjangoMasterDocDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="📚 Documentation Master : Django & Python", transient_for=parent, default_width=1200, default_height=800)
        self.add_css_class("rounded-dialog")
        
        # Configuration de la fenêtre principale
        content_area = self.get_content_area()
        content_area.set_spacing(0)
        
        # Layout Principal : Sidebar (Gauche) + Contenu (Droite)
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.set_hexpand(True)
        main_box.set_vexpand(True)
        
        # 1. SIDEBAR DE NAVIGATION & RECHERCHE
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar.set_size_request(320, -1)
        sidebar.add_css_class("sidebar-bg") # Fond sombre
        
        # Barre de recherche
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        search_box.set_margin_start(10)
        search_box.set_margin_end(10)
        search_box.set_margin_top(10)
        search_box.set_margin_bottom(10)
        
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("🔍 Rechercher un concept...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("changed", self._on_search_changed)
        search_box.append(self.search_entry)
        sidebar.append(search_box)
        
        # Liste de navigation
        scroll_sidebar = Gtk.ScrolledWindow()
        scroll_sidebar.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll_sidebar.set_vexpand(True)
        
        self.nav_listbox = Gtk.ListBox()
        self.nav_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.nav_listbox.connect("row-selected", self._on_nav_selected)
        scroll_sidebar.set_child(self.nav_listbox)
        sidebar.append(scroll_sidebar)
        
        # 2. ZONE DE CONTENU PRINCIPAL
        content_stack = Gtk.Stack()
        content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        content_stack.set_hexpand(True)
        content_stack.set_vexpand(True)
        
        scroll_content = Gtk.ScrolledWindow()
        scroll_content.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll_content.set_vexpand(True)
        scroll_content.set_hexpand(True)
        
        self.content_view = GtkSource.View()
        self.content_view.set_editable(False)
        self.content_view.set_cursor_visible(False)
        self.content_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.content_view.set_monospace(False)
        self.content_view.set_show_line_numbers(False)
        self.content_view.add_css_class("code-editor")
        self.content_view.set_margin_start(30)
        self.content_view.set_margin_end(30)
        self.content_view.set_margin_top(30)
        self.content_view.set_margin_bottom(30)
        
        scroll_content.set_child(self.content_view)
        content_stack.add_named(scroll_content, "main")
        
        main_box.append(sidebar)
        main_box.append(content_stack)
        
        # Pied de page
        footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        footer_box.set_margin_start(16)
        footer_box.set_margin_end(16)
        footer_box.set_margin_top(8)
        footer_box.set_margin_bottom(8)
        
        btn_close = Gtk.Button(label="Fermer")
        btn_close.connect("clicked", lambda *_: self.destroy())
        btn_close.set_halign(Gtk.Align.END)
        footer_box.append(btn_close)
        
        content_area.append(main_box)
        content_area.append(Gtk.Separator())
        content_area.append(footer_box)
        
        # Initialisation des données exhaustives
        self.doc_data = self._generate_exhaustive_content()
        self.all_items = [] # Pour la recherche
        self._populate_sidebar()
        
        # Sélectionner le premier élément par défaut
        first_row = self.nav_listbox.get_row_at_index(0)
        if first_row:
            self.nav_listbox.select_row(first_row)

    def _on_search_changed(self, entry):
        query = entry.get_text().lower().strip()
        # Vider la liste actuelle
        while child := self.nav_listbox.get_first_child():
            self.nav_listbox.remove(child)
            
        if not query:
            # Restaurer la liste complète
            for item in self.all_items:
                self.nav_listbox.append(item['row'])
        else:
            # Filtrer par titre ou mots-clés
            for item in self.all_items:
                if query in item['keywords'] or query in item['title'].lower():
                    self.nav_listbox.append(item['row'])

    def _on_nav_selected(self, listbox, row):
        if row and hasattr(row, "_content_key"):
            key = row._content_key
            if key in self.doc_data:
                self._display_content(self.doc_data[key])
            else:
                self._display_content(f"Erreur: Contenu introuvable pour la section '{key}'")

    def _display_content(self, text_content):
        """Affiche le contenu dans le TextView en préservant le formatage simple."""
        buf = self.content_view.get_buffer()
        buf.set_text(text_content)

    def _populate_sidebar(self):
        categories = [
            ("intro", "1. Les Bases (Py, C++, JS, CSS, HTML)", "python cpp js html css base syntaxe"),
            ("mvt", "2. Architecture MVT", "model view template architecture mvc django"),
            ("project_app", "3. Structure Projet & App", "startproject startapp settings urls wsgi asgi installed_apps"),
            ("manage", "4. Manage.py & Migrations", "makemigrations migrate createsuperuser collectstatic shell dumpdata loaddata"),
            ("models", "5. Les Modèles Django", "database orm class model schema table meta on_delete"),
            ("fields", "6. Liste des Fields (Copiable)", "charfield textfield integer boolean foreignkey manytomany uuid email url file image"),
            ("field_opts", "7. Options des Champs", "null blank default unique choices verbose_name help_text"),
            ("model_methods", "8. Astuces Pro Modèles", "save delete str property get_absolute_url clean signals"),
            ("views", "9. Les Vues (FBV & CBV)", "function based class based listview detailview createview updateview request response"),
            ("decorators", "10. Décorateurs Django", "login_required permission_required csrf_exempt cache require_post"),
            ("view_cases", "11. Cas GET/POST/Fichier", "method post get file upload form data"),
            ("responses", "12. Types de Réponses", "httpresponse jsonresponse redirect fileresponse streaming render"),
            ("forms", "13. Les Formulaires", "form modelform clean validation widget formset csrf"),
            ("form_model", "14. Lien Model-Form-Template", "connection link bridge save commit instance"),
            ("form_tips", "15. Astuces Pro Forms", "clean_field initial help_text error_messages"),
            ("templates", "16. Les Templates", "html jinja inheritance block include extends"),
            ("tags", "17. Tags Django & Utilité", "url static csrf if for loop empty load"),
            ("template_logic", "18. Logique Template", "condition boucle filter date length slice truncate"),
            ("filters", "22. Filtres ORM Avancés", "icontains startswith gt lt range in isnull year lookup"),
            ("static_media", "19. Fichiers Statiques & Média", "staticfiles media upload image filefield storage"),
            ("orm", "20. L'ORM Django (Requêtes)", "queryset filter exclude get all order_by count aggregate q object"),
            ("orm_methods", "21. Méthodes Récupération/Soumission", "create update delete bulk_create select_related prefetch_related"),
            ("postgresql", "23. Gestion PostgreSQL", "engine config psycopg2 backup pg_dump production wal"),
            ("sqlite", "24. Gestion SQLite", "wal mode optimization backup pragma dev"),
            ("security", "25. Sécurité & Auth", "csrf xss sql injection login_required permission user group password hash"),
            ("cookies", "26. Cookies & Sessions", "cookie session signed_cookie request.session"),
            ("encryption", "27. Chiffrement & SSL", "hash password argon2 bcrypt fernet symmetric signing token ssl tls"),
            ("js_ajax", "28. JS & AJAX", "fetch api json async await promise"),
            ("browser_api", "29. API Navigateur", "camera microphone geolocation filesystem clipboard"),
            ("api_drf", "30. API REST Framework", "serializer viewset router jwt token authentication permission cors"),
            ("channels", "31. Django Channels", "websocket asgi consumer redis real-time chat"),
            ("celery", "32. Celery (Async)", "task queue broker redis rabbitmq background email"),
            ("nginx_gunicorn", "33. Nginx & Gunicorn", "proxy_pass upstream worker ssl certificate systemd service"),
            ("gunicorn_opts", "34. Options CMD Gunicorn", "workers threads bind timeout preload max_requests log"),
            ("production", "35. Standards Production", "debug false allowed_hosts secret_key environment logging cache redis"),
            ("deploy", "36. Déploiement Gykhamine", "gunicorn nginx ssl systemd deploy production studio"),
            ("tips", "37. Astuces & Bonnes Pratiques", "performance n+1 query only defer exists count test debug toolbar"),
        ]
        
        for key, title, keywords in categories:
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label=title, xalign=0)
            label.set_margin_start(10)
            label.set_margin_top(8)
            label.set_margin_bottom(8)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            row.set_child(label)
            row._content_key = key
            
            self.all_items.append({
                'row': row,
                'title': title,
                'keywords': keywords
            })
            self.nav_listbox.append(row)

    def _generate_exhaustive_content(self):
        data = {}
        
        # --- Helpers for formatting ---
        def fmt_title(t):
            return f"\n{'='*60}\n{t.upper()}\n{'='*60}\n"
        
        def fmt_subtitle(t):
            return f"\n--- {t} ---\n"
        
        def fmt_code(code):
            return f"\n{code}\n"
            
        def mt(t): return fmt_title(t)
        def st(t): return fmt_subtitle(t)
        def cb(c): return fmt_code(c)

# =====================================================================
        # --- 1. BASES & ARCHITECTURE ---
        # =====================================================================

        data["intro"] = (
            mt("1. Les Bases Fondamentales de la Programmation") +
            "Introduction : Pour maîtriser le web, il faut comprendre comment les langages structurent la logique, les données et l'exécution.\n\n" +
            
            st("Concepts Transversaux (Théorie Multi-Langages)") +
            "• Variables : Espaces mémoire nommés pour stocker une valeur. En C, le type est statique (`int x`); en Python/JS, il est dynamique.\n" +
            "• Conditions : Branchements logiques basés sur des booléens (`if / else`).\n" +
            "• Switch / Match : Structure de contrôle pour tester plusieurs valeurs d'une variable. `switch` en C/JS, `match` depuis Python 3.10.\n" +
            "• Boucles : Répétition d'instructions (`for` pour itérer sur une collection, `while` tant qu'une condition est vraie).\n" +
            "• Fonctions : Blocs de code réutilisables prenant des arguments et retournant un résultat.\n" +
            "• Modules : Découpage du code en plusieurs fichiers pour organiser l'application.\n" +
            "• Exceptions : Capture et gestion des erreurs d'exécution pour éviter le crash du programme (`try / except / catch`).\n" +
            "• Classes (POO) : Modèles (Blueprints) permettant de créer des objets regroupant états (attributs) et comportements (méthodes).\n" +
            "• Décorateurs : Fonctions qui enveloppent et modifient le comportement d'une autre fonction ou classe sans modifier son code source.\n\n" +
            
            st("Le Langage C (Le Bas-Niveau & Gestion Mémoire)") +
            "Pourquoi : Comprendre la compilation, les pointeurs, et la gestion stricte des types.\n" +
            cb("#include <stdio.h>\nint main() {\n    int age = 20;\n    if (age >= 18) {\n        printf(\"Majeur\\n\");\n    }\n    return 0;\n}") + "\n\n" +
            
            st("Python (La Logique Backend)") +
            "Pourquoi : Syntaxe épurée, typage dynamique fort, cœur de Django.\n" +
            cb("def verifier_statut(user_role):\n    match user_role:\n        case 'admin': return 'Accès total'\n        case 'client': return 'Accès restreint'\n        case _: raise ValueError('Rôle inconnu')") + "\n\n" +
            
            st("Le Trio Frontend : HTML5 / CSS3 / JavaScript (ES6+)") +
            "• HTML5 : Structure sémantique du DOM.\n" +
            cb("<div id='app'>\n    <h1>Mon Titre</h1>\n    <p class='text'>Texte synchrone</p>\n</div>") + "\n" +
            "• CSS3 : Mise en page (Flexbox, Grid) et design système.\n" +
            cb(".text { color: #2c3e50; font-family: sans-serif; display: flex; }") + "\n" +
            "• JavaScript : Asynchronisme (Promises, Async/Await), manipulation dynamique du DOM.\n" +
            cb("const fetchData = async () => {\n    try {\n        const res = await fetch('/api/data');\n        const data = await res.json();\n        console.log(data);\n    } catch (err) {\n        console.error(err);\n    }\n};")
        )

        data["mvt"] = (
            mt("2. Architecture MVT") +
            "Description : Model-View-Template. Séparation stricte des responsabilités.\n" +
            "Pourquoi : Rend l'application modulaire, scalable et facilement maintenable.\n" +
            "Quand : L'architecture structurelle de référence pour toute application Django.\n" +
            "Comment :\n" +
            "• Model (Données) : Couche d'abstraction (ORM) au-dessus de la base SQL. Gère les contraintes et validations physiques.\n" +
            "• View (Logique métier) : Intercepte la requête HTTP, orchestre l'accès aux données via les modèles, applique la logique de contrôle et retourne une réponse.\n" +
            "• Template (Présentation) : Génère dynamiquement le HTML côté serveur en fusionnant le squelette d'affichage avec les données fournies par la vue."
        )

        data["project_app"] = (
            mt("3. Structure Projet & App") +
            "Description : Architecture modulaire d'un écosystème Django.\n" +
            "Pourquoi : Un projet regroupe les configurations globales (settings, urls, wsgi), tandis qu'une application est un module métier isolé et réutilisable.\n\n" +
            st("Création du Projet et de l'Application") +
            cb("django-admin startproject core_project .\npython manage.py startapp gestion_clinique") + "\n\n" +
            st("Enregistrement Strict (settings.py)") +
            cb("# settings.py\nINSTALLED_APPS = [\n    'django.contrib.admin',\n    'django.contrib.auth',\n    'django.contrib.contenttypes',\n    'django.contrib.sessions',\n    'django.contrib.messages',\n    'django.contrib.staticfiles',\n    # Apps locales autonomes\n    'gestion_clinique.apps.GestionCliniqueConfig',\n]")
        )

        data["manage"] = (
            mt("4. Manage.py & Migrations") +
            "Description : Interface de contrôle en ligne de commande de Django.\n" +
            "Pourquoi : Synchroniser l'état du code source des modèles avec le schéma physique SQL.\n\n" +
            st("Commandes Essentielles et Cycle de Vie") +
            cb("python manage.py makemigrations  # Inspecte les modèles et crée les fichiers d'instructions de migration") + "\n" +
            cb("python manage.py migrate         # Exécute de manière transactionnelle les migrations en base") + "\n" +
            cb("python manage.py createsuperuser # Instancie un utilisateur avec is_staff et is_superuser à True") + "\n" +
            cb("python manage.py collectstatic   # Rassemble les assets statiques dans STATIC_ROOT pour Gunicorn/Nginx") + "\n" +
            cb("python manage.py shell           # Initialise un interpréteur interactif Python configuré avec l'ORM") + "\n" +
            cb("python manage.py dumpdata > data.json # Sérialise la base de données courante dans un fichier JSON")
        )

        # =====================================================================
        # --- 2. MODÈLES & DONNÉES ---
        # =====================================================================

        data["models"] = (
            mt("5. Les Modèles Django & ORM") +
            "Description : Déclaration de la structure des données sous forme de classes Python pures.\n" +
            "Pourquoi : Abstraction SQL totale, typage fort des colonnes, indexation automatique et sécurité native contre les injections SQL.\n\n" +
            st("Exemple Industriel Complet") +
            cb("from django.db import models\nfrom django.contrib.auth.models import User\n\nclass Categorie(models.Model):\n    nom = models.CharField(max_length=100, unique=True)\n\nclass Article(models.Model):\n    STATUT_CHOICES = [('brouillon', 'Brouillon'), ('publie', 'Publié')]\n    \n    titre = models.CharField(max_length=200)\n    slug = models.SlugField(unique=True, max_length=255)\n    contenu = models.TextField()\n    auteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='articles')\n    categorie = models.ForeignKey(Categorie, on_delete=models.PROTECT, null=True, blank=True)\n    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='brouillon')\n    publie = models.BooleanField(default=False)\n    date_creation = models.DateTimeField(auto_now_add=True)\n    date_modification = models.DateTimeField(auto_now=True)\n\n    class Meta:\n        ordering = ['-date_creation']\n        indexes = [\n            models.Index(fields=['slug']),\n            models.Index(fields=['statut']),\n        ]\n\n    def __str__(self):\n        return self.titre") + "\n\n" +
            st("Comportements d'Intégrité Référentielle (on_delete)") +
            "• models.CASCADE : Supprime automatiquement les enregistrements dépendants si le parent est détruit.\n" +
            "• models.PROTECT : Lève une `ProtectedError` pour interdire la suppression du parent tant qu'un enfant y est lié.\n" +
            "• models.SET_NULL : Remplace la clé par `NULL`. Requiert impérativement `null=True` sur le champ."
        )

        data["fields"] = (
            mt("6. Liste des Fields Django (Copiable)") +
            "Description : Dictionnaire exhaustif des types de champs pour l'implémentation de modèles.\n\n" +
            cb("models.CharField(max_length=100)       # Varchar SQL standard") + "\n" +
            cb("models.TextField()                     # Text ou LongText SQL pour blocs longs") + "\n" +
            cb("models.IntegerField()                  # Entier signé standard") + "\n" +
            cb("models.FloatField()                    # Nombre à virgule flottante double précision") + "\n" +
            cb("models.DecimalField(max_digits=10, decimal_places=2) # Précision exacte (monétaire)") + "\n" +
            cb("models.BooleanField(default=False)     # Booléen (TinyInt ou Boolean SQL)") + "\n" +
            cb("models.DateField()                     # Date brute (sans heure)") + "\n" +
            cb("models.DateTimeField()                 # Horodatage précis avec timezone") + "\n" +
            cb("models.EmailField()                    # CharField validé par expression régulière email") + "\n" +
            cb("models.URLField()                      # CharField validé par expression régulière URL") + "\n" +
            cb("models.FileField(upload_to='docs/')    # Stocke le chemin du fichier, gère l'upload") + "\n" +
            cb("models.ImageField(upload_to='imgs/')   # FileField avec validation d'intégrité graphique (Pillow)") + "\n" +
            cb("models.ForeignKey('Model', on_delete=models.CASCADE) # Relation 1-à-N") + "\n" +
            cb("models.ManyToManyField('Model')   # Relation N-à-N avec table de jointure automatique") + "\n" +
            cb("models.OneToOneField('Model', on_delete=models.CASCADE) # Relation unique 1-à-1 (extension de table)") + "\n" +
            cb("models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False) # UUID4 unique")
        )

        data["field_opts"] = (
            mt("7. Options des Champs") +
            "Description : Paramètres modifiant le comportement physique (base de données) ou applicatif (formulaires) des champs.\n" +
            "Comment :\n" +
            "• null=True : Impact physique. Autorise la valeur `NULL` au niveau des colonnes de la base de données.\n" +
            "• blank=True : Impact applicatif. Autorise la soumission d'une valeur vide lors de la validation des formulaires.\n" +
            "• default=valeur : Attribue une valeur par défaut automatique si aucune valeur n'est passée à l'instanciation.\n" +
            "• unique=True : Génère une contrainte d'unicité SQL UNIQUE sur la colonne concernée.\n" +
            "• choices=[...] : Limite les choix possibles dans l'interface d'administration et valide la valeur soumise.\n" +
            "• verbose_name='...' : Définit un libellé lisible et propre pour l'interface utilisateur et la génération des formulaires."
        )

        data["model_methods"] = (
            mt("8. Logique Métier dans les Modèles (Pourquoi & Comment)") +
            "Pourquoi : Respecter le paradigme 'Fat Models, Skinny Views'. Centraliser la logique interne des données directement dans le modèle évite la duplication de code et garantit la cohérence du système.\n\n" +
            st("Implémentation Pratique") +
            cb("from django.db import models\nfrom django.utils.text import slugify\nfrom django.urls import reverse\n\nclass Produit(models.Model):\n    nom = models.CharField(max_length=150)\n    slug = models.SlugField(unique=True, blank=True)\n    prix_ht = models.DecimalField(max_digits=10, decimal_places=2)\n    taux_tva = models.DecimalField(max_digits=4, decimal_places=2, default=0.20)\n\n    # Pourquoi : Calculer dynamiquement sans stocker une valeur redondante en base\n    @property\n    def prix_ttc(self):\n        return self.prix_ht * (1 + self.taux_tva)\n\n    # Pourquoi : Permettre à Django de connaître l'URL absolue canonique de cet objet\n    def get_absolute_url(self):\n        return reverse('produit-detail', kwargs={'slug': self.slug})\n\n    # Pourquoi : Intercepter la sauvegarde pour automatiser des actions de nettoyage/calcul\n    def save(self, *args, **kwargs):\n        if not self.slug:\n            self.slug = slugify(self.nom)\n        super().save(*args, **kwargs) # Important : exécuter le comportement natif de sauvegarde")
        )

        # =====================================================================
        # --- 3. VUES & LOGIQUE ---
        # =====================================================================

        data["views"] = (
            mt("9. Routage et Traitement : GET, GET avec arguments, et POST") +
            "Description : Structure universelle permettant d'aiguiller et de traiter les requêtes HTTP selon leur verbe et leurs paramètres.\n\n" +
            st("Exemple Exhaustif en Function Based View (FBV)") +
            cb("from django.shortcuts import render, get_object_or_404, redirect\nfrom django.http import HttpResponseNotAllowed\nfrom .models import Article\nfrom .forms import ArticleForm\n\ndef gestion_article_view(request, article_id=None):\n    # 1. Cas GET avec Argument (Lecture d'un objet spécifique)\n    if request.method == 'GET' and article_id:\n        article = get_object_or_404(Article, id=article_id)\n        return render(request, 'detail.html', {'article': article})\n        \n    # 2. Cas GET Simple (Affichage d'un formulaire vide ou d'une liste)\n    elif request.method == 'GET':\n        form = ArticleForm()\n        articles = Article.objects.all()\n        return render(request, 'index.html', {'form': form, 'articles': articles})\n        \n    # 3. Cas POST (Soumission et écriture en base de données)\n    elif request.method == 'POST':\n        form = ArticleForm(request.POST, request.FILES)\n        if form.is_valid():\n            article = form.save()\n            return redirect('article-detail', article_id=article.id)\n        return render(request, 'index.html', {'form': form})\n        \n    else:\n        return HttpResponseNotAllowed(['GET', 'POST'])")
        )

        data["decorators"] = (
            mt("10. Décorateurs et Mixins dans les Class Based Views (CBV)") +
            "Description : Application de middleware et contrôles de sécurité sur des structures de classes.\n" +
            "Comment : Comme les CBV ne sont pas des fonctions directes, on applique les décorateurs via `method_decorator` sur la méthode `dispatch` de la classe, ou on hérite directement de structures de Mixins sécurisées.\n\n" +
            st("Exemple Pratique et Propre") +
            cb("from django.views.generic import ListView, CreateView\nfrom django.utils.method_decorator import method_decorator\nfrom django.contrib.auth.decorators import login_required, permission_required\nfrom django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin\nfrom .models import Article\n\n# Approche 1 : Utilisation des Mixins d'héritage (Recommandé en CBV)\nclass ArticleSecureCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):\n    model = Article\n    fields = ['titre', 'contenu']\n    template_name = 'form.html'\n    login_url = '/login/'\n    permission_required = 'gestion_clinique.add_article'\n\n# Approche 2 : Utilisation des décorateurs classiques via method_decorator\n@method_decorator(login_required, name='dispatch')\n@method_decorator(permission_required('gestion_clinique.view_article', raise_exception=True), name='dispatch')\nclass ArticleDashboardListView(ListView):\n    model = Article\n    template_name = 'dashboard.html'\n    context_object_name = 'articles'")
        )

        data["view_cases"] = (
            mt("11. Gestion Unifiée des Flux HTTP") +
            "Description : Traitement distinct des cycles de vie des requêtes.\n" +
            "Principe : Une requête POST doit systématiquement être suivie d'une redirection (Pattern PRG : Post/Redirect/Get) afin d'éviter la resoumission accidentelle de formulaires en cas de rafraîchissement de la page par l'utilisateur."
        )

        data["responses"] = (
            mt("12. Liste Complète des Réponses HTTP Django") +
            "Description : Structures de retour serveur normalisées selon le protocole HTTP.\n\n" +
            st("1. Render (Génération HTML)") +
            cb("from django.shortcuts import render\nreturn render(request, 'template.html', {'data': context})") + "\n\n" +
            st("2. Redirect (Redirection HTTP 302/301)") +
            cb("from django.shortcuts import redirect\nreturn redirect('nom-url-pattern', id=obj.id)") + "\n\n" +
            st("3. JsonResponse (Payload pour API Rest ou AJAX)") +
            cb("from django.http import JsonResponse\nreturn JsonResponse({'status': 'success', 'code': 200, 'payload': []}, safe=True)") + "\n\n" +
            st("4. FileResponse (Streaming de fichiers binaires)") +
            cb("from django.http import FileResponse\nfile = open('rapport.pdf', 'rb')\nreturn FileResponse(file, as_attachment=True, filename='export.pdf')") + "\n\n" +
            st("5. Http404 (Lancement d'une exception de page non trouvée)") +
            cb("from django.http import Http404\nraise Http404('La ressource demandée n'existe pas')")
        )

        # =====================================================================
        # --- 4. FORMULAIRES ---
        # =====================================================================

        data["forms"] = (
            mt("13. Validation & Nettoyage avec les Formulaires") +
            "Description : Structure assurant l'étanchéité applicative entre les données utilisateur entrantes et le backend Python.\n\n" +
            st("Exemple Complet et Métier") +
            cb("from django import forms\nfrom .models import Article\n\nclass ArticleForm(forms.ModelForm):\n    class Meta:\n        model = Article\n        fields = ['titre', 'contenu', 'slug']\n        widgets = {\n            'titre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Entrez le titre'}),\n            'contenu': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),\n        }\n\n    # Pourquoi : Valider et nettoyer un champ spécifique de manière isolée\n    def clean_titre(self):\n        titre = self.cleaned_data.get('titre')\n        if \"interdit\" in titre.lower():\n            raise forms.ValidationError(\"Le titre contient un mot non autorisé.\")\n        return titre\n\n    # Pourquoi : Validation globale croisée mettant en relation plusieurs champs\n    def clean(self):\n        cleaned_data = super().clean()\n        titre = cleaned_data.get('titre')\n        slug = cleaned_data.get('slug')\n        if titre and slug and slug == titre:\n            raise forms.ValidationError(\"Le slug ne peut pas être strictement identique au titre.\")\n        return cleaned_data")
        )

        data["form_model"] = (
            mt("14. Surcharge des Méthodes de Validation Formulaires") +
            "Pourquoi : Permet d'injecter des règles de validation complexes métier (Vérification de doublons, nettoyage de balises HTML malveillantes) avant la persistance en base de données.\n" +
            "• clean_<champ>() : S'exécute en premier, renvoie la valeur nettoyée stockée dans `cleaned_data`.\n" +
            "• clean() : S'exécute en second, idéal pour comparer des champs dépendants (ex: validation et confirmation de mot de passe)."
        )

        data["form_tips"] = (
            mt("15. Gestion des Erreurs complexes") +
            "Description : Renvoyer des messages d'erreurs clairs via `raise forms.ValidationError()` directement interceptés par le dictionnaire d'erreurs du template frontend."
        )

        # =====================================================================
        # --- 5. TEMPLATES & FRONTEND ---
        # =====================================================================

        data["templates"] = (
            mt("16. Le Moteur de Templates Django") +
            "Description : Système d'affichage découplant l'interface de la logique."
        )

        data["tags"] = (
            mt("17. Liste Exhaustive des Balises (Tags) Django Built-in") +
            "Description : Instructions logiques interprétées côté serveur lors du rendu HTML.\n\n" +
            "• `{% url 'route' %}` : Résout de manière dynamique le pattern d'URL nommé.\n" +
            "• `{% static 'path' %}` : Génère l'URL absolue vers un asset statique configuré.\n" +
            "• `{% csrf_token %}` : Génère un input caché contenant le jeton de sécurité anti-CSRF.\n" +
            "• `{% extends 'base.html' %}` : Déclare le squelette HTML parent à hériter.\n" +
            "• `{% block nom %} ... {% endblock %}` : Zone d'injection de contenu dynamique.\n" +
            "• `{% if condition %} ... {% elif %} ... {% else %} ... {% endif %}` : Structure conditionnelle.\n" +
            "• `{% for item in liste %} ... {% empty %} ... {% endfor %}` : Boucle d'itération avec fallback adaptatif si la liste est vide.\n" +
            "• `{% include 'chemin/template.html' %}` : Inclut un fragment de template isolé.\n" +
            "• `{% with var=long_var.attr %} ... {% endwith %}` : Assigne une variable locale pour optimiser l'accès.\n" +
            "• `{% load static %}` : Charge un package de balises ou filtres personnalisés dans le scope courant."
        )

        data["template_logic"] = (
            mt("18. Logique Avancée & Filtres") +
            "Description : Traitement visuel direct des variables de contexte.\n\n" +
            cb("{% if user.is_authenticated %}\n    <p>Bienvenue {{ user.username|upper }}</p>\n{% endif %}")
        )

        data["filters"] = (
            mt("22. Liste Exhaustive des Filtres Django Intégrés") +
            "Description : Modificateurs de variables appliqués à l'aide d'un caractère pipe `|`.\n\n" +
            "• `{{ var|upper }}` : Transforme la chaîne en majuscules.\n" +
            "• `{{ var|lower }}` : Transforme la chaîne en minuscules.\n" +
            "• `{{ var|capfirst }}` : Capitalise la première lettre de la chaîne.\n" +
            "• `{{ var|truncatewords:20 }}` : Tronque une chaîne après X mots.\n" +
            "• `{{ var|truncatechars:50 }}` : Tronque une chaîne après X caractères.\n" +
            "• `{{ date_var|date:'d/m/Y H:i' }}` : Formate un objet datetime selon un pattern strict.\n" +
            "• `{{ var|default:'Valeur par défaut' }}` : Fallback si la variable est évaluée à False ou None.\n" +
            "• `{{ liste|length }}` : Retourne la taille de la collection.\n" +
            "• `{{ texte|safe }}` : Désactive l'auto-échappement HTML (Attention aux failles XSS).\n" +
            "• `{{ valeur|add:5 }}` : Ajoute un entier à une valeur numérique.\n" +
            "• `{{ valeur|slugify }}` : Convertit le texte en slug propre (minuscules, tirets, sans accents).\n" +
            "• `{{ liste|join:', ' }}` : Concatène une liste en une chaîne avec séparateur.\n" +
            "• `{{ dict|get_item:key }}` : Extrait une valeur dynamique depuis un dictionnaire (via template filter custom)."
        )

        data["static_media"] = (
            mt("19. Fichiers Statiques & Média") +
            "Configuration de Production (settings.py) :\n" +
            cb("STATIC_URL = '/static/'\nSTATIC_ROOT = BASE_DIR / 'staticfiles'\nMEDIA_URL = '/media/'\nMEDIA_ROOT = BASE_DIR / 'media'")
        )

        # =====================================================================
        # --- 6. ORM & BASE DE DONNÉES ---
        # =====================================================================

        data["orm"] = (
            mt("20. Maîtrise de l'ORM & Optimisations") +
            "Lookups Avancés d'interrogation et de requêtage de base de données :\n" +
            cb("Article.objects.filter(date_creation__year=2026) # Requête ciblée temporelle")
        )

        data["orm_methods"] = (
            mt("21. Méthodes CRUD Fondamentales") +
            "Méthodes de requêtage de l'ORM :\n" +
            "• `.filter()`, `.get()`, `.create()`, `.delete()`, `.bulk_create()`."
        )

        data["postgresql"] = (
            mt("23. Implémentation Rigoureuse de PostgreSQL") +
            "Description : Base de données relationnelle industrielle standard pour Django.\n\n" +
            st("Installation du Driver Natif") +
            cb("pip install psycopg2-binary") + "\n\n" +
            st("Configuration Enterprise (settings.py)") +
            cb("import os\nfrom pathlib import Path\n\nDATABASES = {\n    'default': {\n        'ENGINE': 'django.db.backends.postgresql',\n        'NAME': os.environ.get('DB_NAME', 'gykhamine_db'),\n        'USER': os.environ.get('DB_USER', 'postgres'),\n        'PASSWORD': os.environ.get('DB_PASSWORD', 'secure_pass'),\n        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),\n        'PORT': os.environ.get('DB_PORT', '5432'),\n        'CONN_MAX_AGE': 600, # Persistance des connexions pour optimiser les performances\n    }\n}")
        )

        data["sqlite"] = (
            mt("24. Configuration SQLite avec Optimisations") +
            "Description : Base de données embarquée légère, parfaire pour les tests ou environnements de développement.\n\n" +
            st("Configuration et Mode WAL (Write-Ahead Logging)") +
            cb("DATABASES = {\n    'default': {\n        'ENGINE': 'django.db.backends.sqlite3',\n        'NAME': BASE_DIR / 'db.sqlite3',\n    }\n}\n\n# Optimisation de la concurrence d'écriture (à exécuter via le shell ou à l'initialisation)\n# PRAGMA journal_mode=WAL;")
        )

        # =====================================================================
        # --- 7. SÉCURITÉ & AUTH ---
        # =====================================================================

        data["security"] = (
            mt("25. Durcissement de la Sécurité") +
            "Règles impératives : SSL, Gestion fine des CORS, Middleware de protection."
        )

        data["cookies"] = ( mt("26. Cookies & Sessions") + "Stockage : Gestion des cycles de vie sessions client/serveur." )
        data["encryption"] = ( mt("27. Chiffrement Cryptographique") + "Algorithmes : Pbkdf2/Argon2 pour les mots de passe." )

        # =====================================================================
        # --- 8. AVANCÉ & API ---
        # =====================================================================

        data["js_ajax"] = ( mt("28. JavaScript & AJAX") + "Asynchronisme : Communication asynchrone DOM backend." )

        data["browser_api"] = (
            mt("29. Interactions avec l'API Web du Navigateur") +
            "Description : Connexion directe de l'interface frontend aux capacités matérielles de l'hôte via JavaScript natif.\n\n" +
            st("Exemple d'Intégration Avancée (Géolocalisation & Notification)") +
            cb("const initGeolocAndNotify = () => {\n    if ('geolocation' in navigator) {\n        navigator.geolocation.getCurrentPosition(\n            (position) => {\n                const { latitude, longitude } = position.coords;\n                console.log(`Lat: ${latitude}, Lon: ${longitude}`);\n                \n                // Déclenchement de l'API de Notification du système\n                if (Notification.permission === 'granted') {\n                    new Notification('Position synchronisée !', { body: `Lat: ${latitude}` });\n                } else if (Notification.permission !== 'denied') {\n                    Notification.requestPermission().then(permission => {\n                        if (permission === 'granted') new Notification('Merci !');\n                    });\n                }\n            },\n            (error) => console.error(`Erreur de capture : ${error.message}`),\n            { enableHighAccuracy: true, timeout: 5000 }\n        );\n    }\n};")
        )

        data["api_drf"] = (
            mt("30. Construction d'API REST avec Django Rest Framework (DRF)") +
            "Description : Exposition de endpoints standardisés JSON, sécurisés par jetons d'accès.\n\n" +
            st("Implémentation de l'Écosystème REST") +
            cb("from rest_framework import serializers, viewsets, permissions\nfrom rest_framework_simplejwt.authentication import JWTAuthentication\nfrom .models import Article\n\n# 1. Sérialiseur : Conversion de l'ORM vers JSON complexes et inversement\nclass ArticleSerializer(serializers.ModelSerializer):\n    auteur_name = serializers.CharField(source='auteur.username', read_only=True)\n\n    class Meta:\n        model = Article\n        fields = ['id', 'titre', 'contenu', 'auteur_name', 'statut']\n\n# 2. ViewSet : Contrôleur automatique exposant les routes CRUD standard\nclass ArticleViewSet(viewsets.ModelViewSet):\n    queryset = Article.objects.filter(statut='publie')\n    serializer_class = ArticleSerializer\n    authentication_classes = [JWTAuthentication]\n    permission_classes = [permissions.IsAuthenticatedOrReadOnly]")
        )

        data["channels"] = (
            mt("31. Temps Réel Évolutif avec Django Channels & WebSockets") +
            "Description : Architecture asynchrone permettant de maintenir des connexions persistantes full-duplex temps réel.\n\n" +
            st("Feuille de Route d'Intégration (Roadmap)") +
            "1. Remplacer le serveur d'application synchrone WSGI par ASGI (Daphne / Uvicorn).\n" +
            "2. Configurer une couche de transport (Channel Layer) performante basée sur Redis.\n" +
            "3. Rédiger un système de routage de protocoles (`ProtocolTypeRouter`) dans `asgi.py`.\n" +
            "4. Implémenter des Consumers (l'équivalent asynchrone des vues) pour intercepter le trafic WebSocket.\n\n" +
            st("Code Source Asynchrone Pratique (consumers.py)") +
            cb("import json\nfrom channels.generic.websocket import AsyncWebsocketConsumer\n\nclass NotificationConsumer(AsyncWebsocketConsumer):\n    async def connect(self):\n        self.group_name = 'live_notifications'\n        # Rejoindre le groupe de diffusion de manière asynchrone\n        await self.channel_layer.group_add(self.group_name, self.channel_name)\n        await self.accept()\n\n    async def disconnect(self, close_code):\n        # Quitter le groupe lors de la déconnexion\n        await self.channel_layer.group_discard(self.group_name, self.channel_name)\n\n    async def receive(self, text_data):\n        data = json.loads(text_data)\n        message = data.get('message', '')\n        \n        # Diffuser le message à l'ensemble du groupe\n        await self.channel_layer.group_send(\n            self.group_name,\n            {\n                'type': 'send_notification',\n                'message': message\n            }\n        )\n\n    async def send_notification(self, event):\n        message = event['message']\n        # Envoi physique de la trame au client connecté en WebSocket\n        await self.send(text_data=json.dumps({'notification': message}))")
        )

        data["celery"] = (
            mt("32. Exécution de Tâches Asynchrones & Distribuées via Celery") +
            "Description : Déchargement des traitements lourds et asynchrones en arrière-plan.\n" +
            "Pourquoi : Garantir un temps de réponse instantané au client HTTP (inférieur à 100ms) et déléguer les calculs à des nœuds d'exécution (Workers).\n\n" +
            st("Feuille de Route d'Intégration (Roadmap)") +
            "1. Installer Celery et un broker de messages : `pip install celery redis`.\n" +
            "2. Instancier l'application Celery globale (`celery.py`) connectée à la configuration Django.\n" +
            "3. Configurer l'adresse du broker Redis dans les `settings.py`.\n" +
            "4. Déclarer des tâches isolées via le décorateur `@shared_task`.\n" +
            "5. Démarrer les processus serveurs parallèles : Le serveur Django d'un côté, le Worker Celery de l'autre.\n\n" +
            st("Code Source Opérationnel (tasks.py)") +
            cb("# celery.py (Configuration globale d'instance)\nimport os\nfrom celery import Celery\n\nos.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core_project.settings')\napp = Celery('core_project')\napp.config_from_object('django.conf:settings', namespace='CELERY')\napp.autodiscover_tasks()\n\n# ==================================================\n# tasks.py (Déclaration des tâches métiers)\nfrom celery import shared_task\nimport time\n\n@shared_task\ndef executer_traitement_lourd(patient_id, donnees_medicales):\n    \"\"\"Simule une analyse de données statistiques massives non bloquante\"\"\"\n    time.sleep(10) # Simulation d'un calcul complexe de 10 secondes\n    # Logique d'analyse prédictive ou de calcul de métriques ici...\n    return f\"Analyse terminée pour le patient {patient_id}\"") + "\n\n" +
            st("Appel non bloquant depuis une Vue") +
            cb("# Dans views.py\ndef declencher_calcul_view(request):\n    # L'appel via .delay() pousse la tâche dans Redis et rend la main immédiatement\n    executer_traitement_lourd.delay(patient_id=42, donnees_medicales={})\n    return JsonResponse({'status': 'Tâche envoyée en arrière-plan'})")
        )

        # =====================================================================
        # --- 9. DÉPLOIEMENT & PROD ---
        # =====================================================================

        data["nginx_gunicorn"] = ( mt("33. Nginx & Gunicorn") + "Stack : Reverse proxy Nginx couplé au serveur WSGI Gunicorn." )
        data["gunicorn_opts"] = ( mt("34. Optimisation Gunicorn") + "CMD : Gestion dynamique du nombre de workers et timeout." )
        data["production"] = ( mt("35. Checklist de Production") + "Checklist : Désactivation stricte du mode DEBUG, gestion des clés secrètes." )
        data["deploy"] = ( mt("36. Déploiement Gykhamine Studio") + "DevOps : Industrialisation et gestion automatisée de l'infrastructure." )
        data["tips"] = ( mt("37. Bonnes Pratiques") + "Performance : Optimisation des requêtes SQL et indexation physique." )        
        # Fill remaining keys with placeholder if missing
        for key in ["project_app", "manage", "fields", "field_opts", "model_methods", "views", "decorators", "view_cases", "responses", "forms", "form_model", "form_tips", "templates", "tags", "template_logic", "filters", "static_media", "orm", "orm_methods", "postgresql", "sqlite", "security", "cookies", "encryption", "js_ajax", "browser_api", "api_drf", "channels", "celery", "nginx_gunicorn", "gunicorn_opts", "production", "deploy", "tips"]:
            if key not in data:
                data[key] = fmt_title(key.upper()) + "Documentation détaillée à venir dans cette section."
                
        return data

