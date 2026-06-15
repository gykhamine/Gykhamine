#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║           GYKHAMINE STUDIO — v3.3.1 (SSL & Full DB)      ║
║     No-code visual editor for Gykhamine capsules         ║
║     Developed for the GCI project — Brazzaville, Congo   ╚
Dependencies : python3-gi, gtk4, libadwaita-1, zipfile, pandas, openpyxl, requests
Launch       : python3 gy.py
"""
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk, Pango, GtkSource
import os, sys, re, subprocess, threading, shutil, json, webbrowser, socket, zipfile, sqlite3, select, pty, tty, termios, fcntl, struct, requests
from pathlib import Path
from datetime import datetime
import time
import hashlib
# ═══════════════════════════════════════════════════════════════════════
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
        except:
            pass




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
    except Exception:
        pass

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
    
# 2. Définition des valeurs par défaut uniquement
BASE_PATH = "/run/media/gykhamine/GY/GS-CODE/"

DEFAULT_CONFIG = {
    # LLaMA Server
    "llama_server_path": os.path.join(BASE_PATH, "gysingner/llama-server"),
    "llama_model_path": os.path.join(BASE_PATH, "gysingner/models/gysingner.gguf"),
    "llama_host": "127.0.0.1",
    "llama_port": 8080,
    
    # Gunicorn
    "gunicorn_bind": "0.0.0.0:8000",
    "gunicorn_ssl_enabled": False,
    "gunicorn_ssl_cert_path": os.path.join(BASE_PATH, "ssl/cert.pem"),
    "gunicorn_ssl_key_path": os.path.join(BASE_PATH, "ssl/key.pem"),
    
    # Projets
    "last_project": "",
    "last_projects": [],
    
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
    
    # PostgreSQL
    "pg_device": get_env_value("PG_PARTITION_UUID"),
    "pg_mount_point": "/var/lib/pgsql/data",
    "pg_db_name": "ma_base",
    "pg_db_user": "mon_user",
    "pg_db_password": "mot_de_passe",
    "pg_bind_ip": "127.0.0.1",
    
    # Redis
    "redis_mode": "local",
    "redis_ip": "127.0.0.1",
    "redis_port": 6379,
    "redis_data_dir": os.path.join(BASE_PATH, "data_redis/"),
    "redis_use_persistence": True,
    "redis_env_path": os.path.join(BASE_PATH, "Gykhamine/gy/.env"),
    "redis_update_env": False,
    
    # NFS
    "nfs_server_mode": "local",
    "nfs_export_dir": os.path.join(BASE_PATH, "gy/media"),
    "nfs_lan_network": "192.168.1.0/24",
    "nfs_client_server_ip": "192.168.1.10",
    "nfs_client_export_dir": "/srv/nfs",
    "nfs_client_mount_point": os.path.expanduser("~/nfs_mount"),
    
    # Nginx
    "nginx_conf_path": "/etc/nginx/nginx.conf",
    "nginx_mode": "reverse_proxy",
    "nginx_server_name": "localhost",
    "nginx_listen_port": "443",
    "nginx_upstream_name": "gunicorn",
    "nginx_upstream_servers": "127.0.0.1:8000, 127.0.0.1:8001, 127.0.0.1:8002",
    "nginx_proxy_pass": "http://gunicorn",
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
    "ssh_server_port": 22,
    "ssh_client_host": "192.168.1.10",
    "ssh_client_port": 22,
    "ssh_client_user": "root",
    "ssh_client_key": os.path.join(BASE_PATH, ".ssh/id_rsa"),
    "ssh_client_auth_mode": "key",
    
    # Virtual Environment
    "venv_name": "venv",
    "venv_path": "",
}
# ═══════════════════════════════════════════════════════════════════════
#  SQLITE ENGINE — CONFIG + SMART MEMORY + LOGS
# ═══════════════════════════════════════════════════════════════════════
def _get_db_path(cfg_override: str = None) -> Path:
    # Utilise le chemin passé en argument, sinon celui de la config par défaut/env
    path_str = cfg_override if cfg_override else DEFAULT_CONFIG["db_path"]
    return Path(path_str)

def _init_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    cur.execute("CREATE TABLE IF NOT EXISTS recent_projects (id INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT UNIQUE NOT NULL, opened_at TEXT NOT NULL)")
    cur.execute("CREATE TABLE IF NOT EXISTS memory (id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT NOT NULL, file_path TEXT NOT NULL, block_name TEXT, action TEXT, ts TEXT NOT NULL, UNIQUE(project, file_path, block_name))")
    
    # --- Table 1 : Cache Commandes Shell ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_cmd_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            intent_hash TEXT UNIQUE NOT NULL, 
            command TEXT NOT NULL, 
            is_process INTEGER DEFAULT 0, 
            created_at TEXT NOT NULL
        )
    """)

    # --- Table 2 : Cache Blocs de Code (Python, C, JS...) ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_block_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            intent_hash TEXT UNIQUE NOT NULL, 
            content TEXT NOT NULL, 
            block_type TEXT DEFAULT 'code', 
            created_at TEXT NOT NULL
        )
    """)

    # --- Table 3 : Cache Processus & JSON (Élaborateur) ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_process_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            intent_hash TEXT UNIQUE NOT NULL, 
            json_content TEXT NOT NULL, 
            role_type TEXT DEFAULT 'general', 
            created_at TEXT NOT NULL
        )
    """)
    
    con.commit()
    con.close()
    
def load_config() -> dict:
    db_path = _get_db_path()
    _init_db(db_path)
    cfg = dict(DEFAULT_CONFIG)
    try:
        con = sqlite3.connect(str(db_path))
        rows = con.execute("SELECT key, value FROM config").fetchall()
        con.close()
        for key, val in rows:
            try: cfg[key] = json.loads(val)
            except Exception: cfg[key] = val
    except Exception: pass
    return cfg

def save_config(cfg: dict):
    db_path = _get_db_path(cfg.get("db_path"))
    _init_db(db_path)
    con = sqlite3.connect(str(db_path))
    for key, val in cfg.items():
        if key == "last_projects": continue
        con.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, json.dumps(val)))
    con.commit()
    con.close()

def add_recent_project(project_path: str, config: dict):
    db_path = _get_db_path(config.get("db_path"))
    _init_db(db_path)
    con = sqlite3.connect(str(db_path))
    now = datetime.now().isoformat()
    con.execute("INSERT OR REPLACE INTO recent_projects (path, opened_at) VALUES (?, ?)", (project_path, now))
    con.execute("DELETE FROM recent_projects WHERE id NOT IN (SELECT id FROM recent_projects ORDER BY opened_at DESC LIMIT 20)")
    con.commit()
    con.close()

def get_recent_projects(config: dict) -> list:
    db_path = _get_db_path(config.get("db_path"))
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        rows = con.execute("SELECT path FROM recent_projects ORDER BY opened_at DESC LIMIT 20").fetchall()
        con.close()
        return [r[0] for r in rows if Path(r[0]).exists()]
    except Exception: return []

def memory_record(config: dict, project: str, file_path: str, block_name: str = None, action: str = "edit"):
    db_path = _get_db_path(config.get("db_path"))
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        con.execute("INSERT OR REPLACE INTO memory (project, file_path, block_name, action, ts) VALUES (?, ?, ?, ?, ?)", (project, file_path, block_name or "", action, datetime.now().isoformat()))
        con.commit()
        con.close()
    except Exception as e: 
        global_log(f"❌ Échec enregistrement mémoire (SQLite): {e}")

