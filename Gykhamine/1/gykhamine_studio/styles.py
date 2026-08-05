"""
Module contenant uniquement les styles CSS pour Gykhamine Studio.
Ce fichier ne doit contenir que la variable CSS pour éviter les conflits d'imports.
"""
CSS = """
/* ── Base & Fond Noir Complet ──────────────────── */
window, dialog, popover, scrolledwindow, viewport, button, entry, textview, listbox, treeview, headerbar, box, stack, notebook, .background, .csd, preferencesdialog, preferencespage, preferencesgroup, actionrow, entryrow, switchrow, comborow, toastoverlay {
    background-color: #000000;
    color: #4aa3df;
}

/* Force le fond noir même pour les widgets internes */
textview, textview text {
    background-color: #000000;
    color: #4aa3df;
}

/* ── Coins Arrondis ─────────────────── */
dialog, .rounded-dialog, window.dialog, popover {
    border-radius: 12px;
}

/* ── Panel titles ─────────────────── */
.panel-title, .control-section-title { 
    font-size: 11px; 
    font-weight: bold; 
    color: #4aa3df; 
    text-transform: uppercase; 
    min-width: 0; 
}

/* ── File list ─────────────────── */
.file-item { 
    font-size: 11px; 
    font-family: monospace; 
    min-width: 0; 
    color: #4aa3df; 
}
.file-category { 
    font-size: 10px; 
    color: #4aa3df; 
    min-width: 0; 
    transition: all 0.2s ease;
}
.file-category:hover { 
    color: #6bcfff; 
    background-color: #0a0a0a;
}
.block-name { 
    font-size: 11px; 
    font-family: monospace; 
    min-width: 0; 
    color: #4aa3df; 
}

/* ── Block cards ─────────────────── */
.block-card { 
    background-color: #000000; 
    border-radius: 6px; 
    border: 1px solid #2a2a2a; 
    margin-bottom: 4px; 
    min-width: 0; 
    transition: all 0.2s ease;
}
.block-card:hover { 
    border-color: #6bcfff; 
    background-color: #0a0a0a;
}

/* ── Type badges ─────────────────── */
.block-badge { 
    font-size: 9px; 
    font-weight: bold; 
    border-radius: 4px; 
    padding: 1px 4px; 
    min-width: 0; 
    background-color: #111111;
    color: #4aa3df;
    border: 1px solid #2a2a2a;
    transition: all 0.2s ease;
}
.block-badge:hover {
    border-color: #6bcfff;
    background-color: #0a0a0a;
    color: #6bcfff;
}
.badge-import, .badge-style, .badge-style_rule { border-color: #3498db; }
.badge-class { border-color: #3498db; }
.badge-function, .badge-script_block { border-color: #9b59b6; }
.badge-template, .badge-template_part, .badge-django_block { border-color: #e67e22; }
.badge-script, .badge-c_block { border-color: #f1c40f; }
.badge-separator, .badge-other { border-color: #333; }

/* ── Block action buttons ─────────────────── */
.block-action-btn { 
    font-size: 10px; 
    background: #000000; 
    border: 1px solid #2a2a2a; 
    border-radius: 4px; 
    padding: 2px 5px; 
    min-width: 0; 
    color: #4aa3df;
    transition: all 0.2s ease;
}
.block-action-btn:hover { 
    background-color: #0a0a0a; 
    border-color: #6bcfff;
    color: #6bcfff;
}

/* ── Code editor ─────────────────── */
.code-editor { 
    font-family: monospace; 
    font-size: 9px; 
    background-color: #000000; 
    color: #4aa3df; 
    min-width: 0; 
    border: 1px solid #2a2a2a;
    transition: all 0.2s ease;
}
.code-editor:focus {
    border-color: #6bcfff;
    background-color: #050505;
}

/* ── Save buttons ─────────────────── */
.save-btn, .save-file-btn { 
    background-color: #000000; 
    color: #4aa3df; 
    border: 1px solid #2ecc71; 
    border-radius: 4px; 
    min-width: 0;
    transition: all 0.2s ease;
}
.save-btn:hover, .save-file-btn:hover {
    background-color: #0a0a0a;
    border-color: #6bcfff;
    color: #6bcfff;
}
.cancel-btn { 
    background-color: #000000; 
    color: #4aa3df; 
    border: 1px solid #e74c3c; 
    border-radius: 4px; 
    min-width: 0;
    transition: all 0.2s ease;
}
.cancel-btn:hover {
    background-color: #0a0a0a;
    border-color: #6bcfff;
    color: #6bcfff;
}

/* ── Control panel buttons ─────────────────── */
.ctrl-btn, .ctrl-btn-small, .toolbar-btn { 
    background-color: #000000; 
    border: 1px solid #333; 
    border-radius: 4px; 
    font-size: 10px; 
    padding: 3px 6px; 
    min-width: 0; 
    color: #4aa3df;
    transition: all 0.2s ease;
}
.ctrl-btn:hover, .ctrl-btn-small:hover, .toolbar-btn:hover {
    background-color: #0a0a0a;
    border-color: #6bcfff;
    color: #6bcfff;
}
.ctrl-btn-start { 
    background-color: #000000; 
    color: #4aa3df; 
    border-color: #2ecc71; 
    border-radius: 4px; 
    font-size: 10px; 
    padding: 3px 6px; 
    min-width: 0;
    transition: all 0.2s ease;
}
.ctrl-btn-start:hover {
    background-color: #0a0a0a;
    border-color: #6bcfff;
    color: #6bcfff;
}
.ctrl-btn-stop { 
    background-color: #000000; 
    color: #4aa3df; 
    border-color: #e74c3c; 
    border-radius: 4px; 
    font-size: 10px; 
    padding: 3px 6px; 
    min-width: 0;
    transition: all 0.2s ease;
}
.ctrl-btn-stop:hover {
    background-color: #0a0a0a;
    border-color: #6bcfff;
    color: #6bcfff;
}
.ctrl-btn-warn { 
    background-color: #000000; 
    color: #4aa3df; 
    border-color: #f39c12; 
    border-radius: 4px; 
    font-size: 10px; 
    padding: 3px 6px; 
    min-width: 0;
    transition: all 0.2s ease;
}
.ctrl-btn-warn:hover {
    background-color: #0a0a0a;
    border-color: #6bcfff;
    color: #6bcfff;
}

/* ── Status indicators ─────────────────── */
.status-dot-off { color: #333; }
.status-dot-on  { color: #2ecc71; }

/* ── Terminal Panel ─────────────────── */
.terminal-panel { 
    background-color: #000000; 
    border-top: 1px solid #3c3c3c; 
}
.terminal-title { 
    font-size: 11px; 
    font-weight: bold; 
    color: #4aa3df; 
    text-transform: uppercase; 
}
.log-view { 
    font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace; 
    font-size: 12px; 
    background-color: #000000 !important; 
    color: #4aa3df !important; 
    padding: 8px; 
    min-width: 0; 
}
.terminal-prompt { 
    color: #4aa3df; 
    font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace; 
    font-weight: bold; 
    font-size: 12px; 
    margin-right: 4px; 
}
.terminal-input { 
    background-color: #000000; 
    color: #4aa3df; 
    border: 1px solid #3c3c3c; 
    border-radius: 4px; 
    font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace; 
    font-size: 12px; 
    padding: 4px 8px;
    transition: all 0.2s ease;
}
.terminal-input:focus { 
    border-color: #6bcfff; 
    outline: none;
    background-color: #0a0a0a;
}
.terminal-input:hover {
    border-color: #6bcfff;
}

/* ── Chat (Élaborateur / Analyseur de logs) ─────────────────── */
.chat-scroll {
    background-color: #000000;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
}
.chat-bubble-user {
    background-color: #0a2a3a;
    color: #6bcfff;
    border: 1px solid #2a5a7a;
    border-radius: 12px 12px 2px 12px;
    padding: 8px 12px;
}
.chat-bubble-ai {
    background-color: #0a0a0a;
    color: #4aa3df;
    border: 1px solid #2a2a2a;
    border-radius: 12px 12px 12px 2px;
    padding: 8px 12px;
    font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 12px;
}
.chat-bubble-sender {
    font-size: 9px;
    font-weight: bold;
    text-transform: uppercase;
    color: #6bcfff;
    opacity: 0.7;
}
.chat-bubble-copy-btn {
    min-width: 20px;
    min-height: 20px;
    padding: 2px;
    opacity: 0.5;
    background: transparent;
    border: none;
}
.chat-bubble-copy-btn:hover {
    opacity: 1;
    background-color: rgba(107, 207, 255, 0.15);
}
/* Bouton ✅ Valider : même taille que le bouton copier, mais reste
 * discret quand la réponse n'est pas encore validée. Une fois validé
 * (classe `validated` ajoutée par _ChatView._render_validate_icon), il
 * passe en vert pour donner un retour visuel clair. Cohérent avec
 * la palette sombre du chat. */
.chat-bubble-validate-btn {
    min-width: 20px;
    min-height: 20px;
    padding: 2px;
    opacity: 0.5;
    background: transparent;
    border: none;
}
.chat-bubble-validate-btn:hover {
    opacity: 1;
    background-color: rgba(107, 207, 255, 0.15);
}
.chat-bubble-validate-btn.validated {
    opacity: 1;
    color: #4ade80;
    background-color: rgba(74, 222, 128, 0.12);
}
.chat-bubble-validate-btn.validated:hover {
    background-color: rgba(74, 222, 128, 0.22);
}
.chat-input-bar {
    background-color: #000000;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 4px;
}
.chat-role-combo {
    min-width: 0;
}

/* ── Scrollbars (partout dans l'app) ─────────────────────────
   Sur écran tactile, GTK affiche par défaut des scrollbars "mode tactile"
   épaisses qui peuvent recouvrir du contenu dans les panneaux étroits
   (explorateur, Terminal Log...). Règle globale pour rester fin partout,
   tout en gardant une zone cliquable/tactile correcte (8px). */
scrollbar {
    min-width: 8px;
    min-height: 8px;
}
scrollbar slider {
    min-width: 8px;
    min-height: 8px;
    opacity: 0.5;
}
scrollbar slider:hover {
    opacity: 0.8;
}

/* ── Barre d'icônes de l'explorateur (📄🕒➕📥🙈🔄☑️) ─────────
   Enveloppée dans un ScrolledWindow horizontal pour ne pas déborder de la
   fenêtre. Encore plus fine que la règle globale ci-dessus, car purement
   décorative ici (juste pour ne pas gêner les boutons juste au-dessus). */
.nav-bar-scroll scrollbar {
    min-height: 4px;
}
.nav-bar-scroll scrollbar slider {
    min-height: 4px;
    opacity: 0.5;
}

/* ── Barres d'outils compactes (explorateur, panneau de contrôle) ── */
.nav-icon-btn {
    padding: 2px 4px;
    min-width: 24px;
    min-height: 24px;
    font-size: 11px;
}

/* ── Editor toolbar ─────────────────── */
.toolbar-label { 
    font-size: 11px; 
    color: #4aa3df; 
    min-width: 0; 
}
.block-count-badge { 
    font-size: 10px; 
    font-weight: bold; 
    background-color: #000000; 
    color: #4aa3df; 
    border-radius: 4px; 
    padding: 1px 6px; 
    min-width: 0;
    border: 1px solid #2a2a2a;
    transition: all 0.2s ease;
}
.block-count-badge:hover {
    border-color: #6bcfff;
    background-color: #0a0a0a;
    color: #6bcfff;
}
.editor-file-label { 
    font-size: 12px; 
    font-weight: bold; 
    min-width: 0; 
    color: #4aa3df; 
}

/* ── Bottom accent bar of cards ─────────────────── */
.block-accent-bar { min-height: 2px; min-width: 0; }
.accent-function, .accent-script_block { background-color: #9b59b6; }
.accent-class { background-color: #3498db; }
.accent-import, .accent-style { background-color: #2980b9; }
.accent-django_block { background-color: #e67e22; }
.accent-script, .accent-c_block { background-color: #f1c40f; }
.accent-separator { background-color: #333; }
.accent-other, .accent-template_part { background-color: #222; }

/* ── Tabs System ─────────────────── */
.tab-bar { 
    background-color: #000000; 
    border-bottom: 1px solid #333; 
    min-height: 35px; 
}
.tab-button { 
    background-color: #000000; 
    border-radius: 4px 4px 0 0; 
    padding: 4px 8px; 
    border: 1px solid #333; 
    border-bottom: none;
    transition: all 0.2s ease;
}
.tab-button:hover { 
    background-color: #0a0a0a; 
    border-color: #6bcfff;
}
.tab-button.active-tab { 
    background-color: #000000; 
    border-top: 2px solid #6bcfff; 
}
.tab-button label { 
    color: #4aa3df; 
    font-size: 12px; 
}
.tab-button button { 
    min-width: 20px; 
    min-height: 20px; 
    padding: 0; 
}

/* ── Light theme override - DÉSACTIVÉ (tout en noir) ─────────────────── */
.theme-light window, .theme-light dialog, .theme-light popover { 
    background-color: #000000; 
    color: #4aa3df; 
}
.theme-light .block-card { 
    background-color: #000000; 
    border-color: #2a2a2a; 
}
.theme-light .code-editor { 
    background-color: #000000; 
    color: #4aa3df; 
}
.theme-light .log-view { 
    background-color: #000000 !important; 
    color: #4aa3df !important; 
}
.theme-light .ctrl-btn, .theme-light .toolbar-btn { 
    background-color: #000000; 
    border-color: #333; 
    color: #4aa3df; 
}
.theme-light .terminal-panel { 
    background-color: #000000; 
    border-color: #3c3c3c; 
}
.theme-light .terminal-input { 
    background-color: #000000; 
    color: #4aa3df; 
    border-color: #3c3c3c; 
}
.theme-light .terminal-prompt { 
    color: #4aa3df; 
}
.theme-light .tab-bar { 
    background-color: #000000; 
    border-color: #333; 
}
.theme-light .tab-button { 
    background-color: #000000; 
    border-color: #333; 
}
.theme-light .tab-button label { 
    color: #4aa3df; 
}
.theme-light .tab-button.active-tab { 
    background-color: #000000; 
    border-top-color: #6bcfff; 
}

/* Bouton IA */
.btn-ai { 
    background-color: #000000; 
    color: #4aa3df; 
    border-color: #bb86fc;
    transition: all 0.2s ease;
}
.btn-ai:hover { 
    background-color: #0a0a0a;
    border-color: #6bcfff;
    color: #6bcfff;
}

/* WhatsApp Style Button */
.whatsapp-btn { 
    background-color: #000000; 
    color: #4aa3df; 
    border-radius: 50%; 
    min-width: 40px; 
    min-height: 40px; 
    padding: 0; 
    border: 1px solid #25D366;
    transition: all 0.2s ease;
}
.whatsapp-btn:hover { 
    background-color: #0a0a0a;
    border-color: #6bcfff;
    color: #6bcfff;
}
.whatsapp-btn image { 
    color: #4aa3df; 
}

/* ── Nouveaux Tags pour le Constructeur de Commandes ───────────────── */
.option-tag, .arg-tag { 
    background-color: #000000; 
    color: #4aa3df; 
    border: 1px solid #2ecc71; 
    border-radius: 4px; 
    padding: 2px 6px; 
    font-size: 11px; 
    font-family: monospace;
    transition: all 0.2s ease;
}
.option-tag:hover, .arg-tag:hover {
    background-color: #0a0a0a;
    border-color: #6bcfff;
    color: #6bcfff;
}
.options-container, .args-container { 
    background-color: #000000; 
    border: 1px solid #333; 
    border-radius: 4px; 
    padding: 4px; 
    min-height: 30px; 
}

/* Indentation des blocs enfants */
.child-block { 
    border-left: 2px solid #333; 
    margin-left: 10px; 
}
.block-card { 
    transition: all 0.2s ease; 
}

/* ── Entrées et Listes ─────────────────── */
entry, entryrow {
    background-color: #000000;
    color: #4aa3df;
    border: 1px solid #2a2a2a;
    transition: all 0.2s ease;
}
entry:focus, entryrow:focus {
    border-color: #6bcfff;
    background-color: #0a0a0a;
}
entry:hover, entryrow:hover {
    border-color: #6bcfff;
    background-color: #0a0a0a;
}

listbox, listbox row {
    background-color: #000000;
    color: #4aa3df;
    transition: all 0.2s ease;
}
listbox row:hover {
    background-color: #0a0a0a;
    border-color: #6bcfff;
}

/* ── Sidebar sombre (ex: Documentation Master) ─────────────────── */
/* Classe utilisée par plusieurs panneaux latéraux mais jamais définie :
   sans cette règle le panneau retombe sur le fond clair du thème GTK
   par défaut ("le blanc dérange"). */
.sidebar-bg {
    background-color: #050505;
    border-right: 1px solid #2a2a2a;
}
.sidebar-bg entry {
    background-color: #000000;
}

/* ── Switches et Comboboxes ─────────────────── */
switch {
    background-color: #111111;
    border: 1px solid #2a2a2a;
    transition: all 0.2s ease;
}
switch:hover {
    border-color: #6bcfff;
}
switch:checked {
    background-color: #1a4a2a;
}

comborow, combobox {
    background-color: #000000;
    color: #4aa3df;
    border: 1px solid #2a2a2a;
    transition: all 0.2s ease;
}
comborow:hover, combobox:hover {
    border-color: #6bcfff;
    background-color: #0a0a0a;
}

/* ── Buttons généraux ─────────────────── */
button {
    background-color: #000000;
    color: #4aa3df;
    border: 1px solid #2a2a2a;
    transition: all 0.2s ease;
}
button:hover {
    background-color: #0a0a0a;
    border-color: #6bcfff;
    color: #6bcfff;
}
button:active {
    background-color: #111111;
}

/* ── Status Bar ─────────────────── */
.status-bar {
    background-color: #0a0a0a;
    border-top: 1px solid #2a2a2a;
    min-height: 24px;
    padding: 2px 12px;
}
.status-bar label {
    font-size: 11px;
    font-family: 'Fira Code', 'Consolas', monospace;
    color: #666;
}
.status-bar separator {
    background-color: #2a2a2a;
    min-width: 1px;
}

/* ── Search bar ─────────────────── */
entry.search-entry {
    background-color: #0a0a0a;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    color: #4aa3df;
    padding: 4px 8px;
    font-size: 11px;
}
entry.search-entry:focus {
    border-color: #6bcfff;
}
entry.search-entry::placeholder {
    color: #444;
}

/* ── QR Code dialog ─────────────── */
frame {
    background-color: #000000;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 8px;
}
frame > label {
    color: #4aa3df;
    font-size: 11px;
    font-weight: bold;
}

/* ── Dim label utility ───────────── */
.dim-label {
    color: #666;
}

/* ── Tooltip style ──────────────── */
tooltip {
    background-color: #1a1a1a;
    color: #4aa3df;
    border: 1px solid #333;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}

/* ── Code editor (mono utilitaire) ──────────── */
.mono {
    font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 11px;
}

/* ── Coloration syntaxique custom (fallback si GtkSource lang absent) ──────────── */
/* Ces règles s'appliquent via tags sur le buffer si besoin, mais GtkSource les
   surcharge déjà via son style scheme. On les garde pour cohérence visuelle
   globale sur les zones non-GtkSource (logs, snippets). */
.log-view .syntax-keyword  { color: #c586c0; font-weight: bold; }   /* if, for, def, var, let, const, function */
.log-view .syntax-string   { color: #ce9178; }                       /* "..." '...' `...` */
.log-view .syntax-number   { color: #b5cea8; }                       /* 123 0x1f */
.log-view .syntax-comment  { color: #6a9955; font-style: italic; }   /* // # */
.log-view .syntax-function { color: #dcdcaa; }                       /* nom de fonction */
.log-view .syntax-type     { color: #4ec9b0; }                       /* class, type, struct */
.log-view .syntax-operator { color: #d4d4d4; }                       /* = + - * / < > */
.log-view .syntax-builtin  { color: #9cdcfe; }                       /* true, false, null, self */

/* ── QR code dialog specifics ──────────── */
frame > box > picture {
    background-color: #000000;
    border-radius: 4px;
}

entry.ssl-entry {
    border-color: #2ecc71;
}
entry.wifi-entry {
    border-color: #3498db;
}

.block-search-match {
    border: 1px solid #4aa3df;
}

/* ── Mise en page adaptative (équivalent des media-queries CSS web) ──────────
   GTK4 n'a pas de @media : ces classes sont posées dynamiquement par
   app.py (_on_window_resize) selon la taille/orientation réelle de la fenêtre :
   device-mobile / device-tablet / device-desktop, orientation-portrait / orientation-landscape.
   ────────────────────────────────────────────────────────────────────────── */

/* Mobile : on resserre les marges et réduit un peu le texte pour gagner de la place */
window.device-mobile .control-section-title,
window.device-mobile .panel-title {
    font-size: 10px;
}
window.device-mobile .block-card {
    padding: 4px;
}
window.device-mobile button {
    min-height: 34px; /* cibles tactiles plus grandes sur petit écran */
}

/* Tablette : compromis, légèrement plus compact que le desktop */
window.device-tablet .control-section-title,
window.device-tablet .panel-title {
    font-size: 10.5px;
}

/* Portrait : les panneaux empilés (éditeur au-dessus, console en dessous)
   profitent d'un peu plus de respiration verticale */
window.orientation-portrait .block-card {
    margin-bottom: 6px;
}

/* Desktop large / paysage : densité d'information maximale (comportement historique) */
window.device-desktop .control-section-title,
window.device-desktop .panel-title {
    font-size: 11px;
}
"""
