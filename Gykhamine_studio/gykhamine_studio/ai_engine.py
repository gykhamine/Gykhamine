"""Module généré automatiquement depuis gy.py"""
import re, requests, threading
from pathlib import Path
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("GtkSource", "5")
from gi.repository import Gtk, GLib, Gdk, GtkSource
from .config import global_log, set_margins
from .database import get_cached_block, save_block_to_cache, get_cached_command, save_command_to_cache, get_cached_process, save_process_to_cache

#  AI ENGINE & MODIFICATION DIALOG
# ═══════════════════════════════════════════════════════════════════════
class BlockAIEngine:
    def __init__(self, config_getter, log_callback):
        self.get_config = config_getter
        self.log = log_callback

# Dans la classe BlockAIEngine, remplacez les méthodes _build_prompt et process_modification par :

    def _build_prompt(self, block_type, current_code, user_intent, context_deps="", mode="modify", custom_role=None):
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
            "business_process": "Tu es un expert algorithmique de processus métier Django. Tu sais décomposer un problème complexe en tâches techniques précises et ordonnées.",
            "other": "Tu es un assistant de codage polyvalent."
        }
        # Utilisation du rôle personnalisé s'il est fourni, sinon fallback sur le rôle par défaut
        role = custom_role if custom_role else roles.get(block_type, roles["other"])
        
        if mode == "contextual_modify":
            format_instruction = "RÈGLE ABSOLUE : Réponds UNIQUEMENT par le code du bloc cible modifié. Pas de markdown, pas de texte."
        elif mode == "cpp_optimize":
            format_instruction = "RÈGLE ABSOLUE : Génère DU CODE C++ pur. Pas de markdown, pas de texte."
        elif mode == "terminal_gen":
            format_instruction = "RÈGLE ABSOLUE : Réponds UNIQUEMENT par la commande shell exacte. Pas d'explication, pas de markdown."
        elif mode == "log_analysis":
            format_instruction = """RÈGLE ABSOLUE (JSON STRICT) :
1. Analyse les logs fournis.
2. Réponds UNIQUEMENT avec un objet JSON valide.
3. N'ajoute AUCUN texte explicatif, AUCUNE balise markdown (interdiction formelle de ```json).
4. Format JSON attendu : {"erreur": "Description courte", "cause": "Explication technique", "solution": "Commande ou action concrète", "severite": "critique/moyen/faible"}"""
        elif mode == "business_process":
            format_instruction = """RÈGLE ABSOLUE (JSON STRICT) :
1. Tu dois générer UNIQUEMENT une réponse structurée en JSON selon les instructions spécifiques de ton rôle.
2. N'ajoute AUCUN texte explicatif, AUCUNE balise markdown (interdiction formelle de ```json).
3. Respecte scrupuleusement le format JSON demandé dans ta description de rôle."""
        else:
            format_instruction = "RÈGLE ABSOLUE : Ne réponds QUE par le code modifié ou la réponse demandée. N'ajoute AUCUN texte explicatif superflu."
            
        prompt = f"""{role}
CONTEXTE SUPPLÉMENTAIRE : {context_deps if context_deps else "Aucune dépendance externe majeure."}
CODE ACTUEL / CONTEXTE :
{current_code}
DEMANDE : "{user_intent}"
OBJECTIF : {format_instruction}
"""
        return prompt

    def _clean_json_output(self, text: str) -> str:
        """
        Extrait STRICTEMENT le JSON entre les backticks.
        Si pas de backticks -> Réponse non admise.
        """
        if not text: return "{}"
        
        # Recherche du bloc ```json ... ``` ou ``` ... ```
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        
        if match:
            content = match.group(1).strip()
            # Vérification basique que c'est bien du JSON
            if content.startswith('{') or content.startswith('['):
                return content
        
        # Si on arrive ici, c'est qu'il n'y a pas de backticks ou pas de JSON valide dedans
        return "FORMAT NON AUTORISÉ : L'IA doit renvoyer le JSON entre des balises ```json ... ```"

    def _clean_code_output(self, text, block_type):
        """
        Extrait STRICTEMENT le code entre les backticks.
        Si pas de backticks -> Réponse non admise.
        """
        if not text: return ""
        
        # Recherche du bloc ```lang ... ```
        match = re.search(r'```[a-zA-Z]*\s*([\s\S]*?)\s*```', text)
        
        if match:
            return match.group(1).strip()
        
        # Si on arrive ici, c'est qu'il n'y a pas de backticks
        return "FORMAT NON AUTORISÉ : L'IA doit renvoyer le code entre des balises ```... ```"

    def process_modification(self, block_type, current_code, user_intent, context_deps="", mode="modify", custom_role=None):
        cfg = self.get_config()
        host = cfg.get("llama_host", "127.0.0.1")
        port = cfg.get("llama_port", 8080)
        url = f"http://{host}:{port}/v1/chat/completions"
        
        # Passage du custom_role au prompt builder
        prompt = self._build_prompt(block_type, current_code, user_intent, context_deps, mode=mode, custom_role=custom_role)
        
        payload = {
            "model": "qwen2.5-coder",
            "messages": [
                {"role": "system", "content": "Tu es un moteur de génération de code strict. Tu ne parles pas, tu codes."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "top_p": 0.9,
            "max_tokens": 2048,
            "stream": False
        }
        try:
            self.log(f"🤖 Envoi de la requête IA ({mode})...")
            response = requests.post(url, json=payload, timeout=12000)
            if response.status_code == 200:
                data = response.json()
                raw_content = data['choices'][0]['message']['content']
                # Utilisation du bon nettoyeur selon le mode
                if mode in ["log_analysis", "business_process"]:
                    cleaned_code = self._clean_json_output(raw_content)
                else:
                    cleaned_code = self._clean_code_output(raw_content, block_type if mode != "terminal_gen" else "shell")
                return cleaned_code
            else:
                self.log(f"❌ Erreur API IA: {response.status_code}")
                return None
        except Exception as e:
            self.log(f"❌ Exception connexion IA: {e}")
            return None
            
# --- NOUVEAU : Dialogues pour le Modificateur Contextuel (Version Simplifiée) ---
class AIModificationDialog(Gtk.Dialog):
    def __init__(self, parent, block, ai_engine, on_confirm_cb, project_root=None):
        super().__init__(title=f"✨ Modification IA : {block['name']}", transient_for=parent, default_width=1000, default_height=700)
        self.add_css_class("rounded-dialog")
        self.block = block
        self.ai_engine = ai_engine
        self.on_confirm_cb = on_confirm_cb
        self.project_root = project_root
        self.modified_code = None
        self.context_deps = ""
        
        content = self.get_content_area()
        content.set_spacing(10)
        set_margins(content, 16)
        
        # --- Header avec Switch Auto-Apply ---
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl_type = Gtk.Label(label=f"Type: {block['type'].upper()}", css_classes=["badge-function"], margin_end=10)
        header.append(lbl_type)
        
        spacer = Gtk.Box(hexpand=True)
        header.append(spacer)
        
        self.switch_auto_apply = Gtk.Switch()
        self.switch_auto_apply.set_tooltip_text("Appliquer automatiquement le code généré sans confirmation")
        lbl_auto = Gtk.Label(label="⚡ Auto-Apply", css_classes=["dim-label"])
        
        auto_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        auto_box.append(lbl_auto)
        auto_box.append(self.switch_auto_apply)
        header.append(auto_box)
        
        content.append(header)
        content.append(Gtk.Separator())
        
        # Main Paned (Original vs New)
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_vexpand(True)
        paned.set_hexpand(True)
        paned.set_wide_handle(True)
        
        # Original Code
        box_orig = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box_orig.append(Gtk.Label(label="Code Actuel", xalign=0, css_classes=["dim-label"]))
        scroll_orig = Gtk.ScrolledWindow()
        scroll_orig.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_orig.set_vexpand(True)
        scroll_orig.set_size_request(-1, 400)
        self.view_orig = GtkSource.View()
        self.view_orig.set_editable(False)
        self.view_orig.set_monospace(True)
        self.view_orig.set_show_line_numbers(True)
        self.view_orig.set_highlight_current_line(True)
        
        buf_orig = GtkSource.Buffer()
        lang_mgr = GtkSource.LanguageManager.get_default()
        lang_orig = lang_mgr.get_language(self._get_lang(block['type']))
        if lang_orig: buf_orig.set_language(lang_orig)
        buf_orig.set_text(block['code'])
        self.view_orig.set_buffer(buf_orig)
        scroll_orig.set_child(self.view_orig)
        box_orig.append(scroll_orig)
        
        # New Code
        box_new = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box_new.append(Gtk.Label(label="Proposition IA", xalign=0, css_classes=["dim-label"]))
        scroll_new = Gtk.ScrolledWindow()
        scroll_new.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_new.set_vexpand(True)
        scroll_new.set_size_request(-1, 400)
        self.view_new = GtkSource.View()
        self.view_new.set_editable(False)
        self.view_new.set_monospace(True)
        self.view_new.set_show_line_numbers(True)
        self.view_new.set_highlight_current_line(True)
        
        buf_new = GtkSource.Buffer()
        lang_mgr = GtkSource.LanguageManager.get_default()
        lang_new = lang_mgr.get_language(self._get_lang(self.block['type']))
        if lang_new: buf_new.set_language(lang_new)
        buf_new.set_text("// En attente de génération...")
        self.view_new.set_buffer(buf_new)
        scroll_new.set_child(self.view_new)
        box_new.append(scroll_new)
        
        bottom_action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, halign=Gtk.Align.END)
        btn_reject = Gtk.Button(label="❌ Annuler")
        btn_reject.connect("clicked", lambda *_: self.destroy())
        
        btn_accept = Gtk.Button(label="✅ Conserver", css_classes=["suggested-action"])
        btn_accept.connect("clicked", self._on_accept)
        
        bottom_action_box.append(btn_reject)
        bottom_action_box.append(btn_accept)
        box_new.append(bottom_action_box)
        
        paned.set_start_child(box_orig)
        paned.set_end_child(box_new)
        paned.set_position(500)
        content.append(paned)
        
        content.append(Gtk.Separator())
        
        # Prompt Box
        prompt_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        prompt_box.append(Gtk.Label(label="Instructions pour l'IA (Max 150 mots) :", xalign=0, css_classes=["heading"]))
        scroll_prompt = Gtk.ScrolledWindow()
        scroll_prompt.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_prompt.set_size_request(-1, 120)
        self.intent_entry = Gtk.TextView()
        self.intent_entry.set_wrap_mode(Gtk.WrapMode.WORD)
        self.intent_entry.set_monospace(True)
        scroll_prompt.set_child(self.intent_entry)
        prompt_box.append(scroll_prompt)
        
        action_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_bar.set_halign(Gtk.Align.END)
        
        self.btn_cancel_gen = Gtk.Button(label="Annuler")
        self.btn_cancel_gen.connect("clicked", lambda *_: self.destroy())
        
        self.spinner = Gtk.Spinner()
        self.spinner.set_visible(False)
        
        self.btn_generate = Gtk.Button()
        self.btn_generate.add_css_class("whatsapp-btn")
        self.btn_generate.set_tooltip_text("Envoyer la demande")
        icon = Gtk.Image.new_from_icon_name("mail-send-symbolic")
        self.btn_generate.set_child(icon)
        self.btn_generate.connect("clicked", self._on_generate)
        
        generate_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        generate_box.append(self.spinner)
        generate_box.append(self.btn_generate)
        
        action_bar.append(self.btn_cancel_gen)
        action_bar.append(generate_box)
        prompt_box.append(action_bar)
        content.append(prompt_box)

    def _on_generate(self, *_):
        buf = self.intent_entry.get_buffer()
        intent = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True).strip()
        
        if len(intent.split()) > 150:
            self.ai_engine.log("⚠️ Votre demande dépasse 150 mots.")
            return
        if not intent:
            self.ai_engine.log("⚠️ Veuillez décrire la modification.")
            return
            
        # Construction du contexte (vide car supprimé de l'UI)
        self.context_deps = ""
        
        self.spinner.start()
        self.spinner.set_visible(True)
        self.btn_generate.set_sensitive(False)
        
        threading.Thread(target=self._thread_generate, args=(self.block['type'], intent), daemon=True).start()

    def _thread_generate(self, btype, intent):
        # 1. Vérifier le cache spécifique aux blocs de code
        cached = get_cached_block(intent)
        
        if cached:
            result = cached["content"]
            GLib.idle_add(lambda: self.ai_engine.log(f"📂 Modification récupérée depuis la DB (Cache Code)"))
        else:
            # 2. Appel IA
            result = self.ai_engine.process_modification(btype, self.block['code'], intent, self.context_deps, mode="contextual_modify")
            
            if result:
                save_block_to_cache(intent, result, block_type=btype)
                GLib.idle_add(lambda: self.ai_engine.log(f"💾 Nouvelle modification sauvegardée (Cache Code)"))

        GLib.idle_add(self._update_ui_with_result, result)
        
    def _update_ui_with_result(self, result):
        self.spinner.stop()
        self.spinner.set_visible(False)
        self.btn_generate.set_sensitive(True)
        
        if result:
            self.modified_code = result
            self.view_new.get_buffer().set_text(result)
            self.ai_engine.log("✅ Modification générée.")
            
            # Auto-Apply si activé
            if self.switch_auto_apply.get_active():
                self._on_accept(None)
        else:
            self.ai_engine.log("❌ Échec de la génération ou erreur serveur.")
            self.view_new.get_buffer().set_text("// Erreur lors de la génération.")

    def _on_accept(self, *_):
        if self.modified_code:
            self.on_confirm_cb(self.block, self.modified_code)
            self.destroy()

    def _get_lang(self, btype):
        mapping = {
            "function": "python", "class": "python", "django_model": "python",
            "django_view": "python", "django_form": "python", "django_settings": "python",
            "django_url": "python", "template": "jinja", "javascript": "js",
            "c_block": "c", "shell": "bash", "css": "css"
        }
        return mapping.get(btype, "python")
        
        
        