def _get_log_path(config: dict) -> Path:
    p = Path(config.get("log_file_path", DEFAULT_CONFIG["log_file_path"]))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def log_to_file(config: dict, message: str):
    try:
        with open(_get_log_path(config), "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception as e: 
        global_log(f"❌ Échec écriture fichier log: {e}")
        



def _get_intent_hash(intent: str) -> str:
    return hashlib.md5(intent.strip().lower().encode('utf-8')).hexdigest()

# --- Fonctions pour le Générateur de Commandes (Shell) ---
def get_cached_command(intent: str) -> dict:
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        row = con.execute("SELECT command, is_process FROM ai_cmd_cache WHERE intent_hash = ?", (_get_intent_hash(intent),)).fetchone()
        con.close()
        if row: return {"command": row[0], "is_process": bool(row[1])}
    except Exception: pass
    return None

def save_command_to_cache(intent: str, command: str, is_process: bool = False):
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        con.execute("INSERT OR REPLACE INTO ai_cmd_cache (intent_hash, command, is_process, created_at) VALUES (?, ?, ?, ?)", 
                    (_get_intent_hash(intent), command, int(is_process), datetime.now().isoformat()))
        con.commit(); con.close()
    except Exception as e: global_log(f"❌ Erreur cache cmd: {e}")

# --- Fonctions pour le Modificateur de Blocs (Code) ---
def get_cached_block(intent: str) -> dict:
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        row = con.execute("SELECT content, block_type FROM ai_block_cache WHERE intent_hash = ?", (_get_intent_hash(intent),)).fetchone()
        con.close()
        if row: return {"content": row[0], "block_type": row[1]}
    except Exception: pass
    return None

def save_block_to_cache(intent: str, content: str, block_type: str = 'code'):
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        con.execute("INSERT OR REPLACE INTO ai_block_cache (intent_hash, content, block_type, created_at) VALUES (?, ?, ?, ?)", 
                    (_get_intent_hash(intent), content, block_type, datetime.now().isoformat()))
        con.commit(); con.close()
    except Exception as e: global_log(f"❌ Erreur cache bloc: {e}")

# --- Fonctions pour l'Élaborateur (Processus JSON) ---
def get_cached_process(intent: str) -> dict:
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        row = con.execute("SELECT json_content, role_type FROM ai_process_cache WHERE intent_hash = ?", (_get_intent_hash(intent),)).fetchone()
        con.close()
        if row: return {"json_content": row[0], "role_type": row[1]}
    except Exception: pass
    return None

def save_process_to_cache(intent: str, json_content: str, role_type: str = 'general'):
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        con.execute("INSERT OR REPLACE INTO ai_process_cache (intent_hash, json_content, role_type, created_at) VALUES (?, ?, ?, ?)", 
                    (_get_intent_hash(intent), json_content, role_type, datetime.now().isoformat()))
        con.commit(); con.close()
    except Exception as e: global_log(f"❌ Erreur cache process: {e}")


def is_port_in_use(port: int, host: str = "0.0.0.0") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex((host, port)) == 0

def find_free_port(start_port: int, end_port: int, host: str = "0.0.0.0") -> int:
    for port in range(start_port, end_port + 1):
        if not is_port_in_use(port, host): return port
    return None

def kill_process_on_port(port: int) -> bool:
    try:
        result = subprocess.run(f"lsof -ti:{port}", shell=True, capture_output=True, text=True)
        if result.stdout.strip():
            for pid in result.stdout.strip().split('\n'): subprocess.run(f"kill -9 {pid}", shell=True)
            return True
    except Exception: pass
    return False

# ═══════════════════════════════════════════════════════════════════════
#  SYNTAX HIGHLIGHTING ENGINE & PARSER
# ═══════════════════════════════════════════════════════════════════════
def apply_syntax_highlighting(textview, lang):
    buf = textview.get_buffer()
    text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
    tag_table = buf.get_tag_table()
    colors = {
        "keyword": ("#c678dd", Pango.Weight.BOLD),
        "type": ("#e5c07b", Pango.Weight.NORMAL),
        "function": ("#61afef", Pango.Weight.NORMAL),
        "variable": ("#e06c75", Pango.Weight.NORMAL),
        "string": ("#98c379", Pango.Weight.NORMAL),
        "comment": ("#5c6370", Pango.Weight.NORMAL, True),
        "number": ("#d19a66", Pango.Weight.NORMAL),
        "tag": ("#e06c75", Pango.Weight.NORMAL),
        "attr": ("#d19a66", Pango.Weight.NORMAL),
        "jinja": ("#c678dd", Pango.Weight.BOLD),
        "preproc": ("#56b6c2", Pango.Weight.NORMAL),
    }
    for name, props in colors.items():
        tag = Gtk.TextTag(name=name)
        tag.set_property("foreground", props[0])
        if len(props) > 1 and props[1] != Pango.Weight.NORMAL: tag.set_property("weight", props[1])
        if len(props) > 2 and props[2]: tag.set_property("style", Pango.Style.ITALIC)
        if not tag_table.lookup(name): tag_table.add(tag)
    for tag_name in colors.keys():
        buf.remove_tag_by_name(tag_name, buf.get_start_iter(), buf.get_end_iter())
    
    patterns = []
    if lang in ("html", "jinja"):
        patterns = [(r'(<!--[\s\S]*?-->)', "comment"), (r'(\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\})', "jinja"), (r'(</?[a-zA-Z0-9:_-]+)', "tag"), (r'\b([a-zA-Z0-9:_-]+)(?=\s*=)', "attr"), (r'("[^"]*"|\'[^\']*\')', "string")]
    elif lang in ("python", "py"):
        patterns = [(r'(#.*)', "comment"), (r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"[^"]*"|\'[^\']*\')', "string"), (r'\b(True|False|None|and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield)\b', "keyword"), (r'\b\d+\b', "number"), (r'\bclass\s+([A-Z]\w*)', "type"), (r'(@\w+)', "function"), (r'\b[a-zA-Z_]\w*(?=\s*\()', "function"), (r'\b[a-zA-Z_]\w*(?=\s*=)', "variable")]
    elif lang in ("c", "cpp", "h"):
        patterns = [(r'(//.*|/\*[\s\S]*?\*/)', "comment"), (r'("[^"]*"|\'[^\']*\'|`[^`]*`)', "string"), (r'^\s*#\s*\w+', "preproc"), (r'\b(auto|break|case|char|const|continue|default|do|double|else|enum|extern|float|for|goto|if|inline|int|long|register|return|short|signed|sizeof|static|struct|switch|typedef|union|unsigned|void|volatile|while|class|public|private|protected|virtual|template|namespace|bool|true|false|wchar_t)\b', "keyword"), (r'\b\d+\b', "number"), (r'\b[A-Z]\w*\b', "type"), (r'\b[a-zA-Z_]\w*(?=\s*\()', "function")]
    elif lang in ("css",):
        patterns = [(r'(/\*[\s\S]*?\*/)', "comment"), (r'("[^"]*"|\'[^\']*\')', "string"), (r'(@[a-zA-Z-]+)', "keyword"), (r'(\.[a-zA-Z0-9_-]+|#[a-zA-Z0-9_-]+)', "type"), (r'\b[a-zA-Z-]+(?=\s*:)', "attr"), (r'#[0-9a-fA-F]{3,6}\b|\b\d+(?:px|em|rem|%|vh|vw|deg|s|ms)?\b', "number")]
    elif lang in ("javascript", "js"):
        patterns = [(r'(//.*|/\*[\s\S]*?\*/)', "comment"), (r'("[^"]*"|\'[^\']*\'|`[^`]*`)', "string"), (r'\b(break|case|catch|class|const|continue|debugger|default|delete|do|else|export|extends|finally|for|function|if|import|in|instanceof|new|return|super|switch|this|throw|try|typeof|var|void|while|with|yield|let|async|await|of)\b', "keyword"), (r'\b\d+\b', "number"), (r'\b[A-Z]\w*\b', "type"), (r'\b[a-zA-Z_]\w*(?=\s*\()', "function"), (r'\b[a-zA-Z_]\w*(?=\s*=)', "variable")]
    elif lang in ("bash", "sh", "pl"):
        patterns = [(r'(#.*)', "comment"), (r'("[^"]*"|\'[^\']*\')', "string"), (r'\b(if|then|else|elif|fi|case|esac|for|while|until|do|done|in|function|return|exit|break|continue|export|source|local)\b', "keyword"), (r'(\$[a-zA-Z_]\w*|\$\{[^}]+\})', "variable"), (r'\b(echo|cd|ls|pwd|grep|awk|sed|chmod|chown|sudo|apt|mkdir|rm|cp|mv|cat|find|curl|wget|python3|pip)\b', "function")]
    
    for pattern, tag_name in patterns:
        for match in re.finditer(pattern, text):
            buf.apply_tag_by_name(tag_name, buf.get_iter_at_offset(match.start()), buf.get_iter_at_offset(match.end()))

SEPARATOR_RE = re.compile(r'^#{4,}.*$|^/{4,}.*$|^-{4,}.*$', re.MULTILINE)

def _find_matching_brace(lines, start_idx):
    """Trouve l'index de la ligne contenant l'accolade fermante correspondante."""
    depth = 0
    for i in range(start_idx, len(lines)):
        # On compte les accolades. (Une version parfaite ignorerait les chaînes, 
        # mais ce compteur suffit pour 99% du code bien formaté).
        depth += lines[i].count('{') - lines[i].count('}')
        if depth == 0:
            return i
    return len(lines) - 1










def _get_indent(line: str) -> int:
    """Calcule l'indentation réelle (espaces + tabulations)"""
    return len(line) - len(line.lstrip(' \t'))

def _get_decorator_start(lines: list, idx: int) -> int:
    """Remonte les lignes pour trouver le début de la chaîne de décorateurs"""
    start = idx
    for k in range(idx - 1, -1, -1):
        stripped = lines[k].strip()
        if stripped.startswith('@'):
            start = k
        elif stripped == '' or stripped.startswith('#'):
            continue # Ignore les lignes vides ou commentaires entre le décorateur et la def
        else:
            break # On a touché un autre code, on s'arrête
    return start

def _find_function_end(lines: list, start_idx: int, base_indent: int) -> int:
    """Trouve la fin d'une fonction ou classe, en partant de la ligne de définition (pas du décorateur)."""
    i = start_idx + 1
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        current_indent = _get_indent(line)
        # Dès qu'on retombe au niveau d'indentation de la fonction/classe, le bloc est fini
        if current_indent <= base_indent:
            return i - 1
        i += 1
    return len(lines) - 1

def _find_control_flow_end(lines: list, start_idx: int, base_indent: int, allow_continuations: bool = False) -> int:
    """Trouve la fin d'un bloc en se basant strictement sur l'indentation."""
    continuations = {'elif', 'else', 'except', 'finally'}
    i = start_idx + 1
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        current_indent = _get_indent(line)
        if current_indent < base_indent:
            return i - 1
        elif current_indent == base_indent:
            is_continuation = any(stripped.startswith(kw) for kw in continuations)
            if not allow_continuations or not is_continuation:
                return i - 1
        i += 1
    return len(lines) - 1




def _find_if_else_chain_end(lines: list, start_idx: int) -> int:
    """Trouve la fin d'une chaîne if/else if/else ou try/catch/finally en JS/C."""
    base_indent = _get_indent(lines[start_idx])
    i = start_idx + 1
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        
        current_indent = _get_indent(line)
        
        # Si on revient à l'indentation de base ou moins, c'est fini
        if current_indent <= base_indent:
            # Vérifier si c'est une continuation valide (else, catch, finally)
            is_continuation = any(stripped.startswith(kw) for kw in ['else', 'catch', 'finally'])
            if not is_continuation:
                return i - 1
            # Si c'est une continuation, on continue la boucle pour trouver la fin de ce nouveau bloc
            base_indent = current_indent
            
        i += 1
    return len(lines) - 1

def _find_brace_or_stmt_end(lines: list, start_idx: int) -> int:
    """
    Trouve la fin d'un bloc délimité par des accolades {} en ignorant 
    les accolades présentes dans les chaînes de caractères et les commentaires.
    """
    depth = 0
    found_open = False
    in_single_quote = False
    in_double_quote = False
    in_backtick = False
    in_line_comment = False
    in_block_comment = False
    
    for i in range(start_idx, len(lines)):
        line = lines[i]
        j = 0
        while j < len(line):
            char = line[j]
            next_char = line[j+1] if j + 1 < len(line) else ''
            
            # Gestion des commentaires
            if not in_single_quote and not in_double_quote and not in_backtick:
                if not in_block_comment and char == '/' and next_char == '/':
                    in_line_comment = True
                if not in_line_comment and char == '/' and next_char == '*':
                    in_block_comment = True
                    j += 1 # Sauter le *
                if in_block_comment and char == '*' and next_char == '/':
                    in_block_comment = False
                    j += 1 # Sauter le /
            
            # Gestion des chaînes de caractères
            if not in_line_comment and not in_block_comment:
                if char == '\\' and (in_single_quote or in_double_quote or in_backtick):
                    j += 1 # Sauter le caractère échappé
                    continue
                
                if char == "'" and not in_double_quote and not in_backtick:
                    in_single_quote = not in_single_quote
                elif char == '"' and not in_single_quote and not in_backtick:
                    in_double_quote = not in_double_quote
                elif char == '`' and not in_single_quote and not in_double_quote:
                    in_backtick = not in_backtick
                
                # Comptage des accolades uniquement si on n'est ni dans une chaîne ni dans un commentaire
                if not in_single_quote and not in_double_quote and not in_backtick:
                    if char == '{':
                        depth += 1
                        found_open = True
                    elif char == '}':
                        depth -= 1
                        if found_open and depth == 0:
                            return i
            
            j += 1
        
        # Fin de ligne : reset du commentaire ligne
        in_line_comment = False
        
    # Si on arrive ici, c'est qu'on n'a pas trouvé la fermeture correspondante
    return len(lines) - 1    






def _parse_python_blocks(code: str, file_path: str) -> list[dict]:
    """Parseur Python optimisé : Décorateurs groupés, if/else fusionnés, indentation préservée, SANS boucle infinie."""
    lines = code.splitlines(keepends=True)
    blocks = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
            
        current_indent = _get_indent(line)
        
        # Détection des structures
        is_class = re.match(r'^class\s+(\w+)', stripped)
        is_func = re.match(r'^(async\s+)?def\s+(\w+)', stripped)
        is_import = re.match(r'^(import|from)\s+', stripped)
        is_main = re.match(r'^if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:', stripped)
        is_if = re.match(r'^if\s+', stripped)
        is_try = re.match(r'^try\s*:', stripped)
        is_docstring = stripped.startswith('"""') or stripped.startswith("'''")
        is_decorator = stripped.startswith('@')
        
        # CORRECTION CRITIQUE : On ignore les décorateurs ici pour qu'ils soient capturés 
        # par le bloc is_func/is_class qui suit, évitant ainsi la boucle infinie.
        if is_decorator:
            i += 1
            continue
            
        if is_class or is_func:
            # 1. Capturer les décorateurs associés
            start_idx = _get_decorator_start(lines, i)
            # 2. L'indentation de référence est celle de la fonction/classe
            base_indent = current_indent
            # 3. Trouver la fin en partant de la ligne de la fonction (i), pas du décorateur
            end_idx = _find_function_end(lines, i, base_indent)
            
            raw_code = "".join(lines[start_idx:end_idx + 1])
            name = is_class.group(1) if is_class else is_func.group(2)
            btype = "class" if is_class else "function"
            
            blocks.append({
                "type": btype,
                "name": f"{name} (Indent: {base_indent})",
                "code": raw_code,
                "start": start_idx,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
            
        elif is_if or is_try:
            # Fusionne if/elif/else ou try/except/finally
            end_idx = _find_control_flow_end(lines, i, current_indent, allow_continuations=True)
            raw_code = "".join(lines[i:end_idx + 1])
            name = "Condition (if/else)" if is_if else "Gestion d'erreur (try/except)"
            
            blocks.append({
                "type": "logic_block",
                "name": f"{name} (Indent: {current_indent})",
                "code": raw_code,
                "start": i,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
            
        elif is_import:
            end_idx = _find_control_flow_end(lines, i, current_indent, allow_continuations=False)
            blocks.append({
                "type": "import",
                "name": "Imports",
                "code": "".join(lines[i:end_idx + 1]),
                "start": i,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
            
        elif stripped.startswith('#') or is_docstring:
            end_idx = i
            for k in range(i + 1, len(lines)):
                k_stripped = lines[k].strip()
                if k_stripped.startswith('#') or k_stripped.startswith('"""') or k_stripped.startswith("'''") or not k_stripped:
                    end_idx = k
                else:
                    break
            blocks.append({
                "type": "comment",
                "name": "Commentaire / Docstring",
                "code": "".join(lines[i:end_idx + 1]),
                "start": i,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
            
        else:
            # Fallback pour tout autre code racine
            end_idx = _find_control_flow_end(lines, i, current_indent, allow_continuations=False)
            blocks.append({
                "type": "other",
                "name": f"Bloc de code (Indent: {current_indent})",
                "code": "".join(lines[i:end_idx + 1]),
                "start": i,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
            
    return blocks











def _parse_template_blocks(code: str, file_path: str) -> list[dict]:
    """
    Parseur HTML/Jinja RADICAL :
    - Ignore TOUTES les balises HTML structurelles (div, section, etc.).
    - Ne découpe QUE sur les blocs logiques (Django/Jinja) et les scripts/styles.
    - Retourne le fichier complet si aucun bloc logique n'est trouvé.
    - Sans récursion.
    """
    lines = code.splitlines(keepends=True)
    blocks = []
    
    # Indices des lignes déjà attribuées à un bloc spécial
    used_lines = set()
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if not stripped:
            i += 1
            continue
            
        start_idx = i
        end_idx = i
        block_type = None
        block_name = "Bloc"
        
        # 1. Détection Bloc Django/Jinja Root ({% block ... %})
        m_block = re.match(r"\{%-?\s*block\s+(\w+).*?%\}", stripped, re.IGNORECASE)
        if m_block:
            block_type = "django_block"
            block_name = f"block: {m_block.group(1)}"
            # Chercher {% endblock %}
            for k in range(i + 1, len(lines)):
                if re.match(r"\{%-?\s*endblock\b", lines[k].strip(), re.IGNORECASE):
                    end_idx = k
                    break
            else:
                end_idx = len(lines) - 1 # Fermeture implicite à la fin
        
        # 2. Détection Style
        elif re.match(r"<style(\s[^>]*)?>", stripped, re.IGNORECASE):
            block_type = "style"
            block_name = "<style>"
            for k in range(i + 1, len(lines)):
                if re.match(r"</style\s*>", lines[k].strip(), re.IGNORECASE):
                    end_idx = k
                    break
            else:
                end_idx = len(lines) - 1

        # 3. Détection Script
        elif re.match(r"<script(\s[^>]*)?>", stripped, re.IGNORECASE):
            block_type = "script"
            block_name = "<script>"
            for k in range(i + 1, len(lines)):
                if re.match(r"</script\s*>", lines[k].strip(), re.IGNORECASE):
                    end_idx = k
                    break
            else:
                end_idx = len(lines) - 1
        
        # Si un bloc spécial a été détecté
        if block_type:
            raw_code = "".join(lines[start_idx:end_idx + 1])
            blocks.append({
                "type": block_type,
                "name": block_name,
                "code": raw_code,
                "start": start_idx,
                "end": end_idx,
                "children": []
            })
            # Marquer les lignes comme utilisées
            for x in range(start_idx, end_idx + 1):
                used_lines.add(x)
            i = end_idx + 1
            continue
            
        i += 1

    # SI AUCUN BLOC LOGIQUE N'A ÉTÉ TROUVÉ : Retourner le fichier entier
    if not blocks:
        return [{
            "type": "html_file",
            "name": Path(file_path).name if file_path else "template.html",
            "code": code,
            "start": 0,
            "end": len(lines) - 1,
            "children": []
        }]

    # Optionnel : Si vous voulez aussi récupérer le HTML "orphelin" entre les blocs django
    # comme un bloc "Autre", décommentez ci-dessous. Sinon, seul le fichier complet ou les blocs logiques sont retournés.
    """
    orphan_start = None
    for idx in range(len(lines)):
        if idx not in used_lines:
            if orphan_start is None: orphan_start = idx
        else:
            if orphan_start is not None:
                blocks.append({
                    "type": "html_fragment",
                    "name": "HTML Orphelin",
                    "code": "".join(lines[orphan_start:idx]),
                    "start": orphan_start,
                    "end": idx - 1,
                    "children": []
                })
                orphan_start = None
    if orphan_start is not None:
        blocks.append({
            "type": "html_fragment",
            "name": "HTML Orphelin",
            "code": "".join(lines[orphan_start:]),
            "start": orphan_start,
            "end": len(lines) - 1,
            "children": []
        })
    blocks.sort(key=lambda b: b['start'])
    """
    
    return blocks
    
    
def _parse_css_blocks(code: str, file_path: str) -> list[dict]:
    lines = code.splitlines(keepends=True)
    
    def _extract_css_children(start_idx, end_idx):
        """Extrait récursivement les sélecteurs, variables, propriétés et règles @"""
        children = []
        i = start_idx
        while i <= end_idx:
            line = lines[i]
            stripped = line.strip()
            
            # Ignorer les lignes vides et les commentaires simples
            if not stripped or stripped.startswith('/*') or stripped.startswith('*'):
                i += 1
                continue

            # 1. Détection des règles @ (@media, @keyframes, @font-face, @import, etc.)
            is_at_rule = re.match(r'^@([\w-]+)', stripped)
            if is_at_rule:
                rule_type = is_at_rule.group(1)
                block_name = stripped[:60]
                
                # Trouver le début de l'accolade (parfois sur la ligne suivante)
                brace_start = i
                for k in range(i, min(i + 10, len(lines))):
                    if '{' in lines[k]:
                        brace_start = k
                        break
                
                brace_end = _find_matching_brace(lines, brace_start)
                raw_code = "".join(lines[i:brace_end + 1])
                
                # APPEL RÉCURSIF : Analyser l'intérieur du @media ou @keyframes
                sub_children = _extract_css_children(brace_start + 1, brace_end - 1)
                
                children.append({
                    "type": f"css_at_{rule_type}",
                    "name": block_name,
                    "code": raw_code,
                    "start": i,
                    "end": brace_end,
                    "children": sub_children
                })
                i = brace_end + 1
                continue

            # 2. Détection des Sélecteurs standards (.class, #id, element) contenant { }
            if '{' in stripped and not stripped.startswith('--'):
                # Nettoyer le nom du sélecteur (enlever le { et les espaces)
                block_name = stripped.split('{')[0].strip()[:50]
                
                brace_start = i
                for k in range(i, min(i + 5, len(lines))):
                    if '{' in lines[k]:
                        brace_start = k
                        break
                
                brace_end = _find_matching_brace(lines, brace_start)
                raw_code = "".join(lines[i:brace_end + 1])
                
                # APPEL RÉCURSIF : Analyser les propriétés à l'intérieur du sélecteur
                sub_children = _extract_css_children(brace_start + 1, brace_end - 1)
                
                children.append({
                    "type": "css_selector",
                    "name": block_name,
                    "code": raw_code,
                    "start": i,
                    "end": brace_end,
                    "children": sub_children
                })
                i = brace_end + 1
                continue

            # 3. Détection des Variables CSS (--nom-variable: valeur;)
            is_variable = re.match(r'^--[\w-]+\s*:', stripped)
            # 4. Détection des Propriétés simples (se terminant par ;)
            is_property = stripped.endswith(';') and not is_variable

            if is_variable or is_property:
                block_type = "css_variable" if is_variable else "css_property"
                # Extraire le nom de la variable ou de la propriété (avant les deux-points)
                block_name = stripped.split(':')[0].strip()[:40] if ':' in stripped else stripped[:40]
                
                # Une propriété peut s'étaler sur plusieurs lignes, on cherche le ;
                prop_end = i
                for k in range(i, min(i + 15, len(lines))):
                    if ';' in lines[k]:
                        prop_end = k
                        break
                
                raw_code = "".join(lines[i:prop_end + 1])
                
                children.append({
                    "type": block_type,
                    "name": block_name,
                    "code": raw_code,
                    "start": i,
                    "end": prop_end,
                    "children": [] # Les propriétés sont des feuilles (pas d'enfants)
                })
                i = prop_end + 1
                continue

            # Fallback : si c'est une ligne bizarre, on avance
            i += 1
            
        return children

    # --- Parsing du niveau racine ---
    # On traite tout le fichier comme un conteneur dont on extrait les enfants de premier niveau
    root_children = _extract_css_children(0, len(lines) - 1)
    
    if root_children:
        return [{
            "type": "css_file",
            "name": Path(file_path).name if file_path else "Stylesheet.css",
            "code": code,
            "start": 0,
            "end": len(lines) - 1,
            "children": root_children
        }]
    
    # Fallback si le fichier est vide ou incompréhensible
    return [{"type": "css_file", "name": "Stylesheet", "code": code, "start": 0, "end": len(lines)-1, "children": []}]


def _parse_js_blocks(code: str, file_path: str) -> list[dict]:
    """Parseur JS robuste : Se concentre uniquement sur les fonctions, classes et exports majeurs via les accolades."""
    lines = code.splitlines(keepends=True)
    blocks = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if not stripped or stripped.startswith('//'):
            i += 1
            continue
            
        # Détection des structures principales
        is_class = re.match(r'^(export\s+)?(default\s+)?class\s+(\w+)', stripped)
        # Match function declaration or arrow function assignment
        is_func = re.match(r'^(export\s+)?(default\s+)?(async\s+)?function\s+(\w+)|^(export\s+)?(const|let|var)\s+(\w+)\s*=\s*(async\s+)?(?:function|\([^)]*\)\s*=>|\w+\s*=>)', stripped)
        is_export_default = re.match(r'^export\s+default\s+', stripped)
        
        start_idx = -1
        name = "Anonymous"
        btype = "other"
        
        if is_class:
            start_idx = i
            name = is_class.group(3)
            btype = "class"
        elif is_func:
            start_idx = i
            if is_func.group(4): name = is_func.group(4) # Named function
            elif is_func.group(6): name = is_func.group(6) # Variable assignment
            btype = "function"
        elif is_export_default and ('{' in stripped or 'function' in stripped or 'class' in stripped):
             # Cas export default { ... } ou export default function...
             start_idx = i
             name = "Default Export"
             btype = "other"

        if start_idx != -1:
            # Chercher l'accolade ouvrante
            brace_idx = -1
            for k in range(i, min(i + 20, len(lines))):
                if '{' in lines[k]:
                    brace_idx = k
                    break
            
            if brace_idx != -1:
                end_idx = _find_brace_or_stmt_end(lines, brace_idx)
                raw_code = "".join(lines[start_idx:end_idx + 1])
                
                blocks.append({
                    "type": btype,
                    "name": name,
                    "code": raw_code,
                    "start": start_idx,
                    "end": end_idx,
                    "children": []
                })
                i = end_idx + 1
                continue
        
        i += 1
        
    return blocks

def _parse_c_blocks(code: str, file_path: str) -> list[dict]:
    """Parseur C/C++ robuste : Se concentre uniquement sur les fonctions, structs et classes via les accolades."""
    lines = code.splitlines(keepends=True)
    blocks = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
            i += 1
            continue
            
        # Détection des structures principales
        is_struct_class = re.match(r'^(typedef\s+)?(struct|class|enum|union|namespace)\s+(\w*)', stripped)
        # Fonction C classique : type nom(...)
        is_func = re.match(r'^(void|int|char|float|double|bool|auto|unsigned|signed|long|short|size_t|ssize_t|uint\d+_t|int\d+_t|struct\s+\w+)\s+\**\s*(\w+)\s*\(', stripped)
        
        start_idx = -1
        name = "Unknown"
        btype = "other"
        
        if is_struct_class:
            start_idx = i
            name = is_struct_class.group(3) if is_struct_class.group(3) else "Anonymous"
            btype = "class" # On groupe struct/class/enum sous "class" pour l'icône
        elif is_func:
            start_idx = i
            name = is_func.group(2)
            btype = "function"
            
        if start_idx != -1:
            # Chercher l'accolade ouvrante
            brace_idx = -1
            for k in range(i, min(i + 20, len(lines))):
                if '{' in lines[k]:
                    brace_idx = k
                    break
            
            if brace_idx != -1:
                end_idx = _find_brace_or_stmt_end(lines, brace_idx)
                raw_code = "".join(lines[start_idx:end_idx + 1])
                
                blocks.append({
                    "type": btype,
                    "name": name,
                    "code": raw_code,
                    "start": start_idx,
                    "end": end_idx,
                    "children": []
                })
                i = end_idx + 1
                continue
        
        i += 1
        
    return blocks    
def parse_blocks(code: str, file_path: str = "") -> list[dict]:
    ext = Path(file_path).suffix.lower()
    if ext in ('.html', '.jinja', '.jinja2', '.htm'): return _parse_template_blocks(code, file_path)
    elif ext == '.css': return _parse_css_blocks(code, file_path)
    elif ext == '.js': return _parse_js_blocks(code, file_path)
    elif ext in ('.c', '.cpp', '.h'): return _parse_c_blocks(code, file_path)
    else: return _parse_python_blocks(code, file_path)

# ═══════════════════════════════════════════════════════════════════════
#  NATIVE TTY TERMINAL (POPUP)
# ═══════════════════════════════════════════════════════════════════════
class NativeTtyTerminal(Gtk.Window):
    def __init__(self, parent, title, command, cwd=None):
        super().__init__(title=title, transient_for=parent, default_width=900, default_height=600)
        self.add_css_class("rounded-dialog")
        self.command = command
        self.cwd = cwd
        self.pid = None
        self.master_fd = None
        self.is_running = False
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(box)
        
        header = Gtk.HeaderBar()
        btn_close = Gtk.Button(label="✕ Close Terminal")
        btn_close.connect("clicked", lambda *_: self._close_terminal())
        header.pack_end(btn_close)
        box.append(header)
        
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_hexpand(True)
        self.scrolled.set_vexpand(True)
        box.append(self.scrolled)
        
        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_cursor_visible(True)
        self.text_view.set_monospace(True)
        self.text_view.set_wrap_mode(Gtk.WrapMode.NONE)
        self.text_view.add_css_class("terminal-tty-view")
        
        provider = Gtk.CssProvider()
        provider.load_from_data(b""".terminal-tty-view { background-color: #000000 !important; color: #cccccc; font-family: 'Fira Code', 'Consolas', 'Monaco', monospace; font-size: 14px; padding: 10px; }""")
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        self.scrolled.set_child(self.text_view)
        self.buf = self.text_view.get_buffer()
        
        self.key_controller = Gtk.EventControllerKey()
        self.key_controller.connect("key-pressed", self._on_key_pressed)
        self.text_view.add_controller(self.key_controller)
        
        self.resize_controller = Gtk.EventControllerMotion()
        self.connect("notify::default-width", self._on_resize)
        self.connect("notify::default-height", self._on_resize)
        
        self.show()
        self._spawn_shell()

    def _spawn_shell(self):
        self.pid, self.master_fd = pty.fork()
        if self.pid == 0:
            try:
                if self.cwd: os.chdir(self.cwd)
                if self.command: os.execvp("bash", ["bash", "-c", self.command])
                else: os.execvp("bash", ["bash"])
            except Exception as e:
                print(f"Exec error: {e}")
                os._exit(1)
        else:
            self.is_running = True
            attrs = termios.tcgetattr(self.master_fd)
            attrs[3] = attrs[3] & ~termios.ECHO
            termios.tcsetattr(self.master_fd, termios.TCSANOW, attrs)
            threading.Thread(target=self._read_loop, daemon=True).start()

    def _read_loop(self):
        while self.is_running:
            try:
                r, _, _ = select.select([self.master_fd], [], [], 0.1)
                if r:
                    data = os.read(self.master_fd, 1024)
                    if not data:
                        self.is_running = False
                        GLib.idle_add(self._close_terminal)
                        break
                    text = data.decode('utf-8', errors='replace')
                    GLib.idle_add(self._append_text, text)
            except OSError:
                self.is_running = False
                break

    def _append_text(self, text):
        end_iter = self.buf.get_end_iter()
        self.buf.insert(end_iter, text)
        mark = self.buf.create_mark(None, end_iter, False)
        self.text_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        if not self.is_running: return False
        char = chr(keyval) if keyval < 128 else None
        data = b""
        if char and not (state & Gdk.ModifierType.CONTROL_MASK): data = char.encode('utf-8')
        elif keyval == Gdk.KEY_Return: data = b"\n"
        elif keyval == Gdk.KEY_BackSpace: data = b"\x7f"
        elif keyval == Gdk.KEY_Tab: data = b"\t"
        elif keyval == Gdk.KEY_Escape: data = b"\x1b"
        elif keyval == Gdk.KEY_Up: data = b"\x1b[A"
        elif keyval == Gdk.KEY_Down: data = b"\x1b[B"
        elif keyval == Gdk.KEY_Right: data = b"\x1b[C"
        elif keyval == Gdk.KEY_Left: data = b"\x1b[D"
        elif state & Gdk.ModifierType.CONTROL_MASK:
            if keyval == Gdk.KEY_c: data = b"\x03"
            elif keyval == Gdk.KEY_d: data = b"\x04"
            elif keyval == Gdk.KEY_l: data = b"\x0c"
            elif keyval == Gdk.KEY_u: data = b"\x15"
            elif keyval == Gdk.KEY_w: data = b"\x17"
        
        if data:
            try: os.write(self.master_fd, data)
            except OSError: self.is_running = False
            return True
        return False

    def _on_resize(self, *args):
        if not self.is_running: return
        h, w = self.text_view.get_allocated_height(), self.text_view.get_allocated_width()
        cols = max(w // 9, 80)
        rows = max(h // 18, 24)
        try: fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        except: pass

    def _close_terminal(self, *args):
        self.is_running = False
        if self.pid:
            try: os.kill(self.pid, 9); os.waitpid(self.pid, 0)
            except: pass
        if self.master_fd:
            try: os.close(self.master_fd)
            except: pass
        self.destroy()

# ═══════════════════════════════════════════════════════════════════════
#  FILE WATCHER
# ═══════════════════════════════════════════════════════════════════════
class FileWatcher(threading.Thread):
    def __init__(self, root_path, callback_on_change):
        super().__init__(daemon=True)
        self.root_path = Path(root_path)
        self.callback = callback_on_change
        self.running = True
        self.snapshot = {}
        self._update_snapshot()

    def _update_snapshot(self):
        self.snapshot = {}
        if self.root_path.exists():
            for p in self.root_path.rglob('*'):
                if p.is_file():
                    try: self.snapshot[str(p)] = p.stat().st_mtime
                    except: pass

    def run(self):
        while self.running:
            time.sleep(1.5)
            if not self.root_path.exists(): continue
            current_files = {}
            changed = False
            for p in self.root_path.rglob('*'):
                if p.is_file():
                    try:
                        mtime = p.stat().st_mtime
                        current_files[str(p)] = mtime
                        if str(p) not in self.snapshot or self.snapshot[str(p)] != mtime: changed = True
                    except: pass
            if set(current_files.keys()) != set(self.snapshot.keys()): changed = True
            if changed:
                self.snapshot = current_files
                GLib.idle_add(self.callback)

# ═══════════════════════════════════════════════════════════════════════
#  AI ENGINE & MODIFICATION DIALOG
# ═══════════════════════════════════════════════════════════════════════
class BlockAIEngine:
    def __init__(self, config_getter, log_callback):
        self.get_config = config_getter
        self.log = log_callback

# Dans la classe BlockAIEngine, remplacez les méthodes _build_prompt et process_modification par :

    def _build_prompt(self, block_type, current_code, user_intent, context_deps="", mode="modify", custom_role=None):
        roles = {
            "function": "Tu es un expert Python Senior spécialisé en optimisation et clean code.",
            "class": "Tu es un architecte logiciel Python expert en POO.",
            "django_model": "Tu es un expert Django ORM. Tu maîtrises les relations et validations.",
            "django_view": "Tu es un expert Django Views. Tu privilégies les Class-Based Views ou fonctions optimisées.",
            "django_form": "Tu es un expert Django Forms.",
            "django_settings": "Tu es un expert configuration Django sécurisée.",
            "django_url": "Tu es un expert Django URL routing.",
            "template": "Tu es un expert Django Templates (Jinja2).",
            "javascript": "Tu es un développeur JavaScript moderne (ES6+).",
            "c_block": "Tu es un expert C/C++ système.",
            "shell": "Tu es un expert Bash/Linux.",
            "css": "Tu es un expert CSS moderne.",
            "business_process": "Tu es un expert algorithmique de processus métier Django. Tu sais décomposer un problème complexe en tâches techniques précises et ordonnées.",
            "other": "Tu es un assistant de codage polyvalent."
        }
        # Utilisation du rôle personnalisé s'il est fourni, sinon fallback sur le rôle par défaut
        role = custom_role if custom_role else roles.get(block_type, roles["other"])
        
        if mode == "contextual_modify":
            format_instruction = "RÈGLE ABSOLUE : Réponds UNIQUEMENT par le code du bloc cible modifié. Pas de markdown, pas de texte."
        elif mode == "cpp_optimize":
            format_instruction = "RÈGLE ABSOLUE : Génère DU CODE C++ pur. Pas de markdown, pas de texte."
        elif mode == "terminal_gen":
            format_instruction = "RÈGLE ABSOLUE : Réponds UNIQUEMENT par la commande shell exacte. Pas d'explication, pas de markdown."
        elif mode == "log_analysis":
            format_instruction = """RÈGLE ABSOLUE (JSON STRICT) :
1. Analyse les logs fournis.
2. Réponds UNIQUEMENT avec un objet JSON valide.
3. N'ajoute AUCUN texte explicatif, AUCUNE balise markdown (interdiction formelle de ```json).
4. Format JSON attendu : {"erreur": "Description courte", "cause": "Explication technique", "solution": "Commande ou action concrète", "severite": "critique/moyen/faible"}"""
        elif mode == "business_process":
            format_instruction = """RÈGLE ABSOLUE (JSON STRICT) :
1. Tu dois générer UNIQUEMENT une réponse structurée en JSON selon les instructions spécifiques de ton rôle.
2. N'ajoute AUCUN texte explicatif, AUCUNE balise markdown (interdiction formelle de ```json).
3. Respecte scrupuleusement le format JSON demandé dans ta description de rôle."""
        else:
            format_instruction = "RÈGLE ABSOLUE : Ne réponds QUE par le code modifié ou la réponse demandée. N'ajoute AUCUN texte explicatif superflu."
            
        prompt = f"""{role}
CONTEXTE SUPPLÉMENTAIRE : {context_deps if context_deps else "Aucune dépendance externe majeure."}
CODE ACTUEL / CONTEXTE :
{current_code}
DEMANDE : "{user_intent}"
OBJECTIF : {format_instruction}
"""
        return prompt

    def _clean_json_output(self, text: str) -> str:
        """
        Extrait STRICTEMENT le JSON entre les backticks.
        Si pas de backticks -> Réponse non admise.
        """
        if not text: return "{}"
        
        # Recherche du bloc ```json ... ``` ou ``` ... ```
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        
        if match:
            content = match.group(1).strip()
            # Vérification basique que c'est bien du JSON
            if content.startswith('{') or content.startswith('['):
                return content
        
        # Si on arrive ici, c'est qu'il n'y a pas de backticks ou pas de JSON valide dedans
        return "FORMAT NON AUTORISÉ : L'IA doit renvoyer le JSON entre des balises ```json ... ```"

    def _clean_code_output(self, text, block_type):
        """
        Extrait STRICTEMENT le code entre les backticks.
        Si pas de backticks -> Réponse non admise.
        """
        if not text: return ""
        
        # Recherche du bloc ```lang ... ```
        match = re.search(r'```[a-zA-Z]*\s*([\s\S]*?)\s*```', text)
        
        if match:
            return match.group(1).strip()
        
        # Si on arrive ici, c'est qu'il n'y a pas de backticks
        return "FORMAT NON AUTORISÉ : L'IA doit renvoyer le code entre des balises ```... ```"

    def process_modification(self, block_type, current_code, user_intent, context_deps="", mode="modify", custom_role=None):
        cfg = self.get_config()
        host = cfg.get("llama_host", "127.0.0.1")
        port = cfg.get("llama_port", 8080)
        url = f"http://{host}:{port}/v1/chat/completions"
        
        # Passage du custom_role au prompt builder
        prompt = self._build_prompt(block_type, current_code, user_intent, context_deps, mode=mode, custom_role=custom_role)
        
        payload = {
            "model": "qwen2.5-coder",
            "messages": [
                {"role": "system", "content": "Tu es un moteur de génération de code strict. Tu ne parles pas, tu codes."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "top_p": 0.9,
            "max_tokens": 2048,
            "stream": False
        }
        try:
            self.log(f"🤖 Envoi de la requête IA ({mode})...")
            response = requests.post(url, json=payload, timeout=12000)
            if response.status_code == 200:
                data = response.json()
                raw_content = data['choices'][0]['message']['content']
                # Utilisation du bon nettoyeur selon le mode
                if mode in ["log_analysis", "business_process"]:
                    cleaned_code = self._clean_json_output(raw_content)
                else:
                    cleaned_code = self._clean_code_output(raw_content, block_type if mode != "terminal_gen" else "shell")
                return cleaned_code
            else:
                self.log(f"❌ Erreur API IA: {response.status_code}")
                return None
        except Exception as e:
            self.log(f"❌ Exception connexion IA: {e}")
            return None
            
# --- NOUVEAU : Dialogues pour le Modificateur Contextuel (Version Simplifiée) ---
class AIModificationDialog(Gtk.Dialog):
    def __init__(self, parent, block, ai_engine, on_confirm_cb, project_root=None):
        super().__init__(title=f"✨ Modification IA : {block['name']}", transient_for=parent, default_width=1000, default_height=700)
        self.add_css_class("rounded-dialog")
        self.block = block
        self.ai_engine = ai_engine
        self.on_confirm_cb = on_confirm_cb
        self.project_root = project_root
        self.modified_code = None
        self.context_deps = ""
        
        content = self.get_content_area()
        content.set_spacing(10)
        set_margins(content, 16)
        
        # --- Header avec Switch Auto-Apply ---
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl_type = Gtk.Label(label=f"Type: {block['type'].upper()}", css_classes=["badge-function"], margin_end=10)
        header.append(lbl_type)
        
        spacer = Gtk.Box(hexpand=True)
        header.append(spacer)
        
        self.switch_auto_apply = Gtk.Switch()
        self.switch_auto_apply.set_tooltip_text("Appliquer automatiquement le code généré sans confirmation")
        lbl_auto = Gtk.Label(label="⚡ Auto-Apply", css_classes=["dim-label"])
        
        auto_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        auto_box.append(lbl_auto)
        auto_box.append(self.switch_auto_apply)
        header.append(auto_box)
        
        content.append(header)
        content.append(Gtk.Separator())
        
        # Main Paned (Original vs New)
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_vexpand(True)
        paned.set_hexpand(True)
        paned.set_wide_handle(True)
        
        # Original Code
        box_orig = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box_orig.append(Gtk.Label(label="Code Actuel", xalign=0, css_classes=["dim-label"]))
        scroll_orig = Gtk.ScrolledWindow()
        scroll_orig.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_orig.set_vexpand(True)
        scroll_orig.set_size_request(-1, 400)
        self.view_orig = GtkSource.View()
        self.view_orig.set_editable(False)
        self.view_orig.set_monospace(True)
        self.view_orig.set_show_line_numbers(True)
        self.view_orig.set_highlight_current_line(True)
        
        buf_orig = GtkSource.Buffer()
        lang_mgr = GtkSource.LanguageManager.get_default()
        lang_orig = lang_mgr.get_language(self._get_lang(block['type']))
        if lang_orig: buf_orig.set_language(lang_orig)
        buf_orig.set_text(block['code'])
        self.view_orig.set_buffer(buf_orig)
        scroll_orig.set_child(self.view_orig)
        box_orig.append(scroll_orig)
        
        # New Code
        box_new = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box_new.append(Gtk.Label(label="Proposition IA", xalign=0, css_classes=["dim-label"]))
        scroll_new = Gtk.ScrolledWindow()
        scroll_new.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_new.set_vexpand(True)
        scroll_new.set_size_request(-1, 400)
        self.view_new = GtkSource.View()
        self.view_new.set_editable(False)
        self.view_new.set_monospace(True)
        self.view_new.set_show_line_numbers(True)
        self.view_new.set_highlight_current_line(True)
        
        buf_new = GtkSource.Buffer()
        lang_mgr = GtkSource.LanguageManager.get_default()
        lang_new = lang_mgr.get_language(self._get_lang(self.block['type']))
        if lang_new: buf_new.set_language(lang_new)
        buf_new.set_text("// En attente de génération...")
        self.view_new.set_buffer(buf_new)
        scroll_new.set_child(self.view_new)
        box_new.append(scroll_new)
        
        bottom_action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, halign=Gtk.Align.END)
        btn_reject = Gtk.Button(label="❌ Annuler")
        btn_reject.connect("clicked", lambda *_: self.destroy())
        
        btn_accept = Gtk.Button(label="✅ Conserver", css_classes=["suggested-action"])
        btn_accept.connect("clicked", self._on_accept)
        
        bottom_action_box.append(btn_reject)
        bottom_action_box.append(btn_accept)
        box_new.append(bottom_action_box)
        
        paned.set_start_child(box_orig)
        paned.set_end_child(box_new)
        paned.set_position(500)
        content.append(paned)
        
        content.append(Gtk.Separator())
        
        # Prompt Box
        prompt_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        prompt_box.append(Gtk.Label(label="Instructions pour l'IA (Max 150 mots) :", xalign=0, css_classes=["heading"]))
        scroll_prompt = Gtk.ScrolledWindow()
        scroll_prompt.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_prompt.set_size_request(-1, 120)
        self.intent_entry = Gtk.TextView()
        self.intent_entry.set_wrap_mode(Gtk.WrapMode.WORD)
        self.intent_entry.set_monospace(True)
        scroll_prompt.set_child(self.intent_entry)
        prompt_box.append(scroll_prompt)
        
        action_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_bar.set_halign(Gtk.Align.END)
        
        self.btn_cancel_gen = Gtk.Button(label="Annuler")
        self.btn_cancel_gen.connect("clicked", lambda *_: self.destroy())
        
        self.spinner = Gtk.Spinner()
        self.spinner.set_visible(False)
        
        self.btn_generate = Gtk.Button()
        self.btn_generate.add_css_class("whatsapp-btn")
        self.btn_generate.set_tooltip_text("Envoyer la demande")
        icon = Gtk.Image.new_from_icon_name("mail-send-symbolic")
        self.btn_generate.set_child(icon)
        self.btn_generate.connect("clicked", self._on_generate)
        
        generate_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        generate_box.append(self.spinner)
        generate_box.append(self.btn_generate)
        
        action_bar.append(self.btn_cancel_gen)
        action_bar.append(generate_box)
        prompt_box.append(action_bar)
        content.append(prompt_box)

    def _on_generate(self, *_):
        buf = self.intent_entry.get_buffer()
        intent = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True).strip()
        
        if len(intent.split()) > 150:
            self.ai_engine.log("⚠️ Votre demande dépasse 150 mots.")
            return
        if not intent:
            self.ai_engine.log("⚠️ Veuillez décrire la modification.")
            return
            
        # Construction du contexte (vide car supprimé de l'UI)
        self.context_deps = ""
        
        self.spinner.start()
        self.spinner.set_visible(True)
        self.btn_generate.set_sensitive(False)
        
        threading.Thread(target=self._thread_generate, args=(self.block['type'], intent), daemon=True).start()

    def _thread_generate(self, btype, intent):
        # 1. Vérifier le cache spécifique aux blocs de code
        cached = get_cached_block(intent)
        
        if cached:
            result = cached["content"]
            GLib.idle_add(lambda: self.ai_engine.log(f"📂 Modification récupérée depuis la DB (Cache Code)"))
        else:
            # 2. Appel IA
            result = self.ai_engine.process_modification(btype, self.block['code'], intent, self.context_deps, mode="contextual_modify")
            
            if result:
                save_block_to_cache(intent, result, block_type=btype)
                GLib.idle_add(lambda: self.ai_engine.log(f"💾 Nouvelle modification sauvegardée (Cache Code)"))

        GLib.idle_add(self._update_ui_with_result, result)
        
    def _update_ui_with_result(self, result):
        self.spinner.stop()
        self.spinner.set_visible(False)
        self.btn_generate.set_sensitive(True)
        
        if result:
            self.modified_code = result
            self.view_new.get_buffer().set_text(result)
            self.ai_engine.log("✅ Modification générée.")
            
            # Auto-Apply si activé
            if self.switch_auto_apply.get_active():
                self._on_accept(None)
        else:
            self.ai_engine.log("❌ Échec de la génération ou erreur serveur.")
            self.view_new.get_buffer().set_text("// Erreur lors de la génération.")

    def _on_accept(self, *_):
        if self.modified_code:
            self.on_confirm_cb(self.block, self.modified_code)
            self.destroy()

    def _get_lang(self, btype):
        mapping = {
            "function": "python", "class": "python", "django_model": "python",
            "django_view": "python", "django_form": "python", "django_settings": "python",
            "django_url": "python", "template": "jinja", "javascript": "js",
            "c_block": "c", "shell": "bash", "css": "css"
        }
        return mapping.get(btype, "python")
        
        
        
class LlamaSetupDialog(Gtk.Dialog):
    def __init__(self, parent, config, on_save_and_start):
        super().__init__(title="⚙️ Configuration Llama.cpp (Sudo)", transient_for=parent, default_width=500, default_height=300)
        self.add_css_class("rounded-dialog")
        self.config = config
        self.on_save_and_start = on_save_and_start
        
        content = self.get_content_area()
        content.set_spacing(12)
        set_margins(content, 16)
        
        info = Gtk.Label(label="Veuillez sélectionner le binaire llama-server et le modèle .gguf.\nLe serveur sera lancé avec les droits sudo.", xalign=0, margin_bottom=10)
        info.add_css_class("dim-label")
        content.append(info)
        
        box_bin = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.entry_bin = Gtk.Entry()
        self.entry_bin.set_text(config.get("llama_server_path", "/usr/local/bin/llama-server"))
        self.entry_bin.set_hexpand(True)
        btn_bin = Gtk.Button(label="📂 Parcourir")
        btn_bin.connect("clicked", lambda *_: self._browse_file("Binaire llama-server", self.entry_bin))
        box_bin.append(Gtk.Label(label="Binaire:", xalign=0, width_request=80))
        box_bin.append(self.entry_bin)
        box_bin.append(btn_bin)
        content.append(box_bin)
        
        box_model = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.entry_model = Gtk.Entry()
        self.entry_model.set_text(config.get("llama_model_path", "/models/qwen2.5-coder.gguf"))
        self.entry_model.set_hexpand(True)
        btn_model = Gtk.Button(label="📂 Parcourir")
        btn_model.connect("clicked", lambda *_: self._browse_file("Modèle .gguf", self.entry_model))
        box_model.append(Gtk.Label(label="Modèle:", xalign=0, width_request=80))
        box_model.append(self.entry_model)
        box_model.append(btn_model)
        content.append(box_model)
        
        box_port = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.entry_port = Gtk.Entry()
        self.entry_port.set_text(str(config.get("llama_port", "8080")))
        box_port.append(Gtk.Label(label="Port:", xalign=0, width_request=80))
        box_port.append(self.entry_port)
        content.append(box_port)
        
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.END, margin_top=12)
        btn_cancel = Gtk.Button(label="Annuler")
        btn_cancel.connect("clicked", lambda *_: self.destroy())
        btn_start = Gtk.Button(label="🚀 Sauvegarder & Lancer (Sudo)", css_classes=["suggested-action"])
        btn_start.connect("clicked", self._on_start)
        btn_box.append(btn_cancel)
        btn_box.append(btn_start)
        content.append(btn_box)

    def _browse_file(self, title, entry):
        dialog = Gtk.FileDialog(title=title)
        dialog.open(self.get_root(), None, lambda d, r: self._on_file_selected(d, r, entry))

    def _on_file_selected(self, dialog, result, entry):
        try:
            file = dialog.open_finish(result)
            if file: entry.set_text(file.get_path())
        except: pass

    def _on_start(self, *_):
        bin_path = self.entry_bin.get_text().strip()
        model_path = self.entry_model.get_text().strip()
        port = self.entry_port.get_text().strip()
        if not bin_path or not model_path:
            return self._show_error("Chemin binaire et modèle requis")
        self.config["llama_server_path"] = bin_path
        self.config["llama_model_path"] = model_path
        self.config["llama_port"] = port
        self.on_save_and_start(bin_path, model_path, port)
        self.destroy()

    def _show_error(self, msg):
        dlg = Gtk.MessageDialog(transient_for=self.get_root(), flags=0, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text=msg)
        dlg.add_css_class("rounded-dialog")
        dlg.connect("response", lambda d, _: d.destroy())
        dlg.present()

# ═══════════════════════════════════════════════════════════════════════
#  NOUVEAUX POPUPS TERMINAL (DÉSATURATION)
# ═══════════════════════════════════════════════════════════════════════
class LogAnalyzerDialog(Gtk.Dialog):
    def __init__(self, parent, ai_engine, log_callback):
        super().__init__(title="🔍 Analyseur de Logs IA", transient_for=parent, default_width=700, default_height=600)
        self.add_css_class("rounded-dialog")
        self.ai_engine = ai_engine
        self.log_callback = log_callback
        
        content = self.get_content_area()
        content.set_spacing(12)
        set_margins(content, 16)
        
        content.append(Gtk.Label(label="1. Collez les logs à analyser :", xalign=0, css_classes=["heading"]))
        scroll_logs = Gtk.ScrolledWindow()
        scroll_logs.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_logs.set_size_request(-1, 150)
        self.txt_logs = GtkSource.View()
        self.txt_logs.set_wrap_mode(Gtk.WrapMode.WORD)
        self.txt_logs.set_show_line_numbers(True)
        self.txt_logs.set_monospace(True)
        lang_mgr = GtkSource.LanguageManager.get_default()
        lang_txt = lang_mgr.get_language("txt")
        if lang_txt: self.txt_logs.get_buffer().set_language(lang_txt)
        scroll_logs.set_child(self.txt_logs)
        content.append(scroll_logs)
        
        content.append(Gtk.Label(label="2. Question spécifique (optionnel) :", xalign=0, css_classes=["heading"], margin_top=8))
        self.txt_question = Gtk.Entry()
        self.txt_question.set_placeholder_text("Ex: Pourquoi le serveur plante-t-il ?")
        content.append(self.txt_question)
        
        btn_analyze = Gtk.Button(label="🤖 Analyser les Logs")
        btn_analyze.add_css_class("suggested-action")
        btn_analyze.set_halign(Gtk.Align.END)
        btn_analyze.connect("clicked", self._on_analyze)
        content.append(btn_analyze)
        
        content.append(Gtk.Separator(margin_top=8, margin_bottom=8))
        
        content.append(Gtk.Label(label="3. Résultat de l'analyse :", xalign=0, css_classes=["heading"]))
        scroll_result = Gtk.ScrolledWindow()
        scroll_result.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_result.set_vexpand(True)
        self.txt_result = GtkSource.View()
        self.txt_result.set_editable(False)
        self.txt_result.set_monospace(True)
        self.txt_result.set_wrap_mode(Gtk.WrapMode.WORD)
        self.txt_result.set_show_line_numbers(True)
        self.txt_result.add_css_class("code-editor")
        
        lang_mgr = GtkSource.LanguageManager.get_default()
        lang_json = lang_mgr.get_language("json")
        if lang_json: self.txt_result.get_buffer().set_language(lang_json)
        
        scroll_result.set_child(self.txt_result)
        content.append(scroll_result)
        
        btn_close = Gtk.Button(label="Fermer", margin_top=12)
        btn_close.set_halign(Gtk.Align.END)
        btn_close.connect("clicked", lambda *_: self.destroy())
        content.append(btn_close)

    def _on_analyze(self, *_):
        logs = self.txt_logs.get_buffer().get_text(self.txt_logs.get_buffer().get_start_iter(), self.txt_logs.get_buffer().get_end_iter(), True).strip()
        question = self.txt_question.get_text().strip()
        if not logs:
            self.log_callback("❌ Veuillez coller des logs à analyser.")
            return
        
        intent = f"Analyse ces logs. Question spécifique: {question if question else 'Explique les erreurs et propose une solution.'}"
        self.log_callback("🤖 Analyse des logs en cours (Format JSON strict)...")
        self.txt_result.get_buffer().set_text("Analyse en cours...")
        
        def _thread():
            result = self.ai_engine.process_modification("log_analysis", logs, intent, mode="log_analysis")
            if result:
                clean_json = self.ai_engine._clean_json_output(result)
                GLib.idle_add(lambda: self.txt_result.get_buffer().set_text(clean_json))
                GLib.idle_add(lambda: self.log_callback("📊 ANALYSE IA TERMINÉE (Format JSON)."))
            else:
                GLib.idle_add(lambda: self.txt_result.get_buffer().set_text("❌ Échec de l'analyse IA."))
                GLib.idle_add(lambda: self.log_callback("❌ Échec de l'analyse IA."))
        
        threading.Thread(target=_thread, daemon=True).start()

class AICmdGeneratorDialog(Gtk.Dialog):
    def __init__(self, parent, terminal_panel):
        super().__init__(title="🤖 Générateur de Commandes IA", transient_for=parent, default_width=600, default_height=450)
        self.add_css_class("rounded-dialog")
        self.terminal_panel = terminal_panel
        self.generated_cmd = ""
        self.is_process_mode = False
        
        content = self.get_content_area()
        content.set_spacing(12)
        set_margins(content, 16)
        
        # --- Header avec Switch Auto-Run ---
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.append(Gtk.Label(label="Décrivez l'action :", xalign=0, css_classes=["heading"]))
        
        spacer = Gtk.Box(hexpand=True)
        header_box.append(spacer)
        
        self.switch_auto_run = Gtk.Switch()
        self.switch_auto_run.set_tooltip_text("Exécuter automatiquement la commande trouvée/générée")
        lbl_auto = Gtk.Label(label="⚡ Auto-Run", css_classes=["dim-label"])
        
        auto_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        auto_box.append(lbl_auto)
        auto_box.append(self.switch_auto_run)
        header_box.append(auto_box)
        
        content.append(header_box)
        
        # --- Input avec Placeholder (Correction du bug TextView) ---
        scroll_in = Gtk.ScrolledWindow()
        scroll_in.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_in.set_size_request(-1, 100)
        
        self.txt_input = Gtk.TextView()
        self.txt_input.set_wrap_mode(Gtk.WrapMode.WORD)
        
        # Création du placeholder via Overlay
        overlay = Gtk.Overlay()
        overlay.set_child(self.txt_input)
        
        self.lbl_placeholder = Gtk.Label(
            label="Ex: 'Mettre à jour le système' ou 'Liste: installer git, cloner repo, entrer dans le dossier'",
            xalign=0, yalign=0, margin_start=8, margin_top=8
        )
        self.lbl_placeholder.add_css_class("dim-label")
        overlay.add_overlay(self.lbl_placeholder)
        
        # Gestion de la visibilité du placeholder
        self.txt_input.get_buffer().connect("changed", self._on_input_changed)
        self._on_input_changed(self.txt_input.get_buffer())
        
        scroll_in.set_child(overlay)
        content.append(scroll_in)
        
        # --- Bouton Générer ---
        btn_translate = Gtk.Button(label="🔄 Générer / Chercher")
        btn_translate.add_css_class("suggested-action")
        btn_translate.connect("clicked", self._on_translate)
        content.append(btn_translate)
        
        content.append(Gtk.Label(label="Résultat :", xalign=0, css_classes=["heading"], margin_top=8))
        
        # Zone de résultat plus grande pour les processus
        scroll_res = Gtk.ScrolledWindow()
        scroll_res.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_res.set_size_request(-1, 100)
        self.lbl_result = Gtk.Label(label="$ ...", xalign=0, css_classes=["terminal-prompt"])
        self.lbl_result.set_selectable(True)
        self.lbl_result.set_wrap(True) # Permet le retour à la ligne
        scroll_res.set_child(self.lbl_result)
        content.append(scroll_res)
        
        # --- Actions ---
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, halign=Gtk.Align.END, margin_top=12)
        btn_cancel = Gtk.Button(label="Annuler")
        btn_cancel.connect("clicked", lambda *_: self.destroy())
        
        self.btn_exec = Gtk.Button(label="▶ Exécuter")
        self.btn_exec.add_css_class("ctrl-btn-start")
        self.btn_exec.set_sensitive(False)
        self.btn_exec.connect("clicked", self._on_execute)
        
        action_box.append(btn_cancel)
        action_box.append(self.btn_exec)
        content.append(action_box)

    def _on_input_changed(self, buffer):
        """Gère l'affichage/masquage du placeholder"""
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True).strip()
        if self.lbl_placeholder:
            self.lbl_placeholder.set_visible(len(text) == 0)

    def _on_translate(self, *_):
        intent = self.txt_input.get_buffer().get_text(
            self.txt_input.get_buffer().get_start_iter(), 
            self.txt_input.get_buffer().get_end_iter(), True
        ).strip()
        
        if not intent: 
            self.terminal_panel._log("❌ Veuillez décrire une action.")
            return
            
        self.lbl_result.set_text("Recherche dans le cache...")
        self.btn_exec.set_sensitive(False)
        
        # Détection simple de mode "Processus" (si l'utilisateur utilise des mots clés comme "liste", "puis", "et ensuite")
        process_keywords = ["liste", "processus", "étapes", "puis", "ensuite", "et"]
        self.is_process_mode = any(kw in intent.lower() for kw in process_keywords)

        def _thread():
            # 1. Vérifier le cache
            cached = get_cached_command(intent)
            
            if cached:
                cmd = cached["command"]
                source = "Cache DB ✅"
                GLib.idle_add(lambda: self.terminal_panel._log(f"📂 Commande récupérée depuis la base de données ({source})"))
            else:
                # 2. Si pas dans le cache, appeler l'IA
                GLib.idle_add(lambda: self.lbl_result.set_text("Génération IA en cours..."))
                mode = "terminal_gen"
                # Si c'est un processus, on demande à l'IA de retourner une liste séparée par && ou ;
                if self.is_process_mode:
                    prompt_suffix = " (Retourne une seule ligne de commande chaînée avec && ou ;)"
                else:
                    prompt_suffix = ""
                    
                cmd = self.terminal_panel.ai_engine.process_modification(
                    "shell", "", intent + prompt_suffix, mode="terminal_gen"
                )
                
                if cmd:
                    # Sauvegarder dans le cache
                    save_command_to_cache(intent, cmd, self.is_process_mode)
                    source = "IA 🤖"
                    GLib.idle_add(lambda: self.terminal_panel._log(f"💾 Nouvelle commande générée et sauvegardée ({source})"))
                else:
                    GLib.idle_add(lambda: (
                        self.lbl_result.set_text("❌ Échec de la génération."), 
                        self.btn_exec.set_sensitive(False)
                    ))
                    return

            # Affichage du résultat
            display_cmd = cmd.replace("&&", "\n&& ").replace(";", "\n; ") if self.is_process_mode else cmd
            GLib.idle_add(lambda: (
                self.lbl_result.set_text(f"$ {display_cmd}"), 
                self.btn_exec.set_sensitive(True), 
                setattr(self, 'generated_cmd', cmd)
            ))
            
            # Auto-Run si activé
            if self.switch_auto_run.get_active():
                GLib.idle_add(lambda: self._on_execute(None))

        threading.Thread(target=_thread, daemon=True).start()

    def _on_execute(self, *_):
        if hasattr(self, 'generated_cmd') and self.generated_cmd:
            # Si c'est un processus, on loggue chaque étape
            if self.is_process_mode:
                steps = [s.strip() for s in self.generated_cmd.replace("&&", ";").split(";") if s.strip()]
                self.terminal_panel._log(f"🚀 Lancement du processus ({len(steps)} étapes)...")
            
            self.terminal_panel._run_custom_command_text(self.generated_cmd)
            # On ne ferme pas forcément le dialogue pour voir le résultat
class GitManagerDialog(Gtk.Dialog):
    def __init__(self, parent, project_root, log_callback):
        super().__init__(title="🐙 Mini GitHub Desktop", transient_for=parent, default_width=700, default_height=600)
        self.add_css_class("rounded-dialog")
        self.project_root = project_root
        self.log_callback = log_callback
        # Par défaut, on propose le dossier parent du projet actuel ou le home
        self.current_dir = str(project_root.parent) if project_root else str(Path.home())
        
        content = self.get_content_area()
        content.set_spacing(12)
        set_margins(content, 16)
        
        # --- Section 1: Configuration & Chemin ---
        content.append(Gtk.Label(label="1. Configuration du Dépôt", xalign=0, css_classes=["heading"]))
        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(8)
        grid.attach(Gtk.Label(label="URL du Repo (HTTPS/SSH) :", xalign=0), 0, 0, 1, 1)
        self.entry_url = Gtk.Entry()
        self.entry_url.set_placeholder_text("https://github.com/user/repo.git")
        self.entry_url.set_hexpand(True)
        grid.attach(self.entry_url, 1, 0, 1, 1)
        
        grid.attach(Gtk.Label(label="Chemin local :", xalign=0), 0, 1, 1, 1)
        box_path = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.entry_path = Gtk.Entry()
        self.entry_path.set_text(self.current_dir)
        self.entry_path.set_hexpand(True)
        btn_browse = Gtk.Button(label="📂")
        btn_browse.connect("clicked", self._browse_folder)
        box_path.append(self.entry_path)
        box_path.append(btn_browse)
        grid.attach(box_path, 1, 1, 1, 1)
        content.append(grid)
        
        content.append(Gtk.Separator(margin_top=8, margin_bottom=8))
        
        # --- Section 2: Actions Git ---
        content.append(Gtk.Label(label="2. Actions Git", xalign=0, css_classes=["heading"]))
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_halign(Gtk.Align.CENTER)
        btn_clone = Gtk.Button(label="📥 Cloner")
        btn_clone.add_css_class("suggested-action")
        btn_clone.connect("clicked", lambda *_: self._run_git_command("clone"))
        action_box.append(btn_clone)
        btn_status = Gtk.Button(label="🔍 Status")
        btn_status.connect("clicked", lambda *_: self._run_git_command("status"))
        action_box.append(btn_status)
        btn_add = Gtk.Button(label="➕ Add All")
        btn_add.connect("clicked", lambda *_: self._run_git_command("add"))
        action_box.append(btn_add)
        btn_commit = Gtk.Button(label="💾 Commit & Push")
        btn_commit.add_css_class("ctrl-btn-warn")
        btn_commit.connect("clicked", self._open_commit_dialog)
        action_box.append(btn_commit)
        content.append(action_box)
        
        content.append(Gtk.Separator(margin_top=8, margin_bottom=8))
        
        # --- Section 3: Sortie Git ---
        content.append(Gtk.Label(label="3. Sortie Git", xalign=0, css_classes=["heading"]))
        scroll_log = Gtk.ScrolledWindow()
        scroll_log.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_log.set_vexpand(True)
        self.txt_log = GtkSource.View()
        self.txt_log.set_editable(False)
        self.txt_log.set_monospace(True)
        self.txt_log.set_show_line_numbers(True)
        self.txt_log.add_css_class("log-view")
        
        lang_mgr = GtkSource.LanguageManager.get_default()
        lang_sh = lang_mgr.get_language("sh")
        if lang_sh: self.txt_log.get_buffer().set_language(lang_sh)
        
        scroll_log.set_child(self.txt_log)
        content.append(scroll_log)
        
        btn_close = Gtk.Button(label="Fermer", margin_top=12)
        btn_close.set_halign(Gtk.Align.END)
        btn_close.connect("clicked", lambda *_: self.destroy())
        content.append(btn_close)

    def _browse_folder(self, *_):
        Gtk.FileDialog(title="Choisir le dossier local").select_folder(self.get_root(), None, self._on_folder_selected)

    def _on_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder: self.entry_path.set_text(folder.get_path())
        except: pass

    def _log(self, text):
        buf = self.txt_log.get_buffer()
        buf.insert(buf.get_end_iter(), f"$ {text}\n")
        adj = self.txt_log.get_parent().get_vadjustment()
        adj.set_value(adj.get_upper())

    def _run_git_command(self, action, commit_msg=""):
        path = self.entry_path.get_text().strip()
        url = self.entry_url.get_text().strip()
        if not path:
            self._log("❌ Chemin local requis.")
            return
            
        if action == "clone":
            if not url:
                self._log("❌ URL du dépôt requise pour cloner.")
                return
            # Correction Git Clone :
            target_dir = Path(path)
            if target_dir.exists():
                if any(target_dir.iterdir()):
                    self._log(f"❌ Le dossier '{path}' existe déjà et n'est pas vide. Git refuse d'écraser.")
                    self._log("💡 Astuce : Choisissez un nouveau nom de dossier à la fin du chemin.")
                    return
                else:
                    self._log(f"ℹ️ Le dossier '{path}' existe mais est vide. Clonage autorisé.")
            else:
                parent_dir = target_dir.parent
                if not parent_dir.exists():
                    self._log(f"❌ Le dossier parent '{parent_dir}' n'existe pas. Veuillez choisir un chemin valide.")
                    return
            
            cmd = ["git", "clone", url, path]
            self._log(f"Exécution : {' '.join(cmd)}")
            self._execute_git_command(cmd)
            
        elif action == "status":
            cmd = ["git", "-C", path, "status"]
            self._log(f"Exécution : {' '.join(cmd)}")
            self._execute_git_command(cmd)
            
        elif action == "add":
            cmd = ["git", "-C", path, "add", "."]
            self._log(f"Exécution : {' '.join(cmd)}")
            self._execute_git_command(cmd)
            
        elif action == "commit_push":
            if not commit_msg:
                self._log("❌ Message de commit requis.")
                return
            cmd_add = ["git", "-C", path, "add", "."]
            cmd_commit = ["git", "-C", path, "commit", "-m", commit_msg]
            cmd_push = ["git", "-C", path, "push"]
            self._execute_git_sequence([cmd_add, cmd_commit, cmd_push])

    def _execute_git_command(self, cmd):
        def _thread():
            try:
                target_path = self.entry_path.get_text().strip()
                # Astuce : On exécute git depuis le dossier PARENT
                cwd = str(Path(target_path).parent)
                # Sécurité : si on est à la racine '/', on utilise home
                if cwd == '/':
                    cwd = str(Path.home())
                
                proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
                output = proc.stdout.strip() or proc.stderr.strip()
                
                if proc.returncode == 0:
                    GLib.idle_add(lambda: self._log(f"✅ Succès:\n{output}"))
                    # Mise à jour automatique du champ pour pointer vers le nouveau dossier
                    if "clone" in " ".join(cmd):
                        final_folder = Path(target_path)
                        if not final_folder.exists():
                            repo_name = self.entry_url.get_text().strip().split('/')[-1].replace('.git', '')
                            final_folder = Path(cwd) / repo_name
                        if final_folder.exists():
                            GLib.idle_add(lambda: self.entry_path.set_text(str(final_folder)))
                else:
                    GLib.idle_add(lambda: self._log(f"❌ Erreur (Code {proc.returncode}):\n{output}"))
            except Exception as e:
                GLib.idle_add(lambda err=e: self._log(f"❌ Exception: {err}"))
        
        threading.Thread(target=_thread, daemon=True).start()

    def _execute_git_sequence(self, cmds):
        def _thread():
            for cmd in cmds:
                GLib.idle_add(lambda c=cmd: self._log(f"▶ {' '.join(c)}"))
                try:
                    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=self.entry_path.get_text().strip())
                    output = proc.stdout.strip() or proc.stderr.strip()
                    if proc.returncode != 0:
                        GLib.idle_add(lambda o=output: self._log(f"❌ Échec de la séquence:\n{o}"))
                        return
                    GLib.idle_add(lambda o=output: self._log(f"✅ {o}"))
                except Exception as e:
                    GLib.idle_add(lambda err=e: self._log(f"❌ Exception: {err}"))
                    return
            GLib.idle_add(lambda: self._log("🎉 Séquence Commit & Push terminée avec succès."))
        
        threading.Thread(target=_thread, daemon=True).start()

    def _open_commit_dialog(self, *_):
        dialog = Gtk.Dialog(title="Message de Commit", transient_for=self, default_width=400, default_height=200)
        dialog.add_css_class("rounded-dialog")
        content = dialog.get_content_area()
        content.set_spacing(8)
        set_margins(content, 12)
        content.append(Gtk.Label(label="Décrivez vos modifications :", xalign=0))
        entry = Gtk.Entry()
        entry.set_placeholder_text("ex: feat: ajout de la fonctionnalité X")
        content.append(entry)
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_cancel = Gtk.Button(label="Annuler")
        btn_ok = Gtk.Button(label="✅ Valider", css_classes=["suggested-action"])
        btn_box.append(btn_cancel)
        btn_box.append(btn_ok)
        content.append(btn_box)
        
        def on_ok(*_):
            msg = entry.get_text().strip()
            if msg:
                self._run_git_command("commit_push", msg)
                dialog.destroy()
        
        btn_ok.connect("clicked", on_ok)
        btn_cancel.connect("clicked", lambda *_: dialog.destroy())
        entry.connect("activate", on_ok)
        dialog.present()

# Remplacez entièrement la classe BusinessProcessDialog par :

class BusinessProcessDialog(Gtk.Dialog):
    def __init__(self, parent, ai_engine, log_callback, config_getter=None):
        super().__init__(title="🧠 Assistant IA & Élaborateur de Processus", transient_for=parent, default_width=850, default_height=650)
        self.add_css_class("rounded-dialog")
        self.ai_engine = ai_engine
        self.log_callback = log_callback
        self.config_getter = config_getter
        
        # Rôles par défaut calibrés et très explicites (orientés JSON)
        self.default_roles = {
            "Élaborateur": "Tu es un expert algorithmique de processus métier. Tu sais décomposer un problème complexe en tâches techniques précises, ordonnées et réalisables. Réponds UNIQUEMENT avec un tableau JSON d'étapes : [{'etape': 1, 'tache': '...', 'fichier': '...', 'details': '...'}].",
            "Prof de programmation": "Tu es un professeur de programmation pédagogue et expert. Tu expliques les concepts clairement. Réponds UNIQUEMENT avec un objet JSON : {'explication': '...', 'exemple_code': '...', 'bonnes_pratiques': ['...']}.",
            "Expert en Django": "Tu es un architecte logiciel Django Senior. Tu privilégies les bonnes pratiques et la sécurité. Réponds UNIQUEMENT avec un objet JSON : {'analyse': '...', 'fichiers_a_modifier': ['...'], 'code_propose': '...'}.",
            "Traducteur": "Tu es un traducteur technique expert. Tu traduis les demandes avec une précision absolue. Réponds UNIQUEMENT avec un objet JSON : {'original': '...', 'traduction': '...'}.",
            "Expert Linux": "Tu es un administrateur système Linux et DevOps expert. Tu fournis des commandes shell optimisées. Réponds UNIQUEMENT avec un objet JSON : {'commande': '...', 'explication': '...', 'avertissements': '...'}.",
            "Expert en astuce en informatique": "Tu es un guru de l'informatique. Tu donnes des astuces et solutions ingénieuses. Réponds UNIQUEMENT avec un objet JSON : {'astuce': '...', 'contexte_utilisation': '...', 'gain_estime': '...'}."
        }

        content = self.get_content_area()
        content.set_spacing(12)
        set_margins(content, 16)

        # --- Header avec Switch Auto-Copy ---
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.append(Gtk.Label(label="1. Choisissez le rôle de l'IA :", xalign=0, css_classes=["heading"]))
        
        spacer = Gtk.Box(hexpand=True)
        header_box.append(spacer)
        
        self.switch_auto_copy = Gtk.Switch()
        self.switch_auto_copy.set_tooltip_text("Copier automatiquement le résultat JSON dans le presse-papiers")
        lbl_auto = Gtk.Label(label="⚡ Auto-Copy", css_classes=["dim-label"])
        
        auto_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        auto_box.append(lbl_auto)
        auto_box.append(self.switch_auto_copy)
        header_box.append(auto_box)
        
        content.append(header_box)

        role_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.combo_role = Gtk.ComboBoxText()
        self.combo_role.set_hexpand(True)
        for role_name in self.default_roles.keys():
            self.combo_role.append_text(role_name)
        self.combo_role.set_active(0) # Élaborateur par défaut
        
        # Charger les rôles personnalisés depuis la config
        self.custom_roles = {}
        if self.config_getter:
            cfg = self.config_getter()
            self.custom_roles = cfg.get("custom_ai_roles", {})
            for role_name in self.custom_roles.keys():
                self.combo_role.append_text(role_name)
                
        role_box.append(self.combo_role)
        btn_add_role = Gtk.Button(label="➕ Ajouter un rôle")
        btn_add_role.add_css_class("ctrl-btn")
        btn_add_role.connect("clicked", self._open_add_role_dialog)
        role_box.append(btn_add_role)
        content.append(role_box)
        
        content.append(Gtk.Separator(margin_top=8, margin_bottom=8))

        # --- Section 2: Demande ---
        content.append(Gtk.Label(label="2. Décrivez votre demande ou problème :", xalign=0, css_classes=["heading"]))
        scroll_in = Gtk.ScrolledWindow()
        scroll_in.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_in.set_size_request(-1, 120)
        self.txt_problem = GtkSource.View()
        self.txt_problem.set_wrap_mode(Gtk.WrapMode.WORD)
        self.txt_problem.set_show_line_numbers(True)
        self.txt_problem.set_monospace(True)
        scroll_in.set_child(self.txt_problem)
        content.append(scroll_in)

        btn_generate = Gtk.Button(label="🤖 Générer la réponse (JSON)")
        btn_generate.add_css_class("suggested-action")
        btn_generate.set_halign(Gtk.Align.END)
        btn_generate.connect("clicked", self._on_generate)
        content.append(btn_generate)

        content.append(Gtk.Separator(margin_top=8, margin_bottom=8))

        # --- Section 3: Résultat ---
        content.append(Gtk.Label(label="3. Résultat (JSON Strict) :", xalign=0, css_classes=["heading"]))
        scroll_out = Gtk.ScrolledWindow()
        scroll_out.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_out.set_vexpand(True)
        self.txt_result = GtkSource.View()
        self.txt_result.set_editable(False)
        self.txt_result.set_monospace(True)
        self.txt_result.set_wrap_mode(Gtk.WrapMode.WORD)
        self.txt_result.set_show_line_numbers(True)
        self.txt_result.add_css_class("code-editor")
        
        lang_mgr = GtkSource.LanguageManager.get_default()
        lang_json = lang_mgr.get_language("json")
        if lang_json: self.txt_result.get_buffer().set_language(lang_json)
        
        scroll_out.set_child(self.txt_result)
        content.append(scroll_out)

        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, halign=Gtk.Align.END, margin_top=8)
        btn_copy = Gtk.Button(label="📋 Copier")
        btn_copy.connect("clicked", self._copy_result)
        btn_close = Gtk.Button(label="Fermer")
        btn_close.connect("clicked", lambda *_: self.destroy())
        action_box.append(btn_copy)
        action_box.append(btn_close)
        content.append(action_box)

    def _open_add_role_dialog(self, *_):
        dialog = Gtk.Dialog(title="Ajouter un nouveau rôle IA", transient_for=self, default_width=500, default_height=350)
        dialog.add_css_class("rounded-dialog")
        content = dialog.get_content_area()
        content.set_spacing(10)
        set_margins(content, 16)
        
        content.append(Gtk.Label(label="Nom du rôle :", xalign=0))
        entry_name = Gtk.Entry()
        entry_name.set_placeholder_text("Ex: Expert en Sécurité Web")
        content.append(entry_name)
        
        content.append(Gtk.Label(label="Prompt d'entête (Calibrage du rôle) :", xalign=0, margin_top=8))
        content.append(Gtk.Label(label="⚠️ Important : Précisez explicitement le format JSON attendu dans ce prompt.", xalign=0, css_classes=["dim-label"], margin_bottom=4))
        
        scroll_prompt = Gtk.ScrolledWindow()
        scroll_prompt.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_prompt.set_size_request(-1, 120)
        text_prompt = Gtk.TextView()
        text_prompt.set_wrap_mode(Gtk.WrapMode.WORD)
        scroll_prompt.set_child(text_prompt)
        content.append(scroll_prompt)
        
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, halign=Gtk.Align.END, margin_top=12)
        btn_cancel = Gtk.Button(label="Annuler")
        btn_cancel.connect("clicked", lambda *_: dialog.destroy())
        btn_save = Gtk.Button(label="💾 Sauvegarder", css_classes=["suggested-action"])
        btn_box.append(btn_cancel)
        btn_box.append(btn_save)
        content.append(btn_box)

        def on_save(*_):
            name = entry_name.get_text().strip()
            prompt = text_prompt.get_buffer().get_text(
                text_prompt.get_buffer().get_start_iter(),
                text_prompt.get_buffer().get_end_iter(), True
            ).strip()
            
            if not name or not prompt:
                self.log_callback("❌ Le nom et le prompt sont requis.")
                return
            
            if name in self.default_roles or name in self.custom_roles:
                self.log_callback(f"❌ Le rôle '{name}' existe déjà.")
                return
                
            self.custom_roles[name] = prompt
            self.combo_role.append_text(name)
            
            # Sauvegarder dans la config
            if self.config_getter:
                cfg = self.config_getter()
                cfg["custom_ai_roles"] = self.custom_roles
                save_config(cfg)
                
            self.log_callback(f"✅ Rôle '{name}' ajouté avec succès.")
            dialog.destroy()

        btn_save.connect("clicked", on_save)
        dialog.present()

    def _on_generate(self, *_):
        problem = self.txt_problem.get_buffer().get_text(
            self.txt_problem.get_buffer().get_start_iter(),
            self.txt_problem.get_buffer().get_end_iter(), True
        ).strip()
        
        if not problem:
            self.log_callback("❌ Veuillez décrire votre demande.")
            return

        active_text = self.combo_role.get_active_text()
        selected_role_prompt = self.default_roles.get(active_text) or self.custom_roles.get(active_text, "Tu es un assistant IA polyvalent. Réponds UNIQUEMENT en format JSON.")
        
        self.txt_result.get_buffer().set_text("Recherche dans le cache...")
        
        def _thread():
            # 1. Vérifier le cache spécifique aux processus JSON
            cached = get_cached_process(problem)
            if cached:
                result = cached["json_content"]
                GLib.idle_add(lambda: self.log_callback(f"📂 Réponse récupérée depuis la DB (Cache Processus)"))
            else:
                # 2. Appel IA avec gestion robuste des erreurs de connexion
                GLib.idle_add(lambda: self.txt_result.get_buffer().set_text("Connexion à Llama.cpp en cours..."))
                
                try:
                    result = self.ai_engine.process_modification(
                        "business_process",
                        "Contexte: Demande utilisateur",
                        problem,
                        mode="business_process",
                        custom_role=selected_role_prompt
                    )
                    
                    if result is None:
                        raise ConnectionError("Llama server ne répond pas ou a retourné une erreur.")
                        
                    save_process_to_cache(problem, result, role_type=active_text)
                    GLib.idle_add(lambda: self.log_callback(f"💾 Nouvelle réponse sauvegardée (Cache Processus)"))
                    
                except Exception as e:
                    error_msg = f"❌ Échec de connexion IA: {str(e)}"
                    GLib.idle_add(lambda: (
                        self.txt_result.get_buffer().set_text(error_msg),
                        self.log_callback(error_msg)
                    ))
                    return

            # Nettoyage garanti des balises markdown ```json par le parseur
            clean_result = self.ai_engine._clean_json_output(result)
            
            # Vérification si le nettoyage a échoué (format non autorisé)
            if "FORMAT NON AUTORISÉ" in clean_result:
                 GLib.idle_add(lambda: (
                    self.txt_result.get_buffer().set_text(clean_result),
                    self.log_callback("⚠️ L'IA n'a pas respecté le format JSON strict.")
                ))
            else:
                GLib.idle_add(lambda: self.txt_result.get_buffer().set_text(clean_result))
                GLib.idle_add(lambda: self.log_callback(f"📊 RÉPONSE GÉNÉRÉE (Rôle: {active_text}, Format: JSON)."))
                
                # Auto-Copy si activé
                if self.switch_auto_copy.get_active():
                    GLib.idle_add(lambda: (
                        Gdk.Display.get_default().get_clipboard().set(clean_result),
                        self.log_callback("📋 Résultat copié automatiquement dans le presse-papiers.")
                    ))

        threading.Thread(target=_thread, daemon=True).start()        
        def _thread():
            # 1. Vérifier le cache spécifique aux processus JSON
            cached = get_cached_process(problem)
            
            if cached:
                result = cached["json_content"]
                GLib.idle_add(lambda: self.log_callback(f"📂 Réponse récupérée depuis la DB (Cache Processus)"))
            else:
                # 2. Appel IA
                GLib.idle_add(lambda: self.txt_result.get_buffer().set_text("Génération IA en cours..."))
                result = self.ai_engine.process_modification(
                    "business_process",
                    "Contexte: Demande utilisateur",
                    problem,
                    mode="business_process",
                    custom_role=selected_role_prompt
                )
                
                if result:
                    save_process_to_cache(problem, result, role_type=active_text)
                    GLib.idle_add(lambda: self.log_callback(f"💾 Nouvelle réponse sauvegardée (Cache Processus)"))
                else:
                    GLib.idle_add(lambda: (self.txt_result.get_buffer().set_text("❌ Échec."), self.log_callback("❌ Échec.")))
                    return

            clean_result = self.ai_engine._clean_json_output(result)
            GLib.idle_add(lambda: self.txt_result.get_buffer().set_text(clean_result))
            GLib.idle_add(lambda: self.log_callback(f"📊 RÉPONSE GÉNÉRÉE (Rôle: {active_text})."))
            
            if self.switch_auto_copy.get_active():
                GLib.idle_add(lambda: (
                    Gdk.Display.get_default().get_clipboard().set(clean_result),
                    self.log_callback("📋 Résultat copié automatiquement.")
                ))
                
            # Nettoyage garanti des balises markdown ```json par le parseur
            clean_result = self.ai_engine._clean_json_output(result)
            
            GLib.idle_add(lambda: self.txt_result.get_buffer().set_text(clean_result))
            GLib.idle_add(lambda: self.log_callback(f"📊 RÉPONSE GÉNÉRÉE (Rôle: {active_text}, Format: JSON)."))
            
            # Auto-Copy si activé
            if self.switch_auto_copy.get_active():
                GLib.idle_add(lambda: (
                    Gdk.Display.get_default().get_clipboard().set(clean_result),
                    self.log_callback("📋 Résultat copié automatiquement dans le presse-papiers.")
                ))

        threading.Thread(target=_thread, daemon=True).start()

    def _copy_result(self, *_):
        text = self.txt_result.get_buffer().get_text(
            self.txt_result.get_buffer().get_start_iter(),
            self.txt_result.get_buffer().get_end_iter(), True
        ).strip()
        
        if text and text != "Génération en cours..." and not text.startswith("❌"):
            Gdk.Display.get_default().get_clipboard().set(text)
            self.log_callback("✅ Résultat JSON copié dans le presse-papiers.")
            
            
            
            
            
# ═══════════════════════════════════════════════════════════════════════
#  WIDGETS
# ═══════════════════════════════════════════════════════════════════════
TYPE_ICONS = {"import": "📦", "class": "🏛", "function": "⚡", "separator": "─", "comment": "💬", "other": "▪", "template": "🌐", "template_part": "🌐", "django_block": "🧩", "style": "🎨", "style_rule": "🎨", "script": "⚙️", "script_block": "⚡", "c_block": "⚙️"}

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
        header.append(Gtk.Label(label=TYPE_ICONS.get(self.block["type"], "▪"), css_classes=["block-icon"]))
        badge = Gtk.Label(label=self.block["type"].upper()); badge.add_css_class("block-badge"); badge.add_css_class(f"badge-{self.block['type']}"); header.append(badge)
        
        # --- NOUVEAU : Affichage du compteur hiérarchique au lieu du nom ---
        hierarchical_id = self.block.get("hierarchical_id", "")
        lbl_name = Gtk.Label(label=hierarchical_id); lbl_name.set_ellipsize(Pango.EllipsizeMode.NONE); lbl_name.set_hexpand(True); lbl_name.set_xalign(0); lbl_name.add_css_class("block-name"); header.append(lbl_name)
        
        if self.ai_engine:
            btn_ai = Gtk.Button(label="🤖 IA")
            btn_ai.set_tooltip_text("Modifier ce bloc avec l'IA")
            btn_ai.add_css_class("block-action-btn")
            btn_ai.add_css_class("btn-ai")
            btn_ai.connect("clicked", self._open_ai_dialog)
            header.append(btn_ai)
            
        # --- NOUVEAU: Boutons de déplacement de bloc ---
        btn_up = Gtk.Button(label="⬆"); btn_up.set_tooltip_text("Monter le bloc (et ses enfants)"); btn_up.add_css_class("block-action-btn"); btn_up.connect("clicked", lambda *_: self._move_block(-1))
        btn_down = Gtk.Button(label="⬇"); btn_down.set_tooltip_text("Descendre le bloc (et ses enfants)"); btn_down.add_css_class("block-action-btn"); btn_down.connect("clicked", lambda *_: self._move_block(1))
        header.append(btn_up); header.append(btn_down)

        for label, tooltip, cb, css in [("👁", "View / Edit", self._view_code, "btn-view"), ("✏", "Inline Edit", self._toggle_edit, "btn-edit"), ("⧉", "Copy", self._do_copy, "btn-copy"), ("✕", "Delete", self._do_delete, "btn-delete")]:
            btn = Gtk.Button(label=label); btn.set_tooltip_text(tooltip); btn.add_css_class("block-action-btn"); btn.add_css_class(css); btn.connect("clicked", cb); header.append(btn)
        self.append(header)
        bar = Gtk.Box(); bar.set_size_request(-1, 2); bar.add_css_class("block-accent-bar"); bar.add_css_class(f"accent-{self.block['type']}"); self.append(bar)

    def _build_editor(self):
        self.editor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        set_margins(self.editor_box, 0)
        self.editor_box.set_margin_start(12)
        self.editor_box.set_margin_end(12)
        self.editor_box.set_margin_bottom(8)
        self.editor_box.set_visible(False)
        
        # 1. Création de la Vue Source
        self.textview = GtkSource.View()
        self.textview.set_monospace(True)
        self.textview.set_wrap_mode(Gtk.WrapMode.NONE)
        self.textview.set_show_line_numbers(True)
        self.textview.set_highlight_current_line(True)
        self.textview.set_auto_indent(True)
        self.textview.set_insert_spaces_instead_of_tabs(True)
        self.textview.set_tab_width(4)
        self.textview.add_css_class("code-editor")
        
        # 2. Configuration du Buffer et du Langage
        buffer = GtkSource.Buffer()
        lang_mgr = GtkSource.LanguageManager.get_default()
        
        # Mapping des extensions vers les IDs de langage GtkSource
        lang_map = {
            'py': 'python', 'js': 'javascript', 'css': 'css', 
            'html': 'html', 'c': 'c', 'cpp': 'cpp', 'sh': 'sh', 
            'jinja': 'html' # Jinja utilise souvent la coloration HTML comme base
        }
        
        lang_id = lang_map.get(self.lang, 'text') # Fallback sur 'text' si inconnu
        language = lang_mgr.get_language(lang_id)
        
        if language:
            buffer.set_language(language)
            
        # 3. APPLICATION DU THÈME SOMBRE (C'est ici que l'aperçu revient !)
        scheme_mgr = GtkSource.StyleSchemeManager.get_default()
        # Essayer d'abord 'Adwaita-dark', sinon 'cobalt', sinon 'oblivion'
        scheme = scheme_mgr.get_scheme('Adwaita-dark')
        if not scheme:
            scheme = scheme_mgr.get_scheme('cobalt')
        if not scheme:
            scheme = scheme_mgr.get_scheme('oblivion')
            
        if scheme:
            buffer.set_style_scheme(scheme)
            
        # 4. Chargement du code
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
            # Sauvegarde automatique des modifications en mémoire avant de fermer l'aperçu
            self.block["code"] = self.textview.get_buffer().get_text(
                self.textview.get_buffer().get_start_iter(), 
                self.textview.get_buffer().get_end_iter(), 
                True
            )
            self.on_save_cb(self.block, self.block["code"])
            
        self.expanded = not self.expanded
        self.editor_box.set_visible(self.expanded)

    def _view_code(self, *_):
        dialog = Gtk.Dialog(title=f"Editing: {self.block['name']}", transient_for=self.get_root())
        dialog.add_css_class("rounded-dialog")
        dialog.set_default_size(800, 500)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        set_margins(content, 12)
        dialog.set_child(content)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)
        
        textview = Gtk.TextView()
        textview.set_monospace(True)
        textview.set_editable(True)
        textview.set_wrap_mode(Gtk.WrapMode.WORD)
        textview.add_css_class("code-editor")
        textview.get_buffer().set_text(self.block["code"])
        apply_syntax_highlighting(textview, self.lang)
        
        scroll.set_child(textview)
        content.append(scroll)
        
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_box.set_halign(Gtk.Align.END)
        
        btn1 = Gtk.Button(label="📋 Copy")
        btn1.connect("clicked", lambda *_: self._do_copy())
        btn_box.append(btn1)
        
        # Le bouton Fermer agit maintenant comme "Sauvegarder et Fermer" pour simplifier l'interface
        btn_close = Gtk.Button(label="✕ Fermer (Sauvegarder)", css_classes=["suggested-action"])
        btn_close.connect("clicked", lambda *_: self._save_from_popup(textview, dialog))
        btn_box.append(btn_close)
        
        content.append(btn_box)
        dialog.present()
        
    def _save_from_popup(self, textview, dialog):
        self.block["code"] = textview.get_buffer().get_text(textview.get_buffer().get_start_iter(), textview.get_buffer().get_end_iter(), True)
        self.on_save_cb(self.block, self.block["code"]); self.textview.get_buffer().set_text(self.block["code"]); dialog.destroy()

    def _do_save(self, *_):
        self.block["code"] = self.textview.get_buffer().get_text(self.textview.get_buffer().get_start_iter(), self.textview.get_buffer().get_end_iter(), True)
        self.on_save_cb(self.block, self.block["code"]); self._toggle_edit()

    def _do_copy(self, *_): Gdk.Display.get_default().get_clipboard().set(self.block["code"])
    def _do_delete(self, *_): self.on_delete_cb(self.block)

    def _open_ai_dialog(self, *_):
        if not self.ai_engine or not self.parent_window: return
        
        # Find the actual Gtk.Window ancestor
        root = self.get_root()
        if not root: return

        project_root = None
        # Try to get project_root from the root window (GykhamineStudioApp.win)
        if hasattr(root, 'project_root'):
            project_root = root.project_root
            
        def on_confirm(block, new_code):
            self.block["code"] = new_code
            self.on_save_cb(self.block, new_code)
            self.textview.get_buffer().set_text(new_code)
            if hasattr(root, '_show_toast'):
                root._show_toast("✅ Bloc modifié par IA")

        # Pass 'root' (the Window) instead of 'self.parent_window'
        dialog = AIModificationDialog(root, self.block, self.ai_engine, on_confirm, project_root=project_root)
        dialog.present()
        
    def _move_block(self, direction):
        """Déplace le bloc (et toute sa hiérarchie d'enfants) vers le haut (-1) ou le bas (1) et sauvegarde le fichier."""
        
        def find_and_swap(blocks_list, target_block, dir):
            for i, b in enumerate(blocks_list):
                if b is target_block:
                    # Vérification des limites de la liste
                    if dir == -1 and i > 0:
                        blocks_list[i], blocks_list[i-1] = blocks_list[i-1], blocks_list[i]
                        return True
                    elif dir == 1 and i < len(blocks_list) - 1:
                        blocks_list[i], blocks_list[i+1] = blocks_list[i+1], blocks_list[i]
                        return True
                # Si ce n'est pas le bon bloc, on cherche récursivement DANS ses enfants
                if "children" in b and b["children"]:
                    if find_and_swap(b["children"], target_block, dir):
                        return True
            return False

        # self.parent_window est l'instance de BlockEditorView
        editor_view = self.parent_window
        
        if hasattr(editor_view, 'blocks') and find_and_swap(editor_view.blocks, self.block, direction):
            # 1. Mettre à jour l'état en mémoire (Undo/Redo) et l'affichage visuel
            editor_view._push_state()
            editor_view._render_blocks()
            
            # 2. NOUVEAU : Sauvegarder réellement le fichier sur le disque après le déplacement
            # Cela assure que l'ordre des blocs (parents et enfants) est persisté
            editor_view._save_file()
            
            # 3. Notification utilisateur
            if hasattr(editor_view, 'toast_cb'):
                editor_view.toast_cb("✅ Bloc déplacé et fichier sauvegardé")
        else:
            if hasattr(editor_view, 'toast_cb'):
                editor_view.toast_cb("⚠️ Limite de déplacement atteinte")


class FilePanel(Gtk.Box):
    def __init__(self, on_file_select, on_project_select, on_file_created, on_file_imported):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.on_file_select = on_file_select
        self.on_project_select = on_project_select
        self.on_file_created = on_file_created
        self.on_file_imported = on_file_imported
        self.project_root = None
        self.tree_store = Gtk.TreeStore(str, str, bool)
        self.show_hidden = False
        self.clipboard_action = None
        self.clipboard_path = None
        self.watcher = None
        
        lbl = Gtk.Label(label="📁 Projet"); lbl.add_css_class("panel-title"); lbl.set_xalign(0); lbl.set_margin_start(12); lbl.set_margin_top(10); lbl.set_margin_bottom(6)
        self.append(lbl); self.append(Gtk.Separator())
        
        self.stack = Gtk.Stack(); self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        
        scroll_files = Gtk.ScrolledWindow(); scroll_files.set_vexpand(True); scroll_files.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.tree_view = Gtk.TreeView(model=self.tree_store); self.tree_view.set_headers_visible(False); self.tree_view.add_css_class("file-tree-view")
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Fichiers", renderer, text=0)
        column.set_cell_data_func(renderer, self._on_tree_cell_data)
        self.tree_view.append_column(column)
        self.tree_view.connect("row-activated", self._on_row_activated)
        self.gesture_click = Gtk.GestureClick.new(); self.gesture_click.set_button(Gdk.BUTTON_SECONDARY); self.gesture_click.connect("pressed", self._on_right_click)
        self.tree_view.add_controller(self.gesture_click)
        scroll_files.set_child(self.tree_view)
        
        scroll_projs = Gtk.ScrolledWindow(); scroll_projs.set_vexpand(True); scroll_projs.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.recent_list = Gtk.ListBox(); self.recent_list.add_css_class("file-list"); self.recent_list.connect("row-activated", self._on_project_selected)
        scroll_projs.set_child(self.recent_list)
        
        self.stack.add_named(scroll_files, "files"); self.stack.add_named(scroll_projs, "recent")
        self.append(self.stack)
        
        nav_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4); set_margins(nav_bar, 6); nav_bar.set_margin_start(8); nav_bar.set_margin_end(8)
        btn_files = Gtk.Button(label="📄"); btn_files.set_tooltip_text("Fichiers"); btn_files.add_css_class("flat"); btn_files.set_hexpand(True); btn_files.connect("clicked", lambda *_: self.stack.set_visible_child_name("files"))
        btn_recent = Gtk.Button(label="🕒"); btn_recent.set_tooltip_text("Récents"); btn_recent.add_css_class("flat"); btn_recent.set_hexpand(True); btn_recent.connect("clicked", lambda *_: self.stack.set_visible_child_name("recent"))
        btn_new = Gtk.Button(label="➕"); btn_new.set_tooltip_text("Nouveau fichier"); btn_new.add_css_class("flat"); btn_new.set_hexpand(True); btn_new.connect("clicked", self._create_new_file)
        btn_import = Gtk.Button(label="📥"); btn_import.set_tooltip_text("Importer"); btn_import.add_css_class("flat"); btn_import.set_hexpand(True); btn_import.connect("clicked", self._import_file)
        self.btn_hidden = Gtk.Button(label="🙈"); self.btn_hidden.set_tooltip_text("Afficher les fichiers cachés"); self.btn_hidden.add_css_class("flat"); self.btn_hidden.connect("clicked", self._toggle_hidden_files)
        nav_bar.append(btn_files); nav_bar.append(btn_recent); nav_bar.append(btn_new); nav_bar.append(btn_import); nav_bar.append(self.btn_hidden)
        self.append(nav_bar)

    def _log_message(self, msg):
        """Tente d'envoyer le message au terminal parent ou affiche un toast."""
        try:
            # Essayer d'accéder au panneau terminal via la fenêtre parente
            root = self.get_root()
            if root and hasattr(root, 'terminal_panel'):
                root.terminal_panel._log(msg)
            else:
                # Fallback vers un toast si le terminal n'est pas accessible
                self._show_toast(msg)
        except Exception:
            pass

    def start_watcher(self, root_path):
        if self.watcher: 
            self.watcher.running = False
            self.watcher = None
        if root_path:
            try:
                self.watcher = FileWatcher(root_path, self._refresh_tree_idle)
                self.watcher.start()
            except Exception as e:
                self._log_message(f"⚠️ Erreur démarrage watcher: {e}")

    def _refresh_tree_idle(self): 
        GLib.idle_add(self._refresh_tree)

    def _refresh_tree(self):
        if not self.project_root:
            return
        
        # CORRECTION CRITIQUE : Vider le store avant de repeupler pour éviter les doublons
        self.tree_store.clear()
        
        try:
            self._populate_tree(self.project_root, None)
        except Exception as e:
            self._log_message(f"❌ Erreur rafraîchissement arbre: {e}")

    def _toggle_hidden_files(self, *_):
        self.show_hidden = not self.show_hidden
        if self.show_hidden: 
            self.btn_hidden.set_label("👁")
            self.btn_hidden.set_tooltip_text("Masquer les fichiers cachés")
        else: 
            self.btn_hidden.set_label("🙈")
            self.btn_hidden.set_tooltip_text("Afficher les fichiers cachés")
        
        if self.project_root: 
            self.load_project(self.project_root, load_config())

    def _on_tree_cell_data(self, column, cell, model, tree_iter, data):
        name = model.get_value(tree_iter, 0); is_folder = model.get_value(tree_iter, 2)
        if is_folder:
            cell.set_property("weight", Pango.Weight.BOLD); cell.set_property("text", f"📁 {name}"); cell.set_property("foreground", "#888888" if name.startswith('.') else "#4aa3df")
        else:
            cell.set_property("weight", Pango.Weight.NORMAL)
            ext = Path(name).suffix.lower() if '.' in name else ""; icon, color = "📄", "#888888" if name.startswith('.') else "#4aa3df"
            if name in ("settings.py", "manage.py"): icon = "⚙"
            elif name == "views.py": icon = "👁"
            elif name == "models.py": icon = "🗄"
            elif ext == '.css': icon = "🎨"
            elif ext == '.js': icon = "⚡"
            elif ext in ('.c', '.cpp', '.h'): icon = "⚙️"
            elif ext == '.sh': icon = "📜"
            elif ext in ('.html', '.jinja', '.jinja2'): icon = "🌐"
            cell.set_property("text", f"  {icon} {name}"); cell.set_property("foreground", color)

    def _on_row_activated(self, treeview, path, column):
        model = treeview.get_model(); tree_iter = model.get_iter(path); full_path = model.get_value(tree_iter, 1); is_folder = model.get_value(tree_iter, 2)
        if is_folder:
            if treeview.row_expanded(path): treeview.collapse_row(path)
            else: treeview.expand_row(path, False)
        else:
            if Path(full_path).exists(): self.on_file_select(Path(full_path))

    def load_project(self, root: Path, config: dict):
        self.project_root = root
        # CORRECTION CRITIQUE : Vider complètement le TreeStore
        self.tree_store.clear()
        try:
            self._populate_tree(root, None)
            # Cette ligne est cruciale : elle met à jour l'onglet "Récents"
            self._load_recent_projects(config) 
            self.start_watcher(root)
        except Exception as e:
            self._log_message(f"❌ Erreur chargement projet: {e}")
            
    def _populate_tree(self, directory: Path, parent_iter):
        """Remplit l'arbre récursivement. Toutes les erreurs sont loggées."""
        if not directory:
            return

        try:
            # Vérifier si le dossier existe encore
            if not directory.exists():
                self._log_message(f"⚠️ Le dossier n'existe plus: {directory}")
                return

            entries = []
            for entry in directory.iterdir():
                # Filtres standards
                if entry.name in ["__pycache__", "node_modules", ".git", ".venv", "venv"]: 
                    continue
                if not self.show_hidden and entry.name.startswith('.'): 
                    continue
                
                entries.append(entry)
            
            # Tri : Dossiers d'abord, puis fichiers, par ordre alphabétique insensible à la casse
            entries.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
            
            for entry in entries:
                try:
                    is_folder = entry.is_dir()
                    # Ajout au store
                    new_iter = self.tree_store.append(parent_iter, [entry.name, str(entry), is_folder])
                    
                    # Si c'est un dossier, on explore récursivement
                    if is_folder: 
                        self._populate_tree(entry, new_iter)
                except PermissionError:
                    self._log_message(f"⛔ Permission refusée pour: {entry.name}")
                except Exception as e:
                    self._log_message(f"⚠️ Erreur lecture entrée {entry.name}: {e}")
                    
        except PermissionError:
            self._log_message(f"⛔ Permission refusée pour le dossier: {directory}")
        except Exception as e:
            self._log_message(f"❌ Erreur critique dans _populate_tree ({directory}): {e}")

    # Dans la classe FilePanel, méthode _load_recent_projects
    def _load_recent_projects(self, config):
        # Nettoyer la liste actuelle
        while child := self.recent_list.get_first_child(): 
            self.recent_list.remove(child)
            
        # Récupérer les projets depuis la DB
        for proj_path in get_recent_projects(config):
            path = Path(proj_path)
            if path.exists():
                row = Gtk.ListBoxRow()
                row._project_path = path
                
                # Affichage plus clair : Nom du projet + Chemin parent
                lbl = Gtk.Label(label=f"  📂 {path.name}\n{path.parent}")
                lbl.set_xalign(0)
                lbl.set_margin_start(16)
                lbl.set_margin_top(6)
                lbl.set_margin_bottom(6)
                lbl.set_ellipsize(Pango.EllipsizeMode.END)
                lbl.set_max_width_chars(35)
                lbl.add_css_class("file-item")
                
                row.set_child(lbl)
                self.recent_list.append(row)
    def _on_project_selected(self, lb, row):
        if hasattr(row, "_project_path"): self.on_project_select(row._project_path)

    def _create_new_file(self, *_):
        if not self.project_root: return self._show_error("Aucun projet ouvert")
        dialog = Gtk.Dialog(title="Nouveau fichier", transient_for=self.get_root()); dialog.add_css_class("rounded-dialog"); dialog.set_default_size(400, 250)
        content = dialog.get_content_area(); content.set_spacing(8); set_margins(content, 12)
        content.append(Gtk.Label(label="Nom du fichier (avec extension):", xalign=0))
        entry = Gtk.Entry(); entry.set_placeholder_text("ex: style.css, script.js, main.c"); content.append(entry)
        content.append(Gtk.Label(label="Contenu initial (optionnel):", xalign=0, margin_top=8))
        text_buf = GtkSource.Buffer()
        text_view = GtkSource.View.new_with_buffer(text_buf)
        text_view.set_size_request(-1, 100)
        text_view.set_show_line_numbers(True)
        text_view.set_monospace(True)
        
        lang_mgr = GtkSource.LanguageManager.get_default()
        lang_py = lang_mgr.get_language("python")
        if lang_py: text_buf.set_language(lang_py)
        
        scroll = Gtk.ScrolledWindow(); scroll.set_child(text_view); content.append(scroll)
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_cancel = Gtk.Button(label="Annuler"); btn_create = Gtk.Button(label="✅ Créer"); btn_create.add_css_class("suggested-action")
        btn_box.append(btn_cancel); btn_box.append(btn_create); content.append(btn_box)
        def on_create(*_):
            filename = entry.get_text().strip()
            if not filename: return self._show_error("Nom requis")
            filepath = self.project_root / filename
            if filepath.exists(): return self._show_error(f"{filename} existe déjà")
            text = text_buf.get_text(text_buf.get_start_iter(), text_buf.get_end_iter(), True) or f"# {filename}\n# Créé avec Gykhamine Studio\n"
            try:
                filepath.write_text(text, encoding='utf-8')
                self.on_file_created(filepath); self.load_project(self.project_root, load_config()); dialog.destroy()
            except Exception as e:
                self._log_message(f"❌ Erreur création fichier: {e}")
                self._show_error(f"Erreur: {e}")
        btn_create.connect("clicked", on_create); btn_cancel.connect("clicked", lambda *_: dialog.destroy()); dialog.present()

    def _import_file(self, *_):
        if not self.project_root: return self._show_error("Aucun projet ouvert")
        Gtk.FileDialog(title="Importer un fichier").open(self.get_root(), None, self._on_import_selected)

    def _on_import_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                src = Path(file.get_path()); dst = self.project_root / src.name
                if dst.exists() and Gtk.MessageDialog(transient_for=self.get_root(), flags=0, message_type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.YES_NO, text="Fichier existant", secondary_text=f"{dst.name} existe. Écraser ?").run() != Gtk.ResponseType.YES:
                    return
                shutil.copy2(src, dst); self.on_file_imported(dst); self.load_project(self.project_root, load_config())
        except Exception as e: 
            self._log_message(f"❌ Erreur importation: {e}")
            self._show_error(f"Erreur: {e}")

    def _show_error(self, msg: str):
        root = self.get_root()
        if root and hasattr(root.get_child(), "add_toast"): root.get_child().add_toast(Adw.Toast(title=f"❌ {msg}", timeout=3))

    def _show_toast(self, msg: str):
        root = self.get_root()
        if root and hasattr(root.get_child(), "add_toast"): root.get_child().add_toast(Adw.Toast(title=msg, timeout=3))

    def _on_right_click(self, gesture, n_press, x, y):
        result = self.tree_view.get_path_at_pos(int(x), int(y))
        if result is None: return
        path, column, cell_x, cell_y = result; self.tree_view.set_cursor(path)
        model = self.tree_view.get_model(); tree_iter = model.get_iter(path)
        name = model.get_value(tree_iter, 0); full_path = model.get_value(tree_iter, 1); is_folder = model.get_value(tree_iter, 2)
        self._show_context_menu(int(x), int(y), full_path, name, is_folder)

    def _set_clipboard(self, action, path, popover):
        self.clipboard_action = action
        self.clipboard_path = path
        popover.popdown()
        self._show_toast(f"✅ {path} mis dans le presse-papiers ({action})")

    def _paste_clipboard(self, target_dir, popover):
        popover.popdown()
        if not self.clipboard_action or not self.clipboard_path:
            return
        src = Path(self.clipboard_path)
        dst = Path(target_dir) / src.name
        
        # Sécurité : Éviter de coller un dossier dans lui-même
        if src.resolve() == dst.resolve() or str(src.resolve()) in str(dst.resolve()):
            self._show_error("❌ Impossible de coller un élément dans lui-même ou un de ses sous-dações.")
            return

        try:
            if self.clipboard_action == "copy":
                if src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                self._show_toast(f"✅ Copié vers {dst.name}")
            elif self.clipboard_action == "cut":
                shutil.move(str(src), str(dst))
                self.clipboard_action = None
                self.clipboard_path = None
                self._show_toast(f"✅ Déplacé vers {dst.name}")
            
            self.load_project(self.project_root, load_config())
        except Exception as e:
            self._log_message(f"❌ Erreur collage: {e}")
            self._show_error(f"Erreur: {e}")

    def _show_context_menu(self, x, y, full_path, name, is_folder):
        popover = Gtk.Popover(); popover.set_parent(self.tree_view); popover.set_has_arrow(False)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4); set_margins(box, 6)
        # --- NOUVEAU: Gestion Copier/Couper/Coller ---
        if not is_folder:
            btn_copy = Gtk.Button(label="📋 Copier"); btn_copy.set_halign(Gtk.Align.FILL); btn_copy.add_css_class("flat"); btn_copy.connect("clicked", lambda *_: self._set_clipboard("copy", full_path, popover))
            btn_cut = Gtk.Button(label="✂️ Couper"); btn_cut.set_halign(Gtk.Align.FILL); btn_cut.add_css_class("flat"); btn_cut.connect("clicked", lambda *_: self._set_clipboard("cut", full_path, popover))
            box.append(btn_copy); box.append(btn_cut)
        else:
            if self.clipboard_action and self.clipboard_path:
                btn_paste = Gtk.Button(label=f"📥 Coller ici ({self.clipboard_action})"); btn_paste.set_halign(Gtk.Align.FILL); btn_paste.add_css_class("flat"); btn_paste.add_css_class("suggested-action"); btn_paste.connect("clicked", lambda *_: self._paste_clipboard(full_path, popover))
                box.append(btn_paste)
            btn_copy_dir = Gtk.Button(label="📋 Copier le dossier"); btn_copy_dir.set_halign(Gtk.Align.FILL); btn_copy_dir.add_css_class("flat"); btn_copy_dir.connect("clicked", lambda *_: self._set_clipboard("copy", full_path, popover))
            btn_cut_dir = Gtk.Button(label="✂️ Couper le dossier"); btn_cut_dir.set_halign(Gtk.Align.FILL); btn_cut_dir.add_css_class("flat"); btn_cut_dir.connect("clicked", lambda *_: self._set_clipboard("cut", full_path, popover))
            box.append(btn_copy_dir); box.append(btn_cut_dir)

        btn_rename = Gtk.Button(label="✏️ Renommer"); btn_rename.set_halign(Gtk.Align.FILL); btn_rename.add_css_class("flat"); btn_rename.connect("clicked", lambda *_: self._rename_item(full_path, name, is_folder, popover))
        btn_delete = Gtk.Button(label="🗑 Supprimer"); btn_delete.set_halign(Gtk.Align.FILL); btn_delete.add_css_class("flat"); btn_delete.add_css_class("destructive-action"); btn_delete.connect("clicked", lambda *_: self._delete_item(full_path, name, is_folder, popover))
        box.append(btn_rename); box.append(btn_delete); popover.set_child(box)
        rect = Gdk.Rectangle(); rect.x = x; rect.y = y; rect.width = 1; rect.height = 1; popover.set_pointing_to(rect); popover.popup()

    def _rename_item(self, full_path, old_name, is_folder, popover):
        popover.popdown()
        dialog = Gtk.Dialog(title="Renommer", transient_for=self.get_root()); dialog.add_css_class("rounded-dialog"); dialog.set_default_size(350, 150)
        content = dialog.get_content_area(); content.set_spacing(8); set_margins(content, 12)
        content.append(Gtk.Label(label=f"Nouveau nom pour '{old_name}':", xalign=0))
        entry = Gtk.Entry(); entry.set_text(old_name); entry.set_activates_default(True); content.append(entry)
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_cancel = Gtk.Button(label="Annuler"); btn_rename = Gtk.Button(label="✅ Renommer"); btn_rename.add_css_class("suggested-action")
        btn_box.append(btn_cancel); btn_box.append(btn_rename); content.append(btn_box)
        def on_rename(*_):
            new_name = entry.get_text().strip()
            if not new_name or new_name == old_name: dialog.destroy(); return
            if "/" in new_name or "\\" in new_name: self._show_error("Le nom ne peut pas contenir '/' ou '\\'"); return
            new_path = Path(full_path).parent / new_name
            if new_path.exists(): self._show_error(f"'{new_name}' existe déjà"); return
            try:
                Path(full_path).rename(new_path); self.load_project(self.project_root, load_config()); self._show_toast(f"✅ Renommé en '{new_name}'")
            except Exception as e: 
                self._log_message(f"❌ Erreur renommage: {e}")
                self._show_error(f"Erreur: {e}")
            dialog.destroy()
        btn_rename.connect("clicked", on_rename); btn_cancel.connect("clicked", lambda *_: dialog.destroy()); dialog.present()

    def _delete_item(self, full_path, name, is_folder, popover):
        popover.popdown()
        dialog = Gtk.Dialog(title="Confirmer la suppression", transient_for=self.get_root()); dialog.add_css_class("rounded-dialog"); dialog.set_default_size(350, 150)
        content = dialog.get_content_area(); content.set_spacing(8); set_margins(content, 12)
        content.append(Gtk.Label(label=f"Voulez-vous vraiment supprimer '{name}' ?", xalign=0, margin_bottom=8))
        content.append(Gtk.Label(label="Cette action est irréversible.", xalign=0, css_classes=["dim-label"]))
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_cancel = Gtk.Button(label="Annuler"); btn_delete = Gtk.Button(label="🗑 Supprimer"); btn_delete.add_css_class("destructive-action")
        btn_box.append(btn_cancel); btn_box.append(btn_delete); content.append(btn_box)
        def on_delete(*_):
            try:
                path = Path(full_path)
                if path.is_dir(): shutil.rmtree(path)
                else: path.unlink()
                self.load_project(self.project_root, load_config()); self._show_toast(f"🗑 Supprimé: {name}")
            except Exception as e: 
                self._log_message(f"❌ Erreur suppression: {e}")
                self._show_error(f"Erreur: {e}")
            dialog.destroy()
        btn_delete.connect("clicked", on_delete); btn_cancel.connect("clicked", lambda *_: dialog.destroy()); dialog.present()
class TerminalPanel(Gtk.Box):
    def __init__(self, get_project_root, get_config, show_toast):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.get_project_root, self.get_config, self.show_toast = get_project_root, get_config, show_toast
        self.add_css_class("terminal-panel"); self._build()
        self.ai_engine = BlockAIEngine(config_getter=self.get_config, log_callback=self._log)

    def _build(self):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8); header.set_margin_start(8); header.set_margin_end(8); header.set_margin_top(4); header.set_margin_bottom(4)
        header.append(Gtk.Label(label="🖥 Terminal Log", css_classes=["terminal-title"]))
        spacer = Gtk.Box(); spacer.set_hexpand(True); header.append(spacer)
        btn_analyze = Gtk.Button(label="🔍 Analyseur Logs IA")
        btn_analyze.add_css_class("ctrl-btn-small")
        btn_analyze.connect("clicked", lambda *_: self._open_log_analyzer())
        header.append(btn_analyze)
        btn_gen_cmd = Gtk.Button(label="🤖 Générer Cmd IA")
        btn_gen_cmd.add_css_class("ctrl-btn-small")
        btn_gen_cmd.connect("clicked", lambda *_: self._open_ai_cmd_generator())
        header.append(btn_gen_cmd)
        btn_clear = Gtk.Button(label="🗑 Clear"); btn_clear.add_css_class("ctrl-btn-small"); btn_clear.connect("clicked", lambda *_: self.log_view.get_buffer().set_text(""))
        header.append(btn_clear); self.append(header); self.append(Gtk.Separator())
        
        self.log_view = GtkSource.View()
        self.log_view.set_editable(False)
        self.log_view.set_monospace(True)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_view.set_cursor_visible(False)
        self.log_view.set_show_line_numbers(False)
        self.log_view.add_css_class("log-view")
        
        # Configuration langage Shell pour les logs
        lang_mgr = GtkSource.LanguageManager.get_default()
        lang_sh = lang_mgr.get_language("sh")
        if lang_sh: self.log_view.get_buffer().set_language(lang_sh)
        log_scroll = Gtk.ScrolledWindow(); log_scroll.set_hexpand(True); log_scroll.set_vexpand(True); log_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC); log_scroll.set_child(self.log_view)
        self.append(log_scroll)
        
        self.append(Gtk.Separator())
        term_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6); term_box.set_margin_top(4); term_box.set_margin_bottom(4); term_box.set_margin_start(8); term_box.set_margin_end(8)
        term_box.append(Gtk.Label(label="➜", css_classes=["terminal-prompt"]))
        self.cmd_entry = Gtk.Entry(); self.cmd_entry.set_placeholder_text("Enter a command..."); self.cmd_entry.set_hexpand(True); self.cmd_entry.add_css_class("terminal-input"); self.cmd_entry.connect("activate", self._run_custom_command)
        btn_run = Gtk.Button(label="▶"); btn_run.add_css_class("ctrl-btn-start"); btn_run.connect("clicked", self._run_custom_command)
        term_box.append(self.cmd_entry); term_box.append(btn_run); self.append(term_box)

    def _open_log_analyzer(self, *_):
        dialog = LogAnalyzerDialog(self.get_root(), self.ai_engine, self._log)
        dialog.present()

    def _open_ai_cmd_generator(self, *_):
        dialog = AICmdGeneratorDialog(self.get_root(), self)
        dialog.present()

    def _log(self, text: str):
        def _append():
            buf = self.log_view.get_buffer(); buf.insert(buf.get_end_iter(), f"[{datetime.now().strftime('%H:%M:%S')}] {text}\n")
            adj = self.log_view.get_parent().get_vadjustment(); adj.set_value(adj.get_upper())
        GLib.idle_add(_append); log_to_file(self.get_config(), text)

    def _run_custom_command_text(self, cmd_text):
        self._log(f"💻 $ {cmd_text}")
        root = self.get_project_root()
        def _thread():
            try:
                env = os.environ.copy(); env["PYTHONUNBUFFERED"] = "1"; env["DJANGO_COLORS"] = "nocolor"
                proc = subprocess.Popen(cmd_text, shell=True, cwd=str(root) if root else None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, text=True, bufsize=0, env=env)
                def _read(stream):
                    for line in iter(stream.readline, ''):
                        if line: GLib.idle_add(self._log, line.rstrip())
                    stream.close()
                t1 = threading.Thread(target=_read, args=(proc.stdout,), daemon=True)
                t2 = threading.Thread(target=_read, args=(proc.stderr,), daemon=True)
                t1.start(); t2.start(); t1.join(); t2.join(); proc.wait()
                GLib.idle_add(self._log, f"✅ Finished (code {proc.returncode})")
            except Exception as e: GLib.idle_add(self._log, f"❌ Error: {e}")
        threading.Thread(target=_thread, daemon=True).start()

    def _run_custom_command(self, *_):
        cmd_text = self.cmd_entry.get_text().strip()
        if not cmd_text: return
        self._run_custom_command_text(cmd_text)
        self.cmd_entry.set_text("")

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
        commands = [("📐 makemigrations", "makemigrations"), ("⬆ migrate", "migrate"), ("👤 superuser", "createsuperuser"), ("🐚 shell", "shell"), ("🗄 dbshell", "dbshell"), ("📦 collectstatic", "collectstatic"), ("✅ check", "check"), ("📜 showmigrations", "showmigrations"), ("🧹 flush", "flush")]
        for idx, (label, cmd) in enumerate(commands):
            btn = Gtk.Button(label=label); btn.add_css_class("ctrl-btn")
            if cmd == "createsuperuser": btn.connect("clicked", lambda *_: self._show_createsuperuser_dialog())
            else: btn.connect("clicked", lambda _, c=cmd: self._run_manage_command(c))
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
        except: pass
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
        except Exception:
            pass

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
        except:
            pass

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
        except: pass
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
        except: pass

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
                except Exception: pass
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
        except Exception: pass

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

class CCompilerDialog(Gtk.Dialog):
    def __init__(self, parent, get_config, terminal_log_cb):
        super().__init__(title="🛠️ Compilateur C/C++ & Optimiseur", transient_for=parent, default_width=800, default_height=600)
        self.add_css_class("rounded-dialog")
        self.get_config = get_config
        self.terminal_log = terminal_log_cb
        self.current_output_file = None
        self.ai_engine = BlockAIEngine(config_getter=self.get_config, log_callback=self.terminal_log)
        
        content = self.get_content_area()
        content.set_spacing(10)
        set_margins(content, 16)
        
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.append(Gtk.Label(label="Code Source C/C++", css_classes=["heading"], xalign=0))
        self.combo_type = Gtk.ComboBoxText()
        self.combo_type.append_text("Executable (.out)")
        self.combo_type.append_text("Shared Library (.so)")
        self.combo_type.append_text("Kernel Module (.ko - gcc only)")
        self.combo_type.set_active(0)
        header_box.append(self.combo_type)
        
        btn_compile = Gtk.Button(label="▶ Compiler", css_classes=["suggested-action"])
        btn_compile.connect("clicked", self._on_compile)
        header_box.append(btn_compile)
        
        btn_optimize = Gtk.Button(label="🤖 Optimiser (Eigen3)")
        btn_optimize.add_css_class("ctrl-btn-warn")
        btn_optimize.connect("clicked", self._on_optimize_cpp)
        header_box.append(btn_optimize)
        
        content.append(header_box)
        content.append(Gtk.Separator())
        
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        self.text_view = GtkSource.View()
        self.text_view.set_monospace(True)
        self.text_view.set_wrap_mode(Gtk.WrapMode.NONE)
        self.text_view.set_show_line_numbers(True)
        self.text_view.set_highlight_current_line(True)
        self.text_view.add_css_class("code-editor")
        
        buf_c = GtkSource.Buffer()
        lang_c = GtkSource.LanguageManager.get_default().get_language("c")
        if lang_c: buf_c.set_language(lang_c)
        buf_c.set_text("// Collez votre code C ici\n#include <stdio.h>\nint main() {\nprintf(\"Hello from Gykhamine!\\n\");\nreturn 0;\n}")
        self.text_view.set_buffer(buf_c)
        self.scrolled.set_child(self.text_view)
        content.append(self.scrolled)
        
        content.append(Gtk.Label(label="Sortie Compilation:", xalign=0, margin_top=10))
        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.set_monospace(True)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_view.add_css_class("log-view")
        log_scroll = Gtk.ScrolledWindow()
        log_scroll.set_size_request(-1, 150)
        log_scroll.set_child(self.log_view)
        content.append(log_scroll)
        
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.END)
        btn_close = Gtk.Button(label="Fermer")
        btn_close.connect("clicked", lambda *_: self.destroy())
        btn_box.append(btn_close)
        content.append(btn_box)

    def _log(self, text):
        buf = self.log_view.get_buffer()
        buf.insert(buf.get_end_iter(), f"{text}\n")
        adj = self.log_view.get_parent().get_vadjustment()
        adj.set_value(adj.get_upper())

    def _on_optimize_cpp(self, *_):
        code = self.text_view.get_buffer().get_text(self.text_view.get_buffer().get_start_iter(), self.text_view.get_buffer().get_end_iter(), True)
        if not code.strip():
            self._log("❌ Aucun code à optimiser.")
            return
        dialog = Gtk.Dialog(title="Demande d'Optimisation C++", transient_for=self.get_root())
        dialog.add_css_class("rounded-dialog")
        dialog.set_default_size(400, 200)
        content = dialog.get_content_area()
        content.set_spacing(10)
        set_margins(content, 16)
        content.append(Gtk.Label(label="Décrivez l'optimisation souhaitée (ex: vectorisation, réduction mémoire) :", xalign=0))
        entry_intent = Gtk.Entry(); entry_intent.set_placeholder_text("Optimiser la boucle de calcul..."); content.append(entry_intent)
        btn_gen = Gtk.Button(label="🤖 Générer Code Optimisé", css_classes=["suggested-action"])
        content.append(btn_gen)
        def on_generate(*_):
            intent = entry_intent.get_text().strip() or "Optimiser les performances numériques avec Eigen3"
            self._log("🤖 Génération d'optimisation C++ en cours...")
            dialog.destroy()
            def _thread():
                result = self.ai_engine.process_modification("c_block", code, intent, mode="cpp_optimize")
                if result:
                    GLib.idle_add(lambda: (self.text_view.get_buffer().set_text(result), self._log("✅ Code optimisé généré."), self.text_view.set_buffer(buf_c)))
                else:
                    GLib.idle_add(lambda: self._log("❌ Échec de la génération d'optimisation."))
            threading.Thread(target=_thread, daemon=True).start()
        btn_gen.connect("clicked", on_generate)
        dialog.present()

    def _on_compile(self, *_):
        code = self.text_view.get_buffer().get_text(self.text_view.get_buffer().get_start_iter(), self.text_view.get_buffer().get_end_iter(), True)
        if not code.strip():
            self._log("❌ Aucun code à compiler.")
            return

        import tempfile
        
        # Détection basique du langage C++
        is_cpp = any(kw in code for kw in ["#include <iostream>", "std::", "class ", "namespace ", "#include <vector>"])
        
        # Si c'est du C++, on utilise .cpp, sinon .c
        suffix = ".cpp" if is_cpp else ".c"
        fd, src_path = tempfile.mkstemp(suffix=suffix)
        
        try:
            with os.fdopen(fd, 'w') as f: 
                f.write(code)

            output_type = self.combo_type.get_active()
            out_ext = ".out"
            compiler_flags = []
            
            # Choix du compilateur
            compiler = "g++" if is_cpp else "gcc"

            if output_type == 1: 
                out_ext = ".so"
                # -fPIC est nécessaire pour les bibliothèques partagées dans les deux langages
                compiler_flags = ["-shared", "-fPIC"]
            elif output_type == 2: 
                out_ext = ".ko"
                # Les modules kernel sont généralement en C pur, mais on laisse l'option
                compiler_flags = ["-c"]
                if is_cpp:
                    self._log("⚠️ Attention : Les modules kernel (.ko) sont rarement écrits en C++.")

            # Nom du fichier de sortie
            out_path = src_path.replace(suffix, out_ext)
            self.current_output_file = out_path
            
            cmd = [compiler] + compiler_flags + [src_path, "-o", out_path]
            
            # Ajout des bibliothèques standards si nécessaire
            if output_type == 1: 
                cmd.append("-lm") # Math library
            if is_cpp and output_type != 2: 
                # g++ lie automatiquement libstdc++, mais c'est une bonne pratique de s'en assurer
                pass 

            self._log(f"▶ Compilation ({compiler}): {' '.join(cmd)}")
            proc = subprocess.run(cmd, capture_output=True, text=True)
            
            if proc.returncode == 0:
                self._log(f"✅ Succès! Fichier généré: {out_path}")
                self._log(f"💡 Vous pouvez le trouver dans le dossier temporaire ou le déplacer.")
            else:
                self._log(f"❌ Erreur de compilation:")
                self._log(proc.stderr)
        finally:
            # Nettoyage du fichier source temporaire si besoin, 
            # mais on le laisse souvent pour déboguer si ça échoue
            pass

class TabButton(Gtk.Box):
    def __init__(self, file_path, on_close, on_activate):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.file_path = file_path
        self.on_close = on_close
        self.add_css_class("tab-button")
        ext = Path(file_path).suffix.lower()
        icon = "📄"
        if ext == '.py': icon = "🐍"
        elif ext in ['.c', '.cpp', '.h']: icon = "⚙️"
        elif ext == '.js': icon = "⚡"
        elif ext == '.css': icon = "🎨"
        elif ext in ['.html', '.jinja']: icon = "🌐"
        lbl = Gtk.Label(label=f"{icon} {Path(file_path).name}")
        lbl.set_ellipsize(Pango.EllipsizeMode.END)
        lbl.set_max_width_chars(15)
        lbl.set_xalign(0)
        self.append(lbl)
        btn_close = Gtk.Button(label="✕")
        btn_close.add_css_class("flat")
        btn_close.set_tooltip_text("Fermer l'onglet")
        btn_close.connect("clicked", lambda *_: on_close(file_path))
        self.append(btn_close)
        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", lambda *_: on_activate(file_path))
        self.add_controller(gesture)

    def set_active(self, active):
        if active: self.add_css_class("active-tab")
        else: self.remove_css_class("active-tab")

class BlockEditorView(Gtk.Box):
    def __init__(self, toast_cb, run_file_cb, get_config_cb=None, ai_engine=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.toast_cb, self.run_file_cb, self._get_config_cb = toast_cb, run_file_cb, get_config_cb
        self.ai_engine = ai_engine
        self.current_file, self.blocks, self._cards, self.css_file, self.file_ext = None, [], [], None, "py"
        self.undo_stack, self.redo_stack, self.max_history = [], [], 20
        
        self.tab_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.tab_bar.add_css_class("tab-bar")
        self.tab_bar.set_margin_start(8)
        self.tab_bar.set_margin_top(4)
        self.open_tabs = {}
        self.active_tab_path = None
        self.append(self.tab_bar)
        
        self.file_label = Gtk.Label(label="Select a file"); self.file_label.add_css_class("editor-file-label"); self.file_label.set_xalign(0)
        set_margins(self.file_label, 12); self.append(self.file_label); self.append(Gtk.Separator())
        self._build_toolbar()
        
        self.scroll = Gtk.ScrolledWindow(); self.scroll.set_vexpand(True); self.scroll.set_hexpand(True); self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.blocks_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8); set_margins(self.blocks_box, 16)
        self.scroll.set_child(self.blocks_box); self.append(self.scroll)

    def _build_toolbar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8); set_margins(bar, 8)
        bar.append(Gtk.Label(label="Blocks:", css_classes=["toolbar-label"]))
        self.lbl_count = Gtk.Label(label="0"); self.lbl_count.add_css_class("block-count-badge"); bar.append(self.lbl_count)
        spacer = Gtk.Box(); spacer.set_hexpand(True); bar.append(spacer)
        btn_compiler = Gtk.Button(label="🛠️ Compiler C"); btn_compiler.add_css_class("ctrl-btn-warn"); btn_compiler.connect("clicked", self._open_c_compiler)
        bar.append(btn_compiler)
        btn_add = Gtk.Button(label="➕ Add block"); btn_add.add_css_class("ctrl-btn-start"); btn_add.connect("clicked", self._add_block_dialog); bar.append(btn_add)
        for label, cb in [("↩ Undo", self._undo), ("↪ Redo", self._redo), ("⬇ Expand all", self._expand_all), ("⬆ Collapse all", self._collapse_all)]:
            btn = Gtk.Button(label=label); btn.add_css_class("toolbar-btn"); btn.connect("clicked", cb); bar.append(btn)
        btn_run = Gtk.Button(label="▶ Run"); btn_run.add_css_class("ctrl-btn-start"); btn_run.connect("clicked", lambda *_: self._run_current_file()); bar.append(btn_run)
        self.btn_css = Gtk.Button(label="🎨 Edit associated CSS"); self.btn_css.add_css_class("toolbar-btn"); self.btn_css.set_visible(False); self.btn_css.connect("clicked", self._open_linked_css); bar.append(self.btn_css)
        btn_save = Gtk.Button(label="💾 Save"); btn_save.add_css_class("save-file-btn"); btn_save.connect("clicked", self._save_file); bar.append(btn_save)
        self.append(bar); self.append(Gtk.Separator())

    def _open_c_compiler(self, *_):
        dialog = CCompilerDialog(self.get_root(), self._get_config_cb, self.toast_cb)
        dialog.present()

    def _add_tab(self, file_path):
        if file_path in self.open_tabs:
            self._activate_tab(file_path)
            return
        tab_btn = TabButton(file_path, self._close_tab, self._activate_tab)
        self.open_tabs[file_path] = tab_btn
        self.tab_bar.append(tab_btn)
        self._activate_tab(file_path)

    def _activate_tab(self, file_path):
        if self.active_tab_path == file_path: return
        self.active_tab_path = file_path
        for path, btn in self.open_tabs.items():
            btn.set_active(path == file_path)
        self.load_file(Path(file_path))

    def _close_tab(self, file_path):
        if file_path in self.open_tabs:
            btn = self.open_tabs.pop(file_path)
            self.tab_bar.remove(btn)
            if self.active_tab_path == file_path:
                self.active_tab_path = None
                self.file_label.set_text("Select a file")
                while child := self.blocks_box.get_first_child(): self.blocks_box.remove(child)
                self._cards = []
                self.blocks = []
                if self.open_tabs:
                    next_path = list(self.open_tabs.keys())[0]
                    self._activate_tab(next_path)

    def _add_block_dialog(self, *_):
        if not self.current_file: return self.toast_cb("❌ No file open")
        dialog = Gtk.Dialog(title="Add a new block", transient_for=self.get_root()); dialog.add_css_class("rounded-dialog"); dialog.set_default_size(400, 250)
        content = dialog.get_content_area(); set_margins(content, 12); content.set_spacing(8)
        content.append(Gtk.Label(label="Block type:", xalign=0))
        type_combo = Gtk.ComboBoxText()
        for t in ["Function (def)", "Class (class)", "Separator (####)", "Comment (#)", "Empty block"]: type_combo.append_text(t)
        type_combo.set_active(0); content.append(type_combo)
        content.append(Gtk.Label(label="Name / Title:", xalign=0, margin_top=8))
        name_entry = Gtk.Entry(); name_entry.set_placeholder_text("e.g., my_function, MySeparator"); content.append(name_entry)
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_cancel = Gtk.Button(label="Cancel"); btn_add = Gtk.Button(label="✅ Add"); btn_add.add_css_class("suggested-action")
        btn_box.append(btn_cancel); btn_box.append(btn_add); content.append(btn_box)
        def on_add(*_):
            btype_raw = type_combo.get_active_text(); name = name_entry.get_text().strip() or "new_block"
            if "Function" in btype_raw: code, btype = f"def {name}():\n    pass\n", "function"
            elif "Class" in btype_raw: code, btype = f"class {name}:\n    pass\n", "class"
            elif "Separator" in btype_raw: code, btype = f"################################\n# {name}\n################################\n", "separator"
            elif "Comment" in btype_raw: code, btype = f"# {name}\n", "comment"
            else: code, btype = f"# {name}\n", "other"
            self.blocks.append({"type": btype, "name": name, "code": code, "start": len(self.blocks), "end": len(self.blocks)})
            self._push_state(); self._render_blocks(); self.toast_cb(f"✅ Block '{name}' added"); dialog.destroy()
        btn_add.connect("clicked", on_add); btn_cancel.connect("clicked", lambda *_: dialog.destroy()); dialog.present()

    def _push_state(self):
        self.undo_stack.append("".join(b["code"] for b in self.blocks))
        if len(self.undo_stack) > self.max_history: self.undo_stack.pop(0)
        self.redo_stack.clear()

    def _undo(self, *_):
        if len(self.undo_stack) > 1:
            self.redo_stack.append(self.undo_stack.pop()); self._restore_state(self.undo_stack[-1]); self.toast_cb("↩ Undone")

    def _redo(self, *_):
        if self.redo_stack:
            state = self.redo_stack.pop(); self.undo_stack.append(state); self._restore_state(state); self.toast_cb("↪ Redone")

    def _restore_state(self, state: str):
        self.blocks = parse_blocks(state, str(self.current_file) if self.current_file else ""); self._render_blocks()

    def load_file(self, path: Path):
        self.current_file = path; self.file_label.set_text(f"📄  {path.name}")
        self.file_ext = path.suffix.lower().replace('.', ''); self.css_file = None
        if path.suffix == '.py':
            linked_css = path.with_suffix('.css')
            if linked_css.exists(): self.css_file = linked_css; self.btn_css.set_label(f"🎨 Edit {linked_css.name}"); self.btn_css.set_visible(True)
            else: self.btn_css.set_visible(False)
        try:
            self.blocks = parse_blocks(path.read_text(encoding="utf-8"), str(path))
            self._push_state(); self._render_blocks()
            if self._get_config_cb: memory_record(self._get_config_cb(), str(path.parent), str(path), action="open")
        except Exception as e: self.file_label.set_text(f"❌ Error: {e}")
        self._add_tab(str(path))

    def _open_linked_css(self, *_):
        if self.css_file and self.css_file.exists(): self._save_file(); self.load_file(self.css_file); self.toast_cb(f"🎨 {self.css_file.name}")

    def _render_blocks_recursive(self, blocks, container, level=0, parent_prefix=""):
        """Rend les blocs et leurs enfants de manière récursive avec indentation et numérotation."""
        for index, block in enumerate(blocks):
            # Calcul de l'ID hiérarchique (ex: 1.2.1)
            current_index = index + 1
            if parent_prefix:
                block["hierarchical_id"] = f"{parent_prefix}.{current_index}"
            else:
                block["hierarchical_id"] = str(current_index)
            
            # Le nom interne reste utile pour la logique, mais l'affichage utilise hierarchical_id
            # On garde block["name"] tel quel pour la compatibilité interne si besoin, 
            # mais l'UI utilisera hierarchical_id via la Modif 1.
            card = BlockCard(
                block, 
                self._on_block_save, 
                self._on_block_delete, 
                self._on_block_copy, 
                self.file_ext, 
                ai_engine=self.ai_engine, 
                parent_window=self
            )
            
            # Indentation visuelle pour les enfants
            if level > 0:
                card.set_margin_start(level * 20)
                card.add_css_class("child-block") 
            
            container.append(card)
            self._cards.append(card) 
            
            # Si le bloc a des enfants, on les rend récursivement en passant le préfixe actuel
            if block.get("children"):
                self._render_blocks_recursive(block["children"], container, level + 1, parent_prefix=block["hierarchical_id"])


    def _render_blocks(self):
        while child := self.blocks_box.get_first_child(): 
            self.blocks_box.remove(child)
        
        self.lbl_count.set_text(str(len(self.blocks)))
        self._cards = []
        
        # Appel récursif initial au niveau 0
        self._render_blocks_recursive(self.blocks, self.blocks_box, level=0)

    def _on_block_save(self, block, new_code):
        # CORRECTION CRITIQUE : Forcer un saut de ligne à la fin de chaque bloc 
        # pour éviter que le bloc suivant ne se colle à lui (ex: "return finidef autre()")
        if not new_code.endswith('\n'):
            new_code += '\n'
            
        block["code"] = new_code
        self._push_state()
        self.toast_cb("✅ Updated")
        
        if self.current_file and self._get_config_cb:
            memory_record(self._get_config_cb(), str(self.current_file.parent), str(self.current_file), block.get("name"), "edit")
            
    def _on_block_delete(self, block):
        self.blocks.remove(block); self._push_state(); self._render_blocks(); self.toast_cb("🗑 Deleted")

    def _on_block_copy(self, code):
        Gdk.Display.get_default().get_clipboard().set(code); self.toast_cb("⧉ Copied")

    def _expand_all(self, *_):
        for card in self._cards:
            if not card.expanded: card._toggle_edit()

    def _collapse_all(self, *_):
        for card in self._cards:
            if card.expanded: card._toggle_edit()

    def _save_file(self, *_):
        if not self.current_file:
            return self.toast_cb("❌ No file open")
        try:
            # 1. Créer un fichier de sauvegarde (.bak)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.current_file.with_suffix(f".{timestamp}{self.current_file.suffix}.bak")
            if self.current_file.exists():
                shutil.copy2(self.current_file, backup_path)
            
            # 2. Écrire dans un fichier temporaire
            temp_path = self.current_file.with_suffix(f".{timestamp}.tmp")
            
            # CORRECTION CRITIQUE : S'assurer que chaque bloc se termine par un saut de ligne 
            # avant de les concaténer, même si un bloc a été corrompu en mémoire.
            safe_blocks = []
            for b in self.blocks:
                code = b["code"]
                if not code.endswith('\n'):
                    code += '\n'
                safe_blocks.append(code)
                
            new_content = "".join(safe_blocks)
            temp_path.write_text(new_content, encoding="utf-8")
            
            # 3. Remplacer le fichier original
            shutil.move(str(temp_path), str(self.current_file))
            self._push_state()
            self.toast_cb(f"💾 Saved: {self.current_file.name} (Backup: {backup_path.name})")
            
        except Exception as e:
            self.toast_cb(f"❌ Error: {e}")




    def _run_current_file(self, *_):
        if not self.current_file: return self.toast_cb("❌ No file")
        if self.run_file_cb: self.run_file_cb(self.current_file)

