"""Module généré automatiquement - Classe BlockCard"""
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk, Pango, GtkSource
from pathlib import Path

# Imports relatifs vers les modules racines
from ..config import global_log, set_margins
from ..ai_engine import AIModificationDialog

# Constantes locales nécessaires à l'affichage des icônes
TYPE_ICONS = {
    "import": "📦", "class": "🏛", "function": "⚡", "separator": "─",
    "comment": "💬", "other": "▪", "template": "🌐", "template_part": "🌐",
    "django_block": "🧩", "style": "🎨", "style_rule": "🎨",
    "script": "⚙️", "script_block": "⚡", "c_block": "⚙️"
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
        
        self.add_css_class("block-card")
        self.lang = self.file_ext.replace('.', '')
        if self.block["type"] == "style": self.lang = "css"
        elif self.block["type"] == "script": self.lang = "js"
        elif self.block["type"] in ("django_block", "template_part"): self.lang = "jinja"
        
        self._build_header()
        self._build_editor()

    def _build_header(self):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        set_margins(header, 8); header.set_margin_start(12)
        
        # Icône
        header.append(Gtk.Label(label=TYPE_ICONS.get(self.block["type"], "▪"), css_classes=["block-icon"]))
        
        # Badge Type
        badge = Gtk.Label(label=self.block["type"].upper())
        badge.add_css_class("block-badge")
        badge.add_css_class(f"badge-{self.block['type']}")
        header.append(badge)
        
        # Nom Hiérarchique
        hierarchical_id = self.block.get("hierarchical_id", " ")
        lbl_name = Gtk.Label(label=hierarchical_id)
        lbl_name.set_ellipsize(Pango.EllipsizeMode.NONE)
        lbl_name.set_hexpand(True)
        lbl_name.set_xalign(0)
        lbl_name.add_css_class("block-name")
        header.append(lbl_name)
        
        # Bouton IA
        if self.ai_engine:
            btn_ai = Gtk.Button(label="🤖 IA")
            btn_ai.set_tooltip_text("Modifier ce bloc avec l'IA")
            btn_ai.add_css_class("block-action-btn")
            btn_ai.add_css_class("btn-ai")
            btn_ai.connect("clicked", self._open_ai_dialog)
            header.append(btn_ai)
            
        # Boutons Déplacement
        btn_up = Gtk.Button(label="⬆")
        btn_up.set_tooltip_text("Monter le bloc")
        btn_up.add_css_class("block-action-btn")
        btn_up.connect("clicked", lambda *_: self._move_block(-1))
        
        btn_down = Gtk.Button(label="⬇")
        btn_down.set_tooltip_text("Descendre le bloc")
        btn_down.add_css_class("block-action-btn")
        btn_down.connect("clicked", lambda *_: self._move_block(1))
        
        header.append(btn_up)
        header.append(btn_down)

        # Boutons Actions Standard
        for label, tooltip, cb, css in [
            ("👁", "View / Edit", self._view_code, "btn-view"),
            ("✏", "Inline Edit", self._toggle_edit, "btn-edit"),
            ("⧉", "Copy", self._do_copy, "btn-copy"),
            ("✕", "Delete", self._do_delete, "btn-delete")
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

    def _build_editor(self):
        self.editor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        set_margins(self.editor_box, 0)
        self.editor_box.set_margin_start(12)
        self.editor_box.set_margin_end(12)
        self.editor_box.set_margin_bottom(8)
        self.editor_box.set_visible(False)
        
        # Vue Source
        self.textview = GtkSource.View()
        self.textview.set_monospace(True)
        self.textview.set_wrap_mode(Gtk.WrapMode.NONE)
        self.textview.set_show_line_numbers(True)
        self.textview.set_highlight_current_line(True)
        self.textview.set_auto_indent(True)
        self.textview.set_insert_spaces_instead_of_tabs(True)
        self.textview.set_tab_width(4)
        self.textview.add_css_class("code-editor")
        
        # Buffer et Langage
        buffer = GtkSource.Buffer()
        lang_mgr = GtkSource.LanguageManager.get_default()
        lang_map = {
            'py': 'python', 'js': 'javascript', 'css': 'css', 
            'html': 'html', 'c': 'c', 'cpp': 'cpp', 'sh': 'sh', 
            'jinja': 'html'
        }
        lang_id = lang_map.get(self.lang, 'text')
        language = lang_mgr.get_language(lang_id)
        if language:
            buffer.set_language(language)
            
        # Thème Sombre
        scheme_mgr = GtkSource.StyleSchemeManager.get_default()
        scheme = scheme_mgr.get_scheme('Adwaita-dark') or scheme_mgr.get_scheme('cobalt') or scheme_mgr.get_scheme('oblivion')
        if scheme:
            buffer.set_style_scheme(scheme)
            
        buffer.set_text(self.block["code"])
        self.textview.set_buffer(buffer)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_size_request(-1, 200)
        scroll.set_child(self.textview)
        
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_cancel = Gtk.Button(label="✕ Close")
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
        textview.add_css_class("code-editor")
        
        buffer = GtkSource.Buffer()
        lang_mgr = GtkSource.LanguageManager.get_default()
        lang_map = {
            'py': 'python', 'js': 'javascript', 'css': 'css',
            'html': 'html', 'c': 'c', 'cpp': 'cpp', 'sh': 'sh',
            'jinja': 'html'
        }
        lang_id = lang_map.get(self.lang, 'text')
        language = lang_mgr.get_language(lang_id)
        if language:
            buffer.set_language(language)
            
        scheme_mgr = GtkSource.StyleSchemeManager.get_default()
        scheme = scheme_mgr.get_scheme('Adwaita-dark') or scheme_mgr.get_scheme('cobalt') or scheme_mgr.get_scheme('oblivion')
        if scheme:
            buffer.set_style_scheme(scheme)
            
        buffer.set_text(self.block["code"])
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
                editor_view.toast_cb("✅ Bloc déplacé et fichier sauvegardé")
        else:
            if hasattr(editor_view, 'toast_cb'):
                editor_view.toast_cb("⚠️ Limite de déplacement atteinte")
