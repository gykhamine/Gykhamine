"""Module généré automatiquement depuis gy.py"""
import os, sys, re, subprocess, json, hashlib, time, sqlite3, requests
from pathlib import Path
from datetime import datetime

#  GLOBAL LOGGER SYSTEM (Centralisation des erreurs)
# ═══════════════════════════════════════════════════════════════════════
_global_log_callbacks = []

def register_logger(callback):
    """Permet au TerminalPanel de s'enregistrer pour recevoir les logs"""
    if callback not in _global_log_callbacks:
        _global_log_callbacks.append(callback)

def global_log(message: str):
    """Écrit le message dans tous les loggers enregistrés ET dans la console"""
    print(message) # Fallback console
    for cb in _global_log_callbacks:
        try:
            cb(message)
        except Exception as e:
            global_log(f"⚠️ Erreur dans global_log: {type(e).__name__} - {e}")




# ═══════════════════════════════════════════════════════════════════════
#  HELPER : LECTURE .ENV EXTERNE (Simple & Robuste)
# ═══════════════════════════════════════════════════════════════════════
def set_margins(widget, val):
    widget.set_margin_top(val)
    widget.set_margin_bottom(val)
    widget.set_margin_start(val)
    widget.set_margin_end(val)

def enable_window_controls(window, title=None):
    """Remplace la barre de titre par défaut d'une fenêtre (Gtk.Dialog ou Gtk.Window)
    par une Adw.HeaderBar affichant explicitement réduire/agrandir/fermer, et
    s'assure qu'elle reste redimensionnable.
    Par défaut GTK ne montre qu'un bouton fermer sur les fenêtres de type
    "dialogue" (comportement HIG) : sans ce correctif elles sont de fait à
    taille fixe, sans moyen de les agrandir autrement qu'en plein écran.
    Important : le ':' dans decoration_layout sépare gauche/droite. Sans lui,
    et avec show_start_title_buttons resté à sa valeur par défaut (True),
    un bouton fermer apparaissait EN PLUS à gauche -> 2 X visibles sur la
    même fenêtre. On désactive donc explicitement le côté gauche."""
    from gi.repository import Adw, Gtk
    window.set_resizable(True)
    header = Adw.HeaderBar()
    header.set_show_start_title_buttons(False)
    header.set_show_end_title_buttons(True)
    header.set_decoration_layout(":minimize,maximize,close")
    if title:
        header.set_title_widget(Gtk.Label(label=title))
    window.set_titlebar(header)
    return header

# ═══════════════════════════════════════════════════════════════════════
#  GLOBAL CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════
APP_ID   = "org.gykhamine.studio"
VERSION  = "3.3.1"
SCRIPT_DIR = Path(__file__).parent.resolve()
LOGO_PATH  = Path("/usr/share/Gykhamine/icon/gykhamine_logo.png")


# ═══════════════════════════════════════════════════════════════════════
#  CHEMINS FIXES — SYSTÈME PERSISTANT (installation définitive, plus de live-USB)
# ═══════════════════════════════════════════════════════════════════════
# Depuis la version installée en persistant, il n'y a plus de partition GY
# amovible à monter/sélectionner au premier lancement : le logiciel et ses
# données vivent à des emplacements fixes du système.
#   - llama-server : binaire système, dans /bin
#   - modèle GGUF  : donnée applicative en lecture seule, sous /usr/share/Gykhamine
#   - PostgreSQL   : directement sous /var (pas de périphérique/partition à monter)
#   - logs / DB    : données persistantes de l'utilisateur gy, sous ~/.local/GSCODE
GY_DATA_DIR = Path("/home/gy/.local/GSCODE")

DEFAULT_CONFIG = {
    # LLaMA Server
    "llama_server_path": "/bin/llama-server",
    "llama_model_path": "/usr/share/Gykhamine/model/gysingner.gguf",
    "llama_host": "",
    "llama_port": "",
    
    # Gunicorn
    "gunicorn_bind": "",
    "gunicorn_ssl_enabled": False, # Gardé en dur car c'est un booléen simple
    "gunicorn_ssl_cert_path": "",
    "gunicorn_ssl_key_path": "",
    
    # Projets
    "last_project": "",
    "last_projects": [],
    
    # Interface
    "theme": "dark",
    "open_browser_on_run": False,
    
    # Ports
    "auto_find_free_port": True,
    "default_port_range_start": "",
    "default_port_range_end": "",
    
    # Logs et Base de données
    "log_file_path": str(GY_DATA_DIR / "logs" / "studio.log"),
    "db_path": str(GY_DATA_DIR / "db" / "gykhamine_studio.db"),
    
    # PostgreSQL (entièrement configurable depuis le panneau Settings) — plus de
    # périphérique/partition à monter : /var est déjà le dossier de données local.
    "pg_device": "",
    "pg_mount_point": "/var/lib/pgsql/data",
    "pg_db_name": "",
    "pg_db_user": "",
    "pg_db_password": "",
    "pg_bind_ip": "",
    
    # Redis
    "redis_mode": "local",
    "redis_ip": "",
    "redis_port": "",
    "redis_data_dir": str(GY_DATA_DIR / "data_redis"),
    "redis_use_persistence": True,
    "redis_env_path": str(GY_DATA_DIR / "Gykhamine" / "gy" / ".env"),
    "redis_update_env": False,
    
    # NFS
    "nfs_server_mode": "local",
    "nfs_export_dir": str(GY_DATA_DIR / "gy" / "media"),
    "nfs_lan_network": "",
    "nfs_client_server_ip": "",
    "nfs_client_export_dir": "/srv/nfs",
    "nfs_client_mount_point": os.path.expanduser("~/nfs_mount"),
    
    # Nginx
    "nginx_conf_path": "/etc/nginx/nginx.conf",
    "nginx_mode": "reverse_proxy",
    "nginx_server_name": "",
    "nginx_listen_port": "",
    "nginx_upstream_name": "gunicorn",
    "nginx_upstream_servers": "",
    "nginx_proxy_pass": "",
    "nginx_force_https": True,
    "nginx_ssl_cert": "/etc/pki/nginx/server.crt",
    "nginx_ssl_key": "/etc/pki/nginx/private/server.key",
    "nginx_static_url": "/static/",
    "nginx_static_path": str(GY_DATA_DIR / "file" / "statics"),
    "nginx_media_url": "/media/",
    "nginx_media_path": str(GY_DATA_DIR / "file" / "media"),
    "nginx_max_body": "20M",
    "nginx_read_timeout": "60s",
    "nginx_connect_timeout": "60s",
    "nginx_proxy_buffering": True,
    "nginx_security_headers": True,
    "nginx_custom_redirects": "/ancien -> /nouveau\n",
    
    # SSH
    "ssh_server_mode": "local",
    "ssh_server_port": "",
    "ssh_client_host": "",
    "ssh_client_port": "",
    "ssh_client_user": "",
    "ssh_client_key": os.path.expanduser("~/.ssh/id_rsa"),
    "ssh_client_auth_mode": "key",
    
    # Virtual Environment
    "venv_name": "venv",
    "venv_path": "",

    # Dialog IP/QR — derniers paramètres saisis
    "qr_last_scheme": "https://",
    "qr_last_port": "443",
    "qr_last_custom_ip": "",
    "qr_last_wifi_ssid": "",
    "qr_last_wifi_password": "",
    "qr_last_wifi_security": 0,   # index ComboBoxText (0=WPA, 1=WEP, 2=ouvert)
}# ═══════════════════════════════════════════════════════════════════════