class DirectoryPickerRow(Adw.ActionRow):
    def __init__(self, title, subtitle, initial_value, filename):
        super().__init__(title=title, subtitle=subtitle)
        self.filename = filename
        self.entry = Gtk.Entry(); self.entry.set_text(initial_value); self.entry.set_hexpand(True); self.add_suffix(self.entry)
        btn = Gtk.Button(icon_name="folder-symbolic"); btn.set_tooltip_text("Choose folder"); btn.set_valign(Gtk.Align.CENTER); btn.connect("clicked", self._on_browse); self.add_suffix(btn)

    def _on_browse(self, btn):
        Gtk.FileDialog(title="Choose destination folder").select_folder(self.get_root(), None, self._on_folder_selected)

    def _on_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder: self.entry.set_text(str(Path(folder.get_path()) / self.filename))
        except Exception: pass

    def get_text(self): return self.entry.get_text()

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
        pg_device_row = DirectoryPickerRow(title="Périphérique de la partition", subtitle="Sélectionnez /dev/sdX ou un fichier image", initial_value=config.get("pg_device", ""), filename="")
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
        for key, title, placeholder in [("redis_port", "Port", "6379"), ("redis_data_dir", "Dossier de données", str(Path.home() / "redis_data")), ("redis_env_path", "Chemin du fichier .env", "/run/media/gykhamine/GY/Gykhamine/gy/.env")]:
            row = Adw.EntryRow(title=title); row.set_text(str(config.get(key, placeholder))); self._rows[key] = row; grp_redis.add(row)
        persist_row = Adw.SwitchRow(title="Utiliser la persistance (AOF)"); persist_row.set_active(config.get("redis_use_persistence", True)); self._rows["redis_use_persistence"] = persist_row; grp_redis.add(persist_row)
        env_update_row = Adw.SwitchRow(title="Mettre à jour REDIS_URL dans le .env"); env_update_row.set_active(config.get("redis_update_env", False)); env_update_row.set_subtitle("Respecte la gestion manuelle si désactivé"); self._rows["redis_update_env"] = env_update_row; grp_redis.add(env_update_row)
        
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
            elif hasattr(row, "get_text"): self.config[key] = row.get_text()
        try:
            self.config["default_port_range_start"] = int(self.config.get("default_port_range_start", 8000))
            self.config["default_port_range_end"] = int(self.config.get("default_port_range_end", 8010))
        except: pass
        self.on_save(self.config); self.close()


