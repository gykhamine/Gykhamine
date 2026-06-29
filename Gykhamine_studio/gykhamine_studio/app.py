"""Module généré automatiquement depuis gy.py"""
import sys, subprocess, threading, socket, tempfile, re
from pathlib import Path
from datetime import datetime
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk, Pango
Adw.init()
from .config import APP_ID, VERSION, LOGO_PATH, register_logger, set_margins, global_log
from .database import load_config, save_config, add_recent_project
from .ai_engine import BlockAIEngine
from .widgets import FilePanel, TerminalPanel, ControlPanel, BlockEditorView, SettingsDialog
from .styles import CSS
from .runtime import RuntimeManager, RuntimeDialog


class GykhamineStudioApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.config = load_config()
        self.project_root = None
        self.is_fullscreen = False
        self.runtime_manager = RuntimeManager()
        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        # 1. CSS global theme
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # 2. Fenêtre principale
        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title("Gykhamine Studio")
        self.win.set_default_size(1600, 950)

        # 3. Structure
        self.toast_overlay = Adw.ToastOverlay()
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # 4. Header Bar
        header = Adw.HeaderBar()
        logo_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        if LOGO_PATH.exists():
            try:
                from PIL import Image as PilImage
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

        # Panel toggle buttons
        self.btn_toggle_left = Gtk.Button(label="☰")
        self.btn_toggle_left.set_tooltip_text("Explorer (F9)")
        self.btn_toggle_left.connect("clicked", self._toggle_left_panel)
        header.pack_start(self.btn_toggle_left)

        btn_open = Gtk.Button(label="📂 Open")
        btn_open.add_css_class("suggested-action")
        btn_open.connect("clicked", self._open_project_dialog)
        header.pack_start(btn_open)

        # IP / QR Code button
        btn_ip_qr = Gtk.Button(label="🌐 IP/QR")
        btn_ip_qr.set_tooltip_text("Afficher IP publique et QR code")
        btn_ip_qr.add_css_class("flat")
        btn_ip_qr.connect("clicked", self._show_ip_qr_dialog)
        header.pack_start(btn_ip_qr)

        self.btn_toggle_terminal = Gtk.Button(label="🖥")
        self.btn_toggle_terminal.set_tooltip_text("Terminal (F12)")
        self.btn_toggle_terminal.connect("clicked", self._toggle_terminal_panel)
        header.pack_end(self.btn_toggle_terminal)

        btn_fullscreen = Gtk.Button(label="⛶")
        btn_fullscreen.set_tooltip_text("Plein écran (F11)")
        btn_fullscreen.connect("clicked", self._toggle_fullscreen)
        header.pack_end(btn_fullscreen)

        self.btn_toggle_right = Gtk.Button(label="⚙")
        self.btn_toggle_right.set_tooltip_text("Panneau contrôle (F8)")
        self.btn_toggle_right.connect("clicked", self._toggle_right_panel)
        header.pack_end(self.btn_toggle_right)

        btn_settings = Gtk.Button(icon_name="preferences-system-symbolic")
        btn_settings.set_tooltip_text("Paramètres")
        btn_settings.connect("clicked", self._open_settings)
        header.pack_end(btn_settings)

        btn_runtime = Gtk.Button(label="⚡")
        btn_runtime.set_tooltip_text("Runtimes — automatisations")
        btn_runtime.add_css_class("flat")
        btn_runtime.connect("clicked", self._open_runtime_dialog)
        header.pack_end(btn_runtime)

        main_box.append(header)

        # 5. Main panels
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

        # Logger
        register_logger(lambda msg: self.terminal_panel._log(msg))

        self.ai_engine = BlockAIEngine(
            config_getter=lambda: self.config,
            log_callback=lambda msg: self.terminal_panel._log(msg)
        )

        self.editor_view = BlockEditorView(
            self._show_toast,
            self._run_python_file,
            get_config_cb=lambda: self.config,
            ai_engine=self.ai_engine,
            status_update_cb=self._update_status_bar
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

        # 6. Status Bar
        self.status_bar = self._build_status_bar()
        main_box.append(Gtk.Separator())
        main_box.append(self.status_bar)

        self.toast_overlay.set_child(main_box)
        self.win.set_content(self.toast_overlay)
        self._apply_theme()

        # Panel states
        self.left_visible, self.right_visible, self.terminal_visible = True, True, True
        self._left_pos, self._right_pos, self._terminal_pos = 320, 800, 600

        # 7. Keyboard shortcuts
        self._setup_keyboard_shortcuts()

        # 8. Show window first
        self.win.present()

        # 9. Load startup project + last file in background
        def _load_startup_project():
            last = self.config.get("last_project", "")
            if last and Path(last).exists():
                self._load_project(Path(last))
            elif len(sys.argv) > 1 and Path(sys.argv[1]).exists():
                self._load_project(Path(sys.argv[1]))
            
            # Auto-load last opened file
            last_file = self.config.get("last_file", "")
            if last_file and Path(last_file).exists():
                GLib.idle_add(self._on_file_selected, Path(last_file))
            
            GLib.idle_add(self.file_panel._load_recent_projects, self.config)

        GLib.idle_add(_load_startup_project)               
        self.win.present()

        # Register user actions for runtime
        def _register_actions():
            rm = self.runtime_manager
            rm.register_action("open_last_project", "Ouvrir le dernier projet", lambda: self._load_project(Path(self.config.get("last_project", ""))) if self.config.get("last_project") and Path(self.config.get("last_project", "")).exists() else None)
            rm.register_action("run_current_file", "Lancer le fichier courant", self.editor_view._run_current_file)
            rm.register_action("save_current_file", "Sauvegarder le fichier courant", self.editor_view._save_file)
            rm.register_action("start_django_dev", "Démarrer Django dev server", lambda: self.control_panel._start_django() if hasattr(self.control_panel, '_start_django') else None)
            rm.register_action("stop_all_services", "Arrêter tous les services", lambda: self.control_panel._stop_all_services() if hasattr(self.control_panel, '_stop_all_services') else None)
            # Lancer le runtime automatique si défini
            def _log(msg): 
                if hasattr(self, 'terminal_panel'):
                    self.terminal_panel._log(msg)
            rm.run_auto(_log)
        GLib.idle_add(_register_actions)

    def _build_status_bar(self):
        """Barre de statut professionnelle en bas de la fenêtre."""
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bar.add_css_class("status-bar")
        set_margins(bar, 4)
        bar.set_margin_start(12)
        bar.set_margin_end(12)

        self.status_project = Gtk.Label(label="Aucun projet")
        self.status_project.set_xalign(0)
        self.status_project.add_css_class("dim-label")
        bar.append(self.status_project)

        sep1 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep1.set_margin_top(2)
        sep1.set_margin_bottom(2)
        bar.append(sep1)

        self.status_file = Gtk.Label(label="")
        self.status_file.set_xalign(0)
        self.status_file.add_css_class("dim-label")
        bar.append(self.status_file)

        sep2 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep2.set_margin_top(2)
        sep2.set_margin_bottom(2)
        bar.append(sep2)

        self.status_info = Gtk.Label(label="")
        self.status_info.set_xalign(0)
        self.status_info.add_css_class("dim-label")
        bar.append(self.status_info)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        bar.append(spacer)

        self.status_encoding = Gtk.Label(label="UTF-8")
        self.status_encoding.set_xalign(1)
        self.status_encoding.add_css_class("dim-label")
        bar.append(self.status_encoding)

        sep3 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep3.set_margin_top(2)
        sep3.set_margin_bottom(2)
        bar.append(sep3)

        self.status_lang = Gtk.Label(label="")
        self.status_lang.set_xalign(1)
        self.status_lang.add_css_class("dim-label")
        bar.append(self.status_lang)

        return bar

    def _update_status_bar(self, file_path=None, info=None):
        """Met à jour la barre de statut."""
        if file_path:
            p = Path(file_path)
            self.status_file.set_text(f"📄 {p.name}")
            self.status_info.set_text(f"{p.parent}")
            # Detect language from extension
            from .parser import get_gtksource_lang_id
            ext = p.suffix.lstrip('.').lower()
            lang_id = get_gtksource_lang_id(ext)
            self.status_lang.set_text(lang_id.upper())
            
            # Save last opened file
            self.config["last_file"] = str(file_path)
            save_config(self.config)
        elif info:
            self.status_info.set_text(info)

    def _setup_keyboard_shortcuts(self):
        """Configure les raccourcis clavier globaux."""
        # Ctrl+S = Save
        key_ctrl_s = Gtk.ShortcutTrigger.parse_string("<Control>s")
        action_save = Gtk.CallbackAction.new(lambda *_: self.editor_view._save_file())
        self.win.add_shortcut(Gtk.Shortcut.new(key_ctrl_s, action_save))

        # Ctrl+Z = Undo
        key_ctrl_z = Gtk.ShortcutTrigger.parse_string("<Control>z")
        action_undo = Gtk.CallbackAction.new(lambda *_: self.editor_view._undo())
        self.win.add_shortcut(Gtk.Shortcut.new(key_ctrl_z, action_undo))

        # Ctrl+Shift+Z = Redo
        key_ctrl_sz = Gtk.ShortcutTrigger.parse_string("<Control><Shift>z")
        action_redo = Gtk.CallbackAction.new(lambda *_: self.editor_view._redo())
        self.win.add_shortcut(Gtk.Shortcut.new(key_ctrl_sz, action_redo))

        # Ctrl+W = Close tab
        key_ctrl_w = Gtk.ShortcutTrigger.parse_string("<Control>w")
        action_close_tab = Gtk.CallbackAction.new(lambda *_: self._close_active_tab())
        self.win.add_shortcut(Gtk.Shortcut.new(key_ctrl_w, action_close_tab))

        # Ctrl+Tab = Next tab
        key_ctrl_tab = Gtk.ShortcutTrigger.parse_string("<Control>Tab")
        action_next_tab = Gtk.CallbackAction.new(lambda *_: self._switch_tab(1))
        self.win.add_shortcut(Gtk.Shortcut.new(key_ctrl_tab, action_next_tab))

        # Ctrl+Shift+Tab = Previous tab
        key_ctrl_stab = Gtk.ShortcutTrigger.parse_string("<Control><Shift>Tab")
        action_prev_tab = Gtk.CallbackAction.new(lambda *_: self._switch_tab(-1))
        self.win.add_shortcut(Gtk.Shortcut.new(key_ctrl_stab, action_prev_tab))

        # Ctrl+N = New file
        key_ctrl_n = Gtk.ShortcutTrigger.parse_string("<Control>n")
        action_new = Gtk.CallbackAction.new(lambda *_: self.file_panel._create_new_file())
        self.win.add_shortcut(Gtk.Shortcut.new(key_ctrl_n, action_new))

        # F5 = Run
        key_f5 = Gtk.ShortcutTrigger.parse_string("F5")
        action_run = Gtk.CallbackAction.new(lambda *_: self.editor_view._run_current_file())
        self.win.add_shortcut(Gtk.Shortcut.new(key_f5, action_run))

        # F11 = Fullscreen
        key_f11 = Gtk.ShortcutTrigger.parse_string("F11")
        action_fs = Gtk.CallbackAction.new(lambda *_: self._toggle_fullscreen())
        self.win.add_shortcut(Gtk.Shortcut.new(key_f11, action_fs))

        # F9 = Toggle left panel
        key_f9 = Gtk.ShortcutTrigger.parse_string("F9")
        action_lp = Gtk.CallbackAction.new(lambda *_: self._toggle_left_panel())
        self.win.add_shortcut(Gtk.Shortcut.new(key_f9, action_lp))

        # F12 = Toggle terminal
        key_f12 = Gtk.ShortcutTrigger.parse_string("F12")
        action_tp = Gtk.CallbackAction.new(lambda *_: self._toggle_terminal_panel())
        self.win.add_shortcut(Gtk.Shortcut.new(key_f12, action_tp))

        # F8 = Toggle right panel
        key_f8 = Gtk.ShortcutTrigger.parse_string("F8")
        action_rp = Gtk.CallbackAction.new(lambda *_: self._toggle_right_panel())
        self.win.add_shortcut(Gtk.Shortcut.new(key_f8, action_rp))

        # Ctrl+P = Open project
        key_ctrl_p = Gtk.ShortcutTrigger.parse_string("<Control>p")
        action_open = Gtk.CallbackAction.new(lambda *_: self._open_project_dialog())
        self.win.add_shortcut(Gtk.Shortcut.new(key_ctrl_p, action_open))

    def _close_active_tab(self):
        if self.editor_view.active_tab_path:
            self.editor_view._close_tab(self.editor_view.active_tab_path)

    def _switch_tab(self, direction):
        tabs = list(self.editor_view.open_tabs.keys())
        if not tabs:
            return
        if self.editor_view.active_tab_path in tabs:
            idx = tabs.index(self.editor_view.active_tab_path)
            new_idx = (idx + direction) % len(tabs)
            self.editor_view._activate_tab(tabs[new_idx])

    # ── IP / QR CODE / WIFI DIALOG ──────────────────────────────────
    def _show_ip_qr_dialog(self, *_):
        """Affiche la liste des IPs détectées via `hostname -I`,
        le QR code HTTPS, et le QR code WiFi. Serveur en réseau fermé :
        pas d'IP publique, tout vient de hostname -I.
        """
        dialog = Gtk.Dialog(title="IP / QR Code / WiFi", transient_for=self.win)
        dialog.add_css_class("rounded-dialog")
        dialog.set_default_size(560, 760)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        set_margins(content, 20)
        dialog.set_child(content)

        # Title
        title = Gtk.Label(label="🌐 Connexion réseau & WiFi")
        title.add_css_class("panel-title")
        title.set_xalign(0)
        content.append(title)

        # ── IPs via `hostname -I` (réseau fermé : pas d'IP publique) ──
        local_ips = self._get_local_ips()
        if not local_ips:
            local_ips = ["127.0.0.1"]

        # ── SÉLECTEUR D'IP ──────────────────────────────────────────
        # Dropdown listant TOUTES les IPs renvoyées par hostname -I + option
        # "Personnalisé…" pour saisir manuellement (utile si l'utilisateur veut
        # mettre une IP statique, un hostname DNS, etc.)
        ip_selector_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ip_selector_box.append(Gtk.Label(label="IP réseau:", xalign=0, css_classes=["toolbar-label"]))

        ip_combo = Gtk.ComboBoxText()
        for ip in local_ips:
            ip_combo.append_text(ip)
        # Option "Personnalisé…" en queue
        ip_combo.append_text("Personnalisé…")
        ip_combo.set_active(0)
        ip_combo.set_hexpand(True)
        ip_combo.set_tooltip_text(
            "IPs détectées via: hostname -I\n"
            + "\n".join(f"  • {ip}" for ip in local_ips)
        )
        ip_selector_box.append(ip_combo)

        # Entry éditable pour la personnalisation (initialement caché)
        ip_custom_entry = Gtk.Entry()
        ip_custom_entry.set_placeholder_text("Saisir IP ou hostname…")
        ip_custom_entry.set_hexpand(True)
        ip_custom_entry.set_visible(False)
        ip_selector_box.append(ip_custom_entry)

        btn_refresh_ips = Gtk.Button(label="🔄")
        btn_refresh_ips.set_tooltip_text("Relancer hostname -I")
        btn_refresh_ips.add_css_class("flat")
        ip_selector_box.append(btn_refresh_ips)

        content.append(ip_selector_box)

        # Variable d'état : IP actuellement sélectionnée (par défaut la 1ère de hostname -I)
        state = {"selected_ip": local_ips[0]}

        def _on_ip_combo_changed(*_):
            idx = ip_combo.get_active()
            if idx < 0:
                return
            if idx < len(local_ips):
                # IP détectée par hostname -I
                ip_custom_entry.set_visible(False)
                state["selected_ip"] = local_ips[idx]
            else:
                # "Personnalisé…"
                ip_custom_entry.set_visible(True)
                state["selected_ip"] = ip_custom_entry.get_text().strip() or "127.0.0.1"
                ip_custom_entry.grab_focus()
            _on_url_changed()

        def _on_custom_ip_changed(*_):
            if ip_combo.get_active() == len(local_ips):
                state["selected_ip"] = ip_custom_entry.get_text().strip() or "127.0.0.1"
                _on_url_changed()

        ip_combo.connect("changed", _on_ip_combo_changed)
        ip_custom_entry.connect("changed", _on_custom_ip_changed)

        def _refresh_ips(*_):
            nonlocal local_ips
            new_ips = self._get_local_ips()
            if not new_ips:
                self._show_toast("⚠️ hostname -I n'a renvoyé aucune IP")
                return
            local_ips = new_ips
            # Reconstruire le dropdown
            ip_combo.remove_all()
            for ip in local_ips:
                ip_combo.append_text(ip)
            ip_combo.append_text("Personnalisé…")
            ip_combo.set_active(0)
            ip_custom_entry.set_visible(False)
            state["selected_ip"] = local_ips[0]
            self._show_toast(f"🔄 {len(local_ips)} IP(s) détectée(s)")
            _on_url_changed()

        btn_refresh_ips.connect("clicked", _refresh_ips)

        # ── PORT + SCHÈME ────────────────────────────────────────────
        scheme_port_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        scheme_port_box.append(Gtk.Label(label="Schéma:", xalign=0, css_classes=["toolbar-label"]))
        scheme_combo = Gtk.ComboBoxText()
        scheme_combo.append_text("https://")
        scheme_combo.append_text("http://")
        scheme_combo.set_active(0)  # HTTPS par défaut
        scheme_combo.set_hexpand(False)
        scheme_port_box.append(scheme_combo)
        scheme_port_box.append(Gtk.Label(label="Port:", xalign=0, css_classes=["toolbar-label"]))
        port_entry = Gtk.Entry()
        port_entry.set_text("443")
        port_entry.set_hexpand(True)
        port_entry.set_tooltip_text("HTTPS par défaut → 443 (reverse-proxy nginx). HTTP → 8000 (gunicorn direct).")
        scheme_port_box.append(port_entry)
        content.append(scheme_port_box)

        # ── URL ──────────────────────────────────────────────────────
        url_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        url_box.set_margin_top(4)
        url_box.append(Gtk.Label(label="URL:", xalign=0, css_classes=["toolbar-label"]))
        url_label = Gtk.Label(label=f"https://{state['selected_ip']}/")
        url_label.set_selectable(True)
        url_label.set_hexpand(True)
        url_label.set_xalign(0)
        url_label.add_css_class("mono")
        url_box.append(url_label)
        btn_copy_url = Gtk.Button(label="⧉")
        btn_copy_url.set_tooltip_text("Copier l'URL")
        btn_copy_url.add_css_class("flat")
        url_box.append(btn_copy_url)
        content.append(url_box)

        # ── BOUTON OUVRIR DANS LE NAVIGATEUR ─────────────────────────
        btn_open_browser = Gtk.Button(label="🚀 Ouvrir dans le navigateur")
        btn_open_browser.add_css_class("suggested-action")
        btn_open_browser.set_halign(Gtk.Align.START)
        content.append(btn_open_browser)

        # ── SÉPARATEUR ───────────────────────────────────────────────
        sep = Gtk.Separator()
        sep.set_margin_top(8)
        sep.set_margin_bottom(4)
        content.append(sep)

        # ── QR CODES (côte à côte) ───────────────────────────────────
        qr_section_title = Gtk.Label(label="📱 QR Codes de connexion")
        qr_section_title.add_css_class("panel-title")
        qr_section_title.set_xalign(0)
        content.append(qr_section_title)

        qr_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        qr_row.set_halign(Gtk.Align.CENTER)
        content.append(qr_row)

        # QR Code 1: URL HTTPS
        qr_url_frame = Gtk.Frame()
        qr_url_frame.set_label("🔗 URL HTTPS")
        qr_url_frame.set_label_align(0.5)
        qr_row.append(qr_url_frame)

        qr_url_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        qr_url_box.set_margin_start(12)
        qr_url_box.set_margin_end(12)
        qr_url_box.set_margin_top(12)
        qr_url_box.set_margin_bottom(12)
        qr_url_frame.set_child(qr_url_box)

        qr_url_image = Gtk.Picture()
        qr_url_image.set_size_request(180, 180)
        qr_url_box.append(qr_url_image)

        qr_url_caption = Gtk.Label(label="Scannez pour ouvrir l'URL")
        qr_url_caption.add_css_class("dim-label")
        qr_url_box.append(qr_url_caption)

        # QR Code 2: WiFi
        qr_wifi_frame = Gtk.Frame()
        qr_wifi_frame.set_label("📶 WiFi")
        qr_wifi_frame.set_label_align(0.5)
        qr_row.append(qr_wifi_frame)

        qr_wifi_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        qr_wifi_box.set_margin_start(12)
        qr_wifi_box.set_margin_end(12)
        qr_wifi_box.set_margin_top(12)
        qr_wifi_box.set_margin_bottom(12)
        qr_wifi_frame.set_child(qr_wifi_box)

        qr_wifi_image = Gtk.Picture()
        qr_wifi_image.set_size_request(180, 180)
        qr_wifi_box.append(qr_wifi_image)

        qr_wifi_caption = Gtk.Label(label="Scannez pour rejoindre le WiFi")
        qr_wifi_caption.add_css_class("dim-label")
        qr_wifi_box.append(qr_wifi_caption)

        # ── CHAMPS WIFI MANUELS (fallback si non auto-détecté) ───────
        wifi_fields = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        wifi_fields.set_margin_top(8)
        content.append(wifi_fields)

        wifi_detect_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        wifi_detect_row.append(Gtk.Label(label="SSID WiFi:", xalign=0, css_classes=["toolbar-label"]))
        ssid_entry = Gtk.Entry()
        ssid_entry.set_placeholder_text("Nom du réseau WiFi")
        ssid_entry.set_hexpand(True)
        wifi_detect_row.append(ssid_entry)
        btn_detect_wifi = Gtk.Button(label="🔍 Détecter")
        btn_detect_wifi.set_tooltip_text("Tente de détecter le SSID WiFi actif")
        wifi_detect_row.append(btn_detect_wifi)
        wifi_fields.append(wifi_detect_row)

        wifi_pass_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        wifi_pass_row.append(Gtk.Label(label="Mot de passe:", xalign=0, css_classes=["toolbar-label"]))
        pass_entry = Gtk.Entry()
        pass_entry.set_placeholder_text("Laisser vide si réseau ouvert")
        pass_entry.set_hexpand(True)
        wifi_pass_row.append(pass_entry)
        wifi_fields.append(wifi_pass_row)

        wifi_type_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        wifi_type_row.append(Gtk.Label(label="Sécurité:", xalign=0, css_classes=["toolbar-label"]))
        wifi_type_combo = Gtk.ComboBoxText()
        wifi_type_combo.append_text("WPA/WPA2")
        wifi_type_combo.append_text("WEP")
        wifi_type_combo.append_text("Aucune (ouvert)")
        wifi_type_combo.set_active(0)
        wifi_type_combo.set_hexpand(True)
        wifi_type_row.append(wifi_type_combo)
        wifi_fields.append(wifi_type_row)

        # ── LOGIQUE DE MISE À JOUR ───────────────────────────────────
        def _compute_url() -> str:
            scheme = scheme_combo.get_active_text() or "https://"
            port = port_entry.get_text().strip() or "443"
            ip = state["selected_ip"] or "127.0.0.1"
            # Masquer le port par défaut (80 pour http, 443 pour https)
            if (scheme == "https://" and port == "443") or (scheme == "http://" and port == "80"):
                return f"{scheme}{ip}/"
            return f"{scheme}{ip}:{port}/"

        def _update_url_display():
            u = _compute_url()
            url_label.set_text(u)
            return u

        def _update_qr_url():
            url = _compute_url()
            qr_path = self._generate_qr_code(url, fill="#6bcfff")
            if qr_path:
                GLib.idle_add(qr_url_image.set_filename, qr_path)

        def _build_wifi_payload() -> str:
            ssid = ssid_entry.get_text().strip()
            pwd = pass_entry.get_text()
            sec_idx = wifi_type_combo.get_active()
            sec_map = {0: "WPA", 1: "WEP", 2: "nopass"}
            sec = sec_map.get(sec_idx, "WPA")
            if not ssid:
                return ""
            # Échapper les caractères spéciaux du SSID/mot de passe selon spec WIFI:
            # \, ;, ,, :, ", ' → \X
            def _esc(s: str) -> str:
                out = []
                for ch in s:
                    if ch in "\\;,:\"'":
                        out.append("\\" + ch)
                    else:
                        out.append(ch)
                return "".join(out)
            if sec == "nopass":
                return f"WIFI:T:nopass;S:{_esc(ssid)};;"
            return f"WIFI:T:{sec};S:{_esc(ssid)};P:{_esc(pwd)};H:false;;"

        def _update_qr_wifi():
            payload = _build_wifi_payload()
            if not payload:
                # QR code d'aide si pas de SSID
                qr_path = self._generate_qr_code(
                    "Renseignez le SSID WiFi puis appuyez sur 🔍 Détecter ou saisissez-le manuellement",
                    fill="#f39c12"
                )
                if qr_path:
                    GLib.idle_add(qr_wifi_image.set_filename, qr_path)
                return
            qr_path = self._generate_qr_code(payload, fill="#2ecc71")
            if qr_path:
                GLib.idle_add(qr_wifi_image.set_filename, qr_path)

        def _on_url_changed(*_):
            _update_url_display()
            threading.Thread(target=_update_qr_url, daemon=True).start()

        scheme_combo.connect("changed", _on_url_changed)
        port_entry.connect("changed", _on_url_changed)
        btn_copy_url.connect("clicked", lambda *_: self._copy_text(_compute_url()))

        def _open_in_browser(*_):
            url = _compute_url()
            try:
                Gtk.UriLauncher.new(url).launch(dialog, None, lambda *_: None)
            except Exception:
                # Fallback: xdg-open
                try:
                    subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    self._copy_text(url)
                    self._show_toast("⧉ URL copiée (lancez-la manuellement)")

        btn_open_browser.connect("clicked", _open_in_browser)

        # WiFi events
        ssid_entry.connect("changed", lambda *_: threading.Thread(target=_update_qr_wifi, daemon=True).start())
        pass_entry.connect("changed", lambda *_: threading.Thread(target=_update_qr_wifi, daemon=True).start())
        wifi_type_combo.connect("changed", lambda *_: threading.Thread(target=_update_qr_wifi, daemon=True).start())

        def _detect_wifi(*_):
            info = self._detect_wifi_info()
            if info.get("ssid"):
                ssid_entry.set_text(info["ssid"])
                if info.get("security"):
                    sec_map = {"WPA": 0, "WEP": 1, "nopass": 2}
                    sec_idx = sec_map.get(info["security"], 0)
                    wifi_type_combo.set_active(sec_idx)
                self._show_toast(f"📶 WiFi détecté: {info['ssid']}")
                # On ne peut pas récupérer le mot de passe via ces outils → l'utilisateur le saisit
            else:
                self._show_toast("⚠️ SSID non détecté — saisissez-le manuellement")

        btn_detect_wifi.connect("clicked", _detect_wifi)

        # ── INITIAL DISPLAY ───────────────────────────────────────────
        # Réseau fermé : aucune IP publique à fetch, on utilise directement
        # le résultat de `hostname -I`.
        _update_url_display()
        _update_qr_url()
        _update_qr_wifi()

        # ── BOUTON FERMER ────────────────────────────────────────────
        btn_close = Gtk.Button(label="✕ Fermer")
        btn_close.set_halign(Gtk.Align.END)
        btn_close.add_css_class("suggested-action")
        btn_close.set_margin_top(8)
        btn_close.connect("clicked", lambda *_: dialog.destroy())
        content.append(btn_close)

        dialog.present()

    def _get_local_ips(self) -> list[str]:
        """
        Récupère toutes les IPs locales via `hostname -I`.
        Retourne une liste (peut être vide si la commande échoue).
        """
        try:
            out = subprocess.check_output(["hostname", "-I"], text=True, timeout=3).strip()
            return [ip.strip() for ip in out.split() if ip.strip()]
        except Exception:
            return []

    def _get_local_ip(self) -> str:
        """Compatibilité: renvoie la première IP locale détectée par `hostname -I`."""
        ips = self._get_local_ips()
        if ips:
            return ips[0]
        # Fallback ultime
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _detect_wifi_info(self) -> dict:
        """
        Tente de détecter le SSID WiFi actif et son type de sécurité.
        Utilise nmcli (NetworkManager) puis iwgetid / iwconfig en fallback.
        Ne récupère PAS le mot de passe (impossible sans root + libnm-devel).
        """
        # 1) nmcli -t -f active,ssid,security
        try:
            out = subprocess.check_output(
                ["nmcli", "-t", "-f", "ACTIVE,SSID,SECURITY", "dev", "wifi"],
                text=True, timeout=3
            )
            for line in out.splitlines():
                parts = line.split(":")
                if len(parts) >= 3 and parts[0].strip().lower() in ("oui", "yes", "true"):
                    ssid = parts[1].strip()
                    sec = parts[2].strip().upper()
                    if not sec or sec == "--":
                        sec = "nopass"
                    elif "WEP" in sec:
                        sec = "WEP"
                    else:
                        sec = "WPA"
                    if ssid:
                        return {"ssid": ssid, "security": sec}
        except Exception:
            pass

        # 2) iwgetid -r
        try:
            ssid = subprocess.check_output(["iwgetid", "-r"], text=True, timeout=3).strip()
            if ssid:
                sec = "WPA"
                # Détection sommaire du type
                try:
                    iw_out = subprocess.check_output(["iwgetid", "-p"], text=True, timeout=3).strip().upper()
                    if "WEP" in iw_out:
                        sec = "WEP"
                    elif "802-1X" in iw_out or "ESS" in iw_out:
                        sec = "WPA"
                except Exception:
                    pass
                return {"ssid": ssid, "security": sec}
        except Exception:
            pass

        # 3) iwconfig (parse ESSID)
        try:
            out = subprocess.check_output(["iwconfig"], text=True, timeout=3, stderr=subprocess.DEVNULL)
            m = re.search(r'ESSID:"([^"]+)"', out)
            if m and m.group(1) and m.group(1) != "off/any":
                return {"ssid": m.group(1), "security": "WPA"}
        except Exception:
            pass

        return {"ssid": "", "security": ""}

    def _generate_qr_code(self, data: str, fill: str = "#6bcfff") -> str:
        """Génère un QR code et retourne le chemin du fichier PNG."""
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=8, border=2)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color=fill, back_color="#000000")
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            img.save(tmp.name)
            return tmp.name
        except ImportError:
            # Fallback: PIL + texte si qrcode n'est pas installé
            try:
                from PIL import Image, ImageDraw, ImageFont
                size = 220
                img = Image.new("RGB", (size, size), "black")
                draw = ImageDraw.Draw(img)
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
                except Exception:
                    font = ImageFont.load_default()
                # Word-wrap
                lines = []
                words = data.split()
                cur = ""
                for w in words:
                    if len(cur) + len(w) + 1 > 28:
                        lines.append(cur)
                        cur = w
                    else:
                        cur = (cur + " " + w).strip()
                if cur:
                    lines.append(cur)
                y = (size - len(lines) * 14) // 2
                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    draw.text(((size - tw) // 2, y), line, fill=fill, font=font)
                    y += th + 4
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                img.save(tmp.name)
                return tmp.name
            except Exception:
                return None
        except Exception:
            return None

    def _copy_text(self, text: str):
        Gdk.Display.get_default().get_clipboard().set(text)
        self._show_toast("⧉ Copié!")

    # ── PANEL TOGGLES ────────────────────────────────────────────────
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

    # ── PROJECT / FILE ───────────────────────────────────────────────
    def _open_project_dialog(self, *_):
        Gtk.FileDialog(title="Ouvrir un projet").select_folder(self.win, None, self._on_project_selected)

    def _on_project_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder: self._load_project(Path(folder.get_path()))
        except Exception as e:
            global_log(f"⚠️ Erreur sélection projet: {type(e).__name__} - {e}")

    def _load_project(self, path: Path):
        self.project_root = path
        self.config["last_project"] = str(path)
        add_recent_project(str(path), self.config)
        self.config = load_config()
        self.file_panel.load_project(path, self.config)
        self.win.set_title(f"Gykhamine Studio — {path.name}")
        self.status_project.set_text(f"📂 {path.name}")
        self._show_toast(f"📂 Projet: {path.name}")

    def _on_file_selected(self, path: Path):
        self.editor_view.load_file(path)
        self._update_status_bar(str(path))

    def _on_file_created(self, path: Path):
        self._show_toast(f"✅ Créé: {path.name}")
        self.editor_view.load_file(path)

    def _on_file_imported(self, path: Path):
        self._show_toast(f"📥 Importé: {path.name}")
        self.editor_view.load_file(path)

    def _run_python_file(self, path: Path):
        if not path: return
        self._show_toast(f"▶ Exécution {path.name}")
        self.terminal_panel._log(f"▶ python {path.name}")
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
                GLib.idle_add(self.terminal_panel._log, f"✅ Terminé (code {proc.returncode})")
            except Exception as e: GLib.idle_add(self.terminal_panel._log, f"❌ Erreur: {e}")
        threading.Thread(target=_thread, daemon=True).start()

    def _open_settings(self, *_):
        dlg = SettingsDialog(self.win, self.config, self._on_settings_saved); dlg.present(self.win)

    def _open_runtime_dialog(self, *_):
        def _log(msg):
            if hasattr(self, 'terminal_panel'):
                self.terminal_panel._log(msg)
        dlg = RuntimeDialog(self.win, self.runtime_manager, log_cb=_log)
        dlg.present()

    def _on_settings_saved(self, new_config):
        self.config = new_config; save_config(new_config); self._apply_theme(); self._show_toast("⚙ Sauvegardé")
        if self.project_root: self.file_panel.load_project(self.project_root, self.config)

    def _apply_theme(self):
        if self.config.get("theme", "dark") == "light": self.win.add_css_class("theme-light")
        else: self.win.remove_css_class("theme-light")

    def _show_toast(self, msg: str):
        self.toast_overlay.add_toast(Adw.Toast(title=msg, timeout=2))

if __name__ == "__main__":
    app = GykhamineStudioApp()
    sys.exit(app.run(sys.argv))
