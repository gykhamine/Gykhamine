"""Module de gestion SQLite — Base de données, caches IA, prompts et logs"""
import sqlite3
import json
import hashlib
import subprocess
import socket
from pathlib import Path
from datetime import datetime
from .config import DEFAULT_CONFIG, global_log

# ═══════════════════════════════════════════════════════════════════════
#  SQLITE ENGINE — CONFIG + SMART MEMORY + LOGS
# ═══════════════════════════════════════════════════════════════════════

# Rôles IA par défaut : source unique pour amorcer (seed) la table ai_prompts
DEFAULT_AI_PROMPTS = {
    "Élaborateur": "Tu es un expert algorithmique de processus métier. Tu sais décomposer un problème complexe en tâches techniques précises, ordonnées et réalisables. Réponds UNIQUEMENT avec un tableau JSON d'étapes : [{'etape': 1, 'tache': '...', 'fichier': '...', 'details': '...'}].",
    "Prof de programmation": "Tu es un professeur de programmation pédagogue et expert. Tu expliques les concepts clairement. Réponds UNIQUEMENT avec un objet JSON : {'explication': '...', 'exemple_code': '...', 'bonnes_pratiques': ['...']}.",
    "Expert en Django": "Tu es un architecte logiciel Django Senior. Tu privilégies les bonnes pratiques et la sécurité. Réponds UNIQUEMENT avec un objet JSON : {'analyse': '...', 'fichiers_a_modifier': ['...'], 'code_propose': '...'}.",
    "Traducteur": "Tu es un traducteur technique expert. Tu traduis les demandes avec une précision absolue. Réponds UNIQUEMENT avec un objet JSON : {'original': '...', 'traduction': '...'}.",
    "Expert Linux": "Tu es un administrateur système Linux et DevOps expert. Tu fournis des commandes shell optimisées. Réponds UNIQUEMENT avec un objet JSON : {'commande': '...', 'explication': '...', 'avertissements': '...'}.",
    "Expert en astuce en informatique": "Tu es un guru de l'informatique. Tu donnes des astuces et solutions ingénieuses. Réponds UNIQUEMENT avec un objet JSON : {'astuce': '...', 'contexte_utilisation': '...', 'gain_estime': '...'}.",
    "Bloc: function": "Tu es un expert Python Senior spécialisé en optimisation et clean code.",
    "Bloc: class": "Tu es un architecte logiciel Python expert en POO.",
    "Bloc: django_model": "Tu es un expert Django ORM. Tu maîtrises les relations et validations.",
    "Bloc: django_view": "Tu es un expert Django Views. Tu privilégies les Class-Based Views ou fonctions optimisées.",
    "Bloc: django_form": "Tu es un expert Django Forms.",
    "Bloc: django_settings": "Tu es un expert configuration Django sécurisée.",
    "Bloc: django_url": "Tu es un expert Django URL routing.",
    "Bloc: template": "Tu es un expert Django Templates (Jinja2).",
    "Bloc: javascript": "Tu es un développeur JavaScript moderne (ES6+).",
    "Bloc: c_block": "Tu es un expert C/C++ système.",
    "Bloc: shell": "Tu es un expert Bash/Linux.",
    "Bloc: css": "Tu es un expert CSS moderne.",
    "Bloc: business_process": "Tu es un expert algorithmique de processus métier Django. Tu sais décomposer un problème complexe en tâches techniques précises et ordonnées.",
    "Bloc: other": "Tu es un assistant de codage polyvalent.",
    "Système: génération de code": "Tu es un moteur de génération de code strict. Tu ne parles pas, tu codes.",
}

def _get_db_path(cfg_override: str = None) -> Path:
    path_str = cfg_override if cfg_override else DEFAULT_CONFIG["db_path"]
    return Path(path_str)

def _ensure_column(con: sqlite3.Connection, table: str, column: str, definition: str):
    """Ajoute une colonne à une table existante si elle n'y est pas déjà (migration douce)."""
    try:
        rows = con.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {r[1] for r in rows}
        if column not in existing:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    except Exception as e:
        global_log(f"⚠️ Migration colonne {table}.{column} échouée: {e}")

