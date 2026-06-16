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

# ═══════════════════════════════════════════════════════════════════════
#  GLOBAL CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════
APP_ID   = "org.gykhamine.studio"
VERSION  = "3.3.1"
SCRIPT_DIR = Path(__file__).parent.resolve()
LOGO_PATH  = Path("/usr/share/Gykhamine/icon/gykhamine_logo.png")


# ═══════════════════════════════════════════════════════════════════════
#  INSTALLATION AUTOMATIQUE DES FICHIERS .DESKTOP (SUDO)
# ═══════════════════════════════════════════════════════════════════════
def install_desktop_files_startup():
    """Copie les fichiers .desktop du dossier ./bureau vers /usr/share/applications/ au démarrage."""
    source_dir = SCRIPT_DIR / "Bureau"
    dest_dir = Path("/usr/share/applications")
    
    if not source_dir.exists():
        return
        
    desktop_files = list(source_dir.glob("*.desktop"))
    if not desktop_files:
        return

    files_to_copy = []
    for f in desktop_files:
        if not (dest_dir / f.name).exists():
            files_to_copy.append(f)
    
    if not files_to_copy:
        return

    print(f"📂 Détection de {len(files_to_copy)} raccourci(s) à installer...")
    
    # Tentative de copie directe
    remaining = []
    for f in files_to_copy:
        try:
            if not os.access(dest_dir, os.W_OK):
                raise PermissionError("Accès refusé")
            shutil.copy2(f, dest_dir / f.name)
            os.chmod(dest_dir / f.name, 0o644)
            print(f"   ✅ Copié : {f.name}")
        except (PermissionError, OSError):
            remaining.append(f)

    # Si des fichiers restent, on utilise SUDO via subprocess
    if remaining:
        cmd_parts = ["sudo", "bash", "-c"]
        bash_cmd = ""
        for f in remaining:
            bash_cmd += f"cp '{f}' '{dest_dir}/' && chmod 644 '{dest_dir}/{f.name}' ; "
        
        try:
            print("⚠️ Droits insuffisants. Demande de privilèges sudo...")
            subprocess.run(cmd_parts + [bash_cmd], check=True)
            print("✅ Installation réussie via sudo.")
        except Exception as e:
            print(f"❌ Échec de l'installation des raccourcis: {e}")

# Exécution immédiate au lancement du script
install_desktop_files_startup()
# ═══════════════════════════════════════════════════════════════════════
#  MONTAGE AUTOMATIQUE DE LA PARTITION GY VIA SON UUID (SUDO)
# ═══════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════
#  HELPER : LECTURE .ENV EXTERNE (Simple & Robuste)
# ═══════════════════════════════════════════════════════════════════════
def get_env_value(key: str, default: str = "") -> str:
    """
    Lit un fichier .env externe pour récupérer une variable.
    Utilise 'with' pour une gestion propre des fichiers.
    """
    env_path = Path(".env")
    if not env_path.exists():
        return default
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Match KEY=VALUE ou KEY="VALUE"
                    match = re.match(rf'^{re.escape(key)}\s*=\s*["\']?(.*?)["\']?$', line)
                    if match:
                        return match.group(1).strip()
    except Exception as e:
        global_log(f"⚠️ Erreur lecture .env pour {key}: {e}")
    return default

def auto_mount_gy():
    """
    Monte la partition Gy via son UUID si elle n'est pas déjà montée.
    """
    # ⚠️ REMPLACEZ "VOTRE_UUID_ICI" par l'UUID réel de votre partition /dev/sdb
    # Pour le trouver, lancez dans un terminal : sudo blkid /dev/sdb*
    # Exemple : GY_DEVICE = "UUID=a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8"
    GY_DEVICE = get_env_value("GY_PARTITION_UUID")  
    GY_MOUNT_POINT = "/run/media/gykhamine/GY"
    
    is_mounted = False
    try:
        result = subprocess.run(["mountpoint", "-q", GY_MOUNT_POINT], capture_output=True)
        if result.returncode == 0:
            is_mounted = True
            print(f"✅ Partition GY déjà montée sur {GY_MOUNT_POINT}")
    except Exception as e:
        global_log(f"⚠️ Erreur dans auto_mount_gy: {type(e).__name__} - {e}")

    if not is_mounted:
        print(f"📂 Tentative de montage de {GY_DEVICE} sur {GY_MOUNT_POINT}...")
        try:
            subprocess.run(["sudo", "mkdir", "-p", GY_MOUNT_POINT], check=True, capture_output=True)
            # La commande 'mount' de Linux accepte nativement le format "UUID=..."
            subprocess.run(["sudo", "mount", GY_DEVICE, GY_MOUNT_POINT], check=True, capture_output=True)
            print("✅ Partition montée avec succès.")
            is_mounted = True
        except subprocess.CalledProcessError as e:
            print(f"❌ Échec du montage: {e.stderr.decode().strip()}")
            return False
        except Exception as e:
            print(f"❌ Erreur inattendue lors du montage: {e}")
            return False
    return is_mounted
    
    