# ═══════════════════════════════════════════════════════════════════════
#  DOCUMENTATION MASTER DJANGO & PYTHON (EXHAUSTIVE - STYLE NEO4J)
# ═══════════════════════════════════════════════════════════════════════

# ... (Previous code remains unchanged) ...

class DjangoMasterDocDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="📚 Documentation Master : Django & Python", transient_for=parent, default_width=1200, default_height=800)
        self.add_css_class("rounded-dialog")
        
        # Configuration de la fenêtre principale
        content_area = self.get_content_area()
        content_area.set_spacing(0)
        
        # Layout Principal : Sidebar (Gauche) + Contenu (Droite)
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.set_hexpand(True)
        main_box.set_vexpand(True)
        
        # 1. SIDEBAR DE NAVIGATION & RECHERCHE
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar.set_size_request(320, -1)
        sidebar.add_css_class("sidebar-bg") # Fond sombre
        
        # Barre de recherche
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        search_box.set_margin_start(10)
        search_box.set_margin_end(10)
        search_box.set_margin_top(10)
        search_box.set_margin_bottom(10)
        
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("🔍 Rechercher un concept...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("changed", self._on_search_changed)
        search_box.append(self.search_entry)
        sidebar.append(search_box)
        
        # Liste de navigation
        scroll_sidebar = Gtk.ScrolledWindow()
        scroll_sidebar.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll_sidebar.set_vexpand(True)
        
        self.nav_listbox = Gtk.ListBox()
        self.nav_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.nav_listbox.connect("row-selected", self._on_nav_selected)
        scroll_sidebar.set_child(self.nav_listbox)
        sidebar.append(scroll_sidebar)
        
        # 2. ZONE DE CONTENU PRINCIPAL
        content_stack = Gtk.Stack()
        content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        content_stack.set_hexpand(True)
        content_stack.set_vexpand(True)
        
        scroll_content = Gtk.ScrolledWindow()
        scroll_content.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll_content.set_vexpand(True)
        scroll_content.set_hexpand(True)
        
        self.content_view = GtkSource.View()
        self.content_view.set_editable(False)
        self.content_view.set_cursor_visible(False)
        self.content_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.content_view.set_monospace(False)
        self.content_view.set_show_line_numbers(False)
        self.content_view.add_css_class("code-editor")
        self.content_view.set_margin_start(30)
        self.content_view.set_margin_end(30)
        self.content_view.set_margin_top(30)
        self.content_view.set_margin_bottom(30)
        
        scroll_content.set_child(self.content_view)
        content_stack.add_named(scroll_content, "main")
        
        main_box.append(sidebar)
        main_box.append(content_stack)
        
        # Pied de page
        footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        footer_box.set_margin_start(16)
        footer_box.set_margin_end(16)
        footer_box.set_margin_top(8)
        footer_box.set_margin_bottom(8)
        
        btn_close = Gtk.Button(label="Fermer")
        btn_close.connect("clicked", lambda *_: self.destroy())
        btn_close.set_halign(Gtk.Align.END)
        footer_box.append(btn_close)
        
        content_area.append(main_box)
        content_area.append(Gtk.Separator())
        content_area.append(footer_box)
        
        # Initialisation des données exhaustives
        self.doc_data = self._generate_exhaustive_content()
        self.all_items = [] # Pour la recherche
        self._populate_sidebar()
        
        # Sélectionner le premier élément par défaut
        first_row = self.nav_listbox.get_row_at_index(0)
        if first_row:
            self.nav_listbox.select_row(first_row)

    def _on_search_changed(self, entry):
        query = entry.get_text().lower().strip()
        # Vider la liste actuelle
        while child := self.nav_listbox.get_first_child():
            self.nav_listbox.remove(child)
            
        if not query:
            # Restaurer la liste complète
            for item in self.all_items:
                self.nav_listbox.append(item['row'])
        else:
            # Filtrer par titre ou mots-clés
            for item in self.all_items:
                if query in item['keywords'] or query in item['title'].lower():
                    self.nav_listbox.append(item['row'])

    def _on_nav_selected(self, listbox, row):
        if row and hasattr(row, "_content_key"):
            key = row._content_key
            if key in self.doc_data:
                self._display_content(self.doc_data[key])
            else:
                self._display_content(f"Erreur: Contenu introuvable pour la section '{key}'")

    def _display_content(self, text_content):
        """Affiche le contenu dans le TextView en préservant le formatage simple."""
        buf = self.content_view.get_buffer()
        buf.set_text(text_content)

    def _populate_sidebar(self):
        categories = [
            ("intro", "1. Les Bases (Py, C++, JS, CSS, HTML)", "python cpp js html css base syntaxe"),
            ("mvt", "2. Architecture MVT", "model view template architecture mvc django"),
            ("project_app", "3. Structure Projet & App", "startproject startapp settings urls wsgi asgi installed_apps"),
            ("manage", "4. Manage.py & Migrations", "makemigrations migrate createsuperuser collectstatic shell dumpdata loaddata"),
            ("models", "5. Les Modèles Django", "database orm class model schema table meta on_delete"),
            ("fields", "6. Liste des Fields (Copiable)", "charfield textfield integer boolean foreignkey manytomany uuid email url file image"),
            ("field_opts", "7. Options des Champs", "null blank default unique choices verbose_name help_text"),
            ("model_methods", "8. Astuces Pro Modèles", "save delete str property get_absolute_url clean signals"),
            ("views", "9. Les Vues (FBV & CBV)", "function based class based listview detailview createview updateview request response"),
            ("decorators", "10. Décorateurs Django", "login_required permission_required csrf_exempt cache require_post"),
            ("view_cases", "11. Cas GET/POST/Fichier", "method post get file upload form data"),
            ("responses", "12. Types de Réponses", "httpresponse jsonresponse redirect fileresponse streaming render"),
            ("forms", "13. Les Formulaires", "form modelform clean validation widget formset csrf"),
            ("form_model", "14. Lien Model-Form-Template", "connection link bridge save commit instance"),
            ("form_tips", "15. Astuces Pro Forms", "clean_field initial help_text error_messages"),
            ("templates", "16. Les Templates", "html jinja inheritance block include extends"),
            ("tags", "17. Tags Django & Utilité", "url static csrf if for loop empty load"),
            ("template_logic", "18. Logique Template", "condition boucle filter date length slice truncate"),
            ("filters", "22. Filtres ORM Avancés", "icontains startswith gt lt range in isnull year lookup"),
            ("static_media", "19. Fichiers Statiques & Média", "staticfiles media upload image filefield storage"),
            ("orm", "20. L'ORM Django (Requêtes)", "queryset filter exclude get all order_by count aggregate q object"),
            ("orm_methods", "21. Méthodes Récupération/Soumission", "create update delete bulk_create select_related prefetch_related"),
            ("postgresql", "23. Gestion PostgreSQL", "engine config psycopg2 backup pg_dump production wal"),
            ("sqlite", "24. Gestion SQLite", "wal mode optimization backup pragma dev"),
            ("security", "25. Sécurité & Auth", "csrf xss sql injection login_required permission user group password hash"),
            ("cookies", "26. Cookies & Sessions", "cookie session signed_cookie request.session"),
            ("encryption", "27. Chiffrement & SSL", "hash password argon2 bcrypt fernet symmetric signing token ssl tls"),
            ("js_ajax", "28. JS & AJAX", "fetch api json async await promise"),
            ("browser_api", "29. API Navigateur", "camera microphone geolocation filesystem clipboard"),
            ("api_drf", "30. API REST Framework", "serializer viewset router jwt token authentication permission cors"),
            ("channels", "31. Django Channels", "websocket asgi consumer redis real-time chat"),
            ("celery", "32. Celery (Async)", "task queue broker redis rabbitmq background email"),
            ("nginx_gunicorn", "33. Nginx & Gunicorn", "proxy_pass upstream worker ssl certificate systemd service"),
            ("gunicorn_opts", "34. Options CMD Gunicorn", "workers threads bind timeout preload max_requests log"),
            ("production", "35. Standards Production", "debug false allowed_hosts secret_key environment logging cache redis"),
            ("deploy", "36. Déploiement Gykhamine", "gunicorn nginx ssl systemd deploy production studio"),
            ("tips", "37. Astuces & Bonnes Pratiques", "performance n+1 query only defer exists count test debug toolbar"),
        ]
        
        for key, title, keywords in categories:
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label=title, xalign=0)
            label.set_margin_start(10)
            label.set_margin_top(8)
            label.set_margin_bottom(8)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            row.set_child(label)
            row._content_key = key
            
            self.all_items.append({
                'row': row,
                'title': title,
                'keywords': keywords
            })
            self.nav_listbox.append(row)

    def _generate_exhaustive_content(self):
        data = {}
        
        # --- Helpers for formatting ---
        def fmt_title(t):
            return f"\n{'='*60}\n{t.upper()}\n{'='*60}\n"
        
        def fmt_subtitle(t):
            return f"\n--- {t} ---\n"
        
        def fmt_code(code):
            return f"\n{code}\n"
            
        def mt(t): return fmt_title(t)
        def st(t): return fmt_subtitle(t)
        def cb(c): return fmt_code(c)

