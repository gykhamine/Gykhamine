"""Module généré automatiquement depuis widgets.py - Classe TabButton"""
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