def _init_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    cur.execute("CREATE TABLE IF NOT EXISTS recent_projects (id INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT UNIQUE NOT NULL, opened_at TEXT NOT NULL)")
    cur.execute("CREATE TABLE IF NOT EXISTS memory (id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT NOT NULL, file_path TEXT NOT NULL, block_name TEXT, action TEXT, ts TEXT NOT NULL, UNIQUE(project, file_path, block_name))")
    
    # Cache Commandes Shell
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_cmd_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intent_hash TEXT UNIQUE NOT NULL,
            command TEXT NOT NULL,
            is_process INTEGER DEFAULT 0,
            validated INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    _ensure_column(con, "ai_cmd_cache", "validated", "INTEGER DEFAULT 0")

    # Cache Blocs de Code
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_block_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intent_hash TEXT UNIQUE NOT NULL,
            content TEXT NOT NULL,
            block_type TEXT DEFAULT 'code',
            validated INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    _ensure_column(con, "ai_block_cache", "validated", "INTEGER DEFAULT 0")

    # Cache Processus & JSON (Élaborateur)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_process_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intent_hash TEXT UNIQUE NOT NULL,
            json_content TEXT NOT NULL,
            role_type TEXT DEFAULT 'general',
            validated INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    _ensure_column(con, "ai_process_cache", "validated", "INTEGER DEFAULT 0")

    # Table Prompts IA
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'custom',
            is_default INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Seed des prompts par défaut
    now = datetime.now().isoformat()
    for name, content in DEFAULT_AI_PROMPTS.items():
        cur.execute(
            "INSERT OR IGNORE INTO ai_prompts (name, content, category, is_default, created_at, updated_at) VALUES (?, ?, 'default', 1, ?, ?)",
            (name, content, now, now)
        )

    con.commit()
    con.close()

# ═══════════════════════════════════════════════════════════════════════
#  FONCTIONS DE CONFIGURATION & MÉMOIRE PROJET
# ═══════════════════════════════════════════════════════════════════════

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
        global_log(f"⚠️ Erreur chargement config: {type(e).__name__} - {e}")
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

# ═══════════════════════════════════════════════════════════════════════
#  CACHES IA (COMMANDES, BLOCS, PROCESSUS) & VALIDATION
# ═══════════════════════════════════════════════════════════════════════

def _get_intent_hash(intent: str) -> str:
    return hashlib.md5(intent.strip().lower().encode('utf-8')).hexdigest()

def get_cached_command(intent: str) -> dict:
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        row = con.execute("SELECT command, is_process FROM ai_cmd_cache WHERE intent_hash = ?", (_get_intent_hash(intent),)).fetchone()
        con.close()
        if row: return {"command": row[0], "is_process": bool(row[1])}
    except Exception as e:
        global_log(f"⚠️ Erreur cache cmd: {type(e).__name__} - {e}")
    return None

def save_command_to_cache(intent: str, command: str, is_process: bool = False):
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        con.execute("INSERT OR REPLACE INTO ai_cmd_cache (intent_hash, command, is_process, created_at) VALUES (?, ?, ?, ?)", 
                    (_get_intent_hash(intent), command, int(is_process), datetime.now().isoformat()))
        con.commit(); con.close()
    except Exception as e: global_log(f"❌ Erreur sauvegarde cache cmd: {e}")

def get_cached_block(intent: str) -> dict:
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        row = con.execute("SELECT content, block_type FROM ai_block_cache WHERE intent_hash = ?", (_get_intent_hash(intent),)).fetchone()
        con.close()
        if row: return {"content": row[0], "block_type": row[1]}
    except Exception as e:
        global_log(f"⚠️ Erreur cache block: {type(e).__name__} - {e}")
    return None

def save_block_to_cache(intent: str, content: str, block_type: str = 'code'):
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        con.execute("INSERT OR REPLACE INTO ai_block_cache (intent_hash, content, block_type, created_at) VALUES (?, ?, ?, ?)", 
                    (_get_intent_hash(intent), content, block_type, datetime.now().isoformat()))
        con.commit(); con.close()
    except Exception as e: global_log(f"❌ Erreur sauvegarde cache block: {e}")

