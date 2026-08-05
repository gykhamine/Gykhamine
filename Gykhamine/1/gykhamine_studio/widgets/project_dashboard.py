"""Tableau de bord du projet : statistiques de code + état système, graphiques seaborn,
et schéma de liaison complet (graphe) entre apps / modèles / vues / urls / templates /
formulaires / serializers / admin / commandes / modules tiers.

L'inspection des imports (et donc la détection des modules tiers) se fait directement en
parsant l'AST de chaque fichier .py du projet — pas de regex approximative sur le texte."""
import os, re, sys, ast, threading, tempfile
from pathlib import Path
from collections import Counter

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gdk

from ..config import global_log, set_margins
from .file_panel import IGNORED_DIRS

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import matplotlib
    matplotlib.use("Agg")  # backend hors-écran : ne doit jamais toucher la boucle GTK
    import matplotlib.pyplot as plt
    import seaborn as sns
    sns.set_theme(style="darkgrid")
    HAS_CHARTS = True
except ImportError:
    HAS_CHARTS = False

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

CODE_EXTENSIONS = {".py", ".html", ".js", ".jsx", ".css", ".c", ".cpp", ".h", ".hpp", ".sql", ".sh"}
DEBUG_RE = re.compile(r"^\s*DEBUG\s*=\s*(\w+)", re.MULTILINE)
DB_ENGINE_RE = re.compile(r"['\"]ENGINE['\"]\s*:\s*['\"]([\w\.]+)['\"]")
INSTALLED_APPS_RE = re.compile(r"INSTALLED_APPS\s*=\s*\[(.*?)\]", re.DOTALL)

# Utilisé seulement si sys.stdlib_module_names est indisponible (Python < 3.10)
_FALLBACK_STDLIB = {
    "os", "sys", "re", "json", "math", "time", "datetime", "collections", "itertools",
    "functools", "pathlib", "subprocess", "threading", "asyncio", "logging", "typing",
    "abc", "io", "socket", "sqlite3", "hashlib", "uuid", "random", "string", "copy",
    "shutil", "tempfile", "unittest", "traceback", "argparse", "enum", "dataclasses",
    "csv", "xml", "html", "http", "urllib", "email", "base64", "struct", "pickle",
    "zipfile", "tarfile", "gzip", "inspect", "importlib", "contextlib", "warnings",
    "decimal", "fractions", "statistics", "queue", "multiprocessing", "signal", "ast",
}

# Types de nœuds affichés dans le schéma de liaison (ordre = ordre de la légende)
GRAPH_NODE_STYLE = {
    "app":        {"color": "#4C72B0", "label": "App",              "size": 260},
    "model":      {"color": "#DD8452", "label": "Modèle",           "size": 90},
    "view":       {"color": "#55A868", "label": "Vue",              "size": 90},
    "url":        {"color": "#C44E52", "label": "URL",              "size": 70},
    "template":   {"color": "#8172B2", "label": "Template",         "size": 70},
    "form":       {"color": "#9B8431", "label": "Formulaire",       "size": 80},
    "serializer": {"color": "#64B5CD", "label": "Serializer",       "size": 80},
    "admin":      {"color": "#937860", "label": "Admin",            "size": 80},
    "command":    {"color": "#DA8BC3", "label": "Commande manage",  "size": 80},
    "django":     {"color": "#8C8C8C", "label": "Django (core)",    "size": 180},
    "tierce":     {"color": "#B4B400", "label": "Module tiers",     "size": 140},
    "permission": {"color": "#B22222", "label": "Droit / Permission", "size": 60},
    "group":      {"color": "#2E8B57", "label": "Groupe",          "size": 60},
    "action":     {"color": "#D2A441", "label": "Action",          "size": 50},
}


# ═══════════════════════════════════════════════════════════════════════
#  ANALYSE STATIQUE — parsing AST direct (imports, models, vues, urls, ...)
# ═══════════════════════════════════════════════════════════════════════

def _unparse(node) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def _meta_model(class_node) -> str:
    """Cherche, dans le corps d'une classe Form/Serializer, une sous-classe
    ``Meta`` avec ``model = NomDuModele`` et retourne ce nom (ou '' si absent).
    Sert à relier Formulaire/Serializer → Modèle dans le schéma de liaison."""
    for child in class_node.body:
        if isinstance(child, ast.ClassDef) and child.name == "Meta":
            for stmt in child.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id == "model":
                            return _unparse(stmt.value)
    return ""


def _app_for_file(fpath: Path, project_root: Path, django_apps: set) -> str:
    """Rattache un fichier à l'app Django la plus proche (dossier connu contenant
    apps.py/models.py), sinon retombe sur le premier segment du chemin relatif."""
    try:
        parts = fpath.relative_to(project_root).parts
    except Exception:
        return "?"
    for part in parts:
        if part in django_apps:
            return part
    return parts[0] if parts else "?"


def _model_relations(class_node) -> list:
    """Cherche dans le corps d'un modèle les champs ForeignKey/OneToOneField/
    ManyToManyField et retourne les noms de modèles cibles référencés — pour
    relier un modèle aux autres entités auxquelles il est lié."""
    rel_fields = {"ForeignKey", "OneToOneField", "ManyToManyField"}
    targets = []
    for stmt in class_node.body:
        value = None
        if isinstance(stmt, ast.Assign):
            value = stmt.value
        elif isinstance(stmt, ast.AnnAssign):
            value = stmt.value
        if not isinstance(value, ast.Call):
            continue
        fname = value.func.attr if isinstance(value.func, ast.Attribute) else (
            value.func.id if isinstance(value.func, ast.Name) else None)
        if fname not in rel_fields or not value.args:
            continue
        arg0 = value.args[0]
        target = None
        if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
            target = arg0.value
        elif isinstance(arg0, ast.Name):
            target = arg0.id
        elif isinstance(arg0, ast.Attribute):
            target = arg0.attr
        if target and target != "self":
            targets.append(target.split(".")[-1])
    return targets


