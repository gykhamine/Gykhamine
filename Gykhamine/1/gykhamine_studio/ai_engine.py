"""Module généré automatiquement depuis gy.py"""
import re, requests, threading, textwrap, subprocess, os
from pathlib import Path
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("GtkSource", "5")
from gi.repository import Gtk, GLib, Gdk, GtkSource
from .config import global_log, set_margins
from .database import get_cached_block, save_block_to_cache, get_cached_command, save_command_to_cache, get_cached_process, save_process_to_cache, get_all_prompts, save_prompt, get_prompt, is_cache_validated, mark_cache_validated

#  AI ENGINE & MODIFICATION DIALOG
# ═══════════════════════════════════════════════════════════════════════
def _hard_wrap(text: str, width: int = 70) -> str:
    """Force des retours à la ligne réels (\\n) tous les `width` caractères.
    Contrairement au wrap automatique d'un Gtk.Label (qui dépend de la
    négociation de taille GTK/Pango et peut échouer à se déclencher assez
    tôt sur du texte dense type JSON), ceci insère les sauts de ligne
    directement dans la chaîne AVANT affichage : la largeur de la bulle ne
    peut alors plus jamais dépasser `width` caractères, quel que soit le
    contenu ni le comportement du moteur de layout."""
    if not text:
        return text
    out_lines = []
    for line in text.split("\n"):
        if len(line) <= width:
            out_lines.append(line)
            continue
        # On préserve l'indentation de tête (utile pour le JSON) sur chaque
        # ligne recoupée. On ne coupe qu'aux espaces (break_long_words=False)
        # pour ne jamais scinder un mot normal en deux ; un mot isolé plus
        # long que `width` (ex: chemin de fichier) dépassera alors la bulle
        # sur cette seule ligne, mais c'est un cas rare — le wrap GTK du
        # Gtk.Label (WORD_CHAR) sert de filet pour ce cas précis.
        indent = line[:len(line) - len(line.lstrip())]
        wrapped = textwrap.wrap(
            line, width=width, initial_indent=indent, subsequent_indent=indent,
            break_long_words=False, break_on_hyphens=False,
        )
        out_lines.extend(wrapped or [""])
    return "\n".join(out_lines)


