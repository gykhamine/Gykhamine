"""Module généré automatiquement depuis widgets.py - Classe FilePanel"""
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
TYPE_ICONS = {"import": "📦", "class": "🏛", "function": "⚡", "separator": "─", "comment": "💬", "other": "▪", "template": "🌐", "template_part": "🌐", "django_block": "🧩", "style": "🎨", "style_rule": "🎨", "script": "⚙️", "script_block": "⚡", "c_block": "⚙️", "logic_block": "🔁"}

# Extensions to ignore in file explorer
IGNORED_DIRS = {"__pycache__", "node_modules", ".git", ".venv", "venv", ".mypy_cache", ".pytest_cache", ".tox", "dist", "build", ".eggs", "*.egg-info"}

EXT_ICONS = {
    '.css': '🎨', '.scss': '🎨', '.sass': '🎨', '.less': '🎨',
    '.js': '⚡', '.jsx': '⚡', '.ts': '⚡', '.tsx': '⚡', '.mjs': '⚡',
    '.c': '⚙️', '.cpp': '⚙️', '.h': '⚙️', '.hpp': '⚙️', '.cc': '⚙️',
    '.sh': '📜', '.bash': '📜', '.zsh': '📜',
    '.html': '🌐', '.htm': '🌐', '.jinja': '🌐', '.jinja2': '🌐',
    '.py': '🐍', '.pyw': '🐍',
    '.json': '📋', '.xml': '📋', '.yaml': '📋', '.yml': '📋', '.toml': '📋',
    '.md': '📝', '.rst': '📝', '.txt': '📄',
    '.sql': '🗃', '.db': '🗃', '.sqlite': '🗃',
    '.rb': '💎', '.go': '🔵', '.rs': '🦀', '.java': '☕', '.kt': '🟣',
    '.php': '🐘', '.lua': '🌙',
    '.png': '🖼', '.jpg': '🖼', '.jpeg': '🖼', '.gif': '🖼', '.svg': '🖼', '.ico': '🖼',
    '.zip': '📦', '.tar': '📦', '.gz': '📦',
    '.dockerfile': '🐳', '.env': '🔒',
}


