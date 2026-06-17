"""Module généré automatiquement depuis widgets.py - Classe ControlPanel"""
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
from .django_master_doc_dialog import DjangoMasterDocDialog

#  WIDGETS
# ═══════════════════════════════════════════════════════════════════════
TYPE_ICONS = {"import": "📦", "class": "🏛", "function": "⚡", "separator": "─", "comment": "💬", "other": "▪", "template": "🌐", "template_part": "🌐", "django_block": "🧩", "style": "🎨", "style_rule": "🎨", "script": "⚙️", "script_block": "⚡", "c_block": "⚙️"}



class ControlPanel(Gtk.Box):
    def __init__(self, get_project_root, get_config, show_toast, terminal_panel):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.get_project_root, self.get_config, self.show_toast, self.terminal = get_project_root, get_config, show_toast, terminal_panel
        self.sessions, self.current_session, self.processes = {}, None, {}
        self.dev_port_label, self.gunicorn_port_label = None, None
        set_margins(self, 8); self._build()

    def _build(self):
        self.session_label = Gtk.Label(label="No project loaded"); self.session_label.add_css_class("control-section-title"); self.session_label.set_xalign(0); self.append(self.session_label)
        
        port_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6); port_box.set_margin_bottom(8)
        for label, cb in [("🔍 Check", self._check_ports), ("🔫 Kill port", self._kill_port_dialog), ("🔓 UFW Allow", self._ufw_allow_dialog), ("🌐 URLs Accessibles", self._show_open_browser_dialog)]:
            btn = Gtk.Button(label=label); btn.add_css_class("ctrl-btn-small"); btn.connect("clicked", cb); port_box.append(btn)
        self.append(port_box)
        
        lbl1 = Gtk.Label(label="🚀 Django Server"); lbl1.add_css_class("control-section-title"); lbl1.set_xalign(0); self.append(lbl1)
        self._add_service_row("runserver", "▶ Dev Server", self._start_devserver, self._stop_service_factory("runserver"))
        self.dev_port_label = Gtk.Label(label="Port: auto"); self.dev_port_label.add_css_class("ctrl-btn-small"); self.dev_port_label.set_xalign(0); self.append(self.dev_port_label)
        
        self._add_service_row("gunicorn", "▶ Gunicorn", self._start_gunicorn, self._stop_service_factory("gunicorn"))
        self.gunicorn_port_label = Gtk.Label(label="Bind: config"); self.gunicorn_port_label.add_css_class("ctrl-btn-small"); self.gunicorn_port_label.set_xalign(0); self.append(self.gunicorn_port_label)
        
        sep = Gtk.Separator(); sep.set_margin_top(8); sep.set_margin_bottom(4); self.append(sep)
        
        lbl2 = Gtk.Label(label="🗄 Django Commands (manage.py)"); lbl2.add_css_class("control-section-title"); lbl2.set_xalign(0); self.append(lbl2)
        grid = Gtk.Grid(); grid.set_column_spacing(6); grid.set_row_spacing(6)
        commands = [("📐 makemigrations", "makemigrations"), ("⬆ migrate", "migrate"), ("👤 superuser", "createsuperuser"), ("📱 New App", "startapp"), ("🐚 shell", "shell"), ("🗄 dbshell", "dbshell"), ("📦 collectstatic", "collectstatic"), ("✅ check", "check"), ("📜 showmigrations", "showmigrations"), ("🧹 flush", "flush")]
        for idx, (label, cmd) in enumerate(commands):
            btn = Gtk.Button(label=label); btn.add_css_class("ctrl-btn")
            if cmd == "createsuperuser": 
                btn.connect("clicked", lambda *_: self._show_createsuperuser_dialog())
            elif cmd == "startapp": 
                btn.connect("clicked", lambda *_: self._show_startapp_dialog())
            else: 
                btn.connect("clicked", lambda _, c=cmd: self._run_manage_command(c))
            grid.attach(btn, idx % 3, idx // 3, 1, 1)
        self.append(grid)
        
        sep_db = Gtk.Separator(); sep_db.set_margin_top(8); sep_db.set_margin_bottom(4); self.append(sep_db)
        lbl_db = Gtk.Label(label="🗄 Base de données"); lbl_db.add_css_class("control-section-title"); lbl_db.set_xalign(0); self.append(lbl_db)
        btn_db_stats = Gtk.Button(label="📊 Visualiser les Tables et Données")
        btn_db_stats.add_css_class("ctrl-btn"); btn_db_stats.set_hexpand(True); btn_db_stats.set_tooltip_text("Afficher un tableau avec les colonnes, clés et les données réelles (TOUTES les lignes)")
        btn_db_stats.connect("clicked", self._show_db_stats)
        self.append(btn_db_stats)
        
        # === NOUVEAU : Section SSL ===
        sep_ssl = Gtk.Separator(); sep_ssl.set_margin_top(8); sep_ssl.set_margin_bottom(4); self.append(sep_ssl)
        lbl_ssl = Gtk.Label(label="🔒 SSL / HTTPS (Gunicorn & Nginx)"); lbl_ssl.add_css_class("control-section-title"); lbl_ssl.set_xalign(0); self.append(lbl_ssl)
        
        row_ssl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_gen_ssl = Gtk.Button(label="🔑 Générer Certificat SSL")
        btn_gen_ssl.add_css_class("ctrl-btn")
        btn_gen_ssl.set_hexpand(True)
        btn_gen_ssl.set_tooltip_text("Génère un certificat auto-signé via OpenSSL pour Gunicorn et Nginx")
        btn_gen_ssl.connect("clicked", self._generate_ssl)
        row_ssl.append(btn_gen_ssl)
        self.append(row_ssl)
        # ============================
        
        sep_pg = Gtk.Separator(); sep_pg.set_margin_top(8); sep_pg.set_margin_bottom(4); self.append(sep_pg)
        lbl_pg = Gtk.Label(label="🐘 Gestion PostgreSQL"); lbl_pg.add_css_class("control-section-title"); lbl_pg.set_xalign(0); self.append(lbl_pg)
        pg_config_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_init = Gtk.Button(label="🔧 Init"); btn_init.add_css_class("ctrl-btn"); btn_init.set_hexpand(True); btn_init.connect("clicked", self._run_pg_initdb); pg_config_box.append(btn_init)
        btn_create = Gtk.Button(label="➕ Créer DB"); btn_create.add_css_class("ctrl-btn"); btn_create.set_hexpand(True); btn_create.connect("clicked", self._run_pg_creatdb); pg_config_box.append(btn_create)
        self.append(pg_config_box)
        self._add_custom_service_row("postgresql", "▶ Démarrer & Configurer", self._run_pg_rundb, self._run_pg_stopdb)
        
        sep_redis = Gtk.Separator(); sep_redis.set_margin_top(8); sep_redis.set_margin_bottom(4); self.append(sep_redis)
        lbl_redis = Gtk.Label(label="🔴 Gestion Redis"); lbl_redis.add_css_class("control-section-title"); lbl_redis.set_xalign(0); self.append(lbl_redis)
        self._add_custom_service_row("redis", "▶ Démarrer Redis", self._run_redis_start, self._run_redis_stop)
        
        sep_nfs_s = Gtk.Separator(); sep_nfs_s.set_margin_top(8); sep_nfs_s.set_margin_bottom(4); self.append(sep_nfs_s)
        lbl_nfs_s = Gtk.Label(label="📁 NFS Serveur"); lbl_nfs_s.add_css_class("control-section-title"); lbl_nfs_s.set_xalign(0); self.append(lbl_nfs_s)
        self._add_custom_service_row("nfs_server", "▶ Démarrer Serveur", self._run_nfs_server_start, self._run_nfs_server_stop)
        
        sep_nfs_c = Gtk.Separator(); sep_nfs_c.set_margin_top(8); sep_nfs_c.set_margin_bottom(4); self.append(sep_nfs_c)
        lbl_nfs_c = Gtk.Label(label="💻 NFS Client"); lbl_nfs_c.add_css_class("control-section-title"); lbl_nfs_c.set_xalign(0); self.append(lbl_nfs_c)
        self._add_custom_service_row("nfs_client", "📥 Monter le partage", self._run_nfs_client_mount, self._run_nfs_client_umount)
        
        sep_nginx = Gtk.Separator(); sep_nginx.set_margin_top(8); sep_nginx.set_margin_bottom(4); self.append(sep_nginx)
        lbl_nginx = Gtk.Label(label="🌐 Gestion Nginx"); lbl_nginx.add_css_class("control-section-title"); lbl_nginx.set_xalign(0); self.append(lbl_nginx)
        nginx_ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_nginx_config = Gtk.Button(label="⚙ Configurer"); btn_nginx_config.add_css_class("ctrl-btn"); btn_nginx_config.set_hexpand(True); btn_nginx_config.connect("clicked", self._show_nginx_config_dialog)
        btn_nginx_restart = Gtk.Button(label="🔄 Redémarrer"); btn_nginx_restart.add_css_class("ctrl-btn-warn"); btn_nginx_restart.set_hexpand(True); btn_nginx_restart.connect("clicked", self._run_nginx_restart)
        nginx_ctrl_box.append(btn_nginx_config); nginx_ctrl_box.append(btn_nginx_restart)
        self.append(nginx_ctrl_box)
        self._add_custom_service_row("nginx", "▶ Démarrer Nginx", self._run_nginx_start, self._run_nginx_stop)
        
        sep_ssh = Gtk.Separator(); sep_ssh.set_margin_top(8); sep_ssh.set_margin_bottom(4); self.append(sep_ssh)
        lbl_ssh = Gtk.Label(label="🔐 Gestion SSH (TTY Native)"); lbl_ssh.add_css_class("control-section-title"); lbl_ssh.set_xalign(0); self.append(lbl_ssh)
        ssh_ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_ssh_config = Gtk.Button(label="⚙ Config"); btn_ssh_config.add_css_class("ctrl-btn"); btn_ssh_config.set_hexpand(True); btn_ssh_config.connect("clicked", self._show_ssh_config_dialog)
        btn_ssh_server = Gtk.Button(label="▶ Start Server"); btn_ssh_server.add_css_class("ctrl-btn-start"); btn_ssh_server.set_hexpand(True); btn_ssh_server.connect("clicked", self._run_ssh_server_start)
        ssh_ctrl_box.append(btn_ssh_config); ssh_ctrl_box.append(btn_ssh_server)
        self.append(ssh_ctrl_box)
        self._add_custom_service_row("ssh_client", "🔗 Connect Client (TTY)", self._run_ssh_client_connect, self._run_ssh_client_disconnect_dummy)
        
        sep_venv = Gtk.Separator(); sep_venv.set_margin_top(8); sep_venv.set_margin_bottom(4); self.append(sep_venv)
        lbl_venv = Gtk.Label(label="🐍 Environnements Virtuels"); lbl_venv.add_css_class("control-section-title"); lbl_venv.set_xalign(0); self.append(lbl_venv)
        venv_ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_venv_create = Gtk.Button(label="➕ Create"); btn_venv_create.add_css_class("ctrl-btn"); btn_venv_create.set_hexpand(True); btn_venv_create.connect("clicked", self._run_venv_create)
        btn_venv_install = Gtk.Button(label="📦 Install Pkg"); btn_venv_install.add_css_class("ctrl-btn"); btn_venv_install.set_hexpand(True); btn_venv_install.connect("clicked", self._show_venv_install_dialog)
        btn_venv_del = Gtk.Button(label="🗑 Delete"); btn_venv_del.add_css_class("ctrl-btn-stop"); btn_venv_del.set_hexpand(True); btn_venv_del.connect("clicked", self._run_venv_delete)
        venv_ctrl_box.append(btn_venv_create); venv_ctrl_box.append(btn_venv_install); venv_ctrl_box.append(btn_venv_del)
        self.append(venv_ctrl_box)
        self._add_custom_service_row("venv_activate", "⚡ Activate Shell (TTY)", self._run_venv_activate, self._run_venv_deactivate_dummy)
        
        sep_tools = Gtk.Separator(); sep_tools.set_margin_top(8); sep_tools.set_margin_bottom(4); self.append(sep_tools)
        lbl_tools = Gtk.Label(label="🛠️ Outils DevOps & IA"); lbl_tools.add_css_class("control-section-title"); lbl_tools.set_xalign(0); self.append(lbl_tools)
        tools_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        tools_box.set_hexpand(True)
        btn_git = Gtk.Button(label="🐙 Mini GitHub Desktop")
        btn_git.add_css_class("ctrl-btn")
        btn_git.set_hexpand(True)
        btn_git.set_tooltip_text("Cloner, Commiter et Pusher sans quitter l'interface")
        btn_git.connect("clicked", self._open_git_manager)
        tools_box.append(btn_git)
        btn_process = Gtk.Button(label="🧠 Élaborateur Processus Métier")
        btn_process.add_css_class("ctrl-btn-warn")
        btn_process.set_hexpand(True)
        btn_process.set_tooltip_text("Générer un plan d'action Django structuré en JSON")
        btn_process.connect("clicked", self._open_business_process)
        tools_box.append(btn_process)

        # NOUVEAU: Bouton Gestion Système & Réseau
        btn_sys = Gtk.Button(label="🛡️ Gestion Système & Réseau")
        btn_sys.add_css_class("ctrl-btn")
        btn_sys.set_hexpand(True)
        btn_sys.set_tooltip_text("Firewall, IP Statique/DHCP, Services Systemd")
        btn_sys.connect("clicked", self._show_system_manager_dialog)
        tools_box.append(btn_sys)

        self.append(tools_box)
        
        sep3 = Gtk.Separator(); sep3.set_margin_top(8); sep3.set_margin_bottom(4); self.append(sep3)
        lbl4 = Gtk.Label(label="💊 Gykhamine Capsule"); lbl4.add_css_class("control-section-title"); lbl4.set_xalign(0); self.append(lbl4)
        row_cap = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        for label, path, sudo in [("🔑 /1/gy.py", "Gykhamine/1/gy.py", True), ("👤 /2/gy.py", "Gykhamine/2/gy.py", False)]:
            btn = Gtk.Button(label=f"Run {label}"); btn.add_css_class("ctrl-btn-warn" if sudo else "ctrl-btn"); btn.connect("clicked", lambda *_: self._run_gy(path, sudo)); row_cap.append(btn)
        self.append(row_cap)
        
        sep4 = Gtk.Separator(); sep4.set_margin_top(8); sep4.set_margin_bottom(4); self.append(sep4)
        lbl_arch = Gtk.Label(label="📦 ZIP Archiving"); lbl_arch.add_css_class("control-section-title"); lbl_arch.set_xalign(0); self.append(lbl_arch)
        row_arch = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_compress = Gtk.Button(label="🗜 Compress to .zip"); btn_compress.add_css_class("ctrl-btn"); btn_compress.connect("clicked", self._compress_project)
        btn_decompress = Gtk.Button(label="📂 Decompress .zip"); btn_decompress.add_css_class("ctrl-btn"); btn_decompress.connect("clicked", self._decompress_archive)
        row_arch.append(btn_compress); row_arch.append(btn_decompress); self.append(row_arch)
        
        sep5 = Gtk.Separator(); sep5.set_margin_top(8); sep5.set_margin_bottom(4); self.append(sep5)
        lbl_ai = Gtk.Label(label="🤖 AI (llama.cpp)"); lbl_ai.add_css_class("control-section-title"); lbl_ai.set_xalign(0); self.append(lbl_ai)
        llama_status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, margin_bottom=6)
        self.llama_lamp = Gtk.Label(label="🔴")
        self.llama_lamp.set_tooltip_text("Llama Server : Arrêté")
        self.llama_status_text = Gtk.Label(label="Arrêté", css_classes=["dim-label"])
        llama_status_box.append(self.llama_lamp)
        llama_status_box.append(self.llama_status_text)
        self.append(llama_status_box)
        llama_ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.btn_setup_llama = Gtk.Button(label="⚙️ Configurer & Lancer")
        self.btn_setup_llama.add_css_class("ctrl-btn-warn")
        self.btn_setup_llama.connect("clicked", self._open_llama_setup)
        llama_ctrl_box.append(self.btn_setup_llama)
        self.btn_stop_llama = Gtk.Button(label="⏹ Arrêter")
        self.btn_stop_llama.add_css_class("ctrl-btn-stop")
        self.btn_stop_llama.set_sensitive(False)
        self.btn_stop_llama.connect("clicked", self._stop_llama)
        llama_ctrl_box.append(self.btn_stop_llama)
        self.append(llama_ctrl_box)
        
        sep6 = Gtk.Separator(); sep6.set_margin_top(8); sep6.set_margin_bottom(4); self.append(sep6)
        btn_stop_all = Gtk.Button(label="⏹ Stop all"); btn_stop_all.add_css_class("ctrl-btn-stop"); btn_stop_all.connect("clicked", self._stop_all_services); self.append(btn_stop_all)
        # ... code existant ...
        
        # NOUVEAU BOUTON DOCUMENTATION MASTER
        btn_doc = Gtk.Button(label="📚 Documentation Master Django")
        btn_doc.add_css_class("ctrl-btn")
        btn_doc.set_hexpand(True)
        btn_doc.set_tooltip_text("Accéder à la documentation exhaustive avec recherche")
        btn_doc.connect("clicked", lambda *_: DjangoMasterDocDialog(self.get_root()).present())
        tools_box.append(btn_doc)
        
        # ... suite du code existant ...

    def _add_service_row(self, name, label, start_cb, stop_cb):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._status_dots = getattr(self, "_status_dots", {})
        dot = Gtk.Label(label="⬤"); dot.add_css_class("status-dot-off"); self._status_dots[name] = dot
        btn_start = Gtk.Button(label=label)
        btn_start.add_css_class("ctrl-btn-start")
        btn_start.set_hexpand(True)
        btn_start.connect("clicked", start_cb)
        btn_stop = Gtk.Button(label="⏹")
        btn_stop.add_css_class("ctrl-btn-stop")
        btn_stop.connect("clicked", lambda *_: stop_cb())
        row.append(dot); row.append(btn_start); row.append(btn_stop); self.append(row)

    def _add_custom_service_row(self, name, label, start_cb, stop_cb):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._status_dots = getattr(self, "_status_dots", {})
        dot = Gtk.Label(label="⬤"); dot.add_css_class("status-dot-off"); self._status_dots[name] = dot
        btn_start = Gtk.Button(label=label)
        btn_start.add_css_class("ctrl-btn-start")
        btn_start.set_hexpand(True)
        btn_start.connect("clicked", start_cb)
        btn_stop = Gtk.Button(label="⏹ Arrêter")
        btn_stop.add_css_class("ctrl-btn-stop")
        btn_stop.set_hexpand(True)
        btn_stop.connect("clicked", lambda *_: stop_cb())
        row.append(dot); row.append(btn_start); row.append(btn_stop); self.append(row)

    def _set_dot(self, name, running: bool):
        dot = self._status_dots.get(name)
        if dot:
            dot.remove_css_class("status-dot-on" if not running else "status-dot-off")
            dot.add_css_class("status-dot-off" if not running else "status-dot-on")

    def _update_llama_status(self, is_running):
        if is_running:
            self.llama_lamp.set_text("🟢")
            self.llama_lamp.set_tooltip_text("Llama Server : En cours d'exécution")
            self.llama_status_text.set_text("En cours d'exécution")
            self.llama_status_text.remove_css_class("dim-label")
            self.btn_stop_llama.set_sensitive(True)
            self.btn_setup_llama.set_label("⚙️ Reconfigurer")
        else:
            self.llama_lamp.set_text("🔴")
            self.llama_lamp.set_tooltip_text("Llama Server : Arrêté")
            self.llama_status_text.set_text("Arrêté")
            self.llama_status_text.add_css_class("dim-label")
            self.btn_stop_llama.set_sensitive(False)
            self.btn_setup_llama.set_label("⚙️ Configurer & Lancer")

    def _stop_llama(self, *_):
        proc = self.processes.get("llama")
        if proc:
            proc.terminate()
            self.terminal._log("⏹ Llama-server arrêté (terminate).")
            self.processes.pop("llama", None)
        else:
            self.terminal._log("⚠ Llama-server non trouvé dans les processus, tentative de kill global...")
            subprocess.run(["pkill", "-f", "llama-server"], capture_output=True)
        self._update_llama_status(False)
        self.show_toast("✅ Llama-server arrêté")

    def _get_or_create_session(self):
        root = self.get_project_root()
        if not root: return None
        if str(root) not in self.sessions: self.sessions[str(root)] = type('ProjectSession', (), {'project_root': root, 'dev_port': None, 'gunicorn_port': None})()
        self.current_session = self.sessions[str(root)]; self.session_label.set_text(f"📁 Session: {root.name}")
        return self.current_session

    def _run_cmd(self, cmd: list, cwd=None, name=None, shell=False, extra_env=None):
        def _thread():
            try:
                env = os.environ.copy(); env["PYTHONUNBUFFERED"] = "1"; env["PYTHONDONTWRITEBYTECODE"] = "1"; env["DJANGO_COLORS"] = "nocolor"
                if extra_env: env.update(extra_env)
                proc = subprocess.Popen(cmd, cwd=cwd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, text=True, bufsize=0, env=env)
                if name: self.processes[name] = proc
                GLib.idle_add(self._set_dot, name, True)
                if name == "llama": GLib.idle_add(self._update_llama_status, True)
                if not shell: GLib.idle_add(self.terminal._log, f"▶ {' '.join(str(c) for c in cmd)}")
                def _read_stream(stream, prefix=""):
                    for line in iter(stream.readline, ''):
                        if line: GLib.idle_add(self.terminal._log, prefix + line.rstrip())
                    stream.close()
                t_out = threading.Thread(target=_read_stream, args=(proc.stdout,), daemon=True)
                t_err = threading.Thread(target=_read_stream, args=(proc.stderr, ""), daemon=True)
                t_out.start(); t_err.start(); t_out.join(); t_err.join(); proc.wait()
                if name: self.processes.pop(name, None)
                GLib.idle_add(self._set_dot, name, False)
                if name == "llama": GLib.idle_add(self._update_llama_status, False)
                GLib.idle_add(self.terminal._log, f"✓ Finished (code {proc.returncode})")
            except Exception as e:
                GLib.idle_add(self.terminal._log, f"❌ Error: {e}")
                if name: GLib.idle_add(self._set_dot, name, False)
                if name == "llama": GLib.idle_add(self._update_llama_status, False)
        threading.Thread(target=_thread, daemon=True).start()

    def _manage_path(self):
        root = self.get_project_root()
        if not root: return None
        mp = root / "manage.py"
        return mp if mp.exists() else (list(root.rglob("manage.py"))[0] if list(root.rglob("manage.py")) else None)

    def _run_manage_command(self, command):
        if command in ("shell", "dbshell"): return self._run_interactive_command(command)
        mp = self._manage_path()
        if not mp: return
        self.terminal._log(f"▶ python {mp.name} {command}")
        self._run_cmd([sys.executable, str(mp), command], cwd=str(mp.parent))

    def _run_interactive_command(self, command):
        mp = self._manage_path()
        if not mp: return
        full_cmd = f"{sys.executable} {mp.name} {command}"
        self.terminal._log(f"🖥 Ouverture TTY pour: {full_cmd}")
        NativeTtyTerminal(self.get_root(), f"Django: {command}", full_cmd, cwd=str(mp.parent))

    def _show_createsuperuser_dialog(self, *_):
        dialog = Gtk.Dialog(title="Créer un Superutilisateur Django", transient_for=self.get_root()); dialog.add_css_class("rounded-dialog"); dialog.set_default_size(400, 300)
        content = dialog.get_content_area(); content.set_spacing(12); set_margins(content, 16)
        grid = Gtk.Grid(); grid.set_row_spacing(8); grid.set_column_spacing(8)
        grid.attach(Gtk.Label(label="Nom d'utilisateur :", xalign=0), 0, 0, 1, 1)
        entry_user = Gtk.Entry(); entry_user.set_placeholder_text("admin"); grid.attach(entry_user, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="Adresse e-mail :", xalign=0), 0, 1, 1, 1)
        entry_email = Gtk.Entry(); entry_email.set_placeholder_text("admin@example.com"); grid.attach(entry_email, 1, 1, 1, 1)
        grid.attach(Gtk.Label(label="Mot de passe :", xalign=0), 0, 2, 1, 1)
        entry_pwd = Gtk.Entry(); entry_pwd.set_visibility(False); grid.attach(entry_pwd, 1, 2, 1, 1)
        grid.attach(Gtk.Label(label="Confirmer le mot de passe :", xalign=0), 0, 3, 1, 1)
        entry_pwd_confirm = Gtk.Entry(); entry_pwd_confirm.set_visibility(False); grid.attach(entry_pwd_confirm, 1, 3, 1, 1)
        content.append(grid)
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6); btn_box.set_halign(Gtk.Align.END)
        btn_cancel = Gtk.Button(label="Annuler"); btn_create = Gtk.Button(label="✅ Créer", css_classes=["suggested-action"])
        btn_box.append(btn_cancel); btn_box.append(btn_create); content.append(btn_box)
        def on_create(*_):
            username = entry_user.get_text().strip(); email = entry_email.get_text().strip(); pwd = entry_pwd.get_text(); pwd_confirm = entry_pwd_confirm.get_text()
            if not username or not pwd: self.show_toast("❌ Le nom d'utilisateur et le mot de passe sont requis"); return
            if pwd != pwd_confirm: self.show_toast("❌ Les mots de passe ne correspondent pas"); return
            mp = self._manage_path()
            if not mp: return
            self.terminal._log(f"▶ Création du superutilisateur: {username}")
            extra_env = {"DJANGO_SUPERUSER_USERNAME": username, "DJANGO_SUPERUSER_EMAIL": email, "DJANGO_SUPERUSER_PASSWORD": pwd}
            self._run_cmd([sys.executable, str(mp), "createsuperuser", "--noinput"], cwd=str(mp.parent), extra_env=extra_env)
            dialog.destroy()
        btn_create.connect("clicked", on_create); btn_cancel.connect("clicked", lambda *_: dialog.destroy()); dialog.present()

    def _show_startapp_dialog(self, *_):
        """Ouvre un dialogue pour créer une nouvelle app Django"""
        dialog = Gtk.Dialog(title="Créer une nouvelle App Django", transient_for=self.get_root())
        dialog.add_css_class("rounded-dialog")
        dialog.set_default_size(400, 200)
        
        content = dialog.get_content_area()
        content.set_spacing(12)
        set_margins(content, 16)
        
        # Information
        info_lbl = Gtk.Label(label="Entrez le nom de l'application (ex: blog, accounts)", xalign=0, margin_bottom=8)
        info_lbl.add_css_class("dim-label")
        content.append(info_lbl)
        
        # Champ de saisie
        entry_name = Gtk.Entry()
        entry_name.set_placeholder_text("nom_de_l_app")
        entry_name.set_activates_default(True)
        content.append(entry_name)
        
        # Boutons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.END, margin_top=12)
        btn_cancel = Gtk.Button(label="Annuler")
        btn_create = Gtk.Button(label="✅ Créer", css_classes=["suggested-action"])
        btn_box.append(btn_cancel)
        btn_box.append(btn_create)
        content.append(btn_box)
        
        def on_create(*_):
            app_name = entry_name.get_text().strip()
            if not app_name:
                self.show_toast("❌ Le nom de l'app est requis")
                return
            
            # Vérification basique du format
            if not re.match(r'^[a-zA-Z_]\w*$', app_name):
                self.show_toast("❌ Nom invalide (lettres, chiffres, underscores uniquement)")
                return
                
            self._run_startapp(app_name)
            dialog.destroy()
            
        btn_create.connect("clicked", on_create)
        btn_cancel.connect("clicked", lambda *_: dialog.destroy())
        entry_name.connect("activate", on_create)
        
        dialog.present()

    def _run_startapp(self, app_name):
        """Exécute la commande startapp"""
        mp = self._manage_path()
        if not mp:
            self.show_toast("❌ Projet Django non détecté (manage.py introuvable)")
            return
            
        self.terminal._log(f"▶ Création de l'app : {app_name}")
        # Exécution de la commande
        self._run_cmd([sys.executable, str(mp), "startapp", app_name], cwd=str(mp.parent))
        
        # Rafraîchissement de l'explorateur de fichiers après un court délai
        def refresh_explorer():
            if self.get_project_root():
                self.file_panel.load_project(self.get_project_root(), self.get_config())
                self.show_toast(f"✅ App '{app_name}' créée")
        
        GLib.timeout_add_seconds(2, refresh_explorer)


    def _get_free_port(self, preferred_port=None):
        cfg = self.get_config()
        if cfg.get("auto_find_free_port", True):
            port = find_free_port(cfg.get("default_port_range_start", 8000), cfg.get("default_port_range_end", 8010))
            if port: return port
        return preferred_port if preferred_port and not is_port_in_use(preferred_port) else None

    def _start_devserver(self, *_):
        session = self._get_or_create_session()
        if not session: return
        mp = self._manage_path()
        if not mp: return
        free_port = self._get_free_port(session.dev_port or 8000)
        if not free_port: return self.terminal._log("❌ No free port")
        session.dev_port = free_port; self.dev_port_label.set_text(f"Port: {free_port}")
        self.terminal._log(f"▶ Dev server on port {free_port}")
        self._run_cmd([sys.executable, str(mp), "runserver", f"0.0.0.0:{free_port}"], cwd=str(mp.parent), name="runserver")

    def _start_gunicorn(self, *_):
        session = self._get_or_create_session()
        if not session: return
        mp = self._manage_path()
        if not mp: return
        
        cfg = self.get_config()
        bind_addr = cfg.get("gunicorn_bind", "")
        
        if not bind_addr or bind_addr == "0.0.0.0:8000":
            preferred = 8443 if cfg.get("gunicorn_ssl_enabled", False) else 8001
            free_port = self._get_free_port(session.gunicorn_port or preferred)
            if not free_port: return self.terminal._log("❌ No free port")
            bind_addr = f"0.0.0.0:{free_port}"
            session.gunicorn_port = free_port
            self.gunicorn_port_label.set_text(f"Port: {free_port}")
        else:
            self.gunicorn_port_label.set_text(f"Bind: {bind_addr}")

        if ":80" in bind_addr or ":443" in bind_addr:
            self.terminal._log("⚠ Warning: Ports 80/443 often require root (sudo) privileges.")

        wsgi = ".".join(f.relative_to(mp.parent).parts[:-1]) + ".wsgi" if (f := next(mp.parent.rglob("wsgi.py"), None)) else "wsgi"
        
        # Construction de la commande de base
        cmd = ["gunicorn", "--bind", bind_addr, "--workers", "2", wsgi]

        # === NOUVEAU : Ajout des paramètres SSL si activé ===
        if cfg.get("gunicorn_ssl_enabled", False):
            cert_path = cfg.get("gunicorn_ssl_cert_path", "")
            key_path = cfg.get("gunicorn_ssl_key_path", "")
            if Path(cert_path).exists() and Path(key_path).exists():
                cmd.extend(["--certfile", cert_path, "--keyfile", key_path])
                self.terminal._log(f"🔒 SSL activé (Cert: {cert_path}, Key: {key_path})")
            else:
                self.terminal._log("❌ SSL activé dans la config, mais les fichiers de certificat/clé sont introuvables. Démarrage annulé.")
                self.show_toast("❌ Fichiers SSL introuvables")
                return
        # ================================================

        self.terminal._log(f"▶ Gunicorn → {bind_addr} ({wsgi})")
        self._run_cmd(cmd, cwd=str(mp.parent), name="gunicorn")

    def _stop_service_factory(self, name):
        def _stop(*_):
            proc = self.processes.get(name)
            if proc: proc.terminate(); self.terminal._log(f"⏹ {name} stopped.")
            else: self.terminal._log(f"⚠ {name} is not running.")
        return _stop

    def _stop_all_services(self, *_):
        for name in list(self.processes.keys()):
            if self.processes.get(name): self.processes[name].terminate(); self.terminal._log(f"⏹ {name} stopped.")
        self.processes.clear()
        for name in self._status_dots: self._set_dot(name, False)

    def _check_ports(self, *_):
        cfg = self.get_config(); start, end = cfg.get("default_port_range_start", 8000), cfg.get("default_port_range_end", 8010)
        free, busy = [p for p in range(start, end + 1) if not is_port_in_use(p)], [p for p in range(start, end + 1) if is_port_in_use(p)]
        self.terminal._log(f"🔍 Ports {start}-{end} | ✅ Free: {free[:5]}{'...' if len(free)>5 else ''} | 🔴 Busy: {busy}")
        if busy: self.show_toast(f"⚠ {len(busy)} port(s) busy")

    def _kill_port_dialog(self, *_):
        dialog = Gtk.Dialog(title="Kill a process", transient_for=self.get_root()); dialog.add_css_class("rounded-dialog"); dialog.set_default_size(300, 150)
        content = dialog.get_content_area(); set_margins(content, 12); content.append(Gtk.Label(label="Port number:", margin_bottom=6))
        entry = Gtk.Entry(); entry.set_placeholder_text("e.g., 8000"); content.append(entry)
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_cancel = Gtk.Button(label="Cancel"); btn_kill = Gtk.Button(label="🔫 Kill"); btn_kill.add_css_class("destructive-action")
        btn_box.append(btn_cancel); btn_box.append(btn_kill); content.append(btn_box)
        def on_kill(*_):
            try:
                if kill_process_on_port(int(entry.get_text())): self.terminal._log("🔫 Process killed"); self.show_toast("Port freed")
                else: self.terminal._log("⚠ No process found")
            except ValueError: self.terminal._log("❌ Invalid port")
            dialog.destroy()
        btn_kill.connect("clicked", on_kill); btn_cancel.connect("clicked", lambda *_: dialog.destroy()); dialog.present()

    def _ufw_allow_dialog(self, *_):
        dialog = Gtk.Dialog(title="Ouvrir un port (UFW)", transient_for=self.get_root()); dialog.add_css_class("rounded-dialog"); dialog.set_default_size(320, 160)
        content = dialog.get_content_area(); set_margins(content, 12)
        content.append(Gtk.Label(label="Numéro de port à ouvrir (TCP) :", xalign=0, margin_bottom=6))
        entry = Gtk.Entry(); entry.set_placeholder_text("ex: 8000"); content.append(entry)
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_cancel = Gtk.Button(label="Annuler"); btn_open = Gtk.Button(label="🔓 Ouvrir"); btn_open.add_css_class("suggested-action")
        btn_box.append(btn_cancel); btn_box.append(btn_open); content.append(btn_box)
        def on_open(*_):
            try:
                port = int(entry.get_text().strip())
                self.terminal._log(f"🔓 Demande d'ouverture du port {port}/tcp via UFW...")
                proc = subprocess.run(["ufw", "allow", f"{port}/tcp"], capture_output=True, text=True)
                if proc.returncode == 0: self.terminal._log(f"✅ Port {port}/tcp ouvert avec succès."); self.show_toast(f"✅ Port {port} ouvert")
                else: self.terminal._log(f"❌ Erreur UFW: {proc.stderr.strip() or proc.stdout.strip() or 'Erreur inconnue'}"); self.show_toast("❌ Échec de l'ouverture du port")
            except ValueError: self.terminal._log("❌ Port invalide (doit être un nombre entier)")
            dialog.destroy()
        btn_open.connect("clicked", on_open); btn_cancel.connect("clicked", lambda *_: dialog.destroy()); dialog.present()

    def _show_open_browser_dialog(self, *_):
        urls = []
        session = self.current_session
        if session and getattr(session, 'dev_port', None):
            urls.append(("Django Dev Server", f"http://127.0.0.1:{session.dev_port}"))
        if session and getattr(session, 'gunicorn_port', None):
            urls.append(("Gunicorn", f"http://127.0.0.1:{session.gunicorn_port}"))
        cfg = self.get_config()
        if self.processes.get("llama"):
            urls.append(("Llama.cpp", f"http://{cfg.get('llama_host', '127.0.0.1')}:{cfg.get('llama_port', '8080')}"))
        
        if not urls:
            self.show_toast("❌ Aucun serveur actif à copier")
            return
            
        dialog = Gtk.Dialog(title="🌐 URLs Accessibles", transient_for=self.get_root())
        dialog.add_css_class("rounded-dialog")
        dialog.set_default_size(450, 250)
        content = dialog.get_content_area()
        content.set_spacing(12)
        set_margins(content, 16)
        content.append(Gtk.Label(label="Serveurs actifs détectés (Cliquez pour copier) :", xalign=0, css_classes=["heading"], margin_bottom=8))
        
        for name, url in urls:
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, margin_bottom=4)
            lbl = Gtk.Label(label=f"{name} : {url}", xalign=0, hexpand=True)
            lbl.add_css_class("monospace")
            box.append(lbl)
            btn = Gtk.Button(label="📋 Copier")
            btn.add_css_class("suggested-action")
            btn.connect("clicked", lambda _, u=url: self._copy_to_clipboard(u))
            box.append(btn)
            content.append(box)
            
        btn_close = Gtk.Button(label="Fermer", margin_top=12)
        btn_close.connect("clicked", lambda *_: dialog.destroy())
        content.append(btn_close)
        dialog.present()

    def _copy_to_clipboard(self, text):
        Gdk.Display.get_default().get_clipboard().set(text)
        self.show_toast("✅ URL copiée dans le presse-papiers")

    def _open_llama_setup(self, *_):
        dialog = LlamaSetupDialog(self.get_root(), self.get_config(), self._start_llama_sudo)
        dialog.present()

    def _start_llama_sudo(self, server_path, model_path, port):
        host = self.get_config().get("llama_host", "127.0.0.1")
        self.terminal._log(f"🤖 Lancement sudo llama-server → {host}:{port}")
        self.terminal._log(f"📁 Modèle: {model_path}")
        cmd = ["sudo", server_path, "-m", model_path, "--host", host, "--port", port]
        binary_dir = os.path.dirname(os.path.abspath(server_path))
        self._run_cmd(cmd, name="llama", cwd=binary_dir)

    def _open_git_manager(self, *_):
        dialog = GitManagerDialog(self.get_root(), self.get_project_root(), self.terminal._log)
        dialog.present()

