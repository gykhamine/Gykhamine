#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║           GYKHAMINE STUDIO — v3.0.1 (UI Update)          ║
║     No-code visual editor for Gykhamine capsules         ║
║     Developed for the GCI project — Brazzaville, Congo   ║
╚══════════════════════════════════════════════════════════╝
Dependencies : python3-gi, gtk4, libadwaita-1, zipfile, pandas, openpyxl, requests
Launch       : python3 gy.py
"""
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk, Pango
import os, sys, re, subprocess, threading, shutil, json, webbrowser, socket, zipfile, sqlite3, select, pty, tty, termios, fcntl, struct, requests
from pathlib import Path
from datetime import datetime
import time
# ═══════════════════════════════════════════════════════════════════════
#  GTK4 UTILITIES
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
VERSION  = "3.0.1"
SCRIPT_DIR = Path(__file__).parent.resolve()
LOGO_PATH  = SCRIPT_DIR / "logo.png"
DB_PATH    = Path.home() / ".config" / "gykhamine_studio.db"
DEFAULT_CONFIG = {
    "llama_server_path": "/usr/local/bin/llama-server",
    "llama_model_path":  "/models/qwen2.5-coder.gguf",
    "llama_host":        "127.0.0.1",
    "llama_port":        "8080",
    "gunicorn_bind":     "0.0.0.0:8000",
    "last_project":      "",
    "last_projects":     [],
    "theme":             "dark",
    "open_browser_on_run": True,
    "auto_find_free_port": True,
    "default_port_range_start": 8000,
    "default_port_range_end": 8010,
    "log_file_path":     str(Path.home() / ".local/share/gykhamine_studio/studio.log"),
    "db_path":           str(Path.home() / ".config" / "gykhamine_studio.db"),
    # === Configuration PostgreSQL ===
    "pg_device":         "",
    "pg_mount_point":    "/var/lib/pgsql/data",
    "pg_db_name":        "ma_base",
    "pg_db_user":        "mon_user",
    "pg_db_password":    "mot_de_passe",
    "pg_bind_ip":        "127.0.0.1",
    # === Configuration Redis ===
    "redis_mode":        "local",
    "redis_ip":          "127.0.0.1",
    "redis_port":        "6379",
    "redis_data_dir":    str(Path.home() / "redis_data"),
    "redis_use_persistence": True,
    "redis_env_path":    "/run/media/gykhamine/GY/Gykhamine/gy/.env",
    "redis_update_env":  False,
    # === Configuration NFS Serveur ===
    "nfs_server_mode":   "local",
    "nfs_export_dir":    "/run/media/gykhamine/GY/gy/media",
    "nfs_lan_network":   "192.168.1.0/24",
    # === Configuration NFS Client ===
    "nfs_client_server_ip":   "192.168.1.10",
    "nfs_client_export_dir":  "/srv/nfs",
    "nfs_client_mount_point": str(Path.home() / "nfs_mount"),
    # === Configuration Nginx ===
    "nginx_conf_path":        "/etc/nginx/nginx.conf",
    "nginx_mode":             "reverse_proxy",
    "nginx_server_name":      "localhost",
    "nginx_listen_port":      "443",
    "nginx_upstream_name":    "gunicorn",
    "nginx_upstream_servers": "127.0.0.1:8000, 127.0.0.1:8001, 127.0.0.1:8002",
    "nginx_proxy_pass":       "http://gunicorn",
    "nginx_force_https":      True,
    "nginx_ssl_cert":         "/etc/pki/nginx/server.crt",
    "nginx_ssl_key":          "/etc/pki/nginx/private/server.key",
    "nginx_static_url":       "/static/",
    "nginx_static_path":      "/chemin/vers/ton/projet/static/",
    "nginx_media_url":        "/media/",
    "nginx_media_path":       "/chemin/vers/ton/projet/media/",
    "nginx_max_body":         "20M",
    "nginx_read_timeout":     "60s",
    "nginx_connect_timeout":  "60s",
    "nginx_proxy_buffering":  True,
    "nginx_security_headers": True,
    "nginx_custom_redirects": "/ancien -> /nouveau\n",
    # === Configuration SSH ===
    "ssh_server_mode":       "local",
    "ssh_server_port":       "22",
    "ssh_client_host":       "192.168.1.10",
    "ssh_client_port":       "22",
    "ssh_client_user":       "root",
    "ssh_client_key":        "~/.ssh/id_rsa",
    "ssh_client_auth_mode":  "key",
    # === Configuration Venv ===
    "venv_name":             "venv",
    "venv_path":             "",
}

# ═══════════════════════════════════════════════════════════════════════
#  SQLITE ENGINE — CONFIG + SMART MEMORY + LOGS
# ═══════════════════════════════════════════════════════════════════════
def _get_db_path(cfg_override: str = None) -> Path:
    return Path(cfg_override) if cfg_override else DB_PATH

def _init_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    cur.execute("CREATE TABLE IF NOT EXISTS recent_projects (id INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT UNIQUE NOT NULL, opened_at TEXT NOT NULL)")
    cur.execute("CREATE TABLE IF NOT EXISTS memory (id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT NOT NULL, file_path TEXT NOT NULL, block_name TEXT, action TEXT, ts TEXT NOT NULL, UNIQUE(project, file_path, block_name))")
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
    except Exception: pass

def _get_log_path(config: dict) -> Path:
    p = Path(config.get("log_file_path", DEFAULT_CONFIG["log_file_path"]))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def log_to_file(config: dict, message: str):
    try:
        with open(_get_log_path(config), "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception: pass

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
    
    # Updated colors to match Dark Sky Blue theme request slightly better or keep contrast
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
        patterns = [
            (r'(//.*|/\*[\s\S]*?\*/)', "comment"),
            (r'("[^"]*"|\'[^\']*\'|`[^`]*`)', "string"),
            (r'^\s*#\s*\w+', "preproc"),
            (r'\b(auto|break|case|char|const|continue|default|do|double|else|enum|extern|float|for|goto|if|inline|int|long|register|return|short|signed|sizeof|static|struct|switch|typedef|union|unsigned|void|volatile|while|class|public|private|protected|virtual|template|namespace|bool|true|false|wchar_t)\b', "keyword"),
            (r'\b\d+\b', "number"),
            (r'\b[A-Z]\w*\b', "type"),
            (r'\b[a-zA-Z_]\w*(?=\s*\()', "function"),
            (r'\b[a-zA-Z_]\w*(?=\s*=)', "variable")
        ]
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

def _parse_python_blocks(code: str, file_path: str) -> list[dict]:
    lines = code.splitlines(keepends=True)
    blocks, i, current_lines, current_start = [], 0, [], 0
    
    def flush(label_override=None):
        nonlocal current_lines, current_start
        if not current_lines: return
        raw = "".join(current_lines)
        if raw.strip():
            stripped = raw.strip()
            if label_override: btype, bname = "separator", label_override
            elif re.match(r'^(import|from)\s+', stripped): btype, bname = "import", stripped.splitlines()[0][:60]
            elif re.match(r'^class\s+(\w+)', stripped): btype, bname = "class", re.match(r'^class\s+(\w+)', stripped).group(1)
            elif re.search(r'\bdef\s+(\w+)\s*\(', stripped): btype, bname = "function", re.search(r'\bdef\s+(\w+)\s*\(', stripped).group(1)
            elif stripped.startswith("#"): btype, bname = "comment", stripped[:60]
            else: btype, bname = "other", stripped[:40] if stripped else "bloc"
            
            blocks.append({"type": btype, "name": bname, "code": raw, "start": current_start, "end": current_start + len(current_lines) - 1})
        current_lines, current_start = [], i

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if SEPARATOR_RE.match(stripped):
            flush()
            blocks.append({"type": "separator", "name": stripped.strip("#/-").strip() or "Séparateur", "code": line, "start": i, "end": i})
            current_start = i + 1
            i += 1
            continue
            
        is_root_block_start = not line.startswith((" ", "\t")) and (
            stripped.startswith("@") or 
            re.match(r'^(async\s+)?def\s+\w+', stripped) or 
            re.match(r'^class\s+\w+', stripped) or 
            stripped.startswith("#")
        )
        
        if is_root_block_start:
            flush()
            current_start = i
            while i < len(lines) and lines[i].strip().startswith("@"):
                current_lines.append(lines[i])
                i += 1
            if i < len(lines):
                current_lines.append(lines[i])
                i += 1
            while i < len(lines):
                l = lines[i]
                if l.strip() == "" or l.startswith((" ", "\t")):
                    current_lines.append(l)
                    i += 1
                elif not l.startswith((" ", "\t")) and (l.strip().startswith("@") or re.match(r'^(async\s+)?def\s+\w+', l.strip()) or re.match(r'^class\s+\w+', l.strip()) or l.strip().startswith("#")):
                    break
                else:
                    current_lines.append(l)
                    i += 1
            flush()
            continue
            
        current_lines.append(line)
        i += 1
        
    flush()
    return blocks

def _parse_template_blocks(code: str, file_path: str) -> list[dict]:
    lines = code.splitlines(keepends=True)
    blocks, i, current_lines, current_start, current_type, current_name = [], 0, [], 0, "template_part", "Template"
    
    def flush():
        nonlocal current_lines, current_start, current_type, current_name
        if not current_lines: return
        raw = "".join(current_lines)
        if raw.strip(): blocks.append({"type": current_type, "name": current_name, "code": raw, "start": current_start, "end": current_start + len(current_lines) - 1})
        current_lines, current_start, current_type, current_name = [], i, "template_part", "Template"

    while i < len(lines):
        line = lines[i]; stripped = line.strip()
        m = re.match(r'\{%-?\s*block\s+(\w+).*?%\}', stripped, re.IGNORECASE)
        if m: flush(); current_type, current_name, current_start = "django_block", f"block: {m.group(1)}", i; current_lines.append(line); i += 1; continue
        if re.match(r'\{%-?\s*endblock\b', stripped, re.IGNORECASE): current_lines.append(line); flush(); current_start = i + 1; i += 1; continue
        if re.match(r'<style(\s[^>]*)?>$', stripped, re.IGNORECASE): flush(); current_type, current_name, current_start = "style", "CSS Block (<style>)", i; current_lines.append(line); i += 1; continue
        if re.match(r'</style\s*>', stripped, re.IGNORECASE): current_lines.append(line); flush(); current_start = i + 1; i += 1; continue
        if re.match(r'<script(\s[^>]*)?>$', stripped, re.IGNORECASE): flush(); current_type, current_name, current_start = "script", "JS Block (<script>)", i; current_lines.append(line); i += 1; continue
        if re.match(r'</script\s*>', stripped, re.IGNORECASE): current_lines.append(line); flush(); current_start = i + 1; i += 1; continue
        current_lines.append(line); i += 1
    flush()
    return blocks

def _parse_css_blocks(code: str, file_path: str) -> list[dict]:
    lines = code.splitlines(keepends=True)
    blocks, i, current_lines, current_start = [], 0, [], 0
    def flush(label="CSS Rule"):
        nonlocal current_lines, current_start
        if not current_lines: return
        raw = "".join(current_lines)
        if raw.strip(): blocks.append({"type": "style_rule", "name": label, "code": raw, "start": current_start, "end": current_start + len(current_lines) - 1})
        current_lines, current_start = [], i

    while i < len(lines):
        line = lines[i]; stripped = line.strip()
        if stripped.startswith('@') or (stripped and not stripped.startswith('/') and '{' in stripped and not stripped.startswith('}')):
            flush(re.sub(r'\s+', ' ', stripped.split('{')[0].strip()[:40]) or "CSS Rule"); current_start = i; current_lines.append(line)
        elif stripped.startswith('/*'): flush("Comment"); current_start = i; current_lines.append(line)
        else: current_lines.append(line); i += 1
    flush("End of file"); return blocks

def _parse_js_blocks(code: str, file_path: str) -> list[dict]:
    lines = code.splitlines(keepends=True)
    blocks, i, current_lines, current_start = [], 0, [], 0
    def flush(label="JS Block"):
        nonlocal current_lines, current_start
        if not current_lines: return
        raw = "".join(current_lines)
        if raw.strip(): blocks.append({"type": "script_block", "name": label, "code": raw, "start": current_start, "end": current_start + len(current_lines) - 1})
        current_lines, current_start = [], i

    while i < len(lines):
        line = lines[i]; stripped = line.strip()
        if re.match(r'^(class|function|async\s+function|const|let|var|export|import)\s+', stripped) or re.match(r'^//\s*#{4,}', stripped):
            parts = stripped.split(); flush(f"{parts[0]} {parts[1].split('(')[0].split('=')[0]}"[:40] if len(parts) >= 2 else parts[0]); current_start = i; current_lines.append(line)
        else: current_lines.append(line); i += 1
    flush("End of file"); return blocks

def _parse_c_blocks(code: str, file_path: str) -> list[dict]:
    lines = code.splitlines(keepends=True)
    blocks, i, current_lines, current_start = [], 0, [], 0
    def flush(label="C/C++ Block"):
        nonlocal current_lines, current_start
        if not current_lines: return
        raw = "".join(current_lines)
        if raw.strip(): blocks.append({"type": "c_block", "name": label, "code": raw, "start": current_start, "end": current_start + len(current_lines) - 1})
        current_lines, current_start = [], i

    while i < len(lines):
        line = lines[i]; stripped = line.strip()
        if re.match(r'^(class|struct|enum|namespace)\s+\w+', stripped) or re.match(r'^(void|int|char|float|double|bool|auto|unsigned|signed|long|short)\s+\w+\s*\(', stripped) or re.match(r'^#\s*(include|define|pragma|ifdef|ifndef|endif)', stripped) or re.match(r'^//\s*#{4,}', stripped):
            parts = stripped.split(); flush(" ".join(parts[:2])[:40]); current_start = i; current_lines.append(line)
        else: current_lines.append(line); i += 1
    flush("End of file"); return blocks

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
        provider.load_from_data(b""".terminal-tty-view { background-color: #000000; color: #cccccc; font-family: 'Fira Code', 'Consolas', 'Monaco', monospace; font-size: 14px; padding: 10px; }""")
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

    def _build_prompt(self, block_type, current_code, user_intent, context_deps=""):
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
            "other": "Tu es un assistant de codage polyvalent."
        }
        role = roles.get(block_type, roles["other"])
        
        format_instruction = """
RÈGLE ABSOLUE :
1. Ne réponds QUE par le code modifié.
2. N'ajoute AUCUN texte explicatif, AUCUNE balise markdown (comme ```python), AUCUN commentaire introductif.
3. Si tu ne peux pas faire la modification, renvoie le code original inchangé.
4. Conserve l'indentation originale.
"""
        prompt = f"""{role}

CONTEXTE :
{context_deps if context_deps else "Aucune dépendance externe majeure."}

CODE ACTUEL À MODIFIER :
{current_code}

DEMANDE DE L'UTILISATEUR :
"{user_intent}"

OBJECTIF :
Modifie le code ci-dessus pour satisfaire la demande tout en respectant les bonnes pratiques.
{format_instruction}
"""
        return prompt

    def process_modification(self, block_type, current_code, user_intent, context_deps=""):
        cfg = self.get_config()
        host = cfg.get("llama_host", "127.0.0.1")
        port = cfg.get("llama_port", "8080")
        url = f"http://{host}:{port}/v1/chat/completions"
        
        prompt = self._build_prompt(block_type, current_code, user_intent, context_deps)
        
        payload = {
            "model": "qwen2.5-coder",
            "messages": [
                {"role": "system", "content": "Tu es un moteur de génération de code strict. Tu ne parles pas, tu codes."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "top_p": 0.9,
            "max_tokens": 1024,
            "stream": False
        }
        
        try:
            self.log(f"🤖 Envoi de la requête IA pour '{block_type}'...")
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 200:
                data = response.json()
                raw_content = data['choices'][0]['message']['content']
                cleaned_code = self._clean_code_output(raw_content, block_type)
                return cleaned_code
            else:
                self.log(f"❌ Erreur API IA: {response.status_code}")
                return None
        except Exception as e:
            self.log(f"❌ Exception connexion IA: {e}")
            return None

    def _clean_code_output(self, text, block_type):
        text = re.sub(r'^```[a-zA-Z]*\n', '', text)
        text = re.sub(r'\n```$', '', text)
        text = text.strip()
        
        if block_type in ["function", "class", "django_model", "django_view"]:
            lines = text.split('\n')
            code_start_idx = 0
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped and not stripped.startswith(("Voici", "Here is", "Le code", "# Note")):
                    if any(keyword in stripped for keyword in ["def ", "class ", "import ", "from ", "@"]):
                        code_start_idx = i
                        break
            if code_start_idx > 0:
                text = "\n".join(lines[code_start_idx:])
        return text

class AIModificationDialog(Gtk.Dialog):
    def __init__(self, parent, block, ai_engine, on_confirm_cb):
        # Augmentation de la largeur par défaut de 900 à 1200 pour plus d'espace
        super().__init__(title=f"✨ Modification IA : {block['name']}", transient_for=parent, default_width=1200, default_height=1200)
        self.block = block
        self.ai_engine = ai_engine
        self.on_confirm_cb = on_confirm_cb
        self.modified_code = None

        content = self.get_content_area()
        content.set_spacing(10)
        set_margins(content, 16)

        # --- Header Info ---
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl_type = Gtk.Label(label=f"Type: {block['type'].upper()}", css_classes=["badge-function"], margin_end=10)
        header.append(lbl_type)
        content.append(header)
        content.append(Gtk.Separator())

        # --- Main Area: Code Comparison ---
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_vexpand(True)
        
        # AJOUT : Permet de mieux saisir la poignée de redimensionnement
        paned.set_wide_handle(True) 
        
        # Original Code
        box_orig = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box_orig.append(Gtk.Label(label="Code Actuel", xalign=0, css_classes=["dim-label"]))
        scroll_orig = Gtk.ScrolledWindow()
        scroll_orig.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.view_orig = Gtk.TextView()
        self.view_orig.set_editable(False)
        self.view_orig.set_monospace(True)
        self.view_orig.get_buffer().set_text(block['code'])
        apply_syntax_highlighting(self.view_orig, self._get_lang(block['type']))
        scroll_orig.set_child(self.view_orig)
        box_orig.append(scroll_orig)

        # New Code
        box_new = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box_new.append(Gtk.Label(label="Proposition IA", xalign=0, css_classes=["dim-label"]))
        scroll_new = Gtk.ScrolledWindow()
        scroll_new.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.view_new = Gtk.TextView()
        self.view_new.set_editable(False)
        self.view_new.set_monospace(True)
        self.view_new.get_buffer().set_text("// En attente de génération...")
        apply_syntax_highlighting(self.view_new, self._get_lang(block['type']))
        scroll_new.set_child(self.view_new)
        box_new.append(scroll_new)

        paned.set_start_child(box_orig)
        paned.set_end_child(box_new)
        
        # MODIFICATION : On définit une position plus large (600 au lieu de 450) 
        # ou on peut commenter cette ligne pour laisser GTK décider (souvent 50/50)
        paned.set_position(600) 
        
        content.append(paned)
        content.append(Gtk.Separator())

        # --- Bottom Area: Prompt Input ---
        prompt_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        prompt_box.append(Gtk.Label(label="Instructions pour l'IA (Max 150 mots) :", xalign=0, css_classes=["heading"]))
        
        # Text View for Prompt (Multiline)
        scroll_prompt = Gtk.ScrolledWindow()
        scroll_prompt.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_prompt.set_size_request(-1, 100) 
        self.intent_entry = Gtk.TextView()
        self.intent_entry.set_wrap_mode(Gtk.WrapMode.WORD)
        self.intent_entry.set_monospace(True)
        scroll_prompt.set_child(self.intent_entry)
        prompt_box.append(scroll_prompt)

        # Action Bar with WhatsApp-style button
        action_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_bar.set_halign(Gtk.Align.END)
        self.btn_cancel = Gtk.Button(label="Annuler")
        self.btn_cancel.connect("clicked", lambda *_: self.destroy())
        
        # WhatsApp Style Button
        btn_generate = Gtk.Button()
        btn_generate.add_css_class("whatsapp-btn")
        btn_generate.set_tooltip_text("Envoyer la demande")
        icon = Gtk.Image.new_from_icon_name("mail-send-symbolic")
        btn_generate.set_child(icon)
        btn_generate.connect("clicked", self._on_generate)
        
        action_bar.append(self.btn_cancel)
        action_bar.append(btn_generate)
        prompt_box.append(action_bar)
        content.append(prompt_box)

    def _get_lang(self, btype):
        mapping = {
            "function": "python", "class": "python", "django_model": "python",
            "django_view": "python", "django_form": "python", "django_settings": "python",
            "django_url": "python", "template": "jinja", "javascript": "js",
            "c_block": "c", "shell": "bash", "css": "css"
        }
        return mapping.get(btype, "python")

    def _on_generate(self, *_):
        buf = self.intent_entry.get_buffer()
        intent = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True).strip()
        
        # Word count check
        if len(intent.split()) > 150:
            self.ai_engine.log("⚠️ Votre demande dépasse 150 mots.")
            return
            
        if not intent:
            self.ai_engine.log("⚠️ Veuillez décrire la modification.")
            return
            
        threading.Thread(target=self._thread_generate, args=(self.block['type'], intent), daemon=True).start()

    def _thread_generate(self, btype, intent):
        result = self.ai_engine.process_modification(btype, self.block['code'], intent)
        GLib.idle_add(self._update_ui_with_result, result)

    def _update_ui_with_result(self, result):
        if result:
            self.modified_code = result
            self.view_new.get_buffer().set_text(result)
            apply_syntax_highlighting(self.view_new, self._get_lang(self.block['type']))
            self.ai_engine.log("✅ Modification générée.")
        else:
            self.ai_engine.log("❌ Échec de la génération ou erreur serveur.")
            self.view_new.get_buffer().set_text("// Erreur lors de la génération.")

    def _on_accept(self, *_):
        if self.modified_code:
            self.on_confirm_cb(self.block, self.modified_code)
            self.destroy()

class LlamaSetupDialog(Gtk.Dialog):
    def __init__(self, parent, config, on_save_and_start):
        super().__init__(title="⚙️ Configuration Llama.cpp (Sudo)", transient_for=parent, default_width=500, default_height=300)
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
        dlg.connect("response", lambda d, _: d.destroy())
        dlg.present()

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
        
        lbl_name = Gtk.Label(label=self.block["name"]); lbl_name.set_ellipsize(Pango.EllipsizeMode.END); lbl_name.set_hexpand(True); lbl_name.set_xalign(0); lbl_name.set_max_width_chars(40); lbl_name.add_css_class("block-name"); header.append(lbl_name)
        
        # --- NOUVEAU BOUTON IA ---
        if self.ai_engine:
            btn_ai = Gtk.Button(label="🤖 IA"); 
            btn_ai.set_tooltip_text("Modifier ce bloc avec l'IA"); 
            btn_ai.add_css_class("block-action-btn"); 
            btn_ai.add_css_class("btn-ai"); 
            btn_ai.connect("clicked", self._open_ai_dialog); 
            header.append(btn_ai)
        # -------------------------
        
        for label, tooltip, cb, css in [("👁", "View / Edit", self._view_code, "btn-view"), ("✏", "Inline Edit", self._toggle_edit, "btn-edit"), ("⧉", "Copy", self._do_copy, "btn-copy"), ("✕", "Delete", self._do_delete, "btn-delete")]:
            btn = Gtk.Button(label=label); btn.set_tooltip_text(tooltip); btn.add_css_class("block-action-btn"); btn.add_css_class(css); btn.connect("clicked", cb); header.append(btn)
        
        self.append(header)
        bar = Gtk.Box(); bar.set_size_request(-1, 2); bar.add_css_class("block-accent-bar"); bar.add_css_class(f"accent-{self.block['type']}"); self.append(bar)

    def _build_editor(self):
        self.editor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        set_margins(self.editor_box, 0); self.editor_box.set_margin_start(12); self.editor_box.set_margin_end(12); self.editor_box.set_margin_bottom(8); self.editor_box.set_visible(False)
        
        self.textview = Gtk.TextView(); self.textview.set_monospace(True); self.textview.set_wrap_mode(Gtk.WrapMode.NONE); self.textview.add_css_class("code-editor")
        self.textview.get_buffer().set_text(self.block["code"]); apply_syntax_highlighting(self.textview, self.lang)
        
        scroll = Gtk.ScrolledWindow(); scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC); scroll.set_size_request(-1, 200); scroll.set_child(self.textview)
        
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_save = Gtk.Button(label="💾 Save"); btn_save.add_css_class("save-btn"); btn_save.connect("clicked", self._do_save)
        btn_cancel = Gtk.Button(label="✕ Close"); btn_cancel.add_css_class("cancel-btn"); btn_cancel.connect("clicked", self._toggle_edit)
        bar.append(btn_save); bar.append(btn_cancel); self.editor_box.append(scroll); self.editor_box.append(bar); self.append(self.editor_box)

    def _toggle_edit(self, *_):
        self.expanded = not self.expanded; self.editor_box.set_visible(self.expanded)

    def _view_code(self, *_):
        dialog = Gtk.Dialog(title=f"Editing: {self.block['name']}", transient_for=self.get_root())
        dialog.set_default_size(800, 500)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        set_margins(content, 12)
        dialog.set_child(content)
        
        scroll = Gtk.ScrolledWindow(); scroll.set_vexpand(True); scroll.set_hexpand(True)
        textview = Gtk.TextView(); textview.set_monospace(True); textview.set_editable(True); textview.set_wrap_mode(Gtk.WrapMode.WORD)
        textview.add_css_class("code-editor")
        textview.get_buffer().set_text(self.block["code"])
        apply_syntax_highlighting(textview, self.lang)
        scroll.set_child(textview); content.append(scroll)
        
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6); btn_box.set_halign(Gtk.Align.END)
        btn1 = Gtk.Button(label="📋 Copy"); btn1.connect("clicked", lambda *_: self._do_copy()); btn_box.append(btn1)
        btn2 = Gtk.Button(label="Close"); btn2.connect("clicked", lambda *_: dialog.destroy()); btn_box.append(btn2)
        btn3 = Gtk.Button(label="💾 Save and Close", css_classes=["suggested-action"]); btn3.connect("clicked", lambda *_: self._save_from_popup(textview, dialog)); btn_box.append(btn3)
        content.append(btn_box)
        dialog.present()

    def _save_from_popup(self, textview, dialog):
        self.block["code"] = textview.get_buffer().get_text(textview.get_buffer().get_start_iter(), textview.get_buffer().get_end_iter(), True)
        self.on_save_cb(self.block, self.block["code"]); self.textview.get_buffer().set_text(self.block["code"]); apply_syntax_highlighting(self.textview, self.lang); dialog.destroy()

    def _do_save(self, *_):
        self.block["code"] = self.textview.get_buffer().get_text(self.textview.get_buffer().get_start_iter(), self.textview.get_buffer().get_end_iter(), True)
        self.on_save_cb(self.block, self.block["code"]); self._toggle_edit()

    def _do_copy(self, *_): Gdk.Display.get_default().get_clipboard().set(self.block["code"])
    def _do_delete(self, *_): self.on_delete_cb(self.block)

    def _open_ai_dialog(self, *_):
        if not self.ai_engine or not self.parent_window: return
        def on_confirm(block, new_code):
            self.block["code"] = new_code
            self.on_save_cb(self.block, new_code)
            self.textview.get_buffer().set_text(new_code)
            apply_syntax_highlighting(self.textview, self.lang)
            self.parent_window._show_toast("✅ Bloc modifié par IA")
            
        dialog = AIModificationDialog(self.parent_window, self.block, self.ai_engine, on_confirm)
        dialog.present()

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

    def start_watcher(self, root_path):
        if self.watcher: self.watcher.running = False; self.watcher = None
        if root_path:
            self.watcher = FileWatcher(root_path, self._refresh_tree_idle)
            self.watcher.start()

    def _refresh_tree_idle(self): GLib.idle_add(self._refresh_tree)
    def _refresh_tree(self):
        if self.project_root: self._populate_tree(self.project_root, None)

    def _toggle_hidden_files(self, *_):
        self.show_hidden = not self.show_hidden
        if self.show_hidden: self.btn_hidden.set_label("👁"); self.btn_hidden.set_tooltip_text("Masquer les fichiers cachés")
        else: self.btn_hidden.set_label("🙈"); self.btn_hidden.set_tooltip_text("Afficher les fichiers cachés")
        if self.project_root: self.load_project(self.project_root, load_config())

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
        self.project_root = root; self.tree_store.clear(); self._populate_tree(root, None); self._load_recent_projects(config)
        self.start_watcher(root)

    def _populate_tree(self, directory: Path, parent_iter):
        try:
            entries = []
            for entry in directory.iterdir():
                if entry.name in ["__pycache__", "node_modules", ".git"]: continue
                if not self.show_hidden and entry.name.startswith('.'): continue
                entries.append(entry)
            entries.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
            for entry in entries:
                is_folder = entry.is_dir()
                new_iter = self.tree_store.append(parent_iter, [entry.name, str(entry), is_folder])
                if is_folder: self._populate_tree(entry, new_iter)
        except PermissionError: pass

    def _load_recent_projects(self, config):
        while child := self.recent_list.get_first_child(): self.recent_list.remove(child)
        for proj_path in get_recent_projects(config):
            path = Path(proj_path)
            if path.exists():
                row = Gtk.ListBoxRow(); row._project_path = path
                lbl = Gtk.Label(label=f"  📂 {path.name}\n{path.parent}"); lbl.set_xalign(0); lbl.set_margin_start(16); lbl.set_margin_top(6); lbl.set_margin_bottom(6)
                lbl.set_ellipsize(Pango.EllipsizeMode.END); lbl.set_max_width_chars(35); lbl.add_css_class("file-item")
                row.set_child(lbl); self.recent_list.append(row)

    def _on_project_selected(self, lb, row):
        if hasattr(row, "_project_path"): self.on_project_select(row._project_path)

    def _create_new_file(self, *_):
        if not self.project_root: return self._show_error("Aucun projet ouvert")
        dialog = Gtk.Dialog(title="Nouveau fichier", transient_for=self.get_root()); dialog.set_default_size(400, 250)
        content = dialog.get_content_area(); content.set_spacing(8); set_margins(content, 12)
        content.append(Gtk.Label(label="Nom du fichier (avec extension):", xalign=0))
        entry = Gtk.Entry(); entry.set_placeholder_text("ex: style.css, script.js, main.c"); content.append(entry)
        content.append(Gtk.Label(label="Contenu initial (optionnel):", xalign=0, margin_top=8))
        text_buf = Gtk.TextBuffer(); text_view = Gtk.TextView.new_with_buffer(text_buf); text_view.set_size_request(-1, 100)
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
            filepath.write_text(text, encoding='utf-8')
            self.on_file_created(filepath); self.load_project(self.project_root, load_config()); dialog.destroy()
            
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
        except Exception as e: self._show_error(f"Erreur: {e}")

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

    def _show_context_menu(self, x, y, full_path, name, is_folder):
        popover = Gtk.Popover(); popover.set_parent(self.tree_view); popover.set_has_arrow(False)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4); set_margins(box, 6)
        btn_rename = Gtk.Button(label="✏️ Renommer"); btn_rename.set_halign(Gtk.Align.FILL); btn_rename.add_css_class("flat"); btn_rename.connect("clicked", lambda *_: self._rename_item(full_path, name, is_folder, popover))
        btn_delete = Gtk.Button(label="🗑 Supprimer"); btn_delete.set_halign(Gtk.Align.FILL); btn_delete.add_css_class("flat"); btn_delete.add_css_class("destructive-action"); btn_delete.connect("clicked", lambda *_: self._delete_item(full_path, name, is_folder, popover))
        box.append(btn_rename); box.append(btn_delete); popover.set_child(box)
        rect = Gdk.Rectangle(); rect.x = x; rect.y = y; rect.width = 1; rect.height = 1; popover.set_pointing_to(rect); popover.popup()

    def _rename_item(self, full_path, old_name, is_folder, popover):
        popover.popdown()
        dialog = Gtk.Dialog(title="Renommer", transient_for=self.get_root()); dialog.set_default_size(350, 150)
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
            except Exception as e: self._show_error(f"Erreur: {e}")
            dialog.destroy()
            
        btn_rename.connect("clicked", on_rename); btn_cancel.connect("clicked", lambda *_: dialog.destroy()); dialog.present()

    def _delete_item(self, full_path, name, is_folder, popover):
        popover.popdown()
        dialog = Gtk.Dialog(title="Confirmer la suppression", transient_for=self.get_root()); dialog.set_default_size(350, 150)
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
            except Exception as e: self._show_error(f"Erreur: {e}")
            dialog.destroy()
            
        btn_delete.connect("clicked", on_delete); btn_cancel.connect("clicked", lambda *_: dialog.destroy()); dialog.present()

