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

def apply_dark_source_scheme(buffer):
    """Force un thème sombre sur un GtkSource.Buffer, avec plusieurs schémas de
    repli si le premier choisi n'est pas installé sur le système. Sans cet
    appel, GtkSourceView retombe sur son thème système par défaut, souvent
    clair/blanc, ce qui casse le thème sombre de l'application (résidus
    blancs dans les éditeurs de code). À appeler sur CHAQUE GtkSource.Buffer
    créé dans l'app (BlockCard, Django Master Doc, etc.)."""
    import gi
    gi.require_version("GtkSource", "5")
    from gi.repository import GtkSource
    scheme_mgr = GtkSource.StyleSchemeManager.get_default()
    scheme = (
        scheme_mgr.get_scheme('Adwaita-dark')
        or scheme_mgr.get_scheme('classic-dark')
        or scheme_mgr.get_scheme('cobalt')
        or scheme_mgr.get_scheme('oblivion')
        or scheme_mgr.get_scheme('solarized-dark')
    )
    if scheme is not None:
        buffer.set_style_scheme(scheme)
    return scheme is not None

# ═══════════════════════════════════════════════════════════════════════
#  GLOBAL CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════
APP_ID   = "org.gykhamine.studio"
VERSION  = "3.3.1"
SCRIPT_DIR = Path(__file__).parent.resolve()
LOGO_PATH  = Path("/usr/share/Gykhamine/icon/gykhamine_logo.png")


# ═══════════════════════════════════════════════════════════════════════
#  MONTAGE AUTOMATIQUE DE LA PARTITION GY (piloté par la config en DB)
# ═══════════════════════════════════════════════════════════════════════
# NOTE DE MIGRATION : ce module ne lit plus de fichier .env externe. Toutes
# les valeurs (y compris les UUID de partitions, autrefois codés en dur dans
# un .env non portable) vivent exclusivement dans la table `config` de la
# base SQLite, renseignées via l'assistant de premier démarrage
# (FirstRunWizardDialog) qui les propose sous forme de liste de volumes
# détectés — jamais de saisie manuelle d'UUID.