# Dans la classe ControlPanel, remplacez la méthode _open_business_process par :

    def _open_business_process(self, *_):
        dialog = BusinessProcessDialog(self.get_root(), self.terminal.ai_engine, self.terminal._log, config_getter=self.get_config)
        dialog.present()    # ═══════════════════════════════════════════════════════════════════════
    #  GESTION SYSTÈME AVANCÉE (Firewall, Réseau, Systemd LiveOS)
    # ═══════════════════════════════════════════════════════════════════════


    def _show_system_manager_dialog(self, *_):
        """Ouvre le panneau de gestion système complet avec les anciens ET nouveaux onglets"""
        dialog = Gtk.Dialog(title="🛡️ Gestion Système & Réseau Avancée", transient_for=self.get_root())
        dialog.add_css_class("rounded-dialog")
        dialog.set_default_size(1200, 850) # Fenêtre plus grande pour tout voir
        
        content = dialog.get_content_area()
        content.set_spacing(0)
        set_margins(content, 0)
        
        # Notebook Principal
        notebook = Gtk.Notebook()
        notebook.set_vexpand(True)
        notebook.set_hexpand(True)
        
        # --- ONGLETS EXISTANTS (Conservés) ---
        notebook.append_page(self._build_firewall_page(), Gtk.Label(label="🔥 Firewall"))
        notebook.append_page(self._build_network_page(), Gtk.Label(label="🌐 Réseau"))
        notebook.append_page(self._build_systemd_page(), Gtk.Label(label="⚙️ Services"))
        
        # --- NOUVEAUX ONGLETS (Ajoutés) ---
        notebook.append_page(self._build_process_page(), Gtk.Label(label="⚡ Processus"))
        notebook.append_page(self._build_dns_page(), Gtk.Label(label="📡 DNS"))
        notebook.append_page(self._build_tor_page(), Gtk.Label(label="🧅 TOR"))
        notebook.append_page(self._build_dnf_page(), Gtk.Label(label="📦 DNF"))
        notebook.append_page(self._build_pip_page(), Gtk.Label(label="🐍 PIP"))
        
        content.append(notebook)
        
        btn_close = Gtk.Button(label="Fermer", margin_top=12, margin_end=12)
        btn_close.set_halign(Gtk.Align.END)
        btn_close.connect("clicked", lambda *_: dialog.destroy())
        content.append(btn_close)
        
        dialog.present()

    def _build_firewall_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        set_margins(box, 10)
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.lbl_ufw_status = Gtk.Label(label="Status: Inconnu", css_classes=["heading"])
        btn_refresh_fw = Gtk.Button(label="🔄 Actualiser")
        btn_refresh_fw.connect("clicked", lambda *_: self._refresh_ufw_status())
        status_box.append(self.lbl_ufw_status)
        status_box.append(btn_refresh_fw)
        box.append(status_box)
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_enable = Gtk.Button(label="✅ Activer UFW", css_classes=["suggested-action"])
        btn_enable.connect("clicked", lambda *_: self._run_ufw_command("enable"))
        btn_disable = Gtk.Button(label="❌ Désactiver UFW", css_classes=["destructive-action"])
        btn_disable.connect("clicked", lambda *_: self._run_ufw_command("disable"))
        action_box.append(btn_enable)
        action_box.append(btn_disable)
        box.append(action_box)
        rule_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        entry_port = Gtk.Entry()
        entry_port.set_placeholder_text("Port (ex: 80, 443, 8000:8010)")
        entry_port.set_hexpand(True)
        combo_proto = Gtk.ComboBoxText()
        combo_proto.append_text("tcp")
        combo_proto.append_text("udp")
        combo_proto.append_text("any")
        combo_proto.set_active(0)
        btn_allow = Gtk.Button(label="➕ Autoriser")
        btn_allow.connect("clicked", lambda *_: self._ufw_allow_port(entry_port.get_text(), combo_proto.get_active_text()))
        btn_deny = Gtk.Button(label="🚫 Interdire")
        btn_deny.connect("clicked", lambda *_: self._ufw_deny_port(entry_port.get_text(), combo_proto.get_active_text()))
        rule_box.append(entry_port)
        rule_box.append(combo_proto)
        rule_box.append(btn_allow)
        rule_box.append(btn_deny)
        box.append(rule_box)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        self.txt_fw_rules = Gtk.TextView()
        self.txt_fw_rules.set_editable(False)
        self.txt_fw_rules.set_monospace(True)
        self.txt_fw_rules.add_css_class("log-view")
        scroll.set_child(self.txt_fw_rules)
        box.append(scroll)
        import threading, subprocess, gi
        gi.require_version("GLib", "2.0")
        from gi.repository import GLib
        GLib.idle_add(self._refresh_ufw_status)
        return box

    def _refresh_ufw_status(self):
        def _thread():
            try:
                import subprocess, gi
                gi.require_version("GLib", "2.0")
                from gi.repository import GLib
                proc = subprocess.run(["sudo", "ufw", "status", "verbose"], capture_output=True, text=True)
                output = proc.stdout.strip()
                GLib.idle_add(lambda: self.txt_fw_rules.get_buffer().set_text(output))
                if "Status: active" in output:
                    GLib.idle_add(lambda: self.lbl_ufw_status.set_text("Status: 🟢 Actif"))
                    GLib.idle_add(lambda: self.lbl_ufw_status.remove_css_class("dim-label"))
                else:
                    GLib.idle_add(lambda: self.lbl_ufw_status.set_text("Status: 🔴 Inactif"))
                    GLib.idle_add(lambda: self.lbl_ufw_status.add_css_class("dim-label"))
            except Exception as e:
                import gi
                gi.require_version("GLib", "2.0")
                from gi.repository import GLib
                GLib.idle_add(lambda: self.txt_fw_rules.get_buffer().set_text(f"Erreur: {e}"))
        import threading
        threading.Thread(target=_thread, daemon=True).start()

    def _run_ufw_command(self, cmd):
        self.terminal._log(f"▶ sudo ufw {cmd}")
        def _thread():
            try:
                import subprocess, gi
                gi.require_version("GLib", "2.0")
                from gi.repository import GLib
                proc = subprocess.run(f"yes | sudo ufw {cmd}", shell=True, capture_output=True, text=True)
                GLib.idle_add(lambda: self.terminal._log(proc.stdout + proc.stderr))
                GLib.idle_add(self._refresh_ufw_status)
                GLib.idle_add(lambda: self.show_toast(f"✅ UFW {cmd} effectué"))
            except Exception as e:
                import gi
                gi.require_version("GLib", "2.0")
                from gi.repository import GLib
                GLib.idle_add(lambda: self.terminal._log(f"❌ Erreur: {e}"))
        import threading
        threading.Thread(target=_thread, daemon=True).start()

    def _ufw_allow_port(self, port, proto):
        if not port: return self.show_toast("❌ Port requis")
        cmd = f"allow {port}/{proto}" if proto != "any" else f"allow {port}"
        self._run_ufw_command(cmd)

    def _ufw_deny_port(self, port, proto):
        if not port: return self.show_toast("❌ Port requis")
        cmd = f"deny {port}/{proto}" if proto != "any" else f"deny {port}"
        self._run_ufw_command(cmd)

    def _build_network_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        set_margins(box, 10)
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.lbl_interface = Gtk.Label(label="Interface: Détection...", xalign=0, css_classes=["heading"])
        self.lbl_current_ip = Gtk.Label(label="IP Actuelle: ...", xalign=0)
        info_box.append(self.lbl_interface)
        info_box.append(self.lbl_current_ip)
        box.append(info_box)
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        row = 0
        grid.attach(Gtk.Label(label="Mode:", xalign=0), 0, row, 1, 1)
        self.combo_net_mode = Gtk.ComboBoxText()
        self.combo_net_mode.append_text("DHCP (Automatique)")
        self.combo_net_mode.append_text("Statique (Manuel)")
        self.combo_net_mode.connect("changed", self._on_net_mode_changed)
        grid.attach(self.combo_net_mode, 1, row, 1, 1)
        row += 1
        grid.attach(Gtk.Label(label="Adresse IP:", xalign=0), 0, row, 1, 1)
        self.entry_ip = Gtk.Entry()
        self.entry_ip.set_sensitive(False)
        grid.attach(self.entry_ip, 1, row, 1, 1)
        row += 1
        grid.attach(Gtk.Label(label="Masque (CIDR):", xalign=0), 0, row, 1, 1)
        self.entry_mask = Gtk.Entry()
        self.entry_mask.set_text("24")
        self.entry_mask.set_sensitive(False)
        grid.attach(self.entry_mask, 1, row, 1, 1)
        row += 1
        grid.attach(Gtk.Label(label="Passerelle (Gateway):", xalign=0), 0, row, 1, 1)
        self.entry_gw = Gtk.Entry()
        self.entry_gw.set_sensitive(False)
        grid.attach(self.entry_gw, 1, row, 1, 1)
        row += 1
        grid.attach(Gtk.Label(label="DNS (séparés par virgule):", xalign=0), 0, row, 1, 1)
        self.entry_dns = Gtk.Entry()
        self.entry_dns.set_text("8.8.8.8, 1.1.1.1")
        self.entry_dns.set_sensitive(False)
        grid.attach(self.entry_dns, 1, row, 1, 1)
        box.append(grid)
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, halign=Gtk.Align.END)
        btn_detect = Gtk.Button(label="🔍 Détecter Config Actuelle")
        btn_detect.connect("clicked", lambda *_: self._detect_network_config())
        btn_apply = Gtk.Button(label="💾 Appliquer Configuration", css_classes=["suggested-action"])
        btn_apply.connect("clicked", lambda *_: self._apply_network_config())
        btn_box.append(btn_detect)
        btn_box.append(btn_apply)
        box.append(btn_box)
        import threading, gi
        gi.require_version("GLib", "2.0")
        from gi.repository import GLib
        GLib.idle_add(self._detect_network_config)
        return box

    def _detect_network_config(self):
        def _thread():
            try:
                import subprocess, json, gi
                gi.require_version("GLib", "2.0")
                from gi.repository import GLib
                proc = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True)
                iface = "eth0"
                if proc.returncode == 0 and proc.stdout:
                    parts = proc.stdout.split()
                    if "dev" in parts:
                        idx = parts.index("dev")
                        if idx + 1 < len(parts):
                            iface = parts[idx+1]
                GLib.idle_add(lambda: self.lbl_interface.set_text(f"Interface: {iface}"))
                proc_ip = subprocess.run(["ip", "-j", "addr", "show", iface], capture_output=True, text=True)
                ip_addr = "Non configurée"
                if proc_ip.returncode == 0:
                    data = json.loads(proc_ip.stdout)
                    if data and data[0].get("addr_info"):
                        for addr in data[0]["addr_info"]:
                            if addr["family"] == "inet":
                                ip_addr = f"{addr['local']}/{addr['prefixlen']}"
                                break
                GLib.idle_add(lambda: self.lbl_current_ip.set_text(f"IP Actuelle: {ip_addr}"))
                GLib.idle_add(lambda: self.entry_ip.set_text(ip_addr.split('/')[0] if '/' in ip_addr else ""))
            except Exception as e:
                import gi
                gi.require_version("GLib", "2.0")
                from gi.repository import GLib
                GLib.idle_add(lambda: self.terminal._log(f"❌ Erreur détection réseau: {e}"))
        import threading
        threading.Thread(target=_thread, daemon=True).start()

    def _on_net_mode_changed(self, combo):
        is_static = combo.get_active() == 1
        self.entry_ip.set_sensitive(is_static)
        self.entry_mask.set_sensitive(is_static)
        self.entry_gw.set_sensitive(is_static)
        self.entry_dns.set_sensitive(is_static)

    def _apply_network_config(self):
        iface = self.lbl_interface.get_text().replace("Interface: ", "")
        mode = self.combo_net_mode.get_active_text()
        if "DHCP" in mode:
            self.terminal._log(f"▶ Configuration DHCP pour {iface}")
            self._run_network_script(f"dhclient -r {iface} && dhclient {iface}")
        else:
            ip = self.entry_ip.get_text().strip()
            mask = self.entry_mask.get_text().strip()
            gw = self.entry_gw.get_text().strip()
            dns = self.entry_dns.get_text().strip()
            if not ip or not gw:
                return self.show_toast("❌ IP et Passerelle requises")
            self.terminal._log(f"▶ Configuration Statique: {ip}/{mask} via {gw}")
            dns_list = [f"nameserver {d.strip()}" for d in dns.split(',')]
            dns_text = "\n".join(dns_list)
            script = f"ip addr flush dev {iface}\n"
            script += f"ip addr add {ip}/{mask} dev {iface}\n"
            script += f"ip route add default via {gw}\n"
            script += f"printf '%s\n' '{dns_text}' > /etc/resolv.conf\n"
            self._run_network_script(script)

    def _run_network_script(self, script):
        def _thread():
            try:
                import subprocess, gi
                gi.require_version("GLib", "2.0")
                from gi.repository import GLib
                proc = subprocess.run(["sudo", "bash", "-c", script], capture_output=True, text=True)
                output = proc.stdout + proc.stderr
                GLib.idle_add(lambda: self.terminal._log(output))
                if proc.returncode == 0:
                    GLib.idle_add(lambda: self.show_toast("✅ Configuration réseau appliquée"))
                    GLib.idle_add(self._detect_network_config)
                else:
                    GLib.idle_add(lambda: self.show_toast("❌ Échec configuration réseau"))
            except Exception as e:
                import gi
                gi.require_version("GLib", "2.0")
                from gi.repository import GLib
                GLib.idle_add(lambda: self.terminal._log(f"❌ Erreur: {e}"))
        import threading
        threading.Thread(target=_thread, daemon=True).start()

    def _build_systemd_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        set_margins(box, 10)
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.entry_svc_search = Gtk.Entry()
        self.entry_svc_search.set_placeholder_text("Rechercher un service...")
        self.entry_svc_search.set_hexpand(True)
        self.entry_svc_search.connect("changed", lambda *_: self._filter_services())
        btn_refresh_svc = Gtk.Button(label="🔄 Actualiser Liste")
        btn_refresh_svc.connect("clicked", lambda *_: self._load_systemd_services())
        search_box.append(self.entry_svc_search)
        search_box.append(btn_refresh_svc)
        box.append(search_box)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        self.listbox_services = Gtk.ListBox()
        self.listbox_services.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll.set_child(self.listbox_services)
        box.append(scroll)
        import threading, gi
        gi.require_version("GLib", "2.0")
        from gi.repository import GLib
        GLib.idle_add(self._load_systemd_services)
        return box

    def _load_systemd_services(self):
        def _thread():
            try:
                import subprocess, gi
                gi.require_version("GLib", "2.0")
                from gi.repository import GLib
                proc = subprocess.run(["systemctl", "list-unit-files", "--type=service", "--no-pager", "--no-legend"], capture_output=True, text=True)
                services = []
                if proc.returncode == 0:
                    for line in proc.stdout.splitlines():
                        parts = line.split()
                        if len(parts) >= 2:
                            services.append((parts[0], parts[1]))
                GLib.idle_add(lambda: self._populate_service_list(services))
            except Exception as e:
                import gi
                gi.require_version("GLib", "2.0")
                from gi.repository import GLib
                GLib.idle_add(lambda: self.terminal._log(f"❌ Erreur chargement services: {e}"))
        import threading
        threading.Thread(target=_thread, daemon=True).start()

    def _populate_service_list(self, services):
        self.all_services = services
        self._filter_services()

    def _filter_services(self):
        query = self.entry_svc_search.get_text().lower()
        while child := self.listbox_services.get_first_child():
            self.listbox_services.remove(child)
        for name, state in self.all_services:
            if query in name.lower():
                self.listbox_services.append(self._create_service_row(name, state))

    def _create_service_row(self, name, state):
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        set_margins(box, 8)
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.append(Gtk.Label(label=name, xalign=0, css_classes=["heading"]))
        self.lbl_state = Gtk.Label(label=f"État au démarrage: {state}", xalign=0, css_classes=["dim-label"])
        info_box.append(self.lbl_state)
        box.append(info_box)
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        box.append(spacer)
        ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        btn_start = Gtk.Button(label="▶"); btn_start.set_tooltip_text("Démarrer")
        btn_start.connect("clicked", lambda *_: self._control_service(name, "start"))
        btn_stop = Gtk.Button(label="⏹"); btn_stop.set_tooltip_text("Arrêter")
        btn_stop.connect("clicked", lambda *_: self._control_service(name, "stop"))
        btn_auto = Gtk.ToggleButton(label="Auto")
        btn_auto.set_tooltip_text("Activer/Désactiver au démarrage (Sauvegardé en DB LiveOS)")
        btn_auto.set_active(self._is_service_auto_start(name))
        btn_auto.connect("toggled", lambda b: self._toggle_service_auto_start(name, b.get_active(), self.lbl_state))
        ctrl_box.append(btn_start)
        ctrl_box.append(btn_stop)
        ctrl_box.append(btn_auto)
        box.append(ctrl_box)
        row.set_child(box)
        return row

    def _is_service_auto_start(self, service_name):
        import sqlite3, subprocess
        db_path = _get_db_path(self.get_config().get("db_path"))
        try:
            con = sqlite3.connect(str(db_path))
            cur = con.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS liveos_services (name TEXT PRIMARY KEY, auto_start INTEGER DEFAULT 0)")
            cur.execute("SELECT auto_start FROM liveos_services WHERE name=?", (service_name,))
            res = cur.fetchone()
            con.close()
            if res: return bool(res[0])
        except Exception as e:
            global_log(f"⚠️ Erreur dans gy.py: {type(e).__name__} - {e}")
        try:
            return subprocess.run(["systemctl", "is-enabled", service_name], capture_output=True).returncode == 0
        except: return False

    def _toggle_service_auto_start(self, service_name, enable, label_widget):
        import sqlite3, subprocess, gi
        gi.require_version("GLib", "2.0")
        from gi.repository import GLib
        db_path = _get_db_path(self.get_config().get("db_path"))
        try:
            con = sqlite3.connect(str(db_path))
            cur = con.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS liveos_services (name TEXT PRIMARY KEY, auto_start INTEGER DEFAULT 0)")
            cur.execute("INSERT OR REPLACE INTO liveos_services (name, auto_start) VALUES (?, ?)", (service_name, 1 if enable else 0))
            con.commit()
            con.close()
            cmd = "enable" if enable else "disable"
            subprocess.run(["sudo", "systemctl", cmd, service_name], capture_output=True)
            GLib.idle_add(lambda: label_widget.set_text(f"État au démarrage: {'activé' if enable else 'désactivé'} (DB)"))
            GLib.idle_add(lambda: self.show_toast(f"✅ {service_name} {'activé' if enable else 'désactivé'} au démarrage"))
        except Exception as e:
            import gi
            gi.require_version("GLib", "2.0")
            from gi.repository import GLib
            GLib.idle_add(lambda: self.terminal._log(f"❌ Erreur DB/Systemd: {e}"))

    def _control_service(self, service_name, action):
        self.terminal._log(f"▶ sudo systemctl {action} {service_name}")
        def _thread():
            try:
                import subprocess, gi
                gi.require_version("GLib", "2.0")
                from gi.repository import GLib
                proc = subprocess.run(["sudo", "systemctl", action, service_name], capture_output=True, text=True)
                if proc.returncode == 0:
                    GLib.idle_add(lambda: self.show_toast(f"✅ {service_name} {action}ed"))
                else:
                    GLib.idle_add(lambda: self.terminal._log(f"❌ Erreur: {proc.stderr}"))
            except Exception as e:
                import gi
                gi.require_version("GLib", "2.0")
                from gi.repository import GLib
                GLib.idle_add(lambda: self.terminal._log(f"❌ Exception: {e}"))
        import threading
        threading.Thread(target=_thread, daemon=True).start()
    # ═══════════════════════════════════════════════════════════════════════
    #  NOUVEAUX MODULES SYSTÈME (Processus, DNS, TOR, DNF, PIP)
    # ═══════════════════════════════════════════════════════════════════════

    # ─── 1. GESTION DES PROCESSUS ──────────────────────────────────────
    def _build_process_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        set_margins(box, 16)
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.lbl_proc_count = Gtk.Label(label="Chargement...", css_classes=["heading"])
        btn_refresh = Gtk.Button(label="🔄 Actualiser")
        btn_refresh.connect("clicked", lambda *_: self._load_processes())
        header.append(self.lbl_proc_count)
        header.append(Gtk.Box(hexpand=True))
        header.append(btn_refresh)
        box.append(header)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        self.store_proc = Gtk.TreeStore(str, str, str, str, str)
        self.tree_proc = Gtk.TreeView(model=self.store_proc)
        self.tree_proc.set_headers_visible(True)
        cols = [("PID", 0, 60), ("Nom", 1, 200), ("User", 2, 80), ("% CPU/MEM", 3, 100), ("État", 4, 60)]
        for title, idx, width in cols:
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=idx)
            column.set_resizable(True)
            column.set_min_width(width)
            if idx == 1: renderer.set_property("weight", Pango.Weight.BOLD)
            self.tree_proc.append_column(column)
            
        gesture = Gtk.GestureClick.new()
        gesture.set_button(Gdk.BUTTON_SECONDARY)
        gesture.connect("pressed", self._on_proc_right_click)
        self.tree_proc.add_controller(gesture)
        
        scroll.set_child(self.tree_proc)
        box.append(scroll)
        
        info_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.lbl_selected_proc = Gtk.Label(label="Clic droit pour actions", xalign=0, css_classes=["dim-label"])
        info_bar.append(self.lbl_selected_proc)
        box.append(info_bar)
        
        GLib.idle_add(self._load_processes)
        return box

    def _load_processes(self):
        self.store_proc.clear()
        try:
            proc = subprocess.run(["ps", "aux", "--sort=-%cpu"], capture_output=True, text=True, check=True)
            lines = proc.stdout.strip().split('\n')[1:]
            count = 0
            for line in lines:
                parts = line.split(None, 10)
                if len(parts) < 11: continue
                user, pid, cpu, mem, vsz, rss, tty, stat, start, time, cmd = parts
                name = cmd.split('/')[-1].split()[0][:30]
                self.store_proc.append(None, [pid, name, user, f"{cpu}%/{mem}%", stat])
                count += 1
                if count > 300: break
            self.lbl_proc_count.set_text(f"{count} processus")
        except Exception as e:
            self.terminal._log(f"❌ Erreur processus: {e}")

    def _on_proc_right_click(self, gesture, n_press, x, y):
        path, _, _, _ = self.tree_proc.get_path_at_pos(int(x), int(y))
        if not path: return
        self.tree_proc.set_cursor(path)
        model = self.tree_proc.get_model()
        iter_row = model.get_iter(path)
        pid = model.get_value(iter_row, 0)
        name = model.get_value(iter_row, 1)
        self.lbl_selected_proc.set_text(f"Sélectionné: {name} (PID: {pid})")
        
        popover = Gtk.Popover()
        popover.set_parent(self.tree_proc)
        v_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        set_margins(v_box, 6)
        
        btn_copy = Gtk.Button(label="📋 Copier PID")
        btn_copy.set_halign(Gtk.Align.FILL)
        btn_copy.add_css_class("flat")
        btn_copy.connect("clicked", lambda *_: (Gdk.Display.get_default().get_clipboard().set(pid), popover.popdown(), self.show_toast("PID copié")))
        
        btn_kill = Gtk.Button(label="💀 Tuer (Kill -9)")
        btn_kill.set_halign(Gtk.Align.FILL)
        btn_kill.add_css_class("flat")
        btn_kill.add_css_class("destructive-action")
        btn_kill.connect("clicked", lambda *_: self._kill_process(pid, name, popover))
        
        v_box.append(btn_copy)
        v_box.append(btn_kill)
        popover.set_child(v_box)
        
        rect = Gdk.Rectangle(); rect.x = int(x); rect.y = int(y); rect.width = 1; rect.height = 1
        popover.set_pointing_to(rect)
        popover.popup()

    def _kill_process(self, pid, name, popover):
        popover.popdown()
        dlg = Gtk.MessageDialog(transient_for=self.get_root(), flags=0, message_type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.YES_NO, text=f"Tuer {name} ?")
        dlg.format_secondary_text(f"Le processus PID {pid} sera arrêté immédiatement.")
        def on_resp(d, r):
            d.destroy()
            if r == Gtk.ResponseType.YES:
                try:
                    subprocess.run(["sudo", "kill", "-9", pid], check=True)
                    self.show_toast(f"✅ Processus {pid} tué")
                    self._load_processes()
                except Exception as e: self.show_toast(f"❌ Échec: {e}")
        dlg.connect("response", on_resp)
        dlg.present()

    # ─── 2. CONFIGURATION DNS COMPLÈTE ──────────────────────────────────────────
    def _build_dns_page(self):
        """Construit l'onglet DNS avec Formulaire, Gestion Service et Permissions Auto"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        set_margins(box, 16)
        
        # --- Section 1: Contrôle du Service Dnsmasq (Vos boutons conservés) ---
        box.append(Gtk.Label(label="🛡️ Service Dnsmasq", xalign=0, css_classes=["heading"]))
        
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.lbl_dnsmasq_status = Gtk.Label(label="Statut: Inconnu", xalign=0, css_classes=["dim-label"])
        status_box.append(self.lbl_dnsmasq_status)
        
        # Boutons de contrôle du service
        btn_start = Gtk.Button(label="▶ Démarrer", css_classes=["ctrl-btn-start"])
        btn_start.connect("clicked", lambda *_: self._control_dnsmasq("start"))
        
        btn_stop = Gtk.Button(label="⏹ Arrêter", css_classes=["ctrl-btn-stop"])
        btn_stop.connect("clicked", lambda *_: self._control_dnsmasq("stop"))
        
        btn_restart = Gtk.Button(label="🔄 Redémarrer", css_classes=["ctrl-btn-warn"])
        btn_restart.connect("clicked", lambda *_: self._control_dnsmasq("restart"))
        
        status_box.append(btn_start)
        status_box.append(btn_stop)
        status_box.append(btn_restart)
        box.append(status_box)
        
        box.append(Gtk.Separator(margin_top=10, margin_bottom=10))

        # --- Section 2: Configuration DNS Client (/etc/resolv.conf) ---
        box.append(Gtk.Label(label="📡 DNS Client (Résolution)", xalign=0, css_classes=["heading"]))
        grid_client = Gtk.Grid(); grid_client.set_column_spacing(10); grid_client.set_row_spacing(10)
        row = 0
        
        grid_client.attach(Gtk.Label(label="Serveurs actuels :", xalign=0), 0, row, 1, 1)
        self.txt_current_dns = GtkSource.View()
        self.txt_current_dns.set_editable(False)
        self.txt_current_dns.set_monospace(True)
        self.txt_current_dns.set_size_request(-1, 50)
        self.txt_current_dns.set_show_line_numbers(True)
        s_dns = Gtk.ScrolledWindow(); s_dns.set_child(self.txt_current_dns); grid_client.attach(s_dns, 1, row, 1, 1); row += 1
        
        grid_client.attach(Gtk.Label(label="Nouveaux DNS (ex: 1.1.1.1 8.8.8.8):", xalign=0), 0, row, 1, 1)
        self.entry_new_dns = Gtk.Entry(); self.entry_new_dns.set_text("1.1.1.1 8.8.8.8"); self.entry_new_dns.set_hexpand(True)
        grid_client.attach(self.entry_new_dns, 1, row, 1, 1); row += 1
        
        btn_box_client = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_apply = Gtk.Button(label="💾 Appliquer (Sudo)", css_classes=["suggested-action"])
        btn_apply.connect("clicked", self._apply_dns)
        btn_restore = Gtk.Button(label="↺ Restaurer DHCP")
        btn_restore.connect("clicked", self._restore_dns_dhcp)
        btn_box_client.append(btn_apply); btn_box_client.append(btn_restore)
        grid_client.attach(btn_box_client, 1, row, 1, 1)
        
        box.append(grid_client)
        box.append(Gtk.Separator(margin_top=10, margin_bottom=10))

        # --- Section 3: Formulaire de Configuration Dnsmasq ---
        box.append(Gtk.Label(label="⚙️ Configuration Dnsmasq (Formulaire)", xalign=0, css_classes=["heading"]))
        
        form_grid = Gtk.Grid()
        form_grid.set_column_spacing(10)
        form_grid.set_row_spacing(10)
        r = 0

        # Champ 1: Serveurs DNS Amont
        form_grid.attach(Gtk.Label(label="DNS Amont (Upstream) :", xalign=0), 0, r, 1, 1)
        self.entry_upstream_dns = Gtk.Entry()
        self.entry_upstream_dns.set_placeholder_text("8.8.8.8, 1.1.1.1")
        self.entry_upstream_dns.set_tooltip_text("IPs des serveurs DNS principaux")
        self.entry_upstream_dns.set_hexpand(True)
        form_grid.attach(self.entry_upstream_dns, 1, r, 1, 1)
        r += 1

        # Champ 2: Adresses Statiques Locales
        form_grid.attach(Gtk.Label(label="Hôtes Locaux (Nom -> IP) :", xalign=0), 0, r, 1, 1)
        self.entry_local_addr = Gtk.Entry()
        self.entry_local_addr.set_placeholder_text("monserveur.local -> 192.168.1.10")
        self.entry_local_addr.set_tooltip_text("Associe un nom de domaine à une IP locale")
        self.entry_local_addr.set_hexpand(True)
        form_grid.attach(self.entry_local_addr, 1, r, 1, 1)
        r += 1

        # Champ 3: Blocage de Domaines
        form_grid.attach(Gtk.Label(label="Domaines Bloqués :", xalign=0), 0, r, 1, 1)
        self.entry_blocked = Gtk.Entry()
        self.entry_blocked.set_placeholder_text("pub.example.com, ads.net")
        self.entry_blocked.set_tooltip_text("Ces domaines pointeront vers 0.0.0.0")
        self.entry_blocked.set_hexpand(True)
        form_grid.attach(self.entry_blocked, 1, r, 1, 1)
        r += 1

        # Champ 4: Interface
        form_grid.attach(Gtk.Label(label="Interface Écoute :", xalign=0), 0, r, 1, 1)
        self.entry_interface = Gtk.Entry()
        self.entry_interface.set_text("lo, eth0")
        self.entry_interface.set_hexpand(True)
        form_grid.attach(self.entry_interface, 1, r, 1, 1)
        r += 1

        box.append(form_grid)

        # Bouton Sauvegarde Configuration
        btn_save_config = Gtk.Button(label="💾 Sauvegarder Config Dnsmasq", css_classes=["suggested-action"], halign=Gtk.Align.END, margin_top=10)
        btn_save_config.connect("clicked", self._save_dnsmasq_from_form)
        box.append(btn_save_config)

        # Chargement initial des données
        GLib.idle_add(self._read_current_dns)
        GLib.idle_add(self._check_dnsmasq_status)
        
        return box

    # ─── 2. CONFIGURATION DNS COMPLÈTE (VERSION CONSOLIDÉE) ──────────────────────────────────────────
    def _control_dnsmasq(self, action):
        """Gère le démarrage/arrêt/redémarrage avec sudo"""
        self.terminal._log(f"▶ Service Dnsmasq : {action}...")
        def _thread():
            try:
                proc = subprocess.run(["sudo", "systemctl", action, "dnsmasq"], capture_output=True, text=True)
                if proc.returncode == 0:
                    GLib.idle_add(lambda: self.show_toast(f"✅ Dnsmasq {action}é"))
                    GLib.idle_add(self._check_dnsmasq_status)
                else:
                    GLib.idle_add(lambda: self.terminal._log(f"❌ Erreur systemctl: {proc.stderr}"))
                    GLib.idle_add(lambda: self.show_toast(f"❌ Échec Dnsmasq {action}"))
            except Exception as e:
                GLib.idle_add(lambda: self.terminal._log(f"❌ Exception: {e}"))
        threading.Thread(target=_thread, daemon=True).start()

    def _check_dnsmasq_status(self):
        """Vérifie l'état du service pour l'affichage"""
        try:
            proc = subprocess.run(["systemctl", "is-active", "dnsmasq"], capture_output=True, text=True)
            status = proc.stdout.strip()
            if status == "active":
                self.lbl_dnsmasq_status.set_text("Statut Service: 🟢 Actif")
                self.lbl_dnsmasq_status.remove_css_class("dim-label")
            else:
                self.lbl_dnsmasq_status.set_text("Statut Service: 🔴 Inactif")
                self.lbl_dnsmasq_status.add_css_class("dim-label")
        except Exception as e:
            global_log(f"⚠️ Erreur dans _check_dnsmasq_status: {type(e).__name__} - {e}")

    def _save_dnsmasq_from_form(self, *_):
        """Génère le fichier de configuration Dnsmasq à partir des champs du formulaire"""
        upstream = self.entry_upstream_dns.get_text().strip()
        local_addr = self.entry_local_addr.get_text().strip()
        blocked = self.entry_blocked.get_text().strip()
        interface = self.entry_interface.get_text().strip()

        config_lines = [
            "# Configuration générée automatiquement par Gykhamine Studio",
            f"# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        if interface:
            config_lines.append(f"interface={interface}")
            config_lines.append("bind-interfaces")
        if upstream:
            for s in re.split(r'[,\s]+', upstream):
                if s.strip(): config_lines.append(f"server={s.strip()}")
        if local_addr:
            for entry in re.split(r'\n+', local_addr):
                if '->' in entry:
                    parts = entry.split('->')
                    if len(parts) == 2:
                        config_lines.append(f"address=/{parts[0].strip()}/{parts[1].strip()}")
        if blocked:
            for d in re.split(r'[,\s]+', blocked):
                if d.strip(): config_lines.append(f"address=/{d.strip()}/0.0.0.0")

        final_content = "\n".join(config_lines) + "\n"
        target_file = "/etc/dnsmasq.d/local.conf"
        self.terminal._log(f"💾 Génération de la configuration pour {target_file}...")

        def _thread():
            try:
                proc = subprocess.run(["sudo", "tee", target_file], input=final_content, text=True, capture_output=True)
                if proc.returncode == 0:
                    GLib.idle_add(lambda: self.terminal._log("✅ Configuration sauvegardée avec succès."))
                    GLib.idle_add(lambda: self.show_toast("✅ Configuration Dnsmasq appliquée"))
                else:
                    GLib.idle_add(lambda: self.terminal._log(f"❌ Erreur d'écriture : {proc.stderr}"))
                    GLib.idle_add(lambda: self.show_toast("❌ Échec de la sauvegarde (Vérifiez le mot de passe sudo)"))
            except Exception as e:
                GLib.idle_add(lambda: self.terminal._log(f"❌ Exception : {e}"))
        threading.Thread(target=_thread, daemon=True).start()

    def _apply_dns(self, *_):
        """Applique les nouveaux serveurs DNS dans /etc/resolv.conf avec sauvegarde"""
        new_dns = self.entry_new_dns.get_text().strip()
        if not new_dns:
            return self.show_toast("❌ DNS requis")

        dns_list = re.split(r'[,\s]+', new_dns)
        nameservers = "\n".join([f"nameserver {ip.strip()}" for ip in dns_list if ip.strip()])

        script = f"""