class TerminalPanel(Gtk.Box):
    def __init__(self, get_project_root, get_config, show_toast):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.get_project_root, self.get_config, self.show_toast = get_project_root, get_config, show_toast
        self.add_css_class("terminal-panel"); self._build()

    def _build(self):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8); header.set_margin_start(8); header.set_margin_end(8); header.set_margin_top(4); header.set_margin_bottom(4)
        header.append(Gtk.Label(label="🖥 Terminal Log", css_classes=["terminal-title"]))
        spacer = Gtk.Box(); spacer.set_hexpand(True); header.append(spacer)
        btn_clear = Gtk.Button(label="🗑 Clear"); btn_clear.add_css_class("ctrl-btn-small"); btn_clear.connect("clicked", lambda *_: self.log_view.get_buffer().set_text(""))
        header.append(btn_clear); self.append(header); self.append(Gtk.Separator())
        
        self.log_view = Gtk.TextView(); self.log_view.set_editable(False); self.log_view.set_monospace(True); self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR); self.log_view.set_cursor_visible(False); self.log_view.add_css_class("log-view")
        log_scroll = Gtk.ScrolledWindow(); log_scroll.set_hexpand(True); log_scroll.set_vexpand(True); log_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC); log_scroll.set_child(self.log_view)
        self.append(log_scroll)
        
        term_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6); term_box.set_margin_top(4); term_box.set_margin_bottom(4); term_box.set_margin_start(8); term_box.set_margin_end(8)
        term_box.append(Gtk.Label(label="➜", css_classes=["terminal-prompt"]))
        self.cmd_entry = Gtk.Entry(); self.cmd_entry.set_placeholder_text("Enter a command..."); self.cmd_entry.set_hexpand(True); self.cmd_entry.add_css_class("terminal-input"); self.cmd_entry.connect("activate", self._run_custom_command)
        btn_run = Gtk.Button(label="▶"); btn_run.add_css_class("ctrl-btn-start"); btn_run.connect("clicked", self._run_custom_command)
        term_box.append(self.cmd_entry); term_box.append(btn_run); self.append(term_box)

    def _log(self, text: str):
        def _append():
            buf = self.log_view.get_buffer(); buf.insert(buf.get_end_iter(), f"[{datetime.now().strftime('%H:%M:%S')}] {text}\n")
            adj = self.log_view.get_parent().get_vadjustment(); adj.set_value(adj.get_upper())
        GLib.idle_add(_append); log_to_file(self.get_config(), text)

    def _run_custom_command(self, *_):
        cmd_text = self.cmd_entry.get_text().strip()
        if not cmd_text: return
        self._log(f"💻 $ {cmd_text}"); self.cmd_entry.set_text("")
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
        for label, cb in [("🔍 Check", self._check_ports), ("🔫 Kill port", self._kill_port_dialog), ("🔓 UFW Allow", self._ufw_allow_dialog)]:
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
        btn_db_stats.add_css_class("ctrl-btn"); btn_db_stats.set_hexpand(True); btn_db_stats.set_tooltip_text("Afficher un tableau avec les colonnes, clés et les données réelles (max 100 lignes)")
        btn_db_stats.connect("clicked", self._show_db_stats)
        self.append(btn_db_stats)

        # === GESTION POSTGRESQL ===
        sep_pg = Gtk.Separator(); sep_pg.set_margin_top(8); sep_pg.set_margin_bottom(4); self.append(sep_pg)
        lbl_pg = Gtk.Label(label="🐘 Gestion PostgreSQL"); lbl_pg.add_css_class("control-section-title"); lbl_pg.set_xalign(0); self.append(lbl_pg)
        pg_config_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_init = Gtk.Button(label="🔧 Init"); btn_init.add_css_class("ctrl-btn"); btn_init.set_hexpand(True); btn_init.connect("clicked", self._run_pg_initdb); pg_config_box.append(btn_init)
        btn_create = Gtk.Button(label="➕ Créer DB"); btn_create.add_css_class("ctrl-btn"); btn_create.set_hexpand(True); btn_create.connect("clicked", self._run_pg_creatdb); pg_config_box.append(btn_create)
        self.append(pg_config_box)
        self._add_custom_service_row("postgresql", "▶ Démarrer & Configurer", self._run_pg_rundb, self._run_pg_stopdb)

        # === GESTION REDIS ===
        sep_redis = Gtk.Separator(); sep_redis.set_margin_top(8); sep_redis.set_margin_bottom(4); self.append(sep_redis)
        lbl_redis = Gtk.Label(label="🔴 Gestion Redis"); lbl_redis.add_css_class("control-section-title"); lbl_redis.set_xalign(0); self.append(lbl_redis)
        self._add_custom_service_row("redis", "▶ Démarrer Redis", self._run_redis_start, self._run_redis_stop)

        # === GESTION NFS SERVEUR ===
        sep_nfs_s = Gtk.Separator(); sep_nfs_s.set_margin_top(8); sep_nfs_s.set_margin_bottom(4); self.append(sep_nfs_s)
        lbl_nfs_s = Gtk.Label(label="📁 NFS Serveur"); lbl_nfs_s.add_css_class("control-section-title"); lbl_nfs_s.set_xalign(0); self.append(lbl_nfs_s)
        self._add_custom_service_row("nfs_server", "▶ Démarrer Serveur", self._run_nfs_server_start, self._run_nfs_server_stop)

        # === GESTION NFS CLIENT ===
        sep_nfs_c = Gtk.Separator(); sep_nfs_c.set_margin_top(8); sep_nfs_c.set_margin_bottom(4); self.append(sep_nfs_c)
        lbl_nfs_c = Gtk.Label(label="💻 NFS Client"); lbl_nfs_c.add_css_class("control-section-title"); lbl_nfs_c.set_xalign(0); self.append(lbl_nfs_c)
        self._add_custom_service_row("nfs_client", "📥 Monter le partage", self._run_nfs_client_mount, self._run_nfs_client_umount)

        # ============================================
        # === GESTION NGINX ===
        sep_nginx = Gtk.Separator(); sep_nginx.set_margin_top(8); sep_nginx.set_margin_bottom(4); self.append(sep_nginx)
        lbl_nginx = Gtk.Label(label="🌐 Gestion Nginx"); lbl_nginx.add_css_class("control-section-title"); lbl_nginx.set_xalign(0); self.append(lbl_nginx)
        nginx_ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_nginx_config = Gtk.Button(label="⚙ Configurer"); btn_nginx_config.add_css_class("ctrl-btn"); btn_nginx_config.set_hexpand(True); btn_nginx_config.connect("clicked", self._show_nginx_config_dialog)
        btn_nginx_restart = Gtk.Button(label="🔄 Redémarrer"); btn_nginx_restart.add_css_class("ctrl-btn-warn"); btn_nginx_restart.set_hexpand(True); btn_nginx_restart.connect("clicked", self._run_nginx_restart)
        nginx_ctrl_box.append(btn_nginx_config); nginx_ctrl_box.append(btn_nginx_restart)
        self.append(nginx_ctrl_box)
        self._add_custom_service_row("nginx", "▶ Démarrer Nginx", self._run_nginx_start, self._run_nginx_stop)

        # ============================================
        # === GESTION SSH AVANCÉE ===
        sep_ssh = Gtk.Separator(); sep_ssh.set_margin_top(8); sep_ssh.set_margin_bottom(4); self.append(sep_ssh)
        lbl_ssh = Gtk.Label(label="🔐 Gestion SSH (TTY Native)"); lbl_ssh.add_css_class("control-section-title"); lbl_ssh.set_xalign(0); self.append(lbl_ssh)
        ssh_ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_ssh_config = Gtk.Button(label="⚙ Config"); btn_ssh_config.add_css_class("ctrl-btn"); btn_ssh_config.set_hexpand(True); btn_ssh_config.connect("clicked", self._show_ssh_config_dialog)
        btn_ssh_server = Gtk.Button(label="▶ Start Server"); btn_ssh_server.add_css_class("ctrl-btn-start"); btn_ssh_server.set_hexpand(True); btn_ssh_server.connect("clicked", self._run_ssh_server_start)
        ssh_ctrl_box.append(btn_ssh_config); ssh_ctrl_box.append(btn_ssh_server)
        self.append(ssh_ctrl_box)
        self._add_custom_service_row("ssh_client", "🔗 Connect Client (TTY)", self._run_ssh_client_connect, self._run_ssh_client_disconnect_dummy)

        # ============================================
        # === GESTION VENV ===
        sep_venv = Gtk.Separator(); sep_venv.set_margin_top(8); sep_venv.set_margin_bottom(4); self.append(sep_venv)
        lbl_venv = Gtk.Label(label="🐍 Environnements Virtuels"); lbl_venv.add_css_class("control-section-title"); lbl_venv.set_xalign(0); self.append(lbl_venv)
        venv_ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_venv_create = Gtk.Button(label="➕ Create"); btn_venv_create.add_css_class("ctrl-btn"); btn_venv_create.set_hexpand(True); btn_venv_create.connect("clicked", self._run_venv_create)
        btn_venv_install = Gtk.Button(label="📦 Install Pkg"); btn_venv_install.add_css_class("ctrl-btn"); btn_venv_install.set_hexpand(True); btn_venv_install.connect("clicked", self._show_venv_install_dialog)
        btn_venv_del = Gtk.Button(label="🗑 Delete"); btn_venv_del.add_css_class("ctrl-btn-stop"); btn_venv_del.set_hexpand(True); btn_venv_del.connect("clicked", self._run_venv_delete)
        venv_ctrl_box.append(btn_venv_create); venv_ctrl_box.append(btn_venv_install); venv_ctrl_box.append(btn_venv_del)
        self.append(venv_ctrl_box)
        self._add_custom_service_row("venv_activate", "⚡ Activate Shell (TTY)", self._run_venv_activate, self._run_venv_deactivate_dummy)

        # ============================================
        sep2 = Gtk.Separator(); sep2.set_margin_top(8); sep2.set_margin_bottom(4); self.append(sep2)
        lbl3 = Gtk.Label(label="💊 Gykhamine Capsule"); lbl3.add_css_class("control-section-title"); lbl3.set_xalign(0); self.append(lbl3)
        row_cap = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        for label, path, sudo in [("🔑 /1/gy.py", "Gykhamine/1/gy.py", True), ("👤 /2/gy.py", "Gykhamine/2/gy.py", False)]:
            btn = Gtk.Button(label=f"Run {label}"); btn.add_css_class("ctrl-btn-warn" if sudo else "ctrl-btn"); btn.connect("clicked", lambda *_: self._run_gy(path, sudo)); row_cap.append(btn)
        self.append(row_cap)
        
        sep3 = Gtk.Separator(); sep3.set_margin_top(8); sep3.set_margin_bottom(4); self.append(sep3)
        lbl4 = Gtk.Label(label="🤖 AI (llama.cpp)"); lbl4.add_css_class("control-section-title"); lbl4.set_xalign(0); self.append(lbl4)
        # Bouton de configuration et lancement
        btn_setup_llama = Gtk.Button(label="⚙️ Configurer & Lancer Llama (Sudo)")
        btn_setup_llama.add_css_class("ctrl-btn-warn")
        btn_setup_llama.connect("clicked", self._open_llama_setup)
        self.append(btn_setup_llama)
        
        btn_browser = Gtk.Button(label="🌐 Open browser"); btn_browser.add_css_class("ctrl-btn"); btn_browser.connect("clicked", self._open_browser); self.append(btn_browser)
        
        sep_arch = Gtk.Separator(); sep_arch.set_margin_top(8); sep_arch.set_margin_bottom(4); self.append(sep_arch)
        lbl_arch = Gtk.Label(label="📦 ZIP Archiving"); lbl_arch.add_css_class("control-section-title"); lbl_arch.set_xalign(0); self.append(lbl_arch)
        row_arch = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_compress = Gtk.Button(label="🗜 Compress to .zip"); btn_compress.add_css_class("ctrl-btn"); btn_compress.connect("clicked", self._compress_project)
        btn_decompress = Gtk.Button(label="📂 Decompress .zip"); btn_decompress.add_css_class("ctrl-btn"); btn_decompress.connect("clicked", self._decompress_archive)
        row_arch.append(btn_compress); row_arch.append(btn_decompress); self.append(row_arch)
        
        sep4 = Gtk.Separator(); sep4.set_margin_top(8); sep4.set_margin_bottom(4); self.append(sep4)
        btn_stop_all = Gtk.Button(label="⏹ Stop all"); btn_stop_all.add_css_class("ctrl-btn-stop"); btn_stop_all.connect("clicked", self._stop_all_services); self.append(btn_stop_all)

    def _add_service_row(self, name, label, start_cb, stop_cb):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._status_dots = getattr(self, "_status_dots", {})
        dot = Gtk.Label(label="⬤"); dot.add_css_class("status-dot-off"); self._status_dots[name] = dot
        btn_start = Gtk.Button(label=label); btn_start.add_css_class("ctrl-btn-start"); btn_start.set_hexpand(True); btn_start.connect("clicked", start_cb)
        btn_stop = Gtk.Button(label="⏹"); btn_stop.add_css_class("ctrl-btn-stop"); btn_stop.connect("clicked", stop_cb)
        row.append(dot); row.append(btn_start); row.append(btn_stop); self.append(row)

    def _add_custom_service_row(self, name, label, start_cb, stop_cb):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._status_dots = getattr(self, "_status_dots", {})
        dot = Gtk.Label(label="⬤"); dot.add_css_class("status-dot-off"); self._status_dots[name] = dot
        btn_start = Gtk.Button(label=label); btn_start.add_css_class("ctrl-btn-start"); btn_start.set_hexpand(True); btn_start.connect("clicked", start_cb)
        btn_stop = Gtk.Button(label="⏹ Arrêter"); btn_stop.add_css_class("ctrl-btn-stop"); btn_stop.set_hexpand(True); btn_stop.connect("clicked", stop_cb)
        row.append(dot); row.append(btn_start); row.append(btn_stop); self.append(row)

    def _set_dot(self, name, running: bool):
        dot = self._status_dots.get(name)
        if dot:
            dot.remove_css_class("status-dot-on" if not running else "status-dot-off")
            dot.add_css_class("status-dot-off" if not running else "status-dot-on")

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
                if not shell: GLib.idle_add(self.terminal._log, f"▶ {' '.join(str(c) for c in cmd)}")
                
                def _read_stream(stream, prefix=""):
                    for line in iter(stream.readline, ''):
                        if line: GLib.idle_add(self.terminal._log, prefix + line.rstrip())
                    stream.close()
                    
                t_out = threading.Thread(target=_read_stream, args=(proc.stdout,), daemon=True)
                t_err = threading.Thread(target=_read_stream, args=(proc.stderr, ""), daemon=True)
                t_out.start(); t_err.start(); t_out.join(); t_err.join(); proc.wait()
                if name: self.processes.pop(name, None)
                GLib.idle_add(self._set_dot, name, False); GLib.idle_add(self.terminal._log, f"✓ Finished (code {proc.returncode})")
            except Exception as e:
                GLib.idle_add(self.terminal._log, f"❌ Error: {e}")
                if name: GLib.idle_add(self._set_dot, name, False)
                
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
        dialog = Gtk.Dialog(title="Créer un Superutilisateur Django", transient_for=self.get_root()); dialog.set_default_size(400, 300)
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
        if self.get_config().get("open_browser_on_run", True): GLib.timeout_add_seconds(2, lambda: self._open_browser_url(f"http://localhost:{free_port}"))

    def _start_gunicorn(self, *_):
        session = self._get_or_create_session()
        if not session: return
        mp = self._manage_path()
        if not mp: return
        cfg = self.get_config(); bind_addr = cfg.get("gunicorn_bind", "")
        if not bind_addr or bind_addr == "0.0.0.0:8000":
            free_port = self._get_free_port(session.gunicorn_port or 8001)
            if not free_port: return self.terminal._log("❌ No free port")
            bind_addr = f"0.0.0.0:{free_port}"; session.gunicorn_port = free_port; self.gunicorn_port_label.set_text(f"Port: {free_port}")
        else: self.gunicorn_port_label.set_text(f"Bind: {bind_addr}")
        
        if ":80" in bind_addr or ":443" in bind_addr: self.terminal._log("⚠ Warning: Ports 80/443 often require root (sudo) privileges.")
        
        wsgi = ".".join(f.relative_to(mp.parent).parts[:-1]) + ".wsgi" if (f := next(mp.parent.rglob("wsgi.py"), None)) else "wsgi"
        self.terminal._log(f"▶ Gunicorn → {bind_addr} ({wsgi})")
        self._run_cmd(["gunicorn", "--bind", bind_addr, "--workers", "2", wsgi], cwd=str(mp.parent), name="gunicorn")

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
        dialog = Gtk.Dialog(title="Kill a process", transient_for=self.get_root()); dialog.set_default_size(300, 150)
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
        dialog = Gtk.Dialog(title="Ouvrir un port (UFW)", transient_for=self.get_root()); dialog.set_default_size(320, 160)
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

    # === NOUVELLE METHODE POUR LLAMA SUDO ===
    def _open_llama_setup(self, *_):
        dialog = LlamaSetupDialog(self.get_root(), self.get_config(), self._start_llama_sudo)
        dialog.present()

    def _start_llama_sudo(self, server_path, model_path, port):
        host = self.get_config().get("llama_host", "127.0.0.1")
        self.terminal._log(f"🤖 Lancement sudo llama-server → {host}:{port}")
        self.terminal._log(f"📁 Modèle: {model_path}")
        cmd = ["sudo", server_path, "-m", model_path, "--host", host, "--port", port]
        self._run_cmd(cmd, name="llama")
        if self.get_config().get("open_browser_on_run", True):
            GLib.timeout_add_seconds(3, lambda: self._open_browser_url(f"http://{host}:{port}"))