# =====================================================================
        # --- 1. BASES & ARCHITECTURE ---
        # =====================================================================

        data["intro"] = (
            mt("1. Les Bases Fondamentales de la Programmation") +
            "Introduction : Pour maîtriser le web, il faut comprendre comment les langages structurent la logique, les données et l'exécution.\n\n" +
            
            st("Concepts Transversaux (Théorie Multi-Langages)") +
            "• Variables : Espaces mémoire nommés pour stocker une valeur. En C, le type est statique (`int x`); en Python/JS, il est dynamique.\n" +
            "• Conditions : Branchements logiques basés sur des booléens (`if / else`).\n" +
            "• Switch / Match : Structure de contrôle pour tester plusieurs valeurs d'une variable. `switch` en C/JS, `match` depuis Python 3.10.\n" +
            "• Boucles : Répétition d'instructions (`for` pour itérer sur une collection, `while` tant qu'une condition est vraie).\n" +
            "• Fonctions : Blocs de code réutilisables prenant des arguments et retournant un résultat.\n" +
            "• Modules : Découpage du code en plusieurs fichiers pour organiser l'application.\n" +
            "• Exceptions : Capture et gestion des erreurs d'exécution pour éviter le crash du programme (`try / except / catch`).\n" +
            "• Classes (POO) : Modèles (Blueprints) permettant de créer des objets regroupant états (attributs) et comportements (méthodes).\n" +
            "• Décorateurs : Fonctions qui enveloppent et modifient le comportement d'une autre fonction ou classe sans modifier son code source.\n\n" +
            
            st("Le Langage C (Le Bas-Niveau & Gestion Mémoire)") +
            "Pourquoi : Comprendre la compilation, les pointeurs, et la gestion stricte des types.\n" +
            cb("#include <stdio.h>\nint main() {\n    int age = 20;\n    if (age >= 18) {\n        printf(\"Majeur\\n\");\n    }\n    return 0;\n}") + "\n\n" +
            
            st("Python (La Logique Backend)") +
            "Pourquoi : Syntaxe épurée, typage dynamique fort, cœur de Django.\n" +
            cb("def verifier_statut(user_role):\n    match user_role:\n        case 'admin': return 'Accès total'\n        case 'client': return 'Accès restreint'\n        case _: raise ValueError('Rôle inconnu')") + "\n\n" +
            
            st("Le Trio Frontend : HTML5 / CSS3 / JavaScript (ES6+)") +
            "• HTML5 : Structure sémantique du DOM.\n" +
            cb("<div id='app'>\n    <h1>Mon Titre</h1>\n    <p class='text'>Texte synchrone</p>\n</div>") + "\n" +
            "• CSS3 : Mise en page (Flexbox, Grid) et design système.\n" +
            cb(".text { color: #2c3e50; font-family: sans-serif; display: flex; }") + "\n" +
            "• JavaScript : Asynchronisme (Promises, Async/Await), manipulation dynamique du DOM.\n" +
            cb("const fetchData = async () => {\n    try {\n        const res = await fetch('/api/data');\n        const data = await res.json();\n        console.log(data);\n    } catch (err) {\n        console.error(err);\n    }\n};")
        )

        data["mvt"] = (
            mt("2. Architecture MVT") +
            "Description : Model-View-Template. Séparation stricte des responsabilités.\n" +
            "Pourquoi : Rend l'application modulaire, scalable et facilement maintenable.\n" +
            "Quand : L'architecture structurelle de référence pour toute application Django.\n" +
            "Comment :\n" +
            "• Model (Données) : Couche d'abstraction (ORM) au-dessus de la base SQL. Gère les contraintes et validations physiques.\n" +
            "• View (Logique métier) : Intercepte la requête HTTP, orchestre l'accès aux données via les modèles, applique la logique de contrôle et retourne une réponse.\n" +
            "• Template (Présentation) : Génère dynamiquement le HTML côté serveur en fusionnant le squelette d'affichage avec les données fournies par la vue."
        )

        data["project_app"] = (
            mt("3. Structure Projet & App") +
            "Description : Architecture modulaire d'un écosystème Django.\n" +
            "Pourquoi : Un projet regroupe les configurations globales (settings, urls, wsgi), tandis qu'une application est un module métier isolé et réutilisable.\n\n" +
            st("Création du Projet et de l'Application") +
            cb("django-admin startproject core_project .\npython manage.py startapp gestion_clinique") + "\n\n" +
            st("Enregistrement Strict (settings.py)") +
            cb("# settings.py\nINSTALLED_APPS = [\n    'django.contrib.admin',\n    'django.contrib.auth',\n    'django.contrib.contenttypes',\n    'django.contrib.sessions',\n    'django.contrib.messages',\n    'django.contrib.staticfiles',\n    # Apps locales autonomes\n    'gestion_clinique.apps.GestionCliniqueConfig',\n]")
        )

        data["manage"] = (
            mt("4. Manage.py & Migrations") +
            "Description : Interface de contrôle en ligne de commande de Django.\n" +
            "Pourquoi : Synchroniser l'état du code source des modèles avec le schéma physique SQL.\n\n" +
            st("Commandes Essentielles et Cycle de Vie") +
            cb("python manage.py makemigrations  # Inspecte les modèles et crée les fichiers d'instructions de migration") + "\n" +
            cb("python manage.py migrate         # Exécute de manière transactionnelle les migrations en base") + "\n" +
            cb("python manage.py createsuperuser # Instancie un utilisateur avec is_staff et is_superuser à True") + "\n" +
            cb("python manage.py collectstatic   # Rassemble les assets statiques dans STATIC_ROOT pour Gunicorn/Nginx") + "\n" +
            cb("python manage.py shell           # Initialise un interpréteur interactif Python configuré avec l'ORM") + "\n" +
            cb("python manage.py dumpdata > data.json # Sérialise la base de données courante dans un fichier JSON")
        )

        # =====================================================================
        # --- 2. MODÈLES & DONNÉES ---
        # =====================================================================

        data["models"] = (
            mt("5. Les Modèles Django & ORM") +
            "Description : Déclaration de la structure des données sous forme de classes Python pures.\n" +
            "Pourquoi : Abstraction SQL totale, typage fort des colonnes, indexation automatique et sécurité native contre les injections SQL.\n\n" +
            st("Exemple Industriel Complet") +
            cb("from django.db import models\nfrom django.contrib.auth.models import User\n\nclass Categorie(models.Model):\n    nom = models.CharField(max_length=100, unique=True)\n\nclass Article(models.Model):\n    STATUT_CHOICES = [('brouillon', 'Brouillon'), ('publie', 'Publié')]\n    \n    titre = models.CharField(max_length=200)\n    slug = models.SlugField(unique=True, max_length=255)\n    contenu = models.TextField()\n    auteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='articles')\n    categorie = models.ForeignKey(Categorie, on_delete=models.PROTECT, null=True, blank=True)\n    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='brouillon')\n    publie = models.BooleanField(default=False)\n    date_creation = models.DateTimeField(auto_now_add=True)\n    date_modification = models.DateTimeField(auto_now=True)\n\n    class Meta:\n        ordering = ['-date_creation']\n        indexes = [\n            models.Index(fields=['slug']),\n            models.Index(fields=['statut']),\n        ]\n\n    def __str__(self):\n        return self.titre") + "\n\n" +
            st("Comportements d'Intégrité Référentielle (on_delete)") +
            "• models.CASCADE : Supprime automatiquement les enregistrements dépendants si le parent est détruit.\n" +
            "• models.PROTECT : Lève une `ProtectedError` pour interdire la suppression du parent tant qu'un enfant y est lié.\n" +
            "• models.SET_NULL : Remplace la clé par `NULL`. Requiert impérativement `null=True` sur le champ."
        )

        data["fields"] = (
            mt("6. Liste des Fields Django (Copiable)") +
            "Description : Dictionnaire exhaustif des types de champs pour l'implémentation de modèles.\n\n" +
            cb("models.CharField(max_length=100)       # Varchar SQL standard") + "\n" +
            cb("models.TextField()                     # Text ou LongText SQL pour blocs longs") + "\n" +
            cb("models.IntegerField()                  # Entier signé standard") + "\n" +
            cb("models.FloatField()                    # Nombre à virgule flottante double précision") + "\n" +
            cb("models.DecimalField(max_digits=10, decimal_places=2) # Précision exacte (monétaire)") + "\n" +
            cb("models.BooleanField(default=False)     # Booléen (TinyInt ou Boolean SQL)") + "\n" +
            cb("models.DateField()                     # Date brute (sans heure)") + "\n" +
            cb("models.DateTimeField()                 # Horodatage précis avec timezone") + "\n" +
            cb("models.EmailField()                    # CharField validé par expression régulière email") + "\n" +
            cb("models.URLField()                      # CharField validé par expression régulière URL") + "\n" +
            cb("models.FileField(upload_to='docs/')    # Stocke le chemin du fichier, gère l'upload") + "\n" +
            cb("models.ImageField(upload_to='imgs/')   # FileField avec validation d'intégrité graphique (Pillow)") + "\n" +
            cb("models.ForeignKey('Model', on_delete=models.CASCADE) # Relation 1-à-N") + "\n" +
            cb("models.ManyToManyField('Model')   # Relation N-à-N avec table de jointure automatique") + "\n" +
            cb("models.OneToOneField('Model', on_delete=models.CASCADE) # Relation unique 1-à-1 (extension de table)") + "\n" +
            cb("models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False) # UUID4 unique")
        )

        data["field_opts"] = (
            mt("7. Options des Champs") +
            "Description : Paramètres modifiant le comportement physique (base de données) ou applicatif (formulaires) des champs.\n" +
            "Comment :\n" +
            "• null=True : Impact physique. Autorise la valeur `NULL` au niveau des colonnes de la base de données.\n" +
            "• blank=True : Impact applicatif. Autorise la soumission d'une valeur vide lors de la validation des formulaires.\n" +
            "• default=valeur : Attribue une valeur par défaut automatique si aucune valeur n'est passée à l'instanciation.\n" +
            "• unique=True : Génère une contrainte d'unicité SQL UNIQUE sur la colonne concernée.\n" +
            "• choices=[...] : Limite les choix possibles dans l'interface d'administration et valide la valeur soumise.\n" +
            "• verbose_name='...' : Définit un libellé lisible et propre pour l'interface utilisateur et la génération des formulaires."
        )

        data["model_methods"] = (
            mt("8. Logique Métier dans les Modèles (Pourquoi & Comment)") +
            "Pourquoi : Respecter le paradigme 'Fat Models, Skinny Views'. Centraliser la logique interne des données directement dans le modèle évite la duplication de code et garantit la cohérence du système.\n\n" +
            st("Implémentation Pratique") +
            cb("from django.db import models\nfrom django.utils.text import slugify\nfrom django.urls import reverse\n\nclass Produit(models.Model):\n    nom = models.CharField(max_length=150)\n    slug = models.SlugField(unique=True, blank=True)\n    prix_ht = models.DecimalField(max_digits=10, decimal_places=2)\n    taux_tva = models.DecimalField(max_digits=4, decimal_places=2, default=0.20)\n\n    # Pourquoi : Calculer dynamiquement sans stocker une valeur redondante en base\n    @property\n    def prix_ttc(self):\n        return self.prix_ht * (1 + self.taux_tva)\n\n    # Pourquoi : Permettre à Django de connaître l'URL absolue canonique de cet objet\n    def get_absolute_url(self):\n        return reverse('produit-detail', kwargs={'slug': self.slug})\n\n    # Pourquoi : Intercepter la sauvegarde pour automatiser des actions de nettoyage/calcul\n    def save(self, *args, **kwargs):\n        if not self.slug:\n            self.slug = slugify(self.nom)\n        super().save(*args, **kwargs) # Important : exécuter le comportement natif de sauvegarde")
        )

        # =====================================================================
        # --- 3. VUES & LOGIQUE ---
        # =====================================================================

        data["views"] = (
            mt("9. Routage et Traitement : GET, GET avec arguments, et POST") +
            "Description : Structure universelle permettant d'aiguiller et de traiter les requêtes HTTP selon leur verbe et leurs paramètres.\n\n" +
            st("Exemple Exhaustif en Function Based View (FBV)") +
            cb("from django.shortcuts import render, get_object_or_404, redirect\nfrom django.http import HttpResponseNotAllowed\nfrom .models import Article\nfrom .forms import ArticleForm\n\ndef gestion_article_view(request, article_id=None):\n    # 1. Cas GET avec Argument (Lecture d'un objet spécifique)\n    if request.method == 'GET' and article_id:\n        article = get_object_or_404(Article, id=article_id)\n        return render(request, 'detail.html', {'article': article})\n        \n    # 2. Cas GET Simple (Affichage d'un formulaire vide ou d'une liste)\n    elif request.method == 'GET':\n        form = ArticleForm()\n        articles = Article.objects.all()\n        return render(request, 'index.html', {'form': form, 'articles': articles})\n        \n    # 3. Cas POST (Soumission et écriture en base de données)\n    elif request.method == 'POST':\n        form = ArticleForm(request.POST, request.FILES)\n        if form.is_valid():\n            article = form.save()\n            return redirect('article-detail', article_id=article.id)\n        return render(request, 'index.html', {'form': form})\n        \n    else:\n        return HttpResponseNotAllowed(['GET', 'POST'])")
        )

        data["decorators"] = (
            mt("10. Décorateurs et Mixins dans les Class Based Views (CBV)") +
            "Description : Application de middleware et contrôles de sécurité sur des structures de classes.\n" +
            "Comment : Comme les CBV ne sont pas des fonctions directes, on applique les décorateurs via `method_decorator` sur la méthode `dispatch` de la classe, ou on hérite directement de structures de Mixins sécurisées.\n\n" +
            st("Exemple Pratique et Propre") +
            cb("from django.views.generic import ListView, CreateView\nfrom django.utils.method_decorator import method_decorator\nfrom django.contrib.auth.decorators import login_required, permission_required\nfrom django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin\nfrom .models import Article\n\n# Approche 1 : Utilisation des Mixins d'héritage (Recommandé en CBV)\nclass ArticleSecureCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):\n    model = Article\n    fields = ['titre', 'contenu']\n    template_name = 'form.html'\n    login_url = '/login/'\n    permission_required = 'gestion_clinique.add_article'\n\n# Approche 2 : Utilisation des décorateurs classiques via method_decorator\n@method_decorator(login_required, name='dispatch')\n@method_decorator(permission_required('gestion_clinique.view_article', raise_exception=True), name='dispatch')\nclass ArticleDashboardListView(ListView):\n    model = Article\n    template_name = 'dashboard.html'\n    context_object_name = 'articles'")
        )

        data["view_cases"] = (
            mt("11. Gestion Unifiée des Flux HTTP") +
            "Description : Traitement distinct des cycles de vie des requêtes.\n" +
            "Principe : Une requête POST doit systématiquement être suivie d'une redirection (Pattern PRG : Post/Redirect/Get) afin d'éviter la resoumission accidentelle de formulaires en cas de rafraîchissement de la page par l'utilisateur."
        )

        data["responses"] = (
            mt("12. Liste Complète des Réponses HTTP Django") +
            "Description : Structures de retour serveur normalisées selon le protocole HTTP.\n\n" +
            st("1. Render (Génération HTML)") +
            cb("from django.shortcuts import render\nreturn render(request, 'template.html', {'data': context})") + "\n\n" +
            st("2. Redirect (Redirection HTTP 302/301)") +
            cb("from django.shortcuts import redirect\nreturn redirect('nom-url-pattern', id=obj.id)") + "\n\n" +
            st("3. JsonResponse (Payload pour API Rest ou AJAX)") +
            cb("from django.http import JsonResponse\nreturn JsonResponse({'status': 'success', 'code': 200, 'payload': []}, safe=True)") + "\n\n" +
            st("4. FileResponse (Streaming de fichiers binaires)") +
            cb("from django.http import FileResponse\nfile = open('rapport.pdf', 'rb')\nreturn FileResponse(file, as_attachment=True, filename='export.pdf')") + "\n\n" +
            st("5. Http404 (Lancement d'une exception de page non trouvée)") +
            cb("from django.http import Http404\nraise Http404('La ressource demandée n'existe pas')")
        )

        # =====================================================================
        # --- 4. FORMULAIRES ---
        # =====================================================================

        data["forms"] = (
            mt("13. Validation & Nettoyage avec les Formulaires") +
            "Description : Structure assurant l'étanchéité applicative entre les données utilisateur entrantes et le backend Python.\n\n" +
            st("Exemple Complet et Métier") +
            cb("from django import forms\nfrom .models import Article\n\nclass ArticleForm(forms.ModelForm):\n    class Meta:\n        model = Article\n        fields = ['titre', 'contenu', 'slug']\n        widgets = {\n            'titre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Entrez le titre'}),\n            'contenu': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),\n        }\n\n    # Pourquoi : Valider et nettoyer un champ spécifique de manière isolée\n    def clean_titre(self):\n        titre = self.cleaned_data.get('titre')\n        if \"interdit\" in titre.lower():\n            raise forms.ValidationError(\"Le titre contient un mot non autorisé.\")\n        return titre\n\n    # Pourquoi : Validation globale croisée mettant en relation plusieurs champs\n    def clean(self):\n        cleaned_data = super().clean()\n        titre = cleaned_data.get('titre')\n        slug = cleaned_data.get('slug')\n        if titre and slug and slug == titre:\n            raise forms.ValidationError(\"Le slug ne peut pas être strictement identique au titre.\")\n        return cleaned_data")
        )

        data["form_model"] = (
            mt("14. Surcharge des Méthodes de Validation Formulaires") +
            "Pourquoi : Permet d'injecter des règles de validation complexes métier (Vérification de doublons, nettoyage de balises HTML malveillantes) avant la persistance en base de données.\n" +
            "• clean_<champ>() : S'exécute en premier, renvoie la valeur nettoyée stockée dans `cleaned_data`.\n" +
            "• clean() : S'exécute en second, idéal pour comparer des champs dépendants (ex: validation et confirmation de mot de passe)."
        )

        data["form_tips"] = (
            mt("15. Gestion des Erreurs complexes") +
            "Description : Renvoyer des messages d'erreurs clairs via `raise forms.ValidationError()` directement interceptés par le dictionnaire d'erreurs du template frontend."
        )

        # =====================================================================
        # --- 5. TEMPLATES & FRONTEND ---
        # =====================================================================

        data["templates"] = (
            mt("16. Le Moteur de Templates Django") +
            "Description : Système d'affichage découplant l'interface de la logique."
        )

        data["tags"] = (
            mt("17. Liste Exhaustive des Balises (Tags) Django Built-in") +
            "Description : Instructions logiques interprétées côté serveur lors du rendu HTML.\n\n" +
            "• `{% url 'route' %}` : Résout de manière dynamique le pattern d'URL nommé.\n" +
            "• `{% static 'path' %}` : Génère l'URL absolue vers un asset statique configuré.\n" +
            "• `{% csrf_token %}` : Génère un input caché contenant le jeton de sécurité anti-CSRF.\n" +
            "• `{% extends 'base.html' %}` : Déclare le squelette HTML parent à hériter.\n" +
            "• `{% block nom %} ... {% endblock %}` : Zone d'injection de contenu dynamique.\n" +
            "• `{% if condition %} ... {% elif %} ... {% else %} ... {% endif %}` : Structure conditionnelle.\n" +
            "• `{% for item in liste %} ... {% empty %} ... {% endfor %}` : Boucle d'itération avec fallback adaptatif si la liste est vide.\n" +
            "• `{% include 'chemin/template.html' %}` : Inclut un fragment de template isolé.\n" +
            "• `{% with var=long_var.attr %} ... {% endwith %}` : Assigne une variable locale pour optimiser l'accès.\n" +
            "• `{% load static %}` : Charge un package de balises ou filtres personnalisés dans le scope courant."
        )

        data["template_logic"] = (
            mt("18. Logique Avancée & Filtres") +
            "Description : Traitement visuel direct des variables de contexte.\n\n" +
            cb("{% if user.is_authenticated %}\n    <p>Bienvenue {{ user.username|upper }}</p>\n{% endif %}")
        )

        data["filters"] = (
            mt("22. Liste Exhaustive des Filtres Django Intégrés") +
            "Description : Modificateurs de variables appliqués à l'aide d'un caractère pipe `|`.\n\n" +
            "• `{{ var|upper }}` : Transforme la chaîne en majuscules.\n" +
            "• `{{ var|lower }}` : Transforme la chaîne en minuscules.\n" +
            "• `{{ var|capfirst }}` : Capitalise la première lettre de la chaîne.\n" +
            "• `{{ var|truncatewords:20 }}` : Tronque une chaîne après X mots.\n" +
            "• `{{ var|truncatechars:50 }}` : Tronque une chaîne après X caractères.\n" +
            "• `{{ date_var|date:'d/m/Y H:i' }}` : Formate un objet datetime selon un pattern strict.\n" +
            "• `{{ var|default:'Valeur par défaut' }}` : Fallback si la variable est évaluée à False ou None.\n" +
            "• `{{ liste|length }}` : Retourne la taille de la collection.\n" +
            "• `{{ texte|safe }}` : Désactive l'auto-échappement HTML (Attention aux failles XSS).\n" +
            "• `{{ valeur|add:5 }}` : Ajoute un entier à une valeur numérique.\n" +
            "• `{{ valeur|slugify }}` : Convertit le texte en slug propre (minuscules, tirets, sans accents).\n" +
            "• `{{ liste|join:', ' }}` : Concatène une liste en une chaîne avec séparateur.\n" +
            "• `{{ dict|get_item:key }}` : Extrait une valeur dynamique depuis un dictionnaire (via template filter custom)."
        )

        data["static_media"] = (
            mt("19. Fichiers Statiques & Média") +
            "Configuration de Production (settings.py) :\n" +
            cb("STATIC_URL = '/static/'\nSTATIC_ROOT = BASE_DIR / 'staticfiles'\nMEDIA_URL = '/media/'\nMEDIA_ROOT = BASE_DIR / 'media'")
        )

        # =====================================================================
        # --- 6. ORM & BASE DE DONNÉES ---
        # =====================================================================

        data["orm"] = (
            mt("20. Maîtrise de l'ORM & Optimisations") +
            "Lookups Avancés d'interrogation et de requêtage de base de données :\n" +
            cb("Article.objects.filter(date_creation__year=2026) # Requête ciblée temporelle")
        )

        data["orm_methods"] = (
            mt("21. Méthodes CRUD Fondamentales") +
            "Méthodes de requêtage de l'ORM :\n" +
            "• `.filter()`, `.get()`, `.create()`, `.delete()`, `.bulk_create()`."
        )

        data["postgresql"] = (
            mt("23. Implémentation Rigoureuse de PostgreSQL") +
            "Description : Base de données relationnelle industrielle standard pour Django.\n\n" +
            st("Installation du Driver Natif") +
            cb("pip install psycopg2-binary") + "\n\n" +
            st("Configuration Enterprise (settings.py)") +
            cb("import os\nfrom pathlib import Path\n\nDATABASES = {\n    'default': {\n        'ENGINE': 'django.db.backends.postgresql',\n        'NAME': os.environ.get('DB_NAME', 'gykhamine_db'),\n        'USER': os.environ.get('DB_USER', 'postgres'),\n        'PASSWORD': os.environ.get('DB_PASSWORD', 'secure_pass'),\n        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),\n        'PORT': os.environ.get('DB_PORT', '5432'),\n        'CONN_MAX_AGE': 600, # Persistance des connexions pour optimiser les performances\n    }\n}")
        )

        data["sqlite"] = (
            mt("24. Configuration SQLite avec Optimisations") +
            "Description : Base de données embarquée légère, parfaire pour les tests ou environnements de développement.\n\n" +
            st("Configuration et Mode WAL (Write-Ahead Logging)") +
            cb("DATABASES = {\n    'default': {\n        'ENGINE': 'django.db.backends.sqlite3',\n        'NAME': BASE_DIR / 'db.sqlite3',\n    }\n}\n\n# Optimisation de la concurrence d'écriture (à exécuter via le shell ou à l'initialisation)\n# PRAGMA journal_mode=WAL;")
        )

        # =====================================================================
        # --- 7. SÉCURITÉ & AUTH ---
        # =====================================================================

        data["security"] = (
            mt("25. Durcissement de la Sécurité") +
            "Règles impératives : SSL, Gestion fine des CORS, Middleware de protection."
        )

        data["cookies"] = ( mt("26. Cookies & Sessions") + "Stockage : Gestion des cycles de vie sessions client/serveur." )
        data["encryption"] = ( mt("27. Chiffrement Cryptographique") + "Algorithmes : Pbkdf2/Argon2 pour les mots de passe." )

        # =====================================================================
        # --- 8. AVANCÉ & API ---
        # =====================================================================

        data["js_ajax"] = ( mt("28. JavaScript & AJAX") + "Asynchronisme : Communication asynchrone DOM backend." )

        data["browser_api"] = (
            mt("29. Interactions avec l'API Web du Navigateur") +
            "Description : Connexion directe de l'interface frontend aux capacités matérielles de l'hôte via JavaScript natif.\n\n" +
            st("Exemple d'Intégration Avancée (Géolocalisation & Notification)") +
            cb("const initGeolocAndNotify = () => {\n    if ('geolocation' in navigator) {\n        navigator.geolocation.getCurrentPosition(\n            (position) => {\n                const { latitude, longitude } = position.coords;\n                console.log(`Lat: ${latitude}, Lon: ${longitude}`);\n                \n                // Déclenchement de l'API de Notification du système\n                if (Notification.permission === 'granted') {\n                    new Notification('Position synchronisée !', { body: `Lat: ${latitude}` });\n                } else if (Notification.permission !== 'denied') {\n                    Notification.requestPermission().then(permission => {\n                        if (permission === 'granted') new Notification('Merci !');\n                    });\n                }\n            },\n            (error) => console.error(`Erreur de capture : ${error.message}`),\n            { enableHighAccuracy: true, timeout: 5000 }\n        );\n    }\n};")
        )

        data["api_drf"] = (
            mt("30. Construction d'API REST avec Django Rest Framework (DRF)") +
            "Description : Exposition de endpoints standardisés JSON, sécurisés par jetons d'accès.\n\n" +
            st("Implémentation de l'Écosystème REST") +
            cb("from rest_framework import serializers, viewsets, permissions\nfrom rest_framework_simplejwt.authentication import JWTAuthentication\nfrom .models import Article\n\n# 1. Sérialiseur : Conversion de l'ORM vers JSON complexes et inversement\nclass ArticleSerializer(serializers.ModelSerializer):\n    auteur_name = serializers.CharField(source='auteur.username', read_only=True)\n\n    class Meta:\n        model = Article\n        fields = ['id', 'titre', 'contenu', 'auteur_name', 'statut']\n\n# 2. ViewSet : Contrôleur automatique exposant les routes CRUD standard\nclass ArticleViewSet(viewsets.ModelViewSet):\n    queryset = Article.objects.filter(statut='publie')\n    serializer_class = ArticleSerializer\n    authentication_classes = [JWTAuthentication]\n    permission_classes = [permissions.IsAuthenticatedOrReadOnly]")
        )

        data["channels"] = (
            mt("31. Temps Réel Évolutif avec Django Channels & WebSockets") +
            "Description : Architecture asynchrone permettant de maintenir des connexions persistantes full-duplex temps réel.\n\n" +
            st("Feuille de Route d'Intégration (Roadmap)") +
            "1. Remplacer le serveur d'application synchrone WSGI par ASGI (Daphne / Uvicorn).\n" +
            "2. Configurer une couche de transport (Channel Layer) performante basée sur Redis.\n" +
            "3. Rédiger un système de routage de protocoles (`ProtocolTypeRouter`) dans `asgi.py`.\n" +
            "4. Implémenter des Consumers (l'équivalent asynchrone des vues) pour intercepter le trafic WebSocket.\n\n" +
            st("Code Source Asynchrone Pratique (consumers.py)") +
            cb("import json\nfrom channels.generic.websocket import AsyncWebsocketConsumer\n\nclass NotificationConsumer(AsyncWebsocketConsumer):\n    async def connect(self):\n        self.group_name = 'live_notifications'\n        # Rejoindre le groupe de diffusion de manière asynchrone\n        await self.channel_layer.group_add(self.group_name, self.channel_name)\n        await self.accept()\n\n    async def disconnect(self, close_code):\n        # Quitter le groupe lors de la déconnexion\n        await self.channel_layer.group_discard(self.group_name, self.channel_name)\n\n    async def receive(self, text_data):\n        data = json.loads(text_data)\n        message = data.get('message', '')\n        \n        # Diffuser le message à l'ensemble du groupe\n        await self.channel_layer.group_send(\n            self.group_name,\n            {\n                'type': 'send_notification',\n                'message': message\n            }\n        )\n\n    async def send_notification(self, event):\n        message = event['message']\n        # Envoi physique de la trame au client connecté en WebSocket\n        await self.send(text_data=json.dumps({'notification': message}))")
        )

        data["celery"] = (
            mt("32. Exécution de Tâches Asynchrones & Distribuées via Celery") +
            "Description : Déchargement des traitements lourds et asynchrones en arrière-plan.\n" +
            "Pourquoi : Garantir un temps de réponse instantané au client HTTP (inférieur à 100ms) et déléguer les calculs à des nœuds d'exécution (Workers).\n\n" +
            st("Feuille de Route d'Intégration (Roadmap)") +
            "1. Installer Celery et un broker de messages : `pip install celery redis`.\n" +
            "2. Instancier l'application Celery globale (`celery.py`) connectée à la configuration Django.\n" +
            "3. Configurer l'adresse du broker Redis dans les `settings.py`.\n" +
            "4. Déclarer des tâches isolées via le décorateur `@shared_task`.\n" +
            "5. Démarrer les processus serveurs parallèles : Le serveur Django d'un côté, le Worker Celery de l'autre.\n\n" +
            st("Code Source Opérationnel (tasks.py)") +
            cb("# celery.py (Configuration globale d'instance)\nimport os\nfrom celery import Celery\n\nos.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core_project.settings')\napp = Celery('core_project')\napp.config_from_object('django.conf:settings', namespace='CELERY')\napp.autodiscover_tasks()\n\n# ==================================================\n# tasks.py (Déclaration des tâches métiers)\nfrom celery import shared_task\nimport time\n\n@shared_task\ndef executer_traitement_lourd(patient_id, donnees_medicales):\n    \"\"\"Simule une analyse de données statistiques massives non bloquante\"\"\"\n    time.sleep(10) # Simulation d'un calcul complexe de 10 secondes\n    # Logique d'analyse prédictive ou de calcul de métriques ici...\n    return f\"Analyse terminée pour le patient {patient_id}\"") + "\n\n" +
            st("Appel non bloquant depuis une Vue") +
            cb("# Dans views.py\ndef declencher_calcul_view(request):\n    # L'appel via .delay() pousse la tâche dans Redis et rend la main immédiatement\n    executer_traitement_lourd.delay(patient_id=42, donnees_medicales={})\n    return JsonResponse({'status': 'Tâche envoyée en arrière-plan'})")
        )

        # =====================================================================
        # --- 9. DÉPLOIEMENT & PROD ---
        # =====================================================================

        data["nginx_gunicorn"] = ( mt("33. Nginx & Gunicorn") + "Stack : Reverse proxy Nginx couplé au serveur WSGI Gunicorn." )
        data["gunicorn_opts"] = ( mt("34. Optimisation Gunicorn") + "CMD : Gestion dynamique du nombre de workers et timeout." )
        data["production"] = ( mt("35. Checklist de Production") + "Checklist : Désactivation stricte du mode DEBUG, gestion des clés secrètes." )
        data["deploy"] = ( mt("36. Déploiement Gykhamine Studio") + "DevOps : Industrialisation et gestion automatisée de l'infrastructure." )
        data["tips"] = ( mt("37. Bonnes Pratiques") + "Performance : Optimisation des requêtes SQL et indexation physique." )        
        # Fill remaining keys with placeholder if missing
        for key in ["project_app", "manage", "fields", "field_opts", "model_methods", "views", "decorators", "view_cases", "responses", "forms", "form_model", "form_tips", "templates", "tags", "template_logic", "filters", "static_media", "orm", "orm_methods", "postgresql", "sqlite", "security", "cookies", "encryption", "js_ajax", "browser_api", "api_drf", "channels", "celery", "nginx_gunicorn", "gunicorn_opts", "production", "deploy", "tips"]:
            if key not in data:
                data[key] = fmt_title(key.upper()) + "Documentation détaillée à venir dans cette section."
                
        return data