class LlamaSetupDialog(Gtk.Dialog):
    def __init__(self, parent, config, on_save_and_start):
        super().__init__(title="⚙️ Configuration Llama.cpp (Sudo)", transient_for=parent, default_width=500, default_height=300)
        self.add_css_class("rounded-dialog")
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
        except Exception as e:
            global_log(f"⚠️ Erreur dans gy.py: {type(e).__name__} - {e}")
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
        dlg.add_css_class("rounded-dialog")
        dlg.connect("response", lambda d, _: d.destroy())
        dlg.present()

# ═══════════════════════════════════════════════════════════════════════
#  NOUVEAUX POPUPS TERMINAL (DÉSATURATION)
# ═══════════════════════════════════════════════════════════════════════
class LogAnalyzerDialog(Gtk.Dialog):
    def __init__(self, parent, ai_engine, log_callback):
        super().__init__(title="🔍 Analyseur de Logs IA", transient_for=parent, default_width=700, default_height=600)
        self.add_css_class("rounded-dialog")
        self.ai_engine = ai_engine
        self.log_callback = log_callback
        
        content = self.get_content_area()
        content.set_spacing(12)
        set_margins(content, 16)
        
        content.append(Gtk.Label(label="1. Collez les logs à analyser :", xalign=0, css_classes=["heading"]))
        scroll_logs = Gtk.ScrolledWindow()
        scroll_logs.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_logs.set_size_request(-1, 150)
        self.txt_logs = GtkSource.View()
        self.txt_logs.set_wrap_mode(Gtk.WrapMode.WORD)
        self.txt_logs.set_show_line_numbers(True)
        self.txt_logs.set_monospace(True)
        lang_mgr = GtkSource.LanguageManager.get_default()
        lang_txt = lang_mgr.get_language("txt")
        if lang_txt: self.txt_logs.get_buffer().set_language(lang_txt)
        scroll_logs.set_child(self.txt_logs)
        content.append(scroll_logs)
        
        content.append(Gtk.Label(label="2. Question spécifique (optionnel) :", xalign=0, css_classes=["heading"], margin_top=8))
        self.txt_question = Gtk.Entry()
        self.txt_question.set_placeholder_text("Ex: Pourquoi le serveur plante-t-il ?")
        content.append(self.txt_question)
        
        btn_analyze = Gtk.Button(label="🤖 Analyser les Logs")
        btn_analyze.add_css_class("suggested-action")
        btn_analyze.set_halign(Gtk.Align.END)
        btn_analyze.connect("clicked", self._on_analyze)
        content.append(btn_analyze)
        
        content.append(Gtk.Separator(margin_top=8, margin_bottom=8))
        
        content.append(Gtk.Label(label="3. Résultat de l'analyse :", xalign=0, css_classes=["heading"]))
        scroll_result = Gtk.ScrolledWindow()
        scroll_result.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_result.set_vexpand(True)
        self.txt_result = GtkSource.View()
        self.txt_result.set_editable(False)
        self.txt_result.set_monospace(True)
        self.txt_result.set_wrap_mode(Gtk.WrapMode.WORD)
        self.txt_result.set_show_line_numbers(True)
        self.txt_result.add_css_class("code-editor")
        
        lang_mgr = GtkSource.LanguageManager.get_default()
        lang_json = lang_mgr.get_language("json")
        if lang_json: self.txt_result.get_buffer().set_language(lang_json)
        
        scroll_result.set_child(self.txt_result)
        content.append(scroll_result)
        
        btn_close = Gtk.Button(label="Fermer", margin_top=12)
        btn_close.set_halign(Gtk.Align.END)
        btn_close.connect("clicked", lambda *_: self.destroy())
        content.append(btn_close)

    def _on_analyze(self, *_):
        logs = self.txt_logs.get_buffer().get_text(self.txt_logs.get_buffer().get_start_iter(), self.txt_logs.get_buffer().get_end_iter(), True).strip()
        question = self.txt_question.get_text().strip()
        if not logs:
            self.log_callback("❌ Veuillez coller des logs à analyser.")
            return
        
        intent = f"Analyse ces logs. Question spécifique: {question if question else 'Explique les erreurs et propose une solution.'}"
        self.log_callback("🤖 Analyse des logs en cours (Format JSON strict)...")
        self.txt_result.get_buffer().set_text("Analyse en cours...")
        
        def _thread():
            result = self.ai_engine.process_modification("log_analysis", logs, intent, mode="log_analysis")
            if result:
                clean_json = self.ai_engine._clean_json_output(result)
                GLib.idle_add(lambda: self.txt_result.get_buffer().set_text(clean_json))
                GLib.idle_add(lambda: self.log_callback("📊 ANALYSE IA TERMINÉE (Format JSON)."))
            else:
                GLib.idle_add(lambda: self.txt_result.get_buffer().set_text("❌ Échec de l'analyse IA."))
                GLib.idle_add(lambda: self.log_callback("❌ Échec de l'analyse IA."))
        
        threading.Thread(target=_thread, daemon=True).start()

