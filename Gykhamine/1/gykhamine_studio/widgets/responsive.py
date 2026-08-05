"""Widget racine qui détecte les changements de taille/orientation de la fenêtre.

GTK4 ne propose pas de media-queries en CSS comme le web. Ce composant joue donc
ce rôle côté Python : il surveille la taille réellement allouée à l'interface et,
à chaque changement significatif, prévient l'application (via `on_resize`) pour
qu'elle ajoute/retire des classes CSS (ex: 'compact-mode', 'portrait-mode') et
réorganise ses panneaux (empiler au lieu de juxtaposer, replier l'explorateur...).
"""
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

# Seuils de largeur (en pixels logiques) séparant les gabarits d'interface
MOBILE_MAX_WIDTH = 640     # écran de type téléphone
TABLET_MAX_WIDTH = 960     # écran de type tablette / petit PC


def classify_width(width: int) -> str:
    """Retourne 'mobile', 'tablet' ou 'desktop' selon la largeur disponible."""
    if width <= MOBILE_MAX_WIDTH:
        return "mobile"
    if width <= TABLET_MAX_WIDTH:
        return "tablet"
    return "desktop"


class ResponsiveRoot(Gtk.Box):
    """Box racine de la fenêtre : surveille sa propre taille allouée et notifie
    l'application uniquement quand le "gabarit" (taille/orientation) change réellement,
    pour éviter de réorganiser l'UI à chaque pixel de redimensionnement."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_resize = None  # callback(width, height, device_class, is_portrait)
        self._last_bucket = None

    def do_size_allocate(self, width, height, baseline):
        Gtk.Box.do_size_allocate(self, width, height, baseline)
        if width <= 0 or height <= 0:
            return
        device_class = classify_width(width)
        is_portrait = height > width
        bucket = (device_class, is_portrait)
        if bucket != self._last_bucket:
            self._last_bucket = bucket
            if self.on_resize:
                self.on_resize(width, height, device_class, is_portrait)