# Sauvegarde automatique de l'ancien fichier
cp /etc/resolv.conf /etc/resolv.conf.bak.$(date +%s)
# Écriture sécurisée via sudo tee
echo '# Généré par Gykhamine Studio' | sudo tee /etc/resolv.conf > /dev/null
echo '{nameservers}' | sudo tee -a /etc/resolv.conf > /dev/null
chmod 644 /etc/resolv.conf
"""
        self._run_system_script(script, "Application DNS Manuelle")

    def _restore_dns_dhcp(self, *_):
        """Restaure la config DNS via DHCP"""
        script = """
rm -f /etc/resolv.conf
# Relance NetworkManager pour régénérer le fichier via DHCP
systemctl restart NetworkManager
"""
        self._run_system_script(script, "Restauration DNS via DHCP")

    def _read_current_dns(self):
        """Lit le resolv.conf actuel"""
        try:
            with open("/etc/resolv.conf", "r") as f:
                self.txt_current_dns.get_buffer().set_text(f.read())
        except Exception as e:
            self.txt_current_dns.get_buffer().set_text(f"Erreur lecture: {e}")
    def _check_dnsmasq_status(self):
        """Vérifie l'état du service pour l'affichage"""
        try:
            proc = subprocess.run(["systemctl", "is-active", "dnsmasq"], capture_output=True, text=True)
            status = proc.stdout.strip()
            if status == "active":
                self.lbl_dnsmasq_status.set_text("Statut: 🟢 Actif")
                self.lbl_dnsmasq_status.remove_css_class("dim-label")
            else:
                self.lbl_dnsmasq_status.set_text("Statut: 🔴 Inactif")
                self.lbl_dnsmasq_status.add_css_class("dim-label")
        except Exception as e:
            global_log(f"⚠️ Erreur dans _check_dnsmasq_status: {type(e).__name__} - {e}")

    def _save_dnsmasq_from_form(self, *_):
        """Génère le fichier /etc/dnsmasq.d/local.conf depuis le formulaire"""
        upstream = self.entry_upstream_dns.get_text().strip()
        local_addr = self.entry_local_addr.get_text().strip()
        blocked = self.entry_blocked.get_text().strip()
        interface = self.entry_interface.get_text().strip()

        config_lines = ["# Généré par Gykhamine Studio - Formulaire DNS"]
        
        if interface:
            for iface in interface.split(','):
                config_lines.append(f"interface={iface.strip()}")
            config_lines.append("bind-interfaces")
        
        if upstream:
            for dns in re.split(r'[,\s]+', upstream):
                if dns: config_lines.append(f"server={dns}")

        if local_addr and '->' in local_addr:
            parts = local_addr.split('->')
            if len(parts) == 2:
                config_lines.append(f"address=/{parts[0].strip()}/{parts[1].strip()}")

        if blocked:
            for domain in re.split(r'[,\s]+', blocked):
                if domain: config_lines.append(f"address=/{domain}/0.0.0.0")

        final_content = "\n".join(config_lines) + "\n"
        target_file = "/etc/dnsmasq.d/local.conf"

        self.terminal._log(f"💾 Écriture de {target_file}...")
        
        def _thread():
            try:
                # Utilisation de sudo tee pour gérer les permissions automatiquement
                proc = subprocess.run(
                    ["sudo", "tee", target_file], 
                    input=final_content, 
                    text=True, 
                    capture_output=True
                )
                if proc.returncode == 0:
                    GLib.idle_add(lambda: self.show_toast("✅ Config Dnsmasq sauvegardée"))
                    GLib.idle_add(lambda: self.terminal._log("✅ Fichier écrit avec succès"))
                else:
                    GLib.idle_add(lambda: self.show_toast("❌ Échec écriture (Sudo ?)"))
            except Exception as e:
                GLib.idle_add(lambda: self.terminal._log(f"❌ Erreur: {e}"))
        
        threading.Thread(target=_thread, daemon=True).start()

    def _apply_dns(self, *_):
        """Applique les DNS dans resolv.conf avec sudo"""
        new_dns = self.entry_new_dns.get_text().strip()
        if not new_dns: return self.show_toast("❌ DNS requis")
        
        dns_list = re.split(r'[,\s]+', new_dns)
        nameservers = "\n".join([f"nameserver {ip.strip()}" for ip in dns_list if ip.strip()])
        
        script = f"""
