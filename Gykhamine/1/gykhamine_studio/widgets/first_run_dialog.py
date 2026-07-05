"""
Assistant de premier démarrage de Gykhamine Studio.

Affiché une seule fois (tant que la clé "setup_completed" n'est pas True dans
la table `config` de la base SQLite), avant que la fenêtre principale ne lance
quoi que ce soit (llama.cpp, Django, PostgreSQL...). Toutes les valeurs saisies
sont écrites directement dans la base via save_config(), ce qui remplace la
dépendance à un fichier .env externe : Gykhamine Studio n'a plus besoin de lire
un fichier .env pour fonctionner, tout vit dans la DB locale.

Ne duplique pas les réglages avancés (PostgreSQL avancé, NFS, Nginx, SSH...) :
un bouton "Configuration avancée" ouvre directement SettingsDialog pour cela.
"""
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw
from ..config import global_log, set_margins
from ..database import save_config
from .directory_picker_row import VolumePickerRow


class FirstRunWizardDialog(Adw.PreferencesDialog):
    """Configuration graphique essentielle affichée au tout premier démarrage,
    avant le lancement de tout service (llama.cpp, Django, PostgreSQL, Redis)."""

    def __init__(self, parent, config: dict, on_complete):
        super().__init__()
        self.set_title("Bienvenue — Configuration initiale")
        self.config = dict(config)
        self.on_complete = on_complete
        self._rows = {}

        page = Adw.PreferencesPage()
        self.add(page)

        intro_grp = Adw.PreferencesGroup()
        page.add(intro_grp)
        intro_lbl = Gtk.Label(
            label="Configurons Gykhamine Studio avant de démarrer les services.\n"
                  "Ces informations remplacent le fichier .env externe : elles sont "
                  "enregistrées directement dans la base de données locale.",
            wrap=True, xalign=0
        )
        set_margins(intro_lbl, 8)
        intro_grp.add(intro_lbl)

        # ── llama.cpp (moteur IA local) ────────────────────────────────
        grp_llama = Adw.PreferencesGroup(title="🤖 Moteur IA (llama.cpp)")
        page.add(grp_llama)
        for key, title, placeholder in [
            ("llama_server_path", "Chemin de llama-server", "/usr/local/bin/llama-server"),
            ("llama_model_path", "Chemin du modèle .gguf", "/models/qwen2.5-coder.gguf"),
            ("llama_host", "Host", "127.0.0.1"),
            ("llama_port", "Port", "8080"),
        ]:
            row = Adw.EntryRow(title=title)
            row.set_text(str(self.config.get(key, "") or placeholder))
            self._rows[key] = row
            grp_llama.add(row)

        # ── Volumes / partitions (sélection backend, jamais d'UUID saisi à la main) ──
        grp_volumes = Adw.PreferencesGroup(
            title="💾 Partitions",
            description="Choisissez les volumes détectés par le système. L'UUID exact est récupéré automatiquement — vous n'avez jamais à le saisir."
        )
        page.add(grp_volumes)

        gy_uuid_row = VolumePickerRow(
            title="Partition Gykhamine (GY)",
            subtitle="Volume contenant les données et modèles Gykhamine",
            initial_uuid=self.config.get("gy_partition_uuid", ""),
        )
        self._rows["gy_partition_uuid"] = gy_uuid_row
        grp_volumes.add(gy_uuid_row)

        pg_uuid_row = VolumePickerRow(
            title="Partition PostgreSQL",
            subtitle="Volume dédié aux données PostgreSQL (optionnel)",
            initial_uuid=(self.config.get("pg_device", "") or "").replace("UUID=", ""),
        )
        self._rows["pg_device"] = pg_uuid_row
        grp_volumes.add(pg_uuid_row)

        # ── PostgreSQL ──────────────────────────────────────────────────
        grp_pg = Adw.PreferencesGroup(title="🐘 Base de données (PostgreSQL)")
        page.add(grp_pg)
        for key, title, placeholder in [
            ("pg_db_name", "Nom de la base de données", "ma_base"),
            ("pg_db_user", "Utilisateur PostgreSQL", "mon_user"),
            ("pg_db_password", "Mot de passe PostgreSQL", ""),
        ]:
            row = Adw.EntryRow(title=title)
            row.set_text(str(self.config.get(key, "") or placeholder if key != "pg_db_password" else self.config.get(key, "")))
            if key == "pg_db_password":
                row.set_input_purpose(Gtk.InputPurpose.PASSWORD)
            self._rows[key] = row
            grp_pg.add(row)

        # ── Redis ───────────────────────────────────────────────────────
        grp_redis = Adw.PreferencesGroup(title="🔴 Redis")
        page.add(grp_redis)
        redis_port_row = Adw.EntryRow(title="Port")
        redis_port_row.set_text(str(self.config.get("redis_port", "") or "6379"))
        self._rows["redis_port"] = redis_port_row
        grp_redis.add(redis_port_row)

        # ── Ports de développement ───────────────────────────────────────
        grp_ports = Adw.PreferencesGroup(title="🔌 Plage de ports pour le serveur Django dev")
        page.add(grp_ports)
        for key, title, placeholder in [
            ("default_port_range_start", "Début", "8000"),
            ("default_port_range_end", "Fin", "8010"),
        ]:
            row = Adw.EntryRow(title=title)
            row.set_text(str(self.config.get(key, "") or placeholder))
            self._rows[key] = row
            grp_ports.add(row)

        # ── Actions ───────────────────────────────────────────────────────
        grp_actions = Adw.PreferencesGroup()
        page.add(grp_actions)
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        set_margins(action_box, 4)

        btn_advanced = Gtk.Button(label="⚙️ Configuration avancée…")
        btn_advanced.connect("clicked", self._open_advanced_settings)
        action_box.append(btn_advanced)

        spacer = Gtk.Box(hexpand=True)
        action_box.append(spacer)

        btn_start = Gtk.Button(label="✅ Enregistrer et démarrer")
        btn_start.add_css_class("suggested-action")
        btn_start.connect("clicked", self._do_complete)
        action_box.append(btn_start)

        grp_actions.add(action_box)

        # Empêche de fermer l'assistant sans configurer (premier démarrage
        # uniquement) : le bouton "Enregistrer et démarrer" est le seul moyen
        # normal de continuer, mais on n'empêche pas la fermeture système par
        # sécurité (évite de bloquer l'utilisateur s'il ferme par erreur).
        self.connect("closed", self._on_closed_without_save)
        self._saved = False

    def _open_advanced_settings(self, *_):
        # Import différé pour éviter toute dépendance circulaire avec settings_dialog.py
        from .settings_dialog import SettingsDialog
        current = self._collect_values(partial=True)
        dialog = SettingsDialog(self, current, self._on_advanced_saved)
        dialog.present(self)

    def _on_advanced_saved(self, new_config: dict):
        self.config = new_config
        for key, row in self._rows.items():
            if key not in self.config:
                continue
            if isinstance(row, Adw.EntryRow):
                row.set_text(str(self.config.get(key, "")))
            # VolumePickerRow n'est volontairement pas resynchronisé ici : sa
            # valeur vient toujours d'une sélection dans la liste des volumes
            # détectés, jamais d'un texte à réappliquer.

    def _collect_values(self, partial: bool = False) -> dict:
        cfg = dict(self.config)
        for key, row in self._rows.items():
            if isinstance(row, Adw.EntryRow):
                cfg[key] = row.get_text()
            elif isinstance(row, VolumePickerRow):
                cfg[key] = row.get_uuid_value() if key == "gy_partition_uuid" else row.get_device_value()
        try:
            cfg["default_port_range_start"] = int(cfg.get("default_port_range_start", 8000) or 8000)
            cfg["default_port_range_end"] = int(cfg.get("default_port_range_end", 8010) or 8010)
        except Exception as e:
            global_log(f"⚠️ Erreur conversion ports (premier démarrage): {e}")
        return cfg

    def _do_complete(self, *_):
        cfg = self._collect_values()
        cfg["setup_completed"] = True
        save_config(cfg)
        self._saved = True
        self.config = cfg
        self.on_complete(cfg)
        self.close()

    def _on_closed_without_save(self, *_):
        if not self._saved:
            # L'utilisateur a fermé sans valider : on enregistre quand même ce
            # qui a été saisi pour ne pas perdre sa saisie, mais on ne marque
            # pas le setup comme terminé — l'assistant réapparaîtra au
            # prochain démarrage tant qu'il n'aura pas cliqué "Démarrer".
            cfg = self._collect_values()
            save_config(cfg)
            global_log("⚠️ Configuration initiale fermée sans validation — elle réapparaîtra au prochain démarrage.")