CSS = """
/* ── Base & Fond Noir Complet (Même en mode sudo) ──────────────────── */
window, dialog, popover, scrolledwindow, viewport, button, entry, textview, listbox, treeview, headerbar, box, stack, notebook, .background, .csd, preferencesdialog, preferencespage, preferencesgroup, actionrow, entryrow, switchrow, comborow, toastoverlay {
background-color: #000000 !important;
color: #4aa3df !important;
}
/* ── Coins Arrondis pour tous les Popups/Dialogues ─────────────────── */
dialog, .rounded-dialog, window.dialog, popover {
border-radius: 12px !important;
}
/* ── Panel titles ────────────────────────────────────────────────────── */
.panel-title, .control-section-title { font-size: 11px; font-weight: bold; color: #4aa3df; text-transform: uppercase; min-width: 0; }
/* ── File list ───────────────────────────────────────────────────────── */
.file-item { font-size: 11px; font-family: monospace; min-width: 0; color: #4aa3df; }
.file-category { font-size: 10px; color: #4aa3df; min-width: 0; }
.file-category:hover { color: #6bcfff; }
.block-name { font-size: 11px; font-family: monospace; min-width: 0; color: #4aa3df; }
/* ── Block cards ─────────────────────────────────────────────────────── */
.block-card { background-color: #111111 !important; border-radius: 6px; border: 1px solid #2a2a2a; margin-bottom: 4px; min-width: 0; }
.block-card:hover { border-color: #444; }
/* ── Type badges ─────────────────────────────────────────────────────── */
.block-badge { font-size: 9px; font-weight: bold; border-radius: 4px; padding: 1px 4px; min-width: 0; }
.badge-import, .badge-style, .badge-style_rule { background-color: #3498db; color: #fff; }
.badge-class { background-color: #3498db; color: #fff; }
.badge-function, .badge-script_block { background-color: #9b59b6; color: #fff; }
.badge-template, .badge-template_part, .badge-django_block { background-color: #e67e22; color: #fff; }
.badge-script, .badge-c_block { background-color: #f1c40f; color: #000; }
.badge-separator, .badge-other { background-color: #333; color: #aaa; }
/* ── Block action buttons ────────────────────────────────────────────── */
.block-action-btn { font-size: 10px; background: transparent; border: 1px solid #2a2a2a; border-radius: 4px; padding: 2px 5px; min-width: 0; color: #4aa3df; }
.block-action-btn:hover { background-color: #1e1e1e; }
/* ── Code editor ─────────────────────────────────────────────────────── */
.code-editor { font-family: monospace; font-size: 9px; background-color: #050505 !important; color: #4aa3df; min-width: 0; }
/* ── Save buttons ────────────────────────────────────────────────────── */
.save-btn, .save-file-btn { background-color: #1a4a2a; color: #2ecc71; border: 1px solid #2ecc71; border-radius: 4px; min-width: 0; }
.cancel-btn { background-color: #2a1a1a; color: #e74c3c; border: 1px solid #e74c3c; border-radius: 4px; min-width: 0; }
/* ── Control panel buttons ───────────────────────────────────────────── */
.ctrl-btn, .ctrl-btn-small, .toolbar-btn { background-color: #1a1a2a; border: 1px solid #333; border-radius: 4px; font-size: 10px; padding: 3px 6px; min-width: 0; color: #4aa3df; }
.ctrl-btn-start { background-color: #0a2a0a; color: #2ecc71; border-color: #2ecc71; border-radius: 4px; font-size: 10px; padding: 3px 6px; min-width: 0; }
.ctrl-btn-stop { background-color: #2a0a0a; color: #e74c3c; border-color: #e74c3c; border-radius: 4px; font-size: 10px; padding: 3px 6px; min-width: 0; }
.ctrl-btn-warn { background-color: #2a1f0a; color: #f39c12; border-color: #f39c12; border-radius: 4px; font-size: 10px; padding: 3px 6px; min-width: 0; }
/* ── Status indicators ───────────────────────────────────────────────── */
.status-dot-off { color: #333; }
.status-dot-on  { color: #2ecc71; }
/* ── Terminal Panel ──────────────────────────────────────────────────── */
.terminal-panel { background-color: #000000 !important; border-top: 1px solid #3c3c3c; }
.terminal-title { font-size: 11px; font-weight: bold; color: #4aa3df; text-transform: uppercase; }
.log-view { font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 12px; background-color: transparent !important; color: #4aa3df; padding: 8px; min-width: 0; }
.terminal-prompt { color: #2ecc71; font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace; font-weight: bold; font-size: 12px; margin-right: 4px; }
.terminal-input { background-color: #0d0d0d !important; color: #4aa3df; border: 1px solid #3c3c3c; border-radius: 4px; font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 12px; padding: 4px 8px; }
.terminal-input:focus { border-color: #007acc; outline: none; }
/* ── Editor toolbar ──────────────────────────────────────────────────── */
.toolbar-label { font-size: 11px; color: #4aa3df; min-width: 0; }
.block-count-badge { font-size: 10px; font-weight: bold; background-color: #1a1a2a; color: #61afef; border-radius: 4px; padding: 1px 6px; min-width: 0; }
.editor-file-label { font-size: 12px; font-weight: bold; min-width: 0; color: #4aa3df; }
/* ── Bottom accent bar of cards ──────────────────────────────────────── */
.block-accent-bar { min-height: 2px; min-width: 0; }
.accent-function, .accent-script_block { background-color: #9b59b6; }
.accent-class { background-color: #3498db; }
.accent-import, .accent-style { background-color: #2980b9; }
.accent-django_block { background-color: #e67e22; }
.accent-script, .accent-c_block { background-color: #f1c40f; }
.accent-separator { background-color: #333; }
.accent-other, .accent-template_part { background-color: #222; }
/* ── Tabs System ─────────────────────────────────────────────────────── */
.tab-bar { background-color: #0a0a0a !important; border-bottom: 1px solid #333; min-height: 35px; }
.tab-button { background-color: #151515; border-radius: 4px 4px 0 0; padding: 4px 8px; cursor: pointer; border: 1px solid #333; border-bottom: none; }
.tab-button:hover { background-color: #1a1a1a; }
.tab-button.active-tab { background-color: #000000 !important; border-top: 2px solid #007acc; }
.tab-button label { color: #4aa3df; font-size: 12px; }
.tab-button button { min-width: 20px; min-height: 20px; padding: 0; }
/* ── Light theme override (si activé manuellement) ───────────────────── */
.theme-light window, .theme-light dialog, .theme-light popover { background-color: #f5f5f5; color: #222; }
.theme-light .block-card { background-color: #ffffff; border-color: #ddd; }
.theme-light .code-editor { background-color: #fafafa; color: #222; }
.theme-light .log-view { background-color: #f0f0f0; color: #1a6a1a; }
.theme-light .ctrl-btn, .theme-light .toolbar-btn { background-color: #e8e8f0; border-color: #ccc; color: #222; }
.theme-light .terminal-panel { background-color: #ffffff; border-color: #ccc; }
.theme-light .terminal-input { background-color: #f5f5f5; color: #222; border-color: #ccc; }
.theme-light .terminal-prompt { color: #2ecc71; }
.theme-light .tab-bar { background-color: #e0e0e0; border-color: #ccc; }
.theme-light .tab-button { background-color: #f0f0f0; border-color: #ccc; }
.theme-light .tab-button label { color: #333; }
.theme-light .tab-button.active-tab { background-color: #f5f5f5; border-top-color: #007acc; }
/* Bouton IA */
.btn-ai {
background-color: #2a1a3a;
color: #bb86fc;
border-color: #bb86fc;
}
.btn-ai:hover {
background-color: #3a2a4a;
}
/* WhatsApp Style Button */
.whatsapp-btn {
background-color: #25D366;
color: white;
border-radius: 50%;
min-width: 40px;
min-height: 40px;
padding: 0;
border: none;
box-shadow: 0 2px 5px rgba(0,0,0,0.3);
}
.whatsapp-btn:hover {
background-color: #128C7E;
}
.whatsapp-btn image {
color: white;
}
/* ── Nouveaux Tags pour le Constructeur de Commandes ───────────────── */
.option-tag, .arg-tag {
background-color: #1a4a2a;
color: #2ecc71;
border: 1px solid #2ecc71;
border-radius: 4px;
padding: 2px 6px;
font-size: 11px;
font-family: monospace;
}
.options-container, .args-container {
background-color: #0a0a0a;
border: 1px solid #333;
border-radius: 4px;
padding: 4px;
min-height: 30px;
}

/* Indentation des blocs enfants */
.child-block {
    border-left: 2px solid #333;
    margin-left: 10px;
}
.block-card {
    transition: margin-left 0.2s ease;
}
"""

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
        except: pass

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
            