def get_cached_process(intent: str) -> dict:
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        row = con.execute("SELECT json_content, role_type FROM ai_process_cache WHERE intent_hash = ?", (_get_intent_hash(intent),)).fetchone()
        con.close()
        if row: return {"json_content": row[0], "role_type": row[1]}
    except Exception as e:
        global_log(f"⚠️ Erreur cache process: {type(e).__name__} - {e}")
    return None

def save_process_to_cache(intent: str, json_content: str, role_type: str = 'general'):
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        con.execute("INSERT OR REPLACE INTO ai_process_cache (intent_hash, json_content, role_type, created_at) VALUES (?, ?, ?, ?)", 
                    (_get_intent_hash(intent), json_content, role_type, datetime.now().isoformat()))
        con.commit(); con.close()
    except Exception as e: global_log(f"❌ Erreur sauvegarde cache process: {e}")

_VALIDATION_TABLES = {
    "cmd":     ("ai_cmd_cache",    "command"),
    "block":   ("ai_block_cache",  "content"),
    "process": ("ai_process_cache","json_content"),
}

def is_cache_validated(intent: str, cache_type: str) -> bool:
    if cache_type not in _VALIDATION_TABLES:
        return False
    table, _ = _VALIDATION_TABLES[cache_type]
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        cols = {r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()}
        if "validated" not in cols:
            con.close()
            return False
        row = con.execute(f"SELECT validated FROM {table} WHERE intent_hash = ?", (_get_intent_hash(intent),)).fetchone()
        con.close()
        return bool(row and row[0])
    except Exception as e:
        global_log(f"⚠️ Erreur lecture validated ({cache_type}): {e}")
        return False

def mark_cache_validated(intent: str, cache_type: str, validated: bool = True) -> bool:
    if cache_type not in _VALIDATION_TABLES:
        return False
    table, _ = _VALIDATION_TABLES[cache_type]
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        cols = {r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()}
        if "validated" not in cols:
            con.close()
            return False
        cur = con.execute(f"UPDATE {table} SET validated = ? WHERE intent_hash = ?", (1 if validated else 0, _get_intent_hash(intent)))
        con.commit()
        updated = cur.rowcount
        con.close()
        return updated > 0
    except Exception as e:
        global_log(f"❌ Erreur mark validated ({cache_type}): {e}")
        return False

# ═══════════════════════════════════════════════════════════════════════
#  RÉSEAU & UTILITAIRES SYSTÈME
# ═══════════════════════════════════════════════════════════════════════

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
            for pid in result.stdout.strip().split('\n'):
                subprocess.run(f"kill -9 {pid}", shell=True)
            return True
    except Exception as e:
        global_log(f"⚠️ Erreur kill_process_on_port: {type(e).__name__} - {e}")
    return False

# ═══════════════════════════════════════════════════════════════════════
#  GESTION DES PROMPTS IA (CRUD)
# ═══════════════════════════════════════════════════════════════════════

def get_all_prompts() -> list:
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        rows = con.execute("SELECT id, name, content, category, is_default, created_at, updated_at FROM ai_prompts ORDER BY is_default DESC, name COLLATE NOCASE ASC").fetchall()
        con.close()
        return [
            {"id": r[0], "name": r[1], "content": r[2], "category": r[3], "is_default": bool(r[4]), "created_at": r[5], "updated_at": r[6]}
            for r in rows
        ]
    except Exception as e:
        global_log(f"⚠️ Erreur lecture ai_prompts: {e}")
        return []

def get_prompt(name: str) -> dict:
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        row = con.execute("SELECT name, content, category, is_default FROM ai_prompts WHERE name = ?", (name,)).fetchone()
        con.close()
        if row:
            return {"name": row[0], "content": row[1], "category": row[2], "is_default": bool(row[3])}
    except Exception as e:
        global_log(f"⚠️ Erreur lecture prompt '{name}': {e}")
    return None