class FilePanel(Gtk.Box):
    def __init__(self, on_file_select, on_project_select, on_file_created, on_file_imported):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.on_file_select = on_file_select
        self.on_project_select = on_project_select
        self.on_file_created = on_file_created
        self.on_file_imported = on_file_imported
        self.project_root = None
        self.tree_store = Gtk.TreeStore(str, str, bool)  # name, full_path, is_folder
        self.show_hidden = False
        self.clipboard_action = None
        self.clipboard_path = None
        self.watcher = None
        self._tree_path_map = {}  # full_path -> TreePath for smart refresh
        
        lbl = Gtk.Label(label="📁 Projet"); lbl.add_css_class("panel-title"); lbl.set_xalign(0); lbl.set_margin_start(12); lbl.set_margin_top(10); lbl.set_margin_bottom(6)
        self.append(lbl); self.append(Gtk.Separator())
        
        # Search bar
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        set_margins(search_box, 4)
        search_box.set_margin_start(8)
        search_box.set_margin_end(8)
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("🔍 Rechercher...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("changed", self._on_search_changed)
        search_box.append(self.search_entry)
        self.append(search_box)
        
        self.stack = Gtk.Stack(); self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        
        scroll_files = Gtk.ScrolledWindow(); scroll_files.set_vexpand(True); scroll_files.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.tree_view = Gtk.TreeView(model=self.tree_store); self.tree_view.set_headers_visible(False); self.tree_view.add_css_class("file-tree-view")
        self.tree_view.set_enable_search(True)
        self.tree_view.set_search_column(0)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Fichiers", renderer, text=0)
        column.set_cell_data_func(renderer, self._on_tree_cell_data)
        self.tree_view.append_column(column)
        self.tree_view.connect("row-activated", self._on_row_activated)
        self.gesture_click = Gtk.GestureClick.new(); self.gesture_click.set_button(Gdk.BUTTON_SECONDARY); self.gesture_click.connect("pressed", self._on_right_click)
        self.tree_view.add_controller(self.gesture_click)
        scroll_files.set_child(self.tree_view)
        
        scroll_projs = Gtk.ScrolledWindow(); scroll_projs.set_vexpand(True); scroll_projs.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.recent_list = Gtk.ListBox(); self.recent_list.add_css_class("file-list"); self.recent_list.connect("row-activated", self._on_project_selected)
        scroll_projs.set_child(self.recent_list)
        
        self.stack.add_named(scroll_files, "files"); self.stack.add_named(scroll_projs, "recent")
        self.append(self.stack)
        
        nav_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4); set_margins(nav_bar, 6); nav_bar.set_margin_start(8); nav_bar.set_margin_end(8)
        btn_files = Gtk.Button(label="📄"); btn_files.set_tooltip_text("Fichiers"); btn_files.add_css_class("flat"); btn_files.set_hexpand(True); btn_files.connect("clicked", lambda *_: self.stack.set_visible_child_name("files"))
        btn_recent = Gtk.Button(label="🕒"); btn_recent.set_tooltip_text("Récents"); btn_recent.add_css_class("flat"); btn_recent.set_hexpand(True); btn_recent.connect("clicked", lambda *_: self.stack.set_visible_child_name("recent"))
        btn_new = Gtk.Button(label="➕"); btn_new.set_tooltip_text("Nouveau fichier"); btn_new.add_css_class("flat"); btn_new.set_hexpand(True); btn_new.connect("clicked", self._create_new_file)
        btn_import = Gtk.Button(label="📥"); btn_import.set_tooltip_text("Importer"); btn_import.add_css_class("flat"); btn_import.set_hexpand(True); btn_import.connect("clicked", self._import_file)
        self.btn_hidden = Gtk.Button(label="🙈"); self.btn_hidden.set_tooltip_text("Fichiers cachés"); self.btn_hidden.add_css_class("flat"); self.btn_hidden.connect("clicked", self._toggle_hidden_files)
        nav_bar.append(btn_files); nav_bar.append(btn_recent); nav_bar.append(btn_new); nav_bar.append(btn_import); nav_bar.append(self.btn_hidden)
        self.append(nav_bar)

    def _log_message(self, msg):
        try:
            root = self.get_root()
            if root and hasattr(root, 'terminal_panel'):
                root.terminal_panel._log(msg)
            else:
                self._show_toast(msg)
        except Exception as e:
            global_log(f"⚠️ Erreur dans _log_message: {type(e).__name__} - {e}")

    def start_watcher(self, root_path):
        if self.watcher: 
            self.watcher.stop()
            self.watcher = None
        if root_path:
            try:
                from .watcher import FileWatcher
                self.watcher = FileWatcher(root_path, self._refresh_tree_idle)
                self.watcher.start()
            except Exception as e:
                self._log_message(f"⚠️ Erreur démarrage watcher: {e}")

    def _refresh_tree_idle(self): 
        GLib.idle_add(self._refresh_tree)

    def _refresh_tree(self):
        """Rafraîchissement intelligent : preserve expansion state and scroll position."""
        if not self.project_root:
            return
        
        # Save expansion state
        expanded_paths = set()
        def save_expansion(model, path, tree_iter, data):
            if self.tree_view.row_expanded(path):
                expanded_paths.add(model.get_value(tree_iter, 1))
            return False
        self.tree_store.foreach(save_expansion, None)
        
        # Clear and repopulate
        self.tree_store.clear()
        self._tree_path_map.clear()
        
        try:
            self._populate_tree(self.project_root, None)
        except Exception as e:
            self._log_message(f"❌ Erreur rafraîchissement arbre: {e}")
        
        # Restore expansion state
        def restore_expansion(model, path, tree_iter, data):
            fp = model.get_value(tree_iter, 1)
            if fp in expanded_paths:
                self.tree_view.expand_row(path, False)
            return False
        self.tree_store.foreach(restore_expansion, None)

    def _on_search_changed(self, entry):
        """Filtre l'arbre de fichiers selon la recherche."""
        search_text = entry.get_text().strip().lower()
        
        def filter_func(model, tree_iter, data):
            name = model.get_value(tree_iter, 0).lower()
            if not search_text:
                return True
            return search_text in name
        
        # Apply filter
        self.tree_view.set_row_separator_func(None)
        if search_text:
            self.tree_store.foreach(self._expand_matching, search_text)
        else:
            # Collapse all when search is cleared
            def collapse_all(model, path, tree_iter, data):
                self.tree_view.collapse_row(path)
                return False
            self.tree_store.foreach(collapse_all, None)
    
    def _expand_matching(self, model, path, tree_iter, search_text):
        """Expand paths that match the search."""
        name = model.get_value(tree_iter, 0).lower()
        if search_text in name:
            # Expand parent rows
            parent_path = path.copy()
            while parent_path:
                self.tree_view.expand_row(parent_path, False)
                parent_path = parent_path.copy()
                if not parent_path.up():
                    break

    def _toggle_hidden_files(self, *_):
        self.show_hidden = not self.show_hidden
        if self.show_hidden: 
            self.btn_hidden.set_label("👁")
            self.btn_hidden.set_tooltip_text("Masquer les fichiers cachés")
        else: 
            self.btn_hidden.set_label("🙈")
            self.btn_hidden.set_tooltip_text("Afficher les fichiers cachés")
        
        if self.project_root: 
            self.load_project(self.project_root, load_config())

    def _on_tree_cell_data(self, column, cell, model, tree_iter, data):
        name = model.get_value(tree_iter, 0); is_folder = model.get_value(tree_iter, 2)
        if is_folder:
            cell.set_property("weight", Pango.Weight.BOLD)
            cell.set_property("text", f"📁 {name}")
            cell.set_property("foreground", "#888888" if name.startswith('.') else "#4aa3df")
        else:
            cell.set_property("weight", Pango.Weight.NORMAL)
            ext = Path(name).suffix.lower()
            is_hidden = name.startswith('.')
            icon = EXT_ICONS.get(ext, "📄")
            # Special filenames
            if name == "settings.py": icon = "⚙"
            elif name == "manage.py": icon = "⚙"
            elif name == "views.py": icon = "👁"
            elif name == "models.py": icon = "🗄"
            elif name == "urls.py": icon = "🔗"
            elif name == "forms.py": icon = "📝"
            elif name == "admin.py": icon = "🛡"
            elif name == "tests.py": icon = "🧪"
            elif name == "Dockerfile": icon = "🐳"
            elif name == "Makefile": icon = "📜"
            elif name == "README.md": icon = "📖"
            elif name == ".env": icon = "🔒"
            
            color = "#888888" if is_hidden else "#4aa3df"
            cell.set_property("text", f"  {icon} {name}")
            cell.set_property("foreground", color)

    def _on_row_activated(self, treeview, path, column):
        model = treeview.get_model(); tree_iter = model.get_iter(path); full_path = model.get_value(tree_iter, 1); is_folder = model.get_value(tree_iter, 2)
        if is_folder:
            if treeview.row_expanded(path): treeview.collapse_row(path)
            else: treeview.expand_row(path, False)
        else:
            if Path(full_path).exists(): self.on_file_select(Path(full_path))

    def load_project(self, root: Path, config: dict):
        self.project_root = root
        self.tree_store.clear()
        self._tree_path_map.clear()
        try:
            self._populate_tree(root, None)
            self._load_recent_projects(config) 
            self.start_watcher(root)
        except Exception as e:
            self._log_message(f"❌ Erreur chargement projet: {e}")
            
    def _populate_tree(self, directory: Path, parent_iter):
        """Remplit l'arbre récursivement."""
        if not directory:
            return

        try:
            if not directory.exists():
                return

            entries = []
            for entry in directory.iterdir():
                if entry.name in IGNORED_DIRS: 
                    continue
                if entry.name.endswith('.egg-info'):
                    continue
                if not self.show_hidden and entry.name.startswith('.'): 
                    continue
                entries.append(entry)
            
            entries.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
            
            for entry in entries:
                try:
                    is_folder = entry.is_dir()
                    new_iter = self.tree_store.append(parent_iter, [entry.name, str(entry), is_folder])
                    self._tree_path_map[str(entry)] = new_iter
                    
                    if is_folder: 
                        self._populate_tree(entry, new_iter)
                except PermissionError:
                    pass
                except Exception as e:
                    global_log(f"⚠️ Erreur lecture {entry.name}: {e}")
                    
        except PermissionError:
            pass
        except Exception as e:
            global_log(f"❌ Erreur _populate_tree ({directory}): {e}")

    def get_file_path(self, file_name: str):
        """Retrouve le chemin complet d'un fichier par son nom."""
        for full_path, tree_iter in self._tree_path_map.items():
            if Path(full_path).name == file_name:
                return Path(full_path)
        return None

    def _load_recent_projects(self, config):
        while child := self.recent_list.get_first_child(): 
            self.recent_list.remove(child)
            
        for proj_path in get_recent_projects(config):
            path = Path(proj_path)
            if path.exists():
                row = Gtk.ListBoxRow()
                row._project_path = path
                
                lbl = Gtk.Label(label=f"  📂 {path.name}\n{path.parent}")
                lbl.set_xalign(0)
                lbl.set_margin_start(16)
                lbl.set_margin_top(6)
                lbl.set_margin_bottom(6)
                lbl.set_ellipsize(Pango.EllipsizeMode.END)
                lbl.set_max_width_chars(35)
                lbl.add_css_class("file-item")
                
                row.set_child(lbl)
                self.recent_list.append(row)
                
    def _on_project_selected(self, lb, row):
        if hasattr(row, "_project_path"): self.on_project_select(row._project_path)

    def _create_new_file(self, *_):
        if not self.project_root: return self._show_error("Aucun projet ouvert")
        dialog = Gtk.Dialog(title="Nouveau fichier", transient_for=self.get_root()); dialog.add_css_class("rounded-dialog"); dialog.set_default_size(400, 250)
        content = dialog.get_content_area(); content.set_spacing(8); set_margins(content, 12)
        content.append(Gtk.Label(label="Nom du fichier (avec extension):", xalign=0))
        entry = Gtk.Entry(); entry.set_placeholder_text("ex: style.css, script.js, main.c"); content.append(entry)
        content.append(Gtk.Label(label="Contenu initial (optionnel):", xalign=0, margin_top=8))
        text_buf = GtkSource.Buffer()
        text_view = GtkSource.View.new_with_buffer(text_buf)
        text_view.set_size_request(-1, 100)
        text_view.set_show_line_numbers(True)
        text_view.set_monospace(True)
        
        lang_mgr = GtkSource.LanguageManager.get_default()
        lang_py = lang_mgr.get_language("python")
        if lang_py: text_buf.set_language(lang_py)
        
        scroll = Gtk.ScrolledWindow(); scroll.set_child(text_view); content.append(scroll)
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_cancel = Gtk.Button(label="Annuler"); btn_create = Gtk.Button(label="✅ Créer"); btn_create.add_css_class("suggested-action")
        btn_box.append(btn_cancel); btn_box.append(btn_create); content.append(btn_box)
        def on_create(*_):
            filename = entry.get_text().strip()
            if not filename: return self._show_error("Nom requis")
            filepath = self.project_root / filename
            if filepath.exists(): return self._show_error(f"{filename} existe déjà")
            text = text_buf.get_text(text_buf.get_start_iter(), text_buf.get_end_iter(), True) or f"# {filename}\n"
            try:
                filepath.write_text(text, encoding='utf-8')
                self.on_file_created(filepath); self.load_project(self.project_root, load_config()); dialog.destroy()
            except Exception as e:
                self._log_message(f"❌ Erreur création fichier: {e}")
                self._show_error(f"Erreur: {e}")
        btn_create.connect("clicked", on_create); btn_cancel.connect("clicked", lambda *_: dialog.destroy()); dialog.present()

    def _import_file(self, *_):
        if not self.project_root: return self._show_error("Aucun projet ouvert")
        Gtk.FileDialog(title="Importer un fichier").open(self.get_root(), None, self._on_import_selected)

    def _on_import_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                src = Path(file.get_path()); dst = self.project_root / src.name
                if dst.exists() and Gtk.MessageDialog(transient_for=self.get_root(), flags=0, message_type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.YES_NO, text="Fichier existant", secondary_text=f"{dst.name} existe. Écraser ?").run() != Gtk.ResponseType.YES:
                    return
                shutil.copy2(src, dst); self.on_file_imported(dst); self.load_project(self.project_root, load_config())
        except Exception as e: 
            self._log_message(f"❌ Erreur importation: {e}")
            self._show_error(f"Erreur: {e}")

    def _show_error(self, msg: str):
        root = self.get_root()
        if root and hasattr(root.get_child(), "add_toast"): root.get_child().add_toast(Adw.Toast(title=f"❌ {msg}", timeout=3))

    def _show_toast(self, msg: str):
        root = self.get_root()
        if root and hasattr(root.get_child(), "add_toast"): root.get_child().add_toast(Adw.Toast(title=msg, timeout=3))

    def _on_right_click(self, gesture, n_press, x, y):
        result = self.tree_view.get_path_at_pos(int(x), int(y))
        if result is None: return
        path, column, cell_x, cell_y = result; self.tree_view.set_cursor(path)
        model = self.tree_view.get_model(); tree_iter = model.get_iter(path)
        name = model.get_value(tree_iter, 0); full_path = model.get_value(tree_iter, 1); is_folder = model.get_value(tree_iter, 2)
        self._show_context_menu(int(x), int(y), full_path, name, is_folder)

    def _set_clipboard(self, action, path, popover):
        self.clipboard_action = action
        self.clipboard_path = path
        popover.popdown()
        self._show_toast(f"✅ {Path(path).name} ({action})")

    def _paste_clipboard(self, target_dir, popover):
        popover.popdown()
        if not self.clipboard_action or not self.clipboard_path:
            return
        src = Path(self.clipboard_path)
        dst = Path(target_dir) / src.name
        
        if src.resolve() == dst.resolve() or str(src.resolve()) in str(dst.resolve()):
            self._show_error("Impossible de coller dans lui-même")
            return

        try:
            if self.clipboard_action == "copy":
                if src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                self._show_toast(f"✅ Copié vers {dst.name}")
            elif self.clipboard_action == "cut":
                shutil.move(str(src), str(dst))
                self.clipboard_action = None
                self.clipboard_path = None
                self._show_toast(f"✅ Déplacé vers {dst.name}")
            
            self.load_project(self.project_root, load_config())
        except Exception as e:
            self._log_message(f"❌ Erreur collage: {e}")
            self._show_error(f"Erreur: {e}")

    def _show_context_menu(self, x, y, full_path, name, is_folder):
        popover = Gtk.Popover(); popover.set_parent(self.tree_view); popover.set_has_arrow(False)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4); set_margins(box, 6)
        
        if not is_folder:
            btn_copy = Gtk.Button(label="📋 Copier"); btn_copy.set_halign(Gtk.Align.FILL); btn_copy.add_css_class("flat"); btn_copy.connect("clicked", lambda *_: self._set_clipboard("copy", full_path, popover))
            btn_cut = Gtk.Button(label="✂️ Couper"); btn_cut.set_halign(Gtk.Align.FILL); btn_cut.add_css_class("flat"); btn_cut.connect("clicked", lambda *_: self._set_clipboard("cut", full_path, popover))
            box.append(btn_copy); box.append(btn_cut)
        else:
            if self.clipboard_action and self.clipboard_path:
                btn_paste = Gtk.Button(label=f"📥 Coller ({self.clipboard_action})"); btn_paste.set_halign(Gtk.Align.FILL); btn_paste.add_css_class("flat"); btn_paste.add_css_class("suggested-action"); btn_paste.connect("clicked", lambda *_: self._paste_clipboard(full_path, popover))
                box.append(btn_paste)
            btn_copy_dir = Gtk.Button(label="📋 Copier dossier"); btn_copy_dir.set_halign(Gtk.Align.FILL); btn_copy_dir.add_css_class("flat"); btn_copy_dir.connect("clicked", lambda *_: self._set_clipboard("copy", full_path, popover))
            btn_cut_dir = Gtk.Button(label="✂️ Couper dossier"); btn_cut_dir.set_halign(Gtk.Align.FILL); btn_cut_dir.add_css_class("flat"); btn_cut_dir.connect("clicked", lambda *_: self._set_clipboard("cut", full_path, popover))
            box.append(btn_copy_dir); box.append(btn_cut_dir)
            
            # New file in this directory
            target_dir = full_path
            btn_new_here = Gtk.Button(label="➕ Nouveau fichier ici"); btn_new_here.set_halign(Gtk.Align.FILL); btn_new_here.add_css_class("flat"); btn_new_here.connect("clicked", lambda *_: self._create_file_in_dir(target_dir, popover))
            box.append(btn_new_here)

        btn_rename = Gtk.Button(label="✏️ Renommer"); btn_rename.set_halign(Gtk.Align.FILL); btn_rename.add_css_class("flat"); btn_rename.connect("clicked", lambda *_: self._rename_item(full_path, name, is_folder, popover))
        btn_delete = Gtk.Button(label="🗑 Supprimer"); btn_delete.set_halign(Gtk.Align.FILL); btn_delete.add_css_class("flat"); btn_delete.add_css_class("destructive-action"); btn_delete.connect("clicked", lambda *_: self._delete_item(full_path, name, is_folder, popover))
        box.append(btn_rename); box.append(btn_delete); popover.set_child(box)
        rect = Gdk.Rectangle(); rect.x = x; rect.y = y; rect.width = 1; rect.height = 1; popover.set_pointing_to(rect); popover.popup()

    def _create_file_in_dir(self, target_dir, popover):
        popover.popdown()
        dialog = Gtk.Dialog(title="Nouveau fichier", transient_for=self.get_root()); dialog.add_css_class("rounded-dialog"); dialog.set_default_size(350, 150)
        content = dialog.get_content_area(); content.set_spacing(8); set_margins(content, 12)
        content.append(Gtk.Label(label="Nom du fichier:", xalign=0))
        entry = Gtk.Entry(); entry.set_placeholder_text("fichier.py"); entry.set_activates_default(True); content.append(entry)
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_cancel = Gtk.Button(label="Annuler"); btn_create = Gtk.Button(label="✅ Créer"); btn_create.add_css_class("suggested-action")
        btn_box.append(btn_cancel); btn_box.append(btn_create); content.append(btn_box)
        def on_create(*_):
            filename = entry.get_text().strip()
            if not filename: dialog.destroy(); return
            filepath = Path(target_dir) / filename
            try:
                filepath.write_text("", encoding='utf-8')
                self.on_file_created(filepath); self.load_project(self.project_root, load_config()); dialog.destroy()
            except Exception as e:
                self._show_error(f"Erreur: {e}")
                dialog.destroy()
        btn_create.connect("clicked", on_create); btn_cancel.connect("clicked", lambda *_: dialog.destroy()); dialog.present()

    def _rename_item(self, full_path, old_name, is_folder, popover):
        popover.popdown()
        dialog = Gtk.Dialog(title="Renommer", transient_for=self.get_root()); dialog.add_css_class("rounded-dialog"); dialog.set_default_size(350, 150)
        content = dialog.get_content_area(); content.set_spacing(8); set_margins(content, 12)
        content.append(Gtk.Label(label=f"Renommer '{old_name}':", xalign=0))
        entry = Gtk.Entry(); entry.set_text(old_name); entry.set_activates_default(True); content.append(entry)
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_cancel = Gtk.Button(label="Annuler"); btn_rename = Gtk.Button(label="✅ Renommer"); btn_rename.add_css_class("suggested-action")
        btn_box.append(btn_cancel); btn_box.append(btn_rename); content.append(btn_box)
        def on_rename(*_):
            new_name = entry.get_text().strip()
            if not new_name or new_name == old_name: dialog.destroy(); return
            if "/" in new_name or "\\" in new_name: self._show_error("Nom invalide"); return
            new_path = Path(full_path).parent / new_name
            if new_path.exists(): self._show_error(f"'{new_name}' existe déjà"); return
            try:
                Path(full_path).rename(new_path); self.load_project(self.project_root, load_config()); self._show_toast(f"✅ Renommé en '{new_name}'")
            except Exception as e: 
                self._log_message(f"❌ Erreur renommage: {e}")
                self._show_error(f"Erreur: {e}")
            dialog.destroy()
        btn_rename.connect("clicked", on_rename); btn_cancel.connect("clicked", lambda *_: dialog.destroy()); dialog.present()

    def _delete_item(self, full_path, name, is_folder, popover):
        popover.popdown()
        dialog = Gtk.Dialog(title="Confirmer la suppression", transient_for=self.get_root()); dialog.add_css_class("rounded-dialog"); dialog.set_default_size(350, 150)
        content = dialog.get_content_area(); content.set_spacing(8); set_margins(content, 12)
        content.append(Gtk.Label(label=f"Supprimer '{name}' ?", xalign=0, margin_bottom=8))
        content.append(Gtk.Label(label="Cette action est irréversible.", xalign=0, css_classes=["dim-label"]))
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_cancel = Gtk.Button(label="Annuler"); btn_delete = Gtk.Button(label="🗑 Supprimer"); btn_delete.add_css_class("destructive-action")
        btn_box.append(btn_cancel); btn_box.append(btn_delete); content.append(btn_box)
        def on_delete(*_):
            try:
                path = Path(full_path)
                if path.is_dir(): shutil.rmtree(path)
                else: path.unlink()
                self.load_project(self.project_root, load_config()); self._show_toast(f"🗑 Supprimé: {name}")
            except Exception as e: 
                self._log_message(f"❌ Erreur suppression: {e}")
                self._show_error(f"Erreur: {e}")
            dialog.destroy()
        btn_delete.connect("clicked", on_delete); btn_cancel.connect("clicked", lambda *_: dialog.destroy()); dialog.present()