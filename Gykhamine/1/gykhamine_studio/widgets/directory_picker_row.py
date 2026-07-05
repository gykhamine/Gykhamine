"""Module généré automatiquement depuis widgets.py - Classe DirectoryPickerRow"""
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
        except Exception as e:
            global_log(f"⚠️ Erreur dans gy.py: {type(e).__name__} - {e}")
    def get_text(self): return self.entry.get_text()


class VolumePickerRow(Adw.ActionRow):
    """Sélecteur de volume/partition basé sur les périphériques réellement
    détectés par le système (via lsblk), présentés dans une liste déroulante.
    Remplace toute saisie manuelle d'UUID : l'utilisateur choisit un volume
    dans une liste, l'UUID exact est récupéré automatiquement en arrière-plan.
    get_uuid_value() retourne l'UUID brut (compatible auto_mount_gy),
    get_device_value() retourne "UUID=xxx" (compatible `mount` / pg_device)."""

    def __init__(self, title, subtitle="", initial_uuid=""):
        super().__init__(title=title, subtitle=subtitle)
        from ..config import list_available_block_devices
        self._devices = list_available_block_devices()

        labels = ["(aucun volume sélectionné)"]
        self._uuid_by_index = [""]
        selected_index = 0
        for i, dev in enumerate(self._devices, start=1):
            size = f", {dev['size']}" if dev.get("size") else ""
            fstype = f", {dev['fstype']}" if dev.get("fstype") else ""
            mp = f" — monté sur {dev['mountpoint']}" if dev.get("mountpoint") else ""
            labels.append(f"{dev['device']} — {dev['label']}{size}{fstype}{mp}")
            self._uuid_by_index.append(dev["uuid"])
            if initial_uuid and dev["uuid"] == initial_uuid:
                selected_index = i

        self.dropdown = Gtk.DropDown.new_from_strings(labels)
        self.dropdown.set_selected(selected_index)
        self.dropdown.set_valign(Gtk.Align.CENTER)
        self.add_suffix(self.dropdown)

        btn_refresh = Gtk.Button(icon_name="view-refresh-symbolic")
        btn_refresh.set_tooltip_text("Actualiser la liste des volumes détectés")
        btn_refresh.set_valign(Gtk.Align.CENTER)
        btn_refresh.connect("clicked", self._on_refresh)
        self.add_suffix(btn_refresh)

        if not self._devices:
            self.set_subtitle((subtitle + " — " if subtitle else "") + "⚠️ Aucun volume détecté (lsblk indisponible ou aucune partition visible)")

    def _on_refresh(self, *_):
        from ..config import list_available_block_devices
        current_uuid = self.get_uuid_value()
        self._devices = list_available_block_devices()
        labels = ["(aucun volume sélectionné)"]
        self._uuid_by_index = [""]
        selected_index = 0
        for i, dev in enumerate(self._devices, start=1):
            size = f", {dev['size']}" if dev.get("size") else ""
            fstype = f", {dev['fstype']}" if dev.get("fstype") else ""
            mp = f" — monté sur {dev['mountpoint']}" if dev.get("mountpoint") else ""
            labels.append(f"{dev['device']} — {dev['label']}{size}{fstype}{mp}")
            self._uuid_by_index.append(dev["uuid"])
            if current_uuid and dev["uuid"] == current_uuid:
                selected_index = i
        new_model = Gtk.StringList.new(labels)
        self.dropdown.set_model(new_model)
        self.dropdown.set_selected(selected_index)

    def get_uuid_value(self) -> str:
        idx = self.dropdown.get_selected()
        if idx == Gtk.INVALID_LIST_POSITION or idx >= len(self._uuid_by_index):
            return ""
        return self._uuid_by_index[idx]

    def get_device_value(self) -> str:
        uuid = self.get_uuid_value()
        return f"UUID={uuid}" if uuid else ""


