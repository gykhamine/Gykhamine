"""Module généré automatiquement depuis widgets.py - Classe CCompilerDialog"""
"""Module généré automatiquement depuis gy.py"""
import os, sys, re, subprocess, threading, shutil, json, zipfile, csv, tempfile
from pathlib import Path
from datetime import datetime
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk, Pango, GtkSource
from ..config import global_log, DEFAULT_CONFIG, VERSION, set_margins, apply_dark_source_scheme
from ..parser import parse_blocks
from ..ai_engine import BlockAIEngine, AIModificationDialog, LlamaSetupDialog, LogAnalyzerDialog, AICmdGeneratorDialog, GitManagerDialog, BusinessProcessDialog
from ..terminal_tty import NativeTtyTerminal
from ..database import load_config, save_config, memory_record, add_recent_project, get_recent_projects, is_port_in_use, find_free_port, kill_process_on_port, _get_db_path, log_to_file

#  WIDGETS
# ═══════════════════════════════════════════════════════════════════════
TYPE_ICONS = {"import": "📦", "class": "🏛", "function": "⚡", "separator": "─", "comment": "💬", "other": "▪", "template": "🌐", "template_part": "🌐", "django_block": "🧩", "style": "🎨", "style_rule": "🎨", "script": "⚙️", "script_block": "⚡", "c_block": "⚙️"}



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
        apply_dark_source_scheme(buf_c)
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