def list_available_block_devices() -> list:
    """Interroge le backend (lsblk) pour lister les volumes disponibles avec
    leur UUID, leur label et leur taille, afin de les proposer dans un
    sélecteur graphique (jamais de saisie manuelle d'UUID par l'utilisateur).
    Retourne une liste de dicts : [{"device": "/dev/sdb1", "uuid": "...",
    "label": "...", "size": "...", "fstype": "..."}, ...]."""
    devices = []
    try:
        result = subprocess.run(
            ["lsblk", "-J", "-o", "NAME,UUID,LABEL,SIZE,FSTYPE,MOUNTPOINT,TYPE"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return devices
        data = json.loads(result.stdout)

        def _walk(entries):
            for entry in entries:
                if entry.get("type") == "part" and entry.get("uuid"):
                    devices.append({
                        "device": f"/dev/{entry['name']}",
                        "uuid": entry.get("uuid") or "",
                        "label": entry.get("label") or "(sans label)",
                        "size": entry.get("size") or "",
                        "fstype": entry.get("fstype") or "",
                        "mountpoint": entry.get("mountpoint") or "",
                    })
                if "children" in entry:
                    _walk(entry["children"])

        _walk(data.get("blockdevices", []))
    except Exception as e:
        global_log(f"⚠️ Erreur détection des volumes (lsblk): {e}")
    return devices

def auto_mount_gy(config: dict):
    """Monte la partition Gy via l'UUID stocké en base (config['gy_partition_uuid']),
    si elle n'est pas déjà montée. Ne s'exécute plus automatiquement à l'import
    du module : appelé explicitement une fois la configuration initiale
    disponible (après le premier démarrage, ou à chaque lancement normal)."""
    gy_uuid = config.get("gy_partition_uuid", "")
    if not gy_uuid:
        return False  # Pas encore configuré (premier démarrage non terminé)

    GY_DEVICE = f"UUID={gy_uuid}"
    GY_MOUNT_POINT = config.get("gy_mount_point", "/run/media/gykhamine/GY")

    is_mounted = False
    try:
        result = subprocess.run(["mountpoint", "-q", GY_MOUNT_POINT], capture_output=True)
        if result.returncode == 0:
            is_mounted = True
            global_log(f"✅ Partition GY déjà montée sur {GY_MOUNT_POINT}")
    except Exception as e:
        global_log(f"⚠️ Erreur dans auto_mount_gy: {type(e).__name__} - {e}")

    if not is_mounted:
        global_log(f"📂 Tentative de montage de {GY_DEVICE} sur {GY_MOUNT_POINT}...")
        try:
            subprocess.run(["sudo", "mkdir", "-p", GY_MOUNT_POINT], check=True, capture_output=True)
            subprocess.run(["sudo", "mount", GY_DEVICE, GY_MOUNT_POINT], check=True, capture_output=True)
            global_log("✅ Partition montée avec succès.")
            is_mounted = True
        except subprocess.CalledProcessError as e:
            global_log(f"❌ Échec du montage: {e.stderr.decode().strip() if e.stderr else e}")
            return False
        except Exception as e:
            global_log(f"❌ Erreur inattendue lors du montage: {e}")
            return False
    return is_mounted


# 2. Définition des valeurs par défaut neutres. Toute valeur réelle (ports,
# UUID, identifiants PostgreSQL/Redis...) est écrite en base par l'assistant
# de premier démarrage puis chargée via load_config() — ces valeurs par
# défaut ne servent qu'avant toute configuration.
BASE_PATH = "/run/media/gykhamine/GY/GS-CODE"

DEFAULT_CONFIG = {
    # Premier démarrage
    "setup_completed": False,

    # Lancement automatique des capsules Gykhamine (1/gy.py, 2/gy.py) au
    # démarrage de l'app — remplace l'ancien système de Runtime. Les chemins
    # sont éditables (pas de valeur figée dans le code) : par défaut ils
    # pointent vers l'emplacement conventionnel du dossier Gykhamine, mais
    # peuvent être changés depuis le panneau de contrôle ou le DB Manager.
    "gy1_path": "Gykhamine/1/gy.py",
    "gy1_auto_start": False,
    "gy2_path": "Gykhamine/2/gy.py",
    "gy2_auto_start": False,

    # LLaMA Server
    "llama_server_path": os.path.join(BASE_PATH, "gysingner/llama-server"),
    "llama_model_path": os.path.join(BASE_PATH, "gysingner/models/gysingner.gguf"),
    "llama_host": "127.0.0.1",
    "llama_port": "8080",
    
    # Gunicorn
    "gunicorn_bind": "",
    "gunicorn_ssl_enabled": False, # Gardé en dur car c'est un booléen simple
    "gunicorn_ssl_cert_path": "",
    "gunicorn_ssl_key_path": "",
    
    # Projets
    "last_project": "",
    "last_projects": [],
    
    # Dernier fichier ouvert
    "last_file": "",
    
    # Interface
    "theme": "dark",
    "open_browser_on_run": False,
    
    # Ports
    "auto_find_free_port": True,
    "default_port_range_start": 8000,
    "default_port_range_end": 8010,
    
    # Logs et Base de données
    "log_file_path": os.path.join(BASE_PATH, "logs/studio.log"),
    "db_path": os.path.join(BASE_PATH, "db/gykhamine_studio.db"),

    # Partition Gykhamine (choisie via sélecteur de volume au premier
    # démarrage, jamais saisie manuellement)
    "gy_partition_uuid": "",
    "gy_mount_point": "/run/media/gykhamine/GY",

    # PostgreSQL (partition choisie via sélecteur de volume ; identifiants
    # saisis dans l'assistant de premier démarrage, stockés en DB)
    "pg_device": "",
    "pg_mount_point": "/var/lib/pgsql/data",
    "pg_db_name": "",
    "pg_db_user": "",
    "pg_db_password": "",
    "pg_bind_ip": "127.0.0.1",
    
    # Redis
    "redis_mode": "local",
    "redis_ip": "127.0.0.1",
    "redis_port": "6379",
    "redis_data_dir": os.path.join(BASE_PATH, "data_redis/"),
    "redis_use_persistence": True,
    
    # NFS
    "nfs_server_mode": "local",
    "nfs_export_dir": os.path.join(BASE_PATH, "gy/media"),
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
    "nginx_static_path": os.path.join(BASE_PATH, "file/statics/"),
    "nginx_media_url": "/media/",
    "nginx_media_path": os.path.join(BASE_PATH, "file/media/"),
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
    "ssh_client_key": os.path.join(BASE_PATH, ".ssh/id_rsa"),
    "ssh_client_auth_mode": "key",
    
    # Virtual Environment
    "venv_name": "venv",
    "venv_path": "",
}
# ═══════════════════════════════════════════════════════════════════════