# ═══════════════════════════════════════════════════════════
#  GESTION POSTGRESQL INTÉGRÉE
# ═══════════════════════════════════════════════════════════
    def _run_pg_initdb(self, *_):
        cfg = self.get_config()
        device = cfg.get("pg_device", "")
        mount_point = cfg.get("pg_mount_point", "/var/lib/pgsql/data")
        if not device:
            self.show_toast("❌ Veuillez sélectionner une partition dans les paramètres")
            return
        self.terminal._log("🔧 === Initialisation PostgreSQL ===")
        self.terminal._log(f"📁 Point de montage: {mount_point}")
        
        def _thread():
            try:
                GLib.idle_add(self.terminal._log, f"▶ mkdir -p {mount_point}")
                subprocess.run(["mkdir", "-p", mount_point], check=True)
                
                mount_check = subprocess.run(["mountpoint", "-q", mount_point], capture_output=True)
                if mount_check.returncode != 0:
                    GLib.idle_add(self.terminal._log, f"▶ Montage de {device} sur {mount_point}")
                    subprocess.run(["sudo", "mount", device, mount_point], check=True)
                else: GLib.idle_add(self.terminal._log, "✅ Déjà monté")
                
                pg_version_path = Path(mount_point) / "PG_VERSION"
                if not pg_version_path.exists():
                    GLib.idle_add(self.terminal._log, "▶ Initialisation de la base (initdb)...")
                    subprocess.run(["sudo", "chown", "-R", "postgres:postgres", mount_point], check=True)
                    subprocess.run(["sudo", "chmod", "700", mount_point], check=True)
                    subprocess.run(["sudo", "-u", "postgres", "initdb", "-D", mount_point], check=True)
                else: GLib.idle_add(self.terminal._log, "✅ Base de données déjà initialisée")
                
                GLib.idle_add(self.terminal._log, "▶ Démarrage de PostgreSQL...")
                status = subprocess.run(["sudo", "-u", "postgres", "pg_ctl", "-D", mount_point, "status"], capture_output=True)
                if status.returncode != 0:
                    subprocess.run(["sudo", "-u", "postgres", "pg_ctl", "-D", mount_point, "start"], check=True)
                    GLib.idle_add(self.terminal._log, "✅ PostgreSQL démarré")
                else: GLib.idle_add(self.terminal._log, "✅ PostgreSQL déjà en cours d'exécution")
                
                GLib.idle_add(self.show_toast, "✅ Initialisation PostgreSQL réussie")
                GLib.idle_add(self.terminal._log, "=== OK ===")
            except subprocess.CalledProcessError as e:
                GLib.idle_add(self.terminal._log, f"❌ Erreur lors de l'exécution: {e}")
                GLib.idle_add(self.show_toast, "❌ Échec de l'initialisation")
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
                check_user = subprocess.run(["sudo", "-u", "postgres", "psql", "-tAc", f"SELECT 1 FROM pg_roles WHERE rolname='{db_user}'"], capture_output=True, text=True).stdout.strip()
                if check_user != "1":
                    GLib.idle_add(self.terminal._log, f"▶ Création de l'utilisateur {db_user}")
                    subprocess.run(["sudo", "-u", "postgres", "psql", "-c", f"CREATE USER {db_user} WITH PASSWORD '{db_password}';"], check=True)
                else: GLib.idle_add(self.terminal._log, "✅ Utilisateur déjà existant")
                
                check_db = subprocess.run(["sudo", "-u", "postgres", "psql", "-tAc", f"SELECT 1 FROM pg_database WHERE datname='{db_name}'"], capture_output=True, text=True).stdout.strip()
                if check_db != "1":
                    GLib.idle_add(self.terminal._log, f"▶ Création de la base {db_name}")
                    subprocess.run(["sudo", "-u", "postgres", "createdb", "-O", db_user, db_name], check=True)
                else: GLib.idle_add(self.terminal._log, "✅ Base déjà existante")
                
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
                subprocess.run(["mkdir", "-p", pgdata], check=True)
                mount_check = subprocess.run(["mountpoint", "-q", pgdata], capture_output=True)
                if mount_check.returncode != 0:
                    GLib.idle_add(self.terminal._log, f"▶ Montage de {device} sur {pgdata}")
                    subprocess.run(["sudo", "mount", device, pgdata], check=True)
                else:
                    GLib.idle_add(self.terminal._log, "✅ Déjà monté")
                
                status = subprocess.run(["sudo", "-u", "postgres", "pg_ctl", "-D", pgdata, "status"], capture_output=True)
                is_running = (status.returncode == 0)
                
                if not is_running:
                    GLib.idle_add(self.terminal._log, "▶ Démarrage de PostgreSQL...")
                    subprocess.run(["sudo", "-u", "postgres", "pg_ctl", "-D", pgdata, "start"], check=True)
                else:
                    GLib.idle_add(self.terminal._log, "✅ PostgreSQL déjà en cours d'exécution")
                
                GLib.idle_add(self.terminal._log, f"▶ Configuration de listen_addresses sur '{listen_addr}'...")
                subprocess.run(["sudo", "-u", "postgres", "psql", "-c", f"ALTER SYSTEM SET listen_addresses = '{listen_addr}';"], check=True)
                
                if bind_ip == "0.0.0.0":
                    pg_hba_path = Path(pgdata) / "pg_hba.conf"
                    GLib.idle_add(self.terminal._log, "🌐 Mode Réseau détecté. Automatisation de pg_hba.conf...")
                    hba_content = pg_hba_path.read_text(encoding="utf-8")
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