class AICmdGeneratorDialog(Gtk.Dialog):
    def __init__(self, parent, terminal_panel):
        super().__init__(title="🤖 Générateur de Commandes IA", transient_for=parent, default_width=600, default_height=450)
        self.add_css_class("rounded-dialog")
        self.terminal_panel = terminal_panel
        self.generated_cmd = ""
        self.is_process_mode = False
        
        content = self.get_content_area()
        content.set_spacing(12)
        set_margins(content, 16)
        
        # --- Header avec Switch Auto-Run ---
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.append(Gtk.Label(label="Décrivez l'action :", xalign=0, css_classes=["heading"]))
        
        spacer = Gtk.Box(hexpand=True)
        header_box.append(spacer)
        
        self.switch_auto_run = Gtk.Switch()
        self.switch_auto_run.set_tooltip_text("Exécuter automatiquement la commande trouvée/générée")
        lbl_auto = Gtk.Label(label="⚡ Auto-Run", css_classes=["dim-label"])
        
        auto_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        auto_box.append(lbl_auto)
        auto_box.append(self.switch_auto_run)
        header_box.append(auto_box)
        
        content.append(header_box)
        
        # --- Input avec Placeholder (Correction du bug TextView) ---
        scroll_in = Gtk.ScrolledWindow()
        scroll_in.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_in.set_size_request(-1, 100)
        
        self.txt_input = Gtk.TextView()
        self.txt_input.set_wrap_mode(Gtk.WrapMode.WORD)
        
        # Création du placeholder via Overlay
        overlay = Gtk.Overlay()
        overlay.set_child(self.txt_input)
        
        self.lbl_placeholder = Gtk.Label(
            label="Ex: 'Mettre à jour le système' ou 'Liste: installer git, cloner repo, entrer dans le dossier'",
            xalign=0, yalign=0, margin_start=8, margin_top=8
        )
        self.lbl_placeholder.add_css_class("dim-label")
        overlay.add_overlay(self.lbl_placeholder)
        
        # Gestion de la visibilité du placeholder
        self.txt_input.get_buffer().connect("changed", self._on_input_changed)
        self._on_input_changed(self.txt_input.get_buffer())
        
        scroll_in.set_child(overlay)
        content.append(scroll_in)
        
        # --- Bouton Générer ---
        btn_translate = Gtk.Button(label="🔄 Générer / Chercher")
        btn_translate.add_css_class("suggested-action")
        btn_translate.connect("clicked", self._on_translate)
        content.append(btn_translate)
        
        content.append(Gtk.Label(label="Résultat :", xalign=0, css_classes=["heading"], margin_top=8))
        
        # Zone de résultat plus grande pour les processus
        scroll_res = Gtk.ScrolledWindow()
        scroll_res.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_res.set_size_request(-1, 100)
        self.lbl_result = Gtk.Label(label="$ ...", xalign=0, css_classes=["terminal-prompt"])
        self.lbl_result.set_selectable(True)
        self.lbl_result.set_wrap(True) # Permet le retour à la ligne
        scroll_res.set_child(self.lbl_result)
        content.append(scroll_res)
        
        # --- Actions ---
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, halign=Gtk.Align.END, margin_top=12)
        btn_cancel = Gtk.Button(label="Annuler")
        btn_cancel.connect("clicked", lambda *_: self.destroy())
        
        self.btn_exec = Gtk.Button(label="▶ Exécuter")
        self.btn_exec.add_css_class("ctrl-btn-start")
        self.btn_exec.set_sensitive(False)
        self.btn_exec.connect("clicked", self._on_execute)
        
        action_box.append(btn_cancel)
        action_box.append(self.btn_exec)
        content.append(action_box)

    def _on_input_changed(self, buffer):
        """Gère l'affichage/masquage du placeholder"""
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True).strip()
        if self.lbl_placeholder:
            self.lbl_placeholder.set_visible(len(text) == 0)

    def _on_translate(self, *_):
        intent = self.txt_input.get_buffer().get_text(
            self.txt_input.get_buffer().get_start_iter(), 
            self.txt_input.get_buffer().get_end_iter(), True
        ).strip()
        
        if not intent: 
            self.terminal_panel._log("❌ Veuillez décrire une action.")
            return
            
        self.lbl_result.set_text("Recherche dans le cache...")
        self.btn_exec.set_sensitive(False)
        
        # Détection simple de mode "Processus" (si l'utilisateur utilise des mots clés comme "liste", "puis", "et ensuite")
        process_keywords = ["liste", "processus", "étapes", "puis", "ensuite", "et"]
        self.is_process_mode = any(kw in intent.lower() for kw in process_keywords)

        def _thread():
            # 1. Vérifier le cache
            cached = get_cached_command(intent)
            
            if cached:
                cmd = cached["command"]
                source = "Cache DB ✅"
                GLib.idle_add(lambda: self.terminal_panel._log(f"📂 Commande récupérée depuis la base de données ({source})"))
            else:
                # 2. Si pas dans le cache, appeler l'IA
                GLib.idle_add(lambda: self.lbl_result.set_text("Génération IA en cours..."))
                mode = "terminal_gen"
                # Si c'est un processus, on demande à l'IA de retourner une liste séparée par && ou ;
                if self.is_process_mode:
                    prompt_suffix = " (Retourne une seule ligne de commande chaînée avec && ou ;)"
                else:
                    prompt_suffix = ""
                    
                cmd = self.terminal_panel.ai_engine.process_modification(
                    "shell", "", intent + prompt_suffix, mode="terminal_gen"
                )
                
                if cmd:
                    # Sauvegarder dans le cache
                    save_command_to_cache(intent, cmd, self.is_process_mode)
                    source = "IA 🤖"
                    GLib.idle_add(lambda: self.terminal_panel._log(f"💾 Nouvelle commande générée et sauvegardée ({source})"))
                else:
                    GLib.idle_add(lambda: (
                        self.lbl_result.set_text("❌ Échec de la génération."), 
                        self.btn_exec.set_sensitive(False)
                    ))
                    return

            # Affichage du résultat
            display_cmd = cmd.replace("&&", "\n&& ").replace(";", "\n; ") if self.is_process_mode else cmd
            GLib.idle_add(lambda: (
                self.lbl_result.set_text(f"$ {display_cmd}"), 
                self.btn_exec.set_sensitive(True), 
                setattr(self, 'generated_cmd', cmd)
            ))
            
            # Auto-Run si activé
            if self.switch_auto_run.get_active():
                GLib.idle_add(lambda: self._on_execute(None))

        threading.Thread(target=_thread, daemon=True).start()

    def _on_execute(self, *_):
        if hasattr(self, 'generated_cmd') and self.generated_cmd:
            # Si c'est un processus, on loggue chaque étape
            if self.is_process_mode:
                steps = [s.strip() for s in self.generated_cmd.replace("&&", ";").split(";") if s.strip()]
                self.terminal_panel._log(f"🚀 Lancement du processus ({len(steps)} étapes)...")
            
            self.terminal_panel._run_custom_command_text(self.generated_cmd)
            # On ne ferme pas forcément le dialogue pour voir le résultat