def save_prompt(name: str, content: str, category: str = "custom") -> bool:
    db_path = _get_db_path()
    _init_db(db_path)
    now = datetime.now().isoformat()
    try:
        con = sqlite3.connect(str(db_path))
        existing = con.execute("SELECT is_default FROM ai_prompts WHERE name = ?", (name,)).fetchone()
        if existing:
            con.execute("UPDATE ai_prompts SET content = ?, updated_at = ? WHERE name = ?", (content, now, name))
        else:
            con.execute("INSERT INTO ai_prompts (name, content, category, is_default, created_at, updated_at) VALUES (?, ?, ?, 0, ?, ?)", (name, content, category, now, now))
        con.commit(); con.close()
        return True
    except Exception as e:
        global_log(f"❌ Erreur sauvegarde prompt '{name}': {e}")
        return False

def delete_prompt(name: str) -> bool:
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        row = con.execute("SELECT is_default FROM ai_prompts WHERE name = ?", (name,)).fetchone()
        if row and row[0]:
            con.close()
            return False
        con.execute("DELETE FROM ai_prompts WHERE name = ?", (name,))
        con.commit(); con.close()
        return True
    except Exception as e:
        global_log(f"❌ Erreur suppression prompt '{name}': {e}")
        return False

# ═══════════════════════════════════════════════════════════════════════
#  ADMINISTRATION DU CACHE IA (GESTION / PURGE)
# ═══════════════════════════════════════════════════════════════════════

AI_CACHE_TABLES = {
    "ai_cmd_cache": {"label": "🐚 Commandes shell", "content_col": "command"},
    "ai_block_cache": {"label": "🧩 Blocs de code", "content_col": "content"},
    "ai_process_cache": {"label": "📐 Processus (Élaborateur)", "content_col": "json_content"},
}

def get_cache_stats() -> dict:
    db_path = _get_db_path()
    _init_db(db_path)
    stats = {}
    try:
        con = sqlite3.connect(str(db_path))
        for table in AI_CACHE_TABLES:
            try: stats[table] = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except Exception: stats[table] = 0
        con.close()
    except Exception as e:
        global_log(f"⚠️ Erreur lecture stats cache IA: {e}")
    return stats