class _ChatView(Gtk.Box):
    """Vue de conversation façon chatbot (bulles + barre de saisie en bas),
    dans le même esprit que le panneau Terminal : historique qui défile en
    haut, ligne de saisie + bouton d'envoi en bas. Réutilisée par l'Élaborateur
    et l'Analyseur de logs pour remplacer le formulaire figé par un vrai fil
    de conversation."""
    def __init__(self, placeholder="Écrivez votre message…", on_send=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.on_send = on_send

        self.messages_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        set_margins(self.messages_box, 10)

        scroll = Gtk.ScrolledWindow()
        # NEVER en horizontal obligeait le ScrolledWindow à demander toute la
        # largeur "naturelle" de son contenu (il ne peut pas compenser par du
        # scroll) -> une bulle mal wrappée pouvait faire grossir toute la
        # fenêtre au-delà de l'écran. AUTOMATIC sert de filet de sécurité :
        # avec le plafond en pixels posé sur chaque bulle (voir add_message),
        # la scrollbar horizontale ne devrait jamais apparaître en pratique.
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.add_css_class("chat-scroll")
        scroll.set_child(self.messages_box)
        self._scroll = scroll
        self.append(scroll)

        input_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        input_bar.add_css_class("chat-input-bar")
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text(placeholder)
        self.entry.set_hexpand(True)
        self.entry.add_css_class("terminal-input")
        self.entry.connect("activate", self._on_send_clicked)

        self.spinner = Gtk.Spinner()
        self.spinner.set_visible(False)

        self.btn_send = Gtk.Button()
        self.btn_send.add_css_class("whatsapp-btn")
        self.btn_send.set_tooltip_text("Envoyer")
        self.btn_send.set_child(Gtk.Image.new_from_icon_name("mail-send-symbolic"))
        self.btn_send.connect("clicked", self._on_send_clicked)

        input_bar.append(self.entry)
        input_bar.append(self.spinner)
        input_bar.append(self.btn_send)
        self.append(input_bar)

    def _on_send_clicked(self, *_):
        text = self.entry.get_text().strip()
        if not text or not self.on_send:
            return
        # Vider l'entry EN PREMIER, avant d'appeler on_send : si on_send
        # prend du temps et que l'utilisateur ré-appuie sur Entrée, le 2e
        # appel verra un entry vide et sortira proprement au lieu de
        # renvoyer le même texte → cause classique de "même réponse
        # plusieurs fois" signalée par l'utilisateur. On vide aussi le
        # entry *immédiatement* (pas après l'appel), pour la même raison.
        self.entry.set_text("")
        self.on_send(text)

    def add_message(self, text: str, sender: str = "ai", label: str = None,
                    intent_key: str = None, cache_type: str = None) -> Gtk.Label:
        bubble = Gtk.Label(label=_hard_wrap(text, width=70))
        bubble.set_wrap(True)
        bubble.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        bubble.set_xalign(0)
        bubble.set_justify(Gtk.Justification.LEFT)
        bubble.set_selectable(True)
        bubble.set_max_width_chars(64)
        # Filet de sécurité anti-débordement : max_width_chars seul ne borne
        # que la largeur "naturelle" (préférée) du label, pas sa largeur
        # minimale de calcul — avec une bulle sélectionnable (selectable),
        # GTK peut quand même redemander la largeur complète du texte et
        # pousser toute la fenêtre au-delà de l'écran (bug rapporté). On
        # pose donc en plus une largeur MAX en pixels, contrainte dure que
        # GTK doit respecter, quelle que soit la longueur du texte.
        bubble.set_size_request(480, -1)
        bubble.set_hexpand(False)
        bubble.add_css_class("chat-bubble-user" if sender == "user" else "chat-bubble-ai")

        wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        wrapper.set_halign(Gtk.Align.END if sender == "user" else Gtk.Align.START)
        wrapper.set_hexpand(False)
        if label:
            lbl = Gtk.Label(label=label)
            lbl.add_css_class("chat-bubble-sender")
            lbl.set_xalign(1 if sender == "user" else 0)
            wrapper.append(lbl)
        wrapper.append(bubble)

        # Barre d'actions sous la bulle : copier + (valider si applicable).
        # On regroupe les deux boutons dans une Gtk.Box horizontale pour
        # qu'ils restent visuellement cohérents quel que soit le sender.
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        actions.set_halign(Gtk.Align.END if sender == "user" else Gtk.Align.START)
        actions.set_hexpand(False)

        # Bouton copier individuel : chaque bulle peut être copiée seule,
        # sans dépendre du bouton global "Copier la dernière réponse". On
        # copie le texte ORIGINAL (avant le hard-wrap d'affichage) pour ne
        # jamais coller de retours à la ligne artificiels dans le résultat.
        btn_copy_msg = Gtk.Button()
        btn_copy_msg.add_css_class("block-action-btn")
        btn_copy_msg.add_css_class("chat-bubble-copy-btn")
        btn_copy_msg.set_tooltip_text("Copier ce message")
        btn_copy_msg.set_child(Gtk.Image.new_from_icon_name("edit-copy-symbolic"))
        btn_copy_msg.connect("clicked", lambda *_: self._copy_message(text, btn_copy_msg))
        actions.append(btn_copy_msg)

        # Bouton ✅ "Valider" — visible sur TOUTES les vraies bulles IA
        # (sender="ai" + un label de rôle, ce qui exclut les messages
        # d'erreur / d'aide). C'est volontairement plus permissif que la
        # condition d'origine : on veut que l'utilisateur voie le bouton
        # systématiquement, même si la bulle n'est pas encore reliée au
        # cache (intent_key manquant). Dans ce cas, le bouton agit
        # comme un marqueur visuel mais ne touche pas la DB. Le tooltip
        # reflète l'état réel.
        is_cacheable = bool(intent_key and cache_type in ("cmd", "block", "process"))
        if sender == "ai" and label:
            btn_validate = Gtk.Button()
            btn_validate.add_css_class("block-action-btn")
            btn_validate.add_css_class("chat-bubble-validate-btn")
            if is_cacheable:
                btn_validate.set_tooltip_text(
                    "Valider cette réponse IA : la marquer comme fiable et la sauvegarder en cache"
                )
                _already_validated = is_cache_validated(intent_key, cache_type)
                self._render_validate_icon(btn_validate, _already_validated)
            else:
                # Bulle IA sans cache_type (ex: Élaborateur, Compilateur C++,
                # ou une bulle d'erreur/locale). On affiche quand même le
                # bouton pour rester cohérent, mais sans état DB.
                btn_validate.set_tooltip_text(
                    "Marquer cette réponse IA comme fiable (réponse non mise en cache)"
                )
                btn_validate.set_sensitive(False)  # gris\u00e9 pour signaler \"non applicable\"
                self._render_validate_icon(btn_validate, False)
            btn_validate.connect("clicked", lambda *_: self._on_validate_clicked(
                intent_key or "", cache_type or "", btn_validate
            ))
            actions.append(btn_validate)

        wrapper.append(actions)
        self.messages_box.append(wrapper)
        GLib.idle_add(self._scroll_to_bottom)
        return bubble

    @staticmethod
    def _render_validate_icon(btn: Gtk.Button, validated: bool):
        """Met à jour l'icône et la classe CSS du bouton Valider selon l'état.
        Icône ✓ (object-select-symbolic) quand validé, ☐ vide sinon
        (checkbox-symbolic). La classe CSS `validated` permet de teinter
        le bouton (vert par ex.) via le thème."""
        icon = "object-select-symbolic" if validated else "checkbox-symbolic"
        btn.set_child(Gtk.Image.new_from_icon_name(icon))
        if validated:
            btn.add_css_class("validated")
        else:
            btn.remove_css_class("validated")

    def _on_validate_clicked(self, intent: str, cache_type: str, btn: Gtk.Button):
        """Bascule l'état validé de l'entrée de cache correspondant à cette
        réponse IA. Met aussi à jour l'icône du bouton en place (pas de
        rechargement de la bulle). En cas d'erreur (entrée absente du
        cache, etc.), on remet le bouton dans son état précédent et on
        laisse l'UI afficher un toast via le callback on_validation_result
        si la _ChatView en a un — sinon, on log en console."""
        # Lecture de l'état actuel pour pouvoir basculer (toggle)
        current = is_cache_validated(intent, cache_type)
        new_state = not current
        ok = mark_cache_validated(intent, cache_type, new_state)
        if ok:
            self._render_validate_icon(btn, new_state)
            if hasattr(self, "on_validation_result") and self.on_validation_result:
                try:
                    self.on_validation_result(intent, cache_type, new_state)
                except Exception as e:
                    global_log(f"⚠️ on_validation_result a planté: {e}")
        else:
            # Cas typique : la réponse vient d'être générée mais n'est pas
            # encore passée par save_*_to_cache (timing) ou l'intent ne
            # correspond à aucune ligne. On remet l'icône comme avant.
            self._render_validate_icon(btn, current)
            if hasattr(self, "on_validation_result") and self.on_validation_result:
                try:
                    self.on_validation_result(intent, cache_type, None)  # None = erreur
                except Exception:
                    pass

    def _copy_message(self, text: str, btn: Gtk.Button):
        Gdk.Display.get_default().get_clipboard().set(text)
        # Petit retour visuel immédiat sur le bouton lui-même (pas besoin
        # d'un show_toast externe, _ChatView est un composant générique
        # réutilisé par plusieurs dialogues qui n'ont pas tous un toast).
        btn.set_child(Gtk.Image.new_from_icon_name("object-select-symbolic"))
        def _restore():
            btn.set_child(Gtk.Image.new_from_icon_name("edit-copy-symbolic"))
            return False
        GLib.timeout_add(1200, _restore)

    def set_busy(self, busy: bool):
        self.spinner.set_visible(busy)
        if busy: self.spinner.start()
        else: self.spinner.stop()
        self.btn_send.set_sensitive(not busy)
        self.entry.set_sensitive(not busy)

    def _scroll_to_bottom(self):
        adj = self._scroll.get_vadjustment()
        if adj: adj.set_value(adj.get_upper())
        return False


class BlockAIEngine:
    def __init__(self, config_getter, log_callback):
        self.get_config = config_getter
        self.log = log_callback

# Dans la classe BlockAIEngine, remplacez les méthodes _build_prompt et process_modification par :

    def _build_prompt(self, block_type, current_code, user_intent, context_deps="", mode="modify", custom_role=None):
        # Les rôles par type de bloc viennent désormais de la table ai_prompts
        # (éditables dans le Gestionnaire de Prompts), avec un repli en dur
        # uniquement si la base est inaccessible.
        fallback_roles = {
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
        # Utilisation du rôle personnalisé s'il est fourni, sinon lecture en base ("Bloc: <type>"), sinon repli en dur
        if custom_role:
            role = custom_role
        else:
            stored = get_prompt(f"Bloc: {block_type}") or get_prompt("Bloc: other")
            role = stored["content"] if stored else fallback_roles.get(block_type, fallback_roles["other"])
        
        if mode == "contextual_modify":
            format_instruction = "RÈGLE ABSOLUE : Réponds UNIQUEMENT par le code du bloc cible modifié. Pas de markdown, pas de texte."
        elif mode == "cpp_optimize":
            format_instruction = ("RÈGLE ABSOLUE : Réponds UNIQUEMENT avec le code C/C++ complet, "
                                   "entouré d'un bloc balisé ```cpp ... ``` (ou ```c ... ```). "
                                   "Aucun texte hors du bloc, aucun autre langage.")
        elif mode == "terminal_gen":
            format_instruction = "RÈGLE ABSOLUE : Réponds UNIQUEMENT par la commande shell exacte. Pas d'explication, pas de markdown."
        elif mode == "log_analysis":
            # Texte libre : l'Analyseur de logs affiche désormais tout ce que
            # l'IA répond, sans filtre JSON.
            format_instruction = ("Réponds en texte libre et complet : explique l'erreur probable, sa cause, "
                                   "et une solution concrète. Aucun format imposé, pas de JSON obligatoire.")
        elif mode == "business_process":
            # Texte libre : l'Élaborateur affiche désormais tout ce que l'IA
            # répond, sans filtre JSON — le rôle choisi peut demander un format
            # particulier, mais ce n'est plus imposé par le moteur.
            format_instruction = "Réponds en texte libre, en suivant les instructions de ton rôle. Aucun format n'est imposé par le système."
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

    def _dedupe_consecutive_lines(self, text: str) -> str:
        """Retire les lignes consécutives strictement identiques (répétition
        d'une même commande à l'intérieur d'un seul bloc ```)."""
        lines = text.split("\n")
        out = []
        for ln in lines:
            if out and ln.strip() and ln.strip() == out[-1].strip():
                continue
            out.append(ln)
        return "\n".join(out)

    def _dedupe_consecutive(self, items: list) -> list:
        """Retire les éléments consécutifs strictement identiques d'une liste
        (répétition d'un même bloc ``` entier plusieurs fois d'affilée)."""
        out = []
        for it in items:
            if out and it.strip() == out[-1].strip():
                continue
            out.append(it)
        return out

    def _extract_shell_commands(self, text: str) -> str:
        """
        Dédiée au mode `terminal_gen` (Générateur de commandes) : contrairement
        à _clean_code_output (volontairement limitée au PREMIER bloc, pour ne
        jamais fusionner du code incompatible lors de l'édition d'un bloc),
        ici on veut au contraire récupérer TOUTES les commandes que l'IA a pu
        proposer, même quand elles sont séparées par des paragraphes
        d'explication — un modèle local suit rarement à la lettre la consigne
        "pas d'explication".

        Stratégie :
          1. On récupère tous les blocs ``` (peu importe l'étiquette de
             langage, sauf si elle indique clairement un langage non-shell
             comme python/json/javascript — auquel cas on l'ignore).
          2. On les concatène dans l'ordre, une commande par ligne : c'est le
             format que _on_execute sait déjà découper en étapes (\\n, &&, ;).
          3. Si aucun bloc ``` n'est trouvé, on tente les commandes en ligne
             entourées de backticks simples (`cmd`). On reste volontairement
             prudent : pas de devinette sur du texte libre non délimité, pour
             ne jamais risquer d'exécuter un bout de phrase.
        """
        if not text:
            return ""

        non_shell_langs = {"python", "py", "json", "javascript", "js", "html",
                            "css", "yaml", "yml", "sql", "xml", "c", "cpp", "c++"}

        commands = []
        for m in re.finditer(r'```([a-zA-Z0-9+]*)\s*\n?([\s\S]*?)```', text):
            lang = m.group(1).strip().lower()
            if lang in non_shell_langs:
                continue
            block = m.group(2).strip()
            if block:
                # Dédup ligne par ligne À L'INTÉRIEUR du bloc : un modèle
                # local qui boucle répète parfois la MÊME commande, ligne
                # après ligne, sans ligne vide entre elles — ce que
                # _collapse_repetitions (limité aux paragraphes séparés par
                # une ligne vide) ne peut pas détecter. On ne retire que
                # les répétitions consécutives EXACTES, jamais des lignes
                # différentes.
                commands.append(self._dedupe_consecutive_lines(block))

        # Dédup au niveau BLOC : si l'IA répète le bloc ``` entier plusieurs
        # fois d'affilée (même commande proposée 15 fois comme "étape").
        commands = self._dedupe_consecutive(commands)

        if commands:
            return "\n".join(commands)

        # Repli : commandes en ligne entre backticks simples (`cmd`), en
        # évitant de reprendre un mot isolé sans espace (probablement un nom
        # de fichier/variable cité, pas une commande).
        inline = [c.strip() for c in re.findall(r'`([^`\n]+)`', text) if " " in c.strip() or "/" in c.strip()]
        if inline:
            return "\n".join(inline)

        return "FORMAT NON AUTORISÉ : L'IA n'a renvoyé aucune commande délimitée (``` ou `...`)."

    def _clean_cpp_output(self, text: str) -> str:
        """
        Extrait STRICTEMENT du code C/C++ pour le Compilateur : seuls les blocs
        balisés ```c, ```cpp, ```c++, ```cxx, ```cc, ```h, ```hpp ou ``` (sans
        langage précisé) sont acceptés. Un bloc explicitement étiqueté dans un
        autre langage (```python, ```bash, ```json, ```javascript, ...) est
        ignoré, pour que l'Optimiseur ne renvoie jamais autre chose que du
        C/C++ dans l'éditeur.
        """
        if not text:
            return ""

        cpp_tags = {"", "c", "cpp", "c++", "cxx", "cc", "h", "hpp"}
        for match in re.finditer(r'```([a-zA-Z0-9+]*)\s*\n?([\s\S]*?)```', text):
            lang = match.group(1).strip().lower()
            if lang in cpp_tags:
                code = match.group(2).strip()
                if code:
                    return code

        return "FORMAT NON AUTORISÉ : L'IA doit renvoyer du code C/C++ entre des balises ```c ... ``` ou ```cpp ... ```"

    def _collapse_repetitions(self, text: str) -> str:
        """
        Filet de sécurité anti-boucle, appliqué à TOUS les modes (pas un filtre
        de format) : certains modèles locaux, avec une température basse et
        sans pénalité de répétition, se mettent à répéter le même bloc de
        texte mot pour mot jusqu'à épuiser max_tokens. Sans ce filet, tout ce
        contenu dupliqué est affiché tel quel (une bulle géante, ou plusieurs
        blocs identiques bout à bout). On ne touche à AUCUN contenu différent :
        on retire uniquement les répétitions consécutives *exactes*.

        Deux passes, du plus large au plus fin :
          1. Paragraphes séparés par une ligne vide (cas le plus courant).
          2. Repli : motif de N lignes qui se répète au moins 3 fois de suite
             SANS ligne vide entre les répétitions (sinon invisible pour la
             passe 1) — ex: toute la réponse "explication + commande" reprise
             identique plusieurs fois d'affilée.
        """
        if not text:
            return text

        # --- Passe 1 : paragraphes (ligne vide entre eux) ---
        blocks = re.split(r'\n\s*\n', text.strip())
        if len(blocks) >= 3:
            collapsed = [blocks[0]]
            dropped = 0
            for b in blocks[1:]:
                if b.strip() and b.strip() == collapsed[-1].strip():
                    dropped += 1
                    continue
                collapsed.append(b)
            if dropped > 0:
                note = f"\n\n⚠️ {dropped} répétition(s) identique(s) du même bloc ont été retirées (le modèle a bouclé sur sa réponse)."
                return "\n\n".join(collapsed).strip() + note

        # --- Passe 2 : motif périodique de lignes, sans ligne vide ---
        lines = text.strip().split("\n")
        n = len(lines)
        best_k, best_repeats, best_dropped_lines = 0, 0, 0
        max_period = min(25, n // 3)  # motifs de 1 à 25 lignes
        for k in range(1, max_period + 1):
            period = lines[:k]
            if not any(l.strip() for l in period):
                continue  # motif vide (que des lignes blanches), ignorer
            repeats = 1
            pos = k
            while pos + k <= n and lines[pos:pos + k] == period:
                repeats += 1
                pos += k
            if repeats >= 3:
                dropped_lines = (repeats - 1) * k
                if dropped_lines > best_dropped_lines:
                    best_k, best_repeats, best_dropped_lines = k, repeats, dropped_lines

        if best_repeats >= 3:
            k = best_k
            period = lines[:k]
            remainder = lines[best_repeats * k:]
            dropped = best_repeats - 1
            note = f"\n\n⚠️ {dropped} répétition(s) identique(s) du même passage ont été retirées (le modèle a bouclé sur sa réponse)."
            return "\n".join(period + remainder).strip() + note

        return text

    def _strip_code_fences(self, text: str) -> str:
        """
        Retire uniquement les balises de bloc markdown (```json, ```, etc.)
        en gardant tout le contenu à l'intérieur intact. Utilisé pour les
        modes texte libre (log_analysis / business_process) où le rôle
        choisi peut demander du JSON : on ne veut plus voir les balises
        ```json ... ``` dans la bulle de chat, seulement le dictionnaire.
        Si le texte contient d'autres passages hors bloc, ils sont conservés
        tels quels — on ne supprime que les lignes de balise elles-mêmes.
        """
        if not text:
            return text
        # Ligne d'ouverture ```json / ```python / ``` seule sur sa ligne
        text = re.sub(r'^\s*```[a-zA-Z]*\s*\n', '', text)
        text = re.sub(r'\n\s*```\s*$', '', text)
        # Au cas où des balises resteraient ailleurs (plusieurs blocs) :
        text = re.sub(r'```[a-zA-Z]*\n?', '', text)
        return text.strip()

    def process_modification(self, block_type, current_code, user_intent, context_deps="", mode="modify", custom_role=None):
        cfg = self.get_config()
        host = cfg.get("llama_host", "127.0.0.1")
        port = cfg.get("llama_port", 8080)
        url = f"http://{host}:{port}/v1/chat/completions"
        
        # Passage du custom_role au prompt builder
        prompt = self._build_prompt(block_type, current_code, user_intent, context_deps, mode=mode, custom_role=custom_role)
        
        sys_prompt = get_prompt("Système: génération de code")
        sys_content = sys_prompt["content"] if sys_prompt else "Tu es un moteur de génération de code strict. Tu ne parles pas, tu codes."
        payload = {
            "model": "qwen2.5-coder",
            "messages": [
                {"role": "system", "content": sys_content},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            # Anti-boucle côté modèle : sans pénalité, un modèle local à
            # température basse peut se mettre à répéter le même bloc de
            # texte jusqu'à max_tokens (surtout en texte libre, sans qu'un
            # ```json``` ne le force à s'arrêter). repeat_penalty est
            # spécifique à llama.cpp ; frequency/presence_penalty suivent le
            # format OpenAI, les deux sont envoyés pour couvrir les deux cas.
            "repeat_penalty": 1.15,
            "frequency_penalty": 0.3,
            "presence_penalty": 0.2,
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
                # Filet anti-boucle universel : jamais un filtre de format,
                # juste une protection contre un modèle qui répète le même
                # bloc en boucle — appliqué à TOUS les modes.
                raw_content = self._collapse_repetitions(raw_content)
                # Utilisation du bon nettoyeur selon le mode :
                # - log_analysis / business_process : AUCUN filtre, tout le texte
                #   de l'IA est laissé passer tel quel (plus de format JSON imposé).
                # - cpp_optimize : uniquement du code C/C++ (voir _clean_cpp_output).
                # - autres modes (édition de bloc, terminal...) : extraction de
                #   code générique entre balises ```.
                if mode in ("log_analysis", "business_process"):
                    cleaned_code = self._strip_code_fences(raw_content.strip())
                elif mode == "cpp_optimize":
                    cleaned_code = self._clean_cpp_output(raw_content)
                elif mode == "terminal_gen":
                    # Plusieurs commandes séparées par des explications sont
                    # fréquentes ici : extraction dédiée (voir docstring),
                    # au lieu de _clean_code_output qui ne garde que le
                    # 1er bloc ``` et jetait silencieusement le reste.
                    cleaned_code = self._extract_shell_commands(raw_content)
                else:
                    cleaned_code = self._clean_code_output(raw_content, block_type)
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
        super().__init__(title=f"✨ Modification IA : {block['name']}", transient_for=parent, default_width=1050, default_height=750)
        self.add_css_class("rounded-dialog")
        self.block = block
        self.ai_engine = ai_engine
        self.on_confirm_cb = on_confirm_cb
        self.project_root = project_root
        self.modified_code = None
        self.context_deps = ""
        
        outer_content = self.get_content_area()
        outer_content.set_spacing(0)
        # Tout le contenu (diff + fil de statut + prompt) est placé dans une zone
        # défilante : sur un petit écran, le bouton d'envoi ne se retrouve plus
        # caché en dehors de la fenêtre — on peut toujours descendre jusqu'à lui.
        _scroller = Gtk.ScrolledWindow()
        _scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        _scroller.set_vexpand(True)
        _scroller.set_hexpand(True)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_spacing(10)
        set_margins(content, 16)
        _scroller.set_child(content)
        outer_content.append(_scroller)
        
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
        scroll_orig.set_size_request(-1, 300)
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
        scroll_new.set_size_request(-1, 300)
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
        
        # Fil de conversation IA : le VRAI même composant _ChatView que
        # l'Analyseur de Logs / l'Élaborateur / le Compilateur C/C++ (bulles +
        # entrée en pilule + bouton d'envoi circulaire) — pas une imitation.
        # Le comparateur Code Actuel / Proposition IA reste au-dessus, propre à
        # ce dialogue puisqu'il faut voir le "avant/après" avant d'accepter.
        self.chat = _ChatView(placeholder="Décrivez la modification voulue (max 150 mots)…", on_send=self._on_generate)
        self.chat.set_vexpand(True)
        self.chat.set_size_request(-1, 220)
        content.append(self.chat)
        self.chat.add_message("Décrivez la modification voulue ci-dessous, puis envoyez.", sender="ai", label="✨ Modificateur")

    def _on_generate(self, intent: str):
        intent = intent.strip()

        if len(intent.split()) > 150:
            self.ai_engine.log("⚠️ Votre demande dépasse 150 mots.")
            self.chat.add_message("⚠️ Votre demande dépasse 150 mots.", sender="ai", label="✨ Modificateur")
            return
        if not intent:
            self.ai_engine.log("⚠️ Veuillez décrire la modification.")
            self.chat.add_message("⚠️ Veuillez décrire la modification.", sender="ai", label="✨ Modificateur")
            return
            
        # Construction du contexte (vide car supprimé de l'UI)
        self.context_deps = ""

        self.chat.add_message(intent, sender="user")
        self.chat.set_busy(True)
        
        threading.Thread(target=self._thread_generate, args=(self.block['type'], intent), daemon=True).start()

    def _thread_generate(self, btype, intent):
        # 1. Vérifier le cache spécifique aux blocs de code (clé qualifiée par
        # type de bloc : sinon une même formulation sur deux blocs de types
        # différents renverrait le même contenu en cache).
        cache_key = f"[{btype}] {intent}"
        cached = get_cached_block(cache_key)
        
        if cached:
            result = cached["content"]
            GLib.idle_add(lambda: self.ai_engine.log(f"📂 Modification récupérée depuis la DB (Cache Code)"))
            GLib.idle_add(lambda: (self.chat.add_message("📂 Modification récupérée depuis le cache.", sender="ai", label="✨ Modificateur"), False)[1])
        else:
            # 2. Appel IA
            result = self.ai_engine.process_modification(btype, self.block['code'], intent, self.context_deps, mode="contextual_modify")
            
            if result:
                save_block_to_cache(cache_key, result, block_type=btype)
                GLib.idle_add(lambda: self.ai_engine.log(f"💾 Nouvelle modification sauvegardée (Cache Code)"))

        GLib.idle_add(self._update_ui_with_result, result, cache_key)
        
    def _update_ui_with_result(self, result, cache_key: str = ""):
        self.chat.set_busy(False)

        if result:
            self.modified_code = result
            self.view_new.get_buffer().set_text(result)
            self.ai_engine.log("✅ Modification générée.")
            # Bulle "principale" du résultat : c'est sur celle-ci qu'on
            # veut un bouton Valider, car c'est la VRAIE réponse de l'IA
            # (les autres bulles de ce flux sont des acquittements :
            # "veuillez décrire…", "récupéré du cache…", "échec…").
            # `cache_key` est passé par _thread_generate et correspond
            # exactement à la clé utilisée pour save_block_to_cache —
            # donc mark_cache_validated touchera la bonne ligne.
            self.chat.add_message(
                "✅ Modification générée — voir la proposition à droite.",
                sender="ai", label="✨ Modificateur",
                intent_key=cache_key, cache_type="block",
            )
            
            # Auto-Apply si activé
            if self.switch_auto_apply.get_active():
                self._on_accept(None)
        else:
            self.ai_engine.log("❌ Échec de la génération ou erreur serveur.")
            self.chat.add_message("❌ Échec de la génération ou erreur serveur.", sender="ai", label="✨ Modificateur")
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
        super().__init__(title="🔍 Analyseur de Logs IA", transient_for=parent, default_width=760, default_height=700)
        self.add_css_class("rounded-dialog")
        self.ai_engine = ai_engine
        self.log_callback = log_callback

        content = self.get_content_area()
        content.set_spacing(10)
        set_margins(content, 14)

        # Zone de collage des logs, et fil de conversation : les deux zones sont
        # désormais redimensionnables à la souris (poignée entre les deux), comme
        # dans le Modificateur IA (Original vs Proposition).
        paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        paned.set_vexpand(True)
        paned.set_hexpand(True)
        paned.set_wide_handle(True)

        box_logs = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box_logs.append(Gtk.Label(label="Logs à analyser :", xalign=0, css_classes=["dim-label"]))
        scroll_logs = Gtk.ScrolledWindow()
        scroll_logs.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_logs.set_vexpand(True)
        self.txt_logs = GtkSource.View()
        self.txt_logs.set_wrap_mode(Gtk.WrapMode.WORD)
        self.txt_logs.set_show_line_numbers(True)
        self.txt_logs.set_monospace(True)
        lang_mgr = GtkSource.LanguageManager.get_default()
        lang_txt = lang_mgr.get_language("txt")
        if lang_txt: self.txt_logs.get_buffer().set_language(lang_txt)
        scroll_logs.set_child(self.txt_logs)
        box_logs.append(scroll_logs)

        # Fil de conversation : la question posée devient un message "utilisateur",
        # la réponse de l'IA un message "assistant" — les analyses s'accumulent
        # au lieu d'écraser le résultat précédent.
        self.chat = _ChatView(placeholder="Ex: Pourquoi le serveur plante-t-il ?", on_send=self._on_send)
        self.chat.set_vexpand(True)

        paned.set_start_child(box_logs)
        paned.set_end_child(self.chat)
        paned.set_resize_start_child(True)
        paned.set_resize_end_child(True)
        paned.set_shrink_start_child(True)
        paned.set_shrink_end_child(True)
        paned.set_position(180)
        content.append(paned)

        self.chat.add_message(
            "Collez vos logs ci-dessus, puis posez votre question (ou envoyez un message vide pour une analyse générale).",
            sender="ai", label="🔍 Analyseur"
        )

    def _on_send(self, question: str):
        logs = self.txt_logs.get_buffer().get_text(self.txt_logs.get_buffer().get_start_iter(), self.txt_logs.get_buffer().get_end_iter(), True).strip()
        if not logs:
            self.log_callback("❌ Veuillez coller des logs à analyser.")
            self.chat.add_message("⚠️ Aucun log collé — impossible d'analyser.", sender="ai", label="🔍 Analyseur")
            return

        self.chat.add_message(question if question else "(Analyse générale des logs collés)", sender="user")
        self.chat.set_busy(True)
        intent = f"Analyse ces logs. Question spécifique: {question if question else 'Explique les erreurs et propose une solution.'}"
        self.log_callback("🤖 Analyse des logs en cours...")

        def _thread():
            # Clé de cache qualifiée par les 200 premiers caractères des
            # logs : on ne veut pas hasher 10k de lignes de stacktrace, et
            # 200 chars suffisent largement à discriminer deux contextes
            # différents (le 1er frame d'erreur est presque toujours dedans).
            # Si l'utilisateur colle les mêmes logs + la même question,
            # on sert la réponse précédente — c'est exactement le but.
            cache_key = f"[log_analysis] {logs[:200]}|{question}"
            cached = get_cached_process(cache_key)
            if cached:
                result = cached["json_content"]
                GLib.idle_add(lambda: self.log_callback("📂 Analyse récupérée depuis la DB (Cache)"))
            else:
                result = self.ai_engine.process_modification("log_analysis", logs, intent, mode="log_analysis")
                if result:
                    save_process_to_cache(cache_key, result, role_type="log_analysis")
                    GLib.idle_add(lambda: self.log_callback("💾 Nouvelle analyse sauvegardée (Cache)"))
            if result:
                # Plus de filtre JSON : on affiche tel quel tout ce que l'IA a répondu.
                GLib.idle_add(lambda: (self.chat.add_message(result, sender="ai", label="🔍 Analyseur",
                                                              intent_key=cache_key, cache_type="process"), False)[1])
                GLib.idle_add(lambda: self.log_callback("📊 Analyse IA terminée."))
            else:
                GLib.idle_add(lambda: (self.chat.add_message("❌ Échec de l'analyse IA.", sender="ai", label="🔍 Analyseur"), False)[1])
                GLib.idle_add(lambda: self.log_callback("❌ Échec de l'analyse IA."))
            GLib.idle_add(lambda: self.chat.set_busy(False))

        threading.Thread(target=_thread, daemon=True).start()

class AICmdGeneratorDialog(Gtk.Dialog):
    def __init__(self, parent, terminal_panel):
        super().__init__(title="🤖 Générateur de Commandes IA", transient_for=parent, default_width=600, default_height=450)
        self.add_css_class("rounded-dialog")
        self.terminal_panel = terminal_panel
        self.generated_cmd = ""
        self.is_process_mode = False
        # --- BUG #2 : protection contre les générations en double ---
        # Si l'utilisateur tape une commande, valide, et tape une autre
        # commande avant que la 1ère n'ait fini de répondre, deux _thread
        # tournent en parallèle. Quand les deux finissent, on a 2 fois
        # la même réponse dans le chat (parfois c'est la même string
        # par cache, parfois c'est 2 générations distinctes mais très
        # ressemblantes). Ce flag garantit qu'un seul _thread de
        # génération est actif à la fois. Le bouton Envoyer est aussi
        # désactivé via set_busy() de la _ChatView, mais on a un 2e
        # filet de sécurité ici au cas où le timing est bizarre (double
        # signal Entrée, etc.).
        self._generating = False
        
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

        # Exécution en série : les étapes s'exécutent l'une après l'autre en
        # ATTENDANT réellement la fin de chaque commande (contrairement à
        # l'ancien comportement fire-and-forget, où toutes les étapes étaient
        # lancées quasi en parallèle). Actif par défaut dès qu'un "processus"
        # (plusieurs étapes) est détecté — voir _on_translate.
        self.switch_serial = Gtk.Switch()
        self.switch_serial.set_tooltip_text(
            "Exécuter les étapes une par une, dans l'ordre, en attendant chaque "
            "résultat avant de lancer la suivante (arrêt si une étape échoue)."
        )
        lbl_serial = Gtk.Label(label="🔁 Série", css_classes=["dim-label"])
        serial_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        serial_box.append(lbl_serial)
        serial_box.append(self.switch_serial)
        header_box.append(serial_box)
        
        content.append(header_box)
        
        # Fil de conversation IA : même composant que partout ailleurs.
        self.chat = _ChatView(
            placeholder="Ex: 'Mettre à jour le système' ou 'Liste: installer git, cloner repo, entrer dans le dossier'",
            on_send=self._on_translate,
        )
        self.chat.set_vexpand(True)
        content.append(self.chat)
        self.chat.add_message("Décrivez l'action voulue, puis envoyez.", sender="ai", label="🤖 Commandes")
        
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

    def _on_translate(self, intent: str):
        intent = intent.strip()
        if not intent:
            self.terminal_panel._log("❌ Veuillez décrire une action.")
            self.chat.add_message("⚠️ Veuillez décrire une action.", sender="ai", label="🤖 Commandes")
            return

        # --- BUG #2 (suite) : si une génération est déjà en cours, on
        # ignore cette demande. Ça arrive quand l'utilisateur double-
        # clique sur Envoyer ou appuie 2x vite sur Entrée. Sans ce
        # garde, on lançait 2 threads en parallèle → 2 réponses
        # affichées, parfois identiques (cache) parfois différentes.
        if self._generating:
            self.terminal_panel._log("⏳ Génération déjà en cours, requête ignorée.")
            return
        self._generating = True

        self.chat.add_message(intent, sender="user")
        self.chat.set_busy(True)
        self.btn_exec.set_sensitive(False)
        
        # Détection simple de mode "Processus" (si l'utilisateur utilise des mots clés comme "liste", "puis", "et ensuite")
        process_keywords = ["liste", "processus", "étapes", "puis", "ensuite", "et"]
        self.is_process_mode = any(kw in intent.lower() for kw in process_keywords)
        # Une suite d'étapes profite presque toujours de l'exécution en
        # série (ordre garanti, cd qui persiste, arrêt propre sur échec) :
        # activée par défaut dans ce cas, sans écraser un choix déjà fait
        # manuellement par l'utilisateur sur une génération précédente.
        if self.is_process_mode and not self.switch_serial.get_active():
            self.switch_serial.set_active(True)

        def _thread():
            # 1. Vérifier le cache
            cached = get_cached_command(intent)
            
            if cached:
                cmd = cached["command"]
                source = "Cache DB ✅"
                GLib.idle_add(lambda: self.terminal_panel._log(f"📂 Commande récupérée depuis la base de données ({source})"))
            else:
                # 2. Si pas dans le cache, appeler l'IA
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
                        self.chat.add_message("❌ Échec de la génération.", sender="ai", label="🤖 Commandes"),
                        self.chat.set_busy(False),
                        False,
                    )[-1])
                    return

            # Affichage du résultat
            display_cmd = cmd.replace("&&", "\n&& ").replace(";", "\n; ") if self.is_process_mode else cmd
            GLib.idle_add(lambda: (
                self.chat.add_message(f"$ {display_cmd}", sender="ai", label="🤖 Commandes",
                                       intent_key=intent, cache_type="cmd"),
                self.chat.set_busy(False),
                self.btn_exec.set_sensitive(True),
                setattr(self, 'generated_cmd', cmd),
                False,
            )[-1])
            
            # Auto-Run si activé
            if self.switch_auto_run.get_active():
                GLib.idle_add(lambda: self._on_execute(None))

        def _thread_wrapper():
            try:
                _thread()
            finally:
                # Toujours relâcher le flag, même en cas d'exception,
                # sinon l'utilisateur ne peut plus jamais générer.
                self._generating = False

        threading.Thread(target=_thread_wrapper, daemon=True).start()

    def _on_execute(self, *_):
        if hasattr(self, 'generated_cmd') and self.generated_cmd:
            # --- BUG #1 : exécution correcte des suites de commandes ---
            # Avant : on passait tout le `generated_cmd` d'un coup à
            # _run_custom_command_text. Si l'IA renvoyait des commandes
            # sur plusieurs lignes SANS séparateurs `&&` / `;` (elle le
            # fait souvent quand elle formate "joli"), seule la première
            # ligne s'exécutait — le reste était ignoré par le shell.
            #
            # Maintenant : on splitte la commande en étapes en gérant
            # 3 séparateurs possibles (par ordre de robustesse) :
            #   1. `\n`       (l'IA a renvoyé une commande par ligne)
            #   2. `&&`       (succeed chain — stop on fail)
            #   3. `;`        (indépendant)
            raw = self.generated_cmd
            normalized = raw.replace("&&", "\n").replace(";", "\n")
            steps = [s.strip() for s in normalized.split("\n") if s.strip()]

            if self.is_process_mode:
                self.terminal_panel._log(
                    f"🚀 Lancement du processus ({len(steps)} étapes)..."
                )

            if self.switch_serial.get_active() and len(steps) > 1:
                self._run_steps_serial(steps)
            else:
                # Mode historique (fire-and-forget) : conservé pour une
                # commande unique, ou si l'utilisateur désactive la série.
                for i, step in enumerate(steps, 1):
                    if self.is_process_mode:
                        self.terminal_panel._log(f"  [{i}/{len(steps)}] $ {step}")
                    self.terminal_panel._run_custom_command_text(step)
            # On ne ferme pas forcément le dialogue pour voir le résultat

    def _run_steps_serial(self, steps):
        """
        Exécution SÉQUENTIELLE réelle : chaque étape attend la fin de la
        précédente (contrairement à _run_custom_command_text, qui est
        fire-and-forget et lançait toutes les étapes quasi en parallèle).

        - Un `cd <chemin>` isolé est traduit en changement de répertoire de
          travail pour les étapes suivantes (un `cd` lancé dans son propre
          sous-process n'aurait aucun effet une fois ce process terminé).
        - S'arrête à la première étape en échec (code retour ≠ 0), comme
          le ferait un enchaînement `&&` dans un vrai terminal.
        - Tourne dans un thread dédié pour ne pas geler l'interface.
        """
        root = self.terminal_panel.get_project_root()
        cwd = str(root) if root else os.getcwd()

        def _thread():
            total = len(steps)
            for i, step in enumerate(steps, 1):
                cd_match = re.match(r'^cd\s+(.+)$', step.strip())
                if cd_match:
                    target = cd_match.group(1).strip().strip('"\'')
                    new_cwd = target if os.path.isabs(target) else os.path.normpath(os.path.join(cwd, target))
                    if os.path.isdir(new_cwd):
                        cwd = new_cwd
                        GLib.idle_add(self.terminal_panel._log, f"  [{i}/{total}] 📂 cd → {cwd}")
                        continue
                    else:
                        GLib.idle_add(self.terminal_panel._log, f"  [{i}/{total}] ❌ Dossier introuvable : {new_cwd}")
                        GLib.idle_add(self.terminal_panel._log, f"🛑 Série arrêtée à l'étape {i}/{total}.")
                        return

                GLib.idle_add(self.terminal_panel._log, f"  [{i}/{total}] $ {step}")
                try:
                    env = os.environ.copy(); env["PYTHONUNBUFFERED"] = "1"; env["DJANGO_COLORS"] = "nocolor"
                    proc = subprocess.Popen(
                        step, shell=True, cwd=cwd,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL, text=True, bufsize=1, env=env,
                    )
                    for line in iter(proc.stdout.readline, ''):
                        if line:
                            GLib.idle_add(self.terminal_panel._log, line.rstrip())
                    proc.wait()
                except Exception as e:
                    GLib.idle_add(self.terminal_panel._log, f"❌ Erreur étape {i}/{total} : {e}")
                    GLib.idle_add(self.terminal_panel._log, f"🛑 Série arrêtée à l'étape {i}/{total}.")
                    return

                if proc.returncode != 0:
                    GLib.idle_add(self.terminal_panel._log, f"❌ Étape {i}/{total} échouée (code {proc.returncode}).")
                    GLib.idle_add(self.terminal_panel._log, f"🛑 Série arrêtée à l'étape {i}/{total}.")
                    return
                GLib.idle_add(self.terminal_panel._log, f"  ✅ Étape {i}/{total} terminée.")

            GLib.idle_add(self.terminal_panel._log, f"🏁 Série terminée avec succès ({total}/{total} étapes).")

        threading.Thread(target=_thread, daemon=True).start()
class GitManagerDialog(Gtk.Dialog):
    def __init__(self, parent, project_root, log_callback):
        super().__init__(title="🐙 Mini GitHub Desktop", transient_for=parent, default_width=760, default_height=650)
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
        super().__init__(title="🧠 Assistant IA & Élaborateur de Processus", transient_for=parent, default_width=920, default_height=720)
        self.add_css_class("rounded-dialog")
        self.ai_engine = ai_engine
        self.log_callback = log_callback
        self.config_getter = config_getter

        # Rôles IA : désormais chargés depuis la base SQLite (table ai_prompts),
        # amorcée automatiquement avec les rôles par défaut au premier lancement.
        # On exclut les rôles internes utilisés par l'éditeur de blocs ("Bloc: …"
        # et "Système: …") : ce sont des rôles techniques par type de bloc, pas des
        # rôles de conversation — les proposer ici ne ferait qu'embrouiller l'usage.
        # self.roles = {nom: contenu} ; self.role_is_default = {nom: bool}
        self.roles = {}
        self.role_is_default = {}
        for p in get_all_prompts():
            if p["name"].startswith("Bloc: ") or p["name"].startswith("Système:"):
                continue
            self.roles[p["name"]] = p["content"]
            self.role_is_default[p["name"]] = p["is_default"]

        content = self.get_content_area()
        content.set_spacing(12)
        set_margins(content, 16)

        # --- Header avec Switch Auto-Copy ---
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.append(Gtk.Label(label="Rôle de l'IA :", xalign=0, css_classes=["heading"]))
        
        spacer = Gtk.Box(hexpand=True)
        header_box.append(spacer)
        
        self.switch_auto_copy = Gtk.Switch()
        self.switch_auto_copy.set_tooltip_text("Copier automatiquement le résultat dans le presse-papiers")
        lbl_auto = Gtk.Label(label="⚡ Auto-Copy", css_classes=["dim-label"])
        
        auto_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        auto_box.append(lbl_auto)
        auto_box.append(self.switch_auto_copy)
        header_box.append(auto_box)
        
        content.append(header_box)

        role_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.combo_role = Gtk.ComboBoxText()
        self.combo_role.set_hexpand(True)
        for role_name in self.roles.keys():
            self.combo_role.append_text(role_name)
        self.combo_role.set_active(0) # Premier rôle (par défaut : Élaborateur) par défaut

        role_box.append(self.combo_role)
        btn_add_role = Gtk.Button(label="➕ Ajouter un rôle")
        btn_add_role.add_css_class("ctrl-btn")
        btn_add_role.connect("clicked", self._open_add_role_dialog)
        role_box.append(btn_add_role)
        content.append(role_box)
        content.append(Gtk.Separator(margin_top=8, margin_bottom=8))

        # Le formulaire figé (zone de saisie + zone de résultat qui s'écrase à
        # chaque génération) devient un vrai fil de conversation façon chatbot :
        # chaque demande et chaque réponse s'empilent, comme dans le Terminal.
        self.chat = _ChatView(placeholder="Décrivez votre demande ou problème…", on_send=self._on_generate)
        self.chat.set_vexpand(True)
        content.append(self.chat)

        self.last_result = None
        content.append(Gtk.Separator(margin_top=4, margin_bottom=4))
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, halign=Gtk.Align.END)
        btn_copy = Gtk.Button(label="📋 Copier la dernière réponse")
        btn_copy.connect("clicked", self._copy_result)
        action_box.append(btn_copy)
        content.append(action_box)

        active_role = self.combo_role.get_active_text()
        self.chat.add_message(f"Rôle actif : {active_role}. Décrivez votre demande ci-dessous.", sender="ai", label="🧠 Élaborateur")

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
        content.append(Gtk.Label(label="ℹ️ Précisez ici le format de réponse attendu si besoin (texte libre par défaut, JSON possible si vous le demandez explicitement).", xalign=0, css_classes=["dim-label"], margin_bottom=4))
        
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
            
            if name in self.roles:
                self.log_callback(f"❌ Le rôle '{name}' existe déjà.")
                return

            self.roles[name] = prompt
            self.role_is_default[name] = False
            self.combo_role.append_text(name)

            # Sauvegarder dans la base SQLite (table ai_prompts)
            if save_prompt(name, prompt, category="custom"):
                self.log_callback(f"✅ Rôle '{name}' ajouté avec succès (base de données).")
            else:
                self.log_callback(f"⚠️ Rôle '{name}' ajouté en mémoire, mais échec de la sauvegarde en base.")
            dialog.destroy()

        btn_save.connect("clicked", on_save)
        dialog.present()

    def _on_generate(self, problem: str):
        problem = problem.strip()
        if not problem:
            self.log_callback("❌ Veuillez décrire votre demande.")
            return

        active_text = self.combo_role.get_active_text()
        selected_role_prompt = self.roles.get(active_text, "Tu es un assistant IA polyvalent.")

        self.chat.add_message(problem, sender="user")
        self.chat.set_busy(True)

        def _thread():
            # Cache Élaborateur : la clé est qualifiée par le rôle actif
            # (chaque rôle a sa propre personnalité, donc une même question
            # peut donner 2 réponses différentes selon le rôle) + la question.
            # On NE met PAS le problème entier dans la clé pour rester lisible
            # en DB et éviter les hashs à rallier sur de longs process.
            cache_key = f"[business_process|{active_text}] {problem}"
            try:
                cached = get_cached_process(cache_key)
                if cached:
                    result = cached["json_content"]
                    GLib.idle_add(lambda: self.log_callback("📂 Réponse récupérée depuis la DB (Cache)"))
                else:
                    # Pas de cache ici : l'Élaborateur est un fil de conversation, pas
                    # un générateur déterministe (contrairement au Générateur de
                    # commandes shell). Servir une réponse mise en cache pour une
                    # formulation proche donnait l'impression de recevoir "toujours
                    # la même réponse" — chaque demande obtient maintenant une
                    # génération IA fraîche.
                    result = self.ai_engine.process_modification(
                        "business_process",
                        "Contexte: Demande utilisateur",
                        problem,
                        mode="business_process",
                        custom_role=selected_role_prompt
                    )
                    if result is None:
                        raise ConnectionError("Llama server ne répond pas ou a retourné une erreur.")
                    save_process_to_cache(cache_key, result, role_type=f"business_process:{active_text}")
                    GLib.idle_add(lambda: self.log_callback("💾 Réponse Élaborateur sauvegardée (Cache)"))
            except Exception as e:
                error_msg = f"❌ Échec de connexion IA: {e}"
                GLib.idle_add(lambda: (self.chat.add_message(error_msg, sender="ai", label=f"🧠 {active_text}"), False)[1])
                GLib.idle_add(lambda: self.log_callback(error_msg))
                GLib.idle_add(lambda: self.chat.set_busy(False))
                return

            # Plus de filtre JSON ici : process_modification renvoie déjà le
            # texte de l'IA tel quel pour ce mode — on l'affiche directement.
            self.last_result = result

            GLib.idle_add(lambda: (self.chat.add_message(result, sender="ai", label=f"🧠 {active_text}",
                                                          intent_key=cache_key, cache_type="process"), False)[1])
            GLib.idle_add(lambda: self.log_callback(f"📊 Réponse générée (Rôle: {active_text})."))
            if self.switch_auto_copy.get_active():
                GLib.idle_add(lambda: (
                    Gdk.Display.get_default().get_clipboard().set(result),
                    self.log_callback("📋 Résultat copié automatiquement dans le presse-papiers."),
                    False,
                )[-1])
            GLib.idle_add(lambda: self.chat.set_busy(False))

        threading.Thread(target=_thread, daemon=True).start()

    def _copy_result(self, *_):
        if self.last_result:
            Gdk.Display.get_default().get_clipboard().set(self.last_result)
            self.log_callback("✅ Dernière réponse copiée dans le presse-papiers.")
        else:
            self.log_callback("⚠️ Aucune réponse à copier pour l'instant.")

# ═══════════════════════════════════════════════════════════════════════
