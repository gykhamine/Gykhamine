import gi
import os
import sys
import re
import json
import hashlib
import time
import sqlite3
import requests
import shutil
import threading
import subprocess

from pathlib import Path
from datetime import datetime

gi.require_version("Gtk", "4.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gtk, GLib


SCRIPT_DIR = Path(__file__).parent.resolve()


class SplashApplication(Gtk.Application):

    def __init__(self):
        super().__init__(application_id="com.gci.splash")

        self.width = 700
        self.height = 300

        self.etapes = [
            (
                "🎮",
                "#3498db",
                ["🕹️", "👾", "🖱️", "⌨️", "📺", "🔌", "💾", "💿", "🕹️", "🎯"],
            ),
            (
                "🎸",
                "#e74c3c",
                ["🎵", "🎼", "🎹", "🥁", "🎻", "🎷", "🎺", "🎶", "🎤", "🎧"],
            ),
            (
                "🌍",
                "#2ecc71",
                ["🌱", "🌳", "🏔️", "🌊", "🌬️", "☀️", "🌙", "🌦️", "🌋", "🏜️"],
            ),
            (
                "🛬",
                "#9b59b6",
                ["🛫", "☁️", "🛂", "🗺️", "🧳", "🏨", "🚆", "🚕", "🏢", "🏘️"],
            ),
            (
                "💻",
                "#34495e",
                ["⚙️", "🔧", "🛠️", "📐", "📈", "📉", "📁", "📂", "🔋", "🔌"],
            ),
            (
                "🏆",
                "#f1c40f",
                ["🥇", "🥈", "🥉", "🏅", "🎖️", "🥊", "🥋", "💪", "🏃", "🏁"],
            ),
            (
                "👑",
                "#e67e22",
                ["✨", "🛡️", "🏛️", "🕯️", "📖", "📜", "🖋️", "🗝️", "🚪", "🌟"],
            ),
        ]

    def do_activate(self):

        self.fenetre = Gtk.ApplicationWindow(application=self)

        self.fenetre.set_default_size(
            self.width,
            self.height
        )

        self.fenetre.set_decorated(False)

        self.label = Gtk.Label()

        self.label.set_markup(
            '<span font_desc="Arial 110" weight="bold">GCI</span>'
        )

        self.label.set_halign(Gtk.Align.CENTER)
        self.label.set_valign(Gtk.Align.CENTER)

        self.fenetre.set_child(self.label)
        self.fenetre.present()

        GLib.timeout_add(
            7000,
            self.demarrer_animation
        )

    def demarrer_animation(self):
        threading.Thread(
            target=self.animer_histoire,
            daemon=True
        ).start()

        return False

    def install_desktop_files_startup(self):
        """
        Copie les fichiers .desktop de ./Bureau
        vers /usr/share/applications
        """

        source_dir = SCRIPT_DIR / "Bureau"
        dest_dir = Path("/usr/share/applications")

        if not source_dir.exists():
            return

        desktop_files = list(
            source_dir.glob("*.desktop")
        )

        if not desktop_files:
            return

        files_to_copy = []

        for f in desktop_files:
            if not (dest_dir / f.name).exists():
                files_to_copy.append(f)

        if not files_to_copy:
            return

        print(
            f"📂 Détection de "
            f"{len(files_to_copy)} raccourci(s) à installer..."
        )

        remaining = []

        for f in files_to_copy:

            try:

                if not os.access(dest_dir, os.W_OK):
                    raise PermissionError(
                        "Accès refusé"
                    )

                shutil.copy2(
                    f,
                    dest_dir / f.name
                )

                os.chmod(
                    dest_dir / f.name,
                    0o644
                )

                print(
                    f"   ✅ Copié : {f.name}"
                )

            except (PermissionError, OSError):

                remaining.append(f)

        if remaining:

            bash_cmd = ""

            for f in remaining:

                bash_cmd += (
                    f"cp '{f}' '{dest_dir}/' && "
                    f"chmod 644 '{dest_dir}/{f.name}' ; "
                )

            try:

                print(
                    "⚠️ Droits insuffisants. "
                    "Demande de privilèges sudo..."
                )

                subprocess.run(
                    ["sudo", "bash", "-c", bash_cmd],
                    check=True
                )

                print(
                    "✅ Installation réussie via sudo."
                )

            except Exception as e:

                print(
                    f"❌ Échec de l'installation : {e}"
                )

    def animer_histoire(self):

        for icone_finale, couleur, enfants in self.etapes:

            for i in range(25):

                symbole = enfants[
                    i % len(enfants)
                ]

                GLib.idle_add(
                    self.mettre_a_jour_label,
                    symbole,
                    "gray"
                )

                time.sleep(0.060)

            GLib.idle_add(
                self.mettre_a_jour_label,
                icone_finale,
                couleur
            )

            # Installation au moment exact où 💻 apparaît
            if icone_finale == "💻":

                threading.Thread(
                    target=self.install_desktop_files_startup,
                    daemon=True
                ).start()

            time.sleep(1.200)

        time.sleep(2.0)

        GLib.idle_add(
            self.quitter_application
        )

    def mettre_a_jour_label(
        self,
        texte,
        couleur
    ):

        markup = (
            f'<span font_desc="Arial 110" '
            f'weight="bold" '
            f'foreground="{couleur}">'
            f'{texte}'
            f'</span>'
        )

        self.label.set_markup(markup)

    def quitter_application(self):

        self.fenetre.close()

        self.quit()


if __name__ == "__main__":

    app = SplashApplication()

    app.run(None)