def get_cache_entries(table: str, limit: int = 100) -> list:
    if table not in AI_CACHE_TABLES: return []
    db_path = _get_db_path()
    _init_db(db_path)
    content_col = AI_CACHE_TABLES[table]["content_col"]
    try:
        con = sqlite3.connect(str(db_path))
        rows = con.execute(f"SELECT intent_hash, {content_col}, created_at FROM {table} ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        con.close()
        return [{"intent_hash": r[0], "content": r[1], "created_at": r[2]} for r in rows]
    except Exception as e:
        global_log(f"⚠️ Erreur lecture entrées cache '{table}': {e}")
        return []

def clear_cache_table(table: str) -> bool:
    if table not in AI_CACHE_TABLES: return False
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        con.execute(f"DELETE FROM {table}")
        con.commit(); con.close()
        return True
    except Exception as e:
        global_log(f"❌ Erreur vidage cache '{table}': {e}")
        return False

def delete_cache_entry(table: str, intent_hash: str) -> bool:
    if table not in AI_CACHE_TABLES: return False
    db_path = _get_db_path()
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        con.execute(f"DELETE FROM {table} WHERE intent_hash = ?", (intent_hash,))
        con.commit(); con.close()
        return True
    except Exception as e:
        global_log(f"❌ Erreur suppression entrée cache '{table}': {e}")
        return False

def update_cache_entry(table: str, intent_hash: str, new_content: str) -> bool:
    if table not in AI_CACHE_TABLES: return False
    db_path = _get_db_path()
    _init_db(db_path)
    content_col = AI_CACHE_TABLES[table]["content_col"]
    try:
        con = sqlite3.connect(str(db_path))
        con.execute(f"UPDATE {table} SET {content_col} = ? WHERE intent_hash = ?", (new_content, intent_hash))
        con.commit(); con.close()
        return True
    except Exception as e:
        global_log(f"❌ Erreur modification entrée cache '{table}': {e}")
        return False

def clear_all_ai_cache() -> bool:
    return all(clear_cache_table(t) for t in AI_CACHE_TABLES)

# ═══════════════════════════════════════════════════════════════════════
#  GESTIONNAIRE DE BASE DE DONNÉES (PROJETS, MÉMOIRE, LOGS)
# ═══════════════════════════════════════════════════════════════════════

def get_recent_projects_full(config: dict) -> list:
    db_path = _get_db_path(config.get("db_path"))
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        rows = con.execute("SELECT id, path, opened_at FROM recent_projects ORDER BY opened_at DESC").fetchall()
        con.close()
        return [{"id": r[0], "path": r[1], "opened_at": r[2], "exists": Path(r[1]).exists()} for r in rows]
    except Exception as e:
        global_log(f"⚠️ Erreur lecture recent_projects: {e}")
        return []

def delete_recent_project(config: dict, project_id: int) -> bool:
    db_path = _get_db_path(config.get("db_path"))
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        con.execute("DELETE FROM recent_projects WHERE id = ?", (project_id,))
        con.commit(); con.close()
        return True
    except Exception as e:
        global_log(f"❌ Erreur suppression projet récent: {e}")
        return False

def clear_recent_projects(config: dict) -> bool:
    db_path = _get_db_path(config.get("db_path"))
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        con.execute("DELETE FROM recent_projects")
        con.commit(); con.close()
        return True
    except Exception as e:
        global_log(f"❌ Erreur vidage projets récents: {e}")
        return False

def get_memory_entries(config: dict, limit: int = 200) -> list:
    db_path = _get_db_path(config.get("db_path"))
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        rows = con.execute("SELECT id, project, file_path, block_name, action, ts FROM memory ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
        con.close()
        return [{"id": r[0], "project": r[1], "file_path": r[2], "block_name": r[3], "action": r[4], "ts": r[5]} for r in rows]
    except Exception as e:
        global_log(f"⚠️ Erreur lecture memory: {e}")
        return []

def get_memory_count(config: dict) -> int:
    db_path = _get_db_path(config.get("db_path"))
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        count = con.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
        con.close()
        return count
    except Exception:
        return 0

def delete_memory_entry(config: dict, entry_id: int) -> bool:
    db_path = _get_db_path(config.get("db_path"))
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        con.execute("DELETE FROM memory WHERE id = ?", (entry_id,))
        con.commit(); con.close()
        return True
    except Exception as e:
        global_log(f"❌ Erreur suppression entrée mémoire: {e}")
        return False

def clear_memory(config: dict, project: str = None) -> bool:
    db_path = _get_db_path(config.get("db_path"))
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        if project: con.execute("DELETE FROM memory WHERE project = ?", (project,))
        else: con.execute("DELETE FROM memory")
        con.commit(); con.close()
        return True
    except Exception as e:
        global_log(f"❌ Erreur vidage mémoire: {e}")
        return False

def get_config_entries(config: dict) -> list:
    db_path = _get_db_path(config.get("db_path"))
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        rows = con.execute("SELECT key, value FROM config ORDER BY key COLLATE NOCASE ASC").fetchall()
        con.close()
        return [{"key": r[0], "value": r[1]} for r in rows]
    except Exception as e:
        global_log(f"⚠️ Erreur lecture config: {e}")
        return []

def delete_config_entry(config: dict, key: str) -> bool:
    db_path = _get_db_path(config.get("db_path"))
    _init_db(db_path)
    try:
        con = sqlite3.connect(str(db_path))
        con.execute("DELETE FROM config WHERE key = ?", (key,))
        con.commit(); con.close()
        return True
    except Exception as e:
        global_log(f"❌ Erreur suppression clé config '{key}': {e}")
        return False

def get_log_tail(config: dict, max_lines: int = 300) -> str:
    try:
        p = _get_log_path(config)
        if not p.exists(): return ""
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return "".join(lines[-max_lines:])
    except Exception as e:
        global_log(f"⚠️ Erreur lecture log: {e}")
        return ""

def get_log_size(config: dict) -> int:
    try:
        p = _get_log_path(config)
        return p.stat().st_size if p.exists() else 0
    except Exception:
        return 0

def clear_log_file(config: dict) -> bool:
    try:
        p = _get_log_path(config)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8"): pass
        return True
    except Exception as e:
        global_log(f"❌ Erreur vidage fichier log: {e}")
        return False
