"""Gestionnaire de Prompts IA : popup listant les prompts (table ai_prompts) sous forme
de cartes façon éditeur de blocs (voir/éditer/copier/supprimer), avec ajout de nouveaux prompts."""
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gdk, Pango

from ..config import global_log, set_margins, enable_window_controls
from ..database import get_all_prompts, save_prompt, delete_prompt


class PromptCard(Gtk.Box):
    """Une carte représentant un prompt IA, avec le même comportement que les cartes de blocs :
    👁 Voir, ✏ Modifier (édition inline), ⧉ Copier, ✕ Supprimer (désactivé pour les défauts)."""

    def __init__(self, prompt: dict, on_saved, on_deleted, show_toast):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.prompt = prompt
        self.on_saved = on_saved
        self.on_deleted = on_deleted
        self.show_toast = show_toast
        self.expanded = False
        self.add_css_class("block-card")

        self._build_header()
        self._build_editor()

    def _build_header(self):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        set_margins(header, 8); header.set_margin_start(12)

        icon = "🔒" if self.prompt["is_default"] else "🧠"
        header.append(Gtk.Label(label=icon, css_classes=["block-icon"]))

        badge = Gtk.Label(label="DÉFAUT" if self.prompt["is_default"] else "PERSONNALISÉ")
        badge.add_css_class("block-badge")
        badge.add_css_class("badge-class" if self.prompt["is_default"] else "badge-function")
        header.append(badge)

        lbl_name = Gtk.Label(label=self.prompt["name"])
        lbl_name.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        lbl_name.set_hexpand(True); lbl_name.set_xalign(0)
        lbl_name.add_css_class("block-name")
        header.append(lbl_name)

        for label, tooltip, cb in [
            ("👁", "Voir en grand", self._view_full),
            ("✏", "Modifier", self._toggle_edit),
            ("⧉", "Copier", self._do_copy),
        ]:
            btn = Gtk.Button(label=label); btn.set_tooltip_text(tooltip)
            btn.add_css_class("block-action-btn")
            btn.connect("clicked", cb)
            header.append(btn)

        btn_delete = Gtk.Button(label="✕")
        btn_delete.add_css_class("block-action-btn")
        if self.prompt["is_default"]:
            btn_delete.set_tooltip_text("Un prompt par défaut ne peut pas être supprimé")
            btn_delete.set_sensitive(False)
        else:
            btn_delete.set_tooltip_text("Supprimer")
            btn_delete.connect("clicked", self._do_delete)
        header.append(btn_delete)

        self.append(header)

        bar = Gtk.Box(); bar.set_size_request(-1, 2)
        bar.add_css_class("block-accent-bar")
        bar.add_css_class("accent-class" if self.prompt["is_default"] else "accent-function")
        self.append(bar)

    def _build_editor(self):
        self.editor_revealer = Gtk.Revealer()
        self.editor_revealer.set_reveal_child(False)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        set_margins(box, 10)

        scroll = Gtk.ScrolledWindow(); scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_size_request(-1, 160)
        self.textview = Gtk.TextView(); self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textview.get_buffer().set_text(self.prompt["content"])
        scroll.set_child(self.textview)
        box.append(scroll)

        btn_save = Gtk.Button(label="💾 Sauvegarder"); btn_save.add_css_class("suggested-action")
        btn_save.set_halign(Gtk.Align.END)
        btn_save.connect("clicked", self._do_save)
        box.append(btn_save)

        self.editor_revealer.set_child(box)
        self.append(self.editor_revealer)

    def _toggle_edit(self, *_):
        self.expanded = not self.expanded
        self.editor_revealer.set_reveal_child(self.expanded)

    def _view_full(self, *_):
        dialog = Gtk.Dialog(title=self.prompt["name"], transient_for=self.get_root())
        dialog.add_css_class("rounded-dialog")
        dialog.set_default_size(600, 400)
        enable_window_controls(dialog, self.prompt["name"])
        content = dialog.get_content_area(); set_margins(content, 16)
        scroll = Gtk.ScrolledWindow(); scroll.set_vexpand(True)
        tv = Gtk.TextView(); tv.set_editable(False); tv.set_wrap_mode(Gtk.WrapMode.WORD)
        tv.get_buffer().set_text(self.prompt["content"])
        scroll.set_child(tv)
        content.append(scroll)
        dialog.present()

    def _do_copy(self, *_):
        Gdk.Display.get_default().get_clipboard().set(self.prompt["content"])
        self.show_toast(f"⧉ Prompt « {self.prompt['name']} » copié")

    def _do_save(self, *_):
        buf = self.textview.get_buffer()
        new_content = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True).strip()
        if not new_content:
            self.show_toast("❌ Le contenu du prompt ne peut pas être vide")
            return
        if save_prompt(self.prompt["name"], new_content, category=self.prompt.get("category", "custom")):
            self.prompt["content"] = new_content
            self.show_toast(f"💾 Prompt « {self.prompt['name']} » sauvegardé")
            if self.on_saved:
                self.on_saved()
        else:
            self.show_toast("❌ Échec de la sauvegarde en base")

    def _do_delete(self, *_):
        if delete_prompt(self.prompt["name"]):
            self.show_toast(f"🗑 Prompt « {self.prompt['name']} » supprimé")
            if self.on_deleted:
                self.on_deleted()
        else:
            self.show_toast("❌ Suppression refusée ou échouée")


