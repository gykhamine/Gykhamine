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

/* ── Coins Arrondis ─────────────────── */
dialog, .rounded-dialog, window.dialog, popover {
    border-radius: 12px;
}

/* ── Panel titles ─────────────────── */
.panel-title, .control-section-title { font-size: 11px; font-weight: bold; color: #4aa3df; text-transform: uppercase; min-width: 0; }

/* ── File list ─────────────────── */
.file-item { font-size: 11px; font-family: monospace; min-width: 0; color: #4aa3df; }
.file-category { font-size: 10px; color: #4aa3df; min-width: 0; }
.file-category:hover { color: #6bcfff; }
.block-name { font-size: 11px; font-family: monospace; min-width: 0; color: #4aa3df; }

/* ── Block cards ─────────────────── */
.block-card { background-color: #111111; border-radius: 6px; border: 1px solid #2a2a2a; margin-bottom: 4px; min-width: 0; }
.block-card:hover { border-color: #444; }

/* ── Type badges ─────────────────── */
.block-badge { font-size: 9px; font-weight: bold; border-radius: 4px; padding: 1px 4px; min-width: 0; }
.badge-import, .badge-style, .badge-style_rule { background-color: #3498db; color: #fff; }
.badge-class { background-color: #3498db; color: #fff; }
.badge-function, .badge-script_block { background-color: #9b59b6; color: #fff; }
.badge-template, .badge-template_part, .badge-django_block { background-color: #e67e22; color: #fff; }
.badge-script, .badge-c_block { background-color: #f1c40f; color: #000; }
.badge-separator, .badge-other { background-color: #333; color: #aaa; }

/* ── Block action buttons ─────────────────── */
.block-action-btn { font-size: 10px; background: transparent; border: 1px solid #2a2a2a; border-radius: 4px; padding: 2px 5px; min-width: 0; color: #4aa3df; }
.block-action-btn:hover { background-color: #1e1e1e; }

/* ── Code editor ─────────────────── */
.code-editor { font-family: monospace; font-size: 9px; background-color: #050505; color: #4aa3df; min-width: 0; }

/* ── Save buttons ─────────────────── */
.save-btn, .save-file-btn { background-color: #1a4a2a; color: #2ecc71; border: 1px solid #2ecc71; border-radius: 4px; min-width: 0; }
.cancel-btn { background-color: #2a1a1a; color: #e74c3c; border: 1px solid #e74c3c; border-radius: 4px; min-width: 0; }

/* ── Control panel buttons ─────────────────── */
.ctrl-btn, .ctrl-btn-small, .toolbar-btn { background-color: #1a1a2a; border: 1px solid #333; border-radius: 4px; font-size: 10px; padding: 3px 6px; min-width: 0; color: #4aa3df; }
.ctrl-btn-start { background-color: #0a2a0a; color: #2ecc71; border-color: #2ecc71; border-radius: 4px; font-size: 10px; padding: 3px 6px; min-width: 0; }
.ctrl-btn-stop { background-color: #2a0a0a; color: #e74c3c; border-color: #e74c3c; border-radius: 4px; font-size: 10px; padding: 3px 6px; min-width: 0; }
.ctrl-btn-warn { background-color: #2a1f0a; color: #f39c12; border-color: #f39c12; border-radius: 4px; font-size: 10px; padding: 3px 6px; min-width: 0; }

/* ── Status indicators ─────────────────── */
.status-dot-off { color: #333; }
.status-dot-on  { color: #2ecc71; }

/* ── Terminal Panel ─────────────────── */
.terminal-panel { background-color: #000000; border-top: 1px solid #3c3c3c; }
.terminal-title { font-size: 11px; font-weight: bold; color: #4aa3df; text-transform: uppercase; }
.log-view { font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 12px; background-color: transparent; color: #4aa3df; padding: 8px; min-width: 0; }
.terminal-prompt { color: #2ecc71; font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace; font-weight: bold; font-size: 12px; margin-right: 4px; }
.terminal-input { background-color: #0d0d0d; color: #4aa3df; border: 1px solid #3c3c3c; border-radius: 4px; font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 12px; padding: 4px 8px; }
.terminal-input:focus { border-color: #007acc; outline: none; }

/* ── Editor toolbar ─────────────────── */
.toolbar-label { font-size: 11px; color: #4aa3df; min-width: 0; }
.block-count-badge { font-size: 10px; font-weight: bold; background-color: #1a1a2a; color: #61afef; border-radius: 4px; padding: 1px 6px; min-width: 0; }
.editor-file-label { font-size: 12px; font-weight: bold; min-width: 0; color: #4aa3df; }

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
.tab-bar { background-color: #0a0a0a; border-bottom: 1px solid #333; min-height: 35px; }
.tab-button { background-color: #151515; border-radius: 4px 4px 0 0; padding: 4px 8px; border: 1px solid #333; border-bottom: none; }
.tab-button:hover { background-color: #1a1a1a; }
.tab-button.active-tab { background-color: #000000; border-top: 2px solid #007acc; }
.tab-button label { color: #4aa3df; font-size: 12px; }
.tab-button button { min-width: 20px; min-height: 20px; padding: 0; }

/* ── Light theme override ─────────────────── */
.theme-light window, .theme-light dialog, .theme-light popover { background-color: #f5f5f5; color: #222; }
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
.btn-ai { background-color: #2a1a3a; color: #bb86fc; border-color: #bb86fc; }
.btn-ai:hover { background-color: #3a2a4a; }

/* WhatsApp Style Button */
.whatsapp-btn { background-color: #25D366; color: white; border-radius: 50%; min-width: 40px; min-height: 40px; padding: 0; border: none; box-shadow: 0 2px 5px rgba(0,0,0,0.3); }
.whatsapp-btn:hover { background-color: #128C7E; }
.whatsapp-btn image { color: white; }

/* ── Nouveaux Tags pour le Constructeur de Commandes ───────────────── */
.option-tag, .arg-tag { background-color: #1a4a2a; color: #2ecc71; border: 1px solid #2ecc71; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-family: monospace; }
.options-container, .args-container { background-color: #0a0a0a; border: 1px solid #333; border-radius: 4px; padding: 4px; min-height: 30px; }

/* Indentation des blocs enfants */
.child-block { border-left: 2px solid #333; margin-left: 10px; }
.block-card { transition: margin-left 0.2s ease; }
"""
