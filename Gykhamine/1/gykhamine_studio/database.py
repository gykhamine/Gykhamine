"""Module généré automatiquement depuis gy.py"""
import sqlite3, json, hashlib, subprocess
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

# --- Invalidation du cache (rejet d'une réponse IA non validée) ---
def delete_cached_command(intent: str):
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        con.execute("DELETE FROM ai_cmd_cache WHERE intent_hash = ?", (_get_intent_hash(intent),))
        con.commit(); con.close()
    except Exception as e: global_log(f"❌ Erreur suppression cache cmd: {e}")

def delete_cached_block(intent: str):
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        con.execute("DELETE FROM ai_block_cache WHERE intent_hash = ?", (_get_intent_hash(intent),))
        con.commit(); con.close()
    except Exception as e: global_log(f"❌ Erreur suppression cache bloc: {e}")

def delete_cached_process(intent: str):
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        con.execute("DELETE FROM ai_process_cache WHERE intent_hash = ?", (_get_intent_hash(intent),))
        con.commit(); con.close()
    except Exception as e: global_log(f"❌ Erreur suppression cache process: {e}")


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
#  DB MANAGER — Introspection et CRUD génériques pour la base interne
# ═══════════════════════════════════════════════════════════════════════
# Utilisé par l'interface graphique de gestion de la base (DBManagerDialog)
# pour visualiser, ajouter, modifier et supprimer le contenu de n'importe
# quelle table sans avoir à coder une UI spécifique par table.

def list_db_tables(config: dict) -> list:
    """Retourne la liste des tables utilisateur de la base (hors tables
    internes SQLite)."""
    db_path = _get_db_path(config.get("db_path"))
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        rows = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        con.close()
        return [r[0] for r in rows]
    except Exception as e:
        global_log(f"❌ Erreur liste tables DB: {e}")
        return []

def get_table_schema(config: dict, table: str) -> list:
    """Retourne [(nom_colonne, type, is_pk), ...] pour une table donnée."""
    db_path = _get_db_path(config.get("db_path"))
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        rows = con.execute(f"PRAGMA table_info({_quote_ident(table)})").fetchall()
        con.close()
        # PRAGMA table_info -> (cid, name, type, notnull, dflt_value, pk)
        return [(r[1], r[2], bool(r[5])) for r in rows]
    except Exception as e:
        global_log(f"❌ Erreur schéma table {table}: {e}")
        return []

def _quote_ident(name: str) -> str:
    """Échappe un identifiant SQLite (nom de table ou de colonne) avec des
    guillemets doubles, la syntaxe correcte pour les identifiants en SQL.
    ATTENTION : des guillemets simples ('nom') désignent un littéral de
    chaîne en SQLite, pas un identifiant — les utiliser autour d'un nom de
    colonne dans une clause WHERE/SET fait que la comparaison porte sur le
    texte constant au lieu de la colonne, ce qui provoque un échec
    silencieux (aucune erreur, mais aucune ligne mise à jour/supprimée).
    C'était la cause du bug empêchant modification/suppression dans le
    DB Manager. Un guillemet double interne est doublé pour l'échapper."""
    return '"' + name.replace('"', '""') + '"'

def get_table_rows(config: dict, table: str, limit: int = 500) -> list:
    """Retourne les lignes d'une table sous forme de liste de dicts
    {colonne: valeur}, limitée à `limit` lignes (protection contre une table
    de cache très volumineuse)."""
    db_path = _get_db_path(config.get("db_path"))
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        con.row_factory = sqlite3.Row
        rows = con.execute(f"SELECT * FROM {_quote_ident(table)} LIMIT ?", (limit,)).fetchall()
        con.close()
        return [dict(r) for r in rows]
    except Exception as e:
        global_log(f"❌ Erreur lecture table {table}: {e}")
        return []

def get_table_primary_key(config: dict, table: str) -> str:
    """Retourne le nom de la colonne clé primaire d'une table, ou None si
    aucune n'est définie (cas de `config` où `key` est PK)."""
    for name, _type, is_pk in get_table_schema(config, table):
        if is_pk:
            return name
    return None

def insert_table_row(config: dict, table: str, values: dict) -> bool:
    """Insère une nouvelle ligne dans la table donnée."""
    db_path = _get_db_path(config.get("db_path"))
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        cols = ", ".join(_quote_ident(k) for k in values.keys())
        placeholders = ", ".join("?" for _ in values)
        con.execute(f"INSERT INTO {_quote_ident(table)} ({cols}) VALUES ({placeholders})", list(values.values()))
        con.commit(); con.close()
        return True
    except Exception as e:
        global_log(f"❌ Erreur insertion dans {table}: {e}")
        return False

def update_table_row(config: dict, table: str, pk_column: str, pk_value, values: dict) -> bool:
    """Met à jour une ligne existante, identifiée par sa clé primaire."""
    db_path = _get_db_path(config.get("db_path"))
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        set_clause = ", ".join(f"{_quote_ident(k)} = ?" for k in values.keys())
        params = list(values.values()) + [pk_value]
        cur = con.execute(f"UPDATE {_quote_ident(table)} SET {set_clause} WHERE {_quote_ident(pk_column)} = ?", params)
        con.commit()
        updated = cur.rowcount
        con.close()
        if updated == 0:
            global_log(f"⚠️ Mise à jour {table}: aucune ligne trouvée pour {pk_column}={pk_value!r}")
            return False
        return True
    except Exception as e:
        global_log(f"❌ Erreur mise à jour {table}: {e}")
        return False

def delete_table_row(config: dict, table: str, pk_column: str, pk_value) -> bool:
    """Supprime une ligne identifiée par sa clé primaire."""
    db_path = _get_db_path(config.get("db_path"))
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        cur = con.execute(f"DELETE FROM {_quote_ident(table)} WHERE {_quote_ident(pk_column)} = ?", (pk_value,))
        con.commit()
        deleted = cur.rowcount
        con.close()
        if deleted == 0:
            global_log(f"⚠️ Suppression {table}: aucune ligne trouvée pour {pk_column}={pk_value!r}")
            return False
        return True
    except Exception as e:
        global_log(f"❌ Erreur suppression {table}: {e}")
        return False

def truncate_table(config: dict, table: str) -> bool:
    """Vide entièrement une table (remise à 0), sans supprimer la table
    elle-même ni son schéma. Réinitialise aussi le compteur AUTOINCREMENT
    si la table en possède un (sqlite_sequence), pour que les prochains ID
    repartent de 1 plutôt que de continuer après le dernier ID jamais
    utilisé."""
    db_path = _get_db_path(config.get("db_path"))
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        con.execute(f"DELETE FROM {_quote_ident(table)}")
        # Réinitialise le compteur auto-incrémenté s'il existe pour cette table.
        # La table sqlite_sequence n'existe elle-même que si au moins une table
        # AUTOINCREMENT a été créée dans la base — son absence ne doit pas faire
        # échouer la réinitialisation de la table elle-même.
        try:
            con.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
        except sqlite3.OperationalError:
            pass
        con.commit()
        con.close()
        global_log(f"🗑 Table « {table} » réinitialisée (toutes les lignes supprimées).")
        return True
    except Exception as e:
        global_log(f"❌ Erreur réinitialisation table {table}: {e}")
        return False

# ═══════════════════════════════════════════════════════════════════════
