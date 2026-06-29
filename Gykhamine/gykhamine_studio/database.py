"""Module généré automatiquement depuis gy.py"""
import sqlite3, json, hashlib
from pathlib import Path
from datetime import datetime
from .config import DEFAULT_CONFIG, global_log
import socket

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
    except Exception as e:
        global_log(f"⚠️ Erreur dans gy.py: {type(e).__name__} - {e}")
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
    except Exception as e:
        global_log(f"⚠️ Erreur dans gy.py: {type(e).__name__} - {e}")
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
    except Exception as e:
        global_log(f"⚠️ Erreur dans gy.py: {type(e).__name__} - {e}")
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
    except Exception as e:
        global_log(f"⚠️ Erreur dans gy.py: {type(e).__name__} - {e}")
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
    except Exception as e:
        global_log(f"⚠️ Erreur dans gy.py: {type(e).__name__} - {e}")
    return False

# ═══════════════════════════════════════════════════════════════════════
