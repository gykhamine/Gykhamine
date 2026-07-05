"""Module généré automatiquement depuis widgets.py - Classe SettingsDialog"""
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
from .directory_picker_row import DirectoryPickerRow, VolumePickerRow
#  WIDGETS
# ═══════════════════════════════════════════════════════════════════════
TYPE_ICONS = {"import": "📦", "class": "🏛", "function": "⚡", "separator": "─", "comment": "💬", "other": "▪", "template": "🌐", "template_part": "🌐", "django_block": "🧩", "style": "🎨", "style_rule": "🎨", "script": "⚙️", "script_block": "⚡", "c_block": "⚙️"}



class SettingsDialog(Adw.PreferencesDialog):
    def __init__(self, parent, config: dict, on_save):
        super().__init__(); self.set_title("Settings"); self.config, self.on_save = dict(config), on_save
        page = Adw.PreferencesPage(); self.add(page)
        
        grp = Adw.PreferencesGroup(title="🤖 llama.cpp"); page.add(grp); self._rows = {}
        for key, title, placeholder in [("llama_server_path", "llama-server path", "/usr/local/bin/llama-server"), ("llama_model_path", ".gguf model path", "/models/qwen2.5-coder.gguf"), ("llama_host", "Host", "127.0.0.1"), ("llama_port", "Port", "8080")]:
            row = Adw.EntryRow(title=title); row.set_text(str(config.get(key, placeholder))); self._rows[key] = row; grp.add(row)
            
        grp_ports = Adw.PreferencesGroup(title="🔌 Ports & Servers"); page.add(grp_ports)
        auto_port = Adw.SwitchRow(title="Auto-detect free ports"); auto_port.set_active(config.get("auto_find_free_port", True)); self._rows["auto_find_free_port"] = auto_port; grp_ports.add(auto_port)
        for key, title, default in [("default_port_range_start", "Range start", 8000), ("default_port_range_end", "Range end", 8010)]:
            row = Adw.EntryRow(title=title); row.set_text(str(config.get(key, default))); self._rows[key] = row; grp_ports.add(row)
        gunicorn_row = Adw.EntryRow(title="Gunicorn bind address"); gunicorn_row.set_text(str(config.get("gunicorn_bind", "0.0.0.0:8000"))); gunicorn_row.set_tooltip_text("e.g., 0.0.0.0:8000, 0.0.0.0:80 or 0.0.0.0:443")
        self._rows["gunicorn_bind"] = gunicorn_row; grp_ports.add(gunicorn_row)
        
        grp2 = Adw.PreferencesGroup(title="🌐 Options"); page.add(grp2)
        browser_switch = Adw.SwitchRow(title="Open browser automatically"); browser_switch.set_active(config.get("open_browser_on_run", True)); self._rows["open_browser_on_run"] = browser_switch; grp2.add(browser_switch)
        theme_row = Adw.ComboRow(title="Theme"); theme_row.set_model(Gtk.StringList.new(["Dark", "Light"])); theme_row.set_selected(0 if config.get("theme", "dark") == "dark" else 1); self._rows["theme"] = theme_row; grp2.add(theme_row)
        
        grp_paths = Adw.PreferencesGroup(title="📁 File Paths"); page.add(grp_paths)
        log_row = DirectoryPickerRow(title="Log file (.log)", subtitle="Destination folder for logs", initial_value=config.get("log_file_path", DEFAULT_CONFIG["log_file_path"]), filename="studio.log")
        self._rows["log_file_path"] = log_row; grp_paths.add(log_row)
        db_row = DirectoryPickerRow(title="SQLite database (.db)", subtitle="Destination folder for the database", initial_value=config.get("db_path", DEFAULT_CONFIG["db_path"]), filename="gykhamine_studio.db")
        self._rows["db_path"] = db_row; grp_paths.add(db_row)
        
        grp_pg = Adw.PreferencesGroup(title="🐘 Base de données (PostgreSQL)")
        page.add(grp_pg)
        _current_pg_device = config.get("pg_device", "")
        _current_pg_uuid = _current_pg_device.replace("UUID=", "") if _current_pg_device else ""
        pg_device_row = VolumePickerRow(title="Partition PostgreSQL", subtitle="Volume détecté automatiquement — aucune saisie manuelle d'UUID", initial_uuid=_current_pg_uuid)
        self._rows["pg_device"] = pg_device_row
        grp_pg.add(pg_device_row)
        pg_other_rows = [("pg_mount_point", "Point de montage", "/var/lib/pgsql/data"), ("pg_db_name", "Nom de la base de données", "ma_base"), ("pg_db_user", "Nom d'utilisateur PostgreSQL", "mon_user"), ("pg_db_password", "Mot de passe PostgreSQL", "mot_de_passe")]
        for key, title, placeholder in pg_other_rows:
            row = Adw.EntryRow(title=title); row.set_text(str(config.get(key, placeholder))); self._rows[key] = row; grp_pg.add(row)
        bind_row = Adw.ComboRow(title="Adresse d'écoute (IP)")
        bind_row.set_model(Gtk.StringList.new(["127.0.0.1 (Local uniquement)", "0.0.0.0 (Réseau / Externe)"]))
        bind_row.set_selected(0 if config.get("pg_bind_ip", "127.0.0.1") == "127.0.0.1" else 1)
        self._rows["pg_bind_ip"] = bind_row
        grp_pg.add(bind_row)
        
        grp_redis = Adw.PreferencesGroup(title="🔴 Base de données (Redis)")
        page.add(grp_redis)
        redis_mode_row = Adw.ComboRow(title="Mode d'écoute")
        redis_mode_row.set_model(Gtk.StringList.new(["Local (127.0.0.1)", "Réseau (0.0.0.0)"]))
        redis_mode_row.set_selected(0 if config.get("redis_mode", "local") == "local" else 1)
        self._rows["redis_mode"] = redis_mode_row; grp_redis.add(redis_mode_row)
        for key, title, placeholder in [("redis_port", "Port", "6379"), ("redis_data_dir", "Dossier de données", str(Path.home() / "redis_data"))]:
            row = Adw.EntryRow(title=title); row.set_text(str(config.get(key, placeholder))); self._rows[key] = row; grp_redis.add(row)
        persist_row = Adw.SwitchRow(title="Utiliser la persistance (AOF)"); persist_row.set_active(config.get("redis_use_persistence", True)); self._rows["redis_use_persistence"] = persist_row; grp_redis.add(persist_row)
        
        grp_nfs_s = Adw.PreferencesGroup(title="📁 NFS Serveur")
        page.add(grp_nfs_s)
        nfs_s_mode_row = Adw.ComboRow(title="Mode d'accès")
        nfs_s_mode_row.set_model(Gtk.StringList.new(["Local (127.0.0.1)", "Réseau (ex: 192.168.1.0/24)"]))
        nfs_s_mode_row.set_selected(0 if config.get("nfs_server_mode", "local") == "local" else 1)
        self._rows["nfs_server_mode"] = nfs_s_mode_row; grp_nfs_s.add(nfs_s_mode_row)
        for key, title, placeholder in [("nfs_export_dir", "Dossier à exporter", "/run/media/gykhamine/GY/gy/media"), ("nfs_lan_network", "Réseau autorisé (si mode Réseau)", "192.168.1.0/24")]:
            row = Adw.EntryRow(title=title); row.set_text(str(config.get(key, placeholder))); self._rows[key] = row; grp_nfs_s.add(row)
            
        grp_nfs_c = Adw.PreferencesGroup(title="💻 NFS Client")
        page.add(grp_nfs_c)
        for key, title, placeholder in [("nfs_client_server_ip", "IP du serveur NFS", "192.168.1.10"), ("nfs_client_export_dir", "Dossier exporté sur le serveur", "/srv/nfs"), ("nfs_client_mount_point", "Point de montage local", str(Path.home() / "nfs_mount"))]:
            row = Adw.EntryRow(title=title); row.set_text(str(config.get(key, placeholder))); self._rows[key] = row; grp_nfs_c.add(row)
            
        grp_ssh = Adw.PreferencesGroup(title="🔐 SSH")
        page.add(grp_ssh)
        for key, title, placeholder in [("ssh_server_port", "Port Serveur", "22"), ("ssh_client_host", "Hôte Client", "192.168.1.10"), ("ssh_client_port", "Port Client", "22"), ("ssh_client_user", "Utilisateur Client", "root"), ("ssh_client_key", "Clé Privée", "~/.ssh/id_rsa")]:
            row = Adw.EntryRow(title=title); row.set_text(str(config.get(key, placeholder))); self._rows[key] = row; grp_ssh.add(row)
            
        grp_venv = Adw.PreferencesGroup(title="🐍 Python Venv")
        page.add(grp_venv)
        for key, title, placeholder in [("venv_name", "Nom de l'environnement", "venv")]:
            row = Adw.EntryRow(title=title); row.set_text(str(config.get(key, placeholder))); self._rows[key] = row; grp_venv.add(row)
            
        grp_about = Adw.PreferencesGroup(title="ℹ️ About"); page.add(grp_about)
        version_row = Adw.ActionRow(title="Version", subtitle=f"Gykhamine Studio v{VERSION}"); version_row.set_icon_name("dialog-information-symbolic"); grp_about.add(version_row)
        
        btn = Gtk.Button(label="💾 Save"); btn.add_css_class("suggested-action"); btn.connect("clicked", self._do_save)
        grp_save = Adw.PreferencesGroup(); page.add(grp_save); grp_save.add(btn)

    def _do_save(self, *_):
        for key, row in self._rows.items():
            if isinstance(row, Adw.EntryRow): self.config[key] = row.get_text()
            elif isinstance(row, Adw.SwitchRow): self.config[key] = row.get_active()
            elif isinstance(row, Adw.ComboRow):
                if key == "theme": self.config["theme"] = "dark" if row.get_selected() == 0 else "light"
                elif key == "pg_bind_ip": self.config["pg_bind_ip"] = "127.0.0.1" if row.get_selected() == 0 else "0.0.0.0"
                elif key == "redis_mode":
                    self.config["redis_mode"] = "local" if row.get_selected() == 0 else "network"
                    self.config["redis_ip"] = "127.0.0.1" if row.get_selected() == 0 else "0.0.0.0"
                elif key == "nfs_server_mode": self.config["nfs_server_mode"] = "local" if row.get_selected() == 0 else "network"
            elif isinstance(row, VolumePickerRow): self.config[key] = row.get_device_value()
            elif hasattr(row, "get_text"): self.config[key] = row.get_text()
        try:
            self.config["default_port_range_start"] = int(self.config.get("default_port_range_start", 8000))
            self.config["default_port_range_end"] = int(self.config.get("default_port_range_end", 8010))
        except Exception as e:
            global_log(f"⚠️ Erreur dans gy.py: {type(e).__name__} - {e}")
        self.on_save(self.config); self.close()


# ═══════════════════════════════════════════════════════════════════════
#  DOCUMENTATION MASTER DJANGO & PYTHON (EXHAUSTIVE - STYLE NEO4J)
# ═══════════════════════════════════════════════════════════════════════

# ... (Previous code remains unchanged) ...