# ═══════════════════════════════════════════════════════════
#  GESTION REDIS INTÉGRÉE
# ═══════════════════════════════════════════════════════════
    def _run_redis_start(self, *_):
        cfg = self.get_config()
        redis_ip = cfg.get("redis_ip", "127.0.0.1")
        redis_port = cfg.get("redis_port", "6379")
        data_dir = cfg.get("redis_data_dir", str(Path.home() / "redis_data"))
        use_persistence = cfg.get("redis_use_persistence", True)
        env_path = cfg.get("redis_env_path", "")
        update_env = cfg.get("redis_update_env", False)
        
        self.terminal._log("🔴 === Démarrage de Redis ===")
        
        def _thread():
            try:
                if update_env and env_path and Path(env_path).exists():
                    GLib.idle_add(self.terminal._log, "▶ Mise à jour de REDIS_URL dans le .env...")
                    with open(env_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    redis_url = f"redis://{redis_ip}:{redis_port}/1"
                    if "REDIS_URL=" in content:
                        content = re.sub(r'^REDIS_URL=.*$', f'REDIS_URL={redis_url}', content, flags=re.MULTILINE)
                    else:
                        content += f"\nREDIS_URL={redis_url}\n"
                    with open(env_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    GLib.idle_add(self.terminal._log, f"✅ REDIS_URL synchronisé : {redis_url}")
                elif update_env:
                    GLib.idle_add(self.terminal._log, f"⚠ Fichier .env introuvable à : {env_path}")
                
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
        redis_port = cfg.get("redis_port", "6379")
        self.terminal._log("🛑 === Arrêt de Redis ===")
        
        def _thread():
            try:
                GLib.idle_add(self.terminal._log, f"▶ Arrêt de Redis sur {redis_ip}:{redis_port}...")
                subprocess.run(["redis-cli", "-h", redis_ip, "-p", redis_port, "shutdown", "nosave"], capture_output=True)
                subprocess.run(["pkill", "-f", "redis-server"], capture_output=True)
                GLib.idle_add(self._set_dot, "redis", False)
                GLib.idle_add(self.show_toast, "✅ Redis arrêté")
                GLib.idle_add(self.terminal._log, "=== STOPPED ===")
            except Exception as e:
                GLib.idle_add(self.terminal._log, f"❌ Exception: {e}")
                
        threading.Thread(target=_thread, daemon=True).start()

# ═══════════════════════════════════════════════════════════
#  GESTION NFS INTÉGRÉE
# ═══════════════════════════════════════════════════════════
    def _run_nfs_server_start(self, *_):
        cfg = self.get_config()
        export_dir = cfg.get("nfs_export_dir", "/run/media/gykhamine/GY/gy/media")
        mode = cfg.get("nfs_server_mode", "local")
        lan_network = cfg.get("nfs_lan_network", "192.168.1.0/24") if mode == "network" else "127.0.0.1"
        
        self.terminal._log("📁 === Démarrage du Serveur NFS ===")
        
        def _thread():
            try:
                GLib.idle_add(self.terminal._log, f"▶ Création du dossier d'export : {export_dir}")
                subprocess.run(["mkdir", "-p", export_dir], check=True)
                subprocess.run(["chmod", "777", export_dir], check=True)
                
                GLib.idle_add(self.terminal._log, "▶ Mise à jour de /etc/exports...")
                exports_path = "/etc/exports"
                try:
                    with open(exports_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                except FileNotFoundError:
                    lines = []
                
                lines = [l for l in lines if not l.strip().startswith("# --- Gykhamine NFS ---") and not l.strip().startswith(export_dir)]
                new_entry = f"# --- Gykhamine NFS ---\n{export_dir} {lan_network}(rw,sync,no_subtree_check,no_root_squash)\n"
                lines.append(new_entry)
                content = "".join(lines)
                subprocess.run(["sudo", "tee", exports_path], input=content, text=True, check=True)
                
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
                GLib.idle_add(self.show_toast, "❌ Échec du démarrage NFS")
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

# ═══════════════════════════════════════════════════════════
#  GESTION NGINX INTÉGRÉE
# ═══════════════════════════════════════════════════════════
    def _show_nginx_config_dialog(self, *_):
        cfg = self.get_config()
        dialog = Gtk.Dialog(title="⚙ Configuration Avancée Nginx", transient_for=self.get_root())
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
                upstream_block = f"upstream {upstream_name} {{\n    least_conn;\n{upstream_content}\n    keepalive 32;\n}}\n"
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
    location ~* \.(php|py|pl|sh|cgi|exe)$ {{
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

# ═══════════════════════════════════════════════════════════
#  GESTION SSH INTÉGRÉE (AVANCÉE)
# ═══════════════════════════════════════════════════════════
    def _show_ssh_config_dialog(self, *_):
        cfg = self.get_config()
        dialog = Gtk.Dialog(title="⚙ Configuration SSH", transient_for=self.get_root())
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

# ═══════════════════════════════════════════════════════════
#  GESTION VENV INTÉGRÉE
# ═══════════════════════════════════════════════════════════
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

# ═══════════════════════════════════════════════════════════
#  VISUALISATION DES DONNÉES ET EXPORT (TABLEAU RÉEL)
# ═══════════════════════════════════════════════════════════
    def _show_db_stats(self, *_):
        mp = self._manage_path()
        if not mp:
            self.terminal._log("❌ manage.py introuvable. Ouvrez d'abord un projet Django valide.")
            self.show_toast("❌ Projet Django non détecté"); return
            
        self.terminal._log("🔍 Récupération des données via Django ORM (max 100 lignes/table)...")
        self.show_toast("⏳ Chargement des données...")
        
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
            qs = model.objects.all()[:100]
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
                proc = subprocess.run(cmd, cwd=str(mp.parent), capture_output=True, text=True, env=env, timeout=20)
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
                GLib.idle_add(self.terminal._log, "❌ Délai d'attente dépassé (la base est peut-être trop volumineuse).")
                GLib.idle_add(self.show_toast, "⏱ Délai dépassé")
            except Exception as e:
                GLib.idle_add(self.terminal._log, f"❌ Exception: {e}")
                GLib.idle_add(self.show_toast, "❌ Erreur inattendue")
                
        threading.Thread(target=_thread, daemon=True).start()

    def _display_db_stats_popup(self, stats: list):
        self.db_stats_data = stats; self.current_selected_table_data = None
        dialog = Gtk.Dialog(title="📊 Visualisation des Tables et Données", transient_for=self.get_root()); dialog.set_default_size(1000, 650)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12); set_margins(content, 16); dialog.set_child(content)
        
        header_info = Gtk.Label(label=f"{len(stats)} table(s) trouvée(s). Cliquez sur une table pour voir ses données (max 100 lignes)."); header_info.add_css_class("heading"); content.append(header_info); content.append(Gtk.Separator())
        
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

    def _open_browser(self, *_): self._open_browser_url("http://localhost:8000")
    def _open_browser_url(self, url):
        user = os.environ.get("SUDO_USER", "gykhamine")
        self.terminal._log(f"🌐 Ouverture de {url} en tant que {user}...")
        try: subprocess.run(["sudo", "-u", user, "xdg-open", url], check=False)
        except Exception as e: self.terminal._log(f"❌ Erreur d'ouverture du navigateur: {e}"); return False

    def _compress_project(self, *_):
        root = self.get_project_root()
        if not root: return self.terminal._log("❌ No project open")
        dialog = Gtk.Dialog(title="Save ZIP archive", transient_for=self.get_root()); dialog.set_default_size(500, 150)
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

# ═══════════════════════════════════════════════════════════════════════
#  C COMPILER POPUP
# ═══════════════════════════════════════════════════════════════════════
class CCompilerDialog(Gtk.Dialog):
    def __init__(self, parent, get_config, terminal_log_cb):
        super().__init__(title="🛠️ Compilateur C/C++", transient_for=parent, default_width=800, default_height=600)
        self.get_config = get_config
        self.terminal_log = terminal_log_cb
        self.current_output_file = None
        
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
        content.append(header_box)
        content.append(Gtk.Separator())
        
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        self.text_view = Gtk.TextView()
        self.text_view.set_monospace(True)
        self.text_view.set_wrap_mode(Gtk.WrapMode.NONE)
        self.text_view.add_css_class("code-editor")
        self.text_view.get_buffer().set_text("// Collez votre code C ici\n#include <stdio.h>\nint main() {\n    printf(\"Hello from Gykhamine!\\n\");\n    return 0;\n}")
        apply_syntax_highlighting(self.text_view, "c")
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

    def _on_compile(self, *_):
        code = self.text_view.get_buffer().get_text(self.text_view.get_buffer().get_start_iter(), self.text_view.get_buffer().get_end_iter(), True)
        if not code.strip():
            self._log("❌ Aucun code à compiler.")
            return
            
        import tempfile
        fd, src_path = tempfile.mkstemp(suffix=".c")
        try:
            with os.fdopen(fd, 'w') as f: f.write(code)
            
            output_type = self.combo_type.get_active()
            out_ext = ".out"
            gcc_flags = []
            if output_type == 1: out_ext = ".so"; gcc_flags = ["-shared", "-fPIC"]
            elif output_type == 2: out_ext = ".ko"; gcc_flags = ["-c"]
            
            out_path = src_path.replace(".c", out_ext)
            self.current_output_file = out_path
            
            cmd = ["gcc"] + gcc_flags + [src_path, "-o", out_path]
            if output_type == 1: cmd.append("-lm")
            
            self._log(f"▶ Compilation: {' '.join(cmd)}")
            proc = subprocess.run(cmd, capture_output=True, text=True)
            
            if proc.returncode == 0:
                self._log(f"✅ Succès! Fichier généré: {out_path}")
                self._log(f"💡 Vous pouvez le trouver dans le dossier temporaire ou le déplacer.")
            else:
                self._log(f"❌ Erreur de compilation:")
                self._log(proc.stderr)
        finally: pass

# ═══════════════════════════════════════════════════════════════════════
#  TAB SYSTEM & EDITOR VIEW
# ═══════════════════════════════════════════════════════════════════════
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
        dialog = Gtk.Dialog(title="Add a new block", transient_for=self.get_root()); dialog.set_default_size(400, 250)
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

    def _render_blocks(self):
        while child := self.blocks_box.get_first_child(): self.blocks_box.remove(child)
        self.lbl_count.set_text(str(len(self.blocks))); self._cards = []
        for block in self.blocks:
            # Passage de ai_engine et self.get_root() comme parent_window
            card = BlockCard(block, self._on_block_save, self._on_block_delete, self._on_block_copy, self.file_ext, ai_engine=self.ai_engine, parent_window=self.get_root())
            self.blocks_box.append(card); self._cards.append(card)

    def _on_block_save(self, block, new_code):
        block["code"] = new_code; self._push_state(); self.toast_cb("✅ Updated")
        if self.current_file and self._get_config_cb: memory_record(self._get_config_cb(), str(self.current_file.parent), str(self.current_file), block.get("name"), "edit")

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
        if not self.current_file: return self.toast_cb("❌ No file")
        try:
            self.current_file.write_text("".join(b["code"] for b in self.blocks), encoding="utf-8")
            self._push_state(); self.toast_cb(f"💾 Saved: {self.current_file.name}")
        except Exception as e: self.toast_cb(f"❌ Error: {e}")

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

CSS = """
/* ── Base ────────────────────────────────────────────────────────── */
window { background-color: #0d0d0d; color: #4aa3df; } /* Dark Sky Blue Text */

/* ── Panel titles ────────────────────────────────────────────────── */
.panel-title, .control-section-title { font-size: 11px; font-weight: bold; color: #4aa3df; text-transform: uppercase; min-width: 0; }

/* ── File list ───────────────────────────────────────────────────── */
.file-item { font-size: 11px; font-family: monospace; min-width: 0; color: #4aa3df; }
.file-category { font-size: 10px; color: #4aa3df; min-width: 0; }
.file-category:hover { color: #6bcfff; }
.block-name { font-size: 11px; font-family: monospace; min-width: 0; color: #4aa3df; }

/* ── Block cards ─────────────────────────────────────────────────── */
.block-card { background-color: #141414; border-radius: 6px; border: 1px solid #2a2a2a; margin-bottom: 4px; min-width: 0; }
.block-card:hover { border-color: #444; }

/* ── Type badges ─────────────────────────────────────────────────── */
.block-badge { font-size: 9px; font-weight: bold; border-radius: 4px; padding: 1px 4px; min-width: 0; }
.badge-import, .badge-style, .badge-style_rule { background-color: #3498db; color: #fff; }
.badge-class { background-color: #3498db; color: #fff; }
.badge-function, .badge-script_block { background-color: #9b59b6; color: #fff; }
.badge-template, .badge-template_part, .badge-django_block { background-color: #e67e22; color: #fff; }
.badge-script, .badge-c_block { background-color: #f1c40f; color: #000; }
.badge-separator, .badge-other { background-color: #333; color: #aaa; }

/* ── Block action buttons ────────────────────────────────────────── */
.block-action-btn { font-size: 10px; background: transparent; border: 1px solid #2a2a2a; border-radius: 4px; padding: 2px 5px; min-width: 0; color: #4aa3df; }
.block-action-btn:hover { background-color: #1e1e1e; }

/* ── Code editor ─────────────────────────────────────────────────── */
.code-editor { font-family: monospace; font-size: 11px; background-color: #0a0a0a; color: #4aa3df; min-width: 0; }

/* ── Save buttons ────────────────────────────────────────────────── */
.save-btn, .save-file-btn { background-color: #1a4a2a; color: #2ecc71; border: 1px solid #2ecc71; border-radius: 4px; min-width: 0; }
.cancel-btn { background-color: #2a1a1a; color: #e74c3c; border: 1px solid #e74c3c; border-radius: 4px; min-width: 0; }

/* ── Control panel buttons ───────────────────────────────────────── */
.ctrl-btn, .ctrl-btn-small, .toolbar-btn { background-color: #1a1a2a; border: 1px solid #333; border-radius: 4px; font-size: 10px; padding: 3px 6px; min-width: 0; color: #4aa3df; }
.ctrl-btn-start { background-color: #0a2a0a; color: #2ecc71; border-color: #2ecc71; border-radius: 4px; font-size: 10px; padding: 3px 6px; min-width: 0; }
.ctrl-btn-stop { background-color: #2a0a0a; color: #e74c3c; border-color: #e74c3c; border-radius: 4px; font-size: 10px; padding: 3px 6px; min-width: 0; }
.ctrl-btn-warn { background-color: #2a1f0a; color: #f39c12; border-color: #f39c12; border-radius: 4px; font-size: 10px; padding: 3px 6px; min-width: 0; }

/* ── Status indicators ───────────────────────────────────────────── */
.status-dot-off { color: #333; }
.status-dot-on  { color: #2ecc71; }

/* ── Terminal Panel ──────────────────────────────────────────────── */
.terminal-panel { background-color: #1e1e1e; border-top: 1px solid #3c3c3c; }
.terminal-title { font-size: 11px; font-weight: bold; color: #4aa3df; text-transform: uppercase; }
.log-view { font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 12px; background-color: transparent; color: #4aa3df; padding: 8px; min-width: 0; }
.terminal-prompt { color: #2ecc71; font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace; font-weight: bold; font-size: 12px; margin-right: 4px; }
.terminal-input { background-color: #2d2d2d; color: #4aa3df; border: 1px solid #3c3c3c; border-radius: 4px; font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 12px; padding: 4px 8px; }
.terminal-input:focus { border-color: #007acc; outline: none; }

/* ── Editor toolbar ──────────────────────────────────────────────── */
.toolbar-label { font-size: 11px; color: #4aa3df; min-width: 0; }
.block-count-badge { font-size: 10px; font-weight: bold; background-color: #1a1a2a; color: #61afef; border-radius: 4px; padding: 1px 6px; min-width: 0; }
.editor-file-label { font-size: 12px; font-weight: bold; min-width: 0; color: #4aa3df; }

/* ── Bottom accent bar of cards ──────────────────────────────────── */
.block-accent-bar { min-height: 2px; min-width: 0; }
.accent-function, .accent-script_block { background-color: #9b59b6; }
.accent-class { background-color: #3498db; }
.accent-import, .accent-style { background-color: #2980b9; }
.accent-django_block { background-color: #e67e22; }
.accent-script, .accent-c_block { background-color: #f1c40f; }
.accent-separator { background-color: #333; }
.accent-other, .accent-template_part { background-color: #222; }

/* ── Tabs System ─────────────────────────────────────────────────── */
.tab-bar { background-color: #1a1a1a; border-bottom: 1px solid #333; min-height: 35px; }
.tab-button { background-color: #252526; border-radius: 4px 4px 0 0; padding: 4px 8px; cursor: pointer; border: 1px solid #333; border-bottom: none; }
.tab-button:hover { background-color: #2a2a2a; }
.tab-button.active-tab { background-color: #0d0d0d; border-top: 2px solid #007acc; }
.tab-button label { color: #4aa3df; font-size: 12px; }
.tab-button button { min-width: 20px; min-height: 20px; padding: 0; }

/* ── Light theme ─────────────────────────────────────────────────── */
.theme-light window { background-color: #f5f5f5; color: #222; }
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
"""

class GykhamineStudioApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.config = load_config()
        self.project_root = None
        self.is_fullscreen = False
        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        provider = Gtk.CssProvider(); provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        self.win = Adw.ApplicationWindow(application=app); self.win.set_title("Gykhamine Studio"); self.win.set_default_size(1400, 850)
        self.toast_overlay = Adw.ToastOverlay(); main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        header = Adw.HeaderBar()
        logo_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        if LOGO_PATH.exists():
            try:
                from PIL import Image as PilImage; import tempfile
                pil_img = PilImage.open(str(LOGO_PATH)).resize((15, 20), PilImage.LANCZOS)
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False); pil_img.save(tmp.name)
                logo_picture = Gtk.Picture.new_for_filename(tmp.name); logo_picture.set_hexpand(False); logo_picture.set_vexpand(False); logo_box.append(logo_picture)
            except Exception: logo_box.append(Gtk.Label(label="GYKHAMINE", css_classes=["heading"]))
        else: logo_box.append(Gtk.Label(label="GYKHAMINE", css_classes=["heading"]))
        logo_box.append(Gtk.Label(label="GYKHAMINE STUDIO", css_classes=["heading"]))
        header.set_title_widget(logo_box)
        
        self.btn_toggle_left = Gtk.Button(label="☰"); self.btn_toggle_left.set_tooltip_text("Show/Hide explorer"); self.btn_toggle_left.connect("clicked", self._toggle_left_panel); header.pack_start(self.btn_toggle_left)
        btn_open = Gtk.Button(label="📂 Open"); btn_open.add_css_class("suggested-action"); btn_open.connect("clicked", self._open_project_dialog); header.pack_start(btn_open)
        
        self.btn_toggle_terminal = Gtk.Button(label="🖥"); self.btn_toggle_terminal.set_tooltip_text("Show/Hide terminal"); self.btn_toggle_terminal.connect("clicked", self._toggle_terminal_panel); header.pack_end(self.btn_toggle_terminal)
        btn_fullscreen = Gtk.Button(label="⛶"); btn_fullscreen.set_tooltip_text("Fullscreen"); btn_fullscreen.connect("clicked", self._toggle_fullscreen); header.pack_end(btn_fullscreen)
        self.btn_toggle_right = Gtk.Button(label="⚙"); self.btn_toggle_right.set_tooltip_text("Show/Hide control panel"); self.btn_toggle_right.connect("clicked", self._toggle_right_panel); header.pack_end(self.btn_toggle_right)
        btn_settings = Gtk.Button(icon_name="preferences-system-symbolic"); btn_settings.set_tooltip_text("Settings"); btn_settings.connect("clicked", self._open_settings); header.pack_end(btn_settings)
        
        main_box.append(header)
        
        self.main_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_paned.set_vexpand(True); self.main_paned.set_hexpand(True); self.main_paned.set_shrink_start_child(True); self.main_paned.set_shrink_end_child(False); self.main_paned.set_resize_start_child(True); self.main_paned.set_resize_end_child(True)
        self.file_panel = FilePanel(self._on_file_selected, self._load_project, self._on_file_created, self._on_file_imported)
        self.main_paned.set_start_child(self.file_panel); self.main_paned.set_position(280)
        
        self.workspace_paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.workspace_paned.set_vexpand(True); self.workspace_paned.set_hexpand(True); self.workspace_paned.set_shrink_start_child(False); self.workspace_paned.set_shrink_end_child(False); self.workspace_paned.set_resize_start_child(True); self.workspace_paned.set_resize_end_child(True)
        
        self.content_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.content_paned.set_shrink_start_child(False); self.content_paned.set_shrink_end_child(False); self.content_paned.set_resize_start_child(True); self.content_paned.set_resize_end_child(False)
        
        # Initialisation du moteur IA
        self.ai_engine = BlockAIEngine(
            config_getter=lambda: self.config,
            log_callback=lambda msg: self.terminal_panel._log(msg)
        )
        
        self.editor_view = BlockEditorView(
            self._show_toast,
            self._run_python_file,
            get_config_cb=lambda: self.config,
            ai_engine=self.ai_engine # Injection
        )
        self.content_paned.set_start_child(self.editor_view); self.content_paned.set_position(800)
        
        self.terminal_panel = TerminalPanel(get_project_root=lambda: self.project_root, get_config=lambda: self.config, show_toast=self._show_toast)
        self.control_panel = ControlPanel(get_project_root=lambda: self.project_root, get_config=lambda: self.config, show_toast=self._show_toast, terminal_panel=self.terminal_panel)
        self.ctrl_scroll = Gtk.ScrolledWindow(); self.ctrl_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC); self.ctrl_scroll.set_hexpand(True); self.ctrl_scroll.set_vexpand(True); self.ctrl_scroll.set_child(self.control_panel)
        self.content_paned.set_end_child(self.ctrl_scroll)
        
        self.workspace_paned.set_start_child(self.content_paned); self.workspace_paned.set_end_child(self.terminal_panel); self.workspace_paned.set_position(600)
        self.main_paned.set_end_child(self.workspace_paned)
        
        main_box.append(self.main_paned)
        self.toast_overlay.set_child(main_box); self.win.set_content(self.toast_overlay)
        self._apply_theme()
        
        self.left_visible, self.right_visible, self.terminal_visible = True, True, True
        self._left_pos, self._right_pos, self._terminal_pos = 280, 800, 600
        
        last = self.config.get("last_project", "")
        if last and Path(last).exists(): self._load_project(Path(last))
        elif len(sys.argv) > 1 and Path(sys.argv[1]).exists(): self._load_project(Path(sys.argv[1]))
        
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

    def _load_project(self, path: Path):
        self.project_root = path; self.config["last_project"] = str(path)
        add_recent_project(str(path), self.config); self.config = load_config()
        self.file_panel.load_project(path, self.config); self.win.set_title(f"Gykhamine Studio — {path.name}")
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