echo '# Généré par Gykhamine Studio' | sudo tee /etc/resolv.conf > /dev/null
echo '{nameservers}' | sudo tee -a /etc/resolv.conf > /dev/null
chmod 644 /etc/resolv.conf
"""
        self._run_system_script(script, "Application DNS")

    def _restore_dns_dhcp(self, *_):
        """Restaure la config DNS via DHCP"""
        script = "sudo rm -f /etc/resolv.conf && sudo systemctl restart NetworkManager"
        self._run_system_script(script, "Restauration DNS DHCP")

    def _read_current_dns(self):
        """Lit le resolv.conf actuel"""
        try:
            with open("/etc/resolv.conf", "r") as f:
                self.txt_current_dns.get_buffer().set_text(f.read())
        except Exception as e:
            self.txt_current_dns.get_buffer().set_text(f"Erreur: {e}")
    # --- Méthodes de Gestion des Permissions et Services ---

    def _test_dns_connectivity(self, *_):
        self.terminal._log("🔍 Test de résolution DNS...")
        def thread():
            domains = ["google.com", "github.com", "torproject.org"]
            for domain in domains:
                try:
                    r = subprocess.run(["nslookup", domain], capture_output=True, text=True, timeout=5)
                    status = "✅ OK" if r.returncode == 0 else "❌ Échec"
                    GLib.idle_add(lambda s=status, d=domain: self.terminal._log(f"{s} {d}"))
                except Exception as e:
                    GLib.idle_add(lambda e=e, d=domain: self.terminal._log(f"❌ {d}: {e}"))
        threading.Thread(target=thread, daemon=True).start()

    # ─── 3. SUPPORT TOR CORRIGÉ ────────────────────────────────────────────────
    def _build_tor_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        set_margins(box, 16)
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.lbl_tor_status = Gtk.Label(label="Status: Inconnu", css_classes=["heading"])
        self.lbl_tor_ip = Gtk.Label(label="IP: ...", css_classes=["dim-label"])
        header.append(self.lbl_tor_status); header.append(Gtk.Box(hexpand=True)); header.append(self.lbl_tor_ip)
        box.append(header)
        
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_install = Gtk.Button(label="📥 Installer Tor"); btn_install.connect("clicked", lambda *_: self._install_tor())
        btn_fix_perms = Gtk.Button(label="🔧 Fixer Permissions /run/tor")
        btn_fix_perms.connect("clicked", lambda *_: self._fix_tor_permissions())
        btn_start = Gtk.Button(label="▶ Start", css_classes=["suggested-action"]); btn_start.connect("clicked", lambda *_: self._control_tor("start"))
        btn_stop = Gtk.Button(label="⏹ Stop", css_classes=["destructive-action"]); btn_stop.connect("clicked", lambda *_: self._control_tor("stop"))
        btn_check = Gtk.Button(label="🕵️ Vérifier IP"); btn_check.connect("clicked", lambda *_: self._check_tor_ip())
        
        btn_box.append(btn_install); btn_box.append(btn_fix_perms); btn_box.append(btn_start); btn_box.append(btn_stop); btn_box.append(btn_check)
        box.append(btn_box)
        
        GLib.idle_add(self._update_tor_status)
        return box

    def _fix_tor_permissions(self):
        self.terminal._log("🔧 Correction des permissions Tor...")
        script = """