class GitManagerDialog(Gtk.Dialog):
    def __init__(self, parent, project_root, log_callback):
        super().__init__(title="🐙 Mini GitHub Desktop", transient_for=parent, default_width=700, default_height=600)
        self.add_css_class("rounded-dialog")
        self.project_root = project_root
        self.log_callback = log_callback
        # Par défaut, on propose le dossier parent du projet actuel ou le home
        self.current_dir = str(project_root.parent) if project_root else str(Path.home())
        
        content = self.get_content_area()
        content.set_spacing(12)
        set_margins(content, 16)
        
        # --- Section 1: Configuration & Chemin ---
        content.append(Gtk.Label(label="1. Configuration du Dépôt", xalign=0, css_classes=["heading"]))
        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(8)
        grid.attach(Gtk.Label(label="URL du Repo (HTTPS/SSH) :", xalign=0), 0, 0, 1, 1)
        self.entry_url = Gtk.Entry()
        self.entry_url.set_placeholder_text("https://github.com/user/repo.git")
        self.entry_url.set_hexpand(True)
        grid.attach(self.entry_url, 1, 0, 1, 1)
        
        grid.attach(Gtk.Label(label="Chemin local :", xalign=0), 0, 1, 1, 1)
        box_path = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.entry_path = Gtk.Entry()
        self.entry_path.set_text(self.current_dir)
        self.entry_path.set_hexpand(True)
        btn_browse = Gtk.Button(label="📂")
        btn_browse.connect("clicked", self._browse_folder)
        box_path.append(self.entry_path)
        box_path.append(btn_browse)
        grid.attach(box_path, 1, 1, 1, 1)
        content.append(grid)
        
        content.append(Gtk.Separator(margin_top=8, margin_bottom=8))
        
        # --- Section 2: Actions Git ---
        content.append(Gtk.Label(label="2. Actions Git", xalign=0, css_classes=["heading"]))
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_halign(Gtk.Align.CENTER)
        btn_clone = Gtk.Button(label="📥 Cloner")
        btn_clone.add_css_class("suggested-action")
        btn_clone.connect("clicked", lambda *_: self._run_git_command("clone"))
        action_box.append(btn_clone)
        btn_status = Gtk.Button(label="🔍 Status")
        btn_status.connect("clicked", lambda *_: self._run_git_command("status"))
        action_box.append(btn_status)
        btn_add = Gtk.Button(label="➕ Add All")
        btn_add.connect("clicked", lambda *_: self._run_git_command("add"))
        action_box.append(btn_add)
        btn_commit = Gtk.Button(label="💾 Commit & Push")
        btn_commit.add_css_class("ctrl-btn-warn")
        btn_commit.connect("clicked", self._open_commit_dialog)
        action_box.append(btn_commit)
        content.append(action_box)
        
        content.append(Gtk.Separator(margin_top=8, margin_bottom=8))
        
        # --- Section 3: Sortie Git ---
        content.append(Gtk.Label(label="3. Sortie Git", xalign=0, css_classes=["heading"]))
        scroll_log = Gtk.ScrolledWindow()
        scroll_log.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_log.set_vexpand(True)
        self.txt_log = GtkSource.View()
        self.txt_log.set_editable(False)
        self.txt_log.set_monospace(True)
        self.txt_log.set_show_line_numbers(True)
        self.txt_log.add_css_class("log-view")
        
        lang_mgr = GtkSource.LanguageManager.get_default()
        lang_sh = lang_mgr.get_language("sh")
        if lang_sh: self.txt_log.get_buffer().set_language(lang_sh)
        
        scroll_log.set_child(self.txt_log)
        content.append(scroll_log)
        
        btn_close = Gtk.Button(label="Fermer", margin_top=12)
        btn_close.set_halign(Gtk.Align.END)
        btn_close.connect("clicked", lambda *_: self.destroy())
        content.append(btn_close)

    def _browse_folder(self, *_):
        Gtk.FileDialog(title="Choisir le dossier local").select_folder(self.get_root(), None, self._on_folder_selected)

    def _on_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder: self.entry_path.set_text(folder.get_path())
        except Exception as e:
            global_log(f"⚠️ Erreur dans gy.py: {type(e).__name__} - {e}")
    def _log(self, text):
        buf = self.txt_log.get_buffer()
        buf.insert(buf.get_end_iter(), f"$ {text}\n")
        adj = self.txt_log.get_parent().get_vadjustment()
        adj.set_value(adj.get_upper())

    def _run_git_command(self, action, commit_msg=""):
        path = self.entry_path.get_text().strip()
        url = self.entry_url.get_text().strip()
        if not path:
            self._log("❌ Chemin local requis.")
            return
            
        if action == "clone":
            if not url:
                self._log("❌ URL du dépôt requise pour cloner.")
                return
            # Correction Git Clone :
            target_dir = Path(path)
            if target_dir.exists():
                if any(target_dir.iterdir()):
                    self._log(f"❌ Le dossier '{path}' existe déjà et n'est pas vide. Git refuse d'écraser.")
                    self._log("💡 Astuce : Choisissez un nouveau nom de dossier à la fin du chemin.")
                    return
                else:
                    self._log(f"ℹ️ Le dossier '{path}' existe mais est vide. Clonage autorisé.")
            else:
                parent_dir = target_dir.parent
                if not parent_dir.exists():
                    self._log(f"❌ Le dossier parent '{parent_dir}' n'existe pas. Veuillez choisir un chemin valide.")
                    return
            
            cmd = ["git", "clone", url, path]
            self._log(f"Exécution : {' '.join(cmd)}")
            self._execute_git_command(cmd)
            
        elif action == "status":
            cmd = ["git", "-C", path, "status"]
            self._log(f"Exécution : {' '.join(cmd)}")
            self._execute_git_command(cmd)
            
        elif action == "add":
            cmd = ["git", "-C", path, "add", "."]
            self._log(f"Exécution : {' '.join(cmd)}")
            self._execute_git_command(cmd)
            
        elif action == "commit_push":
            if not commit_msg:
                self._log("❌ Message de commit requis.")
                return
            cmd_add = ["git", "-C", path, "add", "."]
            cmd_commit = ["git", "-C", path, "commit", "-m", commit_msg]
            cmd_push = ["git", "-C", path, "push"]
            self._execute_git_sequence([cmd_add, cmd_commit, cmd_push])

    def _execute_git_command(self, cmd):
        def _thread():
            try:
                target_path = self.entry_path.get_text().strip()
                # Astuce : On exécute git depuis le dossier PARENT
                cwd = str(Path(target_path).parent)
                # Sécurité : si on est à la racine '/', on utilise home
                if cwd == '/':
                    cwd = str(Path.home())
                
                proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
                output = proc.stdout.strip() or proc.stderr.strip()
                
                if proc.returncode == 0:
                    GLib.idle_add(lambda: self._log(f"✅ Succès:\n{output}"))
                    # Mise à jour automatique du champ pour pointer vers le nouveau dossier
                    if "clone" in " ".join(cmd):
                        final_folder = Path(target_path)
                        if not final_folder.exists():
                            repo_name = self.entry_url.get_text().strip().split('/')[-1].replace('.git', '')
                            final_folder = Path(cwd) / repo_name
                        if final_folder.exists():
                            GLib.idle_add(lambda: self.entry_path.set_text(str(final_folder)))
                else:
                    GLib.idle_add(lambda: self._log(f"❌ Erreur (Code {proc.returncode}):\n{output}"))
            except Exception as e:
                GLib.idle_add(lambda err=e: self._log(f"❌ Exception: {err}"))
        
        threading.Thread(target=_thread, daemon=True).start()

    def _execute_git_sequence(self, cmds):
        def _thread():
            for cmd in cmds:
                GLib.idle_add(lambda c=cmd: self._log(f"▶ {' '.join(c)}"))
                try:
                    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=self.entry_path.get_text().strip())
                    output = proc.stdout.strip() or proc.stderr.strip()
                    if proc.returncode != 0:
                        GLib.idle_add(lambda o=output: self._log(f"❌ Échec de la séquence:\n{o}"))
                        return
                    GLib.idle_add(lambda o=output: self._log(f"✅ {o}"))
                except Exception as e:
                    GLib.idle_add(lambda err=e: self._log(f"❌ Exception: {err}"))
                    return
            GLib.idle_add(lambda: self._log("🎉 Séquence Commit & Push terminée avec succès."))
        
        threading.Thread(target=_thread, daemon=True).start()

    def _open_commit_dialog(self, *_):
        dialog = Gtk.Dialog(title="Message de Commit", transient_for=self, default_width=400, default_height=200)
        dialog.add_css_class("rounded-dialog")
        content = dialog.get_content_area()
        content.set_spacing(8)
        set_margins(content, 12)
        content.append(Gtk.Label(label="Décrivez vos modifications :", xalign=0))
        entry = Gtk.Entry()
        entry.set_placeholder_text("ex: feat: ajout de la fonctionnalité X")
        content.append(entry)
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_cancel = Gtk.Button(label="Annuler")
        btn_ok = Gtk.Button(label="✅ Valider", css_classes=["suggested-action"])
        btn_box.append(btn_cancel)
        btn_box.append(btn_ok)
        content.append(btn_box)
        
        def on_ok(*_):
            msg = entry.get_text().strip()
            if msg:
                self._run_git_command("commit_push", msg)
                dialog.destroy()
        
        btn_ok.connect("clicked", on_ok)
        btn_cancel.connect("clicked", lambda *_: dialog.destroy())
        entry.connect("activate", on_ok)
        dialog.present()