class PromptManagerDialog(Gtk.Window):
    """Fenêtre listant tous les prompts IA (table ai_prompts) sous forme de cartes."""

    def __init__(self, parent, show_toast=None):
        super().__init__(title="🧠 Gestionnaire de Prompts IA")
        self.set_transient_for(parent)
        self.set_default_size(760, 640)
        # La fenêtre construit sa propre Adw.HeaderBar juste en dessous : sans
        # set_decorated(False), GTK affiche EN PLUS sa barre de titre système
        # avec le même texte -> double titre superposé (bug rapporté).
        self.set_decorated(False)
        self.set_resizable(True)
        self.add_css_class("rounded-dialog")
        self.show_toast = show_toast or (lambda msg: None)

        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        header = Adw.HeaderBar()
        # Sans décoration système, il faut demander explicitement les boutons
        # réduire/agrandir/fermer sur notre barre custom (voir cache_manager_dialog.py).
        header.set_show_end_title_buttons(True)
        header.set_decoration_layout("minimize,maximize,close")
        btn_add = Gtk.Button(label="➕ Nouveau prompt"); btn_add.add_css_class("suggested-action")
        btn_add.connect("clicked", self._open_add_dialog)
        header.pack_end(btn_add)
        btn_refresh = Gtk.Button(label="🔄"); btn_refresh.set_tooltip_text("Actualiser")
        btn_refresh.connect("clicked", lambda *_: self._reload())
        header.pack_end(btn_refresh)
        root_box.append(header)

        self.scroll = Gtk.ScrolledWindow(); self.scroll.set_vexpand(True); self.scroll.set_hexpand(True)
        self.cards_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        set_margins(self.cards_box, 14)
        self.scroll.set_child(self.cards_box)
        root_box.append(self.scroll)

        self.set_child(root_box)
        self._reload()

    def _reload(self):
        while (child := self.cards_box.get_first_child()):
            self.cards_box.remove(child)
        prompts = get_all_prompts()
        if not prompts:
            self.cards_box.append(Gtk.Label(label="Aucun prompt trouvé."))
            return
        for p in prompts:
            card = PromptCard(p, on_saved=self._reload, on_deleted=self._reload, show_toast=self.show_toast)
            self.cards_box.append(card)

    def _open_add_dialog(self, *_):
        dialog = Gtk.Dialog(title="Nouveau prompt IA", transient_for=self, default_width=520, default_height=380)
        dialog.add_css_class("rounded-dialog")
        enable_window_controls(dialog, "Nouveau prompt IA")
        content = dialog.get_content_area(); content.set_spacing(10); set_margins(content, 16)

        content.append(Gtk.Label(label="Nom du prompt :", xalign=0))
        entry_name = Gtk.Entry(); entry_name.set_placeholder_text("Ex: Expert en Sécurité Web")
        content.append(entry_name)

        content.append(Gtk.Label(label="Contenu du prompt :", xalign=0, margin_top=8))
        scroll = Gtk.ScrolledWindow(); scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_size_request(-1, 160)
        text_prompt = Gtk.TextView(); text_prompt.set_wrap_mode(Gtk.WrapMode.WORD)
        scroll.set_child(text_prompt)
        content.append(scroll)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, halign=Gtk.Align.END, margin_top=12)
        btn_cancel = Gtk.Button(label="Annuler"); btn_cancel.connect("clicked", lambda *_: dialog.destroy())
        btn_save = Gtk.Button(label="💾 Créer", css_classes=["suggested-action"])
        btn_box.append(btn_cancel); btn_box.append(btn_save)
        content.append(btn_box)

        def on_save(*_):
            name = entry_name.get_text().strip()
            buf = text_prompt.get_buffer()
            body = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True).strip()
            if not name or not body:
                self.show_toast("❌ Le nom et le contenu sont requis")
                return
            if save_prompt(name, body, category="custom"):
                self.show_toast(f"✅ Prompt « {name} » créé")
                self._reload()
                dialog.destroy()
            else:
                self.show_toast("❌ Échec de la création (nom déjà pris ?)")

        btn_save.connect("clicked", on_save)
        dialog.present()