mkdir -p /run/tor
chown toranon:toranon /run/tor 2>/dev/null || chown $(whoami):$(whoami) /run/tor
chmod 700 /run/tor
"""
        self._run_system_script(script, "Fix Permissions Tor")

    def _install_tor(self): 
        self._run_system_script("sudo dnf install -y tor", "Installation Tor")
    
    def _control_tor(self, action):
        # Utilisation de sudo pour éviter les erreurs de socket dans /run/tor
        self._run_system_script(f"sudo systemctl {action} tor", f"Tor {action}")
        GLib.timeout_add_seconds(2, self._update_tor_status)

    def _update_tor_status(self):
        try:
            status = subprocess.run(["systemctl", "is-active", "tor"], capture_output=True, text=True).stdout.strip()
            if status == "active":
                self.lbl_tor_status.set_text("Status: 🟢 Actif"); self.lbl_tor_status.remove_css_class("dim-label")
            else:
                self.lbl_tor_status.set_text("Status: 🔴 Inactif"); self.lbl_tor_status.add_css_class("dim-label")
        except Exception as e:
            global_log(f"⚠️ Erreur dans gy.py: {type(e).__name__} - {e}")
        return False

    def _check_tor_ip(self):
        self.lbl_tor_ip.set_text("Vérification...")
        def thread():
            try:
                # Utilisation de curl via le proxy SOCKS5 de Tor
                proc = subprocess.run(["curl", "-s", "--socks5-hostname", "127.0.0.1:9050", "https://api.ipify.org"], capture_output=True, text=True, timeout=15)
                if proc.returncode == 0 and proc.stdout:
                    GLib.idle_add(lambda: self.lbl_tor_ip.set_text(f"IP Tor: {proc.stdout.strip()}"))
                    GLib.idle_add(lambda: self.show_toast("✅ Tor Fonctionnel"))
                else:
                    GLib.idle_add(lambda: self.lbl_tor_ip.set_text("Échec connexion (Vérifiez que Tor est lancé)"))
            except Exception as e: 
                GLib.idle_add(lambda: self.lbl_tor_ip.set_text(f"Erreur: {e}"))
        threading.Thread(target=thread, daemon=True).start()

    # ─── 4. GESTION DNF AVANCÉE ────────────────────────────────────────────────
    def _build_dnf_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        set_margins(box, 16)
        
        # --- Section 1: Recherche et Installation (Existant) ---
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.entry_dnf_search = Gtk.Entry(); self.entry_dnf_search.set_placeholder_text("Rechercher paquet..."); self.entry_dnf_search.set_hexpand(True)
        self.entry_dnf_search.connect("activate", lambda *_: self._search_dnf())
        btn_search = Gtk.Button(label="🔍 Chercher"); btn_search.connect("clicked", lambda *_: self._search_dnf())
        search_box.append(self.entry_dnf_search); search_box.append(btn_search)
        box.append(search_box)
        
        scroll_pkgs = Gtk.ScrolledWindow(); scroll_pkgs.set_vexpand(True); scroll_pkgs.set_size_request(-1, 200)
        self.listbox_dnf = Gtk.ListBox(); self.listbox_dnf.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll_pkgs.set_child(self.listbox_dnf)
        box.append(scroll_pkgs)
        
        box.append(Gtk.Separator(margin_top=10, margin_bottom=10))

        # --- Section 2: Configuration du Chemin des Dépôts (Nouveau) ---
        box.append(Gtk.Label(label="📂 Chemin des Dépôts (Repos)", xalign=0, css_classes=["heading"]))
        grid_path = Gtk.Grid(); grid_path.set_column_spacing(10); grid_path.set_row_spacing(10)
        
        row = 0
        grid_path.attach(Gtk.Label(label="Répertoire .repo alternatif:", xalign=0), 0, row, 1, 1)
        self.entry_repo_dir = Gtk.Entry()
        # Par défaut, on utilise le standard, mais l'utilisateur peut changer vers /run/media/...
        self.entry_repo_dir.set_text("/etc/yum.repos.d") 
        self.entry_repo_dir.set_hexpand(True)
        grid_path.attach(self.entry_repo_dir, 1, row, 1, 1)
        
        btn_browse_repo = Gtk.Button(label="📂 Parcourir")
        btn_browse_repo.connect("clicked", lambda *_: self._browse_folder("Choisir dossier repos", self.entry_repo_dir))
        grid_path.attach(btn_browse_repo, 2, row, 1, 1)
        row += 1
        
        info_lbl = Gtk.Label(label="Note: Changer ce chemin nécessite de redémarrer DNF ou d'utiliser '--repofrompath' pour les commandes ponctuelles.", css_classes=["dim-label"], xalign=0, wrap=True)
        grid_path.attach(info_lbl, 1, row, 2, 1)
        
        box.append(grid_path)
        
        box.append(Gtk.Separator(margin_top=10, margin_bottom=10))

        # --- Section 3: Gestion des Dépôts (Liste) ---
        btn_list_repos = Gtk.Button(label="📋 Lister les Repos Actifs")
        btn_list_repos.connect("clicked", self._list_active_repos)
        box.append(btn_list_repos)
        
        # Zone de log pour les repos
        scroll_repo_log = Gtk.ScrolledWindow(); scroll_repo_log.set_size_request(-1, 150)
        self.txt_repo_log = GtkSource.View()
        self.txt_repo_log.set_editable(False)
        self.txt_repo_log.set_monospace(True)
        self.txt_repo_log.set_show_line_numbers(True)
        scroll_repo_log.set_child(self.txt_repo_log)
        box.append(scroll_repo_log)
        
        return box

    def _list_active_repos(self, *_):
        repo_dir = self.entry_repo_dir.get_text().strip()
        self.terminal._log(f"▶ Liste des dépôts depuis: {repo_dir}...")
        
        def _thread():
            try:
                # Si le chemin est différent de /etc/yum.repos.d, on utilise --repofrompath ou on liste les fichiers manuellement
                if repo_dir != "/etc/yum.repos.d":
                    # Pour une utilisation avancée, on pourrait lister les fichiers .repo dans ce dossier
                    import os
                    files = [f for f in os.listdir(repo_dir) if f.endswith('.repo')] if os.path.isdir(repo_dir) else []
                    GLib.idle_add(lambda: self.txt_repo_log.get_buffer().set_text(f"Dépôts trouvés dans {repo_dir}:\n" + "\n".join(files)))
                else:
                    proc = subprocess.run(["dnf", "repolist", "enabled"], capture_output=True, text=True)
                    GLib.idle_add(lambda: self.txt_repo_log.get_buffer().set_text(proc.stdout))
            except Exception as e:
                GLib.idle_add(lambda: self.txt_repo_log.get_buffer().set_text(f"Erreur: {e}"))
                
        threading.Thread(target=_thread, daemon=True).start()
    def _search_dnf(self):
        query = self.entry_dnf_search.get_text().strip()
        if not query: return
        self.lbl_dnf_status.set_text("Recherche...")
        while child := self.listbox_dnf.get_first_child(): self.listbox_dnf.remove(child)
        
        repo_arg = ""
        if self.combo_repo.get_active() > 0:
            # Logique simplifiée pour l'exemple, idéalement on mappe l'index au nom du repo
            pass 

        def thread():
            try:
                cmd = ["dnf", "search", query]
                if repo_arg: cmd.extend(repo_arg)
                proc = subprocess.run(cmd, capture_output=True, text=True)
                lines = proc.stdout.strip().split('\n')
                
                GLib.idle_add(lambda: self.lbl_dnf_status.set_text(f"{len(lines)} résultats trouvés"))
                
                for line in lines:
                    if ": " in line and not line.startswith("======") and not line.startswith("Nom"):
                        parts = line.split(": ", 1)
                        if len(parts) < 2: continue
                        name, desc = parts[0].strip(), parts[1].strip()
                        
                        row = Gtk.ListBoxRow()
                        b = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10); set_margins(b, 8)
                        
                        lbl_name = Gtk.Label(label=name, xalign=0, css_classes=["heading"])
                        lbl_desc = Gtk.Label(label=desc, xalign=0, css_classes=["dim-label"]); lbl_desc.set_ellipsize(Pango.EllipsizeMode.END); lbl_desc.set_max_width_chars(40)
                        
                        # Boutons d'action spécifiques
                        btn_inst = Gtk.Button(label="📥 Install"); btn_inst.add_css_class("suggested-action"); btn_inst.connect("clicked", lambda _, n=name: self._dnf_action("install", n))
                        btn_dl = Gtk.Button(label="💾 Download"); btn_dl.add_css_class("ctrl-btn"); btn_dl.connect("clicked", lambda _, n=name: self._dnf_action("download", n))
                        
                        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2); info.append(lbl_name); info.append(lbl_desc)
                        b.append(info); b.append(Gtk.Box(hexpand=True)); b.append(btn_dl); b.append(btn_inst)
                        row.set_child(b)
                        GLib.idle_add(lambda r=row: self.listbox_dnf.append(r))
                        
            except Exception as e: 
                GLib.idle_add(lambda: self.lbl_dnf_status.set_text(f"Erreur: {e}"))
        threading.Thread(target=thread, daemon=True).start()

    def _dnf_action(self, action, package_name):
        dest = self.entry_dnf_dest.get_text().strip()
        if action == "download" and not os.path.isdir(dest):
            return self.show_toast("❌ Dossier de destination invalide")
            
        self.terminal._log(f"▶ DNF {action} {package_name}...")
        
        def thread():
            try:
                if action == "install":
                    # Installation standard
                    cmd = f"sudo dnf install -y {package_name}"
                elif action == "download":
                    # Téléchargement intelligent : Récupère la liste des dépendances puis télécharge tout
                    # 1. Obtenir la liste des paquets nécessaires (nom.arch)
                    resolve_cmd = f"dnf repoquery --requires --resolve {package_name} 2>/dev/null | sort -u"
                    # Ajout du paquet lui-même
                    full_resolve_cmd = f"(echo {package_name}; {resolve_cmd}) | sort -u"
                    
                    proc_resolve = subprocess.run(full_resolve_cmd, shell=True, capture_output=True, text=True)
                    if proc_resolve.returncode == 0:
                        pkg_list = " ".join(proc_resolve.stdout.strip().split('\n'))
                        if pkg_list:
                            download_cmd = f"dnf download --destdir='{dest}' {pkg_list}"
                            self.terminal._log(f"📦 Téléchargement de {len(pkg_list.split())} paquets vers {dest}...")
                            proc_dl = subprocess.run(download_cmd, shell=True, capture_output=True, text=True)
                            output = proc_dl.stderr + proc_dl.stdout
                            GLib.idle_add(lambda o=output: self.terminal._log(o))
                            if proc_dl.returncode == 0:
                                GLib.idle_add(lambda: self.show_toast(f"✅ Paquets téléchargés dans {dest}"))
                            else:
                                GLib.idle_add(lambda: self.show_toast("❌ Échec du téléchargement"))
                        else:
                            GLib.idle_add(lambda: self.show_toast("❌ Aucune dépendance résolue"))
                    else:
                        GLib.idle_add(lambda: self.show_toast("❌ Erreur de résolution des dépendances"))
                    return # Fin du cas download

                # Cas install standard
                proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                GLib.idle_add(lambda: self.terminal._log(proc.stdout + proc.stderr))
                if proc.returncode == 0:
                    GLib.idle_add(lambda: self.show_toast(f"✅ dnf {action} réussi"))
                else: 
                    GLib.idle_add(lambda: self.show_toast("❌ Échec dnf"))
                    
            except Exception as e: 
                GLib.idle_add(lambda: self.terminal._log(f"❌ {e}"))
        threading.Thread(target=thread, daemon=True).start()

    # ─── 5. GESTION PIP AMÉLIORÉE ──────────────────────────────────────────────
    def _build_pip_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        set_margins(box, 16)
        
        env_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        env_box.append(Gtk.Label(label="Env:", xalign=0))
        self.combo_pip_env = Gtk.ComboBoxText()
        self.combo_pip_env.append_text("Système")
        if self.get_config().get("venv_path"): 
            self.combo_pip_env.append_text(f"Venv: {Path(self.get_config()['venv_path']).name}")
        self.combo_pip_env.set_active(0)
        env_box.append(self.combo_pip_env)
        
        btn_ref = Gtk.Button(label="🔄 Refresh"); btn_ref.connect("clicked", lambda *_: self._list_pip_packages())
        env_box.append(btn_ref)
        box.append(env_box)
        
        # Destination pour download
        dest_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        dest_box.append(Gtk.Label(label="Dest. Download:", xalign=0))
        self.entry_pip_dest = Gtk.Entry()
        self.entry_pip_dest.set_text(str(Path.home() / "Downloads" / "pip_packages"))
        self.entry_pip_dest.set_hexpand(True)
        btn_browse_pip = Gtk.Button(label="📂"); btn_browse_pip.connect("clicked", lambda *_: self._browse_folder("Dossier PIP", self.entry_pip_dest))
        dest_box.append(self.entry_pip_dest); dest_box.append(btn_browse_pip)
        box.append(dest_box)

        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.entry_pip_pkg = Gtk.Entry(); self.entry_pip_pkg.set_placeholder_text("Paquet (ex: requests)"); self.entry_pip_pkg.set_hexpand(True)
        
        btn_inst = Gtk.Button(label="📥 Install", css_classes=["suggested-action"]); btn_inst.connect("clicked", lambda *_: self._pip_action("install"))
        btn_dl = Gtk.Button(label="💾 Download Wheel/Src"); btn_dl.connect("clicked", lambda *_: self._pip_action("download"))
        btn_uninst = Gtk.Button(label="🗑 Uninstall", css_classes=["destructive-action"]); btn_uninst.connect("clicked", lambda *_: self._pip_action("uninstall"))
        
        action_box.append(self.entry_pip_pkg); action_box.append(btn_dl); action_box.append(btn_inst); action_box.append(btn_uninst)
        box.append(action_box)
        
        scroll = Gtk.ScrolledWindow(); scroll.set_vexpand(True)
        self.listbox_pip = Gtk.ListBox(); self.listbox_pip.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll.set_child(self.listbox_pip)
        box.append(scroll)
        
        GLib.idle_add(self._list_pip_packages)
        return box
        
    def _list_pip_packages(self):
        """Liste les paquets pip installés"""
        # Nettoyer la liste actuelle
        while child := self.listbox_pip.get_first_child():
            self.listbox_pip.remove(child)
        
        def thread():
            try:
                # Utiliser le préfixe correct (système ou venv)
                cmd_prefix = self._get_pip_cmd_prefix()
                cmd = cmd_prefix + ["list", "--format=json"]
                
                proc = subprocess.run(cmd, capture_output=True, text=True)
                if proc.returncode == 0:
                    packages = json.loads(proc.stdout)
                    # Trier par nom
                    for pkg in sorted(packages, key=lambda x: x['name'].lower()):
                        row = Gtk.ListBoxRow()
                        b = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                        set_margins(b, 6)
                        
                        lbl_name = Gtk.Label(label=pkg['name'], xalign=0, css_classes=["heading"])
                        lbl_ver = Gtk.Label(label=f"v{pkg['version']}", xalign=0, css_classes=["dim-label"])
                        
                        btn_up = Gtk.Button(label="⬆ Up")
                        btn_up.connect("clicked", lambda _, n=pkg['name']: self._pip_action("install", n))
                        
                        btn_del = Gtk.Button(label="✕")
                        btn_del.add_css_class("destructive-action")
                        btn_del.connect("clicked", lambda _, n=pkg['name']: self._pip_action("uninstall", n))
                        
                        b.append(lbl_name)
                        b.append(lbl_ver)
                        b.append(Gtk.Box(hexpand=True))
                        b.append(btn_up)
                        b.append(btn_del)
                        
                        row.set_child(b)
                        GLib.idle_add(lambda r=row: self.listbox_pip.append(r))
                else:
                    GLib.idle_add(lambda: self.terminal._log(f"❌ Erreur PIP list: {proc.stderr}"))
            except Exception as e:
                GLib.idle_add(lambda: self.terminal._log(f"❌ Exception PIP list: {e}"))
        
        threading.Thread(target=thread, daemon=True).start()

    def _get_pip_cmd_prefix(self):
        """Retourne la commande pip appropriée (système ou venv)"""
        is_venv = self.combo_pip_env.get_active() == 1
        if is_venv and self.get_config().get("venv_path"):
            venv_path = Path(self.get_config()["venv_path"])
            pip_path = venv_path / "bin" / "pip"
            if pip_path.exists():
                return [str(pip_path)]
        return ["pip3"]

    def _pip_action(self, action, package_name=None):
        pkg = package_name or self.entry_pip_pkg.get_text().strip()
        if not pkg: return self.show_toast("❌ Paquet requis")
        
        cmd_prefix = self._get_pip_cmd_prefix()
        dest = self.entry_pip_dest.get_text().strip()
        
        if action == "download":
            os.makedirs(dest, exist_ok=True)
            cmd = cmd_prefix + ["download", "-d", dest, pkg]
        elif action == "install":
            cmd = cmd_prefix + ["install", "--upgrade", pkg]
        else: # uninstall
            cmd = cmd_prefix + ["uninstall", "-y", pkg]
            
        self.terminal._log(f"▶ {' '.join(cmd)}")
        
        def thread():
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True)
                GLib.idle_add(lambda: self.terminal._log(proc.stdout + proc.stderr))
                if proc.returncode == 0:
                    msg = f"✅ PIP {action} réussi"
                    if action == "download": msg += f" dans {dest}"
                    GLib.idle_add(lambda: self.show_toast(msg))
                    if action != "download": GLib.idle_add(self._list_pip_packages)
                else: 
                    GLib.idle_add(lambda: self.show_toast(f"❌ Échec PIP: {proc.stderr[:100]}"))
            except Exception as e: 
                GLib.idle_add(lambda: self.terminal._log(f"❌ {e}"))
        threading.Thread(target=thread, daemon=True).start()

    # Helper générique pour scripts système
    def _run_system_script(self, script, label):
        self.terminal._log(f"▶ {label}...")
        def thread():
            try:
                proc = subprocess.run(script, shell=True, capture_output=True, text=True)
                GLib.idle_add(lambda: self.terminal._log(proc.stdout + proc.stderr))
                if proc.returncode == 0: GLib.idle_add(lambda: self.show_toast(f"✅ {label} réussi"))
                else: GLib.idle_add(lambda: self.show_toast(f"❌ Échec {label}"))
            except Exception as e: GLib.idle_add(lambda: self.terminal._log(f"❌ {e}"))
        threading.Thread(target=thread, daemon=True).start()

    def _browse_folder(self, title, entry):
        Gtk.FileDialog(title=title).select_folder(self.get_root(), None, lambda d, r: self._on_folder_selected_entry(d, r, entry))

    def _on_folder_selected_entry(self, dialog, result, entry):
        try:
            folder = dialog.select_folder_finish(result)
            if folder: entry.set_text(folder.get_path())
        except Exception as e:
            global_log(f"⚠️ Erreur dans gy.py: {type(e).__name__} - {e}")
    # ═══════════════════════════════════════════════════════════════════════
    #  NOUVEAU : GÉNÉRATION SSL AUTOMATIQUE
    # ═══════════════════════════════════════════════════════════════════════
    def _generate_ssl(self, *_):
        cfg = self.get_config()
        
        # On force les chemins vers le dossier système Nginx comme demandé
        cert_path = "/etc/pki/nginx/server.crt"
        key_path = "/etc/pki/nginx/private/server.key"
        
        # Mise à jour de la config pour que Gunicorn utilise aussi ces fichiers s'il est lancé ensuite
        cfg["gunicorn_ssl_cert_path"] = cert_path
        cfg["gunicorn_ssl_key_path"] = key_path
        save_config(cfg)

        self.terminal._log("🔑 Génération du certificat SSL système en cours...")
        
        def _thread():
            try:
                # 1. Création des dossiers systèmes avec SUDO
                GLib.idle_add(self.terminal._log, f"▶ sudo mkdir -p /etc/pki/nginx/private")
                subprocess.run(["sudo", "mkdir", "-p", "/etc/pki/nginx/private"], check=True)
                
                # 2. Génération du certificat directement dans le dossier système
                cmd = f'sudo openssl req -x509 -newkey rsa:4096 -nodes -keyout "{key_path}" -out "{cert_path}" -days 365 -subj "/C=CG/ST=Brazzaville/L=Brazzaville/O=Gykhamine/OU=IT/CN=localhost"'
                
                GLib.idle_add(self.terminal._log, f"📜 Cmd: {cmd}")
                proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if proc.returncode == 0:
                    GLib.idle_add(self.terminal._log, f"✅ Certificat SSL généré avec succès dans /etc/pki/nginx/")
                    GLib.idle_add(self.terminal._log, f"   📄 Certificat : {cert_path}")
                    GLib.idle_add(self.terminal._log, f"   🔑 Clé privée : {key_path}")
                    
                    # Activation automatique du SSL dans la config
                    cfg["gunicorn_ssl_enabled"] = True
                    cfg["nginx_ssl_cert"] = cert_path
                    cfg["nginx_ssl_key"] = key_path
                    save_config(cfg)
                    
                    GLib.idle_add(self.show_toast, "✅ Certificat SSL Système généré")
                    GLib.idle_add(self.terminal._log, "ℹ️ Les chemins Nginx et Gunicorn ont été mis à jour automatiquement.")
                else:
                    GLib.idle_add(self.terminal._log, f"❌ Erreur OpenSSL : {proc.stderr.strip()}")
                    GLib.idle_add(self.show_toast, "❌ Échec de la génération SSL")
                    
            except Exception as e:
                GLib.idle_add(self.terminal._log, f"❌ Exception: {e}")
                GLib.idle_add(self.show_toast, "❌ Erreur lors de la génération")
        
        threading.Thread(target=_thread, daemon=True).start()
    # ═══════════════════════════════════════════════════════════════════════

    # ... (Les méthodes PostgreSQL, Redis, NFS, Nginx, SSH, Venv restent inchangées pour la brièveté, mais sont incluses dans le fichier final) ...
    def _run_pg_initdb(self, *_):
        cfg = self.get_config()
        device = cfg.get("pg_device", "")
        mount_point = cfg.get("pg_mount_point", "/var/lib/pgsql/data")
        
        if not device:
            self.show_toast("❌ Veuillez sélectionner une partition dans les paramètres")
            return

        self.terminal._log("🔧 === Initialisation PostgreSQL (Mode Auto-Sudo) ===")
        self.terminal._log(f"📁 Point de montage: {mount_point}")

        def _thread():
            try:
                # 1. Création du dossier avec SUDO pour éviter les erreurs de permission
                GLib.idle_add(self.terminal._log, f"▶ sudo mkdir -p {mount_point}")
                subprocess.run(["sudo", "mkdir", "-p", mount_point], check=True)
                
                # 2. Vérification du montage
                mount_check = subprocess.run(["mountpoint", "-q", mount_point], capture_output=True)
                if mount_check.returncode != 0:
                    if device:
                        GLib.idle_add(self.terminal._log, f"▶ Montage de {device} sur {mount_point}")
                        subprocess.run(["sudo", "mount", device, mount_point], check=True)
                    else:
                         GLib.idle_add(self.terminal._log, "⚠️ Aucun périphérique sélectionné, utilisation du dossier local.")
                else: 
                    GLib.idle_add(self.terminal._log, "✅ Déjà monté")

                # 3. Initialisation si nécessaire
                pg_version_path = Path(mount_point) / "PG_VERSION"
                if not pg_version_path.exists():
                    GLib.idle_add(self.terminal._log, "▶ Préparation des droits (chown/chmod)...")
                    # Donner les droits à postgres avec SUDO
                    subprocess.run(["sudo", "chown", "-R", "postgres:postgres", mount_point], check=True)
                    subprocess.run(["sudo", "chmod", "700", mount_point], check=True)
                    
                    GLib.idle_add(self.terminal._log, "▶ Initialisation de la base (initdb)...")
                    subprocess.run(["sudo", "-u", "postgres", "initdb", "-D", mount_point], check=True)
                else: 
                    GLib.idle_add(self.terminal._log, "✅ Base de données déjà initialisée")
                    # S'assurer que les droits sont bons même si déjà init
                    subprocess.run(["sudo", "chown", "-R", "postgres:postgres", mount_point], check=True)

                GLib.idle_add(self.terminal._log, "▶ Démarrage de PostgreSQL...")
                status = subprocess.run(["sudo", "-u", "postgres", "pg_ctl", "-D", mount_point, "status"], capture_output=True)
                if status.returncode != 0:
                    subprocess.run(["sudo", "-u", "postgres", "pg_ctl", "-D", mount_point, "start"], check=True)
                    GLib.idle_add(self.terminal._log, "✅ PostgreSQL démarré")
                else: 
                    GLib.idle_add(self.terminal._log, "✅ PostgreSQL déjà en cours d'exécution")
                
                GLib.idle_add(self.show_toast, "✅ Initialisation PostgreSQL réussie")
                GLib.idle_add(self.terminal._log, "=== OK ===")
                
            except subprocess.CalledProcessError as e:
                GLib.idle_add(self.terminal._log, f"❌ Erreur lors de l'exécution: {e}")
                GLib.idle_add(self.terminal._log, "💡 Astuce: Assurez-vous que votre utilisateur a les droits sudo.")
                GLib.idle_add(self.show_toast, "❌ Échec de l'initialisation (Vérifiez sudo)")
            except Exception as e:
                GLib.idle_add(self.terminal._log, f"❌ Exception: {e}")
        
        threading.Thread(target=_thread, daemon=True).start()
        
    def _run_pg_creatdb(self, *_):
        cfg = self.get_config()
        db_name = cfg.get("pg_db_name", "ma_base")
        db_user = cfg.get("pg_db_user", "mon_user")
        db_password = cfg.get("pg_db_password", "mot_de_passe").replace("'", "''")
        self.terminal._log("➕ === Création Base & Utilisateur ===")
        
        def _thread():
            try:
                # Vérification utilisateur avec SUDO
                check_user = subprocess.run(["sudo", "-u", "postgres", "psql", "-tAc", f"SELECT 1 FROM pg_roles WHERE rolname='{db_user}'"], capture_output=True, text=True).stdout.strip()
                
                if check_user != "1":
                    GLib.idle_add(self.terminal._log, f"▶ Création de l'utilisateur {db_user}")
                    subprocess.run(["sudo", "-u", "postgres", "psql", "-c", f"CREATE USER {db_user} WITH PASSWORD '{db_password}';"], check=True)
                else: 
                    GLib.idle_add(self.terminal._log, "✅ Utilisateur déjà existant")

                # Vérification base avec SUDO
                check_db = subprocess.run(["sudo", "-u", "postgres", "psql", "-tAc", f"SELECT 1 FROM pg_database WHERE datname='{db_name}'"], capture_output=True, text=True).stdout.strip()
                
                if check_db != "1":
                    GLib.idle_add(self.terminal._log, f"▶ Création de la base {db_name}")
                    subprocess.run(["sudo", "-u", "postgres", "createdb", "-O", db_user, db_name], check=True)
                else: 
                    GLib.idle_add(self.terminal._log, "✅ Base déjà existante")

                GLib.idle_add(self.terminal._log, "▶ Attribution des privilèges...")
                subprocess.run(["sudo", "-u", "postgres", "psql", "-c", f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};"], check=True)
                subprocess.run(["sudo", "-u", "postgres", "psql", "-d", db_name, "-c", f"GRANT USAGE, CREATE ON SCHEMA public TO {db_user};"], check=True)
                subprocess.run(["sudo", "-u", "postgres", "psql", "-d", db_name, "-c", f"ALTER SCHEMA public OWNER TO {db_user};"], check=True)
                
                GLib.idle_add(self.show_toast, "✅ Base et utilisateur configurés")
                GLib.idle_add(self.terminal._log, "=== OK ===")
                
            except subprocess.CalledProcessError as e:
                GLib.idle_add(self.terminal._log, f"❌ Erreur SQL: {e}")
                GLib.idle_add(self.show_toast, "❌ Échec de la création")
            except Exception as e:
                GLib.idle_add(self.terminal._log, f"❌ Exception: {e}")
        
        threading.Thread(target=_thread, daemon=True).start()




    def _run_pg_rundb(self, *_):
        cfg = self.get_config()
        device = cfg.get("pg_device", "")
        pgdata = cfg.get("pg_mount_point", "/var/lib/pgsql/data")
        bind_ip = cfg.get("pg_bind_ip", "127.0.0.1")
        listen_addr = "*" if bind_ip == "0.0.0.0" else bind_ip
        
        if not device:
            self.show_toast("❌ Veuillez sélectionner une partition dans les paramètres")
            return

        self.terminal._log("🚀 === Démarrage et Configuration IP ===")
        
        def _thread():
            try:
                # 1. Création du dossier avec SUDO (Correction du bug mkdir)
                GLib.idle_add(self.terminal._log, f"▶ sudo mkdir -p {pgdata}")
                subprocess.run(["sudo", "mkdir", "-p", pgdata], check=True)
                
                # 2. Montage
                mount_check = subprocess.run(["mountpoint", "-q", pgdata], capture_output=True)
                if mount_check.returncode != 0:
                    GLib.idle_add(self.terminal._log, f"▶ Montage de {device} sur {pgdata}")
                    subprocess.run(["sudo", "mount", device, pgdata], check=True)
                else:
                    GLib.idle_add(self.terminal._log, "✅ Déjà monté")

                # 3. Démarrage PostgreSQL
                status = subprocess.run(["sudo", "-u", "postgres", "pg_ctl", "-D", pgdata, "status"], capture_output=True)
                is_running = (status.returncode == 0)
                
                if not is_running:
                    GLib.idle_add(self.terminal._log, "▶ Démarrage de PostgreSQL...")
                    subprocess.run(["sudo", "-u", "postgres", "pg_ctl", "-D", pgdata, "start"], check=True)
                else:
                    GLib.idle_add(self.terminal._log, "✅ PostgreSQL déjà en cours d'exécution")

                # 4. Configuration IP
                GLib.idle_add(self.terminal._log, f"▶ Configuration de listen_addresses sur '{listen_addr}'...")
                subprocess.run(["sudo", "-u", "postgres", "psql", "-c", f"ALTER SYSTEM SET listen_addresses = '{listen_addr}';"], check=True)
                
                if bind_ip == "0.0.0.0":
                    pg_hba_path = Path(pgdata) / "pg_hba.conf"
                    GLib.idle_add(self.terminal._log, "🌐 Mode Réseau détecté. Automatisation de pg_hba.conf...")
                    
                    # Lecture et modification sécurisée via sudo tee
                    hba_content = subprocess.run(["sudo", "cat", str(pg_hba_path)], capture_output=True, text=True).stdout
                    
                    if "0.0.0.0/0" not in hba_content:
                        GLib.idle_add(self.terminal._log, "▶ Ajout de la règle d'accès distant dans pg_hba.conf...")
                        rule = "\n# --- Ajouté automatiquement par Gykhamine Studio ---\nhost    all             all             0.0.0.0/0               scram-sha-256\n"
                        subprocess.run(["sudo", "tee", "-a", str(pg_hba_path)], input=rule, text=True, check=True)
                        GLib.idle_add(self.terminal._log, "✅ Règle pg_hba.conf ajoutée avec succès.")
                    else:
                        GLib.idle_add(self.terminal._log, "✅ La règle d'accès distant est déjà présente dans pg_hba.conf.")
                    
                    GLib.idle_add(self.terminal._log, "▶ Redémarrage propre pour appliquer la configuration...")
                    subprocess.run(["sudo", "-u", "postgres", "pg_ctl", "-D", pgdata, "restart", "-m", "fast"], check=True)
                
                GLib.idle_add(self.show_toast, "✅ PostgreSQL démarré et IP configurée")
                GLib.idle_add(self.terminal._log, "=== READY ===")
                GLib.idle_add(self._set_dot, "postgresql", True)
                
            except subprocess.CalledProcessError as e:
                GLib.idle_add(self.terminal._log, f"❌ Erreur: {e}")
                GLib.idle_add(self.show_toast, "❌ Échec du démarrage/config")
            except Exception as e:
                GLib.idle_add(self.terminal._log, f"❌ Exception: {e}")
        
        threading.Thread(target=_thread, daemon=True).start()
        
    def _run_pg_stopdb(self, *_):
        cfg = self.get_config()
        pgdata = cfg.get("pg_mount_point", "/var/lib/pgsql/data")
        self.terminal._log("🛑 === Arrêt de PostgreSQL ===")
        def _thread():
            try:
                GLib.idle_add(self.terminal._log, "▶ Arrêt propre de PostgreSQL (mode fast)...")
                subprocess.run(["sudo", "-u", "postgres", "pg_ctl", "-D", pgdata, "stop", "-m", "fast"], check=True)
                GLib.idle_add(self.show_toast, "✅ PostgreSQL arrêté avec succès")
                GLib.idle_add(self.terminal._log, "=== STOPPED ===")
                GLib.idle_add(self._set_dot, "postgresql", False)
            except subprocess.CalledProcessError as e:
                GLib.idle_add(self.terminal._log, f"❌ Erreur lors de l'arrêt: {e}")
                GLib.idle_add(self.show_toast, "❌ Échec de l'arrêt")
            except Exception as e:
                GLib.idle_add(self.terminal._log, f"❌ Exception: {e}")
        threading.Thread(target=_thread, daemon=True).start()

    def _run_redis_start(self, *_):
        cfg = self.get_config()
        redis_ip = cfg.get("redis_ip", "127.0.0.1")
        redis_port = cfg.get("redis_port", 6379)
        data_dir = cfg.get("redis_data_dir", str(Path.home() / "redis_data"))
        use_persistence = cfg.get("redis_use_persistence", True)
        
        # Note: Les variables env_path et update_env ne sont plus utilisées pour la modification
        # mais on les garde si vous voulez juste les afficher dans les logs ou pour d'autres usages futurs
        env_path = cfg.get("redis_env_path", "")
        
        self.terminal._log("🔴 === Démarrage de Redis ===")
        
        def _thread():
            try:
                # --- DÉBUT DE LA SUPPRESSION ---
                # Tout le bloc 'if update_env and env_path...' a été retiré ici.
                # Redis démarrera simplement avec les paramètres fournis.
                # --- FIN DE LA SUPPRESSION ---

                if use_persistence:
                    os.makedirs(data_dir, exist_ok=True)
                    cmd = f"redis-server --bind {redis_ip} --port {redis_port} --dir {data_dir} --appendonly yes --daemonize yes"
                else:
                    cmd = f"redis-server --bind {redis_ip} --port {redis_port} --daemonize yes"
                
                GLib.idle_add(self.terminal._log, f"▶ Exécution : {cmd}")
                status = os.system(cmd)
                
                if status == 0:
                    GLib.idle_add(self._set_dot, "redis", True)
                    GLib.idle_add(self.show_toast, "✅ Redis démarré")
                    GLib.idle_add(self.terminal._log, f"=== READY : {redis_ip}:{redis_port} ===")
                else:
                    GLib.idle_add(self._set_dot, "redis", False)
                    GLib.idle_add(self.show_toast, "❌ Échec du démarrage Redis")
                    GLib.idle_add(self.terminal._log, "❌ Impossible de démarrer le serveur Redis.")
            except Exception as e:
                GLib.idle_add(self._set_dot, "redis", False)
                GLib.idle_add(self.terminal._log, f"❌ Exception: {e}")
        
        threading.Thread(target=_thread, daemon=True).start()

    def _run_redis_stop(self, *_):
        cfg = self.get_config()
        redis_ip = cfg.get("redis_ip", "127.0.0.1")
        # Correction : S'assurer que le port est une chaîne de caractères
        redis_port = str(cfg.get("redis_port", 6379)) 
        self.terminal._log("🛑 === Arrêt de Redis ===")
        def _thread():
            try:
                GLib.idle_add(self.terminal._log, f"▶ Arrêt de Redis sur {redis_ip}:{redis_port}...")
                # Utilisation explicite de strings pour tous les arguments
                subprocess.run(["redis-cli", "-h", str(redis_ip), "-p", str(redis_port), "shutdown", "nosave"], capture_output=True)
                subprocess.run(["pkill", "-f", "redis-server"], capture_output=True)
                GLib.idle_add(self._set_dot, "redis", False)
                GLib.idle_add(self.show_toast, "✅ Redis arrêté")
                GLib.idle_add(self.terminal._log, "=== STOPPED ===")
            except Exception as e:
                GLib.idle_add(self.terminal._log, f"❌ Exception: {e}")
        threading.Thread(target=_thread, daemon=True).start()
        
    def _run_nfs_server_start(self, *_):
        cfg = self.get_config()
        export_dir = cfg.get("nfs_export_dir", "/run/media/gykhamine/GY/gy/media")
        mode = cfg.get("nfs_server_mode", "local")
        lan_network = cfg.get("nfs_lan_network", "192.168.1.0/24") if mode == "network" else "127.0.0.1"
        
        self.terminal._log("📁 === Démarrage du Serveur NFS ===")
        
        def _thread():
            try:
                GLib.idle_add(self.terminal._log, f"▶ Vérification/Création du dossier d'export : {export_dir}")
                # Création du dossier (si possible)
                try:
                    os.makedirs(export_dir, exist_ok=True)
                except Exception as e:
                    GLib.idle_add(self.terminal._log, f"⚠️ Impossible de créer le dossier automatiquement : {e}")
                
                # Tentative de chmod, mais on ignore l'erreur si c'est un système de fichiers non-Linux (NTFS/exFAT)
                try:
                    subprocess.run(["chmod", "777", export_dir], check=True)
                except subprocess.CalledProcessError:
                    GLib.idle_add(self.terminal._log, "⚠️ chmod ignoré (support non-Linux ou permissions restreintes).")
                
                GLib.idle_add(self.terminal._log, "▶ Mise à jour de /etc/exports...")
                exports_path = "/etc/exports"
                try:
                    with open(exports_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                except FileNotFoundError:
                    lines = []
                
                # Nettoyer les anciennes entrées Gykhamine
                lines = [l for l in lines if not l.strip().startswith("# --- Gykhamine NFS ---") and not l.strip().startswith(export_dir)]
                
                new_entry = f"# --- Gykhamine NFS ---\n{export_dir} {lan_network}(rw,sync,no_subtree_check,no_root_squash)\n"
                lines.append(new_entry)
                content = "".join(lines)
                
                # Écriture avec SUDO
                proc = subprocess.run(["sudo", "tee", exports_path], input=content, text=True, capture_output=True)
                if proc.returncode != 0:
                    raise Exception(f"Erreur sudo tee: {proc.stderr}")

                GLib.idle_add(self.terminal._log, "▶ Application de la configuration (exportfs -ra)...")
                subprocess.run(["sudo", "exportfs", "-ra"], check=True)
                
                GLib.idle_add(self.terminal._log, "▶ Redémarrage du service nfs-server...")
                subprocess.run(["sudo", "systemctl", "restart", "nfs-server.service"], check=True)
                
                GLib.idle_add(self._set_dot, "nfs_server", True)
                GLib.idle_add(self.show_toast, "✅ Serveur NFS démarré")
                GLib.idle_add(self.terminal._log, f"=== READY : Export {export_dir} vers {lan_network} ===")
                
            except subprocess.CalledProcessError as e:
                GLib.idle_add(self._set_dot, "nfs_server", False)
                GLib.idle_add(self.terminal._log, f"❌ Erreur: {e}")
                GLib.idle_add(self.show_toast, "❌ Échec du démarrage NFS (Vérifiez sudo)")
            except Exception as e:
                GLib.idle_add(self._set_dot, "nfs_server", False)
                GLib.idle_add(self.terminal._log, f"❌ Exception: {e}")
        
        threading.Thread(target=_thread, daemon=True).start()
    def _run_nfs_server_stop(self, *_):
        cfg = self.get_config()
        export_dir = cfg.get("nfs_export_dir", "/run/media/gykhamine/GY/gy/media")
        self.terminal._log("🛑 === Arrêt du Serveur NFS ===")
        def _thread():
            try:
                exports_path = "/etc/exports"
                try:
                    with open(exports_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    lines = [l for l in lines if not l.strip().startswith("# --- Gykhamine NFS ---") and not l.strip().startswith(export_dir)]
                    content = "".join(lines)
                    subprocess.run(["sudo", "tee", exports_path], input=content, text=True, check=True)
                except Exception as e:
                    global_log(f"⚠️ Erreur dans gy.py: {type(e).__name__} - {e}")
                subprocess.run(["sudo", "exportfs", "-ra"], check=True)
                subprocess.run(["sudo", "systemctl", "stop", "nfs-server.service"], check=True)
                GLib.idle_add(self._set_dot, "nfs_server", False)
                GLib.idle_add(self.show_toast, "✅ Serveur NFS arrêté")
                GLib.idle_add(self.terminal._log, "=== STOPPED ===")
            except Exception as e:
                GLib.idle_add(self.terminal._log, f"❌ Exception: {e}")
        threading.Thread(target=_thread, daemon=True).start()

    def _run_nfs_client_mount(self, *_):
        cfg = self.get_config()
        server_ip = cfg.get("nfs_client_server_ip", "192.168.1.10")
        export_dir = cfg.get("nfs_client_export_dir", "/srv/nfs")
        mount_point = cfg.get("nfs_client_mount_point", str(Path.home() / "nfs_mount"))
        self.terminal._log("💻 === Montage Client NFS ===")
        def _thread():
            try:
                subprocess.run(["mkdir", "-p", mount_point], check=True)
                GLib.idle_add(self.terminal._log, f"▶ Test de reachabilité du serveur {server_ip}...")
                ping = subprocess.run(["ping", "-c", "1", "-W", "2", server_ip], capture_output=True)
                if ping.returncode != 0:
                    GLib.idle_add(self.terminal._log, "❌ Serveur inaccessible, fallback local ou vérifiez l'IP.")
                    GLib.idle_add(self.show_toast, "❌ Serveur NFS injoignable")
                    return
                GLib.idle_add(self.terminal._log, f"▶ Montage de {server_ip}:{export_dir} sur {mount_point}...")
                subprocess.run(["sudo", "mount", "-t", "nfs", f"{server_ip}:{export_dir}", mount_point], check=True)
                GLib.idle_add(self._set_dot, "nfs_client", True)
                GLib.idle_add(self.show_toast, "✅ Partage NFS monté")
                GLib.idle_add(self.terminal._log, f"=== MOUNTED : {mount_point} ===")
            except subprocess.CalledProcessError as e:
                GLib.idle_add(self._set_dot, "nfs_client", False)
                GLib.idle_add(self.terminal._log, f"❌ Erreur de montage: {e}")
                GLib.idle_add(self.show_toast, "❌ Échec du montage NFS")
            except Exception as e:
                GLib.idle_add(self._set_dot, "nfs_client", False)
                GLib.idle_add(self.terminal._log, f"❌ Exception: {e}")
        threading.Thread(target=_thread, daemon=True).start()

    def _run_nfs_client_umount(self, *_):
        cfg = self.get_config()
        mount_point = cfg.get("nfs_client_mount_point", str(Path.home() / "nfs_mount"))
        self.terminal._log("📤 === Démontage Client NFS ===")
        def _thread():
            try:
                subprocess.run(["sudo", "umount", "-l", mount_point], check=True)
                GLib.idle_add(self._set_dot, "nfs_client", False)
                GLib.idle_add(self.show_toast, "✅ Partage NFS démonté")
                GLib.idle_add(self.terminal._log, "=== UNMOUNTED ===")
            except subprocess.CalledProcessError as e:
                GLib.idle_add(self.terminal._log, f"❌ Erreur de démontage: {e}")
                GLib.idle_add(self.show_toast, "❌ Échec du démontage")
            except Exception as e:
                GLib.idle_add(self.terminal._log, f"❌ Exception: {e}")
        threading.Thread(target=_thread, daemon=True).start()

    def _show_nginx_config_dialog(self, *_):
        cfg = self.get_config()
        dialog = Gtk.Dialog(title="⚙ Configuration Avancée Nginx", transient_for=self.get_root())
        dialog.add_css_class("rounded-dialog")
        dialog.set_default_size(600, 700)
        content = dialog.get_content_area()
        content.set_spacing(10)
        set_margins(content, 16)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(8)
        row = 0
        lbl_sec1 = Gtk.Label(label="🌐 Configuration Générale", css_classes=["control-section-title"], xalign=0, margin_bottom=4)
        grid.attach(lbl_sec1, 0, row, 2, 1); row += 1
        grid.attach(Gtk.Label(label="Mode :", xalign=0), 0, row, 1, 1)
        combo_mode = Gtk.ComboBoxText()
        combo_mode.append_text("Reverse Proxy (Simple)")
        combo_mode.append_text("Load Balancer (Répartition de charge)")
        combo_mode.set_active(0 if cfg.get("nginx_mode") == "reverse_proxy" else 1)
        grid.attach(combo_mode, 1, row, 1, 1); row += 1
        grid.attach(Gtk.Label(label="Nom de domaine (server_name) :", xalign=0), 0, row, 1, 1)
        entry_name = Gtk.Entry(); entry_name.set_text(cfg.get("nginx_server_name", "localhost")); grid.attach(entry_name, 1, row, 1, 1); row += 1
        grid.attach(Gtk.Label(label="Port d'écoute HTTPS :", xalign=0), 0, row, 1, 1)
        entry_port = Gtk.Entry(); entry_port.set_text(cfg.get("nginx_listen_port", "443")); grid.attach(entry_port, 1, row, 1, 1); row += 1
        row_force = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row_force.append(Gtk.Label(label="Forcer HTTPS (Redirect 80 -> 443) :", xalign=0))
        sw_force = Gtk.Switch(); sw_force.set_active(cfg.get("nginx_force_https", True)); row_force.append(sw_force)
        grid.attach(row_force, 0, row, 2, 1); row += 1
        lbl_sec2 = Gtk.Label(label="🔀 Backend & Redirections", css_classes=["control-section-title"], xalign=0, margin_top=8, margin_bottom=4)
        grid.attach(lbl_sec2, 0, row, 2, 1); row += 1
        grid.attach(Gtk.Label(label="Serveurs Backend (séparés par virgule) :", xalign=0), 0, row, 1, 1)
        entry_upstream = Gtk.Entry(); entry_upstream.set_text(cfg.get("nginx_upstream_servers", "127.0.0.1:8000, 127.0.0.1:8001"))
        entry_upstream.set_tooltip_text("Ex: 127.0.0.1:8000, 127.0.0.1:8001")
        grid.attach(entry_upstream, 1, row, 1, 1); row += 1
        grid.attach(Gtk.Label(label="URL de redirection (proxy_pass) :", xalign=0), 0, row, 1, 1)
        entry_proxy = Gtk.Entry(); entry_proxy.set_text(cfg.get("nginx_proxy_pass", "http://gunicorn")); grid.attach(entry_proxy, 1, row, 1, 1); row += 1
        grid.attach(Gtk.Label(label="Redirections personnalisées (une par ligne : /ancien -> /nouveau) :", xalign=0), 0, row, 2, 1); row += 1
        txt_redirects = Gtk.TextView(); txt_redirects.set_wrap_mode(Gtk.WrapMode.WORD)
        txt_redirects.get_buffer().set_text(cfg.get("nginx_custom_redirects", ""))
        scroll_redirects = Gtk.ScrolledWindow(); scroll_redirects.set_size_request(-1, 60); scroll_redirects.set_child(txt_redirects)
        grid.attach(scroll_redirects, 0, row, 2, 1); row += 1
        lbl_sec3 = Gtk.Label(label="📁 Liaison Django (Static & Media)", css_classes=["control-section-title"], xalign=0, margin_top=8, margin_bottom=4)
        grid.attach(lbl_sec3, 0, row, 2, 1); row += 1
        grid.attach(Gtk.Label(label="URL Static :", xalign=0), 0, row, 1, 1)
        entry_s_url = Gtk.Entry(); entry_s_url.set_text(cfg.get("nginx_static_url", "/static/")); grid.attach(entry_s_url, 1, row, 1, 1); row += 1
        grid.attach(Gtk.Label(label="Chemin local Static :", xalign=0), 0, row, 1, 1)
        entry_s_path = Gtk.Entry(); entry_s_path.set_text(cfg.get("nginx_static_path", "/chemin/vers/ton/projet/static/")); grid.attach(entry_s_path, 1, row, 1, 1); row += 1
        grid.attach(Gtk.Label(label="URL Media :", xalign=0), 0, row, 1, 1)
        entry_m_url = Gtk.Entry(); entry_m_url.set_text(cfg.get("nginx_media_url", "/media/")); grid.attach(entry_m_url, 1, row, 1, 1); row += 1
        grid.attach(Gtk.Label(label="Chemin local Media :", xalign=0), 0, row, 1, 1)
        entry_m_path = Gtk.Entry(); entry_m_path.set_text(cfg.get("nginx_media_path", "/chemin/vers/ton/projet/media/")); grid.attach(entry_m_path, 1, row, 1, 1); row += 1
        lbl_sec4 = Gtk.Label(label="🔒 SSL & Sécurité", css_classes=["control-section-title"], xalign=0, margin_top=8, margin_bottom=4)
        grid.attach(lbl_sec4, 0, row, 2, 1); row += 1
        grid.attach(Gtk.Label(label="Certificat SSL (.crt) :", xalign=0), 0, row, 1, 1)
        entry_cert = Gtk.Entry(); entry_cert.set_text(cfg.get("nginx_ssl_cert", "/etc/pki/nginx/server.crt")); entry_cert.set_editable(False); entry_cert.add_css_class("dim-label"); grid.attach(entry_cert, 1, row, 1, 1); row += 1
        grid.attach(Gtk.Label(label="Clé Privée SSL (.key) :", xalign=0), 0, row, 1, 1)
        entry_key = Gtk.Entry(); entry_key.set_text(cfg.get("nginx_ssl_key", "/etc/pki/nginx/private/server.key")); entry_key.set_editable(False); entry_key.add_css_class("dim-label"); grid.attach(entry_key, 1, row, 1, 1); row += 1
        row_sec = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        sw_headers = Gtk.Switch(); sw_headers.set_active(cfg.get("nginx_security_headers", True))
        row_sec.append(Gtk.Label(label="En-têtes de sécurité (HSTS, X-Frame, etc.) :")); row_sec.append(sw_headers)
        sw_buffer = Gtk.Switch(); sw_buffer.set_active(cfg.get("nginx_proxy_buffering", True))
        row_sec.append(Gtk.Label(label="Proxy Buffering :")); row_sec.append(sw_buffer)
        grid.attach(row_sec, 0, row, 2, 1); row += 1
        lbl_sec5 = Gtk.Label(label="⚡ Performances & Timeouts", css_classes=["control-section-title"], xalign=0, margin_top=8, margin_bottom=4)
        grid.attach(lbl_sec5, 0, row, 2, 1); row += 1
        grid.attach(Gtk.Label(label="Taille max upload (client_max_body_size) :", xalign=0), 0, row, 1, 1)
        entry_max_body = Gtk.Entry(); entry_max_body.set_text(cfg.get("nginx_max_body", "20M")); grid.attach(entry_max_body, 1, row, 1, 1); row += 1
        grid.attach(Gtk.Label(label="Délai de connexion (proxy_connect_timeout) :", xalign=0), 0, row, 1, 1)
        entry_conn_to = Gtk.Entry(); entry_conn_to.set_text(cfg.get("nginx_connect_timeout", "60s")); grid.attach(entry_conn_to, 1, row, 1, 1); row += 1
        grid.attach(Gtk.Label(label="Délai de lecture (proxy_read_timeout) :", xalign=0), 0, row, 1, 1)
        entry_read_to = Gtk.Entry(); entry_read_to.set_text(cfg.get("nginx_read_timeout", "60s")); grid.attach(entry_read_to, 1, row, 1, 1); row += 1
        scroll.set_child(grid)
        content.append(scroll)
        info_lbl = Gtk.Label(label="⚠️ Le fichier /etc/nginx/nginx.conf sera modifié directement. Assurez-vous que Nginx est installé.", css_classes=["dim-label"], margin_top=8, xalign=0)
        content.append(info_lbl)
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.END, margin_top=12)
        btn_cancel = Gtk.Button(label="Annuler")
        btn_save = Gtk.Button(label="💾 Sauvegarder & Appliquer", css_classes=["suggested-action"])
        btn_box.append(btn_cancel); btn_box.append(btn_save); content.append(btn_box)
        def on_save(*_):
            mode = "reverse_proxy" if combo_mode.get_active() == 0 else "load_balancer"
            new_cfg = {
                "nginx_mode": mode, "nginx_server_name": entry_name.get_text().strip(), "nginx_listen_port": entry_port.get_text().strip(),
                "nginx_force_https": sw_force.get_active(), "nginx_upstream_servers": entry_upstream.get_text().strip(),
                "nginx_proxy_pass": entry_proxy.get_text().strip(),
                "nginx_custom_redirects": txt_redirects.get_buffer().get_text(txt_redirects.get_buffer().get_start_iter(), txt_redirects.get_buffer().get_end_iter(), True).strip(),
                "nginx_static_url": entry_s_url.get_text().strip(), "nginx_static_path": entry_s_path.get_text().strip(),
                "nginx_media_url": entry_m_url.get_text().strip(), "nginx_media_path": entry_m_path.get_text().strip(),
                "nginx_ssl_cert": entry_cert.get_text().strip(), "nginx_ssl_key": entry_key.get_text().strip(),
                "nginx_security_headers": sw_headers.get_active(), "nginx_proxy_buffering": sw_buffer.get_active(),
                "nginx_max_body": entry_max_body.get_text().strip(), "nginx_connect_timeout": entry_conn_to.get_text().strip(),
                "nginx_read_timeout": entry_read_to.get_text().strip(),
            }
            cfg.update(new_cfg)
            save_config(cfg)
            self._update_nginx_conf()
            self.show_toast("✅ Configuration Nginx sauvegardée et appliquée")
            dialog.destroy()
        btn_save.connect("clicked", on_save)
        btn_cancel.connect("clicked", lambda *_: dialog.destroy())
        dialog.present()

    def _update_nginx_conf(self, *_):
        cfg = self.get_config()
        conf_path = cfg.get("nginx_conf_path", "/etc/nginx/nginx.conf")
        try:
            with open(conf_path, 'r', encoding='utf-8') as f: content = f.read()
            servers_list = [f"    server {s.strip()};" for s in cfg.get("nginx_upstream_servers", "127.0.0.1:8000").split(",") if s.strip()]
            upstream_content = "\n".join(servers_list)
            upstream_name = cfg.get("nginx_upstream_name", "gunicorn")
            if re.search(rf'upstream\s+{upstream_name}\s*\{{', content):
                content = re.sub(rf'(upstream\s+{upstream_name}\s*\{{)(.*?)(\}})', rf'\1\n{upstream_content}\n\3', content, flags=re.DOTALL)
            else:
                upstream_block = f"upstream {upstream_name} {{\nleast_conn;\n{upstream_content}\nkeepalive 32;\n}}\n"
                content = re.sub(r'(\s*# --- Redirection HTTP vers HTTPS ---\s*server\s*\{{)', rf'{upstream_block}\1', content, count=1)
            content = re.sub(r'server_name\s+[^;]+;', f'server_name  {cfg.get("nginx_server_name", "localhost")};', content)
            force_https = cfg.get("nginx_force_https", True)
            listen_port = cfg.get("nginx_listen_port", "443")
            if force_https:
                http_redirect = f"""# --- Redirection HTTP vers HTTPS ---
