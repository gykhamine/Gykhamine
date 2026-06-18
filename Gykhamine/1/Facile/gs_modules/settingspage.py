import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, Gio
import sys, os

from .utils import (
    CSS, lbl, btn, combo, entry, hbox, vbox, 
    scroll_wrap, margins, Gen
)
from .genpage import GenPage

class SettingsPage(GenPage):
    def __init__(self):
        super().__init__("Settings")
        # Section 1 — Global
        self.form_box.append(self._section("1. CONFIGURATION GLOBALE"))
        g = Gtk.Grid(); g.set_column_spacing(10); g.set_row_spacing(6)
        self.e_secret  = entry("", "django-insecure-change-me-in-production")
        self.chk_debug = Gtk.CheckButton.new_with_label("DEBUG=True")
        self.chk_debug.set_active(True)
        self.e_hosts   = entry("", "*")
        self.e_urlconf = entry("", "monprojet.urls")
        for row,(l,w) in enumerate([("Clé Secrète:", self.e_secret),
                                    ("", self.chk_debug),
                                    ("ALLOWED_HOSTS:", self.e_hosts),
                                    ("ROOT_URLCONF:", self.e_urlconf)]):
            if l: g.attach(lbl(l), 0, row, 1, 1)
            g.attach(w, 1, row, 1, 1)
        self.form_box.append(g)
        # Section 2 — Apps & Middleware
        self.form_box.append(self._section("2. APPLICATIONS INSTALLÉES"))
        self.apps_box = vbox(3)
        self.form_box.append(self.apps_box)
        self.form_box.append(btn("➕ App", None, lambda *_: (self._add_row(self.apps_box,"mon_app.apps.MonAppConfig"), self._gen())))
        self.form_box.append(self._section("3. MIDDLEWARE"))
        self.mid_box = vbox(3)
        self.form_box.append(self.mid_box)
        self.form_box.append(btn("➕ Middleware", None, lambda *_: (self._add_row(self.mid_box,"django.middleware.security.SecurityMiddleware"), self._gen())))
        # Section 3 — BDD
        self.form_box.append(self._section("4. BASE DE DONNÉES"))
        g2 = Gtk.Grid(); g2.set_column_spacing(10); g2.set_row_spacing(6)
        self.c_engine = combo([("sqlite3","SQLite3 (local)"),("postgresql","PostgreSQL"),("mysql","MySQL/MariaDB")])
        self.e_dbname = entry("", "db.sqlite3")
        self.e_dbuser = entry("", "")
        self.e_dbpass = entry("", "")
        self.e_dbhost = entry("", "localhost")
        self.e_dbport = Gtk.SpinButton.new_with_range(0, 65535, 1)
        self.e_dbport.set_value(5432)
        for row,(l,w) in enumerate([("Moteur:", self.c_engine),("Nom BDD:", self.e_dbname),
                                    ("Utilisateur:", self.e_dbuser),("Mot de passe:", self.e_dbpass),
                                    ("Hôte:", self.e_dbhost),("Port:", self.e_dbport)]):
            g2.attach(lbl(l), 0, row, 1, 1)
            g2.attach(w, 1, row, 1, 1)
        self.form_box.append(g2)
        self.c_engine.connect("changed", self._gen)
        # Section 4 — Chemins
        self.form_box.append(self._section("5. TEMPLATES & FICHIERS"))
        g3 = Gtk.Grid(); g3.set_column_spacing(10); g3.set_row_spacing(6)
        self.e_tpldir    = entry("", "templates")
        self.e_mediaroot = entry("", "media")
        self.e_mediaurl  = entry("", "/media/")
        self.static_box  = vbox(3)
        for row,(l,w) in enumerate([("Dossier templates:", self.e_tpldir),
                                    ("MEDIA_ROOT:", self.e_mediaroot),
                                    ("MEDIA_URL:", self.e_mediaurl)]):
            g3.attach(lbl(l), 0, row, 1, 1); g3.attach(w, 1, row, 1, 1)
        self.form_box.append(g3)
        self.form_box.append(lbl("Dossiers STATICFILES_DIRS:", "section-title"))
        self.form_box.append(self.static_box)
        self.form_box.append(btn("➕ Dossier static", None, lambda *_: (self._add_row(self.static_box,"static"), self._gen())))
        # Section 5 — i18n & Sécurité
        self.form_box.append(self._section("6. LANGUE & SÉCURITÉ"))
        g4 = Gtk.Grid(); g4.set_column_spacing(10); g4.set_row_spacing(6)
        self.e_lang        = entry("", "fr-fr")
        self.e_tz          = entry("", "Africa/Brazzaville")
        self.chk_csrf      = Gtk.CheckButton.new_with_label("Protection CSRF"); self.chk_csrf.set_active(True)
        self.chk_xss       = Gtk.CheckButton.new_with_label("XSS / Clickjacking"); self.chk_xss.set_active(True)
        self.chk_secookie  = Gtk.CheckButton.new_with_label("Cookies Sécurisés (HTTPS)")
        self.chk_httponly  = Gtk.CheckButton.new_with_label("HttpOnly Cookies"); self.chk_httponly.set_active(True)
        self.e_session_age = entry("", "1209600")
        self.e_login_url   = entry("/login/", "/login/")
        self.e_login_redir = entry("/", "/")
        for row,(l,w) in enumerate([("Langue:", self.e_lang), ("Fuseau Horaire:", self.e_tz),
                                    ("CSRF:", self.chk_csrf), ("XSS:", self.chk_xss),
                                    ("Cookies sécurisés:", self.chk_secookie), ("HttpOnly:", self.chk_httponly),
                                    ("SESSION_COOKIE_AGE:", self.e_session_age),
                                    ("LOGIN_URL:", self.e_login_url), ("Après login:", self.e_login_redir)]):
            if l: g4.attach(lbl(l), 0, row, 1, 1)
            g4.attach(w, 1, row, 1, 1)
        self.form_box.append(g4)
        # Email backend
        self.form_box.append(self._section("7. EMAIL (optionnel)"))
        email_backends = [
            ("","— Désactivé —"),
            ("django.core.mail.backends.smtp.EmailBackend","SMTP réel"),
            ("django.core.mail.backends.console.EmailBackend","Console (debug)"),
            ("django.core.mail.backends.filebased.EmailBackend","Fichier (dev)"),
        ]
        self.c_email = combo(email_backends)
        self.c_email.connect("changed", self._gen)
        self.form_box.append(self.c_email)
        # Initialiser apps/middleware par défaut
        default_apps = [
            "django.contrib.admin","django.contrib.auth",
            "django.contrib.contenttypes","django.contrib.sessions",
            "django.contrib.messages","django.contrib.staticfiles",
        ]
        default_mid = [
            "django.middleware.security.SecurityMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
        ]
        for a in default_apps: self._add_row(self.apps_box, a)
        for m in default_mid:  self._add_row(self.mid_box,  m)
        self._add_row(self.static_box, "static")
        for w in (self.e_secret, self.e_hosts, self.e_urlconf, self.e_tpldir,
                  self.e_mediaroot, self.e_mediaurl, self.e_lang, self.e_tz,
                  self.e_session_age, self.e_login_url, self.e_login_redir,
                  self.e_dbname, self.e_dbuser, self.e_dbpass, self.e_dbhost):
            w.connect("changed", self._gen)
        for chk in (self.chk_debug, self.chk_csrf, self.chk_xss, self.chk_secookie, self.chk_httponly):
            chk.connect("toggled", self._gen)
        self._gen()

    def _add_row(self, box, default):
        row = hbox(6)
        e = entry(text=default)
        e.connect("changed", self._gen)
        b = btn("✕","destructive-action",
                lambda w: (box.remove(row), self._gen()))
        row.append(e); row.append(b)
        box.append(row)

    def _collect(self, box):
        result = []
        child = box.get_first_child()
        while child:
            if isinstance(child, Gtk.Box):
                c = child.get_first_child()
                while c:
                    if isinstance(c, Gtk.Entry):
                        v = c.get_text().strip()
                        if v: result.append(v)
                    c = c.get_next_sibling()
            child = child.get_next_sibling()
        return result

    def _gen(self, *_):
        engine = self.c_engine.get_active_id() or "sqlite3"
        db = {
            'engine': engine,
            'name':   self.e_dbname.get_text() or "db.sqlite3",
            'user':   self.e_dbuser.get_text(),
            'password': self.e_dbpass.get_text(),
            'host':   self.e_dbhost.get_text(),
            'port':   int(self.e_dbport.get_value()),
        }
        email_b = self.c_email.get_active_id() or ""
        self.set_code(Gen.settings({
            'secret_key':    self.e_secret.get_text() or "change-me",
            'debug':         str(self.chk_debug.get_active()),
            'allowed_hosts': [h.strip() for h in self.e_hosts.get_text().split(',') if h.strip()],
            'installed_apps':self._collect(self.apps_box),
            'middleware':    self._collect(self.mid_box),
            'root_urlconf':  self.e_urlconf.get_text() or "monprojet.urls",
            'database':      db,
            'templates_dir': self.e_tpldir.get_text() or "templates",
            'static_dirs':   self._collect(self.static_box),
            'media_root':    self.e_mediaroot.get_text() or "media",
            'media_url':     self.e_mediaurl.get_text() or "/media/",
            'language_code': self.e_lang.get_text() or "fr-fr",
            'time_zone':     self.e_tz.get_text() or "Africa/Brazzaville",
            'csrf':          self.chk_csrf.get_active(),
            'xss':           self.chk_xss.get_active(),
            'secure_cookies':self.chk_secookie.get_active(),
            'http_only':     self.chk_httponly.get_active(),
            'session_age':   self.e_session_age.get_text() or "1209600",
            'login_url':     self.e_login_url.get_text(),
            'login_redirect':self.e_login_redir.get_text(),
            'email_backend': email_b,
        }))