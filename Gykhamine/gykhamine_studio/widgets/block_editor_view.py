"""Module généré automatiquement depuis widgets.py - Classe BlockEditorView"""
import os, sys, re, subprocess, threading, shutil, json, zipfile, csv, tempfile
from pathlib import Path
from datetime import datetime
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk, Pango, GtkSource
from ..config import global_log, DEFAULT_CONFIG, VERSION, set_margins
from ..parser import parse_blocks, get_gtksource_lang_id
from ..ai_engine import BlockAIEngine, AIModificationDialog, LlamaSetupDialog, LogAnalyzerDialog, AICmdGeneratorDialog, GitManagerDialog, BusinessProcessDialog
from ..terminal_tty import NativeTtyTerminal
from ..database import load_config, save_config, memory_record, add_recent_project, get_recent_projects, is_port_in_use, find_free_port, kill_process_on_port, _get_db_path, log_to_file
from .tab_button import TabButton
from .block_card import BlockCard
from .c_compiler_dialog import CCompilerDialog
from .directory_picker_row import DirectoryPickerRow

#  WIDGETS
# ═══════════════════════════════════════════════════════════════════════
TYPE_ICONS = {"import": "📦", "class": "🏛", "function": "⚡", "separator": "─", "comment": "💬", "other": "▪", "template": "🌐", "template_part": "🌐", "django_block": "🧩", "style": "🎨", "style_rule": "🎨", "script": "⚙️", "script_block": "⚡", "c_block": "⚙️", "logic_block": "🔁", "css_file": "🎨", "html_file": "🌐"}