server {{
listen       80;
server_name  {cfg.get('nginx_server_name', 'localhost')};
return 301 https://$host$request_uri;
}}"""
                content = re.sub(r'# --- Redirection HTTP vers HTTPS ---\s*server\s*\{{[^}}]+\}}', http_redirect, content, flags=re.DOTALL)
            else:
                http_block = f"""# --- Redirection HTTP vers HTTPS ---
server {{
listen       80;
server_name  {cfg.get('nginx_server_name', 'localhost')};
}}"""
                content = re.sub(r'# --- Redirection HTTP vers HTTPS ---\s*server\s*\{{[^}}]+\}}', http_block, content, flags=re.DOTALL)
            content = re.sub(r'listen\s+443\s+ssl\s+http2;', f'listen       {listen_port} ssl http2;', content)
            ssl_cert = cfg.get("nginx_ssl_cert", "/etc/pki/nginx/server.crt")
            ssl_key = cfg.get("nginx_ssl_key", "/etc/pki/nginx/private/server.key")
            content = re.sub(r'ssl_certificate\s+[^;]+;', f'ssl_certificate  "{ssl_cert}";', content)
            content = re.sub(r'ssl_certificate_key\s+[^;]+;', f'ssl_certificate_key  "{ssl_key}";', content)
            static_url = cfg.get("nginx_static_url", "/static/")
            static_path = cfg.get("nginx_static_path", "/chemin/vers/ton/projet/static/")
            content = re.sub(r'# --- Fichiers Statiques ---\s*location\s+/static/\s*\{{.*?\n\s*\}}', f"""# --- Fichiers Statiques ---
