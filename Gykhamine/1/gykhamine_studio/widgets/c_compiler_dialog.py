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
from ..config import global_log, DEFAULT_CONFIG, VERSION, set_margins, enable_window_controls
from ..parser import parse_blocks
from ..ai_engine import BlockAIEngine, AIModificationDialog, LlamaSetupDialog, LogAnalyzerDialog, AICmdGeneratorDialog, GitManagerDialog, BusinessProcessDialog, _ChatView
from ..terminal_tty import NativeTtyTerminal
from ..database import load_config, save_config, memory_record, add_recent_project, get_recent_projects, is_port_in_use, find_free_port, kill_process_on_port, _get_db_path, log_to_file, get_cached_process, save_process_to_cache

#  WIDGETS
# ═══════════════════════════════════════════════════════════════════════
TYPE_ICONS = {"import": "📦", "class": "🏛", "function": "⚡", "separator": "─", "comment": "💬", "other": "▪", "template": "🌐", "template_part": "🌐", "django_block": "🧩", "style": "🎨", "style_rule": "🎨", "script": "⚙️", "script_block": "⚡", "c_block": "⚙️"}



class CCompilerDialog(Gtk.Dialog):
    def __init__(self, parent, get_config, terminal_log_cb, get_project_root_cb=None, initial_code=None, default_filename=None, get_c_blocks_cb=None):
        super().__init__(title="🛠️ Compilateur C/C++ & Optimiseur", transient_for=parent, default_width=880, default_height=800)
        self.add_css_class("rounded-dialog")
        enable_window_controls(self, "🛠️ Compilateur C/C++ & Optimiseur")
        self.get_config = get_config
        self.terminal_log = terminal_log_cb
        self.get_project_root_cb = get_project_root_cb
        # Callback optionnel fourni par l'éditeur de blocs : renvoie la liste
        # des blocs de type "c_block" du fichier actuellement ouvert, pour
        # pouvoir en charger un directement depuis le Compilateur, sans avoir
        # à repartir de l'éditeur pour chaque bloc.
        self.get_c_blocks_cb = get_c_blocks_cb
        self.current_output_file = None
        self.ai_engine = BlockAIEngine(config_getter=self.get_config, log_callback=self.terminal_log)
        
        outer_content = self.get_content_area()
        outer_content.set_spacing(0)
        # Contenu défilable : l'éditeur de code, la sortie de compilation et le
        # chat IA ne se disputent plus une hauteur fixe de fenêtre — on peut
        # toujours descendre pour atteindre le bas, et le code reste lisible.
        _scroller = Gtk.ScrolledWindow()
        _scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        _scroller.set_vexpand(True)
        _scroller.set_hexpand(True)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        set_margins(content, 16)
        _scroller.set_child(content)
        outer_content.append(_scroller)
        
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.append(Gtk.Label(label="Code Source C/C++", css_classes=["heading"], xalign=0))

        btn_open = Gtk.Button(label="📂 Ouvrir")
        btn_open.set_tooltip_text("Charger un bloc de code C depuis l'éditeur de blocs")
        btn_open.connect("clicked", self._on_open_from_editor)
        header_box.append(btn_open)

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

        # Destination : dossier (relatif au projet) + nom de fichier — valables pour
        # les deux compilateurs (gcc ou g++, choisis automatiquement selon le code).
        dest_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        dest_box.append(Gtk.Label(label="Dossier:", xalign=0))
        self.entry_folder = Gtk.Entry()
        self.entry_folder.set_text("build_c")
        self.entry_folder.set_tooltip_text("Sous-dossier (créé si besoin) dans le projet courant")
        self.entry_folder.set_hexpand(True)
        dest_box.append(self.entry_folder)
        dest_box.append(Gtk.Label(label="Fichier:", xalign=0))
        self.entry_filename = Gtk.Entry()
        self.entry_filename.set_text(default_filename or "gy_c")
        self.entry_filename.set_tooltip_text("Nom du fichier, sans extension")
        self.entry_filename.set_hexpand(True)
        dest_box.append(self.entry_filename)
        content.append(dest_box)

        content.append(Gtk.Separator())
        
        self.scrolled = Gtk.ScrolledWindow()
        # Pas de vexpand ici : ce ScrolledWindow est déjà à l'intérieur d'un
        # autre ScrolledWindow (_scroller) qui gère lui-même le défilement de
        # toute la boîte de dialogue. Un vexpand=True imbriqué faisait gonfler
        # l'éditeur de code bien au-delà de son contenu réel (grand espace
        # vide sous le code), la fenêtre paraissant "plus grande que la zone
        # de texte" : on fixe simplement une hauteur confortable et fixe.
        self.scrolled.set_vexpand(False)
        self.scrolled.set_size_request(-1, 320)
        self.text_view = GtkSource.View()
        self.text_view.set_monospace(True)
        self.text_view.set_wrap_mode(Gtk.WrapMode.NONE)
        self.text_view.set_show_line_numbers(True)
        self.text_view.set_highlight_current_line(True)
        self.text_view.add_css_class("code-editor")
        
        self.buf_c = GtkSource.Buffer()
        lang_c = GtkSource.LanguageManager.get_default().get_language("c")
        if lang_c: self.buf_c.set_language(lang_c)
        self.buf_c.set_text(initial_code if initial_code is not None else "// Collez votre code C ici\n#include <stdio.h>\nint main() {\nprintf(\"Hello from Gykhamine!\\n\");\nreturn 0;\n}")
        self.text_view.set_buffer(self.buf_c)
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

        # Assistant IA du compilateur : même fil de conversation (bulles + saisie en
        # bas) que l'Analyseur de Logs et l'Élaborateur, pour que toute interaction
        # avec l'IA — édition de bloc, logs, processus métier, C/C++ — se ressemble.
        content.append(Gtk.Label(label="🤖 Assistant IA (optimisation C/C++) :", xalign=0, css_classes=["heading"], margin_top=6))
        self.ai_chat = _ChatView(
            placeholder="Ex: Vectoriser la boucle de calcul, réduire la mémoire, paralléliser avec OpenMP…",
            on_send=self._on_ai_chat_send,
        )
        self.ai_chat.set_vexpand(False)
        self.ai_chat.set_size_request(-1, 160)
        content.append(self.ai_chat)
        self.ai_chat.add_message(
            "Décrivez l'optimisation souhaitée sur le code C/C++ ci-dessus, puis envoyez "
            "(ou laissez vide pour une optimisation générale avec Eigen3).",
            sender="ai", label="🛠️ Compilateur"
        )
        


    def _on_open_from_editor(self, button):
        if not self.get_c_blocks_cb:
            self._log("⚠️ Aucun éditeur de blocs relié à ce Compilateur (ouvert hors contexte).")
            return
        blocks = [b for b in (self.get_c_blocks_cb() or []) if b.get("type") == "c_block"]
        if not blocks:
            self._log("⚠️ Aucun bloc de code C trouvé dans le fichier ouvert dans l'éditeur de blocs.")
            return

        popover = Gtk.Popover()
        popover.set_parent(button)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        set_margins(box, 8)
        box.append(Gtk.Label(label="Blocs C disponibles :", xalign=0, css_classes=["dim-label"]))

        scroll = Gtk.ScrolledWindow()
        scroll.set_size_request(320, min(260, 40 * len(blocks) + 10))
        list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        for b in blocks:
            name = b.get("name") or "(sans nom)"
            btn = Gtk.Button(label=name)
            btn.set_halign(Gtk.Align.FILL)
            btn.get_child().set_xalign(0)

            def _on_pick(_btn, block=b):
                self.buf_c.set_text(block.get("code", ""))
                safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", block.get("name", "") or "gy_c") or "gy_c"
                self.entry_filename.set_text(safe_name)
                self._log(f"📂 Bloc « {block.get('name', '?')} » chargé depuis l'éditeur de blocs.")
                popover.popdown()

            btn.connect("clicked", _on_pick)
            list_box.append(btn)
        scroll.set_child(list_box)
        box.append(scroll)
        popover.set_child(box)
        popover.popup()

    def _log(self, text):
        buf = self.log_view.get_buffer()
        buf.insert(buf.get_end_iter(), f"{text}\n")
        adj = self.log_view.get_parent().get_vadjustment()
        adj.set_value(adj.get_upper())

    def _on_optimize_cpp(self, *_):
        # Le bouton "Optimiser" ne fait plus surgir de popup isolé : il ramène
        # simplement le focus sur le fil de conversation IA en bas de la fenêtre,
        # cohérent avec l'Analyseur de Logs / l'Élaborateur.
        code = self.text_view.get_buffer().get_text(self.text_view.get_buffer().get_start_iter(), self.text_view.get_buffer().get_end_iter(), True)
        if not code.strip():
            self._log("❌ Aucun code à optimiser.")
            return
        self.ai_chat.entry.grab_focus()

    def _on_ai_chat_send(self, message: str):
        buf_c = self.text_view.get_buffer()
        code = buf_c.get_text(buf_c.get_start_iter(), buf_c.get_end_iter(), True)
        if not code.strip():
            self.ai_chat.add_message("⚠️ Aucun code à optimiser dans l'éditeur.", sender="ai", label="🛠️ Compilateur")
            return

        intent = message.strip() or "Optimiser les performances numériques avec Eigen3"
        self.ai_chat.add_message(message if message.strip() else "(Optimisation générale du code C/C++)", sender="user")
        self.ai_chat.set_busy(True)
        self._log("🤖 Génération d'optimisation C++ en cours...")

        def _thread():
            # Clé de cache : les 200 premiers chars du code suffisent à
            # discriminer deux fonctions différentes, et l'intent qualifie
            # la nature de l'optimisation demandée. Comme pour l'Analyseur,
            # on évite de hasher 10k de lignes de code.
            cache_key = f"[cpp_optimize] {code[:200]}|{intent}"
            cached = get_cached_process(cache_key)
            if cached:
                result = cached["json_content"]
                self._log("📂 Optimisation récupérée depuis la DB (Cache)")
            else:
                result = self.ai_engine.process_modification("c_block", code, intent, mode="cpp_optimize")
                if result:
                    save_process_to_cache(cache_key, result, role_type="cpp_optimize")
                    self._log("💾 Optimisation sauvegardée (Cache)")
            if result:
                def _apply():
                    buf_c.set_text(result)
                    self.ai_chat.add_message("✅ Code optimisé généré et appliqué dans l'éditeur.", sender="ai", label="🛠️ Compilateur",
                                              intent_key=cache_key, cache_type="process")
                    self._log("✅ Code optimisé généré.")
                    self.ai_chat.set_busy(False)
                GLib.idle_add(_apply)
            else:
                def _fail():
                    self.ai_chat.add_message("❌ Échec de la génération d'optimisation.", sender="ai", label="🛠️ Compilateur")
                    self._log("❌ Échec de la génération d'optimisation.")
                    self.ai_chat.set_busy(False)
                GLib.idle_add(_fail)

        threading.Thread(target=_thread, daemon=True).start()

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

        # Compilation directement dans le dossier choisi par l'utilisateur, à
        # l'intérieur du projet courant — plus dans /tmp : le livrable reste avec
        # le projet et l'explorateur le voit. Valable pour gcc comme pour g++.
        project_root = self.get_project_root_cb() if self.get_project_root_cb else None
        folder_name = (self.entry_folder.get_text().strip() or "build_c").strip("/")
        base_name = re.sub(r"[^a-zA-Z0-9_\-.]", "_", self.entry_filename.get_text().strip() or "gy_c")
        if project_root:
            build_dir = Path(project_root) / folder_name
            build_dir.mkdir(parents=True, exist_ok=True)
            src_path = str(build_dir / f"{base_name}{suffix}")
            with open(src_path, 'w') as f:
                f.write(code)
        else:
            self._log("⚠️ Aucun projet ouvert : compilation dans un dossier temporaire.")
            fd, src_path = tempfile.mkstemp(prefix=f"{base_name}_", suffix=suffix)
            with os.fdopen(fd, 'w') as f:
                f.write(code)

        try:
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
                if project_root:
                    self._log(f"📂 Disponible dans le projet : build_c/{Path(out_path).name}")
                else:
                    self._log(f"💡 Vous pouvez le trouver dans le dossier temporaire ou le déplacer.")
            else:
                self._log(f"❌ Erreur de compilation:")
                self._log(proc.stderr)
        finally:
            # Nettoyage du fichier source temporaire si besoin, 
            # mais on le laisse souvent pour déboguer si ça échoue
            pass


