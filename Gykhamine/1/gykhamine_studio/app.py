"""Module généré automatiquement depuis gy.py"""
import sys
from pathlib import Path
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk
Adw.init()
from .config import APP_ID, VERSION, LOGO_PATH, register_logger, set_margins, global_log
from .database import load_config, save_config, add_recent_project
from .ai_engine import BlockAIEngine
from .widgets import FilePanel, TerminalPanel, ControlPanel, BlockEditorView, SettingsDialog
from .styles import CSS

class GykhamineStudioApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.config = load_config()
        self.project_root = None
        self.is_fullscreen = False
        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        # 1. Application du thème CSS global
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # 2. Création de la fenêtre principale
        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title("Gykhamine Studio")
        self.win.set_default_size(1600, 950)

        # 3. Structure de base (Toast Overlay & Main Box)
        self.toast_overlay = Adw.ToastOverlay()
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # 4. Header Bar avec Logo et Boutons
        header = Adw.HeaderBar()
        logo_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        if LOGO_PATH.exists():
            try:
                from PIL import Image as PilImage
                import tempfile
                pil_img = PilImage.open(str(LOGO_PATH)).resize((15, 20), PilImage.LANCZOS)
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                pil_img.save(tmp.name)
                logo_picture = Gtk.Picture.new_for_filename(tmp.name)
                logo_picture.set_hexpand(False)
                logo_picture.set_vexpand(False)
                logo_box.append(logo_picture)
            except Exception:
                logo_box.append(Gtk.Label(label="GYKHAMINE", css_classes=["heading"]))
        else:
            logo_box.append(Gtk.Label(label="GYKHAMINE", css_classes=["heading"]))
            
        logo_box.append(Gtk.Label(label="GYKHAMINE STUDIO", css_classes=["heading"]))
        header.set_title_widget(logo_box)

        # Boutons de contrôle des panneaux
        self.btn_toggle_left = Gtk.Button(label="☰")
        self.btn_toggle_left.set_tooltip_text("Show/Hide explorer")
        self.btn_toggle_left.connect("clicked", self._toggle_left_panel)
        header.pack_start(self.btn_toggle_left)

        btn_open = Gtk.Button(label="📂 Open")
        btn_open.add_css_class("suggested-action")
        btn_open.connect("clicked", self._open_project_dialog)
        header.pack_start(btn_open)

        self.btn_toggle_terminal = Gtk.Button(label="🖥")
        self.btn_toggle_terminal.set_tooltip_text("Show/Hide terminal")
        self.btn_toggle_terminal.connect("clicked", self._toggle_terminal_panel)
        header.pack_end(self.btn_toggle_terminal)

        btn_fullscreen = Gtk.Button(label="⛶")
        btn_fullscreen.set_tooltip_text("Fullscreen")
        btn_fullscreen.connect("clicked", self._toggle_fullscreen)
        header.pack_end(btn_fullscreen)

        self.btn_toggle_right = Gtk.Button(label="⚙")
        self.btn_toggle_right.set_tooltip_text("Show/Hide control panel")
        self.btn_toggle_right.connect("clicked", self._toggle_right_panel)
        header.pack_end(self.btn_toggle_right)

        btn_settings = Gtk.Button(icon_name="preferences-system-symbolic")
        btn_settings.set_tooltip_text("Settings")
        btn_settings.connect("clicked", self._open_settings)
        header.pack_end(btn_settings)

        main_box.append(header)

        # 5. Panneaux Principaux
        self.main_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_paned.set_vexpand(True)
        self.main_paned.set_hexpand(True)
        self.main_paned.set_shrink_start_child(True)
        self.main_paned.set_shrink_end_child(False)
        self.main_paned.set_resize_start_child(True)
        self.main_paned.set_resize_end_child(True)

        self.file_panel = FilePanel(self._on_file_selected, self._load_project, self._on_file_created, self._on_file_imported)
        self.main_paned.set_start_child(self.file_panel)
        self.main_paned.set_position(320)

        self.workspace_paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.workspace_paned.set_vexpand(True)
        self.workspace_paned.set_hexpand(True)
        self.workspace_paned.set_shrink_start_child(False)
        self.workspace_paned.set_shrink_end_child(False)
        self.workspace_paned.set_resize_start_child(True)
        self.workspace_paned.set_resize_end_child(True)

        self.content_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.content_paned.set_shrink_start_child(False)
        self.content_paned.set_shrink_end_child(False)
        self.content_paned.set_resize_start_child(True)
        self.content_paned.set_resize_end_child(False)

        # Enregistrement du logger global
        register_logger(lambda msg: self.terminal_panel._log(msg))

        self.ai_engine = BlockAIEngine(
            config_getter=lambda: self.config,
            log_callback=lambda msg: self.terminal_panel._log(msg)
        )

        self.editor_view = BlockEditorView(
            self._show_toast,
            self._run_python_file,
            get_config_cb=lambda: self.config,
            ai_engine=self.ai_engine
        )
        self.content_paned.set_start_child(self.editor_view)
        self.content_paned.set_position(800)

        self.terminal_panel = TerminalPanel(
            get_project_root=lambda: self.project_root,
            get_config=lambda: self.config,
            show_toast=self._show_toast
        )

        self.control_panel = ControlPanel(
            get_project_root=lambda: self.project_root,
            get_config=lambda: self.config,
            show_toast=self._show_toast,
            terminal_panel=self.terminal_panel
        )

        self.ctrl_scroll = Gtk.ScrolledWindow()
        self.ctrl_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.ctrl_scroll.set_hexpand(True)
        self.ctrl_scroll.set_vexpand(True)
        self.ctrl_scroll.set_child(self.control_panel)
        self.content_paned.set_end_child(self.ctrl_scroll)

        self.workspace_paned.set_start_child(self.content_paned)
        self.workspace_paned.set_end_child(self.terminal_panel)
        self.workspace_paned.set_position(600)

        self.main_paned.set_end_child(self.workspace_paned)
        main_box.append(self.main_paned)

        self.toast_overlay.set_child(main_box)
        self.win.set_content(self.toast_overlay)
        self._apply_theme()

        # États initiaux des panneaux
        self.left_visible, self.right_visible, self.terminal_visible = True, True, True
        self._left_pos, self._right_pos, self._terminal_pos = 320, 800, 600

        # 6. AFFICHER LA FENÊTRE D'ABORD (Crucial pour éviter le vide)
        self.win.present()

        # 7. CHARGEMENT DU PROJET EN ARRIÈRE-PLAN UNE FOIS L'UI PRÊTE
        def _load_startup_project():
            last = self.config.get("last_project", "")
            if last and Path(last).exists():
                self._load_project(Path(last))
            elif len(sys.argv) > 1 and Path(sys.argv[1]).exists():
                self._load_project(Path(sys.argv[1]))
            
            # Forcer le rafraîchissement de la liste "Récents" après chargement
            GLib.idle_add(self.file_panel._load_recent_projects, self.config)

        # On utilise idle_add pour exécuter le chargement après que GTK ait fini de dessiner la fenêtre
        GLib.idle_add(_load_startup_project)               
        self.win.present()

    def _toggle_fullscreen(self, *_):
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen: self.win.fullscreen()
        else: self.win.unfullscreen()

    def _toggle_left_panel(self, *_):
        self.left_visible = not self.left_visible
        if self.left_visible:
            self.file_panel.set_visible(True); GLib.idle_add(lambda: self.main_paned.set_position(self._left_pos) and False); self.btn_toggle_left.set_label("☰")
        else:
            self._left_pos = self.main_paned.get_position(); self.main_paned.set_position(0); self.btn_toggle_left.set_label("▶")

    def _toggle_right_panel(self, *_):
        self.right_visible = not self.right_visible
        if self.right_visible:
            self.content_paned.set_end_child(self.ctrl_scroll); GLib.idle_add(lambda: self.content_paned.set_position(self._right_pos) or False); self.btn_toggle_right.set_label("⚙")
        else:
            self._right_pos = self.content_paned.get_position(); self.content_paned.set_end_child(None); self.btn_toggle_right.set_label("◀")

    def _toggle_terminal_panel(self, *_):
        self.terminal_visible = not self.terminal_visible
        if self.terminal_visible:
            self.terminal_panel.set_visible(True); GLib.idle_add(lambda: self.workspace_paned.set_position(self._terminal_pos) and False); self.btn_toggle_terminal.set_label("🖥")
        else:
            self._terminal_pos = self.workspace_paned.get_position(); self.terminal_panel.set_visible(False); GLib.idle_add(lambda: self.workspace_paned.set_position(10000) and False); self.btn_toggle_terminal.set_label("⌨")

    def _open_project_dialog(self, *_):
        Gtk.FileDialog(title="Open a project").select_folder(self.win, None, self._on_project_selected)

    def _on_project_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder: self._load_project(Path(folder.get_path()))
        except Exception as e:
            global_log(f"⚠️ Erreur dans gy.py: {type(e).__name__} - {e}")
    # Dans la classe GykhamineStudioApp, méthode _load_project
    def _load_project(self, path: Path):
        self.project_root = path
        self.config["last_project"] = str(path)
        
        # Ajout explicite à l'historique récent
        add_recent_project(str(path), self.config)
        
        # Rechargement de la config pour être sûr d'avoir les dernières données
        self.config = load_config()
        
        # Mise à jour de l'explorateur de fichiers (qui chargera aussi la liste des récents)
        self.file_panel.load_project(path, self.config)
        
        self.win.set_title(f"Gykhamine Studio — {path.name}")
        self._show_toast(f"📂 Project opened: {path.name}")
    def _on_file_selected(self, path: Path): self.editor_view.load_file(path)
    def _on_file_created(self, path: Path): self._show_toast(f"✅ Created: {path.name}"); self.editor_view.load_file(path)
    def _on_file_imported(self, path: Path): self._show_toast(f"📥 Imported: {path.name}"); self.editor_view.load_file(path)

    def _run_python_file(self, path: Path):
        if not path: return
        self._show_toast(f"▶ Running {path.name}"); self.terminal_panel._log(f"▶ python {path.name}")
        def _thread():
            try:
                proc = subprocess.Popen([sys.executable, str(path)], cwd=str(path.parent), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=0)
                def _read(stream):
                    for line in iter(stream.readline, ''):
                        if line: GLib.idle_add(self.terminal_panel._log, line.rstrip())
                    stream.close()
                t1 = threading.Thread(target=_read, args=(proc.stdout,), daemon=True)
                t2 = threading.Thread(target=_read, args=(proc.stderr,), daemon=True)
                t1.start(); t2.start(); t1.join(); t2.join(); proc.wait()
                GLib.idle_add(self.terminal_panel._log, f"✅ Finished (code {proc.returncode})")
            except Exception as e: GLib.idle_add(self.terminal_panel._log, f"❌ Error: {e}")
        threading.Thread(target=_thread, daemon=True).start()

    def _open_settings(self, *_):
        dlg = SettingsDialog(self.win, self.config, self._on_settings_saved); dlg.present(self.win)

    def _on_settings_saved(self, new_config):
        self.config = new_config; save_config(new_config); self._apply_theme(); self._show_toast("⚙ Saved")
        if self.project_root: self.file_panel.load_project(self.project_root, self.config)

    def _apply_theme(self):
        if self.config.get("theme", "dark") == "light": self.win.add_css_class("theme-light")
        else: self.win.remove_css_class("theme-light")

    def _show_toast(self, msg: str):
        self.toast_overlay.add_toast(Adw.Toast(title=msg, timeout=2))

if __name__ == "__main__":
    app = GykhamineStudioApp()
    sys.exit(app.run(sys.argv))