location {static_url} {{
alias {static_path};
expires 30d;
add_header Cache-Control "public, no-transform";
access_log off;
}}""", content, flags=re.DOTALL)
            media_url = cfg.get("nginx_media_url", "/media/")
            media_path = cfg.get("nginx_media_path", "/chemin/vers/ton/projet/media/")
            content = re.sub(r'# --- Fichiers Media \(Sécurisés\) ---\s*location\s+/media/\s*\{{.*?\n\s*\}}', f"""# --- Fichiers Media (Sécurisés) ---
location {media_url} {{
alias {media_path};
location ~* \\.(php|py|pl|sh|cgi|exe)$ {{
deny all;
}}
}}""", content, flags=re.DOTALL)
            proxy_pass_url = cfg.get("nginx_proxy_pass", f"http://{upstream_name}")
            max_body = cfg.get("nginx_max_body", "20M")
            read_timeout = cfg.get("nginx_read_timeout", "60s")
            connect_timeout = cfg.get("nginx_connect_timeout", "60s")
            proxy_buffering = "on" if cfg.get("nginx_proxy_buffering", True) else "off"
            new_location = f"""# --- Proxy vers Gunicorn ---
location / {{
proxy_pass {proxy_pass_url};
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_connect_timeout {connect_timeout};
proxy_read_timeout {read_timeout};
proxy_buffering {proxy_buffering};
client_max_body_size {max_body};
}}"""
            content = re.sub(r'# --- Proxy vers Gunicorn ---\s*location\s+/\s*\{{.*?\n\s*\}}', new_location, content, flags=re.DOTALL)
            if not cfg.get("nginx_security_headers", True): content = re.sub(r'^\s*add_header\s+[^;]+;\s*$', '', content, flags=re.MULTILINE)
            custom_redirects = cfg.get("nginx_custom_redirects", "")
            if custom_redirects.strip():
                redirect_lines = []
                for r in custom_redirects.split('\n'):
                    if '->' in r:
                        parts = r.split('->')
                        redirect_lines.append(f"    rewrite ^{parts[0].strip()}$ {parts[1].strip()} permanent;")
                if redirect_lines:
                    redirect_block = "\n".join(redirect_lines) + "\n"
                    content = re.sub(r'(# --- Proxy vers Gunicorn ---)', f'{redirect_block}\n\1', content)
            self.terminal._log("📝 Mise à jour de /etc/nginx/nginx.conf...")
            proc = subprocess.run(["sudo", "tee", conf_path], input=content, text=True, capture_output=True)
            if proc.returncode == 0: self.terminal._log("✅ Fichier nginx.conf mis à jour avec succès.")
            else: self.terminal._log(f"❌ Erreur lors de l'écriture : {proc.stderr}")
        except Exception as e:
            self.terminal._log(f"❌ Exception lors de la modification de nginx.conf : {e}")
            self.show_toast("❌ Échec de la modification de nginx.conf")

    def _run_nginx_start(self, *_):
        self.terminal._log("🌐 === Démarrage de Nginx ===")
        def _thread():
            try:
                self._update_nginx_conf()
                self.terminal._log("▶ sudo systemctl start nginx")
                subprocess.run(["sudo", "systemctl", "start", "nginx"], check=True)
                GLib.idle_add(self._set_dot, "nginx", True)
                GLib.idle_add(self.show_toast, "✅ Nginx démarré")
                GLib.idle_add(self.terminal._log, "=== Nginx READY ===")
            except subprocess.CalledProcessError as e:
                GLib.idle_add(self._set_dot, "nginx", False)
                GLib.idle_add(self.terminal._log, f"❌ Erreur systemctl: {e}")
                GLib.idle_add(self.show_toast, "❌ Échec du démarrage Nginx")
            except Exception as e:
                GLib.idle_add(self._set_dot, "nginx", False)
                GLib.idle_add(self.terminal._log, f"❌ Exception: {e}")
        threading.Thread(target=_thread, daemon=True).start()

    def _run_nginx_stop(self, *_):
        self.terminal._log("🛑 === Arrêt de Nginx ===")
        def _thread():
            try:
                subprocess.run(["sudo", "systemctl", "stop", "nginx"], check=True)
                GLib.idle_add(self._set_dot, "nginx", False)
                GLib.idle_add(self.show_toast, "✅ Nginx arrêté")
                GLib.idle_add(self.terminal._log, "=== Nginx STOPPED ===")
            except Exception as e:
                GLib.idle_add(self.terminal._log, f"❌ Exception: {e}")
        threading.Thread(target=_thread, daemon=True).start()

    def _run_nginx_restart(self, *_):
        self.terminal._log("🔄 === Redémarrage de Nginx ===")
        def _thread():
            try:
                self._update_nginx_conf()
                subprocess.run(["sudo", "systemctl", "restart", "nginx"], check=True)
                GLib.idle_add(self._set_dot, "nginx", True)
                GLib.idle_add(self.show_toast, "✅ Nginx redémarré")
                GLib.idle_add(self.terminal._log, "=== Nginx RESTARTED ===")
            except Exception as e:
                GLib.idle_add(self._set_dot, "nginx", False)
                GLib.idle_add(self.terminal._log, f"❌ Exception: {e}")
                GLib.idle_add(self.show_toast, "❌ Échec du redémarrage")
        threading.Thread(target=_thread, daemon=True).start()

    def _show_ssh_config_dialog(self, *_):
        cfg = self.get_config()
        dialog = Gtk.Dialog(title="⚙ Configuration SSH", transient_for=self.get_root())
        dialog.add_css_class("rounded-dialog")
        dialog.set_default_size(450, 400)
        content = dialog.get_content_area()
        content.set_spacing(10)
        set_margins(content, 16)
        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(8)
        row = 0
        lbl_srv = Gtk.Label(label="🖥️ Serveur SSH Local", css_classes=["control-section-title"], xalign=0, margin_bottom=4)
        grid.attach(lbl_srv, 0, row, 2, 1); row += 1
        grid.attach(Gtk.Label(label="Port Serveur :", xalign=0), 0, row, 1, 1)
        entry_srv_port = Gtk.Entry(); entry_srv_port.set_text(str(cfg.get("ssh_server_port", "22"))); grid.attach(entry_srv_port, 1, row, 1, 1); row += 1
        lbl_cli = Gtk.Label(label="🔗 Client SSH Distants", css_classes=["control-section-title"], xalign=0, margin_top=8, margin_bottom=4)
        grid.attach(lbl_cli, 0, row, 2, 1); row += 1
        grid.attach(Gtk.Label(label="Hôte/IP :", xalign=0), 0, row, 1, 1)
        entry_host = Gtk.Entry(); entry_host.set_text(cfg.get("ssh_client_host", "192.168.1.10")); grid.attach(entry_host, 1, row, 1, 1); row += 1
        grid.attach(Gtk.Label(label="Port :", xalign=0), 0, row, 1, 1)
        entry_port = Gtk.Entry(); entry_port.set_text(str(cfg.get("ssh_client_port", "22"))); grid.attach(entry_port, 1, row, 1, 1); row += 1
        grid.attach(Gtk.Label(label="Utilisateur :", xalign=0), 0, row, 1, 1)
        entry_user = Gtk.Entry(); entry_user.set_text(cfg.get("ssh_client_user", "root")); grid.attach(entry_user, 1, row, 1, 1); row += 1
        grid.attach(Gtk.Label(label="Mode Auth :", xalign=0), 0, row, 1, 1)
        combo_auth = Gtk.ComboBoxText()
        combo_auth.append_text("Clé Privée (Key)")
        combo_auth.append_text("Mot de passe (Password)")
        combo_auth.set_active(0 if cfg.get("ssh_client_auth_mode", "key") == "key" else 1)
        grid.attach(combo_auth, 1, row, 1, 1); row += 1
        grid.attach(Gtk.Label(label="Chemin Clé Privée :", xalign=0), 0, row, 1, 1)
        entry_key = Gtk.Entry(); entry_key.set_text(cfg.get("ssh_client_key", "~/.ssh/id_rsa")); entry_key.set_tooltip_text("Laisser vide si mot de passe"); grid.attach(entry_key, 1, row, 1, 1); row += 1
        content.append(grid)
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.END, margin_top=12)
        btn_cancel = Gtk.Button(label="Annuler")
        btn_save = Gtk.Button(label="💾 Sauvegarder", css_classes=["suggested-action"])
        btn_box.append(btn_cancel); btn_box.append(btn_save); content.append(btn_box)
        def on_save(*_):
            auth_mode = "key" if combo_auth.get_active() == 0 else "password"
            new_cfg = {
                "ssh_server_port": entry_srv_port.get_text().strip(), "ssh_client_host": entry_host.get_text().strip(),
                "ssh_client_port": entry_port.get_text().strip(), "ssh_client_user": entry_user.get_text().strip(),
                "ssh_client_auth_mode": auth_mode, "ssh_client_key": entry_key.get_text().strip(),
            }
            cfg.update(new_cfg)
            save_config(cfg)
            self.show_toast("✅ Configuration SSH sauvegardée")
            dialog.destroy()
        btn_save.connect("clicked", on_save)
        btn_cancel.connect("clicked", lambda *_: dialog.destroy())
        dialog.present()

    def _run_ssh_server_start(self, *_):
        cfg = self.get_config()
        port = cfg.get("ssh_server_port", "22")
        self.terminal._log(f"🔐 === Démarrage Serveur SSH (Port {port}) ===")
        def _thread():
            try:
                if not shutil.which("sshd"):
                    GLib.idle_add(self.terminal._log, "❌ sshd non trouvé. Veuillez installer openssh-server.")
                    GLib.idle_add(self.show_toast, "❌ sshd manquant")
                    return
                GLib.idle_add(self.terminal._log, "▶ sudo systemctl restart sshd")
                subprocess.run(["sudo", "systemctl", "restart", "sshd"], check=True)
                if is_port_in_use(int(port)):
                    GLib.idle_add(self._set_dot, "ssh_server", True)
                    GLib.idle_add(self.show_toast, f"✅ Serveur SSH actif sur port {port}")
                    GLib.idle_add(self.terminal._log, f"=== READY : Port {port} ===")
                else:
                    GLib.idle_add(self.terminal._log, "⚠ Le service a démarré mais le port semble fermé.")
            except subprocess.CalledProcessError as e:
                GLib.idle_add(self.terminal._log, f"❌ Erreur systemctl: {e}")
                GLib.idle_add(self.show_toast, "❌ Échec démarrage SSH")
            except Exception as e:
                GLib.idle_add(self.terminal._log, f"❌ Exception: {e}")
        threading.Thread(target=_thread, daemon=True).start()

    def _run_ssh_client_connect(self, *_):
        cfg = self.get_config()
        host = cfg.get("ssh_client_host", "192.168.1.10")
        port = cfg.get("ssh_client_port", "22")
        user = cfg.get("ssh_client_user", "root")
        auth_mode = cfg.get("ssh_client_auth_mode", "key")
        key_path = cfg.get("ssh_client_key", "")
        self.terminal._log(f"🔗 === Connexion SSH vers {user}@{host}:{port} ===")
        cmd_parts = ["ssh"]
        if port != "22": cmd_parts.extend(["-p", str(port)])
        if auth_mode == "key" and key_path:
            expanded_key = os.path.expanduser(key_path)
            cmd_parts.extend(["-i", expanded_key])
            cmd_parts.extend(["-o", "PasswordAuthentication=no"])
        cmd_parts.append(f"{user}@{host}")
        final_cmd = " ".join(cmd_parts)
        NativeTtyTerminal(self.get_root(), f"SSH: {user}@{host}", final_cmd)

    def _run_ssh_client_disconnect_dummy(self, *_):
        self.terminal._log("ℹ️ Pour déconnecter SSH, tapez 'exit' dans le terminal TTY ouvert.")
        self.show_toast("ℹ️ Utilisez 'exit' dans le terminal")

    def _run_venv_create(self, *_):
        root = self.get_project_root()
        if not root: return self.show_toast("❌ Aucun projet ouvert")
        cfg = self.get_config()
        venv_name = cfg.get("venv_name", "venv")
        venv_path = root / venv_name
        if venv_path.exists():
            if Gtk.MessageDialog(transient_for=self.get_root(), flags=0, message_type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.YES_NO, text="Venv existant", secondary_text=f"{venv_name} existe déjà. Recréer ?").run() != Gtk.ResponseType.YES:
                return
        self.terminal._log(f"🐍 === Création environnement virtuel: {venv_name} ===")
        def _thread():
            try:
                GLib.idle_add(self.terminal._log, f"▶ python3 -m venv {venv_name}")
                subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
                GLib.idle_add(self._set_dot, "venv_create", True)
                GLib.idle_add(self.show_toast, f"✅ Venv '{venv_name}' créé")
                GLib.idle_add(self.terminal._log, "=== OK ===")
            except Exception as e:
                GLib.idle_add(self.terminal._log, f"❌ Erreur: {e}")
                GLib.idle_add(self.show_toast, "❌ Échec création venv")
        threading.Thread(target=_thread, daemon=True).start()

    def _show_venv_install_dialog(self, *_):
        root = self.get_project_root()
        if not root: return self.show_toast("❌ Aucun projet ouvert")
        cfg = self.get_config()
        venv_name = cfg.get("venv_name", "venv")
        venv_path = root / venv_name
        if not venv_path.exists():
            return self.show_toast(f"❌ Venv '{venv_name}' introuvable. Créez-le d'abord.")
        dialog = Gtk.Dialog(title="Installer Module Pip", transient_for=self.get_root())
        dialog.add_css_class("rounded-dialog")
        dialog.set_default_size(400, 200)
        content = dialog.get_content_area()
        content.set_spacing(10)
        set_margins(content, 16)
        content.append(Gtk.Label(label=f"Installer dans: {venv_name}", xalign=0, css_classes=["dim-label"]))
        entry_pkg = Gtk.Entry(); entry_pkg.set_placeholder_text("ex: django, pandas, requests"); content.append(entry_pkg)
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.END, margin_top=12)
        btn_cancel = Gtk.Button(label="Annuler")
        btn_install = Gtk.Button(label="📦 Installer", css_classes=["suggested-action"])
        btn_box.append(btn_cancel); btn_box.append(btn_install); content.append(btn_box)
        def on_install(*_):
            pkg = entry_pkg.get_text().strip()
            if not pkg: return
            pip_path = str(venv_path / "bin" / "pip")
            if not Path(pip_path).exists(): pip_path = str(venv_path / "Scripts" / "pip.exe")
            self.terminal._log(f"📦 Installation de {pkg}...")
            cmd = f"{pip_path} install {pkg}"
            NativeTtyTerminal(self.get_root(), f"Pip Install: {pkg}", cmd, cwd=str(root))
            dialog.destroy()
        btn_install.connect("clicked", on_install)
        btn_cancel.connect("clicked", lambda *_: dialog.destroy())
        dialog.present()

    def _run_venv_delete(self, *_):
        root = self.get_project_root()
        if not root: return self.show_toast("❌ Aucun projet ouvert")
        cfg = self.get_config()
        venv_name = cfg.get("venv_name", "venv")
        venv_path = root / venv_name
        if not venv_path.exists():
            return self.show_toast(f"❌ Venv '{venv_name}' introuvable.")
        if Gtk.MessageDialog(transient_for=self.get_root(), flags=0, message_type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.YES_NO, text="Supprimer Venv", secondary_text=f"Êtes-vous sûr de vouloir supprimer {venv_name} ?").run() != Gtk.ResponseType.YES:
            return
        self.terminal._log(f"🗑 Suppression de {venv_name}...")
        try:
            shutil.rmtree(venv_path)
            self.show_toast(f"✅ Venv '{venv_name}' supprimé")
            self.terminal._log("=== OK ===")
        except Exception as e:
            self.terminal._log(f"❌ Erreur: {e}")

    def _run_venv_activate(self, *_):
        root = self.get_project_root()
        if not root: return self.show_toast("❌ Aucun projet ouvert")
        cfg = self.get_config()
        venv_name = cfg.get("venv_name", "venv")
        venv_path = root / venv_name
        if not venv_path.exists():
            return self.show_toast(f"❌ Venv '{venv_name}' introuvable.")
        self.terminal._log(f"⚡ === Activation Shell Venv: {venv_name} ===")
        activate_script = str(venv_path / "bin" / "activate")
        if not Path(activate_script).exists():
            activate_script = str(venv_path / "Scripts" / "activate.bat")
        cmd = f"bash --init-file {activate_script}"
        NativeTtyTerminal(self.get_root(), f"Shell Activé: {venv_name}", cmd, cwd=str(root))

    def _run_venv_deactivate_dummy(self, *_):
        self.terminal._log("ℹ️ Pour désactiver le venv, tapez 'deactivate' dans le terminal TTY ouvert.")
        self.show_toast("ℹ️ Utilisez 'deactivate' dans le terminal")

    def _show_db_stats(self, *_):
        mp = self._manage_path()
        if not mp:
            self.terminal._log("❌ manage.py introuvable. Ouvrez d'abord un projet Django valide.")
            self.show_toast("❌ Projet Django non détecté"); return
        self.terminal._log("🔍 Récupération de TOUTES les données via Django ORM...")
        self.show_toast("⏳ Chargement des données (cela peut prendre du temps)...")
        
        # Script Django pour récupérer TOUTES les données
        django_script = """
