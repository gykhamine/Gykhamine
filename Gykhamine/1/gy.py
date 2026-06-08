#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║           GYKHAMINE STUDIO — v2.6.1 (Full Stack Integrated)║
║     No-code visual editor for Gykhamine capsules         ║
║     Developed for the GCI project — Brazzaville, Congo   ║
╚══════════════════════════════════════════════════════════╝
Dependencies : python3-gi, gtk4, libadwaita-1, zipfile, pandas, openpyxl
Launch       : python3 gy.py
"""
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk, Pango
import os, sys, re, subprocess, threading, shutil, json, webbrowser, socket, zipfile, sqlite3
from pathlib import Path
from datetime import datetime

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
VERSION  = "2.6.1"
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
    "pg_device":         "/dev/sda3",
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
    colors = {
        "keyword": ("#c678dd", Pango.Weight.BOLD), "type": ("#e5c07b", Pango.Weight.NORMAL),
        "function": ("#61afef", Pango.Weight.NORMAL), "variable": ("#e06c75", Pango.Weight.NORMAL),
        "string": ("#98c379", Pango.Weight.NORMAL), "comment": ("#5c6370", Pango.Weight.NORMAL, True),
        "number": ("#d19a66", Pango.Weight.NORMAL), "tag": ("#e06c75", Pango.Weight.NORMAL),
        "attr": ("#d19a66", Pango.Weight.NORMAL), "jinja": ("#c678dd", Pango.Weight.BOLD),
        "preproc": ("#56b6c2", Pango.Weight.NORMAL),
    }
    for name, props in colors.items():
        tag = Gtk.TextTag(name=name)
        tag.set_property("foreground", props[0])
        if len(props) > 1 and props[1] != Pango.Weight.NORMAL: tag.set_property("weight", props[1])
        if len(props) > 2 and props[2]: tag.set_property("style", Pango.Style.ITALIC)
        if not tag_table.lookup(name): tag_table.add(tag)
    
    for tag_name in colors.keys(): buf.remove_tag_by_name(tag_name, buf.get_start_iter(), buf.get_end_iter())
    
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
        current_lines, current_start = [], i

    while i < len(lines):
        line = lines[i]; stripped = line.strip()
        m = re.match(r'\{%-?\s*block\s+(\w+).*?%\}', stripped, re.IGNORECASE)
        if m: flush(); current_type, current_name, current_start = "django_block", f"block: {m.group(1)}", i; current_lines.append(line); i += 1; continue
        if re.match(r'\{%-?\s*endblock\b', stripped, re.IGNORECASE): current_lines.append(line); flush(); current_type, current_name, current_start = "template_part", "Template", i + 1; i += 1; continue
        if re.match(r'<style(\s[^>]*)?>$', stripped, re.IGNORECASE): flush(); current_type, current_name, current_start = "style", "CSS Block (<style>)", i; current_lines.append(line); i += 1; continue
        if re.match(r'</style\s*>', stripped, re.IGNORECASE): current_lines.append(line); flush(); current_type, current_name, current_start = "template_part", "Template", i + 1; i += 1; continue
        if re.match(r'<script(\s[^>]*)?>$', stripped, re.IGNORECASE): flush(); current_type, current_name, current_start = "script", "JS Block (<script>)", i; current_lines.append(line); i += 1; continue
        if re.match(r'</script\s*>', stripped, re.IGNORECASE): current_lines.append(line); flush(); current_type, current_name, current_start = "template_part", "Template", i + 1; i += 1; continue
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
#  WIDGETS
# ═══════════════════════════════════════════════════════════════════════
TYPE_ICONS = {"import": "📦", "class": "🏛", "function": "⚡", "separator": "─", "comment": "💬", "other": "▪", "template": "🌐", "template_part": "🌐", "django_block": "🧩", "style": "🎨", "style_rule": "🎨", "script": "⚙️", "script_block": "⚡", "c_block": "⚙️"}

class BlockCard(Gtk.Box):
    def __init__(self, block: dict, on_save_cb, on_delete_cb, on_copy_cb, file_ext):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.block, self.on_save_cb, self.on_delete_cb, self.on_copy_cb, self.file_ext = block, on_save_cb, on_delete_cb, on_copy_cb, file_ext
        self.expanded = False
        self.add_css_class("block-card")
        self.lang = self.file_ext.replace('.', '')
        if self.block["type"] == "style": self.lang = "css"
        elif self.block["type"] == "script": self.lang = "js"
        elif self.block["type"] in ("django_block", "template_part"): self.lang = "jinja"
        self._build_header(); self._build_editor()

    def _build_header(self):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        set_margins(header, 8); header.set_margin_start(12)
        header.append(Gtk.Label(label=TYPE_ICONS.get(self.block["type"], "▪"), css_classes=["block-icon"]))
        badge = Gtk.Label(label=self.block["type"].upper()); badge.add_css_class("block-badge"); badge.add_css_class(f"badge-{self.block['type']}"); header.append(badge)
        lbl_name = Gtk.Label(label=self.block["name"]); lbl_name.set_ellipsize(Pango.EllipsizeMode.END); lbl_name.set_hexpand(True); lbl_name.set_xalign(0); lbl_name.set_max_width_chars(40); lbl_name.add_css_class("block-name"); header.append(lbl_name)
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

    def _toggle_hidden_files(self, *_):
        self.show_hidden = not self.show_hidden
        if self.show_hidden: self.btn_hidden.set_label("👁"); self.btn_hidden.set_tooltip_text("Masquer les fichiers cachés")
        else: self.btn_hidden.set_label("🙈"); self.btn_hidden.set_tooltip_text("Afficher les fichiers cachés")
        if self.project_root: self.load_project(self.project_root, load_config())

    def _on_tree_cell_data(self, column, cell, model, tree_iter, data):
        name = model.get_value(tree_iter, 0); is_folder = model.get_value(tree_iter, 2)
        if is_folder:
            cell.set_property("weight", Pango.Weight.BOLD); cell.set_property("text", f"📁 {name}"); cell.set_property("foreground", "#888888" if name.startswith('.') else "#e0e0e0")
        else:
            cell.set_property("weight", Pango.Weight.NORMAL)
            ext = Path(name).suffix.lower() if '.' in name else ""; icon, color = "📄", "#888888" if name.startswith('.') else "#e0e0e0"
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

    def _populate_tree(self, directory: Path, parent_iter):
        try:
            entries = []
            for entry in directory.iterdir():
                if entry.name in ["__pycache__", "venv", "node_modules", ".git"]: continue
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
        header.append(Gtk.Label(label="🖥 Terminal", css_classes=["terminal-title"]))
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
        pg_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        btn_init = Gtk.Button(label="🔧 1. Initialiser (initdb & mount)"); btn_init.add_css_class("ctrl-btn"); btn_init.set_hexpand(True); btn_init.connect("clicked", self._run_pg_initdb); pg_box.append(btn_init)
        btn_create = Gtk.Button(label="➕ 2. Créer Base & Utilisateur"); btn_create.add_css_class("ctrl-btn"); btn_create.set_hexpand(True); btn_create.connect("clicked", self._run_pg_creatdb); pg_box.append(btn_create)
        btn_start = Gtk.Button(label="🚀 3. Démarrer & Configurer IP"); btn_start.add_css_class("ctrl-btn"); btn_start.set_hexpand(True); btn_start.connect("clicked", self._run_pg_rundb); pg_box.append(btn_start)
        btn_stop = Gtk.Button(label="🛑 4. Arrêter la Base de données"); btn_stop.add_css_class("ctrl-btn-warn"); btn_stop.set_hexpand(True); btn_stop.connect("clicked", self._run_pg_stopdb); pg_box.append(btn_stop)
        self.append(pg_box)
        # ============================================

        # === GESTION REDIS ===
        sep_redis = Gtk.Separator(); sep_redis.set_margin_top(8); sep_redis.set_margin_bottom(4); self.append(sep_redis)
        lbl_redis = Gtk.Label(label="🔴 Gestion Redis"); lbl_redis.add_css_class("control-section-title"); lbl_redis.set_xalign(0); self.append(lbl_redis)
        self._add_custom_service_row("redis", "▶ Démarrer Redis", self._run_redis_start, self._run_redis_stop)
        # ============================================

        # === GESTION NFS SERVEUR ===
        sep_nfs_s = Gtk.Separator(); sep_nfs_s.set_margin_top(8); sep_nfs_s.set_margin_bottom(4); self.append(sep_nfs_s)
        lbl_nfs_s = Gtk.Label(label="📁 NFS Serveur"); lbl_nfs_s.add_css_class("control-section-title"); lbl_nfs_s.set_xalign(0); self.append(lbl_nfs_s)
        self._add_custom_service_row("nfs_server", "▶ Démarrer Serveur", self._run_nfs_server_start, self._run_nfs_server_stop)
        # ============================================

        # === GESTION NFS CLIENT ===
        sep_nfs_c = Gtk.Separator(); sep_nfs_c.set_margin_top(8); sep_nfs_c.set_margin_bottom(4); self.append(sep_nfs_c)
        lbl_nfs_c = Gtk.Label(label="💻 NFS Client"); lbl_nfs_c.add_css_class("control-section-title"); lbl_nfs_c.set_xalign(0); self.append(lbl_nfs_c)
        self._add_custom_service_row("nfs_client", "📥 Monter le partage", self._run_nfs_client_mount, self._run_nfs_client_umount)
        # ============================================
        
        sep2 = Gtk.Separator(); sep2.set_margin_top(8); sep2.set_margin_bottom(4); self.append(sep2)
        lbl3 = Gtk.Label(label="💊 Gykhamine Capsule"); lbl3.add_css_class("control-section-title"); lbl3.set_xalign(0); self.append(lbl3)
        row_cap = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        for label, path, sudo in [("🔑 /1/gy.py", "Gykhamine/1/gy.py", True), ("👤 /2/gy.py", "Gykhamine/2/gy.py", False)]:
            btn = Gtk.Button(label=f"Run {label}"); btn.add_css_class("ctrl-btn-warn" if sudo else "ctrl-btn"); btn.connect("clicked", lambda *_: self._run_gy(path, sudo)); row_cap.append(btn)
        self.append(row_cap)
        
        sep3 = Gtk.Separator(); sep3.set_margin_top(8); sep3.set_margin_bottom(4); self.append(sep3)
        lbl4 = Gtk.Label(label="🤖 AI (llama.cpp)"); lbl4.add_css_class("control-section-title"); lbl4.set_xalign(0); self.append(lbl4)
        self._add_service_row("llama", "▶ Run llama-server", self._start_llama, self._stop_service_factory("llama"))
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
        """Variante pour les services système (Redis/NFS) qui ne sont pas gérés par subprocess.Popen direct"""
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
        terminals = [("gnome-terminal", "--"), ("konsole", "-e"), ("xfce4-terminal", "-x"), ("alacritty", "-e"), ("kitty", "-e"), ("xterm", "-e"), ("x-terminal-emulator", "-e")]
        term_cmd, exec_flag = None, "-e"
        for t, flag in terminals:
            if shutil.which(t): term_cmd, exec_flag = t, flag; break
        if not term_cmd: return self.terminal._log("❌ Aucun émulateur de terminal trouvé.")
        full_cmd = f"{sys.executable} {mp.name} {command}"
        self.terminal._log(f"🖥 Ouverture d'un terminal externe pour: {full_cmd}")
        try: subprocess.Popen([term_cmd, exec_flag, full_cmd], cwd=str(mp.parent))
        except Exception as e: self.terminal._log(f"❌ Échec de l'ouverture du terminal: {e}")

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

    # ═══════════════════════════════════════════════════════════════════════
    #  GESTION POSTGRESQL INTÉGRÉE
    # ═══════════════════════════════════════════════════════════════════════
    def _run_pg_initdb(self, *_):
        cfg = self.get_config()
        device = cfg.get("pg_device", "/dev/sda3")
        mount_point = cfg.get("pg_mount_point", "/var/lib/pgsql/data")
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
        device = cfg.get("pg_device", "/dev/sda3")
        pgdata = cfg.get("pg_mount_point", "/var/lib/pgsql/data")
        bind_ip = cfg.get("pg_bind_ip", "127.0.0.1")
        listen_addr = "*" if bind_ip == "0.0.0.0" else bind_ip
        
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
            except subprocess.CalledProcessError as e:
                GLib.idle_add(self.terminal._log, f"❌ Erreur lors de l'arrêt: {e}")
                GLib.idle_add(self.show_toast, "❌ Échec de l'arrêt")
            except Exception as e:
                GLib.idle_add(self.terminal._log, f"❌ Exception: {e}")
        threading.Thread(target=_thread, daemon=True).start()

    # ═══════════════════════════════════════════════════════════════════════
    #  GESTION REDIS INTÉGRÉE
    # ═══════════════════════════════════════════════════════════════════════
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

    # ═══════════════════════════════════════════════════════════════════════
    #  GESTION NFS INTÉGRÉE
    # ═══════════════════════════════════════════════════════════════════════
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

    # ═══════════════════════════════════════════════════════════════════════
    #  VISUALISATION DES DONNÉES ET EXPORT (TABLEAU RÉEL)
    # ═══════════════════════════════════════════════════════════════════════
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

    def _start_llama(self, *_):
        cfg = self.get_config(); server, model, host, port = cfg.get("llama_server_path", "llama-server"), cfg.get("llama_model_path", ""), cfg.get("llama_host", "127.0.0.1"), cfg.get("llama_port", "8080")
        if not model: return self.terminal._log("❌ Model not configured")
        if not shutil.which(server) and not Path(server).exists(): return self.terminal._log(f"❌ llama-server not found")
        if is_port_in_use(int(port), host):
            new_port = find_free_port(int(port) + 1, int(port) + 10, host)
            if new_port: port = str(new_port); self.terminal._log(f"🔄 Alternative port {port}")
            else: return self.terminal._log("❌ No alternative port")
        self.terminal._log(f"🤖 llama-server → {host}:{port}")
        self._run_cmd([server, "-m", model, "--host", host, "--port", port], name="llama")
        if cfg.get("open_browser_on_run", True): GLib.timeout_add_seconds(3, lambda: self._open_browser_url(f"http://{host}:{port}"))

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

class BlockEditorView(Gtk.Box):
    def __init__(self, toast_cb, run_file_cb, get_config_cb=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.toast_cb, self.run_file_cb, self._get_config_cb = toast_cb, run_file_cb, get_config_cb
        self.current_file, self.blocks, self._cards, self.css_file, self.file_ext = None, [], [], None, "py"
        self.undo_stack, self.redo_stack, self.max_history = [], [], 20
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
        btn_add = Gtk.Button(label="➕ Add block"); btn_add.add_css_class("ctrl-btn-start"); btn_add.connect("clicked", self._add_block_dialog); bar.append(btn_add)
        for label, cb in [("↩ Undo", self._undo), ("↪ Redo", self._redo), ("⬇ Expand all", self._expand_all), ("⬆ Collapse all", self._collapse_all)]:
            btn = Gtk.Button(label=label); btn.add_css_class("toolbar-btn"); btn.connect("clicked", cb); bar.append(btn)
        btn_run = Gtk.Button(label="▶ Run"); btn_run.add_css_class("ctrl-btn-start"); btn_run.connect("clicked", lambda *_: self._run_current_file()); bar.append(btn_run)
        self.btn_css = Gtk.Button(label="🎨 Edit associated CSS"); self.btn_css.add_css_class("toolbar-btn"); self.btn_css.set_visible(False); self.btn_css.connect("clicked", self._open_linked_css); bar.append(self.btn_css)
        btn_save = Gtk.Button(label="💾 Save"); btn_save.add_css_class("save-file-btn"); btn_save.connect("clicked", self._save_file); bar.append(btn_save)
        self.append(bar); self.append(Gtk.Separator())

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

    def _open_linked_css(self, *_):
        if self.css_file and self.css_file.exists(): self._save_file(); self.load_file(self.css_file); self.toast_cb(f"🎨 {self.css_file.name}")

    def _render_blocks(self):
        while child := self.blocks_box.get_first_child(): self.blocks_box.remove(child)
        self.lbl_count.set_text(str(len(self.blocks))); self._cards = []
        for block in self.blocks:
            card = BlockCard(block, self._on_block_save, self._on_block_delete, self._on_block_copy, self.file_ext)
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
        
        # === Groupe PostgreSQL ===
        grp_pg = Adw.PreferencesGroup(title="🐘 Base de données (PostgreSQL)")
        page.add(grp_pg)
        pg_rows = [
            ("pg_device", "Périphérique de la partition", "/dev/sda3"),
            ("pg_mount_point", "Point de montage", "/var/lib/pgsql/data"),
            ("pg_db_name", "Nom de la base de données", "ma_base"),
            ("pg_db_user", "Nom d'utilisateur PostgreSQL", "mon_user"),
            ("pg_db_password", "Mot de passe PostgreSQL", "mot_de_passe"),
        ]
        for key, title, placeholder in pg_rows:
            row = Adw.EntryRow(title=title)
            row.set_text(str(config.get(key, placeholder)))
            self._rows[key] = row
            grp_pg.add(row)
        bind_row = Adw.ComboRow(title="Adresse d'écoute (IP)")
        bind_row.set_model(Gtk.StringList.new(["127.0.0.1 (Local uniquement)", "0.0.0.0 (Réseau / Externe)"]))
        bind_row.set_selected(0 if config.get("pg_bind_ip", "127.0.0.1") == "127.0.0.1" else 1)
        self._rows["pg_bind_ip"] = bind_row
        grp_pg.add(bind_row)
        # ========================================

        # === Groupe Redis ===
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
        # ========================================

        # === Groupe NFS Serveur ===
        grp_nfs_s = Adw.PreferencesGroup(title="📁 NFS Serveur")
        page.add(grp_nfs_s)
        nfs_s_mode_row = Adw.ComboRow(title="Mode d'accès")
        nfs_s_mode_row.set_model(Gtk.StringList.new(["Local (127.0.0.1)", "Réseau (ex: 192.168.1.0/24)"]))
        nfs_s_mode_row.set_selected(0 if config.get("nfs_server_mode", "local") == "local" else 1)
        self._rows["nfs_server_mode"] = nfs_s_mode_row; grp_nfs_s.add(nfs_s_mode_row)
        
        for key, title, placeholder in [("nfs_export_dir", "Dossier à exporter", "/run/media/gykhamine/GY/gy/media"), ("nfs_lan_network", "Réseau autorisé (si mode Réseau)", "192.168.1.0/24")]:
            row = Adw.EntryRow(title=title); row.set_text(str(config.get(key, placeholder))); self._rows[key] = row; grp_nfs_s.add(row)
        # ========================================

        # === Groupe NFS Client ===
        grp_nfs_c = Adw.PreferencesGroup(title="💻 NFS Client")
        page.add(grp_nfs_c)
        for key, title, placeholder in [("nfs_client_server_ip", "IP du serveur NFS", "192.168.1.10"), ("nfs_client_export_dir", "Dossier exporté sur le serveur", "/srv/nfs"), ("nfs_client_mount_point", "Point de montage local", str(Path.home() / "nfs_mount"))]:
            row = Adw.EntryRow(title=title); row.set_text(str(config.get(key, placeholder))); self._rows[key] = row; grp_nfs_c.add(row)
        # ========================================
        
        grp_about = Adw.PreferencesGroup(title="ℹ️ About"); page.add(grp_about)
        version_row = Adw.ActionRow(title="Version", subtitle=f"Gykhamine Studio v{VERSION}"); version_row.set_icon_name("dialog-information-symbolic"); grp_about.add(version_row)
        btn = Gtk.Button(label="💾 Save"); btn.add_css_class("suggested-action"); btn.connect("clicked", self._do_save)
        grp_save = Adw.PreferencesGroup(); page.add(grp_save); grp_save.add(btn)

    def _do_save(self, *_):
        for key, row in self._rows.items():
            if isinstance(row, Adw.EntryRow): self.config[key] = row.get_text()
            elif isinstance(row, Adw.SwitchRow): self.config[key] = row.get_active()
            elif isinstance(row, Adw.ComboRow):
                if key == "theme":
                    self.config["theme"] = "dark" if row.get_selected() == 0 else "light"
                elif key == "pg_bind_ip":
                    self.config["pg_bind_ip"] = "127.0.0.1" if row.get_selected() == 0 else "0.0.0.0"
                elif key == "redis_mode":
                    self.config["redis_mode"] = "local" if row.get_selected() == 0 else "network"
                    self.config["redis_ip"] = "127.0.0.1" if row.get_selected() == 0 else "0.0.0.0"
                elif key == "nfs_server_mode":
                    self.config["nfs_server_mode"] = "local" if row.get_selected() == 0 else "network"
            elif hasattr(row, "get_text"): self.config[key] = row.get_text()
        try:
            self.config["default_port_range_start"] = int(self.config.get("default_port_range_start", 8000))
            self.config["default_port_range_end"] = int(self.config.get("default_port_range_end", 8010))
        except: pass
        self.on_save(self.config); self.close()

CSS = """
/* ── Base ────────────────────────────────────────────────────────── */
window { background-color: #0d0d0d; color: #e0e0e0; }
/* ── Panel titles ────────────────────────────────────────────────── */
.panel-title, .control-section-title { font-size: 11px; font-weight: bold; color: #aaa; text-transform: uppercase; min-width: 0; }
/* ── File list ───────────────────────────────────────────────────── */
.file-item { font-size: 11px; font-family: monospace; min-width: 0; }
.file-category { font-size: 10px; color: #888; min-width: 0; }
.file-category:hover { color: #ccc; }
.block-name { font-size: 11px; font-family: monospace; min-width: 0; }
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
.block-action-btn { font-size: 10px; background: transparent; border: 1px solid #2a2a2a; border-radius: 4px; padding: 2px 5px; min-width: 0; }
.block-action-btn:hover { background-color: #1e1e1e; }
/* ── Code editor ─────────────────────────────────────────────────── */
.code-editor { font-family: monospace; font-size: 11px; background-color: #0a0a0a; color: #e0e0e0; min-width: 0; }
/* ── Save buttons ────────────────────────────────────────────────── */
.save-btn, .save-file-btn { background-color: #1a4a2a; color: #2ecc71; border: 1px solid #2ecc71; border-radius: 4px; min-width: 0; }
.cancel-btn { background-color: #2a1a1a; color: #e74c3c; border: 1px solid #e74c3c; border-radius: 4px; min-width: 0; }
/* ── Control panel buttons ───────────────────────────────────────── */
.ctrl-btn, .ctrl-btn-small, .toolbar-btn { background-color: #1a1a2a; border: 1px solid #333; border-radius: 4px; font-size: 10px; padding: 3px 6px; min-width: 0; }
.ctrl-btn-start { background-color: #0a2a0a; color: #2ecc71; border-color: #2ecc71; border-radius: 4px; font-size: 10px; padding: 3px 6px; min-width: 0; }
.ctrl-btn-stop { background-color: #2a0a0a; color: #e74c3c; border-color: #e74c3c; border-radius: 4px; font-size: 10px; padding: 3px 6px; min-width: 0; }
.ctrl-btn-warn { background-color: #2a1f0a; color: #f39c12; border-color: #f39c12; border-radius: 4px; font-size: 10px; padding: 3px 6px; min-width: 0; }
/* ── Status indicators ───────────────────────────────────────────── */
.status-dot-off { color: #333; }
.status-dot-on  { color: #2ecc71; }
/* ── Terminal Panel ──────────────────────────────────────────────── */
.terminal-panel { background-color: #1e1e1e; border-top: 1px solid #3c3c3c; }
.terminal-title { font-size: 11px; font-weight: bold; color: #ccc; text-transform: uppercase; }
.log-view { font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 12px; background-color: transparent; color: #d4d4d4; padding: 8px; min-width: 0; }
.terminal-prompt { color: #2ecc71; font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace; font-weight: bold; font-size: 12px; margin-right: 4px; }
.terminal-input { background-color: #2d2d2d; color: #d4d4d4; border: 1px solid #3c3c3c; border-radius: 4px; font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 12px; padding: 4px 8px; }
.terminal-input:focus { border-color: #007acc; outline: none; }
/* ── Editor toolbar ──────────────────────────────────────────────── */
.toolbar-label { font-size: 11px; color: #888; min-width: 0; }
.block-count-badge { font-size: 10px; font-weight: bold; background-color: #1a1a2a; color: #61afef; border-radius: 4px; padding: 1px 6px; min-width: 0; }
.editor-file-label { font-size: 12px; font-weight: bold; min-width: 0; }
/* ── Bottom accent bar of cards ──────────────────────────────────── */
.block-accent-bar { min-height: 2px; min-width: 0; }
.accent-function, .accent-script_block { background-color: #9b59b6; }
.accent-class { background-color: #3498db; }
.accent-import, .accent-style { background-color: #2980b9; }
.accent-django_block { background-color: #e67e22; }
.accent-script, .accent-c_block { background-color: #f1c40f; }
.accent-separator { background-color: #333; }
.accent-other, .accent-template_part { background-color: #222; }
/* ── Light theme ─────────────────────────────────────────────────── */
.theme-light window { background-color: #f5f5f5; color: #222; }
.theme-light .block-card { background-color: #ffffff; border-color: #ddd; }
.theme-light .code-editor { background-color: #fafafa; color: #222; }
.theme-light .log-view { background-color: #f0f0f0; color: #1a6a1a; }
.theme-light .ctrl-btn, .theme-light .toolbar-btn { background-color: #e8e8f0; border-color: #ccc; color: #222; }
.theme-light .terminal-panel { background-color: #ffffff; border-color: #ccc; }
.theme-light .terminal-input { background-color: #f5f5f5; color: #222; border-color: #ccc; }
.theme-light .terminal-prompt { color: #2ecc71; }
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
        self.editor_view = BlockEditorView(self._show_toast, self._run_python_file, get_config_cb=lambda: self.config)
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
