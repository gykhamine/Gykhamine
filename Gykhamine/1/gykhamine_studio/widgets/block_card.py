"""Module généré automatiquement - Classe BlockCard"""
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk, Pango, GtkSource
from pathlib import Path

# Imports relatifs vers les modules racines
from ..config import global_log, set_margins, apply_dark_source_scheme
from ..ai_engine import AIModificationDialog
from ..parser import get_gtksource_lang_id

# Constantes locales nécessaires à l'affichage des icônes
TYPE_ICONS = {
    "import": "📦", "class": "🏛", "function": "⚡", "separator": "─",
    "comment": "💬", "other": "▪", "template": "🌐", "template_part": "🌐",
    "django_block": "🧩", "style": "🎨", "style_rule": "🎨",
    "script": "⚙️", "script_block": "⚡", "c_block": "⚙️",
    "logic_block": "🔁", "css_file": "🎨", "html_file": "🌐",
    "css_selector": "🎨", "css_at_media": "🎨", "css_at_keyframes": "🎨",
    "css_variable": "🎨", "css_property": "🎨",
}

class BlockCard(Gtk.Box):
    def __init__(self, block: dict, on_save_cb, on_delete_cb, on_copy_cb, file_ext, ai_engine=None, parent_window=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.block = block
        self.on_save_cb = on_save_cb
        self.on_delete_cb = on_delete_cb
        self.on_copy_cb = on_copy_cb
        self.file_ext = file_ext
        self.ai_engine = ai_engine
        self.parent_window = parent_window
        self.expanded = False
        self._active_search_context = None
        
        self.add_css_class("block-card")
        
        # Determine language for syntax highlighting
        self.lang = self._detect_lang()
        
        self._build_header()
        self._build_editor()

    def _detect_lang(self) -> str:
        """
        Détecte le langage à utiliser pour la coloration syntaxique.
        Priorité : type de bloc (style/script/template) → extension de fichier.
        Retourne l'extension courte (ex: 'js', 'py', 'ts') qui sera traduite
        par get_gtksource_lang_id() en ID de langage GtkSource.
        """
        btype = self.block.get("type", "")
        # 1) CSS (bloc <style> ou blocs CSS_)
        if btype == "style" or btype.startswith("css_"):
            return "css"
        # 2) JavaScript (bloc <script> inline HTML)
        elif btype in ("script", "script_block"):
            return "js"
        # 3) HTML / templates Django-Jinja
        elif btype in ("django_block", "template_part", "html_file", "template"):
            return "html"
        # 4) Python détecté via extension (incluant pygments)
        elif btype in ("function", "class", "import", "logic_block", "comment"):
            return self.file_ext or "py"
        # 5) Par défaut, l'extension du fichier
        return self.file_ext or "text"

    def _get_lang_id(self) -> str:
        """Retourne l'ID GtkSource pour la coloration syntaxique."""
        return get_gtksource_lang_id(self.lang)

    def _build_header(self):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        set_margins(header, 8); header.set_margin_start(12)
        
        # Icône
        icon = TYPE_ICONS.get(self.block["type"], "▪")
        header.append(Gtk.Label(label=icon, css_classes=["block-icon"]))
        
        # Badge Type
        badge = Gtk.Label(label=self.block["type"].upper())
        badge.add_css_class("block-badge")
        badge.add_css_class(f"badge-{self.block['type']}")
        header.append(badge)
        
        # Nom du bloc
        name_text = self.block.get("hierarchical_id", "")
        block_name = self.block.get("name", "")
        if block_name and block_name != name_text:
            display = f"{name_text}  {block_name}" if name_text else block_name
        else:
            display = name_text or block_name or "Bloc"
        
        lbl_name = Gtk.Label(label=display)
        lbl_name.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        lbl_name.set_hexpand(True)
        lbl_name.set_xalign(0)
        lbl_name.add_css_class("block-name")
        lbl_name.set_tooltip_text(block_name)
        header.append(lbl_name)
        
        # Bouton IA
        if self.ai_engine:
            btn_ai = Gtk.Button(label="🤖")
            btn_ai.set_tooltip_text("Modifier avec l'IA")
            btn_ai.add_css_class("block-action-btn")
            btn_ai.add_css_class("btn-ai")
            btn_ai.connect("clicked", self._open_ai_dialog)
            header.append(btn_ai)
            
        # Boutons Déplacement
        btn_up = Gtk.Button(label="⬆")
        btn_up.set_tooltip_text("Monter")
        btn_up.add_css_class("block-action-btn")
        btn_up.connect("clicked", lambda *_: self._move_block(-1))
        
        btn_down = Gtk.Button(label="⬇")
        btn_down.set_tooltip_text("Descendre")
        btn_down.add_css_class("block-action-btn")
        btn_down.connect("clicked", lambda *_: self._move_block(1))
        
        header.append(btn_up)
        header.append(btn_down)

        # Boutons Actions
        for label, tooltip, cb, css in [
            ("👁", "Voir / Éditer", self._view_code, "btn-view"),
            ("✏", "Édition inline", self._toggle_edit, "btn-edit"),
            ("⧉", "Copier", self._do_copy, "btn-copy"),
            ("✕", "Supprimer", self._do_delete, "btn-delete")
        ]:
            btn = Gtk.Button(label=label)
            btn.set_tooltip_text(tooltip)
            btn.add_css_class("block-action-btn")
            btn.add_css_class(css)
            btn.connect("clicked", cb)
            header.append(btn)
            
        self.append(header)
        
        # Barre accentuée
        bar = Gtk.Box()
        bar.set_size_request(-1, 2)
        bar.add_css_class("block-accent-bar")
        bar.add_css_class(f"accent-{self.block['type']}")
        self.append(bar)

    def _setup_source_buffer(self, buffer: GtkSource.Buffer, text: str):
        """
        Configure un GtkSource.Buffer avec le bon langage et thème.
        Robuste : essaie plusieurs variantes de nom de langage (lang-js,
        javascript, JavaScript, js) + alias par extension, et plusieurs
        thèmes sombres en fallback pour garantir la coloration.
        """
        # ── LANGAGE ─────────────────────────────────────────────
        lang_mgr = GtkSource.LanguageManager.get_default()
        lang_id = self._get_lang_id()

        # Liste d'alias à essayer si le premier ID ne donne rien
        aliases = self._lang_aliases(lang_id)
        language = None
        for candidate in aliases:
            language = lang_mgr.get_language(candidate)
            if language is not None:
                break

        # Tentative ultime : recherche par pattern (par exemple 'js' → 'javascript')
        if language is None and lang_id:
            # Certains managers exposent get_language() insensible à la casse
            for name in ("javascript", "jscript", "java", "typescript", "python3", "python"):
                language = lang_mgr.get_language(name)
                if language is not None:
                    break

        if language is not None:
            buffer.set_language(language)
        # Sinon : pas de coloration spécifique, mais le buffer reste fonctionnel

        # ── THÈME / SCHÉMA DE COULEURS ──────────────────────────
        apply_dark_source_scheme(buffer)

        buffer.set_text(text)

    @staticmethod
    def _lang_aliases(lang_id: str) -> list[str]:
        """
        Retourne une liste d'alias à essayer pour récupérer un langage GtkSource.
        Garantit que JS, TS, HTML, CSS, Python, etc. sont correctement résolus
        même sur des installations minimales.
        """
        aliases_map = {
            # JS & dérivés
            "javascript": ["javascript", "js", "JavaScript", "jscript"],
            "js":         ["javascript", "js", "JavaScript", "jscript"],
            "jsx":        ["jsx", "javascript", "js", "JavaScript"],
            "typescript": ["typescript", "ts", "TypeScript", "javascript", "js"],
            "ts":         ["typescript", "ts", "TypeScript", "javascript", "js"],
            "tsx":        ["tsx", "typescript", "javascript", "js"],
            # Web
            "html":       ["html", "HTML", "html5"],
            "css":        ["css", "CSS"],
            "scss":       ["scss", "SCSS", "css"],
            "sass":       ["sass", "SASS"],
            "less":       ["less", "LESS", "css"],
            # Scripts
            "python":     ["python3", "python", "Python", "py"],
            "py":         ["python3", "python", "Python", "py"],
            "ruby":       ["ruby", "Ruby", "rb"],
            "rb":         ["ruby", "Ruby"],
            "php":        ["php", "PHP"],
            "perl":       ["perl", "Perl", "pl"],
            "lua":        ["lua", "Lua"],
            "sh":         ["sh", "bash", "shell", "Bash", "Shell-script"],
            "bash":       ["sh", "bash", "shell", "Bash", "Shell-script"],
            "fish":       ["fish", "Fish"],
            # C-family
            "c":          ["c", "C"],
            "cpp":        ["cpp", "C++", "c++", "c"],
            "objc":       ["objc", "objective-c", "objective_c"],
            "cs":         ["cs", "c-sharp", "C#"],
            # JVM
            "java":       ["java", "Java"],
            "kotlin":     ["kotlin", "Kotlin"],
            "scala":      ["scala", "Scala"],
            "groovy":     ["groovy", "Groovy"],
            # Systèmes
            "go":         ["go", "Go"],
            "rust":       ["rust", "Rust"],
            "swift":      ["swift", "Swift"],
            # Données
            "sql":        ["sql", "SQL"],
            "json":       ["json", "JSON"],
            "xml":        ["xml", "XML"],
            "yaml":       ["yaml", "YAML", "yml"],
            "toml":       ["toml", "TOML"],
            # Divers
            "markdown":   ["markdown", "Markdown", "md"],
            "ini":        ["ini", "INI"],
            "dockerfile": ["dockerfile", "Dockerfile"],
            "rst":        ["rst", "RST", "rest"],
            "diff":       ["diff", "Diff"],
            "makefile":   ["makefile", "Makefile", "make"],
        }
        return aliases_map.get(lang_id, [lang_id, lang_id.capitalize(), lang_id.upper()])

    def _build_editor(self):
        self.editor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        set_margins(self.editor_box, 0)
        self.editor_box.set_margin_start(12)
        self.editor_box.set_margin_end(12)
        self.editor_box.set_margin_bottom(8)
        self.editor_box.set_visible(False)
        
        # Vue Source avec coloration syntaxique par langage
        self.textview = GtkSource.View()
        self.textview.set_monospace(True)
        self.textview.set_wrap_mode(Gtk.WrapMode.NONE)
        self.textview.set_show_line_numbers(True)
        self.textview.set_highlight_current_line(True)
        self.textview.set_auto_indent(True)
        self.textview.set_insert_spaces_instead_of_tabs(True)
        self.textview.set_tab_width(4)
        self.textview.set_indent_width(4)
        self.textview.set_smart_home_end(True)
        self.textview.add_css_class("code-editor")
        
        buffer = GtkSource.Buffer()
        self._setup_source_buffer(buffer, self.block["code"])
        self.textview.set_buffer(buffer)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_size_request(-1, 200)
        scroll.set_child(self.textview)
        
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_cancel = Gtk.Button(label="✕ Fermer")
        btn_cancel.add_css_class("cancel-btn")
        btn_cancel.connect("clicked", self._toggle_edit)
        bar.append(btn_cancel)
        
        self.editor_box.append(scroll)
        self.editor_box.append(bar)
        self.append(self.editor_box)
        
    def _toggle_edit(self, *_):
        if self.expanded:
            self.block["code"] = self.textview.get_buffer().get_text(
                self.textview.get_buffer().get_start_iter(), 
                self.textview.get_buffer().get_end_iter(), 
                True
            )
            self.on_save_cb(self.block, self.block["code"])
            
        self.expanded = not self.expanded
        self.editor_box.set_visible(self.expanded)

    def collapse(self):
        """Replie le bloc sans déclencher de sauvegarde (contrairement à
        _toggle_edit). Utilisé par la recherche globale pour refermer
        automatiquement les blocs non concernés par le résultat courant."""
        if self.expanded:
            self.expanded = False
            self.editor_box.set_visible(False)

    def contains_text(self, query: str) -> bool:
        """Indique si le code du bloc contient le texte recherché (insensible à la casse).
        Utilisé par la recherche globale de l'éditeur pour localiser les blocs
        correspondants sans avoir à les déplier au préalable."""
        if not query:
            return False
        return query.lower() in self.block.get("code", "").lower()

    def reveal_search_match(self, query: str) -> bool:
        """Déplie le bloc si nécessaire puis surligne la première occurrence du
        texte recherché dans son éditeur. Retourne True si une occurrence a été
        trouvée et surlignée."""
        if not query or not self.contains_text(query):
            return False
        if not self.expanded:
            self._toggle_edit()
        buffer = self.textview.get_buffer()
        self._apply_search_highlight(buffer, query)
        return True

    def _apply_search_highlight(self, buffer, query: str):
        """Configure un GtkSource.SearchContext sur le buffer du bloc et place le
        curseur/la sélection sur la première correspondance, avec scroll automatique."""
        search_settings = GtkSource.SearchSettings()
        search_settings.set_search_text(query)
        search_settings.set_case_sensitive(False)
        search_context = GtkSource.SearchContext.new(buffer, search_settings)
        self._active_search_context = search_context  # garder une référence vivante

        start_iter = buffer.get_start_iter()
        found, match_start, match_end, _wrapped = search_context.forward(start_iter)
        if found:
            buffer.select_range(match_start, match_end)
            GLib.idle_add(lambda: self.textview.scroll_to_iter(match_start, 0.1, True, 0.0, 0.3) and False)

    def clear_search_highlight(self):
        """Retire le contexte de recherche actif (appelé lors d'une nouvelle recherche
        ou de la fermeture de la barre de recherche globale)."""
        self._active_search_context = None

    def _view_code(self, *_):
        dialog = Gtk.Dialog(title=f"Édition : {self.block['name']}", transient_for=self.get_root())
        dialog.add_css_class("rounded-dialog")
        dialog.set_default_size(800, 500)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        set_margins(content, 12)
        dialog.set_child(content)
         
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)
        
        textview = GtkSource.View()
        textview.set_monospace(True)
        textview.set_editable(True)
        textview.set_wrap_mode(Gtk.WrapMode.WORD)
        textview.set_show_line_numbers(True)
        textview.set_highlight_current_line(True)
        textview.set_auto_indent(True)
        textview.set_insert_spaces_instead_of_tabs(True)
        textview.set_smart_home_end(True)
        textview.add_css_class("code-editor")
        
        buffer = GtkSource.Buffer()
        self._setup_source_buffer(buffer, self.block["code"])
        textview.set_buffer(buffer)
        
        scroll.set_child(textview)
        content.append(scroll)
         
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_box.set_halign(Gtk.Align.END)
        
        btn_copy = Gtk.Button(label="📋 Copier")
        btn_copy.connect("clicked", lambda *_: self._do_copy())
        btn_box.append(btn_copy)
        
        btn_close = Gtk.Button(label="✕ Fermer (Sauvegarder)", css_classes=["suggested-action"])
        btn_close.connect("clicked", lambda *_: self._save_from_popup(textview, dialog))
        btn_box.append(btn_close)
        
        content.append(btn_box)
        dialog.present()
        
    def _save_from_popup(self, textview, dialog):
        self.block["code"] = textview.get_buffer().get_text(
            textview.get_buffer().get_start_iter(), 
            textview.get_buffer().get_end_iter(), 
            True
        )
        self.on_save_cb(self.block, self.block["code"])
        self.textview.get_buffer().set_text(self.block["code"])
        dialog.destroy()

    def _do_save(self, *_):
        self.block["code"] = self.textview.get_buffer().get_text(
            self.textview.get_buffer().get_start_iter(), 
            self.textview.get_buffer().get_end_iter(), 
            True
        )
        self.on_save_cb(self.block, self.block["code"])
        self._toggle_edit()

    def _do_copy(self, *_): 
        Gdk.Display.get_default().get_clipboard().set(self.block["code"])
        
    def _do_delete(self, *_): 
        self.on_delete_cb(self.block)

    def _open_ai_dialog(self, *_):
        if not self.ai_engine or not self.parent_window: return
        
        root = self.get_root()
        if not root: return

        project_root = None
        if hasattr(root, 'project_root'):
            project_root = root.project_root
            
        def on_confirm(block, new_code):
            self.block["code"] = new_code
            self.on_save_cb(self.block, new_code)
            self.textview.get_buffer().set_text(new_code)
            if hasattr(root, '_show_toast'):
                root._show_toast("✅ Bloc modifié par IA")

        dialog = AIModificationDialog(root, self.block, self.ai_engine, on_confirm, project_root=project_root)
        dialog.present()
        
    def _move_block(self, direction):
        """Déplace le bloc et sauvegarde."""
        def find_and_swap(blocks_list, target_block, dir):
            for i, b in enumerate(blocks_list):
                if b is target_block:
                    if dir == -1 and i > 0:
                        blocks_list[i], blocks_list[i-1] = blocks_list[i-1], blocks_list[i]
                        return True
                    elif dir == 1 and i < len(blocks_list) - 1:
                        blocks_list[i], blocks_list[i+1] = blocks_list[i+1], blocks_list[i]
                        return True
                if "children" in b and b["children"]:
                    if find_and_swap(b["children"], target_block, dir):
                        return True
            return False

        editor_view = self.parent_window
        
        if hasattr(editor_view, 'blocks') and find_and_swap(editor_view.blocks, self.block, direction):
            editor_view._push_state()
            editor_view._render_blocks()
            editor_view._save_file()
            
            if hasattr(editor_view, 'toast_cb'):
                editor_view.toast_cb("✅ Bloc déplacé")
        else:
            if hasattr(editor_view, 'toast_cb'):
                editor_view.toast_cb("⚠️ Limite atteinte")