# Exécution immédiate au lancement du script
if not auto_mount_gy():
    print("⚠️ Le montage automatique a échoué. L'application va continuer mais certains chemins GY peuvent être inaccessibles.")
    
# 2. Définition des valeurs par défaut uniquement (Lecture dynamique depuis .env)
BASE_PATH = os.getenv("/run/media/gykhamine/GY/GS-CODE"))

DEFAULT_CONFIG = {
    # LLaMA Server
    "llama_server_path": os.path.join(BASE_PATH, "gysingner/llama-server"),
    "llama_model_path": os.path.join(BASE_PATH, "gysingner/models/gysingner.gguf"),
    "llama_host": get_env_value("LLAMA_HOST", ""), 
    "llama_port": get_env_value("LLAMA_PORT", ""), 
    
    # Gunicorn
    "gunicorn_bind": get_env_value("GUNICORN_BIND", ""),
    "gunicorn_ssl_enabled": False, # Gardé en dur car c'est un booléen simple
    "gunicorn_ssl_cert_path": get_env_value("GUNICORN_SSL_CERT", ""),
    "gunicorn_ssl_key_path": get_env_value("GUNICORN_SSL_KEY", ""),
    
    # Projets
    "last_project": "",
    "last_projects": [],
    
    # Interface
    "theme": "dark",
    "open_browser_on_run": False,
    
    # Ports
    "auto_find_free_port": True,
    "default_port_range_start": get_env_value("PORT_RANGE_START", ""),
    "default_port_range_end": get_env_value("PORT_RANGE_END", ""),
    
    # Logs et Base de données
    "log_file_path": os.path.join(BASE_PATH, "logs/studio.log"),
    "db_path": os.path.join(BASE_PATH, "db/gykhamine_studio.db"),
    
    # PostgreSQL (TOUT via .env - Pas de valeur par défaut sensible)
    "pg_device": get_env_value("PG_PARTITION_UUID", ""), 
    "pg_mount_point": "/var/lib/pgsql/data",
    "pg_db_name": get_env_value("PG_DB_NAME", ""),
    "pg_db_user": get_env_value("PG_DB_USER", ""),
    "pg_db_password": get_env_value("PG_DB_PASSWORD", ""), 
    "pg_bind_ip": get_env_value("PG_BIND_IP", ""),
    
    # Redis
    "redis_mode": "local",
    "redis_ip": get_env_value("REDIS_IP", ""),
    "redis_port": get_env_value("REDIS_PORT", ""),
    "redis_data_dir": os.path.join(BASE_PATH, "data_redis/"),
    "redis_use_persistence": True,
    "redis_env_path": os.path.join(BASE_PATH, "Gykhamine/gy/.env"),
    "redis_update_env": False,
    
    # NFS
    "nfs_server_mode": "local",
    "nfs_export_dir": os.path.join(BASE_PATH, "gy/media"),
    "nfs_lan_network": get_env_value("NFS_LAN_NETWORK", ""),
    "nfs_client_server_ip": get_env_value("NFS_CLIENT_SERVER_IP", ""),
    "nfs_client_export_dir": "/srv/nfs",
    "nfs_client_mount_point": os.path.expanduser("~/nfs_mount"),
    
    # Nginx
    "nginx_conf_path": "/etc/nginx/nginx.conf",
    "nginx_mode": "reverse_proxy",
    "nginx_server_name": get_env_value("NGINX_SERVER_NAME", ""),
    "nginx_listen_port": get_env_value("NGINX_LISTEN_PORT", ""),
    "nginx_upstream_name": "gunicorn",
    "nginx_upstream_servers": get_env_value("NGINX_UPSTREAM_SERVERS", ""),
    "nginx_proxy_pass": get_env_value("NGINX_PROXY_PASS", ""),
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
    "ssh_server_port": get_env_value("SSH_SERVER_PORT", ""),
    "ssh_client_host": get_env_value("SSH_CLIENT_HOST", ""),
    "ssh_client_port": get_env_value("SSH_CLIENT_PORT", ""),
    "ssh_client_user": get_env_value("SSH_CLIENT_USER", ""),
    "ssh_client_key": os.path.join(BASE_PATH, ".ssh/id_rsa"),
    "ssh_client_auth_mode": "key",
    
    # Virtual Environment
    "venv_name": "venv",
    "venv_path": "",
}# ═══════════════════════════════════════════════════════════════════════