import json
from django.apps import apps
from django.db import models
result = []
for model in apps.get_models():
    try:
        fields_info = []
        for f in model._meta.fields:
            fields_info.append({"name": f.name, "type": f.get_internal_type(), "is_pk": bool(f.primary_key), "is_fk": isinstance(f, (models.ForeignKey, models.OneToOneField))})
        rows_data = []
        try:
            # PAS DE LIMITE [:100] ICI
            qs = model.objects.all()
            for obj in qs:
                row_dict = {}
                for f in model._meta.fields:
                    val = getattr(obj, f.name)
                    row_dict[f.name] = str(val) if val is not None else "NULL"
                rows_data.append(row_dict)
        except Exception as e:
            rows_data = [{"_error": str(e)}]
        result.append({"table": model._meta.db_table, "model": model._meta.object_name, "total_rows": model.objects.count(), "fields": fields_info, "data": rows_data})
    except Exception as e:
        result.append({"table": model._meta.db_table, "error": str(e)})
print(json.dumps(result, default=str))
"""
        cmd = [sys.executable, str(mp), "shell", "-c", django_script]
        def _thread():
            try:
                env = os.environ.copy(); env["PYTHONUNBUFFERED"] = "1"
                # Timeout augmenté à 60s pour les grosses tables
                proc = subprocess.run(cmd, cwd=str(mp.parent), capture_output=True, text=True, env=env, timeout=60)
                if proc.returncode == 0:
                    output = proc.stdout.strip(); stats = []
                    for line in reversed(output.split('\n')):
                        line = line.strip()
                        if line.startswith('[') or line.startswith('{'):
                            try: stats = json.loads(line); break
                            except json.JSONDecodeError: continue
                    if stats: GLib.idle_add(self._display_db_stats_popup, stats)
                    else:
                        GLib.idle_add(self.terminal._log, f"❌ Erreur de parsing JSON. Sortie brute: {output}")
                        GLib.idle_add(self.show_toast, "❌ Erreur de format des données")
                else:
                    GLib.idle_add(self.terminal._log, f"❌ Erreur Django ORM: {proc.stderr}")
                    GLib.idle_add(self.show_toast, "❌ Échec de la récupération")
            except subprocess.TimeoutExpired:
                GLib.idle_add(self.terminal._log, "❌ Délai d'attente dépassé (la base est très volumineuse).")
                GLib.idle_add(self.show_toast, "⏱ Délai dépassé")
            except Exception as e:
                GLib.idle_add(self.terminal._log, f"❌ Exception: {e}")
                GLib.idle_add(self.show_toast, "❌ Erreur inattendue")
        threading.Thread(target=_thread, daemon=True).start()

    def _display_db_stats_popup(self, stats: list):
        self.db_stats_data = stats; self.current_selected_table_data = None
        dialog = Gtk.Dialog(title="📊 Visualisation des Tables et Données (Illimité)", transient_for=self.get_root())
        dialog.add_css_class("rounded-dialog")
        dialog.set_default_size(1000, 650)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12); set_margins(content, 16); dialog.set_child(content)
        header_info = Gtk.Label(label=f"{len(stats)} table(s) trouvée(s). Cliquez sur une table pour voir TOUTES ses données."); header_info.add_css_class("heading"); content.append(header_info); content.append(Gtk.Separator())
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12); main_box.set_vexpand(True)
        scroll_tables = Gtk.ScrolledWindow(); scroll_tables.set_size_request(250, -1)
        self.listbox_tables = Gtk.ListBox(); self.listbox_tables.set_selection_mode(Gtk.SelectionMode.SINGLE); scroll_tables.set_child(self.listbox_tables); main_box.append(scroll_tables)
        details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8); details_box.set_hexpand(True)
        self.current_table_label = Gtk.Label(label="Sélectionnez une table pour voir les données", xalign=0); self.current_table_label.add_css_class("heading"); details_box.append(self.current_table_label)
        scroll_fields = Gtk.ScrolledWindow(); scroll_fields.set_vexpand(True); scroll_fields.set_hexpand(True)
        self.data_store = Gtk.ListStore(); self.tree_view = Gtk.TreeView(model=self.data_store); scroll_fields.set_child(self.tree_view); details_box.append(scroll_fields)
        export_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8); export_box.set_halign(Gtk.Align.END)
        self.btn_csv = Gtk.Button(label="📄 Exporter CSV"); self.btn_csv.add_css_class("ctrl-btn"); self.btn_csv.set_sensitive(False); self.btn_csv.connect("clicked", lambda *_: self._export_to_csv())
        self.btn_excel = Gtk.Button(label="📊 Exporter Excel (Pandas)"); self.btn_excel.add_css_class("ctrl-btn"); self.btn_excel.set_sensitive(False); self.btn_excel.connect("clicked", lambda *_: self._export_to_excel())
        export_box.append(self.btn_csv); export_box.append(self.btn_excel); details_box.append(export_box)
        main_box.append(details_box); content.append(main_box)
        if not stats:
            lbl_empty = Gtk.Label(label="Aucune table trouvée ou base de données vide."); lbl_empty.set_margin_top(20); lbl_empty.add_css_class("dim-label"); self.listbox_tables.append(lbl_empty)
        else:
            for item in stats:
                row = Gtk.ListBoxRow()
                if "error" in item:
                    lbl = Gtk.Label(label=f"⚠️ {item['table']} (Erreur)", xalign=0); lbl.add_css_class("dim-label")
                else:
                    lbl = Gtk.Label(label=f"🗄 {item['table']} ({item['total_rows']} lignes)", xalign=0); lbl.set_margin_start(8); lbl.set_margin_top(6); lbl.set_margin_bottom(6)
                row.set_child(lbl); row._data = item; self.listbox_tables.append(row)
        self.listbox_tables.connect("row-selected", self._on_table_selected)
        btn_close = Gtk.Button(label="Fermer"); btn_close.set_halign(Gtk.Align.END); btn_close.set_margin_top(8); btn_close.connect("clicked", lambda *_: dialog.destroy()); content.append(btn_close)
        dialog.present()

    def _on_table_selected(self, listbox, row):
        self.data_store.clear()
        for col in self.tree_view.get_columns():
            self.tree_view.remove_column(col)
        if not row or not hasattr(row, "_data"):
            self.current_table_label.set_text("Sélectionnez une table pour voir les données")
            self.current_selected_table_data = None; self.btn_csv.set_sensitive(False); self.btn_excel.set_sensitive(False); return
        item = row._data; self.current_selected_table_data = item
        if "error" in item:
            self.current_table_label.set_text(f"⚠️ Erreur sur la table: {item['table']}")
            self.btn_csv.set_sensitive(False); self.btn_excel.set_sensitive(False); return
        self.current_table_label.set_text(f"🗄 Table: {item['table']} (Affichage de {len(item['data'])} / {item['total_rows']} lignes)")
        self.btn_csv.set_sensitive(True); self.btn_excel.set_sensitive(True)
        fields = item.get("fields", []); data_rows = item.get("data", []); col_types = [str] * len(fields)
        self.data_store = Gtk.ListStore(*col_types); self.tree_view.set_model(self.data_store)
        for idx, field in enumerate(fields):
            renderer = Gtk.CellRendererText(); title = field["name"]
            if field["is_pk"]:
                title = f"🔑 {title}"; renderer.set_property("foreground", "#f1c40f"); renderer.set_property("weight", Pango.Weight.BOLD)
            elif field["is_fk"]:
                title = f"🔗 {title}"; renderer.set_property("foreground", "#3498db")
            col = Gtk.TreeViewColumn(title, renderer, text=idx); col.set_resizable(True); col.set_min_width(100); self.tree_view.append_column(col)
        for row_data in data_rows:
            if "_error" in row_data:
                self.data_store.append([f"Erreur de lecture: {row_data['_error']}"] + [""] * (len(fields) - 1)); break
            row_values = [str(row_data.get(f["name"], "")) for f in fields]
            self.data_store.append(row_values)

    def _export_to_csv(self):
        if not self.current_selected_table_data: return
        try:
            dialog = Gtk.FileDialog(title=f"Exporter {self.current_selected_table_data['table']} en CSV")
            dialog.save(self.get_root(), None, self._on_csv_save_selected)
        except Exception as e:
            self.terminal._log(f"❌ Erreur export CSV: {e}"); self.show_toast("❌ Échec de l'export CSV")

    def _on_csv_save_selected(self, dialog, result):
        try:
            file = dialog.save_finish(result)
            if not file: return
            filepath = Path(file.get_path())
            if not str(filepath).endswith('.csv'): filepath = filepath.with_suffix('.csv')
            import csv
            item = self.current_selected_table_data; fields = item.get("fields", []); data_rows = item.get("data", [])
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f); writer.writerow([f["name"] for f in fields])
                for row_data in data_rows:
                    if "_error" not in row_data: writer.writerow([row_data.get(f["name"], "") for f in fields])
            self.terminal._log(f"✅ Export CSV réussi: {filepath} ({len(data_rows)} lignes)"); self.show_toast("✅ Export CSV réussi")
        except Exception as e:
            self.terminal._log(f"❌ Erreur lors de l'écriture du CSV: {e}"); self.show_toast("❌ Échec de l'export CSV")

    def _export_to_excel(self):
        if not self.current_selected_table_data: return
        try:
            import pandas as pd
            dialog = Gtk.FileDialog(title=f"Exporter {self.current_selected_table_data['table']} en Excel")
            dialog.save(self.get_root(), None, self._on_excel_save_selected)
        except ImportError:
            self.terminal._log("❌ Pandas n'est pas installé. Veuillez l'installer avec: pip install pandas openpyxl")
            self.show_toast("❌ Pandas non installé (pip install pandas openpyxl)")
        except Exception as e:
            self.terminal._log(f"❌ Erreur export Excel: {e}"); self.show_toast("❌ Échec de l'export Excel")

    def _on_excel_save_selected(self, dialog, result):
        try:
            import pandas as pd
            file = dialog.save_finish(result)
            if not file: return
            filepath = Path(file.get_path())
            if not str(filepath).endswith('.xlsx'): filepath = filepath.with_suffix('.xlsx')
            item = self.current_selected_table_data; fields = item.get("fields", []); data_rows = item.get("data", [])
            clean_data = []
            for row_data in data_rows:
                if "_error" not in row_data: clean_data.append({f["name"]: row_data.get(f["name"], "") for f in fields})
            df = pd.DataFrame(clean_data); df.to_excel(filepath, index=False, engine='openpyxl')
            self.terminal._log(f"✅ Export Excel réussi: {filepath} ({len(clean_data)} lignes)"); self.show_toast("✅ Export Excel réussi")
        except ImportError:
            self.terminal._log("❌ Pandas ou openpyxl n'est pas installé. Veuillez l'installer avec: pip install pandas openpyxl")
            self.show_toast("❌ Pandas/openpyxl non installé")
        except Exception as e:
            self.terminal._log(f"❌ Erreur lors de l'écriture du fichier Excel: {e}"); self.show_toast("❌ Échec de l'export Excel")

    def _run_gy(self, rel_path: str, sudo=False):
        root = self.get_project_root()
        if not root: return
        gy_path = root / rel_path
        if not gy_path.exists(): return self.terminal._log(f"❌ Not found: {gy_path}")
        self._run_cmd(["sudo", sys.executable, str(gy_path)] if sudo else [sys.executable, str(gy_path)], cwd=str(gy_path.parent), name=f"gy_{rel_path}")

    def _compress_project(self, *_):
        root = self.get_project_root()
        if not root: return self.terminal._log("❌ No project open")
        dialog = Gtk.Dialog(title="Save ZIP archive", transient_for=self.get_root()); dialog.add_css_class("rounded-dialog"); dialog.set_default_size(500, 150)
        content = dialog.get_content_area(); set_margins(content, 12); content.set_spacing(8)
        box_path = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        entry_path = Gtk.Entry(); entry_path.set_hexpand(True); entry_path.set_text(str(root.parent / f"{root.name}.zip"))
        btn_browse = Gtk.Button(label="📂 Browse"); box_path.append(entry_path); box_path.append(btn_browse)
        content.append(Gtk.Label(label="Destination path:", xalign=0)); content.append(box_path)
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_cancel = Gtk.Button(label="Cancel"); btn_save = Gtk.Button(label="💾 Compress"); btn_save.add_css_class("suggested-action")
        btn_box.append(btn_cancel); btn_box.append(btn_save); content.append(btn_box)
        def on_browse(*_): Gtk.FileDialog(title="Choose destination folder").select_folder(self.get_root(), None, lambda d, r: self._on_folder_selected(d, r, entry_path))
        def on_save(*_):
            zip_path = entry_path.get_text().strip()
            if not zip_path: return
            if not zip_path.endswith('.zip'): zip_path += '.zip'
            try:
                self.terminal._log(f"🗜 Compressing to {zip_path}...")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in root.rglob('*'):
                        if file_path.is_file() and not any(x in str(file_path) for x in ["__pycache__", ".git", "venv", "node_modules"]):
                            zipf.write(file_path, file_path.relative_to(root.parent))
                self.terminal._log(f"✅ Project compressed: {zip_path}"); self.show_toast("📦 Project compressed"); dialog.destroy()
            except Exception as e: self.terminal._log(f"❌ Error: {e}"); self.show_toast("❌ Failed")
        btn_browse.connect("clicked", on_browse); btn_save.connect("clicked", on_save); btn_cancel.connect("clicked", lambda *_: dialog.destroy()); dialog.present()

    def _on_folder_selected(self, dialog, result, entry):
        try:
            folder = dialog.select_folder_finish(result)
            if folder: entry.set_text(str(Path(folder.get_path()) / f"{self.get_project_root().name}.zip"))
        except Exception as e:
            global_log(f"⚠️ Erreur dans gy.py: {type(e).__name__} - {e}")
    def _decompress_archive(self, *_):
        Gtk.FileDialog(title="Select a .zip archive").open(self.get_root(), None, self._on_decompress_selected)

    def _on_decompress_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if not file: return
            archive_path, root = Path(file.get_path()), self.get_project_root()
            extract_to = root.parent if root else Path.home()
            self.terminal._log(f"📂 Decompressing {archive_path.name} to {extract_to}...")
            with zipfile.ZipFile(archive_path, 'r') as zipf: zipf.extractall(path=extract_to)
            self.terminal._log("✅ Decompression finished."); self.show_toast("📂 Archive decompressed")
        except Exception as e: self.terminal._log(f"❌ Error: {e}"); self.show_toast("❌ Failed")


