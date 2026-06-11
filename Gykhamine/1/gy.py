#!/usr/bin/env python3
import os
import shutil
import re

def apply_patch():
    filename = "gy.py"
    backup = "gy.py.bak"
    
    if not os.path.exists(filename):
        print(f"❌ Erreur: Le fichier '{filename}' est introuvable dans ce dossier.")
        return

    # 1. Sauvegarde de sécurité
    shutil.copy2(filename, backup)
    print(f"✅ Sauvegarde de sécurité créée : {backup}")

    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    # ==========================================
    # MODIFICATION 1 : BlockCard _build_header
    # Remplacer l'affichage du nom dynamique par un compteur hiérarchique
    # ==========================================
    
    # On cherche la méthode _build_header dans BlockCard
    old_header_logic = """    def _build_header(self):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        set_margins(header, 8); header.set_margin_start(12)
        header.append(Gtk.Label(label=TYPE_ICONS.get(self.block["type"], "▪"), css_classes=["block-icon"]))
        badge = Gtk.Label(label=self.block["type"].upper()); badge.add_css_class("block-badge"); badge.add_css_class(f"badge-{self.block['type']}"); header.append(badge)
        lbl_name = Gtk.Label(label=self.block["name"]); lbl_name.set_ellipsize(Pango.EllipsizeMode.END); lbl_name.set_hexpand(True); lbl_name.set_xalign(0); lbl_name.set_max_width_chars(40); lbl_name.add_css_class("block-name"); header.append(lbl_name)"""

    new_header_logic = """    def _build_header(self):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        set_margins(header, 8); header.set_margin_start(12)
        header.append(Gtk.Label(label=TYPE_ICONS.get(self.block["type"], "▪"), css_classes=["block-icon"]))
        badge = Gtk.Label(label=self.block["type"].upper()); badge.add_css_class("block-badge"); badge.add_css_class(f"badge-{self.block['type']}"); header.append(badge)
        
        # --- NOUVEAU : Affichage du compteur hiérarchique au lieu du nom ---
        hierarchical_id = self.block.get("hierarchical_id", "")
        lbl_name = Gtk.Label(label=hierarchical_id); lbl_name.set_ellipsize(Pango.EllipsizeMode.NONE); lbl_name.set_hexpand(True); lbl_name.set_xalign(0); lbl_name.add_css_class("block-name"); header.append(lbl_name)"""

    content = content.replace(old_header_logic, new_header_logic)

    # ==========================================
    # MODIFICATION 2 : BlockEditorView _render_blocks_recursive
    # Injecter la logique de calcul du compteur hiérarchique avant le rendu
    # ==========================================

    old_render_recursive = """    def _render_blocks_recursive(self, blocks, container, level=0):
        \"\"\"Rend les blocs et leurs enfants de manière récursive avec indentation.\"\"\"
        for block in blocks:"""

    new_render_recursive = """    def _render_blocks_recursive(self, blocks, container, level=0, parent_prefix=""):
        \"\"\"Rend les blocs et leurs enfants de manière récursive avec indentation et numérotation.\"\"\"
        for index, block in enumerate(blocks):
            # Calcul de l'ID hiérarchique (ex: 1.2.1)
            current_index = index + 1
            if parent_prefix:
                block["hierarchical_id"] = f"{parent_prefix}.{current_index}"
            else:
                block["hierarchical_id"] = str(current_index)
            
            # Le nom interne reste utile pour la logique, mais l'affichage utilise hierarchical_id
            # On garde block["name"] tel quel pour la compatibilité interne si besoin, 
            # mais l'UI utilisera hierarchical_id via la Modif 1."""

    content = content.replace(old_render_recursive, new_render_recursive)

    # Correction de l'appel récursif pour passer le préfixe
    old_recursive_call = """            # Si le bloc a des enfants, on les rend récursivement
            if block.get("children"):
                self._render_blocks_recursive(block["children"], container, level + 1)"""
    
    new_recursive_call = """            # Si le bloc a des enfants, on les rend récursivement en passant le préfixe actuel
            if block.get("children"):
                self._render_blocks_recursive(block["children"], container, level + 1, parent_prefix=block["hierarchical_id"])"""

    # Il peut y avoir plusieurs occurrences de cette fonction (doublons dans le code fourni), on les remplace toutes
    content = content.replace(old_recursive_call, new_recursive_call)

    # ==========================================
    # ÉCRITURE DU FICHIER MODIFIÉ
    # ==========================================
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    print("✅ Patch appliqué avec succès à gy.py !")
    print("💡 Les blocs affichent maintenant un compteur (ex: 1.2.3) au lieu du nom de la première ligne.")
    print("💡 Une sauvegarde est disponible dans gy.py.bak")

if __name__ == "__main__":
    apply_patch()
