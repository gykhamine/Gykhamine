#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║           GYKHAMINE STUDIO — v2.5.3                      ║
║     No-code visual editor for Gykhamine capsules         ║
║     Developed for the GCI project — Brazzaville, Congo   ║
╚══════════════════════════════════════════════════════════╝
Dependencies : python3-gi, gtk4, libadwaita-1, zipfile
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
VERSION  = "2.5.3"
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
            if label_override: 
                btype, bname = "separator", label_override
            elif re.match(r'^(import|from)\s+', stripped): 
                btype, bname = "import", stripped.splitlines()[0][:60]
            elif re.match(r'^class\s+(\w+)', stripped): 
                btype, bname = "class", re.match(r'^class\s+(\w+)', stripped).group(1)
            elif re.search(r'\bdef\s+(\w+)\s*\(', stripped): 
                btype, bname = "function", re.search(r'\bdef\s+(\w+)\s*\(', stripped).group(1)
            elif stripped.startswith("#"): 
                btype, bname = "comment", stripped[:60]
            else: 
                btype, bname = "other", stripped[:40] if stripped else "bloc"
            blocks.append({"type": btype, "name": bname, "code": raw, "start": current_start, "end": current_start + len(current_lines) - 1})
        current_lines, current_start = [], i

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # 1. Gestion des séparateurs visuels (####, ----, etc.)
        if SEPARATOR_RE.match(stripped):
            flush()
            blocks.append({"type": "separator", "name": stripped.strip("#/-").strip() or "Séparateur", "code": line, "start": i, "end": i})
            current_start = i + 1
            i += 1
            continue
            
        # 2. Détection d'un début de bloc racine (décorateur, classe, fonction, ou commentaire racine)
        # Un bloc racine commence obligatoirement à la colonne 0 (pas d'indentation)
        is_root_block_start = not line.startswith((" ", "\t")) and (
            stripped.startswith("@") or 
            re.match(r'^(async\s+)?def\s+\w+', stripped) or 
            re.match(r'^class\s+\w+', stripped) or 
            stripped.startswith("#")
        )
        
        if is_root_block_start:
            flush()
            current_start = i
            
            # Étape A : Capturer TOUS les décorateurs consécutifs (@...)
            while i < len(lines) and lines[i].strip().startswith("@"):
                current_lines.append(lines[i])
                i += 1
                
            # Étape B : Capturer la définition (class ou def) qui suit obligatoirement les décorateurs
            if i < len(lines):
                current_lines.append(lines[i])
                i += 1
                
                # Étape C : Capturer tout le corps indenté de la fonction/classe
                while i < len(lines):
                    l = lines[i]
                    # Si la ligne est vide ou indentée, elle fait partie du bloc
                    if l.strip() == "" or l.startswith((" ", "\t")):
                        current_lines.append(l)
                        i += 1
                    # Si on retombe sur un autre bloc racine (colonne 0), on arrête la capture du corps
                    elif not l.startswith((" ", "\t")) and (l.strip().startswith("@") or re.match(r'^(async\s+)?def\s+\w+', l.strip()) or re.match(r'^class\s+\w+', l.strip()) or l.strip().startswith("#")):
                        break
                    else:
                        # Sécurité : inclure les lignes mal formatées pour ne pas perdre de code
                        current_lines.append(l)
                        i += 1
            flush()
            continue
            
        # 3. Ligne normale (fait partie du bloc en cours ou regroupe les imports/autres)
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
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True); scroll.set_hexpand(True)
        textview = Gtk.TextView()
        textview.set_monospace(True); textview.set_editable(True); textview.set_wrap_mode(Gtk.WrapMode.WORD)
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
        btn2 = Gtk.Button(label="Close")
        btn2.connect("clicked", lambda *_: dialog.destroy())
        btn_box.append(btn2)
        btn3 = Gtk.Button(label="💾 Save and Close", css_classes=["suggested-action"])
        btn3.connect("clicked", lambda *_: self._save_from_popup(textview, dialog))
        btn_box.append(btn3)
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
        # TreeStore: (nom_affiché, chemin_complet, est_dossier)
        self.tree_store = Gtk.TreeStore(str, str, bool)
        self.show_hidden = False # État pour afficher les fichiers cachés
        
        # Header
        lbl = Gtk.Label(label="📁 Projet")
        lbl.add_css_class("panel-title")
        lbl.set_xalign(0)
        lbl.set_margin_start(12)
        lbl.set_margin_top(10)
        lbl.set_margin_bottom(6)
        self.append(lbl)
        self.append(Gtk.Separator())

        # Stack pour basculer entre Fichiers et Récents
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)

        # --- VUE ARBORESCENTE (TREE VIEW) ---
        scroll_files = Gtk.ScrolledWindow()
        scroll_files.set_vexpand(True)
        scroll_files.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.tree_view = Gtk.TreeView(model=self.tree_store)
        self.tree_view.set_headers_visible(False)
        self.tree_view.add_css_class("file-tree-view")
        
        # Colonne avec rendu personnalisé pour les icônes
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Fichiers", renderer, text=0)
        column.set_cell_data_func(renderer, self._on_tree_cell_data)
        self.tree_view.append_column(column)
        
        # Signal natif et fiable pour l'activation (clic/double-clic)
        self.tree_view.connect("row-activated", self._on_row_activated)
        
        scroll_files.set_child(self.tree_view)

        # --- VUE RECENTS (LISTE SIMPLE) ---
        scroll_projs = Gtk.ScrolledWindow()
        scroll_projs.set_vexpand(True)
        scroll_projs.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.recent_list = Gtk.ListBox()
        self.recent_list.add_css_class("file-list")
        self.recent_list.connect("row-activated", self._on_project_selected)
        scroll_projs.set_child(self.recent_list)

        self.stack.add_named(scroll_files, "files")
        self.stack.add_named(scroll_projs, "recent")
        self.append(self.stack)

        # Barre de navigation
        nav_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        set_margins(nav_bar, 6)
        nav_bar.set_margin_start(8)
        nav_bar.set_margin_end(8)
        
        btn_files = Gtk.Button(label="📄")
        btn_files.set_tooltip_text("Fichiers")
        btn_files.add_css_class("flat")
        btn_files.set_hexpand(True)
        btn_files.connect("clicked", lambda *_: self.stack.set_visible_child_name("files"))
        
        btn_recent = Gtk.Button(label="🕒")
        btn_recent.set_tooltip_text("Récents")
        btn_recent.add_css_class("flat")
        btn_recent.set_hexpand(True)
        btn_recent.connect("clicked", lambda *_: self.stack.set_visible_child_name("recent"))
        
        btn_new = Gtk.Button(label="➕")
        btn_new.set_tooltip_text("Nouveau fichier")
        btn_new.add_css_class("flat")
        btn_new.set_hexpand(True)
        btn_new.connect("clicked", self._create_new_file)
        
        btn_import = Gtk.Button(label="📥")
        btn_import.set_tooltip_text("Importer")
        btn_import.add_css_class("flat")
        btn_import.set_hexpand(True)
        btn_import.connect("clicked", self._import_file)

        # Bouton pour afficher/masquer les fichiers cachés
        self.btn_hidden = Gtk.Button(label="🙈")
        self.btn_hidden.set_tooltip_text("Afficher les fichiers cachés")
        self.btn_hidden.add_css_class("flat")
        self.btn_hidden.connect("clicked", self._toggle_hidden_files)

        nav_bar.append(btn_files)
        nav_bar.append(btn_recent)
        nav_bar.append(btn_new)
        nav_bar.append(btn_import)
        nav_bar.append(self.btn_hidden)
        
        self.append(nav_bar)

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
        name = model.get_value(tree_iter, 0)
        is_folder = model.get_value(tree_iter, 2)
        
        if is_folder:
            cell.set_property("weight", Pango.Weight.BOLD)
            cell.set_property("text", f"📁 {name}")
            cell.set_property("foreground", "#888888" if name.startswith('.') else "#e0e0e0")
        else:
            cell.set_property("weight", Pango.Weight.NORMAL)
            ext = Path(name).suffix.lower() if '.' in name else ""
            icon = "📄"
            color = "#888888" if name.startswith('.') else "#e0e0e0"

            if name in ("settings.py", "manage.py"): icon = "⚙"
            elif name == "views.py": icon = "👁"
            elif name == "models.py": icon = "🗄"
            elif ext == '.css': icon = "🎨"
            elif ext == '.js': icon = "⚡"
            elif ext in ('.c', '.cpp', '.h'): icon = "⚙️"
            elif ext == '.sh': icon = "📜"
            elif ext in ('.html', '.jinja', '.jinja2'): icon = "🌐"
            
            cell.set_property("text", f"  {icon} {name}")
            cell.set_property("foreground", color)

    def _on_row_activated(self, treeview, path, column):
        """Gère l'ouverture des fichiers ou l'expansion des dossiers de manière fiable"""
        model = treeview.get_model()
        tree_iter = model.get_iter(path)
        full_path = model.get_value(tree_iter, 1)
        is_folder = model.get_value(tree_iter, 2)
        
        if is_folder:
            if treeview.row_expanded(path):
                treeview.collapse_row(path)
            else:
                treeview.expand_row(path, False)
        else:
            if Path(full_path).exists():
                self.on_file_select(Path(full_path))

    def load_project(self, root: Path, config: dict):
        self.project_root = root
        self.tree_store.clear()
        self._populate_tree(root, None)
        self._load_recent_projects(config)

    def _populate_tree(self, directory: Path, parent_iter):
        """Remplit l'arbre récursivement"""
        try:
            entries = []
            for entry in directory.iterdir():
                # Ignorer les dossiers systèmes standards
                if entry.name in ["__pycache__", "venv", "node_modules", ".git"]:
                    continue
                # Ignorer les fichiers/dossiers cachés si l'option est désactivée
                if not self.show_hidden and entry.name.startswith('.'):
                    continue
                entries.append(entry)

            # Trier : Dossiers d'abord, puis fichiers, alphabétiquement
            entries.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
            
            for entry in entries:
                is_folder = entry.is_dir()
                new_iter = self.tree_store.append(parent_iter, [entry.name, str(entry), is_folder])
                if is_folder:
                    self._populate_tree(entry, new_iter)
        except PermissionError:
            pass

    def _load_recent_projects(self, config):
        while child := self.recent_list.get_first_child(): 
            self.recent_list.remove(child)
        
        for proj_path in get_recent_projects(config):
            path = Path(proj_path)
            if path.exists():
                row = Gtk.ListBoxRow()
                row._project_path = path
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
        if hasattr(row, "_project_path"): 
            self.on_project_select(row._project_path)

    def _create_new_file(self, *_):
        if not self.project_root: 
            return self._show_error("Aucun projet ouvert")
        
        dialog = Gtk.Dialog(title="Nouveau fichier", transient_for=self.get_root())
        dialog.set_default_size(400, 250)
        content = dialog.get_content_area()
        content.set_spacing(8)
        set_margins(content, 12)
        
        content.append(Gtk.Label(label="Nom du fichier (avec extension):", xalign=0))
        entry = Gtk.Entry()
        entry.set_placeholder_text("ex: style.css, script.js, main.c")
        content.append(entry)
        
        content.append(Gtk.Label(label="Contenu initial (optionnel):", xalign=0, margin_top=8))
        text_buf = Gtk.TextBuffer()
        text_view = Gtk.TextView.new_with_buffer(text_buf)
        text_view.set_size_request(-1, 100)
        scroll = Gtk.ScrolledWindow()
        scroll.set_child(text_view)
        content.append(scroll)
        
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_cancel = Gtk.Button(label="Annuler")
        btn_create = Gtk.Button(label="✅ Créer")
        btn_create.add_css_class("suggested-action")
        btn_box.append(btn_cancel)
        btn_box.append(btn_create)
        content.append(btn_box)
        
        def on_create(*_):
            filename = entry.get_text().strip()
            if not filename: 
                return self._show_error("Nom requis")
            
            filepath = self.project_root / filename
            if filepath.exists(): 
                return self._show_error(f"{filename} existe déjà")
            
            text = text_buf.get_text(text_buf.get_start_iter(), text_buf.get_end_iter(), True) or f"# {filename}\n# Créé avec Gykhamine Studio\n"
            filepath.write_text(text, encoding='utf-8')
            
            self.on_file_created(filepath)
            self.load_project(self.project_root, load_config())
            dialog.destroy()
            
        btn_create.connect("clicked", on_create)
        btn_cancel.connect("clicked", lambda *_: dialog.destroy())
        dialog.present()

    def _import_file(self, *_):
        if not self.project_root: 
            return self._show_error("Aucun projet ouvert")
        Gtk.FileDialog(title="Importer un fichier").open(self.get_root(), None, self._on_import_selected)

    def _on_import_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                src = Path(file.get_path())
                dst = self.project_root / src.name
                if dst.exists() and Gtk.MessageDialog(
                    transient_for=self.get_root(), 
                    flags=0, 
                    message_type=Gtk.MessageType.WARNING, 
                    buttons=Gtk.ButtonsType.YES_NO, 
                    text="Fichier existant", 
                    secondary_text=f"{dst.name} existe. Écraser ?"
                ).run() != Gtk.ResponseType.YES: 
                    return
                
                shutil.copy2(src, dst)
                self.on_file_imported(dst)
                self.load_project(self.project_root, load_config())
        except Exception as e: 
            self._show_error(f"Erreur: {e}")

    def _show_error(self, msg: str): 
        self.get_root().get_child().add_toast(Adw.Toast(title=msg, timeout=3))        
        