def _view_extra(node, is_class: bool) -> dict:
    """Analyse une vue (classe ou fonction) pour en extraire les modèles utilisés,
    les droits/permissions requis, les groupes vérifiés, et une action déduite —
    pour densifier le schéma avec Vue → Modèle / Droit / Groupe / Action."""
    model_refs, permission_refs, group_refs = set(), [], []
    decorator_texts = [_unparse(d) for d in getattr(node, "decorator_list", [])]

    if is_class:
        bases_txt = " ".join(_unparse(b) for b in node.bases)
        for mixin, label in (("LoginRequiredMixin", "Connexion requise"),
                              ("PermissionRequiredMixin", "Permission requise"),
                              ("UserPassesTestMixin", "Test d'accès personnalisé")):
            if mixin in bases_txt:
                permission_refs.append(label)
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if not isinstance(target, ast.Name):
                        continue
                    if target.id in ("model",):
                        val = _unparse(stmt.value).split(".")[-1]
                        if val: model_refs.add(val)
                    elif target.id == "queryset":
                        m = re.search(r"([A-Z]\w*)\.objects", _unparse(stmt.value))
                        if m: model_refs.add(m.group(1))
                    elif target.id in ("permission_required", "permission_classes"):
                        permission_refs.append(_unparse(stmt.value).strip("'\"[]"))
                    elif target.id in ("allowed_groups", "group_required"):
                        group_refs.append(_unparse(stmt.value).strip("'\"[]"))
        action = {
            "ListView": "Liste", "CreateView": "Création", "UpdateView": "Modification",
            "DeleteView": "Suppression", "DetailView": "Détail", "FormView": "Formulaire",
        }.get(next((b for b in [_unparse(x) for x in node.bases] if b in (
            "ListView", "CreateView", "UpdateView", "DeleteView", "DetailView", "FormView")), None), "Vue personnalisée")
    else:
        for dec in decorator_texts:
            if "login_required" in dec:
                permission_refs.append("Connexion requise")
            elif dec.startswith("permission_required("):
                permission_refs.append(dec[len("permission_required("):-1].strip("'\""))
            elif dec.startswith("user_passes_test("):
                permission_refs.append("Test d'accès personnalisé")
            elif dec.startswith("group_required("):
                group_refs.append(dec[len("group_required("):-1].strip("'\""))
        for sub in ast.walk(node):
            if isinstance(sub, ast.Attribute) and sub.attr == "objects" and isinstance(sub.value, ast.Name):
                model_refs.add(sub.value.id)
            if isinstance(sub, ast.Call) and "groups" in _unparse(sub.func):
                for kw in sub.keywords:
                    if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        group_refs.append(kw.value.value)
                for a in sub.args:
                    if isinstance(a, ast.Constant) and isinstance(a.value, str):
                        group_refs.append(a.value)
        name_l = node.name.lower()
        if name_l.startswith(("list", "index")): action = "Liste"
        elif name_l.startswith(("create", "add", "new")): action = "Création"
        elif name_l.startswith(("update", "edit")): action = "Modification"
        elif name_l.startswith(("delete", "remove")): action = "Suppression"
        elif name_l.startswith(("detail", "show", "view")): action = "Détail"
        else: action = "Action"

    return {
        "model_refs": sorted(model_refs),
        "permission_refs": sorted(set(permission_refs)),
        "group_refs": sorted(set(group_refs)),
        "action": action,
    }


def _analyze_python_file(content: str, fpath: Path) -> dict:
    """Parse un fichier .py via `ast` et en extrait : imports, modèles, vues,
    formulaires, serializers, enregistrements admin, routes d'URL, templates référencés.
    C'est une inspection directe de l'arbre syntaxique, pas une regex sur le texte."""
    out = {
        "imports": [], "models": [], "views": [], "forms": [], "serializers": [],
        "admin_registrations": [], "urls": [], "templates_referenced": [],
    }
    try:
        tree = ast.parse(content, filename=str(fpath))
    except Exception:
        return out

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out["imports"].append(alias.name.split(".")[0])

        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                out["imports"].append(node.module.split(".")[0])

        elif isinstance(node, ast.ClassDef):
            bases = [_unparse(b) for b in node.bases]
            base_text = " ".join(bases)
            if any("View" in b for b in bases):
                out["views"].append({"name": node.name, "kind": "class", **_view_extra(node, is_class=True)})
            elif "models.Model" in base_text or re.search(r"(^|\.)Model$", base_text):
                out["models"].append({"name": node.name, "relations": _model_relations(node)})
            elif "Serializer" in base_text:
                out["serializers"].append({"name": node.name, "meta_model": _meta_model(node)})
            elif "forms." in base_text or re.search(r"\bForm\b", base_text):
                out["forms"].append({"name": node.name, "meta_model": _meta_model(node)})
            # Décorateur @admin.register(Model)
            for dec in node.decorator_list:
                dec_txt = _unparse(dec)
                m = re.match(r"admin\.register\((.*)\)", dec_txt)
                if m:
                    for arg in m.group(1).split(","):
                        arg = arg.strip()
                        if arg:
                            out["admin_registrations"].append(arg)

        elif isinstance(node, ast.FunctionDef):
            if node.args.args and node.args.args[0].arg == "request":
                out["views"].append({"name": node.name, "kind": "function", **_view_extra(node, is_class=False)})

        elif isinstance(node, ast.Call):
            fname = None
            if isinstance(node.func, ast.Name):
                fname = node.func.id
            elif isinstance(node.func, ast.Attribute):
                fname = node.func.attr
            func_full = _unparse(node.func)

            if fname in ("path", "re_path") and node.args:
                route, view_expr, name = None, None, None
                a0 = node.args[0]
                if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                    route = a0.value
                if len(node.args) > 1:
                    view_expr = _unparse(node.args[1])
                for kw in node.keywords:
                    if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                        name = kw.value.value
                out["urls"].append({"route": route, "view_expr": view_expr, "name": name})

            elif fname == "render" and len(node.args) > 1:
                a1 = node.args[1]
                if isinstance(a1, ast.Constant) and isinstance(a1.value, str):
                    out["templates_referenced"].append(a1.value)

            elif func_full == "admin.site.register" and node.args:
                for arg in node.args[:1]:
                    txt = _unparse(arg)
                    if txt:
                        out["admin_registrations"].append(txt)

        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ("template_name",):
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        out["templates_referenced"].append(node.value.value)

    return out


