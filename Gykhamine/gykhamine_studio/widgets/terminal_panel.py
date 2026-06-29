"""Module généré automatiquement depuis widgets.py - Classe TerminalPanel"""
"""Module généré automatiquement depuis gy.py"""
import os, sys, re, subprocess, threading, shutil, json, zipfile, csv, tempfile
from pathlib import Path
from datetime import datetime
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk, Pango, GtkSource
from ..config import global_log, DEFAULT_CONFIG, VERSION, set_margins
from ..parser import parse_blocks
from ..ai_engine import BlockAIEngine, AIModificationDialog, LlamaSetupDialog, LogAnalyzerDialog, AICmdGeneratorDialog, GitManagerDialog, BusinessProcessDialog
from ..terminal_tty import NativeTtyTerminal
from ..database import load_config, save_config, memory_record, add_recent_project, get_recent_projects, is_port_in_use, find_free_port, kill_process_on_port, _get_db_path, log_to_file

#  WIDGETS
# ═══════════════════════════════════════════════════════════════════════
TYPE_ICONS = {"import": "📦", "class": "🏛", "function": "⚡", "separator": "─", "comment": "💬", "other": "▪", "template": "🌐", "template_part": "🌐", "django_block": "🧩", "style": "🎨", "style_rule": "🎨", "script": "⚙️", "script_block": "⚡", "c_block": "⚙️"}



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