# Remplacez entièrement la classe BusinessProcessDialog par :

class BusinessProcessDialog(Gtk.Dialog):
    def __init__(self, parent, ai_engine, log_callback, config_getter=None):
        super().__init__(title="🧠 Assistant IA & Élaborateur de Processus", transient_for=parent, default_width=850, default_height=650)
        self.add_css_class("rounded-dialog")
        self.ai_engine = ai_engine
        self.log_callback = log_callback
        self.config_getter = config_getter
        
        # Rôles par défaut calibrés et très explicites (orientés JSON)
        self.default_roles = {
            "Élaborateur": "Tu es un expert algorithmique de processus métier. Tu sais décomposer un problème complexe en tâches techniques précises, ordonnées et réalisables. Réponds UNIQUEMENT avec un tableau JSON d'étapes : [{'etape': 1, 'tache': '...', 'fichier': '...', 'details': '...'}].",
            "Prof de programmation": "Tu es un professeur de programmation pédagogue et expert. Tu expliques les concepts clairement. Réponds UNIQUEMENT avec un objet JSON : {'explication': '...', 'exemple_code': '...', 'bonnes_pratiques': ['...']}.",
            "Expert en Django": "Tu es un architecte logiciel Django Senior. Tu privilégies les bonnes pratiques et la sécurité. Réponds UNIQUEMENT avec un objet JSON : {'analyse': '...', 'fichiers_a_modifier': ['...'], 'code_propose': '...'}.",
            "Traducteur": "Tu es un traducteur technique expert. Tu traduis les demandes avec une précision absolue. Réponds UNIQUEMENT avec un objet JSON : {'original': '...', 'traduction': '...'}.",
            "Expert Linux": "Tu es un administrateur système Linux et DevOps expert. Tu fournis des commandes shell optimisées. Réponds UNIQUEMENT avec un objet JSON : {'commande': '...', 'explication': '...', 'avertissements': '...'}.",
            "Expert en astuce en informatique": "Tu es un guru de l'informatique. Tu donnes des astuces et solutions ingénieuses. Réponds UNIQUEMENT avec un objet JSON : {'astuce': '...', 'contexte_utilisation': '...', 'gain_estime': '...'}."
        }

        content = self.get_content_area()
        content.set_spacing(12)
        set_margins(content, 16)

        # --- Header avec Switch Auto-Copy ---
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.append(Gtk.Label(label="1. Choisissez le rôle de l'IA :", xalign=0, css_classes=["heading"]))
        
        spacer = Gtk.Box(hexpand=True)
        header_box.append(spacer)
        
        self.switch_auto_copy = Gtk.Switch()
        self.switch_auto_copy.set_tooltip_text("Copier automatiquement le résultat JSON dans le presse-papiers")
        lbl_auto = Gtk.Label(label="⚡ Auto-Copy", css_classes=["dim-label"])
        
        auto_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        auto_box.append(lbl_auto)
        auto_box.append(self.switch_auto_copy)
        header_box.append(auto_box)
        
        content.append(header_box)

        role_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.combo_role = Gtk.ComboBoxText()
        self.combo_role.set_hexpand(True)
        for role_name in self.default_roles.keys():
            self.combo_role.append_text(role_name)
        self.combo_role.set_active(0) # Élaborateur par défaut
        
        # Charger les rôles personnalisés depuis la config
        self.custom_roles = {}
        if self.config_getter:
            cfg = self.config_getter()
            self.custom_roles = cfg.get("custom_ai_roles", {})
            for role_name in self.custom_roles.keys():
                self.combo_role.append_text(role_name)
                
        role_box.append(self.combo_role)
        btn_add_role = Gtk.Button(label="➕ Ajouter un rôle")
        btn_add_role.add_css_class("ctrl-btn")
        btn_add_role.connect("clicked", self._open_add_role_dialog)
        role_box.append(btn_add_role)
        content.append(role_box)
        
        content.append(Gtk.Separator(margin_top=8, margin_bottom=8))

        # --- Section 2: Demande ---
        content.append(Gtk.Label(label="2. Décrivez votre demande ou problème :", xalign=0, css_classes=["heading"]))
        scroll_in = Gtk.ScrolledWindow()
        scroll_in.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_in.set_size_request(-1, 120)
        self.txt_problem = GtkSource.View()
        self.txt_problem.set_wrap_mode(Gtk.WrapMode.WORD)
        self.txt_problem.set_show_line_numbers(True)
        self.txt_problem.set_monospace(True)
        scroll_in.set_child(self.txt_problem)
        content.append(scroll_in)

        btn_generate = Gtk.Button(label="🤖 Générer la réponse (JSON)")
        btn_generate.add_css_class("suggested-action")
        btn_generate.set_halign(Gtk.Align.END)
        btn_generate.connect("clicked", self._on_generate)
        content.append(btn_generate)

        content.append(Gtk.Separator(margin_top=8, margin_bottom=8))

        # --- Section 3: Résultat ---
        content.append(Gtk.Label(label="3. Résultat (JSON Strict) :", xalign=0, css_classes=["heading"]))
        scroll_out = Gtk.ScrolledWindow()
        scroll_out.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_out.set_vexpand(True)
        self.txt_result = GtkSource.View()
        self.txt_result.set_editable(False)
        self.txt_result.set_monospace(True)
        self.txt_result.set_wrap_mode(Gtk.WrapMode.WORD)
        self.txt_result.set_show_line_numbers(True)
        self.txt_result.add_css_class("code-editor")
        
        lang_mgr = GtkSource.LanguageManager.get_default()
        lang_json = lang_mgr.get_language("json")
        if lang_json: self.txt_result.get_buffer().set_language(lang_json)
        
        scroll_out.set_child(self.txt_result)
        content.append(scroll_out)

        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, halign=Gtk.Align.END, margin_top=8)
        btn_copy = Gtk.Button(label="📋 Copier")
        btn_copy.connect("clicked", self._copy_result)
        btn_close = Gtk.Button(label="Fermer")
        btn_close.connect("clicked", lambda *_: self.destroy())
        action_box.append(btn_copy)
        action_box.append(btn_close)
        content.append(action_box)

    def _open_add_role_dialog(self, *_):
        dialog = Gtk.Dialog(title="Ajouter un nouveau rôle IA", transient_for=self, default_width=500, default_height=350)
        dialog.add_css_class("rounded-dialog")
        content = dialog.get_content_area()
        content.set_spacing(10)
        set_margins(content, 16)
        
        content.append(Gtk.Label(label="Nom du rôle :", xalign=0))
        entry_name = Gtk.Entry()
        entry_name.set_placeholder_text("Ex: Expert en Sécurité Web")
        content.append(entry_name)
        
        content.append(Gtk.Label(label="Prompt d'entête (Calibrage du rôle) :", xalign=0, margin_top=8))
        content.append(Gtk.Label(label="⚠️ Important : Précisez explicitement le format JSON attendu dans ce prompt.", xalign=0, css_classes=["dim-label"], margin_bottom=4))
        
        scroll_prompt = Gtk.ScrolledWindow()
        scroll_prompt.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_prompt.set_size_request(-1, 120)
        text_prompt = Gtk.TextView()
        text_prompt.set_wrap_mode(Gtk.WrapMode.WORD)
        scroll_prompt.set_child(text_prompt)
        content.append(scroll_prompt)
        
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, halign=Gtk.Align.END, margin_top=12)
        btn_cancel = Gtk.Button(label="Annuler")
        btn_cancel.connect("clicked", lambda *_: dialog.destroy())
        btn_save = Gtk.Button(label="💾 Sauvegarder", css_classes=["suggested-action"])
        btn_box.append(btn_cancel)
        btn_box.append(btn_save)
        content.append(btn_box)

        def on_save(*_):
            name = entry_name.get_text().strip()
            prompt = text_prompt.get_buffer().get_text(
                text_prompt.get_buffer().get_start_iter(),
                text_prompt.get_buffer().get_end_iter(), True
            ).strip()
            
            if not name or not prompt:
                self.log_callback("❌ Le nom et le prompt sont requis.")
                return
            
            if name in self.default_roles or name in self.custom_roles:
                self.log_callback(f"❌ Le rôle '{name}' existe déjà.")
                return
                
            self.custom_roles[name] = prompt
            self.combo_role.append_text(name)
            
            # Sauvegarder dans la config
            if self.config_getter:
                cfg = self.config_getter()
                cfg["custom_ai_roles"] = self.custom_roles
                save_config(cfg)
                
            self.log_callback(f"✅ Rôle '{name}' ajouté avec succès.")
            dialog.destroy()

        btn_save.connect("clicked", on_save)
        dialog.present()

    def _on_generate(self, *_):
        problem = self.txt_problem.get_buffer().get_text(
            self.txt_problem.get_buffer().get_start_iter(),
            self.txt_problem.get_buffer().get_end_iter(), True
        ).strip()
        
        if not problem:
            self.log_callback("❌ Veuillez décrire votre demande.")
            return

        active_text = self.combo_role.get_active_text()
        selected_role_prompt = self.default_roles.get(active_text) or self.custom_roles.get(active_text, "Tu es un assistant IA polyvalent. Réponds UNIQUEMENT en format JSON.")
        
        self.txt_result.get_buffer().set_text("Recherche dans le cache...")
        
        def _thread():
            # 1. Vérifier le cache spécifique aux processus JSON
            cached = get_cached_process(problem)
            if cached:
                result = cached["json_content"]
                GLib.idle_add(lambda: self.log_callback(f"📂 Réponse récupérée depuis la DB (Cache Processus)"))
            else:
                # 2. Appel IA avec gestion robuste des erreurs de connexion
                GLib.idle_add(lambda: self.txt_result.get_buffer().set_text("Connexion à Llama.cpp en cours..."))
                
                try:
                    result = self.ai_engine.process_modification(
                        "business_process",
                        "Contexte: Demande utilisateur",
                        problem,
                        mode="business_process",
                        custom_role=selected_role_prompt
                    )
                    
                    if result is None:
                        raise ConnectionError("Llama server ne répond pas ou a retourné une erreur.")
                        
                    save_process_to_cache(problem, result, role_type=active_text)
                    GLib.idle_add(lambda: self.log_callback(f"💾 Nouvelle réponse sauvegardée (Cache Processus)"))
                    
                except Exception as e:
                    error_msg = f"❌ Échec de connexion IA: {str(e)}"
                    GLib.idle_add(lambda: (
                        self.txt_result.get_buffer().set_text(error_msg),
                        self.log_callback(error_msg)
                    ))
                    return

            # Nettoyage garanti des balises markdown ```json par le parseur
            clean_result = self.ai_engine._clean_json_output(result)
            
            # Vérification si le nettoyage a échoué (format non autorisé)
            if "FORMAT NON AUTORISÉ" in clean_result:
                 GLib.idle_add(lambda: (
                    self.txt_result.get_buffer().set_text(clean_result),
                    self.log_callback("⚠️ L'IA n'a pas respecté le format JSON strict.")
                ))
            else:
                GLib.idle_add(lambda: self.txt_result.get_buffer().set_text(clean_result))
                GLib.idle_add(lambda: self.log_callback(f"📊 RÉPONSE GÉNÉRÉE (Rôle: {active_text}, Format: JSON)."))
                
                # Auto-Copy si activé
                if self.switch_auto_copy.get_active():
                    GLib.idle_add(lambda: (
                        Gdk.Display.get_default().get_clipboard().set(clean_result),
                        self.log_callback("📋 Résultat copié automatiquement dans le presse-papiers.")
                    ))

        threading.Thread(target=_thread, daemon=True).start()        
        def _thread():
            # 1. Vérifier le cache spécifique aux processus JSON
            cached = get_cached_process(problem)
            
            if cached:
                result = cached["json_content"]
                GLib.idle_add(lambda: self.log_callback(f"📂 Réponse récupérée depuis la DB (Cache Processus)"))
            else:
                # 2. Appel IA
                GLib.idle_add(lambda: self.txt_result.get_buffer().set_text("Génération IA en cours..."))
                result = self.ai_engine.process_modification(
                    "business_process",
                    "Contexte: Demande utilisateur",
                    problem,
                    mode="business_process",
                    custom_role=selected_role_prompt
                )
                
                if result:
                    save_process_to_cache(problem, result, role_type=active_text)
                    GLib.idle_add(lambda: self.log_callback(f"💾 Nouvelle réponse sauvegardée (Cache Processus)"))
                else:
                    GLib.idle_add(lambda: (self.txt_result.get_buffer().set_text("❌ Échec."), self.log_callback("❌ Échec.")))
                    return

            clean_result = self.ai_engine._clean_json_output(result)
            GLib.idle_add(lambda: self.txt_result.get_buffer().set_text(clean_result))
            GLib.idle_add(lambda: self.log_callback(f"📊 RÉPONSE GÉNÉRÉE (Rôle: {active_text})."))
            
            if self.switch_auto_copy.get_active():
                GLib.idle_add(lambda: (
                    Gdk.Display.get_default().get_clipboard().set(clean_result),
                    self.log_callback("📋 Résultat copié automatiquement.")
                ))
                
            # Nettoyage garanti des balises markdown ```json par le parseur
            clean_result = self.ai_engine._clean_json_output(result)
            
            GLib.idle_add(lambda: self.txt_result.get_buffer().set_text(clean_result))
            GLib.idle_add(lambda: self.log_callback(f"📊 RÉPONSE GÉNÉRÉE (Rôle: {active_text}, Format: JSON)."))
            
            # Auto-Copy si activé
            if self.switch_auto_copy.get_active():
                GLib.idle_add(lambda: (
                    Gdk.Display.get_default().get_clipboard().set(clean_result),
                    self.log_callback("📋 Résultat copié automatiquement dans le presse-papiers.")
                ))

        threading.Thread(target=_thread, daemon=True).start()

    def _copy_result(self, *_):
        text = self.txt_result.get_buffer().get_text(
            self.txt_result.get_buffer().get_start_iter(),
            self.txt_result.get_buffer().get_end_iter(), True
        ).strip()
        
        if text and text != "Génération en cours..." and not text.startswith("❌"):
            Gdk.Display.get_default().get_clipboard().set(text)
            self.log_callback("✅ Résultat JSON copié dans le presse-papiers.")
            
            
            
            
            
# ═══════════════════════════════════════════════════════════════════════