class ProjectDashboardDialog(Gtk.Window):
    """Fenêtre affichant un tableau de bord complet : code du projet, noms détaillés de
    tous les éléments Django, état système, graphiques, et schéma de liaison complet."""

    def __init__(self, parent, project_root, show_toast=None):
        super().__init__(title="📊 Tableau de bord du projet")
        self.set_transient_for(parent)
        self.set_default_size(920, 760)
        # La fenêtre construit sa propre Adw.HeaderBar juste en dessous : sans
        # set_decorated(False), GTK affiche EN PLUS sa barre de titre système
        # avec le même texte -> double titre superposé.
        self.set_decorated(False)
        self.set_resizable(True)
        self.add_css_class("rounded-dialog")
        self.project_root = Path(project_root) if project_root else None
        self.show_toast = show_toast or (lambda msg: None)
        self._tmp_files = []
        self._graph_png_path = None

        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        header = Adw.HeaderBar()
        # Sans décoration système, il faut demander explicitement les boutons
        # réduire/agrandir/fermer sur notre barre custom (voir cache_manager_dialog.py).
        header.set_show_end_title_buttons(True)
        header.set_decoration_layout("minimize,maximize,close")
        self.btn_export_graph = Gtk.Button(label="💾 Exporter le schéma (PNG)")
        self.btn_export_graph.set_sensitive(False)
        self.btn_export_graph.connect("clicked", self._on_export_graph)
        header.pack_end(self.btn_export_graph)
        btn_refresh = Gtk.Button(label="🔄 Actualiser")
        btn_refresh.connect("clicked", lambda *_: self._start_scan())
        header.pack_end(btn_refresh)
        root_box.append(header)

        self.scroll = Gtk.ScrolledWindow(); self.scroll.set_vexpand(True); self.scroll.set_hexpand(True)
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        set_margins(self.content, 16)
        self.scroll.set_child(self.content)
        root_box.append(self.scroll)

        self.set_child(root_box)

        self.spinner = Gtk.Spinner(); self.spinner.set_size_request(32, 32)
        self.status_label = Gtk.Label(label="Analyse en cours…")
        self.content.append(self.spinner); self.content.append(self.status_label)

        if not self.project_root or not self.project_root.exists():
            self.status_label.set_text("⚠️ Aucun projet chargé.")
            self.spinner.stop()
        else:
            self.spinner.start()
            self._start_scan()

    # ── SCAN ─────────────────────────────────────────────────────────
    def _start_scan(self):
        while (child := self.content.get_first_child()):
            self.content.remove(child)
        self.btn_export_graph.set_sensitive(False)
        self._graph_png_path = None
        self.spinner = Gtk.Spinner(); self.spinner.set_size_request(32, 32); self.spinner.start()
        self.status_label = Gtk.Label(label="Analyse en cours (parsing AST de tous les fichiers)…")
        self.content.append(self.spinner); self.content.append(self.status_label)
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        try:
            stats = self._collect_project_stats()
            sys_stats = self._collect_system_stats()
            graph = self._build_link_graph(stats) if HAS_NETWORKX else None
        except Exception as e:
            global_log(f"❌ Erreur scan dashboard: {type(e).__name__} - {e}")
            GLib.idle_add(self._show_error, str(e))
            return
        GLib.idle_add(self._render_dashboard, stats, sys_stats, graph)

    def _collect_project_stats(self) -> dict:
        project_root = self.project_root
        stdlib_names = set(getattr(sys, "stdlib_module_names", ())) or _FALLBACK_STDLIB

        # Passe 1 : détection des apps Django (dossiers contenant apps.py/models.py)
        django_apps = set()
        for dirpath, dirnames, _ in os.walk(project_root):
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS and not d.endswith(".egg-info")]
            try:
                names_here = os.listdir(dirpath)
            except Exception:
                names_here = []
            if "apps.py" in names_here or "models.py" in names_here:
                django_apps.add(Path(dirpath).name)

        ext_lines = Counter(); ext_files = Counter()
        total_files = 0; total_lines = 0; total_size = 0

        models, views, forms, serializers, admin_regs, commands = [], [], [], [], [], []
        urls, templates_all = [], []
        view_template_edges = []  # (app, view_name, template_path)
        settings_files = []
        settings_info = {"debug": None, "db_engines": set(), "installed_apps": []}
        imports_classified = {"stdlib": Counter(), "django": Counter(), "locale": Counter(), "tierce": Counter()}
        file_modules = {}  # rel_path -> {"app": app, "modules": set(third-party/django top-level names)}

        local_names = {a.lower() for a in django_apps}
        local_names.add(project_root.name.lower())

        for dirpath, dirnames, filenames in os.walk(project_root):
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS and not d.endswith(".egg-info")]
            for fname in filenames:
                fpath = Path(dirpath) / fname
                ext = fpath.suffix.lower()
                total_files += 1
                try:
                    total_size += fpath.stat().st_size
                except Exception:
                    pass

                if ext == ".html":
                    try:
                        templates_all.append(str(fpath.relative_to(project_root)))
                    except Exception:
                        pass

                if ext not in CODE_EXTENSIONS:
                    continue

                ext_files[ext] += 1
                try:
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                lines = content.splitlines(keepends=True)
                total_lines += len(lines); ext_lines[ext] += len(lines)

                rel = str(fpath.relative_to(project_root))
                app = _app_for_file(fpath, project_root, django_apps)

                if ext != ".py":
                    continue

                # Commandes de gestion : <app>/management/commands/<name>.py
                if fpath.parent.name == "commands" and "management" in fpath.parts and fname != "__init__.py":
                    commands.append({"name": fpath.stem, "app": app, "file": rel})

                # settings.py (racine ou dossier settings/)
                if fname == "settings.py" or (fname.endswith(".py") and "settings" in Path(dirpath).parts and fname != "__init__.py"):
                    settings_files.append(rel)
                    m = DEBUG_RE.search(content)
                    if m and settings_info["debug"] is None:
                        settings_info["debug"] = m.group(1)
                    settings_info["db_engines"].update(DB_ENGINE_RE.findall(content))
                    apps_match = INSTALLED_APPS_RE.search(content)
                    if apps_match and not settings_info["installed_apps"]:
                        settings_info["installed_apps"] = re.findall(r"""['"]([\w\.]+)['"]""", apps_match.group(1))

                # Inspection directe de l'AST (imports + éléments Django)
                analysis = _analyze_python_file(content, fpath)

                for m in analysis["models"]:
                    models.append({"name": m["name"], "app": app, "file": rel, "relations": m.get("relations", [])})
                for v in analysis["views"]:
                    views.append({
                        "name": v["name"], "kind": v["kind"], "app": app, "file": rel,
                        "model_refs": v.get("model_refs", []), "permission_refs": v.get("permission_refs", []),
                        "group_refs": v.get("group_refs", []), "action": v.get("action", ""),
                    })
                for name in analysis["forms"]:
                    forms.append({"name": name["name"], "app": app, "file": rel, "meta_model": name.get("meta_model", "")})
                for name in analysis["serializers"]:
                    serializers.append({"name": name["name"], "app": app, "file": rel, "meta_model": name.get("meta_model", "")})
                for model_ref in analysis["admin_registrations"]:
                    admin_regs.append({"model": model_ref, "app": app, "file": rel})
                if fname == "urls.py":
                    for u in analysis["urls"]:
                        u2 = dict(u); u2["app"] = app; u2["file"] = rel
                        urls.append(u2)
                for tpl in analysis["templates_referenced"]:
                    for v in analysis["views"]:
                        view_template_edges.append((app, v["name"], tpl))

                # Imports — classification directe (stdlib / django / locale / tierce)
                mods_here = set()
                for mod in analysis["imports"]:
                    top = mod.split(".")[0]
                    if not top or top.startswith("_"):
                        continue
                    if top in stdlib_names:
                        imports_classified["stdlib"][top] += 1
                    elif top == "django":
                        imports_classified["django"][top] += 1
                    elif top.lower() in local_names:
                        imports_classified["locale"][top] += 1
                    else:
                        imports_classified["tierce"][top] += 1
                        mods_here.add(top)
                    if top == "django" or top.lower() not in local_names and top not in stdlib_names:
                        mods_here.add(top)
                file_modules[rel] = {"app": app, "modules": mods_here}

        # Apps déclarées dans INSTALLED_APPS, classées django / locale / tierce
        apps_classified = {"django": [], "locale": [], "tierce": []}
        for entry in settings_info["installed_apps"]:
            short = entry.split(".")[-1].lower()
            if entry.startswith("django."):
                apps_classified["django"].append(entry)
            elif short in local_names or entry.lower() in local_names:
                apps_classified["locale"].append(entry)
            else:
                apps_classified["tierce"].append(entry)

        # requirements.txt à la racine, si présent
        requirements = []
        req_path = project_root / "requirements.txt"
        if req_path.exists():
            try:
                for line in req_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    m = re.match(r"^([A-Za-z0-9_\-\.]+)", line)
                    if m:
                        requirements.append(m.group(1))
            except Exception:
                pass

        return {
            "total_files": total_files, "total_lines": total_lines,
            "total_size_mb": total_size / (1024 * 1024),
            "django_apps": sorted(django_apps),
            "models": models, "views": views, "forms": forms, "serializers": serializers,
            "admin_registrations": admin_regs, "commands": commands,
            "urls": urls, "templates_all": sorted(templates_all),
            "view_template_edges": view_template_edges,
            "settings_files": settings_files, "settings_info": settings_info,
            "apps_classified": apps_classified, "requirements": requirements,
            "imports_classified": imports_classified, "file_modules": file_modules,
            "ext_lines": ext_lines, "ext_files": ext_files,
        }

    def _collect_system_stats(self) -> dict:
        if not HAS_PSUTIL:
            return {}
        try:
            cpu = psutil.cpu_percent(interval=0.4)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage(str(self.project_root))
            return {
                "cpu_percent": cpu,
                "ram_used_gb": mem.used / (1024 ** 3),
                "ram_total_gb": mem.total / (1024 ** 3),
                "ram_percent": mem.percent,
                "disk_used_gb": disk.used / (1024 ** 3),
                "disk_total_gb": disk.total / (1024 ** 3),
                "disk_percent": disk.percent,
            }
        except Exception as e:
            global_log(f"⚠️ Erreur stats système: {e}")
            return {}

    # ── SCHÉMA DE LIAISON (graphe complet, pas un simple diagramme) ────
    def _build_link_graph(self, stats: dict):
        """Construit le graphe orienté des liaisons entre tous les éléments détectés :
        App → Modèle / Vue / URL / Template / Formulaire / Serializer / Admin / Commande,
        App → Module (Django ou tiers, d'après l'inspection directe des imports),
        URL → Vue (résolution par nom), Vue → Template (référencé dans le même fichier)."""
        g = nx.DiGraph()

        def add(node_id, ntype, **attrs):
            if not g.has_node(node_id):
                g.add_node(node_id, type=ntype, **attrs)

        for app in stats["django_apps"]:
            add(f"app:{app}", "app")

        for m in stats["models"]:
            add(f"app:{m['app']}", "app")
            nid = f"model:{m['app']}.{m['name']}"
            add(nid, "model")
            g.add_edge(f"app:{m['app']}", nid)

        # Modèle → Modèle : relations FK / OneToOne / ManyToMany détectées dans les champs.
        model_by_name = {}
        for m in stats["models"]:
            model_by_name.setdefault(m["name"], f"model:{m['app']}.{m['name']}")
        for m in stats["models"]:
            src = f"model:{m['app']}.{m['name']}"
            for rel_target in m.get("relations", []):
                tgt = model_by_name.get(rel_target)
                if tgt and tgt != src:
                    g.add_edge(src, tgt)

        for v in stats["views"]:
            add(f"app:{v['app']}", "app")
            vnid = f"view:{v['app']}.{v['name']}"
            add(vnid, "view")
            g.add_edge(f"app:{v['app']}", vnid)

            # Vue → Modèle(s) utilisés
            for mref in v.get("model_refs", []):
                tgt = model_by_name.get(mref)
                if tgt:
                    g.add_edge(vnid, tgt)

            # Vue → Droit / Permission (nœud partagé si plusieurs vues exigent le même droit)
            for perm in v.get("permission_refs", []):
                pnid = f"permission:{perm}"
                add(pnid, "permission")
                g.add_edge(vnid, pnid)

            # Vue → Groupe (nœud partagé si plusieurs vues vérifient le même groupe)
            for grp in v.get("group_refs", []):
                gnid = f"group:{grp}"
                add(gnid, "group")
                g.add_edge(vnid, gnid)

            # Vue → Action (Liste / Création / Modification / Suppression / Détail…)
            action = v.get("action")
            if action:
                anid = f"action:{action}"
                add(anid, "action")
                g.add_edge(vnid, anid)

        for f in stats["forms"]:
            add(f"app:{f['app']}", "app")
            nid = f"form:{f['app']}.{f['name']}"
            add(nid, "form")
            g.add_edge(f"app:{f['app']}", nid)
            mm = (f.get("meta_model") or "").split(".")[-1]
            if mm:
                target = next((m for m in stats["models"] if m["name"] == mm), None)
                if target:
                    g.add_edge(nid, f"model:{target['app']}.{target['name']}")

        for s in stats["serializers"]:
            add(f"app:{s['app']}", "app")
            nid = f"serializer:{s['app']}.{s['name']}"
            add(nid, "serializer")
            g.add_edge(f"app:{s['app']}", nid)
            mm = (s.get("meta_model") or "").split(".")[-1]
            if mm:
                target = next((m for m in stats["models"] if m["name"] == mm), None)
                if target:
                    g.add_edge(nid, f"model:{target['app']}.{target['name']}")

        for a in stats["admin_registrations"]:
            add(f"app:{a['app']}", "app")
            nid = f"admin:{a['app']}.{a['model']}"
            add(nid, "admin")
            g.add_edge(f"app:{a['app']}", nid)
            mm = (a.get("model") or "").split(".")[-1]
            target = next((m for m in stats["models"] if m["name"] == mm and m["app"] == a["app"]), None) \
                or next((m for m in stats["models"] if m["name"] == mm), None)
            if target:
                g.add_edge(nid, f"model:{target['app']}.{target['name']}")

        for c in stats["commands"]:
            add(f"app:{c['app']}", "app")
            nid = f"command:{c['app']}.{c['name']}"
            add(nid, "command")
            g.add_edge(f"app:{c['app']}", nid)

        view_names_by_app = {}
        for v in stats["views"]:
            view_names_by_app.setdefault(v["app"], []).append(v["name"])

        for u in stats["urls"]:
            app = u.get("app", "?")
            add(f"app:{app}", "app")
            label = u.get("route") or u.get("name") or f"url#{len(g)}"
            nid = f"url:{app}:{label}:{u.get('file','')}"
            add(nid, "url")
            g.add_edge(f"app:{app}", nid)
            expr = u.get("view_expr") or ""
            if "include(" in expr:
                inc_m = re.search(r"include\(\s*['\"]([\w\.]+)", expr)
                if inc_m:
                    target_app = inc_m.group(1).split(".")[0]
                    add(f"app:{target_app}", "app")
                    g.add_edge(nid, f"app:{target_app}")
            else:
                for vname in view_names_by_app.get(app, []):
                    if not vname:
                        continue
                    # Couvre "vue", "vue.as_view()", "module.vue", "module.vue.as_view()"
                    if re.search(rf"(^|\.){re.escape(vname)}(\.as_view\(\))?\s*$", expr) or vname in expr:
                        g.add_edge(nid, f"view:{app}.{vname}")
                        break

        for path_str in stats["templates_all"]:
            add(f"template:{path_str}", "template")

        for app, view_name, tpl in stats["view_template_edges"]:
            vnid = f"view:{app}.{view_name}"
            matches = [t for t in stats["templates_all"] if t.endswith(tpl) or tpl in t]
            tid = f"template:{matches[0]}" if matches else f"template:{tpl}"
            add(tid, "template")
            if g.has_node(vnid):
                g.add_edge(vnid, tid)

        for rel, info in stats["file_modules"].items():
            app = info["app"]
            if not info["modules"]:
                continue
            add(f"app:{app}", "app")
            for mod in info["modules"]:
                mtype = "django" if mod == "django" else "tierce"
                nid = f"{mtype}:{mod}"
                add(nid, mtype)
                g.add_edge(f"app:{app}", nid)

        return g

    def _on_export_graph(self, *_):
        if not self._graph_png_path or not Path(self._graph_png_path).exists():
            self.show_toast("❌ Aucun schéma à exporter")
            return
        try:
            dest_dir = Path.home() / "Desktop"
            if not dest_dir.exists():
                dest_dir = Path.home()
            dest = dest_dir / f"gykhamine_schema_{self.project_root.name}.png"
            import shutil
            shutil.copy(self._graph_png_path, dest)
            self.show_toast(f"💾 Schéma exporté : {dest}")
        except Exception as e:
            global_log(f"❌ Erreur export schéma: {e}")
            self.show_toast("❌ Échec de l'export du schéma")

    # ── RENDU ────────────────────────────────────────────────────────
    def _show_error(self, msg):
        while (child := self.content.get_first_child()):
            self.content.remove(child)
        self.content.append(Gtk.Label(label=f"❌ Erreur d'analyse : {msg}"))

    def _section_title(self, text):
        lbl = Gtk.Label(label=text); lbl.add_css_class("control-section-title"); lbl.set_xalign(0)
        return lbl

    def _stat_row(self, label, value):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        l1 = Gtk.Label(label=label); l1.set_xalign(0); l1.set_hexpand(True)
        l2 = Gtk.Label(label=str(value)); l2.add_css_class("heading"); l2.set_xalign(1)
        box.append(l1); box.append(l2)
        return box

    def _list_section(self, title: str, lines: list, empty_text="Aucun élément détecté."):
        """Section repliable listant des noms complets (pas juste un compteur) — pratique
        pour les listes potentiellement longues (vues, urls, templates, modules...)."""
        expander = Gtk.Expander(label=f"{title} ({len(lines)})")
        expander.set_margin_top(4)
        if not lines:
            lbl = Gtk.Label(label=empty_text); lbl.set_xalign(0); lbl.add_css_class("dim-label")
            set_margins(lbl, 6)
            expander.set_child(lbl)
            return expander
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(min(280, 22 * min(len(lines), 14) + 10))
        scroll.set_max_content_height(340)
        tv = Gtk.TextView(); tv.set_editable(False); tv.set_monospace(True)
        tv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR); tv.set_top_margin(6); tv.set_bottom_margin(6)
        tv.set_left_margin(8); tv.set_right_margin(8)
        tv.get_buffer().set_text("\n".join(lines))
        scroll.set_child(tv)
        expander.set_child(scroll)
        return expander

    def _render_dashboard(self, stats: dict, sys_stats: dict, graph):
        while (child := self.content.get_first_child()):
            self.content.remove(child)

        # Résumé projet
        self.content.append(self._section_title(f"📁 Projet : {self.project_root.name}"))
        self.content.append(self._stat_row("Fichiers au total", stats["total_files"]))
        self.content.append(self._stat_row("Lignes de code (fichiers reconnus)", stats["total_lines"]))
        self.content.append(self._stat_row("Taille du projet", f"{stats['total_size_mb']:.1f} Mo"))
        self.content.append(self._stat_row("Apps Django détectées", len(stats["django_apps"])))
        if stats["django_apps"]:
            apps_lbl = Gtk.Label(label="Apps : " + ", ".join(stats["django_apps"]))
            apps_lbl.set_xalign(0); apps_lbl.set_wrap(True); apps_lbl.add_css_class("dim-label")
            self.content.append(apps_lbl)

        self.content.append(Gtk.Separator())

        # Éléments Django — noms complets, listes repliables
        self.content.append(self._section_title("🧩 Éléments Django détectés (noms complets)"))
        self.content.append(self._list_section(
            "🏛 Modèles", [f"{m['app']} · {m['name']}  ({m['file']})" for m in stats["models"]]))
        self.content.append(self._list_section(
            "⚡ Vues", [f"{v['app']} · {v['name']}  [{v['kind']}]  ({v['file']})" for v in stats["views"]]))
        self.content.append(self._list_section(
            "🧭 Routes d'URL",
            [f"{u['app']} · /{u.get('route','')}"
             + (f"  → {u['view_expr']}" if u.get("view_expr") else "")
             + (f"  [name={u['name']}]" if u.get("name") else "")
             for u in stats["urls"]]))
        self.content.append(self._list_section("🌐 Templates (.html)", stats["templates_all"]))
        self.content.append(self._list_section(
            "📝 Formulaires", [f"{f['app']} · {f['name']}  ({f['file']})" for f in stats["forms"]]))
        self.content.append(self._list_section(
            "🔁 Serializers (DRF)", [f"{s['app']} · {s['name']}  ({s['file']})" for s in stats["serializers"]]))
        self.content.append(self._list_section(
            "🛠 Enregistrements admin", [f"{a['app']} · {a['model']}  ({a['file']})" for a in stats["admin_registrations"]]))
        self.content.append(self._list_section(
            "⌨️ Commandes manage.py", [f"{c['app']} · {c['name']}  ({c['file']})" for c in stats["commands"]]))

        self.content.append(Gtk.Separator())

        # Settings
        self.content.append(self._section_title("⚙️ Settings"))
        si = stats["settings_info"]
        self.content.append(self._stat_row("Fichiers settings détectés", len(stats["settings_files"])))
        self.content.append(self._stat_row("DEBUG", si["debug"] if si["debug"] is not None else "non trouvé"))
        self.content.append(self._stat_row("Moteur(s) de base de données", ", ".join(sorted(si["db_engines"])) or "non détecté"))
        self.content.append(self._stat_row("INSTALLED_APPS (total)", len(si["installed_apps"])))
        if stats["settings_files"]:
            lbl = Gtk.Label(label=", ".join(stats["settings_files"]))
            lbl.set_xalign(0); lbl.set_wrap(True); lbl.add_css_class("dim-label")
            self.content.append(lbl)

        self.content.append(Gtk.Separator())

        # Modules & apps — issus de l'inspection directe des imports (AST)
        self.content.append(self._section_title("📦 Modules & apps (inspection directe des imports)"))
        ac = stats["apps_classified"]
        ic = stats["imports_classified"]
        self.content.append(self._stat_row("Apps Django built-in (INSTALLED_APPS)", len(ac["django"])))
        self.content.append(self._stat_row("Apps locales du projet (INSTALLED_APPS)", len(ac["locale"])))
        self.content.append(self._stat_row("Apps / packages tiers (INSTALLED_APPS)", len(ac["tierce"])))
        self.content.append(self._list_section(
            "📦 Modules tiers importés (top-level, via ast)",
            [f"{mod}  —  importé dans {count} fichier(s)" for mod, count in ic["tierce"].most_common()]))
        self.content.append(self._list_section(
            "🎯 Modules Django importés (sous-modules confondus)",
            [f"django  —  importé dans {count} fichier(s)" for mod, count in ic["django"].most_common()]))
        if stats["requirements"]:
            self.content.append(self._list_section("📄 requirements.txt", stats["requirements"]))

        self.content.append(Gtk.Separator())

        # État système
        self.content.append(self._section_title("🖥️ État du système"))
        if sys_stats:
            self.content.append(self._stat_row("CPU", f"{sys_stats['cpu_percent']:.0f} %"))
            self.content.append(self._stat_row("RAM", f"{sys_stats['ram_used_gb']:.1f} / {sys_stats['ram_total_gb']:.1f} Go ({sys_stats['ram_percent']:.0f}%)"))
            self.content.append(self._stat_row("Disque (partition du projet)", f"{sys_stats['disk_used_gb']:.1f} / {sys_stats['disk_total_gb']:.1f} Go ({sys_stats['disk_percent']:.0f}%)"))
        else:
            self.content.append(Gtk.Label(label="psutil non disponible — installez-le avec `pip install psutil` pour voir l'état système."))

        self.content.append(Gtk.Separator())

        # Graphiques seaborn (répartitions)
        self.content.append(self._section_title("📈 Graphiques"))
        if not HAS_CHARTS:
            self.content.append(Gtk.Label(label="seaborn/matplotlib non disponibles — installez-les avec `pip install seaborn matplotlib` pour voir les graphiques."))
        else:
            img1 = self._chart_lines_by_ext(stats["ext_lines"])
            if img1: self.content.append(img1)
            img2 = self._chart_apps_breakdown(stats["apps_classified"])
            if img2: self.content.append(img2)
            img3 = self._chart_system_usage(sys_stats)
            if img3: self.content.append(img3)

        self.content.append(Gtk.Separator())

        # Schéma de liaison complet (graphe, pas une simple visualisation)
        self.content.append(self._section_title("🕸️ Schéma de liaison complet du projet"))
        hint = Gtk.Label(label="Graphe de toutes les liaisons détectées : App ↔ Modèle / Vue / URL / Template / "
                                "Formulaire / Serializer / Admin / Commande / Module (Django & tiers).")
        hint.set_xalign(0); hint.set_wrap(True); hint.add_css_class("dim-label")
        self.content.append(hint)
        if not HAS_NETWORKX:
            self.content.append(Gtk.Label(label="networkx non disponible — installez-le avec `pip install networkx` pour voir le schéma de liaison."))
        elif not HAS_CHARTS:
            self.content.append(Gtk.Label(label="matplotlib est requis (en plus de networkx) pour dessiner le schéma."))
        elif graph is None or graph.number_of_nodes() == 0:
            self.content.append(Gtk.Label(label="Aucune donnée exploitable pour construire le schéma de liaison."))
        else:
            img4 = self._chart_link_graph(graph)
            if img4:
                self.content.append(img4)
                self.btn_export_graph.set_sensitive(True)

        self.spinner = None
        self.status_label = None

    # ── CHARTS ───────────────────────────────────────────────────────
    def _new_tmp_png(self) -> str:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        self._tmp_files.append(tmp.name)
        return tmp.name

    def _chart_lines_by_ext(self, ext_lines: Counter):
        if not ext_lines:
            return None
        try:
            data = ext_lines.most_common(10)
            exts = [e for e, _ in data]
            values = [v for _, v in data]

            fig, ax = plt.subplots(figsize=(7, 3.2))
            sns.barplot(x=values, y=exts, hue=exts, palette="crest", legend=False, ax=ax)
            ax.set_title("Lignes de code par type de fichier")
            ax.set_xlabel("Lignes"); ax.set_ylabel("")
            fig.tight_layout()

            path = self._new_tmp_png()
            fig.savefig(path, dpi=120, transparent=False)
            plt.close(fig)

            picture = Gtk.Picture.new_for_filename(path)
            picture.set_content_fit(Gtk.ContentFit.CONTAIN)
            picture.set_size_request(-1, 260)
            return picture
        except Exception as e:
            global_log(f"⚠️ Erreur graphique lignes/ext: {e}")
            return None

    def _chart_apps_breakdown(self, apps_classified: dict):
        total = sum(len(v) for v in apps_classified.values())
        if not total:
            return None
        try:
            labels = ["Django (built-in)", "Locales (projet)", "Tierces (packages)"]
            values = [len(apps_classified["django"]), len(apps_classified["locale"]), len(apps_classified["tierce"])]

            fig, ax = plt.subplots(figsize=(7, 2.8))
            sns.barplot(x=labels, y=values, hue=labels, palette="mako", legend=False, ax=ax)
            ax.set_ylabel("Nombre d'apps")
            ax.set_title("Répartition des apps installées (INSTALLED_APPS)")
            fig.tight_layout()

            path = self._new_tmp_png()
            fig.savefig(path, dpi=120, transparent=False)
            plt.close(fig)

            picture = Gtk.Picture.new_for_filename(path)
            picture.set_content_fit(Gtk.ContentFit.CONTAIN)
            picture.set_size_request(-1, 220)
            return picture
        except Exception as e:
            global_log(f"⚠️ Erreur graphique répartition apps: {e}")
            return None

    def _chart_system_usage(self, sys_stats: dict):
        if not sys_stats:
            return None
        try:
            labels = ["CPU", "RAM", "Disque"]
            values = [sys_stats.get("cpu_percent", 0), sys_stats.get("ram_percent", 0), sys_stats.get("disk_percent", 0)]

            fig, ax = plt.subplots(figsize=(7, 2.8))
            sns.barplot(x=labels, y=values, hue=labels, palette="flare", legend=False, ax=ax)
            ax.set_ylim(0, 100)
            ax.set_ylabel("% utilisé")
            ax.set_title("Utilisation du système")
            fig.tight_layout()

            path = self._new_tmp_png()
            fig.savefig(path, dpi=120, transparent=False)
            plt.close(fig)

            picture = Gtk.Picture.new_for_filename(path)
            picture.set_content_fit(Gtk.ContentFit.CONTAIN)
            picture.set_size_request(-1, 220)
            return picture
        except Exception as e:
            global_log(f"⚠️ Erreur graphique système: {e}")
            return None

    def _chart_link_graph(self, graph):
        """Dessine le schéma de liaison complet (node-link diagram) : chaque type
        d'élément est un nœud coloré, chaque relation détectée est une arête orientée.
        Taille de la figure et du rendu adaptée au nombre de nœuds pour rester lisible
        malgré l'exhaustivité (tous les éléments détectés sont inclus, pas un échantillon)."""
        try:
            n = graph.number_of_nodes()
            if n == 0:
                return None
            side = max(10, min(34, 8 + n * 0.12))
            fig, ax = plt.subplots(figsize=(side, side * 0.72))

            k = 1.4 / (n ** 0.5) if n > 1 else 1.0
            # Le layout à ressorts est en O(n²) par itération : sur un projet avec
            # beaucoup d'apps/modules (des centaines de nœuds), 60 itérations fixes
            # faisaient tourner un cœur CPU à fond pendant plusieurs secondes à chaque
            # analyse. On réduit le nombre d'itérations quand le graphe grossit —
            # le rendu reste lisible avec moins de passes de relaxation.
            if n <= 150:
                iterations = 60
            elif n <= 400:
                iterations = 35
            elif n <= 900:
                iterations = 20
            else:
                iterations = 12
            pos = nx.spring_layout(graph, k=k, seed=42, iterations=iterations)

            for ntype, style in GRAPH_NODE_STYLE.items():
                nodelist = [nid for nid, d in graph.nodes(data=True) if d.get("type") == ntype]
                if not nodelist:
                    continue
                nx.draw_networkx_nodes(
                    graph, pos, nodelist=nodelist, node_color=style["color"],
                    node_size=style["size"], alpha=0.9, ax=ax, label=f"{style['label']} ({len(nodelist)})"
                )

            # Arêtes en multicolore selon le nœud SOURCE de la relation : plus
            # facile de suivre visuellement quelles liaisons partent d'une
            # App, d'un Modèle, d'une Vue, etc., au lieu d'un gris uniforme.
            # On garde une couleur de repli grise pour un type non répertorié.
            edgelist = list(graph.edges())
            edge_colors = []
            for u, _v in edgelist:
                src_type = graph.nodes[u].get("type")
                edge_colors.append(GRAPH_NODE_STYLE.get(src_type, {}).get("color", "#999999"))
            nx.draw_networkx_edges(graph, pos, edgelist=edgelist, alpha=0.5, arrows=True, arrowsize=6, width=0.7, ax=ax, edge_color=edge_colors)

            # Étiquettes : TOUS les nœuds sont maintenant nommés (avant, seuls
            # les nœuds structurants "app"/"django"/"tierce" l'étaient — le
            # reste apparaissait comme des points anonymes, illisible pour
            # savoir à quoi correspond quoi). Pour rester lisible malgré le
            # volume, les nœuds structurants gardent une police plus grande,
            # les autres une police réduite — et un léger fond blanc semi-
            # transparent derrière chaque texte pour qu'il ressorte des
            # arêtes qui se croisent partout.
            MAX_LABEL_CHARS = 10

            def _short_label(raw: str) -> str:
                name = raw.split(":", 1)[-1]
                if len(name) > MAX_LABEL_CHARS:
                    return name[:MAX_LABEL_CHARS - 1] + "…"
                return name

            label_types = {"app", "django", "tierce"}
            major_labels = {nid: _short_label(nid) for nid, d in graph.nodes(data=True) if d.get("type") in label_types}
            minor_labels = {nid: _short_label(nid) for nid, d in graph.nodes(data=True) if d.get("type") not in label_types}

            label_bbox = dict(facecolor="white", alpha=0.65, edgecolor="none", pad=0.5)
            nx.draw_networkx_labels(graph, pos, labels=minor_labels, font_size=6, ax=ax, bbox=label_bbox)
            nx.draw_networkx_labels(graph, pos, labels=major_labels, font_size=11, font_weight="bold", ax=ax, bbox=label_bbox)

            ax.set_title(f"Schéma de liaison complet — {n} nœuds, {graph.number_of_edges()} liaisons", fontsize=13)
            ax.legend(loc="upper left", fontsize=10, framealpha=0.85, markerscale=0.7, ncol=2)
            ax.axis("off")
            fig.tight_layout()

            path = self._new_tmp_png()
            fig.savefig(path, dpi=200, transparent=False)
            plt.close(fig)
            self._graph_png_path = path

            return self._make_zoomable_picture(path)
        except Exception as e:
            global_log(f"⚠️ Erreur schéma de liaison: {e}")
            return None

    def _make_zoomable_picture(self, image_path: str):
        """Enveloppe une image dans un conteneur zoomable/déplaçable : boutons +/-,
        molette+Ctrl, pincement tactile. Nécessaire pour un schéma dense où le texte
        est illisible à l'échelle par défaut."""
        picture = Gtk.Picture.new_for_filename(image_path)
        picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        pixbuf = None
        try:
            from gi.repository import GdkPixbuf
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(image_path)
            base_w, base_h = pixbuf.get_width(), pixbuf.get_height()
        except Exception:
            base_w, base_h = 1400, 1000
        # Taille d'affichage initiale (avant zoom) : limitée pour tenir dans le panneau
        display_scale = min(1.0, 1100 / base_w) if base_w else 1.0
        state = {"zoom": display_scale}

        def apply_zoom():
            picture.set_size_request(int(base_w * state["zoom"]), int(base_h * state["zoom"]))

        apply_zoom()

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.set_size_request(-1, 560)
        scroller.set_child(picture)

        def zoom_by(factor):
            state["zoom"] = max(0.2, min(4.0, state["zoom"] * factor))
            apply_zoom()

        def on_scroll(controller, dx, dy):
            zoom_by(1.1 if dy < 0 else (1 / 1.1))
            return True

        scroll_ctrl = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.VERTICAL)
        scroll_ctrl.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        def on_scroll_ctrl(controller, dx, dy):
            state_mods = controller.get_current_event_state() if hasattr(controller, "get_current_event_state") else 0
            if state_mods & Gdk.ModifierType.CONTROL_MASK:
                zoom_by(1.1 if dy < 0 else (1 / 1.1))
                return True
            return False
        scroll_ctrl.connect("scroll", on_scroll_ctrl)
        scroller.add_controller(scroll_ctrl)

        zoom_gesture = Gtk.GestureZoom.new()
        zoom_gesture.connect("scale-changed", lambda g, scale: zoom_by(scale))
        scroller.add_controller(zoom_gesture)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.set_margin_bottom(4)
        btn_out = Gtk.Button(label="🔍-"); btn_out.set_tooltip_text("Zoom arrière")
        btn_out.connect("clicked", lambda *_: zoom_by(1 / 1.25))
        btn_in = Gtk.Button(label="🔍+"); btn_in.set_tooltip_text("Zoom avant")
        btn_in.connect("clicked", lambda *_: zoom_by(1.25))
        btn_reset = Gtk.Button(label="⟲ 100%"); btn_reset.set_tooltip_text("Réinitialiser le zoom")
        def on_reset(*_):
            state["zoom"] = display_scale
            apply_zoom()
        btn_reset.connect("clicked", on_reset)
        hint = Gtk.Label(label="Molette+Ctrl ou pincement pour zoomer")
        hint.add_css_class("dim-label")
        toolbar.append(btn_out); toolbar.append(btn_in); toolbar.append(btn_reset); toolbar.append(hint)

        wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        wrapper.append(toolbar)
        wrapper.append(scroller)
        return wrapper