class TerminalPanel(Gtk.Box):
    def __init__(self, get_project_root, get_config, show_toast):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.get_project_root, self.get_config, self.show_toast = get_project_root, get_config, show_toast
        self.add_css_class("terminal-panel")
        self._build()

    def _build(self):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_start(8); header.set_margin_end(8); header.set_margin_top(4); header.set_margin_bottom(4)
        header.append(Gtk.Label(label="🖥 Terminal", css_classes=["terminal-title"]))
        spacer = Gtk.Box(); spacer.set_hexpand(True); header.append(spacer)
        btn_clear = Gtk.Button(label="🗑 Clear"); btn_clear.add_css_class("ctrl-btn-small"); btn_clear.connect("clicked", lambda *_: self.log_view.get_buffer().set_text(""))
        header.append(btn_clear)
        self.append(header); self.append(Gtk.Separator())
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

# ═══════════════════════════════════════════════════════════════════════
#  CONTROL PANEL (RIGHT) - BUTTON NAMES PRESERVED
# ═══════════════════════════════════════════════════════════════════════
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
        for label, cb in [("🔍 Check", self._check_ports), ("🔫 Kill port", self._kill_port_dialog)]:
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
            btn = Gtk.Button(label=label); btn.add_css_class("ctrl-btn"); btn.connect("clicked", lambda _, c=cmd: self._run_manage_command(c)); grid.attach(btn, idx % 3, idx // 3, 1, 1)
        self.append(grid)
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

    def _run_cmd(self, cmd: list, cwd=None, name=None, shell=False):
        def _thread():
            try:
                env = os.environ.copy(); env["PYTHONUNBUFFERED"] = "1"; env["PYTHONDONTWRITEBYTECODE"] = "1"; env["DJANGO_COLORS"] = "nocolor"
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
        mp = self._manage_path()
        if not mp: return
        self.terminal._log(f"▶ python {mp.name} {command}")
        self._run_cmd([sys.executable, str(mp), command], cwd=str(mp.parent))

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
    def _open_browser_url(self, url): webbrowser.open(url); self.terminal._log(f"🌐 {url}"); return False

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
        self.current_file = path
        self.file_label.set_text(f"📄  {path.name}")
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
            row = Adw.EntryRow(title=title)
            row.set_text(str(config.get(key, placeholder)))
            self._rows[key] = row
            grp.add(row)
        grp_ports = Adw.PreferencesGroup(title="🔌 Ports & Servers"); page.add(grp_ports)
        auto_port = Adw.SwitchRow(title="Auto-detect free ports"); auto_port.set_active(config.get("auto_find_free_port", True)); self._rows["auto_find_free_port"] = auto_port; grp_ports.add(auto_port)
        for key, title, default in [("default_port_range_start", "Range start", 8000), ("default_port_range_end", "Range end", 8010)]:
            row = Adw.EntryRow(title=title)
            row.set_text(str(config.get(key, default)))
            self._rows[key] = row
            grp_ports.add(row)
        gunicorn_row = Adw.EntryRow(title="Gunicorn bind address")
        gunicorn_row.set_text(str(config.get("gunicorn_bind", "0.0.0.0:8000")))
        gunicorn_row.set_tooltip_text("e.g., 0.0.0.0:8000, 0.0.0.0:80 or 0.0.0.0:443")
        self._rows["gunicorn_bind"] = gunicorn_row; grp_ports.add(gunicorn_row)
        grp2 = Adw.PreferencesGroup(title="🌐 Options"); page.add(grp2)
        browser_switch = Adw.SwitchRow(title="Open browser automatically"); browser_switch.set_active(config.get("open_browser_on_run", True)); self._rows["open_browser_on_run"] = browser_switch; grp2.add(browser_switch)
        theme_row = Adw.ComboRow(title="Theme"); theme_row.set_model(Gtk.StringList.new(["Dark", "Light"])); theme_row.set_selected(0 if config.get("theme", "dark") == "dark" else 1); self._rows["theme"] = theme_row; grp2.add(theme_row)
        grp_paths = Adw.PreferencesGroup(title="📁 File Paths"); page.add(grp_paths)
        log_row = DirectoryPickerRow(title="Log file (.log)", subtitle="Destination folder for logs", initial_value=config.get("log_file_path", DEFAULT_CONFIG["log_file_path"]), filename="studio.log")
        self._rows["log_file_path"] = log_row; grp_paths.add(log_row)
        db_row = DirectoryPickerRow(title="SQLite database (.db)", subtitle="Destination folder for the database", initial_value=config.get("db_path", DEFAULT_CONFIG["db_path"]), filename="gykhamine_studio.db")
        self._rows["db_path"] = db_row; grp_paths.add(db_row)
        grp_about = Adw.PreferencesGroup(title="ℹ️ About"); page.add(grp_about)
        version_row = Adw.ActionRow(title="Version", subtitle=f"Gykhamine Studio v{VERSION}"); version_row.set_icon_name("dialog-information-symbolic"); grp_about.add(version_row)
        btn = Gtk.Button(label="💾 Save"); btn.add_css_class("suggested-action"); btn.connect("clicked", self._do_save)
        grp_save = Adw.PreferencesGroup(); page.add(grp_save); grp_save.add(btn)

    def _do_save(self, *_):
        for key, row in self._rows.items():
            if isinstance(row, Adw.EntryRow): self.config[key] = row.get_text()
            elif isinstance(row, Adw.SwitchRow): self.config[key] = row.get_active()
            elif isinstance(row, Adw.ComboRow): self.config["theme"] = "dark" if row.get_selected() == 0 else "light"
            elif hasattr(row, "get_text"): self.config[key] = row.get_text()
        try:
            self.config["default_port_range_start"] = int(self.config.get("default_port_range_start", 8000))
            self.config["default_port_range_end"] = int(self.config.get("default_port_range_end", 8010))
        except: pass
        self.on_save(self.config); self.close()

# CORRECTION: Removed "box-sizing" and "cursor" not supported by GTK4
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
        btn_settings = Gtk.Button(icon_name="preferences-system-symbolic")
        btn_settings.set_tooltip_text("Settings")
        btn_settings.connect("clicked", self._open_settings)
        header.pack_end(btn_settings)
        main_box.append(header)
        
        # 1. Main horizontal pane (Left vs Rest)
        self.main_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_paned.set_vexpand(True); self.main_paned.set_hexpand(True)
        self.main_paned.set_shrink_start_child(True)
        self.main_paned.set_shrink_end_child(False)
        self.main_paned.set_resize_start_child(True)
        self.main_paned.set_resize_end_child(True)
        self.file_panel = FilePanel(self._on_file_selected, self._load_project, self._on_file_created, self._on_file_imported)
        self.main_paned.set_start_child(self.file_panel)
        self.main_paned.set_position(280)
        
        # 2. Workspace vertical pane (Top: Editor+Control vs Bottom: Terminal)
        self.workspace_paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.workspace_paned.set_vexpand(True); self.workspace_paned.set_hexpand(True)
        self.workspace_paned.set_shrink_start_child(False)
        self.workspace_paned.set_shrink_end_child(False)
        self.workspace_paned.set_resize_start_child(True)
        self.workspace_paned.set_resize_end_child(True)
        
        # 3. Content horizontal pane (Editor vs Control Panel)
        self.content_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.content_paned.set_shrink_start_child(False)
        self.content_paned.set_shrink_end_child(False)
        self.content_paned.set_resize_start_child(True)
        self.content_paned.set_resize_end_child(False)
        self.editor_view = BlockEditorView(self._show_toast, self._run_python_file, get_config_cb=lambda: self.config)
        self.content_paned.set_start_child(self.editor_view)
        self.content_paned.set_position(800)
        self.terminal_panel = TerminalPanel(get_project_root=lambda: self.project_root, get_config=lambda: self.config, show_toast=self._show_toast)
        self.control_panel = ControlPanel(get_project_root=lambda: self.project_root, get_config=lambda: self.config, show_toast=self._show_toast, terminal_panel=self.terminal_panel)
        self.ctrl_scroll = Gtk.ScrolledWindow(); self.ctrl_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.ctrl_scroll.set_hexpand(True); self.ctrl_scroll.set_vexpand(True); self.ctrl_scroll.set_child(self.control_panel)
        self.content_paned.set_end_child(self.ctrl_scroll)
        
        # Hierarchy assembly
        self.workspace_paned.set_start_child(self.content_paned)
        self.workspace_paned.set_end_child(self.terminal_panel)
        self.workspace_paned.set_position(600)
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
            self.file_panel.set_visible(True)
            GLib.idle_add(lambda: self.main_paned.set_position(self._left_pos) and False)
            self.btn_toggle_left.set_label("☰")
        else:
            self._left_pos = self.main_paned.get_position()
            self.main_paned.set_position(0)
            self.btn_toggle_left.set_label("▶")

    def _toggle_right_panel(self, *_):
        self.right_visible = not self.right_visible
        if self.right_visible:
            self.content_paned.set_end_child(self.ctrl_scroll)
            GLib.idle_add(lambda: self.content_paned.set_position(self._right_pos) or False)
            self.btn_toggle_right.set_label("⚙")
        else:
            self._right_pos = self.content_paned.get_position()
            self.content_paned.set_end_child(None)
            self.btn_toggle_right.set_label("◀")

    def _toggle_terminal_panel(self, *_):
        self.terminal_visible = not self.terminal_visible
        if self.terminal_visible:
            self.terminal_panel.set_visible(True)
            GLib.idle_add(lambda: self.workspace_paned.set_position(self._terminal_pos) and False)
            self.btn_toggle_terminal.set_label("🖥")
        else:
            self._terminal_pos = self.workspace_paned.get_position()
            self.terminal_panel.set_visible(False)
            GLib.idle_add(lambda: self.workspace_paned.set_position(10000) and False)
            self.btn_toggle_terminal.set_label("⌨")

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
        if self.config.get("theme", "dark") == "light":
            self.win.add_css_class("theme-light")
        else:
            self.win.remove_css_class("theme-light")

    def _show_toast(self, msg: str):
        self.toast_overlay.add_toast(Adw.Toast(title=msg, timeout=2))

if __name__ == "__main__":
    app = GykhamineStudioApp()
    sys.exit(app.run(sys.argv))