class BlockEditorView(Gtk.Box):
    def __init__(self, toast_cb, run_file_cb, get_config_cb=None, ai_engine=None, status_update_cb=None, on_file_saved_cb=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.toast_cb, self.run_file_cb, self._get_config_cb = toast_cb, run_file_cb, get_config_cb
        self.status_update_cb = status_update_cb
        self.on_file_saved_cb = on_file_saved_cb
        self.ai_engine = ai_engine
        self.current_file, self.blocks, self._cards, self.css_file, self.file_ext = None, [], [], None, "py"
        self.undo_stack, self.redo_stack, self.max_history = [], [], 20
        self._modified = False
        
        # Tab bar
        self.tab_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.tab_bar.add_css_class("tab-bar")
        self.tab_bar.set_margin_start(8)
        self.tab_bar.set_margin_top(4)
        self.open_tabs = {}
        self.active_tab_path = None
        self.append(self.tab_bar)
        
        # File label with breadcrumb
        self.file_label = Gtk.Label(label="Sélectionnez un fichier")
        self.file_label.add_css_class("editor-file-label")
        self.file_label.set_xalign(0)
        set_margins(self.file_label, 12)
        self.append(self.file_label)
        self.append(Gtk.Separator())
        
        # Toolbar
        self._build_toolbar()

        # Barre de recherche (Ctrl+F) — cherche dans les blocs du fichier actif
        # et, si besoin, dans les autres onglets ouverts.
        self._search_matches = []   # liste de (file_path, block_card_or_None)
        self._search_index = -1
        self._build_search_bar()

        # Blocks area
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_vexpand(True)
        self.scroll.set_hexpand(True)
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.blocks_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        set_margins(self.blocks_box, 16)
        self.scroll.set_child(self.blocks_box)
        self.append(self.scroll)

    def _build_toolbar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        set_margins(bar, 8)
        bar.append(Gtk.Label(label="Blocs:", css_classes=["toolbar-label"]))
        self.lbl_count = Gtk.Label(label="0")
        self.lbl_count.add_css_class("block-count-badge")
        bar.append(self.lbl_count)
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        bar.append(spacer)
        btn_compiler = Gtk.Button(label="🛠️ C")
        btn_compiler.set_tooltip_text("Compiler C")
        btn_compiler.add_css_class("ctrl-btn-warn")
        btn_compiler.connect("clicked", self._open_c_compiler)
        bar.append(btn_compiler)
        btn_add = Gtk.Button(label="➕")
        btn_add.set_tooltip_text("Ajouter un bloc")
        btn_add.add_css_class("ctrl-btn-start")
        btn_add.connect("clicked", self._add_block_dialog)
        bar.append(btn_add)
        btn_search = Gtk.Button(label="🔍")
        btn_search.set_tooltip_text("Rechercher (Ctrl+F)")
        btn_search.add_css_class("toolbar-btn")
        btn_search.connect("clicked", lambda *_: self.toggle_search_bar())
        bar.append(btn_search)
        for label, tooltip, cb in [
            ("↩", "Annuler (Ctrl+Z)", self._undo),
            ("↪", "Rétablir (Ctrl+Shift+Z)", self._redo),
            ("⬇", "Tout développer", self._expand_all),
            ("⬆", "Tout réduire", self._collapse_all)
        ]:
            btn = Gtk.Button(label=label)
            btn.set_tooltip_text(tooltip)
            btn.add_css_class("toolbar-btn")
            btn.connect("clicked", cb)
            bar.append(btn)
        btn_run = Gtk.Button(label="▶")
        btn_run.set_tooltip_text("Exécuter (F5)")
        btn_run.add_css_class("ctrl-btn-start")
        btn_run.connect("clicked", lambda *_: self._run_current_file())
        bar.append(btn_run)
        self.btn_css = Gtk.Button(label="🎨 CSS")
        self.btn_css.set_tooltip_text("Éditer le CSS associé")
        self.btn_css.add_css_class("toolbar-btn")
        self.btn_css.set_visible(False)
        self.btn_css.connect("clicked", self._open_linked_css)
        bar.append(self.btn_css)
        btn_save = Gtk.Button(label="💾")
        btn_save.set_tooltip_text("Sauvegarder (Ctrl+S)")
        btn_save.add_css_class("save-file-btn")
        btn_save.connect("clicked", self._save_file)
        bar.append(btn_save)
        self.append(bar)
        self.append(Gtk.Separator())

    def _build_search_bar(self):
        self.search_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        set_margins(self.search_bar, 8)
        self.search_bar.set_visible(False)
        self.search_bar.add_css_class("editor-search-bar")

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Rechercher dans tous les éditeurs (blocs)…")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("activate", lambda *_: self._search_next())
        self.search_bar.append(self.search_entry)

        self.search_status_lbl = Gtk.Label(label="")
        self.search_status_lbl.add_css_class("dim-label")
        self.search_bar.append(self.search_status_lbl)

        btn_prev = Gtk.Button(label="⬆")
        btn_prev.set_tooltip_text("Occurrence précédente (Maj+Entrée)")
        btn_prev.add_css_class("toolbar-btn")
        btn_prev.connect("clicked", lambda *_: self._search_prev())
        self.search_bar.append(btn_prev)

        btn_next = Gtk.Button(label="⬇")
        btn_next.set_tooltip_text("Occurrence suivante (Entrée)")
        btn_next.add_css_class("toolbar-btn")
        btn_next.connect("clicked", lambda *_: self._search_next())
        self.search_bar.append(btn_next)

        btn_close = Gtk.Button(label="✕")
        btn_close.set_tooltip_text("Fermer la recherche (Échap)")
        btn_close.add_css_class("toolbar-btn")
        btn_close.connect("clicked", lambda *_: self.toggle_search_bar(False))
        self.search_bar.append(btn_close)

        # Raccourci clavier local à la recherche : Échap pour fermer
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self._on_search_key_pressed)
        self.search_entry.add_controller(key_ctrl)

        self.append(self.search_bar)

    def toggle_search_bar(self, show: bool = None):
        """Affiche ou masque la barre de recherche globale (Ctrl+F)."""
        if show is None:
            show = not self.search_bar.get_visible()
        self.search_bar.set_visible(show)
        if show:
            self.search_entry.grab_focus()
        else:
            self._clear_all_highlights()
            self.search_status_lbl.set_text("")

    def _on_search_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.toggle_search_bar(False)
            return True
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self._search_prev() if shift else self._search_next()
            return True
        return False

    def _clear_all_highlights(self):
        for card in self._cards:
            card.clear_search_highlight()

    def _on_search_changed(self, entry):
        query = entry.get_text().strip()
        self._clear_all_highlights()
        self._search_matches = []
        self._search_index = -1

        if not query:
            self.search_status_lbl.set_text("")
            return

        # 1) Blocs du fichier actuellement ouvert (recherche directe, pas de disque)
        for card in self._cards:
            if card.contains_text(query):
                self._search_matches.append((str(self.current_file) if self.current_file else None, card))

        # 2) Autres onglets ouverts : recherche dans leur contenu sur disque,
        # sans les charger dans l'éditeur (juste pour compter/localiser).
        for path_str in self.open_tabs.keys():
            if self.current_file and path_str == str(self.current_file):
                continue
            try:
                content = Path(path_str).read_text(encoding="utf-8")
                if query.lower() in content.lower():
                    self._search_matches.append((path_str, None))
            except Exception:
                continue

        if not self._search_matches:
            self.search_status_lbl.set_text("Aucun résultat")
            return

        self._search_index = 0
        self.search_status_lbl.set_text(f"1 / {len(self._search_matches)}")
        self._goto_search_match(0, query)

    def _goto_search_match(self, index: int, query: str = None):
        if not self._search_matches:
            return
        query = query or self.search_entry.get_text().strip()
        path_str, card = self._search_matches[index]

        if card is not None:
            # Résultat dans le fichier actif : déplie et surligne directement.
            card.reveal_search_match(query)
        elif path_str:
            # Résultat dans un autre onglet : bascule dessus, puis relance la
            # recherche sur ce fichier fraîchement chargé pour surligner le bloc.
            self._activate_tab(path_str)
            for c in self._cards:
                if c.reveal_search_match(query):
                    break

    def _search_next(self):
        if not self._search_matches:
            return
        self._search_index = (self._search_index + 1) % len(self._search_matches)
        self.search_status_lbl.set_text(f"{self._search_index + 1} / {len(self._search_matches)}")
        self._goto_search_match(self._search_index)

    def _search_prev(self):
        if not self._search_matches:
            return
        self._search_index = (self._search_index - 1) % len(self._search_matches)
        self.search_status_lbl.set_text(f"{self._search_index + 1} / {len(self._search_matches)}")
        self._goto_search_match(self._search_index)

    def _open_c_compiler(self, *_):
        dialog = CCompilerDialog(self.get_root(), self._get_config_cb, self.toast_cb)
        dialog.present()

    # ── TAB MANAGEMENT ───────────────────────────────────────────────
    def _add_tab(self, file_path):
        if file_path in self.open_tabs:
            self._activate_tab(file_path)
            return
        tab_btn = TabButton(file_path, self._close_tab, self._activate_tab)
        self.open_tabs[file_path] = tab_btn
        self.tab_bar.append(tab_btn)
        self._activate_tab(file_path)

    def _activate_tab(self, file_path):
        if self.active_tab_path == file_path: return
        # Save current editor state before switching
        if self.active_tab_path and self.current_file:
            self._save_current_editor_state()
        
        self.active_tab_path = file_path
        for path, btn in self.open_tabs.items():
            btn.set_active(path == file_path)
        self.load_file(Path(file_path))

    def _close_tab(self, file_path):
        if file_path in self.open_tabs:
            btn = self.open_tabs.pop(file_path)
            self.tab_bar.remove(btn)
            if self.active_tab_path == file_path:
                self.active_tab_path = None
                self.current_file = None
                self.file_label.set_text("Sélectionnez un fichier")
                while child := self.blocks_box.get_first_child():
                    self.blocks_box.remove(child)
                self._cards = []
                self.blocks = []
                if self.open_tabs:
                    next_path = list(self.open_tabs.keys())[0]
                    self._activate_tab(next_path)

    def _save_current_editor_state(self):
        """Sauvegarde l'état de l'éditeur courant avant de changer d'onglet."""
        for card in self._cards:
            if card.expanded:
                card._toggle_edit()  # This saves the block code

    # ── BLOCK OPERATIONS ─────────────────────────────────────────────
    def _add_block_dialog(self, *_):
        if not self.current_file:
            return self.toast_cb("❌ Aucun fichier ouvert")
        dialog = Gtk.Dialog(title="Ajouter un bloc", transient_for=self.get_root())
        dialog.add_css_class("rounded-dialog")
        dialog.set_default_size(400, 280)
        content = dialog.get_content_area()
        set_margins(content, 12)
        content.set_spacing(8)
        content.append(Gtk.Label(label="Type de bloc:", xalign=0))
        type_combo = Gtk.ComboBoxText()
        ext = self.file_ext
        if ext in ('py', 'pyw', 'pyi', 'rb', 'lua'):
            block_types = ["Fonction (def)", "Classe (class)", "Séparateur (####)", "Commentaire (#)", "Vide"]
        elif ext in ('js', 'jsx', 'ts', 'tsx', 'mjs'):
            block_types = ["Fonction (function)", "Classe (class)", "Export (export)", "Commentaire (//)", "Vide"]
        elif ext in ('c', 'cpp', 'h', 'hpp', 'rs', 'go', 'java', 'kt'):
            block_types = ["Fonction", "Struct/Classe", "Macro (#define)", "Commentaire (//)", "Vide"]
        elif ext in ('sh', 'bash'):
            block_types = ["Fonction", "Condition (if)", "Commentaire (#)", "Vide"]
        else:
            block_types = ["Fonction (def)", "Classe (class)", "Commentaire", "Vide"]
        for t in block_types:
            type_combo.append_text(t)
        type_combo.set_active(0)
        content.append(type_combo)
        content.append(Gtk.Label(label="Nom :", xalign=0, margin_top=8))
        name_entry = Gtk.Entry()
        name_entry.set_placeholder_text("ex: my_function")
        content.append(name_entry)
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_cancel = Gtk.Button(label="Annuler")
        btn_add = Gtk.Button(label="✅ Ajouter")
        btn_add.add_css_class("suggested-action")
        btn_box.append(btn_cancel)
        btn_box.append(btn_add)
        content.append(btn_box)
        
        def on_add(*_):
            btype_raw = type_combo.get_active_text()
            name = name_entry.get_text().strip() or "new_block"
            ext = self.file_ext
            
            if ext in ('py', 'pyw', 'pyi'):
                if "Fonction" in btype_raw:
                    code = f"def {name}():\n    pass\n"
                    btype = "function"
                elif "Classe" in btype_raw:
                    code = f"class {name}:\n    pass\n"
                    btype = "class"
                elif "Séparateur" in btype_raw:
                    code = f"{'#' * 40}\n# {name}\n{'#' * 40}\n"
                    btype = "separator"
                elif "Commentaire" in btype_raw:
                    code = f"# {name}\n"
                    btype = "comment"
                else:
                    code = f"# {name}\n"
                    btype = "other"
            elif ext in ('js', 'jsx', 'ts', 'tsx', 'mjs'):
                if "Fonction" in btype_raw:
                    code = f"function {name}() {{\n    \n}}\n"
                    btype = "function"
                elif "Classe" in btype_raw:
                    code = f"class {name} {{\n    \n}}\n"
                    btype = "class"
                elif "Export" in btype_raw:
                    code = f"export default {name};\n"
                    btype = "import"
                elif "Commentaire" in btype_raw:
                    code = f"// {name}\n"
                    btype = "comment"
                else:
                    code = f"// {name}\n"
                    btype = "other"
            elif ext in ('c', 'cpp', 'h', 'hpp'):
                if "Fonction" in btype_raw:
                    code = f"void {name}() {{\n    \n}}\n"
                    btype = "function"
                elif "Struct" in btype_raw:
                    code = f"struct {name} {{\n    \n}};\n"
                    btype = "class"
                elif "Macro" in btype_raw:
                    code = f"#define {name} \n"
                    btype = "import"
                elif "Commentaire" in btype_raw:
                    code = f"// {name}\n"
                    btype = "comment"
                else:
                    code = f"// {name}\n"
                    btype = "other"
            else:
                code = f"# {name}\n"
                btype = "other"
                
            self.blocks.append({
                "type": btype, "name": name, "code": code,
                "start": len(self.blocks), "end": len(self.blocks),
                "children": []
            })
            self._push_state()
            self._render_blocks()
            self._modified = True
            self.toast_cb(f"✅ Bloc '{name}' ajouté")
            dialog.destroy()
        
        btn_add.connect("clicked", on_add)
        btn_cancel.connect("clicked", lambda *_: dialog.destroy())
        dialog.present()

    # ── UNDO / REDO ──────────────────────────────────────────────────
    def _push_state(self):
        self.undo_stack.append("".join(b["code"] for b in self.blocks))
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def _undo(self, *_):
        if len(self.undo_stack) > 1:
            self.redo_stack.append(self.undo_stack.pop())
            self._restore_state(self.undo_stack[-1])
            self._modified = True
            self.toast_cb("↩ Annulé")

    def _redo(self, *_):
        if self.redo_stack:
            state = self.redo_stack.pop()
            self.undo_stack.append(state)
            self._restore_state(state)
            self._modified = True
            self.toast_cb("↪ Rétabli")

    def _restore_state(self, state: str):
        self.blocks = parse_blocks(state, str(self.current_file) if self.current_file else "")
        self._render_blocks()

    # ── FILE LOADING ─────────────────────────────────────────────────
    def load_file(self, path: Path):
        if not path.exists():
            self.toast_cb(f"❌ Fichier introuvable: {path.name}")
            return
            
        self.current_file = path
        self.file_label.set_text(f"📄  {path.name}")
        self.file_ext = path.suffix.lower().replace('.', '')
        self.css_file = None
        self._modified = False
        
        if path.suffix == '.py':
            linked_css = path.with_suffix('.css')
            if linked_css.exists():
                self.css_file = linked_css
                self.btn_css.set_label(f"🎨 {linked_css.name}")
                self.btn_css.set_visible(True)
            else:
                self.btn_css.set_visible(False)
        else:
            self.btn_css.set_visible(False)
            
        try:
            content = path.read_text(encoding="utf-8")
            self.blocks = parse_blocks(content, str(path))
            self._push_state()
            self._render_blocks()
            
            # Count lines
            line_count = content.count('\n') + 1
            
            # Update status bar
            if self.status_update_cb:
                self.status_update_cb(str(path), f"{line_count} lignes")
            
            if self._get_config_cb:
                memory_record(self._get_config_cb(), str(path.parent), str(path), action="open")
        except Exception as e:
            self.file_label.set_text(f"❌ Erreur: {e}")
            global_log(f"❌ Erreur chargement fichier: {e}")
            
        self._add_tab(str(path))

    def _open_linked_css(self, *_):
        if self.css_file and self.css_file.exists():
            self._save_file()
            self.load_file(self.css_file)
            self.toast_cb(f"🎨 {self.css_file.name}")

    # ── BLOCK RENDERING ──────────────────────────────────────────────
    def _render_blocks_recursive(self, blocks, container, level=0, parent_prefix=""):
        """Rend les blocs et leurs enfants avec indentation et numérotation."""
        for index, block in enumerate(blocks):
            current_index = index + 1
            if parent_prefix:
                block["hierarchical_id"] = f"{parent_prefix}.{current_index}"
            else:
                block["hierarchical_id"] = str(current_index)
            
            card = BlockCard(
                block,
                self._on_block_save,
                self._on_block_delete,
                self._on_block_copy,
                self.file_ext,
                ai_engine=self.ai_engine,
                parent_window=self
            )
            
            if level > 0:
                card.set_margin_start(level * 20)
                card.add_css_class("child-block")
            
            container.append(card)
            self._cards.append(card)
            
            if block.get("children"):
                self._render_blocks_recursive(block["children"], container, level + 1, parent_prefix=block["hierarchical_id"])

    def _render_blocks(self):
        while child := self.blocks_box.get_first_child():
            self.blocks_box.remove(child)
        
        total_blocks = sum(1 for b in self._count_blocks(self.blocks))
        self.lbl_count.set_text(str(total_blocks))
        self._cards = []
        self._render_blocks_recursive(self.blocks, self.blocks_box, level=0)

    def _count_blocks(self, blocks):
        """Compte tous les blocs y compris les enfants."""
        for b in blocks:
            yield b
            if b.get("children"):
                yield from self._count_blocks(b["children"])

    # ── BLOCK CALLBACKS ──────────────────────────────────────────────
    def _on_block_save(self, block, new_code):
        if not new_code.endswith('\n'):
            new_code += '\n'
        block["code"] = new_code
        self._push_state()
        self._modified = True
        self.toast_cb("✅ Mis à jour")
        
        if self.current_file and self._get_config_cb:
            memory_record(self._get_config_cb(), str(self.current_file.parent), str(self.current_file), block.get("name"), "edit")

    def _on_block_delete(self, block):
        self.blocks.remove(block)
        self._push_state()
        self._render_blocks()
        self._modified = True
        self.toast_cb("🗑 Supprimé")

    def _on_block_copy(self, code):
        Gdk.Display.get_default().get_clipboard().set(code)
        self.toast_cb("⧉ Copié")

    def _expand_all(self, *_):
        for card in self._cards:
            if not card.expanded:
                card._toggle_edit()

    def _collapse_all(self, *_):
        for card in self._cards:
            if card.expanded:
                card._toggle_edit()

    # ── SAVE ─────────────────────────────────────────────────────────
    def _save_file(self, *_):
        if not self.current_file:
            return self.toast_cb("❌ Aucun fichier ouvert")
        saved_path = self.current_file
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.current_file.with_suffix(f".{timestamp}{self.current_file.suffix}.bak")
            if self.current_file.exists():
                shutil.copy2(self.current_file, backup_path)
            
            temp_path = self.current_file.with_suffix(f".{timestamp}.tmp")
            
            safe_blocks = []
            for b in self.blocks:
                code = b["code"]
                if not code.endswith('\n'):
                    code += '\n'
                safe_blocks.append(code)
                
            new_content = "".join(safe_blocks)
            temp_path.write_text(new_content, encoding="utf-8")
            shutil.move(str(temp_path), str(self.current_file))
            
            self._push_state()
            self._modified = False
            self.toast_cb(f"💾 Sauvegardé: {self.current_file.name}")

            # Explorateur : rafraîchi et révèle le fichier sauvegardé.
            if self.on_file_saved_cb:
                self.on_file_saved_cb(saved_path)

            # Ferme puis rouvre le fichier pour reparser et afficher automatiquement
            # la nouvelle structure de blocs (fusion/division éventuelle après écriture).
            # On retire directement l'onglet sans laisser _close_tab activer un autre
            # onglet entre les deux (évite un chargement intermédiaire inutile).
            tab_btn = self.open_tabs.pop(str(saved_path), None)
            if tab_btn:
                self.tab_bar.remove(tab_btn)
            self.active_tab_path = None
            self.load_file(saved_path)

        except Exception as e:
            self.toast_cb(f"❌ Erreur: {e}")
            global_log(f"❌ Erreur sauvegarde: {e}")

    def _run_current_file(self, *_):
        if not self.current_file:
            return self.toast_cb("❌ Aucun fichier")
        # Auto-save before running
        if self._modified:
            self._save_file()
        if self.run_file_cb:
            self.run_file_cb(self.current_file)