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
from ..config import global_log, DEFAULT_CONFIG, VERSION, set_margins, enable_window_controls
from ..parser import parse_blocks
from ..ai_engine import BlockAIEngine, AIModificationDialog, LlamaSetupDialog, LogAnalyzerDialog, AICmdGeneratorDialog, GitManagerDialog, BusinessProcessDialog
from ..terminal_tty import NativeTtyTerminal
from ..database import load_config, save_config, memory_record, add_recent_project, get_recent_projects, is_port_in_use, find_free_port, kill_process_on_port, _get_db_path, log_to_file

# WIDGETS
# ═══════════════════════════════════════════════════════════════════════
TYPE_ICONS = {
    "import": "📦", "class": "🏛", "function": "⚡", "separator": "─", 
    "comment": "💬", "other": "▪", "template": "🌐", "template_part": "🌐", 
    "django_block": "🧩", "style": "🎨", "style_rule": "🎨", "script": "⚙️", 
    "script_block": "⚡", "c_block": "⚙️"
}

class DjangoMasterDocDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="📚 Documentation Master : Django & Python", transient_for=parent, default_width=1280, default_height=860)
        self.add_css_class("rounded-dialog")
        enable_window_controls(self, "📚 Documentation Master : Django & Python")
        
        # Configuration de la fenêtre principale
        content_area = self.get_content_area()
        content_area.set_spacing(0)
        
        # Layout Principal : Sidebar (Gauche, étroite) + Contenu (Droite, plus large)
        main_box = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.set_hexpand(True)
        main_box.set_vexpand(True)
        main_box.set_wide_handle(True)
        # La sidebar de navigation ne doit pas grandir en même temps que la fenêtre ;
        # la zone de contenu (droite) doit rester la plus grande.
        main_box.set_resize_start_child(False)
        main_box.set_shrink_start_child(False)
        main_box.set_resize_end_child(True)
        main_box.set_shrink_end_child(True)
        
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
        
        main_box.set_start_child(sidebar)
        main_box.set_end_child(content_stack)
        main_box.set_position(300)
        
        content_area.append(main_box)
        
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
            cb("#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n\n// Pointeurs : adresses mémoire directes\nint main() {\n    int age = 20;\n    int *ptr = &age;          // ptr pointe vers l'adresse de age\n    printf(\"Valeur : %d\\n\", *ptr);  // Déréférencement : 20\n\n    // Allocation dynamique (à libérer manuellement !)\n    int *tableau = malloc(5 * sizeof(int));\n    for (int i = 0; i < 5; i++) tableau[i] = i * 10;\n    free(tableau);            // OBLIGATOIRE pour éviter les fuites mémoire\n\n    // Struct (équivalent simple d'une classe)\n    struct Personne {\n        char nom[50];\n        int age;\n    };\n    struct Personne p = {\"Alice\", 30};\n    printf(\"%s a %d ans\\n\", p.nom, p.age);\n\n    return 0;\n}") + "\n\n" +
            
            st("Python (La Logique Backend)") +
            "Pourquoi : Syntaxe épurée, typage dynamique fort, cœur de Django.\n" +
            cb("# Typage dynamique : Python déduit le type automatiquement\nnom = \"Alice\"          # str\nage = 30               # int\nscore = 9.8            # float\nactif = True           # bool\n\n# Listes, dictionnaires, ensembles\nfruits = [\"pomme\", \"banane\", \"cerise\"]   # list (ordonné, modifiable)\nconfig = {\"host\": \"localhost\", \"port\": 8000}  # dict (clé-valeur)\nuniques = {1, 2, 3}                      # set (pas de doublons)\n\n# Fonctions\ndef verifier_statut(user_role: str) -> str:\n    match user_role:           # Pattern matching (Python 3.10+)\n        case 'admin':\n            return 'Accès total'\n        case 'client':\n            return 'Accès restreint'\n        case _:\n            raise ValueError(f'Rôle inconnu : {user_role}')\n\n# Classes & POO\nclass Vehicule:\n    def __init__(self, marque: str, vitesse_max: int):\n        self.marque = marque\n        self.vitesse_max = vitesse_max\n\n    def __str__(self):\n        return f\"{self.marque} ({self.vitesse_max} km/h)\"\n\n    @property\n    def est_rapide(self) -> bool:\n        return self.vitesse_max > 200\n\nvoiture = Vehicule(\"Ferrari\", 320)\nprint(voiture)         # Ferrari (320 km/h)\nprint(voiture.est_rapide)  # True\n\n# Compréhensions de listes (très pythonique)\ncarres = [x**2 for x in range(10) if x % 2 == 0]   # [0, 4, 16, 36, 64]\n\n# Gestion d'exceptions\ntry:\n    resultat = 10 / 0\nexcept ZeroDivisionError as e:\n    print(f\"Erreur : {e}\")\nfinally:\n    print(\"Bloc toujours exécuté\")") + "\n\n" +
            
            st("Le Trio Frontend : HTML5 / CSS3 / JavaScript (ES6+)") +
            "• HTML5 : Structure sémantique du DOM.\n" +
            cb("<!-- HTML5 : Structure sémantique -->\n<!DOCTYPE html>\n<html lang=\"fr\">\n<head>\n    <meta charset=\"UTF-8\">\n    <title>Mon App</title>\n    <link rel=\"stylesheet\" href=\"style.css\">\n</head>\n<body>\n    <header>\n        <nav>\n            <a href=\"/\">Accueil</a>\n            <a href=\"/about\">À propos</a>\n        </nav>\n    </header>\n    <main>\n        <article>\n            <h1>Mon Titre</h1>\n            <p class=\"text\">Texte du paragraphe</p>\n        </article>\n    </main>\n    <script src=\"app.js\"></script>\n</body>\n</html>") + "\n" +
            "• CSS3 : Mise en page (Flexbox, Grid) et design système.\n" +
            cb("/* CSS3 : Flexbox & Grid */\n.container {\n    display: flex;\n    justify-content: space-between;\n    align-items: center;\n    gap: 16px;\n}\n\n.grille {\n    display: grid;\n    grid-template-columns: repeat(3, 1fr);\n    gap: 24px;\n}\n\n/* Variables CSS (Custom Properties) */\n:root {\n    --couleur-primaire: #3498db;\n    --rayon: 8px;\n}\n\n.bouton {\n    background-color: var(--couleur-primaire);\n    border-radius: var(--rayon);\n    padding: 12px 24px;\n    transition: opacity 0.3s ease;\n}\n.bouton:hover { opacity: 0.8; }") + "\n" +
            "• JavaScript : Asynchronisme (Promises, Async/Await), manipulation dynamique du DOM.\n" +
            cb("// JavaScript ES6+ : Async/Await, destructuring, modules\nconst fetchData = async (url) => {\n    try {\n        const res = await fetch(url, {\n            method: 'POST',\n            headers: { 'Content-Type': 'application/json' },\n            body: JSON.stringify({ query: 'test' })\n        });\n        if (!res.ok) throw new Error(`HTTP ${res.status}`);\n        const { data, status } = await res.json();   // Destructuring\n        return data;\n    } catch (err) {\n        console.error('Erreur réseau :', err.message);\n    }\n};\n\n// Classes ES6\nclass ApiService {\n    #baseUrl;   // Attribut privé (#)\n    constructor(url) { this.#baseUrl = url; }\n    async get(endpoint) { return fetchData(`${this.#baseUrl}${endpoint}`); }\n}")
        )

        data["mvt"] = (
            mt("2. Architecture MVT") +
            "Description : Model-View-Template. Séparation stricte des responsabilités.\n" +
            "Pourquoi : Rend l'application modulaire, scalable et facilement maintenable.\n" +
            "Quand : L'architecture structurelle de référence pour toute application Django.\n" +
            "Comment :\n" +
            "• Model (Données) : Couche d'abstraction (ORM) au-dessus de la base SQL. Gère les contraintes et validations physiques.\n" +
            "• View (Logique métier) : Intercepte la requête HTTP, orchestre l'accès aux données via les modèles, applique la logique de contrôle et retourne une réponse.\n" +
            "• Template (Présentation) : Génère dynamiquement le HTML côté serveur en fusionnant le squelette d'affichage avec les données fournies par la vue.\n\n" +
            "NAVIGATEUR → Requête HTTP GET /articles/\n" +
            "                    ↓\n" +
            "             urls.py (Routeur)\n" +
            "                    ↓\n" +
            "             views.py (View = Logique métier)\n" +
            "              ↙              ↘\n" +
            "         models.py        templates/\n" +
            "         (Model = BDD)    (Template = HTML)\n" +
            "              ↓\n" +
            "         Réponse HTTP (HTML rendu)\n" +
            "                    ↓\n" +
            "             NAVIGATEUR ← Affichage\n\n" +
            "| Couche | Fichier | Rôle |\n" +
            "| ---|---|---|\n" +
            "| Model | models.py | Structure des données, requêtes SQL via ORM |\n" +
            "| View | views.py | Logique métier, traitement de la requête |\n" +
            "| Template | templates/*.html | Rendu HTML dynamique |\n" +
            "| URL Router | urls.py | Mapping URL → Vue |\n\n" +
            "Règle d'or : Les vues sont minces (skinny views), les modèles sont riches (fat models). La logique métier vit dans le modèle, pas dans la vue."
        )

        data["project_app"] = (
            mt("3. Structure Projet & App") +
            "Description : Architecture modulaire d'un écosystème Django.\n" +
            "Pourquoi : Un projet regroupe les configurations globales (settings, urls, wsgi), tandis qu'une application est un module métier isolé et réutilisable.\n\n" +
            st("Création du Projet et de l'Application") +
            cb("# Créer le projet (le \".\" évite un sous-dossier supplémentaire)\ndjango-admin startproject core_project .\n\n# Créer une application métier\npython manage.py startapp gestion_articles\npython manage.py startapp comptes_utilisateurs") + "\n\n" +
            st("Arborescence Recommandée") +
            cb("mon_projet/\n├── core_project/         ← Configuration globale\n│   ├── settings.py       ← Paramètres (BDD, apps, middleware...)\n│   ├── urls.py           ← Routeur principal\n│   ├── wsgi.py           ← Point d'entrée serveur synchrone\n│   └── asgi.py           ← Point d'entrée serveur asynchrone\n├── gestion_articles/     ← Application métier isolée\n│   ├── models.py         ← Modèles de données\n│   ├── views.py          ← Vues (logique)\n│   ├── urls.py           ← Routes de l'app\n│   ├── forms.py          ← Formulaires\n│   ├── admin.py          ← Enregistrement admin\n│   ├── apps.py           ← Configuration de l'app\n│   ├── tests.py          ← Tests unitaires\n│   └── migrations/       ← Historique des migrations BDD\n├── templates/            ← Templates HTML globaux\n├── static/               ← CSS, JS, images\n├── media/                ← Fichiers uploadés par les utilisateurs\n├── manage.py             ← CLI Django\n└── requirements.txt      ← Dépendances Python") + "\n\n" +
            st("Enregistrement Strict (settings.py)") +
            cb("# settings.py\nINSTALLED_APPS = [\n    # Apps Django natives\n    'django.contrib.admin',\n    'django.contrib.auth',\n    'django.contrib.contenttypes',\n    'django.contrib.sessions',\n    'django.contrib.messages',\n    'django.contrib.staticfiles',\n\n    # Apps tierces\n    'rest_framework',\n    'corsheaders',\n\n    # Tes applications métier (toujours avec AppConfig)\n    'gestion_articles.apps.GestionArticlesConfig',\n    'comptes_utilisateurs.apps.ComptesUtilisateursConfig',\n]") + "\n\n" +
            st("Routage des URLs") +
            cb("# core_project/urls.py (Routeur principal)\nfrom django.contrib import admin\nfrom django.urls import path, include\nfrom django.conf import settings\nfrom django.conf.urls.static import static\n\nurlpatterns = [\n    path('admin/', admin.site.urls),\n    path('articles/', include('gestion_articles.urls')),  # Délégation à l'app\n    path('api/', include('api.urls')),\n] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)\n\n# gestion_articles/urls.py (Routes de l'app)\nfrom django.urls import path\nfrom . import views\n\napp_name = 'articles'   # Namespace pour éviter les conflits de noms\n\nurlpatterns = [\n    path('', views.liste_articles, name='liste'),\n    path('<int:pk>/', views.detail_article, name='detail'),\n    path('creer/', views.creer_article, name='creer'),\n    path('<int:pk>/modifier/', views.modifier_article, name='modifier'),\n    path('<int:pk>/supprimer/', views.supprimer_article, name='supprimer'),\n    path('<slug:slug>/', views.article_par_slug, name='par-slug'),\n]")
        )

        data["manage"] = (
            mt("4. Manage.py & Migrations") +
            "Description : Interface de contrôle en ligne de commande de Django.\n" +
            "Pourquoi : Synchroniser l'état du code source des modèles avec le schéma physique SQL.\n\n" +
            st("Commandes Essentielles et Cycle de Vie") +
            cb("# --- SERVEUR ---\npython manage.py runserver              # Serveur de développement (127.0.0.1:8000)\npython manage.py runserver 0.0.0.0:8080 # Exposé sur tout le réseau, port 8080\n\n# --- MIGRATIONS (cycle de vie BDD) ---\npython manage.py makemigrations         # Détecte les changements dans models.py → crée un fichier de migration\npython manage.py makemigrations articles  # Uniquement pour l'app \"articles\"\npython manage.py migrate                # Applique toutes les migrations en attente en BDD\npython manage.py migrate articles 0003  # Retour à la migration n°3 (rollback)\npython manage.py showmigrations         # Liste toutes les migrations et leur statut (appliquée ou non)\npython manage.py sqlmigrate articles 0001  # Affiche le SQL généré par une migration (très utile pour déboguer)\n\n# --- UTILISATEURS ---\npython manage.py createsuperuser        # Crée un compte admin interactif\n\n# --- SHELL (debug et scripts manuels) ---\npython manage.py shell                  # Shell Python pré-configuré avec Django\npython manage.py shell_plus             # Shell amélioré (nécessite django-extensions)\n\n# --- STATIQUES ---\npython manage.py collectstatic          # Copie tous les assets dans STATIC_ROOT (pour prod)\npython manage.py findstatic mon_fichier.css  # Localise un fichier statique\n\n# --- DONNÉES ---\npython manage.py dumpdata > backup.json  # Exporte toute la BDD en JSON\npython manage.py dumpdata articles > articles.json  # Exporte seulement l'app \"articles\"\npython manage.py loaddata backup.json   # Importe des données depuis un fixture JSON\n\n# --- TESTS ---\npython manage.py test                   # Lance tous les tests\npython manage.py test articles          # Tests de l'app \"articles\"\npython manage.py test articles.tests.ArticleModelTest  # Un test précis") + "\n\n" +
            st("Cycle de Vie d'un Modèle") +
            "1. Modifier models.py → 2. makemigrations → 3. migrate → 4. C'est en BDD\n" +
            "Problème fréquent : Tu as modifié un modèle mais rien ne change ? Tu as oublié `makemigrations` avant `migrate`."
        )

        # =====================================================================
        # --- 2. MODÈLES & DONNÉES ---
        # =====================================================================

        data["models"] = (
            mt("5. Les Modèles Django & ORM") +
            "Description : Déclaration de la structure des données sous forme de classes Python pures.\n" +
            "Pourquoi : Abstraction SQL totale, typage fort des colonnes, indexation automatique et sécurité native contre les injections SQL.\n\n" +
            st("Exemple Industriel Complet") +
            cb("from django.db import models\nfrom django.contrib.auth.models import User\nfrom django.utils.text import slugify\nfrom django.urls import reverse\n\nclass Categorie(models.Model):\n    nom = models.CharField(max_length=100, unique=True)\n    slug = models.SlugField(unique=True, blank=True)\n\n    def save(self, *args, **kwargs):\n        if not self.slug:\n            self.slug = slugify(self.nom)\n        super().save(*args, **kwargs)\n\n    def __str__(self):\n        return self.nom\n\n    class Meta:\n        verbose_name = \"Catégorie\"\n        verbose_name_plural = \"Catégories\"\n        ordering = ['nom']\n\n\nclass Article(models.Model):\n    # --- Choix (Enum Django) ---\n    class Statut(models.TextChoices):\n        BROUILLON = 'brouillon', 'Brouillon'\n        PUBLIE    = 'publie',    'Publié'\n        ARCHIVE   = 'archive',   'Archivé'\n\n    # --- Champs ---\n    titre     = models.CharField(max_length=200)\n    slug      = models.SlugField(unique=True, max_length=255, blank=True)\n    contenu   = models.TextField()\n    resume    = models.CharField(max_length=500, blank=True)\n\n    # --- Relations ---\n    auteur     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='articles')\n    categorie = models.ForeignKey(Categorie, on_delete=models.PROTECT, null=True, blank=True)\n    tags      = models.ManyToManyField('Tag', blank=True, related_name='articles')\n\n    # --- Statut & Flags ---\n    statut    = models.CharField(max_length=10, choices=Statut.choices, default=Statut.BROUILLON)\n    en_vedette = models.BooleanField(default=False)\n\n    # --- Timestamps automatiques ---\n    date_creation    = models.DateTimeField(auto_now_add=True)  # Défini une seule fois à la création\n    date_modification = models.DateTimeField(auto_now=True)     # Mis à jour à chaque save()\n\n    class Meta:\n        ordering = ['-date_creation']       # Tri par défaut : plus récent en premier\n        indexes = [\n            models.Index(fields=['slug']),\n            models.Index(fields=['statut', '-date_creation']),  # Index composite\n        ]\n        verbose_name = \"Article\"\n\n    def __str__(self):\n        return f\"{self.titre} [{self.get_statut_display()}]\"\n\n    def save(self, *args, **kwargs):\n        if not self.slug:\n            self.slug = slugify(self.titre)\n        super().save(*args, **kwargs)\n\n    def get_absolute_url(self): \n        return reverse('articles:detail', kwargs={'slug': self.slug})\n\n    @property\n    def est_publie(self) -> bool:\n        return self.statut == self.Statut.PUBLIE\n\n\n# Comportements on_delete :\n# CASCADE  → Si l'auteur est supprimé, ses articles aussi\n# PROTECT  → Impossible de supprimer la catégorie si des articles y sont liés (lève ProtectedError)\n# SET_NULL → Met auteur=NULL (requiert null=True sur le champ)\n# SET_DEFAULT → Met la valeur par défaut du champ") + "\n\n" +
            st("Comportements d'Intégrité Référentielle (on_delete)") +
            "• models.CASCADE : Supprime automatiquement les enregistrements dépendants si le parent est détruit.\n" +
            "• models.PROTECT : Lève une `ProtectedError` pour interdire la suppression du parent tant qu'un enfant y est lié.\n" +
            "• models.SET_NULL : Remplace la clé par `NULL`. Requiert impérativement `null=True` sur le champ."
        )

        data["fields"] = (
            mt("6. Liste des Fields Django (Copiable)") +
            "Description : Dictionnaire exhaustif des types de champs pour l'implémentation de modèles.\n\n" +
            cb("# Texte\nmodels.CharField(max_length=255)                    # Varchar — texte court, requis max_length\nmodels.TextField()                                  # Text — texte long illimité\nmodels.SlugField(max_length=255, unique=True)       # Varchar slugifié (URL-friendly)\nmodels.EmailField()                                 # CharField avec validation email\nmodels.URLField()                                   # CharField avec validation URL\nmodels.JSONField()                                  # JSON natif (PostgreSQL & SQLite 3.35+)\n\n# Numérique\nmodels.IntegerField()                               # Entier signé standard\nmodels.PositiveIntegerField()                       # Entier positif uniquement\nmodels.BigIntegerField()                            # Grand entier (BigInt SQL)\nmodels.FloatField()                                 # Virgule flottante (imprécis)\nmodels.DecimalField(max_digits=10, decimal_places=2)  # Décimal exact — UTILISER pour l'argent\n\n# Booléen\nmodels.BooleanField(default=False)\n\n# Dates & Heures\nmodels.DateField()                                  # Date brute (YYYY-MM-DD)\nmodels.TimeField()                                  # Heure (HH:MM:SS)\nmodels.DateTimeField()                              # Horodatage complet\nmodels.DateTimeField(auto_now_add=True)             # Défini à la création\nmodels.DateTimeField(auto_now=True)                 # Mis à jour à chaque save()\nmodels.DurationField()                              # Intervalle de temps (timedelta)\n\n# Fichiers\nmodels.FileField(upload_to='documents/%Y/%m/')      # Chemin relatif dans MEDIA_ROOT\nmodels.ImageField(upload_to='images/')              # FileField + validation image (Pillow requis)\n\n# Identifiants\nmodels.AutoField(primary_key=True)                  # int auto-incrémenté (défaut Django)\nmodels.BigAutoField(primary_key=True)               # bigint auto-incrémenté\nmodels.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # UUID4\n\n# Relations\nmodels.ForeignKey('Modele', on_delete=models.CASCADE, related_name='items')  # 1→N\nmodels.OneToOneField('Modele', on_delete=models.CASCADE)                      # 1→1\nmodels.ManyToManyField('Modele', blank=True, related_name='articles')         # N→N")
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
            "• verbose_name='...' : Définit un libellé lisible et propre pour l'interface utilisateur et la génération des formulaires.\n\n" +
            "| Option | Impact | Exemple |\n" +
            "| ---|---|---|\n" +
            "| null=True | Base de données : colonne peut être NULL | models.CharField(null=True) |\n" +
            "| blank=True | Formulaires : champ non obligatoire | models.CharField(blank=True) |\n" +
            "| default=val | Valeur par défaut si non fournie | default='brouillon' |\n" +
            "| unique=True | Contrainte SQL UNIQUE sur la colonne | models.SlugField(unique=True) |\n" +
            "| db_index=True | Crée un index SQL (accélère les recherches) | models.CharField(db_index=True) |\n" +
            "| choices=[...] | Valeurs autorisées (validation + admin) | choices=Statut.choices |\n" +
            "| verbose_name | Libellé affiché dans l'admin | verbose_name=\"Titre de l'article\" |\n" +
            "| help_text | Texte d'aide dans les formulaires | help_text=\"Max 200 caractères\" |\n" +
            "| editable=False | Champ invisible dans les formulaires | editable=False |\n" +
            "| upload_to | Sous-dossier de MEDIA_ROOT | upload_to='docs/%Y/%m/' |\n\n" +
            "Règle critique : `null=True` pour les champs de type relation (ForeignKey) ou texte optionnel, mais pour les `CharField` / `TextField`, préférer `blank=True` sans `null=True` — Django utilise la chaîne vide `\"\"` plutôt que NULL."
        )

        data["model_methods"] = (
            mt("8. Logique Métier dans les Modèles (Pourquoi & Comment)") +
            "Pourquoi : Respecter le paradigme 'Fat Models, Skinny Views'. Centraliser la logique interne des données directement dans le modèle évite la duplication de code et garantit la cohérence du système.\n\n" +
            st("Implémentation Pratique") +
            cb("from django.db import models\nfrom django.utils.text import slugify\nfrom django.urls import reverse\nfrom django.core.exceptions import ValidationError\n\nclass Produit(models.Model):\n    nom = models.CharField(max_length=150)\n    slug = models.SlugField(unique=True, blank=True)\n    prix_ht = models.DecimalField(max_digits=10, decimal_places=2)\n    taux_tva = models.DecimalField(max_digits=4, decimal_places=2, default=0.20)\n    stock = models.PositiveIntegerField(default=0)\n\n    # --- @property : calcul dynamique sans colonne BDD ---\n    @property\n    def prix_ttc(self):\n        \"\"\"Calculé à la volée, jamais stocké.\"\"\"\n        return round(self.prix_ht * (1 + self.taux_tva), 2)\n\n    @property\n    def en_stock(self) -> bool:\n        return self.stock > 0\n\n    # --- get_absolute_url : URL canonique de l'objet ---\n    def get_absolute_url(self):\n        return reverse('produits:detail', kwargs={'slug': self.slug})\n\n    # --- save() : surcharge pour automatiser des actions ---\n    def save(self, *args, **kwargs):\n        if not self.slug:\n            self.slug = slugify(self.nom)\n        super().save(*args, **kwargs)  # Toujours appeler super() !\n\n    # --- clean() : validation personnalisée avant save() ---\n    def clean(self):\n        if self.prix_ht <= 0:\n            raise ValidationError({'prix_ht': \"Le prix doit être positif.\"})\n        if self.taux_tva < 0 or self.taux_tva > 1:\n            raise ValidationError({'taux_tva': \"Le taux TVA doit être entre 0 et 1.\"})\n\n    # --- Signals (dans signals.py, à connecter dans apps.py) ---\n    # from django.db.models.signals import post_save, pre_delete\n    # from django.dispatch import receiver\n    #\n    # @receiver(post_save, sender=Produit)\n    # def notifier_creation(sender, instance, created, **kwargs):\n    #     if created:\n    #         envoyer_email_admin(f\"Nouveau produit : {instance.nom}\")")
        )

        # =====================================================================
        # --- 3. VUES & LOGIQUE ---
        # =====================================================================

        data["views"] = (
            mt("9. Routage et Traitement : GET, GET avec arguments, et POST") +
            "Description : Structure universelle permettant d'aiguiller et de traiter les requêtes HTTP selon leur verbe et leurs paramètres.\n\n" +
            st("Function Based Views (FBV) — Les Plus Explicites") +
            cb("from django.shortcuts import render, get_object_or_404, redirect\nfrom django.contrib.auth.decorators import login_required\nfrom django.http import HttpResponseNotAllowed\nfrom .models import Article\nfrom .forms import ArticleForm\n\ndef liste_articles(request):\n    \"\"\"Vue liste simple — GET uniquement.\"\"\"\n    articles = Article.objects.filter(statut='publie').select_related('auteur', 'categorie')\n    return render(request, 'articles/liste.html', {'articles': articles})\n\ndef detail_article(request, slug):\n    \"\"\"Vue détail avec argument dans l'URL.\"\"\"\n    article = get_object_or_404(Article, slug=slug, statut='publie')\n    return render(request, 'articles/detail.html', {'article': article})\n\n@login_required\ndef creer_article(request):\n    \"\"\"Vue formulaire GET/POST avec pattern PRG.\"\"\"\n    if request.method == 'POST':\n        form = ArticleForm(request.POST, request.FILES)\n        if form.is_valid():\n            article = form.save(commit=False)\n            article.auteur = request.user   # Injecter l'auteur connecté\n            article.save()\n            return redirect('articles:detail', slug=article.slug)  # Redirect après POST !\n    else:\n        form = ArticleForm()\n    return render(request, 'articles/form.html', {'form': form, 'action': 'Créer'})\n\n@login_required\ndef modifier_article(request, pk):\n    \"\"\"Vue modification : GET (pré-remplir) + POST (sauvegarder).\"\"\"\n    article = get_object_or_404(Article, pk=pk, auteur=request.user)  # Vérifier la propriété\n    if request.method == 'POST':\n        form = ArticleForm(request.POST, request.FILES, instance=article)  # instance= pour la MAJ\n        if form.is_valid():\n            form.save()\n            return redirect('articles:detail', slug=article.slug)\n    else:\n        form = ArticleForm(instance=article)\n    return render(request, 'articles/form.html', {'form': form, 'action': 'Modifier'})") + "\n\n" +
            st("Class Based Views (CBV) — Les Plus Puissantes") +
            cb("from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView\nfrom django.contrib.auth.mixins import LoginRequiredMixin\nfrom django.urls import reverse_lazy\n\nclass ArticleListView(ListView):\n    model = Article\n    template_name = 'articles/liste.html'\n    context_object_name = 'articles'  # Nom de la variable dans le template\n    paginate_by = 10                  # Pagination automatique\n\n    def get_queryset(self):           # Surcharger pour filtrer/trier\n        return Article.objects.filter(statut='publie').select_related('auteur')\n\n    def get_context_data(self, **kwargs):  # Ajouter des données au contexte\n        context = super().get_context_data(**kwargs)\n        context['total'] = self.get_queryset().count()\n        return context\n\n\nclass ArticleCreateView(LoginRequiredMixin, CreateView):\n    model = Article\n    fields = ['titre', 'contenu', 'categorie', 'statut']\n    template_name = 'articles/form.html'\n    login_url = '/connexion/'\n\n    def form_valid(self, form):       # Avant save : injecter l'auteur\n        form.instance.auteur = self.request.user\n        return super().form_valid(form)\n\n\nclass ArticleDeleteView(LoginRequiredMixin, DeleteView):\n    model = Article\n    template_name = 'articles/confirmer_suppression.html'\n    success_url = reverse_lazy('articles:liste')  # Redirection après suppression")
        )

        data["decorators"] = (
            mt("10. Décorateurs et Mixins dans les Class Based Views (CBV)") +
            "Description : Application de middleware et contrôles de sécurité sur des structures de classes.\n" +
            "Comment : Comme les CBV ne sont pas des fonctions directes, on applique les décorateurs via `method_decorator` sur la méthode `dispatch` de la classe, ou on hérite directement de structures de Mixins sécurisées.\n\n" +
            st("Exemple Pratique et Propre") +
            cb("from django.contrib.auth.decorators import login_required, permission_required, user_passes_test\nfrom django.views.decorators.http import require_http_methods, require_POST, require_GET\nfrom django.views.decorators.cache import cache_page\nfrom django.views.decorators.csrf import csrf_exempt\n\n# --- Authentification ---\n@login_required(login_url='/connexion/')\ndef vue_privee(request): ...\n\n@permission_required('articles.add_article', raise_exception=True)\ndef creer_article(request): ...\n\n@user_passes_test(lambda u: u.is_staff)\ndef vue_staff(request): ...\n\n# --- Méthodes HTTP ---\n@require_http_methods(['GET', 'POST'])\ndef vue_mixte(request): ...\n\n@require_POST\ndef traiter_formulaire(request): ...\n\n# --- Cache ---\n@cache_page(60 * 15)   # Cache 15 minutes\ndef vue_lente(request): ...\n\n# --- CSRF (API uniquement, dangereux sur vues normales) ---\n@csrf_exempt\ndef webhook_externe(request): ...\n\n# --- Sur les CBV (via method_decorator) ---\nfrom django.utils.decorators import method_decorator\n\n@method_decorator(login_required, name='dispatch')\nclass VueSécurisée(ListView):\n    model = Article\n\n# Ou par héritage de Mixins (recommandé) :\nfrom django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin\n\nclass MaVue(LoginRequiredMixin, PermissionRequiredMixin, ListView):\n    permission_required = 'articles.view_article'")
        )

        data["view_cases"] = (
            mt("11. Gestion Unifiée des Flux HTTP") +
            "Description : Traitement distinct des cycles de vie des requêtes.\n" +
            "Principe : Une requête POST doit systématiquement être suivie d'une redirection (Pattern PRG : Post/Redirect/Get) afin d'éviter la resoumission accidentelle de formulaires en cas de rafraîchissement de la page par l'utilisateur.\n\n" +
            cb("def vue_complete(request):\n    # --- Lire les paramètres GET (filtres, pagination) ---\n    page = request.GET.get('page', 1)\n    search = request.GET.get('q', '')\n\n    # --- Lire les données POST ---\n    if request.method == 'POST':\n        titre = request.POST.get('titre', '').strip()\n        contenu = request.POST.get('contenu', '')\n\n    # --- Gérer l'upload de fichier ---\n    if request.method == 'POST' and request.FILES:\n        fichier = request.FILES.get('document')  # Nom du champ input file\n        if fichier:\n            # Vérifier type & taille\n            if fichier.size > 5 * 1024 * 1024:   # 5 MB max\n                messages.error(request, \"Fichier trop volumineux.\")\n                return redirect('upload')\n            if not fichier.name.endswith(('.pdf', '.docx')):\n                messages.error(request, \"Format non supporté.\")\n                return redirect('upload')\n            # Sauvegarder\n            document = Document(fichier=fichier, nom=fichier.name)\n            document.save()\n\n    # --- Données de session ---\n    request.session['last_visit'] = str(datetime.now())\n    visite = request.session.get('last_visit', 'Jamais')\n\n    # --- Infos utiles sur request ---\n    # request.user          → Utilisateur connecté (ou AnonymousUser)\n    # request.method        → 'GET', 'POST', 'PUT', 'DELETE'\n    # request.path          → '/articles/creer/'\n    # request.META['REMOTE_ADDR']  → IP du client\n    # request.is_ajax()     → Deprecated, utiliser : request.headers.get('X-Requested-With') == 'XMLHttpRequest'\n    # request.content_type  → 'application/json', 'multipart/form-data'...")
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
            cb("from django.http import Http404\nraise Http404('La ressource demandée n'existe pas')") + "\n\n" +
            st("6. HttpResponse (Réponse brute)") +
            cb("return HttpResponse(\"<h1>Hello</h1>\", content_type='text/html', status=200)\nreturn HttpResponse(status=204)  # No Content") + "\n\n" +
            st("7. Codes d'erreur courts") +
            cb("return HttpResponseBadRequest(\"Requête invalide\")   # 400\nreturn HttpResponseForbidden(\"Accès refusé\")        # 403\nreturn HttpResponseNotFound(\"Introuvable\")          # 404\nreturn HttpResponseServerError(\"Erreur serveur\")    # 500")
        )

        # =====================================================================
        # --- 4. FORMULAIRES ---
        # =====================================================================

        data["forms"] = (
            mt("13. Validation & Nettoyage avec les Formulaires") +
            "Description : Structure assurant l'étanchéité applicative entre les données utilisateur entrantes et le backend Python.\n\n" +
            st("Exemple Complet et Métier") +
            cb("from django import forms\nfrom django.core.exceptions import ValidationError\nfrom .models import Article, Categorie\n\nclass ArticleForm(forms.ModelForm):\n    # Champ supplémentaire non lié au modèle\n    confirmer_publication = forms.BooleanField(required=False, label=\"Publier immédiatement\")\n\n    class Meta:\n        model = Article\n        fields = ['titre', 'resume', 'contenu', 'categorie', 'statut']\n        widgets = {\n            'titre': forms.TextInput(attrs={\n                'class': 'form-control',\n                'placeholder': 'Titre de l\\'article',\n                'autofocus': True\n            }),\n            'resume': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),\n            'contenu': forms.Textarea(attrs={'rows': 15, 'class': 'form-control'}),\n            'categorie': forms.Select(attrs={'class': 'form-select'}),\n            'statut': forms.RadioSelect(),\n        }\n        labels = {\n            'titre': 'Titre',\n            'statut': 'État de publication',\n        }\n        error_messages = {\n            'titre': {\n                'required': 'Le titre est obligatoire.',\n                'max_length': 'Le titre ne peut pas dépasser 200 caractères.',\n            }\n        }\n\n    # Validation d'un champ spécifique\n    def clean_titre(self):\n        titre = self.cleaned_data.get('titre', '').strip()\n        if len(titre) < 5:\n            raise ValidationError(\"Le titre doit faire au moins 5 caractères.\")\n        if Article.objects.filter(titre__iexact=titre).exclude(pk=self.instance.pk).exists():\n            raise ValidationError(\"Un article avec ce titre existe déjà.\")\n        return titre  # TOUJOURS retourner la valeur nettoyée\n\n    # Validation globale (plusieurs champs ensemble)\n    def clean(self):\n        cleaned_data = super().clean()\n        statut = cleaned_data.get('statut')\n        confirmer = cleaned_data.get('confirmer_publication')\n\n        if statut == 'publie' and not confirmer:\n            raise ValidationError(\n                \"Cochez la case de confirmation pour publier l'article.\"\n            )\n        return cleaned_data") + "\n\n" +
            st("Formulaire Simple (sans modèle)") +
            cb("class ContactForm(forms.Form):\n    nom    = forms.CharField(max_length=100, label='Votre nom')\n    email  = forms.EmailField(label='Votre email')\n    sujet  = forms.CharField(max_length=200)\n    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))\n\n    def clean_email(self):\n        email = self.cleaned_data['email']\n        if not email.endswith('@gmail.com'):  # Exemple de règle métier\n            raise ValidationError(\"Seuls les emails Gmail sont acceptés.\")\n        return email")
        )

        data["form_model"] = (
            mt("14. Surcharge des Méthodes de Validation Formulaires") +
            "Pourquoi : Permet d'injecter des règles de validation complexes métier (Vérification de doublons, nettoyage de balises HTML malveillantes) avant la persistance en base de données.\n" +
            "• clean_<champ>() : S'exécute en premier, renvoie la valeur nettoyée stockée dans `cleaned_data`.\n" +
            "• clean() : S'exécute en second, idéal pour comparer des champs dépendants (ex: validation et confirmation de mot de passe).\n\n" +
            st("Lien Model-Form-Template (Vue)") +
            cb("@login_required\ndef creer_article(request):\n    if request.method == 'POST':\n        form = ArticleForm(request.POST, request.FILES)\n        if form.is_valid():\n            article = form.save(commit=False)  # commit=False : ne pas encore sauvegarder\n            article.auteur = request.user       # Injecter des données supplémentaires\n            article.save()                      # Sauvegarde réelle\n            form.save_m2m()                     # Sauvegarder les ManyToMany (si commit=False)\n            messages.success(request, f'Article \"{article.titre}\" créé avec succès !')\n            return redirect('articles:detail', slug=article.slug)\n        else:\n            messages.error(request, \"Le formulaire contient des erreurs.\")\n    else:\n        form = ArticleForm(initial={'statut': 'brouillon'})  # Valeur initiale par défaut\n\n    return render(request, 'articles/form.html', {\n        'form': form,\n        'titre_page': 'Créer un article'\n    })") + "\n\n" +
            st("Template (form.html)") +
            cb("{% extends 'base.html' %}\n{% block content %}\n\n<h1>{{ titre_page }}</h1>\n\n<form method=\"post\" enctype=\"multipart/form-data\">  {# enctype OBLIGATOIRE si fichiers #}\n    {% csrf_token %}  {# OBLIGATOIRE pour les formulaires POST #}\n\n    {# Affichage automatique du formulaire #}\n    {{ form.as_div }}\n\n    {# OU champ par champ pour un contrôle total #}\n    <div class=\"mb-3\">\n        <label for=\"{{ form.titre.id_for_label }}\">{{ form.titre.label }}</label>\n        {{ form.titre }}\n        {% if form.titre.errors %}\n            <div class=\"text-danger\">{{ form.titre.errors }}</div>\n        {% endif %}\n        <small>{{ form.titre.help_text }}</small>\n    </div>\n\n    {# Affichage des erreurs globales (non liées à un champ) #}\n    {% if form.non_field_errors %}\n        <div class=\"alert alert-danger\">{{ form.non_field_errors }}</div>\n    {% endif %}\n\n    <button type=\"submit\">Enregistrer</button>\n</form>\n{% endblock %}")
        )

        data["form_tips"] = (
            mt("15. Gestion des Erreurs complexes") +
            "Description : Renvoyer des messages d'erreurs clairs via `raise forms.ValidationError()` directement interceptés par le dictionnaire d'erreurs du template frontend.\n\n" +
            st("Astuces Pro Forms") +
            cb("# --- Pré-remplir un formulaire depuis la BDD ---\narticle = get_object_or_404(Article, pk=pk)\nform = ArticleForm(instance=article)                # Lecture\nform = ArticleForm(request.POST, instance=article)  # Mise à jour\n\n# --- FormSets : plusieurs formulaires du même type ---\nfrom django.forms import modelformset_factory\n\nArticleFormSet = modelformset_factory(Article, fields=['titre', 'statut'], extra=2)\nformset = ArticleFormSet(queryset=Article.objects.filter(auteur=request.user))\n\n# --- Widgets personnalisés ---\nfrom django.forms.widgets import DateInput\ndate_naissance = forms.DateField(\n    widget=DateInput(attrs={'type': 'date', 'class': 'form-control'})\n)\n\n# --- Désactiver un champ (lecture seule) ---\ndef __init__(self, *args, **kwargs):\n    super().__init__(*args, **kwargs)\n    if self.instance.pk:  # En modification seulement\n        self.fields['slug'].disabled = True\n\n# --- Filtrer les choix d'un champ ForeignKey ---\ndef __init__(self, *args, user=None, **kwargs):\n    super().__init__(*args, **kwargs)\n    if user:\n        self.fields['categorie'].queryset = Categorie.objects.filter(actif=True)")
        )

        # =====================================================================
        # --- 5. TEMPLATES & FRONTEND ---
        # =====================================================================

        data["templates"] = (
            mt("16. Le Moteur de Templates Django") +
            "Description : Système d'affichage découplant l'interface de la logique.\n\n" +
            st("base.html — Le Squelette Général") +
            cb("<!DOCTYPE html>\n<html lang=\"fr\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>{% block title %}Mon Site{% endblock %}</title>\n    {% load static %}\n    <link rel=\"stylesheet\" href=\"{% static 'css/style.css' %}\">\n    {% block extra_css %}{% endblock %}\n</head>\n<body>\n    <nav>\n        <a href=\"{% url 'accueil' %}\">Accueil</a>\n        {% if user.is_authenticated %}\n            <span>{{ user.username }}</span>\n            <a href=\"{% url 'deconnexion' %}\">Déconnexion</a>\n        {% else %}\n            <a href=\"{% url 'connexion' %}\">Connexion</a>\n        {% endif %}\n    </nav>\n\n    {% if messages %}\n        {% for message in messages %}\n            <div class=\"alert alert-{{ message.tags }}\">{{ message }}</div>\n        {% endfor %}\n    {% endif %}\n\n    <main>\n        {% block content %}{% endblock %}\n    </main>\n\n    <footer>&copy; {% now \"Y\" %} Mon Site</footer>\n\n    <script src=\"{% static 'js/app.js' %}\"></script>\n    {% block extra_js %}{% endblock %}\n</body>\n</html>") + "\n\n" +
            st("Page Enfant — Héritage") +
            cb("{% extends 'base.html' %}\n{% load static %}\n\n{% block title %}Liste des Articles{% endblock %}\n\n{% block extra_css %}\n    <link rel=\"stylesheet\" href=\"{% static 'css/articles.css' %}\">\n{% endblock %}\n\n{% block content %}\n<h1>Articles</h1>\n\n{% for article in articles %}\n    <article>\n        <h2><a href=\"{{ article.get_absolute_url }}\">{{ article.titre }}</a></h2>\n        <p>Par {{ article.auteur.username }} — {{ article.date_creation|date:\"d/m/Y\" }}</p>\n        <p>{{ article.resume|default:\"Aucun résumé disponible.\" }}</p>\n    </article>\n{% empty %}\n    <p>Aucun article pour l'instant.</p>\n{% endfor %}\n\n{# Pagination #}\n{% if page_obj.has_other_pages %}\n    {% if page_obj.has_previous %}\n        <a href=\"?page={{ page_obj.previous_page_number }}\">← Précédent</a>\n    {% endif %}\n    <span>Page {{ page_obj.number }} / {{ page_obj.paginator.num_pages }}</span>\n    {% if page_obj.has_next %}\n        <a href=\"?page={{ page_obj.next_page_number }}\">Suivant →</a>\n    {% endif %}\n{% endif %}\n{% endblock %}")
        )

        data["tags"] = (
            mt("17. Liste Exhaustive des Balises (Tags) Django Built-in") +
            "Description : Instructions logiques interprétées côté serveur lors du rendu HTML.\n\n" +
            "| Tag | Description | Exemple |\n" +
            "| ---|---|---|\n" +
            "| {% url %} | Génère une URL par nom | {% url 'articles:detail' slug=article.slug %} |\n" +
            "| {% static %} | URL d'un asset statique | {% static 'img/logo.png' %} |\n" +
            "| {% csrf_token %} | Jeton anti-CSRF (formulaires) | <form>{% csrf_token %} |\n" +
            "| {% extends %} | Hérite d'un template parent | {% extends 'base.html' %} |\n" +
            "| {% block %} | Définit une zone remplaçable | {% block content %}...{% endblock %} |\n" +
            "| {% include %} | Inclut un sous-template | {% include 'partials/navbar.html' %} |\n" +
            "| {% if/elif/else %} | Condition | {% if user.is_staff %} |\n" +
            "| {% for/empty %} | Boucle avec fallback | {% for obj in liste %}...{% empty %} |\n" +
            "| {% with %} | Variable locale temporaire | {% with nom=user.first_name %} |\n" +
            "| {% load %} | Charge un ensemble de tags | {% load static %} |\n" +
            "| {% comment %} | Commentaire (invisible en HTML) | {% comment %}Note{% endcomment %} |\n" +
            "| {% now %} | Date/heure actuelle | {% now \"Y\" %} |\n" +
            "| {% verbatim %} | Désactive l'interprétation des templates | {% verbatim %}{{ variable }}{% endverbatim %} |\n\n" +
            st("Variables Loop") +
            cb("{% for article in articles %}\n    {{ forloop.counter }}     {# Numéro de l'itération (commence à 1) #}\n    {{ forloop.counter0 }}    {# Numéro de l'itération (commence à 0) #}\n    {{ forloop.revcounter }}  {# Compte à rebours #}\n    {{ forloop.first }}       {# True si première itération #}\n    {{ forloop.last }}        {# True si dernière itération #}\n    {{ forloop.parentloop }}  {# Référence à la boucle parente (boucles imbriquées) #}\n{% endfor %}")
        )

        data["template_logic"] = (
            mt("18. Logique Avancée & Filtres") +
            "Description : Traitement visuel direct des variables de contexte.\n\n" +
            cb("{% if user.is_authenticated and user.is_staff %}\n    <a href=\"{% url 'admin:index' %}\">Administration</a>\n{% elif user.is_authenticated %}\n    <span>{{ user.username }}</span>\n{% else %}\n    <a href=\"{% url 'connexion' %}\">Se connecter</a>\n{% endif %}\n\n{# Opérateurs disponibles : ==, !=, <, >, <=, >=, in, not in, is, is not #}\n{% if article.statut == \"publie\" and not article.en_vedette %}")
        )

        data["filters"] = (
            mt("22. Liste Exhaustive des Filtres Django Intégrés") +
            "Description : Modificateurs de variables appliqués à l'aide d'un caractère pipe `|`.\n\n" +
            "{# Texte #}\n" +
            "{{ nom|upper }}                     → ALICE\n" +
            "{{ nom|lower }}                     → alice\n" +
            "{{ nom|capfirst }}                  → Alice\n" +
            "{{ nom|title }}                      → Alice Martin\n" +
            "{{ texte|truncatewords:20 }}        → Les 20 premiers mots...\n" +
            "{{ texte|truncatechars:100 }}       → Les 100 premiers caractères...\n" +
            "{{ texte|wordcount }}                → 42\n" +
            "{{ texte|linebreaks }}              → Convertit \\n en <p>\n" +
            "{{ texte|striptags }}               → Retire les balises HTML\n" +
            "{{ texte|safe }}                    → HTML non échappé (attention XSS !)\n" +
            "{{ texte|slugify }}                 → \"Mon Titre\" → \"mon-titre\"\n" +
            "{{ texte|default:\"Valeur par défaut\" }}\n\n" +
            "{# Nombres #}\n" +
            "{{ prix|floatformat:2 }}            → 12.50\n" +
            "{{ valeur|add:5 }}                  → valeur + 5\n\n" +
            "{# Dates #}\n" +
            "{{ date|date:\"d/m/Y\" }}             → 16/06/2026\n" +
            "{{ date|date:\"d M Y à H:i\" }}      → 16 juin 2026 à 14:30\n" +
            "{{ date|timesince }}                → \"3 jours\"\n" +
            "{{ date|timeuntil }}                → \"dans 2 heures\"\n\n" +
            "{# Listes #}\n" +
            "{{ liste|length }}                  → Taille de la liste\n" +
            "{{ liste|first }}                   → Premier élément\n" +
            "{{ liste|last }}                    → Dernier élément\n" +
            "{{ liste|join:\", \" }}               → \"a, b, c\"\n" +
            "{{ liste|slice:\":3\" }}              → Les 3 premiers éléments\n\n" +
            "{# Logique #}\n" +
            "{{ var|yesno:\"Oui,Non,Inconnu\" }}  → Oui/Non/Inconnu selon True/False/None"
        )

        data["static_media"] = (
            mt("19. Fichiers Statiques & Média") +
            "Configuration de Production (settings.py) :\n" +
            cb("# settings.py\n\n# --- Fichiers statiques (CSS, JS, images de l'interface) ---\nSTATIC_URL = '/static/'\nSTATIC_ROOT = BASE_DIR / 'staticfiles'     # Dossier de collecte pour la production\nSTATICFILES_DIRS = [BASE_DIR / 'static']   # Dossiers sources en développement\n\n# --- Fichiers média (uploads utilisateurs) ---\nMEDIA_URL = '/media/'\nMEDIA_ROOT = BASE_DIR / 'media'") + "\n\n" +
            st("Dans les Templates") +
            cb("{# Dans les templates #}\n{% load static %}\n<link rel=\"stylesheet\" href=\"{% static 'css/style.css' %}\">\n<img src=\"{% static 'img/logo.png' %}\" alt=\"Logo\">\n\n{# Afficher un fichier uploadé par un utilisateur #}\n{% if article.image %}\n    <img src=\"{{ article.image.url }}\" alt=\"{{ article.titre }}\">\n{% endif %}") + "\n\n" +
            st("Servir les Médias en Développement (urls.py)") +
            cb("# urls.py — Servir les médias en développement uniquement\nfrom django.conf import settings\nfrom django.conf.urls.static import static\n\nurlpatterns = [\n    ...\n] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)\n# En production, c'est Nginx qui sert les médias.")
        )

        # =====================================================================
        # --- 6. ORM & BASE DE DONNÉES ---
        # =====================================================================

        data["orm"] = (
            mt("20. Maîtrise de l'ORM & Optimisations") +
            "Lookups Avancés d'interrogation et de requêtage de base de données :\n" +
            cb("from .models import Article, Categorie\nfrom django.db.models import Q, Count, Avg, Sum, Max, Min, F\n\n# --- Récupérer des objets ---\ntous = Article.objects.all()                          # Tous les articles (QuerySet lazy)\nun   = Article.objects.get(pk=1)                      # Un seul — lève DoesNotExist si introuvable\nou_404 = get_object_or_404(Article, pk=1)             # Idem mais lève Http404\n\n# --- Filtrer ---\npublies = Article.objects.filter(statut='publie')\nbrouillons = Article.objects.exclude(statut='publie')\n\n# --- Chaîner les filtres (AND implicite) ---\nresultat = Article.objects.filter(\n    statut='publie',\n    auteur__username='alice',           # Traversée de relation (__)\n    date_creation__year=2026,\n    titre__icontains='django'           # icontains = insensible à la casse\n)\n\n# --- Filtres OR avec Q ---\nfrom django.db.models import Q\nrecherche = Article.objects.filter(\n    Q(titre__icontains='python') | Q(contenu__icontains='python')\n)\n\n# --- Trier ---\nArticle.objects.order_by('-date_creation', 'titre')   # - = décroissant\n\n# --- Limiter ---\nArticle.objects.all()[:10]            # Les 10 premiers\nArticle.objects.all()[10:20]          # Pagination manuelle\n\n# --- Agrégations (retournent une valeur) ---\nfrom django.db.models import Count, Avg\ntotal = Article.objects.count()\nmoy = Article.objects.aggregate(moyenne=Avg('nombre_vues'))['moyenne']\n\n# --- Annotation (ajouter un champ calculé à chaque ligne) ---\narticles = Article.objects.annotate(nb_commentaires=Count('commentaires'))\nfor a in articles:\n    print(a.nb_commentaires)  # Disponible comme un attribut normal\n\n# --- Optimisation des relations (CRUCIAL pour éviter N+1) ---\n# select_related : JOIN SQL — pour ForeignKey et OneToOne\narticles = Article.objects.select_related('auteur', 'categorie').filter(statut='publie')\n\n# prefetch_related : Requête séparée — pour ManyToMany et reverse FK\narticles = Article.objects.prefetch_related('tags', 'commentaires').all()\n\n# --- F() : Référencer un champ en BDD dans une expression ---\nArticle.objects.filter(nb_vues__gt=F('nb_commentaires'))  # Articles plus vus que commentés\nArticle.objects.all().update(nb_vues=F('nb_vues') + 1)    # Incrémenter en BDD directement")
        )

        data["orm_methods"] = (
            mt("21. Méthodes CRUD Fondamentales") +
            "Méthodes de requêtage de l'ORM :\n" +
            cb("# --- CREATE ---\n# Méthode 1 : create() (une seule requête SQL)\narticle = Article.objects.create(titre=\"Mon titre\", contenu=\"...\", auteur=user)\n\n# Méthode 2 : instancier puis save()\narticle = Article(titre=\"Mon titre\", auteur=user)\narticle.contenu = \"...\"\narticle.save()\n\n# Méthode 3 : get_or_create() — évite les doublons\narticle, created = Article.objects.get_or_create(\n    slug='mon-slug',\n    defaults={'titre': 'Mon Titre', 'auteur': user}\n)\n# created = True si créé, False si existait déjà\n\n# update_or_create()\narticle, created = Article.objects.update_or_create(\n    slug='mon-slug',\n    defaults={'titre': 'Nouveau titre'}\n)\n\n# bulk_create() — Insérer en masse (une seule requête SQL)\narticles = [Article(titre=f\"Article {i}\", auteur=user) for i in range(100)]\nArticle.objects.bulk_create(articles, batch_size=50)\n\n# --- READ ---\nArticle.objects.all()\nArticle.objects.get(pk=1)\nArticle.objects.filter(statut='publie')\nArticle.objects.values('id', 'titre')       # Dictionnaires (plus léger que les objets)\nArticle.objects.values_list('id', flat=True)  # Liste d'IDs : [1, 2, 3, ...]\nArticle.objects.only('titre', 'slug')       # Charge uniquement ces colonnes\nArticle.objects.defer('contenu')            # Charge tout SAUF contenu\n\n# --- UPDATE ---\n# Méthode 1 : modifier l'objet et save()\narticle = Article.objects.get(pk=1)\narticle.titre = \"Nouveau titre\"\narticle.save(update_fields=['titre'])  # update_fields = optimisation (n'update que titre)\n\n# Méthode 2 : update() sur QuerySet (une seule requête SQL, pas de signal)\nArticle.objects.filter(statut='brouillon').update(statut='publie')\n\n# bulk_update()\narticles = Article.objects.filter(auteur=user)\nfor a in articles:\n    a.statut = 'archive'\nArticle.objects.bulk_update(articles, ['statut'])\n\n# --- DELETE ---\narticle = Article.objects.get(pk=1)\narticle.delete()  # Supprime + lance le signal pre_delete\n\nArticle.objects.filter(statut='archive').delete()  # Suppression en masse")
        )

        data["postgresql"] = (
            mt("23. Implémentation Rigoureuse de PostgreSQL") +
            "Description : Base de données relationnelle industrielle standard pour Django.\n\n" +
            st("Installation du Driver Natif") +
            cb("pip install psycopg2-binary   # Développement\npip install psycopg2          # Production (requiert libpq-dev)") + "\n\n" +
            st("Configuration Enterprise (settings.py)") +
            cb("import os\n\nDATABASES = {\n    'default': {\n        'ENGINE': 'django.db.backends.postgresql',\n        'NAME': os.environ.get('DB_NAME', 'ma_base'),\n        'USER': os.environ.get('DB_USER', 'postgres'),\n        'PASSWORD': os.environ.get('DB_PASSWORD', ''),\n        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),\n        'PORT': os.environ.get('DB_PORT', '5432'),\n        'CONN_MAX_AGE': 600,  # Connexions persistantes 10 minutes (performance)\n        'OPTIONS': {\n            'connect_timeout': 10,\n        }\n    }\n}") + "\n\n" +
            st("Commandes PostgreSQL essentielles") +
            cb("createdb ma_base              # Créer une base\ndropdb ma_base                # Supprimer une base\npg_dump ma_base > backup.sql  # Sauvegarder\npsql ma_base < backup.sql     # Restaurer") + "\n\n" +
            st("Fonctionnalités Spécifiques PostgreSQL") +
            cb("# Champs spécifiques PG\nfrom django.contrib.postgres.fields import ArrayField\nfrom django.contrib.postgres.search import SearchVector, SearchQuery\n\nclass Article(models.Model):\n    tags_array = ArrayField(models.CharField(max_length=50), default=list)\n\n# Recherche plein texte (full-text search)\narticles = Article.objects.annotate(\n    search=SearchVector('titre', 'contenu', config='french')\n).filter(search=SearchQuery('django orm', config='french'))")
        )

        data["sqlite"] = (
            mt("24. Configuration SQLite avec Optimisations") +
            "Description : Base de données embarquée légère, parfaite pour les tests ou environnements de développement.\n\n" +
            st("Configuration et Mode WAL (Write-Ahead Logging)") +
            cb("DATABASES = {\n    'default': {\n        'ENGINE': 'django.db.backends.sqlite3',\n        'NAME': BASE_DIR / 'db.sqlite3',\n    }\n}") + "\n\n" +
            st("Optimisation via hooks de connexion (utils.py)") +
            cb("from django.db.backends.signals import connection_created\nfrom django.dispatch import receiver\n\n@receiver(connection_created)\ndef configure_sqlite(sender, connection, **kwargs):\n    if connection.vendor == 'sqlite':\n        cursor = connection.cursor()\n        cursor.execute('PRAGMA journal_mode=WAL;')    # Write-Ahead Logging : meilleure concurrence\n        cursor.execute('PRAGMA synchronous=NORMAL;')  # Meilleure performance (légèrement moins safe)\n        cursor.execute('PRAGMA cache_size=-64000;')   # Cache 64 MB\n        cursor.execute('PRAGMA foreign_keys=ON;')     # Activer les clés étrangères") + "\n\n" +
            "SQLite = Développement & tests. PostgreSQL = Production."
        )

        # =====================================================================
        # --- 7. SÉCURITÉ & AUTH ---
        # =====================================================================

        data["security"] = (
            mt("25. Durcissement de la Sécurité") +
            "Règles impératives : SSL, Gestion fine des CORS, Middleware de protection.\n\n" +
            st("Système d'Authentification Intégré") +
            cb("# views.py\nfrom django.contrib.auth import authenticate, login, logout\nfrom django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm\nfrom django.contrib.auth.models import User\n\ndef vue_connexion(request):\n    if request.user.is_authenticated:\n        return redirect('accueil')\n    if request.method == 'POST':\n        form = AuthenticationForm(request, data=request.POST)\n        if form.is_valid():\n            user = form.get_user()\n            login(request, user)\n            next_url = request.GET.get('next', 'accueil')\n            return redirect(next_url)\n    else:\n        form = AuthenticationForm()\n    return render(request, 'auth/connexion.html', {'form': form})\n\ndef vue_deconnexion(request):\n    logout(request)\n    return redirect('accueil')") + "\n\n" +
            st("Permissions") +
            cb("# Vérifier les permissions dans le code\nif request.user.has_perm('articles.add_article'):\n    ...\nif request.user.has_perms(['articles.add_article', 'articles.change_article']):\n    ...\n\n# Dans les templates\n{% if perms.articles.add_article %}\n    <a href=\"{% url 'articles:creer' %}\">Nouvel article</a>\n{% endif %}\n\n# Groupes dans la vue\nif request.user.groups.filter(name='Rédacteurs').exists():\n    ...") + "\n\n" +
            st("Sécurité en Production") +
            cb("# settings.py — À configurer impérativement\nSECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')  # JAMAIS en dur dans le code\nDEBUG = False\nALLOWED_HOSTS = ['monsite.com', 'www.monsite.com']\n\n# HTTPS\nSECURE_SSL_REDIRECT = True\nSECURE_HSTS_SECONDS = 31536000        # 1 an\nSECURE_HSTS_INCLUDE_SUBDOMAINS = True\nSECURE_HSTS_PRELOAD = True\n\n# Cookies\nSESSION_COOKIE_SECURE = True          # Cookie session uniquement en HTTPS\nCSRF_COOKIE_SECURE = True             # Cookie CSRF uniquement en HTTPS\nSESSION_COOKIE_HTTPONLY = True        # Inaccessible depuis JS\nCSRF_COOKIE_HTTPONLY = True\n\n# Clickjacking\nX_FRAME_OPTIONS = 'DENY'\n\n# Content type sniffing\nSECURE_CONTENT_TYPE_NOSNIFF = True")
        )

        data["cookies"] = (
            mt("26. Cookies & Sessions") +
            "Stockage : Gestion des cycles de vie sessions client/serveur.\n\n" +
            cb("# --- Sessions ---\n# Lire une valeur de session\npanier = request.session.get('panier', [])\nutilisateur_id = request.session.get('user_id')\n\n# Écrire dans la session\nrequest.session['panier'] = ['item1', 'item2']\nrequest.session['last_visit'] = str(datetime.now())\nrequest.session.modified = True       # Forcer la sauvegarde si on modifie un objet mutable\n\n# Supprimer de la session\ndel request.session['panier']\nrequest.session.flush()               # Vider toute la session + régénérer la clé\n\n# --- Cookies ---\ndef ma_vue(request):\n    # Lire un cookie\n    theme = request.COOKIES.get('theme', 'clair')\n\n    response = render(request, 'template.html', {'theme': theme})\n\n    # Écrire un cookie\n    response.set_cookie(\n        'theme',\n        'sombre',\n        max_age=30*24*3600,    # 30 jours en secondes\n        httponly=True,         # Inaccessible depuis JS\n        secure=True,           # HTTPS uniquement\n        samesite='Strict',     # Protection CSRF supplémentaire\n        path='/'\n    )\n\n    # Supprimer un cookie\n    response.delete_cookie('theme')\n\n    return response\n\n# settings.py — Configuration des sessions\nSESSION_ENGINE = 'django.contrib.sessions.backends.db'  # En BDD (défaut)\n# SESSION_ENGINE = 'django.contrib.sessions.backends.cache'  # En Redis (recommandé en prod)\nSESSION_COOKIE_AGE = 86400     # Durée de vie : 1 jour (en secondes)\nSESSION_EXPIRE_AT_BROWSER_CLOSE = False")
        )

        data["encryption"] = (
            mt("27. Chiffrement Cryptographique") +
            "Algorithmes : Pbkdf2/Argon2 pour les mots de passe.\n\n" +
            st("Mots de Passe") +
            cb("# Django utilise PBKDF2 par défaut. Pour Argon2 (plus sécurisé) :\npip install django[argon2]\n\n# settings.py\nPASSWORD_HASHERS = [\n    'django.contrib.auth.hashers.Argon2PasswordHasher',   # Principal\n    'django.contrib.auth.hashers.PBKDF2PasswordHasher',   # Fallback\n    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',\n]\n\n# Manipulation directe des mots de passe\nfrom django.contrib.auth.hashers import make_password, check_password\nhash = make_password('mon_mot_de_passe')\nvalide = check_password('mon_mot_de_passe', hash)  # True\n\n# Via l'objet User\nuser = User.objects.get(pk=1)\nuser.set_password('nouveau_mot_de_passe')  # Hash automatique\nuser.save()") + "\n\n" +
            st("Chiffrement Symétrique (Fernet)") +
            cb("pip install cryptography\n\nfrom cryptography.fernet import Fernet\n\n# Générer une clé (une seule fois, la stocker en variable d'environnement)\ncle = Fernet.generate_key()                    # b'...'\n\nf = Fernet(cle)\n\n# Chiffrer\nmessage = b\"Donnees sensibles\"\nchiffre = f.encrypt(message)                   # Token chiffré\n\n# Déchiffrer\noriginal = f.decrypt(chiffre)                  # b\"Donnees sensibles\"") + "\n\n" +
            st("Tokens JWT") +
            cb("pip install djangorestframework-simplejwt\n\n# settings.py\nfrom datetime import timedelta\nSIMPLE_JWT = {\n    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),\n    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),\n    'ALGORITHM': 'HS256',\n    'SIGNING_KEY': os.environ.get('JWT_SECRET_KEY'),\n}\n\n# urls.py\nfrom rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView\npath('api/token/', TokenObtainPairView.as_view(), name='token_obtain'),\npath('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),")
        )

        # =====================================================================
        # --- 8. AVANCÉ & API ---
        # =====================================================================

        data["js_ajax"] = (
            mt("28. JavaScript & AJAX") +
            "Asynchronisme : Communication asynchrone DOM backend.\n\n" +
            cb("// Requête AJAX vers une vue Django\nconst getCsrfToken = () => document.querySelector('[name=csrfmiddlewaretoken]').value;\n\nasync function envoyerFormulaire(formData) {\n    try {\n        const response = await fetch('/api/articles/', {\n            method: 'POST',\n            headers: {\n                'X-CSRFToken': getCsrfToken(),\n                'Content-Type': 'application/json',\n            },\n            body: JSON.stringify(formData)\n        });\n\n        if (!response.ok) {\n            const erreurs = await response.json();\n            throw new Error(JSON.stringify(erreurs));\n        }\n\n        const data = await response.json();\n        console.log('Succès :', data);\n        return data;\n\n    } catch (err) {\n        console.error('Erreur :', err.message);\n        afficherErreur(err.message);\n    }\n}\n\n// Envoi de fichier (multipart)\nasync function uploadFichier(fichier) {\n    const fd = new FormData();\n    fd.append('document', fichier);\n    fd.append('titre', 'Mon document');\n\n    const response = await fetch('/upload/', {\n        method: 'POST',\n        headers: { 'X-CSRFToken': getCsrfToken() },\n        body: fd   // PAS de Content-Type ici, FormData le gère automatiquement\n    });\n    return response.json();\n}") + "\n\n" +
            st("Vue Django qui reçoit AJAX") +
            cb("import json\nfrom django.views.decorators.http import require_POST\n\n@require_POST\n@login_required\ndef api_creer_article(request):\n    try:\n        body = json.loads(request.body)\n        titre = body.get('titre', '').strip()\n        if not titre:\n            return JsonResponse({'erreur': 'Titre requis'}, status=400)\n        article = Article.objects.create(titre=titre, auteur=request.user)\n        return JsonResponse({'id': article.pk, 'titre': article.titre}, status=201)\n    except json.JSONDecodeError:\n        return JsonResponse({'erreur': 'JSON invalide'}, status=400)\n    except Exception as e:\n        return JsonResponse({'erreur': str(e)}, status=500)")
        )

        data["browser_api"] = (
            mt("29. Interactions avec l'API Web du Navigateur") +
            "Description : Connexion directe de l'interface frontend aux capacités matérielles de l'hôte via JavaScript natif.\n\n" +
            st("Exemple d'Intégration Avancée (Géolocalisation & Notification)") +
            cb("// --- Géolocalisation ---\nnavigator.geolocation.getCurrentPosition(\n    (pos) => console.log(pos.coords.latitude, pos.coords.longitude),\n    (err) => console.error(err.message),\n    { enableHighAccuracy: true, timeout: 10000 }\n);\n\n// --- Notifications ---\nasync function demanderPermissionNotification() {\n    if (Notification.permission === 'default') {\n        await Notification.requestPermission();\n    }\n    if (Notification.permission === 'granted') {\n        new Notification('Titre', {\n            body: 'Message de notification',\n            icon: '/static/img/icon.png'\n        });\n    }\n}\n\n// --- Clipboard (copier/coller) ---\nawait navigator.clipboard.writeText('Texte à copier');\nconst texte = await navigator.clipboard.readText();\n\n// --- Camera / Microphone ---\nconst stream = await navigator.mediaDevices.getUserMedia({\n    video: { width: 1280, height: 720 },\n    audio: true\n});\ndocument.querySelector('video').srcObject = stream;\n\n// --- Stockage local ---\nlocalStorage.setItem('theme', 'sombre');\nconst theme = localStorage.getItem('theme');\nlocalStorage.removeItem('theme');\n\n// --- Service Worker (PWA offline) ---\nif ('serviceWorker' in navigator) {\n    navigator.serviceWorker.register('/sw.js')\n        .then(reg => console.log('SW enregistré'))\n        .catch(err => console.error(err));\n}")
        )

        data["api_drf"] = (
            mt("30. Construction d'API REST avec Django Rest Framework (DRF)") +
            "Description : Exposition de endpoints standardisés JSON, sécurisés par jetons d'accès.\n\n" +
            cb("pip install djangorestframework djangorestframework-simplejwt django-cors-headers") + "\n\n" +
            st("Configuration (settings.py)") +
            cb("# settings.py\nINSTALLED_APPS += ['rest_framework', 'corsheaders']\nMIDDLEWARE.insert(0, 'corsheaders.middleware.CorsMiddleware')\n\nREST_FRAMEWORK = {\n    'DEFAULT_AUTHENTICATION_CLASSES': [\n        'rest_framework_simplejwt.authentication.JWTAuthentication',\n    ],\n    'DEFAULT_PERMISSION_CLASSES': [\n        'rest_framework.permissions.IsAuthenticatedOrReadOnly',\n    ],\n    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',\n    'PAGE_SIZE': 20,\n    'DEFAULT_THROTTLE_CLASSES': [\n        'rest_framework.throttling.AnonRateThrottle',\n        'rest_framework.throttling.UserRateThrottle'\n    ],\n    'DEFAULT_THROTTLE_RATES': {\n        'anon': '100/day',\n        'user': '1000/day'\n    }\n}\n\nCORS_ALLOWED_ORIGINS = ['https://monfrontend.com']") + "\n\n" +
            st("Serializers") +
            cb("# serializers.py\nfrom rest_framework import serializers\nfrom .models import Article\n\nclass ArticleSerializer(serializers.ModelSerializer):\n    auteur_nom = serializers.CharField(source='auteur.username', read_only=True)\n    prix_ttc = serializers.SerializerMethodField()\n\n    class Meta:\n        model = Article\n        fields = ['id', 'titre', 'slug', 'contenu', 'auteur_nom', 'statut', 'date_creation']\n        read_only_fields = ['slug', 'date_creation']\n\n    def get_prix_ttc(self, obj):\n        return float(obj.prix_ttc) if hasattr(obj, 'prix_ttc') else None\n\n    def validate_titre(self, value):\n        if len(value) < 5:\n            raise serializers.ValidationError(\"Titre trop court.\")\n        return value") + "\n\n" +
            st("Views (ViewSets)") +
            cb("# views.py (DRF)\nfrom rest_framework import viewsets, permissions, filters\nfrom rest_framework.decorators import action\nfrom rest_framework.response import Response\n\nclass ArticleViewSet(viewsets.ModelViewSet):\n    queryset = Article.objects.select_related('auteur').filter(statut='publie')\n    serializer_class = ArticleSerializer\n    filter_backends = [filters.SearchFilter, filters.OrderingFilter]\n    search_fields = ['titre', 'contenu']\n    ordering_fields = ['date_creation', 'titre']\n\n    def perform_create(self, serializer):\n        serializer.save(auteur=self.request.user)  # Injecter l'auteur\n\n    @action(detail=True, methods=['post'], url_path='publier')\n    def publier(self, request, pk=None):\n        \"\"\"Endpoint personnalisé : POST /api/articles/{pk}/publier/\"\"\"\n        article = self.get_object()\n        article.statut = 'publie'\n        article.save()\n        return Response({'status': 'publié'})") + "\n\n" +
            st("URLs (Routers)") +
            cb("# urls.py\nfrom rest_framework.routers import DefaultRouter\nrouter = DefaultRouter()\nrouter.register(r'articles', ArticleViewSet, basename='article')\nurlpatterns = [path('api/', include(router.urls))]\n# Génère automatiquement : GET/POST /api/articles/, GET/PUT/PATCH/DELETE /api/articles/{pk}/")
        )

        data["channels"] = (
            mt("31. Temps Réel Évolutif avec Django Channels & WebSockets") +
            "Description : Architecture asynchrone permettant de maintenir des connexions persistantes full-duplex temps réel.\n\n" +
            cb("pip install channels channels-redis daphne") + "\n\n" +
            st("Configuration (settings.py)") +
            cb("# settings.py\nINSTALLED_APPS += ['channels', 'daphne']\nASGI_APPLICATION = 'core_project.asgi.application'\n\nCHANNEL_LAYERS = {\n    'default': {\n        'BACKEND': 'channels_redis.core.RedisChannelLayer',\n        'CONFIG': {'hosts': [('127.0.0.1', 6379)]},\n    }\n}") + "\n\n" +
            st("asgi.py") +
            cb("# asgi.py\nimport os\nfrom django.core.asgi import get_asgi_application\nfrom channels.routing import ProtocolTypeRouter, URLRouter\nfrom channels.auth import AuthMiddlewareStack\nfrom . import routing\n\nos.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core_project.settings')\n\napplication = ProtocolTypeRouter({\n    'http': get_asgi_application(),       # Requêtes HTTP normales\n    'websocket': AuthMiddlewareStack(     # WebSocket avec auth Django\n        URLRouter(routing.websocket_urlpatterns)\n    ),\n})") + "\n\n" +
            st("routing.py") +
            cb("# routing.py\nfrom django.urls import re_path\nfrom . import consumers\n\nwebsocket_urlpatterns = [\n    re_path(r'ws/chat/(?P<room_name>\\w+)/$', consumers.ChatConsumer.as_asgi()),\n    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),\n]") + "\n\n" +
            st("consumers.py") +
            cb("# consumers.py\nimport json\nfrom channels.generic.websocket import AsyncWebsocketConsumer\n\nclass ChatConsumer(AsyncWebsocketConsumer):\n    async def connect(self):\n        self.room_name = self.scope['url_route']['kwargs']['room_name']\n        self.group_name = f'chat_{self.room_name}'\n\n        await self.channel_layer.group_add(self.group_name, self.channel_name)\n        await self.accept()\n\n    async def disconnect(self, close_code):\n        await self.channel_layer.group_discard(self.group_name, self.channel_name)\n\n    async def receive(self, text_data):\n        data = json.loads(text_data)\n        await self.channel_layer.group_send(\n            self.group_name,\n            {'type': 'chat_message', 'message': data['message'], 'user': data.get('user', 'Anonyme')}\n        )\n\n    async def chat_message(self, event):\n        await self.send(text_data=json.dumps({\n            'message': event['message'],\n            'user': event['user']\n        }))") + "\n\n" +
            st("Côté client") +
            cb("// Côté client\nconst socket = new WebSocket(`ws://${window.location.host}/ws/chat/ma-room/`);\n\nsocket.onopen = () => socket.send(JSON.stringify({ message: 'Bonjour !', user: 'Alice' }));\nsocket.onmessage = (e) => {\n    const data = JSON.parse(e.data);\n    afficherMessage(data.user, data.message);\n};\nsocket.onclose = () => console.log('WebSocket fermé');\nsocket.onerror = (err) => console.error('Erreur WebSocket :', err);")
        )

        data["celery"] = (
            mt("32. Exécution de Tâches Asynchrones & Distribuées via Celery") +
            "Description : Déchargement des traitements lourds et asynchrones en arrière-plan.\n" +
            "Pourquoi : Garantir un temps de réponse instantané au client HTTP (inférieur à 100ms) et déléguer les calculs à des nœuds d'exécution (Workers).\n\n" +
            cb("pip install celery redis") + "\n\n" +
            st("Configuration (celery.py)") +
            cb("# celery.py (à la racine du projet)\nimport os\nfrom celery import Celery\n\nos.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core_project.settings')\n\napp = Celery('core_project')\napp.config_from_object('django.conf:settings', namespace='CELERY')\napp.autodiscover_tasks()  # Découvre automatiquement les tasks.py de toutes les apps") + "\n\n" +
            st("Configuration (settings.py)") +
            cb("# settings.py\nCELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')\nCELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'\nCELERY_ACCEPT_CONTENT = ['json']\nCELERY_TASK_SERIALIZER = 'json'\nCELERY_TIMEZONE = 'Europe/Paris'\n\n# __init__.py du projet (pour auto-découverte)\nfrom .celery import app as celery_app\n__all__ = ('celery_app',)") + "\n\n" +
            st("Tasks (tasks.py)") +
            cb("# tasks.py\nfrom celery import shared_task\nfrom django.core.mail import send_mail\nfrom celery.utils.log import get_task_logger\n\nlogger = get_task_logger(__name__)\n\n@shared_task(bind=True, max_retries=3, default_retry_delay=60)\ndef envoyer_email_bienvenue(self, user_id: int):\n    \"\"\"Tâche avec retry automatique en cas d'échec.\"\"\"\n    from django.contrib.auth.models import User\n    try:\n        user = User.objects.get(pk=user_id)\n        send_mail(\n            subject='Bienvenue !',\n            message=f'Bonjour {user.username}, bienvenue sur notre plateforme.',\n            from_email='noreply@monsite.com',\n            recipient_list=[user.email],\n        )\n        logger.info(f'Email envoyé à {user.email}')\n        return f'Email envoyé à {user.email}'\n    except User.DoesNotExist:\n        logger.error(f'Utilisateur {user_id} introuvable')\n        raise\n    except Exception as exc:\n        logger.warning(f'Erreur email, retry dans 60s : {exc}')\n        raise self.retry(exc=exc)\n\n@shared_task\ndef generer_rapport_mensuel():\n    \"\"\"Tâche périodique (configurer dans CELERY_BEAT_SCHEDULE).\"\"\"\n    # ... logique de génération\n    return 'Rapport généré'") + "\n\n" +
            st("Appel non bloquant depuis une Vue") +
            cb("# Déclencher depuis une vue\nfrom .tasks import envoyer_email_bienvenue\n\ndef inscription(request):\n    user = creer_utilisateur(request.POST)\n    envoyer_email_bienvenue.delay(user.pk)  # .delay() = envoi asynchrone non bloquant\n    return JsonResponse({'status': 'Inscription réussie'})") + "\n\n" +
            st("Tâches périodiques (Celery Beat)") +
            cb("# settings.py\nfrom celery.schedules import crontab\nCELERY_BEAT_SCHEDULE = {\n    'rapport-mensuel': {\n        'task': 'mon_app.tasks.generer_rapport_mensuel',\n        'schedule': crontab(day_of_month=1, hour=2, minute=0),  # Le 1er de chaque mois à 2h\n    },\n}") + "\n\n" +
            st("Démarrer les processus") +
            cb("celery -A core_project worker --loglevel=info          # Worker\ncelery -A core_project beat --loglevel=info            # Scheduler (tâches périodiques)\ncelery -A core_project flower                          # Interface de monitoring web")
        )

        # =====================================================================
        # --- 9. DÉPLOIEMENT & PROD ---
        # =====================================================================

        data["nginx_gunicorn"] = (
            mt("33. Nginx & Gunicorn") +
            "Stack : Reverse proxy Nginx couplé au serveur WSGI Gunicorn.\n\n" +
            st("Architecture") +
            "Internet → Nginx (80/443) → Gunicorn (8000) → Django App\n" +
            "                ↘\n" +
            "           Fichiers statiques/media (servis directement par Nginx)\n\n" +
            st("Configuration Nginx") +
            cb("# /etc/nginx/sites-available/monsite\nserver {\n    listen 80;\n    server_name monsite.com www.monsite.com;\n    return 301 https://$server_name$request_uri;   # Forcer HTTPS\n}\n\nserver {\n    listen 443 ssl http2;\n    server_name monsite.com www.monsite.com;\n\n    # SSL\n    ssl_certificate     /etc/letsencrypt/live/monsite.com/fullchain.pem;\n    ssl_certificate_key /etc/letsencrypt/live/monsite.com/privkey.pem;\n    ssl_protocols TLSv1.2 TLSv1.3;\n\n    # Fichiers statiques (Django collectstatic)\n    location /static/ {\n        alias /var/www/monsite/staticfiles/;\n        expires 30d;\n        add_header Cache-Control \"public, immutable\";\n    }\n\n    # Fichiers média (uploads utilisateurs)\n    location /media/ {\n        alias /var/www/monsite/media/;\n        expires 7d;\n    }\n\n    # Requêtes Django → Gunicorn\n    location / {\n        proxy_pass http://127.0.0.1:8000;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n        proxy_read_timeout 300s;\n        client_max_body_size 50M;    # Taille max upload\n    }\n\n    # WebSockets (si Django Channels)\n    location /ws/ {\n        proxy_pass http://127.0.0.1:8000;\n        proxy_http_version 1.1;\n        proxy_set_header Upgrade $http_upgrade;\n        proxy_set_header Connection \"upgrade\";\n    }\n}") + "\n\n" +
            cb("# Activer le site\nln -s /etc/nginx/sites-available/monsite /etc/nginx/sites-enabled/\nnginx -t          # Tester la configuration\nsystemctl reload nginx")
        )

        data["gunicorn_opts"] = (
            mt("34. Optimisation Gunicorn") +
            "CMD : Gestion dynamique du nombre de workers et timeout.\n\n" +
            cb("# Commande complète recommandée\ngunicorn core_project.wsgi:application \\\n    --workers 5 \\                 # CPU * 2 + 1 (règle empirique)\n    --worker-class sync \\         # sync, gevent, uvicorn.workers.UvicornWorker (async)\n    --threads 2 \\                 # Threads par worker\n    --bind 127.0.0.1:8000 \\      # Interface d'écoute\n    --timeout 120 \\               # Timeout worker (secondes)\n    --keepalive 5 \\               # Durée des connexions persistantes\n    --max-requests 1000 \\         # Redémarrer un worker après N requêtes (évite les fuites mémoire)\n    --max-requests-jitter 50 \\    # Aléatoire pour éviter restart simultané\n    --preload \\                   # Charger l'app avant de forker (économise mémoire)\n    --access-logfile /var/log/gunicorn/access.log \\\n    --error-logfile /var/log/gunicorn/error.log \\\n    --log-level warning") + "\n\n" +
            cb("# gunicorn.conf.py (alternative propre)\nbind = \"127.0.0.1:8000\"\nworkers = 5\nthreads = 2\nworker_class = \"sync\"\ntimeout = 120\nmax_requests = 1000\nmax_requests_jitter = 50\npreload_app = True\naccesslog = \"/var/log/gunicorn/access.log\"\nerrorlog = \"/var/log/gunicorn/error.log\"\nloglevel = \"warning\"\n\n# Lancer avec le fichier de config\ngunicorn -c gunicorn.conf.py core_project.wsgi:application")
        )

        data["production"] = (
            mt("35. Checklist de Production") +
            "Checklist : Désactivation stricte du mode DEBUG, gestion des clés secrètes.\n\n" +
            st("settings.py") +
            cb("import os\nfrom pathlib import Path\n\nSECRET_KEY = os.environ['DJANGO_SECRET_KEY']   # Variable d'environnement, JAMAIS en dur\nDEBUG = False\nALLOWED_HOSTS = ['monsite.com', 'www.monsite.com']\n\n# HTTPS & Sécurité\nSECURE_SSL_REDIRECT = True\nSECURE_HSTS_SECONDS = 31536000\nSECURE_HSTS_INCLUDE_SUBDOMAINS = True\nSECURE_HSTS_PRELOAD = True\nSESSION_COOKIE_SECURE = True\nCSRF_COOKIE_SECURE = True\nX_FRAME_OPTIONS = 'DENY'\nSECURE_CONTENT_TYPE_NOSNIFF = True\n\n# Logging\nLOGGING = {\n    'version': 1,\n    'disable_existing_loggers': False,\n    'handlers': {\n        'file': {\n            'level': 'WARNING',\n            'class': 'logging.handlers.RotatingFileHandler',\n            'filename': '/var/log/django/errors.log',\n            'maxBytes': 1024 * 1024 * 10,  # 10 MB\n            'backupCount': 5,\n        },\n        'mail_admins': {\n            'level': 'ERROR',\n            'class': 'django.utils.log.AdminEmailHandler',\n        }\n    },\n    'loggers': {\n        'django': {'handlers': ['file', 'mail_admins'], 'level': 'WARNING'},\n    }\n}\n\n# Cache Redis\nCACHES = {\n    'default': {\n        'BACKEND': 'django.core.cache.backends.redis.RedisCache',\n        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),\n    }\n}\n\n# Email\nEMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'\nEMAIL_HOST = os.environ.get('EMAIL_HOST')\nEMAIL_PORT = 587\nEMAIL_USE_TLS = True\nEMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')\nEMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')\nDEFAULT_FROM_EMAIL = 'noreply@monsite.com'\nADMINS = [('Admin', 'admin@monsite.com')]") + "\n\n" +
            st("Service Systemd") +
            cb("# /etc/systemd/system/monsite.service\n[Unit]\nDescription=Gunicorn pour monsite\nAfter=network.target\n\n[Service]\nUser=www-data\nGroup=www-data\nWorkingDirectory=/var/www/monsite\nEnvironmentFile=/var/www/monsite/.env\nExecStart=/var/www/monsite/venv/bin/gunicorn -c gunicorn.conf.py core_project.wsgi:application\nRestart=on-failure\nRestartSec=5s\n\n[Install]\nWantedBy=multi-user.target\n\nsystemctl daemon-reload\nsystemctl enable monsite\nsystemctl start monsite\nsystemctl status monsite\njournalctl -u monsite -f   # Voir les logs en temps réel")
        )

        data["deploy"] = (
            mt("36. Déploiement Gykhamine Studio") +
            "DevOps : Industrialisation et gestion automatisée de l'infrastructure.\n\n" +
            st("Procédure Complète") +
            cb("# === PREMIÈRE INSTALLATION ===\n\n# 1. Sur le serveur : préparer l'environnement\nsudo apt update && sudo apt install -y python3-pip python3-venv postgresql nginx certbot\n\n# 2. Cloner le projet\ngit clone https://github.com/monuser/monprojet.git /var/www/monsite\ncd /var/www/monsite\n\n# 3. Environnement virtuel\npython3 -m venv venv\nsource venv/bin/activate\npip install -r requirements.txt\n\n# 4. Variables d'environnement\ncat > .env << EOF\nDJANGO_SECRET_KEY=votre_cle_secrete_tres_longue\nDB_NAME=monsite_db\nDB_USER=postgres\nDB_PASSWORD=mot_de_passe\nREDIS_URL=redis://127.0.0.1:6379/0\nEOF\n\n# 5. Base de données\npython manage.py migrate\npython manage.py createsuperuser\npython manage.py collectstatic --no-input\n\n# 6. Certificat SSL (Let's Encrypt)\ncertbot --nginx -d monsite.com -d www.monsite.com\n\n# 7. Démarrer\nsystemctl start monsite nginx\n\n# === MISES À JOUR ===\ncd /var/www/monsite\ngit pull origin main\nsource venv/bin/activate\npip install -r requirements.txt\npython manage.py migrate\npython manage.py collectstatic --no-input\nsystemctl restart monsite")
        )

        data["tips"] = (
            mt("37. Bonnes Pratiques") +
            "Performance : Optimisation des requêtes SQL et indexation physique.\n\n" +
            st("Éviter le Problème N+1 (Le Plus Courant)") +
            cb("# ❌ MAUVAIS : N+1 requêtes (1 pour les articles + 1 par auteur)\narticles = Article.objects.all()\nfor a in articles:\n    print(a.auteur.username)   # Requête SQL à chaque itération !\n\n# ✅ BON : select_related — 1 seule requête avec JOIN\narticles = Article.objects.select_related('auteur', 'categorie').all()\nfor a in articles:\n    print(a.auteur.username)   # Déjà en mémoire, aucune requête !\n\n# ✅ BON : prefetch_related — 2 requêtes pour les ManyToMany\narticles = Article.objects.prefetch_related('tags').all()") + "\n\n" +
            st("Optimisation des Requêtes") +
            cb("# Vérifier l'existence sans charger l'objet\nif Article.objects.filter(slug=slug).exists():   # ✅ SELECT 1 (ultra-rapide)\n    ...\nif Article.objects.filter(slug=slug).count() > 0:  # ❌ COUNT(*) plus lent\n\n# Charger seulement les colonnes nécessaires\nids = Article.objects.values_list('id', flat=True)         # [1, 2, 3]\ntitres = Article.objects.values('id', 'titre')             # [{'id': 1, 'titre': '...'}]\nArticle.objects.only('titre', 'slug')                       # Objets allégés\n\n# Indexer les colonnes souvent filtrées/triées\nclass Meta:\n    indexes = [\n        models.Index(fields=['statut', '-date_creation']),  # Index composite\n    ]") + "\n\n" +
            st("Debug & Diagnostic") +
            cb("# Voir les requêtes SQL générées\nfrom django.db import connection\nprint(connection.queries)   # Liste de toutes les requêtes (DEBUG=True requis)\n\n# Nombre de requêtes d'une vue\n# pip install django-debug-toolbar  → ajoute une barre de debug dans le navigateur\n\n# Logger personnalisé\nimport logging\nlogger = logging.getLogger(__name__)\n\ndef ma_vue(request):\n    logger.debug(f\"Vue appelée par {request.user}\")\n    logger.warning(\"Quelque chose d'inhabituel\")\n    logger.error(\"Erreur critique\", exc_info=True)  # exc_info=True pour la stack trace") + "\n\n" +
            st("Variables d'Environnement (Bonne Pratique)") +
            cb("# .env (NE JAMAIS committer ce fichier !)\nDJANGO_SECRET_KEY=cle_tres_longue_et_aleatoire\nDB_PASSWORD=mon_mot_de_passe\n\n# pip install python-decouple\nfrom decouple import config\n\nSECRET_KEY = config('DJANGO_SECRET_KEY')\nDB_PASSWORD = config('DB_PASSWORD')\nDEBUG = config('DEBUG', default=False, cast=bool)") + "\n\n" +
            st("Tests") +
            cb("# tests.py\nfrom django.test import TestCase, Client\nfrom django.contrib.auth.models import User\nfrom .models import Article\n\nclass ArticleModelTest(TestCase):\n    def setUp(self):\n        self.user = User.objects.create_user('testuser', password='testpass')\n        self.article = Article.objects.create(\n            titre='Test Article', auteur=self.user, statut='publie'\n        )\n\n    def test_str(self):\n        self.assertEqual(str(self.article), 'Test Article [Publié]')\n\n    def test_slug_auto(self):\n        self.assertEqual(self.article.slug, 'test-article')\n\n    def test_est_publie(self):\n        self.assertTrue(self.article.est_publie)\n\n\nclass ArticleViewTest(TestCase):\n    def setUp(self):\n        self.client = Client()\n        self.user = User.objects.create_user('testuser', password='testpass')\n\n    def test_liste_accessible(self):\n        response = self.client.get('/articles/')\n        self.assertEqual(response.status_code, 200)\n\n    def test_creer_necessite_connexion(self):\n        response = self.client.get('/articles/creer/')\n        self.assertRedirects(response, '/connexion/?next=/articles/creer/')\n\n    def test_creer_article(self):\n        self.client.login(username='testuser', password='testpass')\n        response = self.client.post('/articles/creer/', {\n            'titre': 'Mon Test', 'contenu': 'Contenu de test', 'statut': 'brouillon'\n        })\n        self.assertEqual(response.status_code, 302)   # Redirect après POST\n        self.assertTrue(Article.objects.filter(titre='Mon Test').exists())") + "\n\n" +
            st("Commandes Django Custom") +
            cb("# management/commands/nettoyer_brouillons.py\nfrom django.core.management.base import BaseCommand\nfrom datetime import timedelta\nfrom django.utils import timezone\nfrom articles.models import Article\n\nclass Command(BaseCommand):\n    help = 'Supprime les brouillons de plus de 30 jours'\n\n    def add_arguments(self, parser):\n        parser.add_argument('--dry-run', action='store_true', help='Simuler sans supprimer')\n\n    def handle(self, *args, **options):\n        seuil = timezone.now() - timedelta(days=30)\n        qs = Article.objects.filter(statut='brouillon', date_modification__lt=seuil)\n        count = qs.count()\n        if not options['dry_run']:\n            qs.delete()\n            self.stdout.write(self.style.SUCCESS(f'{count} brouillons supprimés.'))\n        else:\n            self.stdout.write(f'DRY RUN : {count} brouillons seraient supprimés.')\n\n# Utilisation :\n# python manage.py nettoyer_brouillons\n# python manage.py nettoyer_brouillons --dry-run")
        )
        
        # Fill remaining keys with placeholder if missing
        for key in ["project_app", "manage", "fields", "field_opts", "model_methods", "views", "decorators", "view_cases", "responses", "forms", "form_model", "form_tips", "templates", "tags", "template_logic", "filters", "static_media", "orm", "orm_methods", "postgresql", "sqlite", "security", "cookies", "encryption", "js_ajax", "browser_api", "api_drf", "channels", "celery", "nginx_gunicorn", "gunicorn_opts", "production", "deploy", "tips"]:
            if key not in data:
                data[key] = fmt_title(key.upper()) + "Documentation détaillée à venir dans cette section."
                
        return data
