import gi
from gi.repository import Gtk, Adw, Gdk, Gio
import sys, os

CSS = """
window, dialog, .dialog-vbox, box, scrolledwindow, viewport, popover, headerbar {
background-color: #0a0a0f;
color: #c8d0e0;
}
label { color: #c8d0e0; }
entry, spinbutton {
background-color: #12121a;
color: #e0e8ff;
border: 1px solid #2a2a44;
border-radius: 5px;
padding: 5px 8px;
}
entry:focus { border-color: #4a90d9; }
button {
background-color: #1a1a2a;
color: #6ab0f5;
border: 1px solid #2a3a5a;
border-radius: 5px;
padding: 5px 12px;
font-size: 12px;
}
button:hover { background-color: #22223a; }
button.suggested-action {
background-color: #0d3b6e;
color: #90c8ff;
border-color: #4a90d9;
font-weight: bold;
}
button.destructive-action {
background-color: #2a0a0a;
color: #e05050;
border-color: #8a2020;
}
combobox, combobox button {
background-color: #12121a;
color: #e0e8ff;
border: 1px solid #2a2a44;
border-radius: 5px;
}
checkbutton { color: #c8d0e0; }
checkbutton check {
background-color: #12121a;
border: 1px solid #2a2a44;
}
checkbutton check:checked { background-color: #0d3b6e; }
notebook tab {
background-color: #12121a;
color: #6ab0f5;
padding: 4px 10px;
border-bottom: 2px solid transparent;
}
notebook tab:checked {
border-bottom: 2px solid #4a90d9;
color: #90c8ff;
}
separator { background-color: #1e1e30; min-height: 1px; }
.code-area {
font-family: 'Fira Code', 'Courier New', monospace;
font-size: 12px;
background-color: #060610;
color: #a8b8d8;
padding: 14px;
line-height: 1.5;
}
.heading-blue { font-weight: bold; font-size: 13px; color: #4a90d9; }
.heading-green { font-weight: bold; font-size: 12px; color: #50c878; }
.heading-orange { font-weight: bold; font-size: 12px; color: #e0a030; }
.logic-block {
background-color: #12121a;
border: 1px solid #2a3a5a;
border-radius: 6px;
padding: 6px;
margin-bottom: 3px;
}
.field-row {
background-color: #0e0e1c;
border: 1px solid #1e2e40;
border-radius: 5px;
padding: 5px;
margin-bottom: 3px;
}
.file-panel {
background-color: #06060e;
border-right: 1px solid #1a1a2a;
}
.nav-bar {
background-color: #080812;
border-bottom: 1px solid #1a1a2a;
padding: 4px;
}
.section-title {
font-size: 11px;
font-weight: bold;
color: #3a6a9a;
letter-spacing: 1px;
text-transform: uppercase;
margin-top: 8px;
margin-bottom: 4px;
}
.copy-btn {
background-color: #0d4a2a;
color: #50d890;
border-color: #30a060;
font-weight: bold;
font-size: 13px;
padding: 8px 20px;
}
"""

def lbl(text, css=None):
    w = Gtk.Label(label=text, xalign=0)
    if css:
        w.add_css_class(css)
    return w
def margins(w, v=8, h=8):
    w.set_margin_top(v); w.set_margin_bottom(v)
    w.set_margin_start(h); w.set_margin_end(h)
    return w
def combo(items, active=0):
    """items = list of (id, label) or list of str"""
    c = Gtk.ComboBoxText()
    for item in items:
        if isinstance(item, tuple):
            c.append(item[0], item[1])
        else:
            c.append(item, item)
    c.set_active(active)
    return c
def entry(placeholder="", text="", expand=True):
    e = Gtk.Entry()
    if placeholder: e.set_placeholder_text(placeholder)
    if text: e.set_text(text)
    if expand: e.set_hexpand(True)
    return e
def hbox(spacing=6):
    b = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=spacing)
    return b
def vbox(spacing=8):
    b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
    return b
def scroll_wrap(child, vexpand=True, hexpand=True):
    s = Gtk.ScrolledWindow()
    s.set_vexpand(vexpand); s.set_hexpand(hexpand)
    s.set_child(child)
    return s
def btn(label, css=None, callback=None):
    b = Gtk.Button(label=label)
    if css: b.add_css_class(css)
    if callback: b.connect("clicked", callback)
    return b

class Gen:
    """Moteur de génération de code Django 6.0.5 — zero dépendance."""
    # ── Tous les types de champs Django 6.0.5 ──
    FIELD_TYPES = [
        # Texte
        ("CharField", "Texte Court (CharField)"),
        ("TextField", "Texte Long (TextField)"),
        ("SlugField", "Slug / URL (SlugField)"),
        ("EmailField", "Email (EmailField)"),
        ("URLField", "URL (URLField)"),
        ("UUIDField", "UUID unique (UUIDField)"),
        # Nombres
        ("IntegerField", "Entier (IntegerField)"),
        ("PositiveIntegerField", "Entier Positif"),
        ("SmallIntegerField", "Petit Entier"),
        ("BigIntegerField", "Grand Entier"),
        ("FloatField", "Flottant (FloatField)"),
        ("DecimalField", "Décimal / FCFA (DecimalField)"),
        # Dates
        ("DateField", "Date (DateField)"),
        ("DateTimeField", "Date + Heure (DateTimeField)"),
        ("TimeField", "Heure seule (TimeField)"),
        ("DurationField", "Durée (DurationField)"),
        # Booléens
        ("BooleanField", "Booléen Oui/Non"),
        ("NullBooleanField", "Booléen + Null"),
        # Fichiers
        ("FileField", "Fichier générique"),
        ("ImageField", "Image (ImageField)"),
        ("FilePathField", "Chemin de fichier"),
        # Relations
        ("ForeignKey", "Clé Étrangère (ForeignKey)"),
        ("ManyToManyField", "Plusieurs-à-Plusieurs"),
        ("OneToOneField", "Un-à-Un"),
        # Données structurées
        ("JSONField", "JSON (Django 6.x)"),
        ("ArrayField", "Tableau PostgreSQL"),
        # Auto
        ("AutoField", "ID Auto (AutoField)"),
        ("BigAutoField", "ID BigAuto"),
        # Autres
        ("GenericIPAddressField", "Adresse IP"),
        ("BinaryField", "Données binaires"),
    ]
    # ── Options ORM vues ──
    ORM_ACTIONS = [
        ("none",        "Aucune opération ORM"),
        ("all",         "Tout récupérer — .all()"),
        ("filter",      "Filtrer — .filter(actif=True)"),
        ("get_pk",      "Récupérer par PK — get_object_or_404"),
        ("get_slug",    "Récupérer par slug"),
        ("create",      "Créer — .create(...)"),
        ("save_form",   "Sauvegarder formulaire — form.save()"),
        ("delete_pk",   "Supprimer par PK"),
        ("update",      "Modifier — .update(...)"),
        ("count",       "Compter — .count()"),
        ("order_by",    "Trier — .order_by('-date')"),
        ("annotate",    "Agréger/annoter"),
        ("exists",      "Vérifier existence — .exists()"),
        ("paginate",    "Paginer les résultats"),
        ("search",      "Recherche texte — .filter(Q(...))"),
    ]
    # ── Décorateurs disponibles ──
    DECORATORS = [
        ("login_required",       "Connexion obligatoire"),
        ("staff_member_required","Réservé au staff"),
        ("superuser_required",   "Réservé au super-admin"),
        ("permission_required",  "Permission spécifique"),
        ("cache_page",           "Mise en cache"),
        ("require_http_methods", "Méthodes HTTP restreintes"),
        ("csrf_exempt",          "Exempter CSRF"),
        ("transaction_atomic",   "Transaction atomique"),
    ]
    # ── Types de réponse ──
    RESPONSE_TYPES = [
        ("render",    "HTML — render(request, template)"),
        ("redirect",  "Redirection — redirect(url)"),
        ("json",      "JSON — JsonResponse({...})"),
        ("file",      "Fichier — FileResponse(...)"),
        ("pdf",       "PDF — HttpResponse(PDF)"),
        ("stream",    "Streaming — StreamingHttpResponse"),
        ("http",      "HTTP Simple — HttpResponse('OK')"),
        ("error_404", "Erreur 404 — Http404"),
        ("error_403", "Erreur 403 — PermissionDenied"),
    ]
    # ── Tags HTML ──
    HTML_TAGS = [
        ("div",     "div — Conteneur"),
        ("section", "section — Section sémantique"),
        ("article", "article — Article"),
        ("main",    "main — Contenu principal"),
        ("aside",   "aside — Barre latérale"),
        ("header",  "header — En-tête"),
        ("footer",  "footer — Pied de page"),
        ("nav",     "nav — Navigation"),
        ("h1",      "h1 — Titre niveau 1"),
        ("h2",      "h2 — Titre niveau 2"),
        ("h3",      "h3 — Titre niveau 3"),
        ("h4",      "h4 — Titre niveau 4"),
        ("p",       "p — Paragraphe"),
        ("span",    "span — Texte inline"),
        ("a",       "a — Lien hypertexte"),
        ("button",  "button — Bouton"),
        ("form",    "form — Formulaire"),
        ("table",   "table — Tableau"),
        ("tr",      "tr — Ligne tableau"),
        ("td",      "td — Cellule tableau"),
        ("th",      "th — En-tête cellule"),
        ("ul",      "ul — Liste non ordonnée"),
        ("ol",      "ol — Liste ordonnée"),
        ("li",      "li — Élément de liste"),
        ("img",     "img — Image"),
        ("video",   "video — Vidéo"),
        ("audio",   "audio — Audio"),
        ("input",   "input — Champ"),
        ("select",  "select — Liste déroulante"),
        ("textarea","textarea — Zone de texte"),
        ("label",   "label — Label"),
        ("canvas",  "canvas — Dessin JS"),
        ("iframe",  "iframe — Cadre"),
    ]
    # ── Filtres Django ──
    DJANGO_FILTERS = [
        ("", "— Aucun filtre —"),
        ("|date:'d/m/Y'",     "date — Format jour/mois/année"),
        ("|date:'d/m/Y H:i'", "datetime — Date + heure"),
        ("|time:'H:i'",       "time — Heure:minutes"),
        ("|upper",            "upper — MAJUSCULES"),
        ("|lower",            "lower — minuscules"),
        ("|title",            "title — Première Lettre"),
        ("|capfirst",         "capfirst — Première lettre"),
        ("|truncatechars:50", "truncatechars:50 — Couper 50 car."),
        ("|truncatewords:20", "truncatewords:20 — Couper 20 mots"),
        ("|safe",             "safe — HTML non échappé"),
        ("|escape",           "escape — Échapper HTML"),
        ("|length",           "length — Nombre d'éléments"),
        ("|default:'—'",      "default:'—' — Valeur par défaut"),
        ("|yesno:'Oui,Non'",  "yesno — Oui/Non"),
        ("|floatformat:2",    "floatformat:2 — 2 décimales"),
        ("|intcomma",         "intcomma — 1 000 000"),
        ("|linebreaks",       "linebreaks — Sauts de ligne"),
        ("|urlencode",        "urlencode — Encodage URL"),
        ("|slugify",          "slugify — slug-url"),
        ("|pluralize",        "pluralize — singulier/pluriel"),
        ("|join:', '",        "join — Joindre liste"),
        ("|first",            "first — Premier élément"),
        ("|last",             "last — Dernier élément"),
        ("|add:5",            "add:5 — Ajouter valeur"),
        ("|divisibleby:2",    "divisibleby — Divisible par"),
    ]
    # ── Tags Django template ──
    DJANGO_TAGS = [
        ("for",     "{% for item in liste %} ... {% endfor %}"),
        ("if",      "{% if condition %} ... {% endif %}"),
        ("block",   "{% block nom %} ... {% endblock %}"),
        ("include", "{% include 'partial.html' %}"),
        ("url",     "{% url 'nom_vue' %}"),
        ("static",  "{% static 'css/main.css' %}"),
        ("csrf",    "{% csrf_token %}"),
        ("load",    "{% load static %}"),
        ("with",    "{% with var=valeur %}"),
        ("empty",   "{% empty %} (dans un for)"),
        ("elif",    "{% elif condition %}"),
        ("else",    "{% else %}"),
        ("comment", "{% comment %} ... {% endcomment %}"),
        ("verbatim","{% verbatim %} ... {% endverbatim %}"),
        ("now",     "{% now 'd/m/Y' %}"),
        ("spaceless","{% spaceless %} ... {% endspaceless %}"),
        ("extends", "{% extends 'base.html' %}"),
    ]
    # ── 25 snippets JS réutilisables ──
    JS_SNIPPETS = {
        "camera": ("📷 Accès Caméra",
        """  // Permission Caméra
navigator.mediaDevices.getUserMedia({ video: true })
.then(stream => {
const video = document.querySelector('#camera-preview');
if (video) { video.srcObject = stream; video.play(); }
})
.catch(err => console.error('Caméra refusée:', err));"""),
        "microphone": ("🎤 Accès Microphone",
        """  // Permission Microphone
navigator.mediaDevices.getUserMedia({ audio: true })
.then(stream => console.log('Microphone actif'))
.catch(err => console.error('Micro refusé:', err));"""),
        "notification": ("🔔 Notifications Push",
        """  // Permission Notifications
Notification.requestPermission().then(perm => {
if (perm === 'granted') {
new Notification('GCI', { body: 'Notifications activées !' });
}
});"""),
        "location": ("📍 Géolocalisation",
        """  // Géolocalisation GPS
if (navigator.geolocation) {
navigator.geolocation.getCurrentPosition(
pos => { console.log('Lat:', pos.coords.latitude, 'Lng:', pos.coords.longitude); },
err => console.error('Position refusée:', err)
);
}"""),
        "file_handler": ("📁 Gestion Fichiers",
        """  // Gestion Upload Fichier
const fileInput = document.querySelector('input[type="file"]');
if (fileInput) {
fileInput.addEventListener('change', e => {
const file = e.target.files[0];
console.log('Fichier:', file.name, '| Taille:', file.size, 'octets');
});
}"""),
        "contacts": ("👤 Accès Contacts",
        """  // Accès Contacts (API expérimentale)
if ('contacts' in navigator) {
navigator.contacts.select(['name', 'email'], { multiple: true })
.then(contacts => console.log('Contacts:', contacts))
.catch(err => console.error('Contacts refusés:', err));
}"""),
        "refresh_page": ("🔄 Rafraîchissement Auto",
        """  // Rafraîchissement automatique toutes les 60 secondes
const REFRESH_INTERVAL = 60000;
let refreshTimer = setInterval(() => location.reload(), REFRESH_INTERVAL);
// Annuler: clearInterval(refreshTimer);"""),
        "simple_alert": ("⚠️ Alerte Stylée",
        """  // Alerte dynamique (remplace le alert() natif)
function showAlert(message, type='info') {
const div = document.createElement('div');
div.className = `alert alert-${type}`;
div.style.cssText = 'position:fixed;top:20px;right:20px;padding:15px 25px;'
+ 'background:#0d3b6e;color:#90c8ff;border-radius:8px;z-index:9999;'
+ 'box-shadow:0 4px 15px rgba(0,0,0,0.5);animation:slideIn 0.3s ease;';
div.textContent = message;
document.body.appendChild(div);
setTimeout(() => div.remove(), 4000);
}
showAlert('Bienvenue sur GCI !');"""),
        "anim_fadein": ("✨ Animation FadeIn",
        """  // Animation d'entrée progressive
document.querySelectorAll('.fade-in').forEach((el, i) => {
el.style.opacity = '0';
el.style.transform = 'translateY(20px)';
el.style.transition = `opacity 0.6s ease ${i * 0.1}s, transform 0.6s ease ${i * 0.1}s`;
setTimeout(() => {
el.style.opacity = '1';
el.style.transform = 'translateY(0)';
}, 50);
});"""),
        "theme_toggle": ("🌗 Bascule Thème Clair/Sombre",
        """  // Bascule thème clair/sombre
const themeBtn = document.querySelector('#theme-toggle');
const savedTheme = localStorage.getItem('theme') || 'dark';
document.body.setAttribute('data-theme', savedTheme);
if (themeBtn) {
themeBtn.addEventListener('click', () => {
const current = document.body.getAttribute('data-theme');
const next = current === 'dark' ? 'light' : 'dark';
document.body.setAttribute('data-theme', next);
localStorage.setItem('theme', next);
});
}"""),
        "copy_clipboard": ("📋 Copier dans Presse-papier",
        """  // Boutons Copier dans le presse-papier
document.querySelectorAll('[data-copy]').forEach(btn => {
btn.addEventListener('click', () => {
const text = btn.getAttribute('data-copy');
navigator.clipboard.writeText(text).then(() => {
const orig = btn.textContent;
btn.textContent = '✅ Copié !';
setTimeout(() => btn.textContent = orig, 2000);
});
});
});"""),
        "countdown": ("⏱️ Compte à Rebours",
        """  // Compte à rebours
function startCountdown(targetDate, elementId) {
const el = document.getElementById(elementId);
const timer = setInterval(() => {
const diff = new Date(targetDate) - new Date();
if (diff <= 0) { clearInterval(timer); if(el) el.textContent = 'Terminé!'; return; }
const h = Math.floor(diff/3600000), m = Math.floor((diff%3600000)/60000), s = Math.floor((diff%60000)/1000);
if(el) el.textContent = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}, 1000);
}
// Utilisation : startCountdown('2025-12-31T23:59:59', 'timer-display');"""),
        "live_search": ("🔍 Recherche en Temps Réel",
        """  // Recherche live dans un tableau/liste
const searchInput = document.querySelector('#live-search');
if (searchInput) {
searchInput.addEventListener('input', function() {
const q = this.value.toLowerCase();
document.querySelectorAll('[data-searchable]').forEach(row => {
row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
});
});
}"""),
        "pagination_logic": ("📄 Pagination Côté Client",
        """  // Pagination côté client
const PAGE_SIZE = 10;
let currentPage = 1;
const items = document.querySelectorAll('[data-paginate]');
function showPage(page) {
items.forEach((item, i) => {
item.style.display = (i >= (page-1)*PAGE_SIZE && i < page*PAGE_SIZE) ? '' : 'none';
});
}
document.querySelector('#prev-page')?.addEventListener('click', () => { if(currentPage>1){currentPage--;showPage(currentPage);} });
document.querySelector('#next-page')?.addEventListener('click', () => { if(currentPage*PAGE_SIZE<items.length){currentPage++;showPage(currentPage);} });
showPage(1);"""),
        "infinite_scroll": ("🖱️ Scroll Infini",
        """  // Chargement infini au scroll
let loading = false;
window.addEventListener('scroll', () => {
if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 200 && !loading) {
loading = true;
fetch('/api/items/?page=' + nextPage)
.then(r => r.json())
.then(data => {
// Ajouter les items au DOM
loading = false; nextPage++;
});
}
});"""),
        "fullscreen": ("📱 Mode Plein Écran",
        """  // Basculer plein écran
document.querySelector('#fullscreen-btn')?.addEventListener('click', () => {
if (!document.fullscreenElement) {
document.documentElement.requestFullscreen().catch(e => console.error(e));
} else {
document.exitFullscreen();
}
});"""),
        "online_status": ("🌐 Détection Connexion",
        """  // Détecter l'état de la connexion
function updateOnlineStatus() {
const banner = document.querySelector('#connection-status');
if (banner) {
banner.textContent = navigator.onLine ? '✅ En ligne' : '⚠️ Hors ligne';
banner.style.backgroundColor = navigator.onLine ? '#0d3b1a' : '#3b1a0d';
}
}
window.addEventListener('online', updateOnlineStatus);
window.addEventListener('offline', updateOnlineStatus);
updateOnlineStatus();"""),
        "auto_date": ("📅 Afficher Date Automatique",
        """  // Afficher la date actuelle
document.querySelectorAll('[data-autodate]').forEach(el => {
const fmt = el.getAttribute('data-autodate') || 'full';
const now = new Date();
const opts = fmt === 'full'
? { weekday:'long', year:'numeric', month:'long', day:'numeric' }
: { year:'numeric', month:'2-digit', day:'2-digit' };
el.textContent = now.toLocaleDateString('fr-FR', opts);
});"""),
        "pass_strength": ("🔒 Force du Mot de Passe",
        """  // Indicateur de force du mot de passe
const passInput = document.querySelector('#password-input');
const strengthBar = document.querySelector('#strength-bar');
if (passInput && strengthBar) {
passInput.addEventListener('input', function() {
const v = this.value;
let score = 0;
if (v.length >= 8) score++;
if (/[A-Z]/.test(v)) score++;
if (/[0-9]/.test(v)) score++;
if (/[^A-Za-z0-9]/.test(v)) score++;
const colors = ['#e05050','#e08030','#e0c030','#50c878'];
const labels = ['Faible','Moyen','Bon','Excellent'];
strengthBar.style.width = (score * 25) + '%';
strengthBar.style.backgroundColor = colors[score-1] || '#333';
strengthBar.title = labels[score-1] || '';
});
}"""),
        "email_valid": ("📧 Validation Email Temps Réel",
r"""  // Validation email en temps réel
document.querySelectorAll('input[type="email"]').forEach(input => {
input.addEventListener('blur', function() {
const valid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.value);
this.style.borderColor = valid ? '#50c878' : '#e05050';
let msg = this.nextElementSibling;
if (!msg || !msg.classList.contains('validation-msg')) {
msg = document.createElement('small');
msg.className = 'validation-msg';
this.after(msg);
}
msg.textContent = valid ? '' : '⚠️ Email invalide';
msg.style.color = '#e05050';
});
});"""),
        "lazy_load": ("🖼️ Chargement Différé Images",
        """  // Lazy loading des images
const imageObserver = new IntersectionObserver((entries) => {
entries.forEach(entry => {
if (entry.isIntersecting) {
const img = entry.target;
img.src = img.dataset.src;
img.classList.remove('lazy');
imageObserver.unobserve(img);
}
});
});
document.querySelectorAll('img.lazy').forEach(img => imageObserver.observe(img));"""),
        "audio_player": ("🔊 Lecteur Audio Simple",
        """  // Contrôle lecteur audio
const audioEl = document.querySelector('#main-audio');
document.querySelector('#play-btn')?.addEventListener('click', () => {
if (audioEl) audioEl.paused ? audioEl.play() : audioEl.pause();
});
document.querySelector('#stop-btn')?.addEventListener('click', () => {
if (audioEl) { audioEl.pause(); audioEl.currentTime = 0; }
});"""),
        "video_controls": ("🎥 Contrôles Vidéo Personnalisés",
        """  // Contrôles vidéo personnalisés
const videoEl = document.querySelector('#main-video');
document.querySelector('#video-play')?.addEventListener('click', () => {
videoEl?.paused ? videoEl.play() : videoEl.pause();
});
document.querySelector('#video-fullscreen')?.addEventListener('click', () => {
videoEl?.requestFullscreen?.();
});
if (videoEl) {
videoEl.addEventListener('timeupdate', () => {
const progress = document.querySelector('#video-progress');
if (progress) progress.value = (videoEl.currentTime / videoEl.duration) * 100;
});
}"""),
        "form_ajax": ("🚀 Envoi Formulaire AJAX",
        """  // Envoi de formulaire sans rechargement
document.querySelectorAll('form[data-ajax]').forEach(form => {
form.addEventListener('submit', async (e) => {
e.preventDefault();
const data = new FormData(form);
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
const response = await fetch(form.action || window.location.href, {
method: 'POST',
headers: { 'X-CSRFToken': csrfToken },
body: data
});
const result = await response.json();
const feedback = document.querySelector('#ajax-feedback');
if (feedback) feedback.textContent = result.message || (result.ok ? '✅ Succès !' : '❌ Erreur');
});
});"""),
        "sortable_table": ("📊 Tableau Triable",
        """  // Tableau triable par colonne
document.querySelectorAll('table[data-sortable] th').forEach((th, colIndex) => {
th.style.cursor = 'pointer';
th.addEventListener('click', () => {
const table = th.closest('table');
const tbody = table.querySelector('tbody');
const rows = Array.from(tbody.querySelectorAll('tr'));
const asc = th.dataset.sortDir !== 'asc';
th.dataset.sortDir = asc ? 'asc' : 'desc';
rows.sort((a, b) => {
const aVal = a.cells[colIndex]?.textContent.trim() || '';
const bVal = b.cells[colIndex]?.textContent.trim() || '';
return asc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
});
rows.forEach(row => tbody.appendChild(row));
});
});"""),
    }
    # ══ CSS populaires (100 propriétés) ══
    CSS_PROPERTIES = [
        # Layout
        "display", "flex-direction", "justify-content", "align-items",
        "flex-wrap", "gap", "grid-template-columns", "grid-column",
        "position", "top", "left", "right", "bottom", "z-index",
        "float", "clear", "overflow", "overflow-x", "overflow-y",
        # Dimensions
        "width", "height", "min-width", "max-width", "min-height", "max-height",
        # Espacement
        "margin", "margin-top", "margin-bottom", "margin-left", "margin-right",
        "padding", "padding-top", "padding-bottom", "padding-left", "padding-right",
        # Texte
        "font-family", "font-size", "font-weight", "font-style",
        "color", "text-align", "text-decoration", "text-transform",
        "line-height", "letter-spacing", "word-spacing", "white-space",
        "text-overflow", "word-break",
        # Fond
        "background", "background-color", "background-image",
        "background-size", "background-position", "background-repeat",
        # Bordure
        "border", "border-width", "border-style", "border-color",
        "border-top", "border-bottom", "border-left", "border-right",
        "border-radius", "border-collapse",
        # Ombre / Effets
        "box-shadow", "text-shadow", "opacity", "visibility",
        "filter", "backdrop-filter",
        # Animation
        "transition", "animation", "transform", "transform-origin",
        # Apparence
        "cursor", "pointer-events", "user-select", "resize",
        "outline", "list-style", "object-fit", "object-position",
        # Tableau
        "vertical-align", "table-layout",
        # Print/divers
        "page-break-after", "page-break-before",
    ]
    # ══ Générateurs de code ══
    @staticmethod
    def model(table_name, fields, logic):
        cls = ''.join(w.capitalize() for w in table_name.replace('-','_').split('_'))
        lines = [
            "from django.db import models",
            "from django.core.exceptions import ValidationError",
            "from django.utils.translation import gettext_lazy as _",
            "",
            f"class {cls}(models.Model):",
        ]
        if not fields:
            lines.append("    pass")
        else:
            for f in fields:
                name = f.get('name','').strip()
                ftype = f.get('type','CharField')
                opts = f.get('opts',{})
                if not name: continue
                args = Gen._field_args(ftype, opts)
                lines.append(f"    {name} = models.{ftype}({', '.join(args)})")
        # clean()
        if logic:
            lines += ["", "    def clean(self):", "        super().clean()"]
            for b in logic:
                lines += Gen._logic_to_clean(b, indent=8)
        # __str__
        str_field = next((f['name'] for f in fields if f.get('name') in
                          ['nom','name','titre','title','label','libelle']), None)
        lines += [
            "",
            "    def __str__(self):",
            f"        return str(self.{str_field})" if str_field else "        return str(self.pk)",
            "",
            "    class Meta:",
            f"        db_table = '{table_name}'",
            f"        verbose_name = _('{cls}')",
            f"        verbose_name_plural = _('{cls}s')",
            f"        ordering = ['-id']",
        ]
        return '\n'.join(lines)

    @staticmethod
    def _field_args(ftype, opts):
        args = []
        if ftype == 'CharField':
            args.append(f"max_length={opts.get('max_length',255)}")
        elif ftype == 'DecimalField':
            args.append(f"max_digits={opts.get('max_digits',10)}")
            args.append(f"decimal_places={opts.get('decimal_places',2)}")
        elif ftype in ('ForeignKey','OneToOneField','ManyToManyField'):
            args.append(f"'{opts.get('to','SomeModel')}'")
            if ftype != 'ManyToManyField':
                args.append(f"on_delete=models.{opts.get('on_delete','CASCADE')}")
        elif ftype == 'FilePathField':
            args.append(f"path='{opts.get('path','/')}'")
        elif ftype in ('FileField','ImageField'):
            args.append(f"upload_to='{opts.get('upload_to','uploads/')}'")
        elif ftype == 'UUIDField':
            args.append("default=uuid.uuid4")
            args.append("editable=False")
        elif ftype == 'SlugField':
            args.append(f"max_length={opts.get('max_length',100)}")
        # Options communes
        if opts.get('null'):    args.append("null=True")
        if opts.get('blank'):   args.append("blank=True")
        if opts.get('unique'):  args.append("unique=True")
        if opts.get('db_index'):args.append("db_index=True")
        if opts.get('editable') == False: args.append("editable=False")
        default = opts.get('default')
        if default is not None and default != '':
            if isinstance(default, str) and not default.startswith(('True','False','None','uuid')):
                args.append(f"default='{default}'")
            else:
                args.append(f"default={default}")
        verbose = opts.get('verbose')
        if verbose: args.append(f"verbose_name=_('{verbose}')")
        help_text = opts.get('help_text')
        if help_text: args.append(f"help_text=_('{help_text}')")
        return args

    @staticmethod
    def _logic_to_clean(b, indent=8):
        sp = ' '*indent
        lines = []
        action = b.get('action','')
        field  = b.get('field','')
        value  = b.get('value','')
        if action == 'required':
            lines += [f"{sp}if not self.{field}:", f"{sp}    raise ValidationError(_('{field} est obligatoire.'))"]
        elif action == 'min_value':
            lines += [f"{sp}if self.{field} is not None and self.{field} < {value or 0}:",
                      f"{sp}    raise ValidationError(_('{field} doit être ≥ {value or 0}.'))"]
        elif action == 'max_value':
            lines += [f"{sp}if self.{field} is not None and self.{field} > {value or 999}:",
                      f"{sp}    raise ValidationError(_('{field} doit être ≤ {value or 999}.'))"]
        elif action == 'min_length':
            lines += [f"{sp}if self.{field} and len(self.{field}) < {value or 3}:",
                      f"{sp}    raise ValidationError(_('{field} : minimum {value or 3} caractères.'))"]
        elif action == 'unique_together':
            lines += [f"{sp}# unique_together géré dans Meta"]
        elif action == 'date_future':
            lines += [f"{sp}from django.utils import timezone",
                      f"{sp}if self.{field} and self.{field} < timezone.now().date():",
                      f"{sp}    raise ValidationError(_('{field} doit être dans le futur.'))"]
        elif action == 'positive':
            lines += [f"{sp}if self.{field} is not None and self.{field} <= 0:",
                      f"{sp}    raise ValidationError(_('{field} doit être positif.'))"]
        elif action == 'conditional_required':
            lines += [f"{sp}if self.{field} and not self.{value}:",
                      f"{sp}    raise ValidationError(_('{value} est requis si {field} est renseigné.'))"]
        return lines

    @staticmethod
    def view(name, model, decorators, method, orm_action, response_type, url_params, logic, custom_methods=None):
        imports = [
            "from django.shortcuts import render, redirect, get_object_or_404",
            "from django.http import HttpResponse, JsonResponse, FileResponse, Http404",
            "from django.contrib import messages",
            "from django.core.paginator import Paginator",
            "from django.db.models import Q",
        ]
        dec_imports = {
            'login_required':       "from django.contrib.auth.decorators import login_required",
            'staff_member_required':"from django.contrib.admin.views.decorators import staff_member_required",
            'permission_required':  "from django.contrib.auth.decorators import permission_required",
            'cache_page':           "from django.views.decorators.cache import cache_page",
            'require_http_methods': "from django.views.decorators.http import require_http_methods",
            'csrf_exempt':          "from django.views.decorators.csrf import csrf_exempt",
            'transaction_atomic':   "from django.db import transaction",
        }
        for d in decorators:
            if d in dec_imports: imports.append(dec_imports[d])
        if model: imports.append(f"from .models import {model}")
        lines = imports + [""]
        # Décorateurs
        for d in decorators:
            if d == 'login_required':       lines.append("@login_required")
            elif d == 'staff_member_required': lines.append("@staff_member_required")
            elif d == 'permission_required': lines.append("@permission_required('app.can_view')")
            elif d == 'cache_page':         lines.append("@cache_page(60 * 15)  # 15 minutes")
            elif d == 'require_http_methods': lines.append(f"@require_http_methods(['{method}'])")
            elif d == 'csrf_exempt':        lines.append("@csrf_exempt")
            elif d == 'transaction_atomic': lines.append("@transaction.atomic")
        # Signature
        params = ["request"] + [p.strip() for p in url_params.split(',') if p.strip()]
        lines.append(f"def {name}({', '.join(params)}):")
        # Méthode HTTP
        if method != 'ANY' and 'require_http_methods' not in decorators:
            lines += [f"    if request.method == 'POST':", "        pass  # Traitement POST"]
        # ORM Construction via boutons
        ctx_var = "data"
        if model:
            # Logique ORM avancée
            if orm_action == 'all':
                lines.append(f"    {ctx_var} = {model}.objects.all()")
            elif orm_action == 'filter':
                lines.append(f"    {ctx_var} = {model}.objects.filter(actif=True)")
            elif orm_action == 'get_pk':
                lines.append(f"    obj = get_object_or_404({model}, pk=pk)")
            elif orm_action == 'get_slug':
                lines.append(f"    obj = get_object_or_404({model}, slug=slug)")
            elif orm_action == 'create':
                lines.append(f"    obj = {model}.objects.create()  # passer les données")
            elif orm_action == 'save_form':
                lines += [f"    form = {model}Form(request.POST or None)",
                          f"    if form.is_valid():",
                          f"        form.save()",
                          f"        return redirect('{name}')"]
            elif orm_action == 'delete_pk':
                lines += [f"    obj = get_object_or_404({model}, pk=pk)",
                          f"    obj.delete()",
                          f"    return redirect('{name}')"]
            elif orm_action == 'update':
                lines += [f"    obj = get_object_or_404({model}, pk=pk)",
                          f"    # obj.champ = valeur; obj.save()"]
            elif orm_action == 'count':
                lines.append(f"    total = {model}.objects.count()")
            elif orm_action == 'order_by':
                lines.append(f"    {ctx_var} = {model}.objects.order_by('-id')")
            elif orm_action == 'annotate':
                lines += [f"    from django.db.models import Count, Sum",
                          f"    {ctx_var} = {model}.objects.annotate(total=Count('id'))"]
            elif orm_action == 'exists':
                lines.append(f"    existe = {model}.objects.filter(pk=pk).exists()")
            elif orm_action == 'paginate':
                lines += [f"    qs = {model}.objects.all()",
                          f"    paginator = Paginator(qs, 10)",
                          f"    page = request.GET.get('page')",
                          f"    {ctx_var} = paginator.get_page(page)"]
            elif orm_action == 'search':
                lines += [f"    q = request.GET.get('q', '')",
                          f"    {ctx_var} = {model}.objects.filter(Q(nom__icontains=q)) if q else {model}.objects.all()"]
        # Logique personnalisée (Boutons If/Else/For)
        if custom_methods:
            for m in custom_methods:
                lines += Gen._generate_custom_method(m, indent=4)
        # Logique standard (legacy)
        for b in logic:
            if b.get('action') == 'check_auth':
                lines += ["    if not request.user.is_authenticated:",
                          "        return redirect('login')"]
            elif b.get('action') == 'check_param':
                p = b.get('detail','param')
                lines += [f"    {p} = request.GET.get('{p}')",
                          f"    if not {p}:",
                          f"        return HttpResponse('Paramètre manquant', status=400)"]
            elif b.get('action') == 'check_post_field':
                p = b.get('detail','champ')
                lines += [f"    {p} = request.POST.get('{p}','')",
                          f"    if not {p}:",
                          f"        messages.error(request, '{p} est requis.')"]
            elif b.get('action') == 'log_action':
                lines += ["    import logging",
                          "    logger = logging.getLogger(__name__)",
                          f"    logger.info('Vue {name} appelée par %s', request.user)"]
        # Réponse
        ctx = f"{{'{ctx_var}': {ctx_var}}}" if model and orm_action not in ('none','delete_pk','count','exists') else "{}"
        resp = {
            "render":    f"    return render(request, '{name}.html', {ctx})",
            "redirect":  f"    return redirect('nom_de_la_vue')",
            "json":      f"    return JsonResponse({{{ctx_var}: list({ctx_var}.values()) if hasattr({ctx_var},'values') else str({ctx_var})}})",
            "file":      f"    return FileResponse(open('chemin/fichier.pdf', 'rb'))",
            "pdf":       "    response = HttpResponse(content_type='application/pdf')\n"
                        "    response['Content-Disposition'] = 'attachment; filename=\"rapport.pdf\"'\n"
                        "    # Générer PDF ici (ex: reportlab)\n"
                        "    return response",
            "stream":    "    from django.http import StreamingHttpResponse\n"
                        "    def generate():\n        yield 'chunk1'\n"
                        "    return StreamingHttpResponse(generate())",
            "http":      "    return HttpResponse('OK')",
            "error_404": "    raise Http404('Ressource introuvable.')",
            "error_403": "    from django.core.exceptions import PermissionDenied\n    raise PermissionDenied",
        }
        lines.append(resp.get(response_type, "    return HttpResponse('OK')"))
        return '\n'.join(lines)

    @staticmethod
    def _generate_custom_method(method_data, indent=4):
        """Génère du code Python pour les blocs logiques personnalisés (If/For/Assign)"""
        sp = ' ' * indent
        lines = []
        m_type = method_data.get('type', 'assign')
        if m_type == 'if':
            cond = method_data.get('condition', 'True')
            lines.append(f"{sp}if {cond}:")
            # Pour simplifier, on ajoute un commentaire ou une action simple
            lines.append(f"{sp}    pass # Logique conditionnelle")
        elif m_type == 'elif':
            cond = method_data.get('condition', 'True')
            lines.append(f"{sp}elif {cond}:")
            lines.append(f"{sp}    pass")
        elif m_type == 'else':
            lines.append(f"{sp}else:")
            lines.append(f"{sp}    pass")
        elif m_type == 'for':
            iterable = method_data.get('iterable', '[]')
            var = method_data.get('var', 'item')
            lines.append(f"{sp}for {var} in {iterable}:")
            lines.append(f"{sp}    pass")
        elif m_type == 'while':
            cond = method_data.get('condition', 'True')
            lines.append(f"{sp}while {cond}:")
            lines.append(f"{sp}    pass")
        elif m_type == 'assign':
            var = method_data.get('var', 'x')
            val = method_data.get('value', 'None')
            lines.append(f"{sp}{var} = {val}")
        elif m_type == 'return':
            val = method_data.get('value', 'None')
            lines.append(f"{sp}return {val}")
        return lines

    @staticmethod
    def form(model, all_fields, selected_fields, logic, widgets):
        cls = model.replace('_',' ').title().replace(' ','')
        lines = [
            f"from django import forms",
            f"from .models import {cls}",
            f"from django.utils.translation import gettext_lazy as _",
            "",
            f"class {cls}Form(forms.ModelForm):",
            "    class Meta:",
            f"        model = {cls}",
        ]
        if all_fields or not selected_fields:
            lines.append("        fields = '__all__'")
        else:
            fields_str = "[" + ", ".join(f"'{f}'" for f in selected_fields) + "]"
            lines.append(f"        fields = {fields_str}")
        # Widgets
        if widgets:
            lines.append("        widgets = {")
            for w in widgets:
                f = w.get('field','champ')
                wtype = w.get('widget','TextInput')
                attrs = w.get('attrs','{}')
                lines.append(f"            '{f}': forms.{wtype}(attrs={attrs}),")
            lines.append("        }")
        # Labels
        lines += [
            "        labels = {}",
            "        help_texts = {}",
            "        error_messages = {}",
        ]
        # Logique
        if logic:
            lines += ["", "    def clean(self):", "        cleaned_data = super().clean()"]
            for b in logic:
                action = b.get('action','')
                field  = b.get('field','')
                value  = b.get('value','')
                if action == 'required':
                    lines += [f"        if not cleaned_data.get('{field}'):",
                              f"            self.add_error('{field}', _('{field} est obligatoire.'))"]
                elif action == 'min_length':
                    lines += [f"        if cleaned_data.get('{field}') and len(cleaned_data['{field}']) < {value or 3}:",
                              f"            self.add_error('{field}', _('{field} : minimum {value} caractères.'))"]
                elif action == 'match_fields':
                    f2 = value or 'password_confirm'
                    lines += [f"        if cleaned_data.get('{field}') != cleaned_data.get('{f2}'):",
                              f"            self.add_error('{f2}', _('Les champs {field} et {f2} ne correspondent pas.'))"]
                elif action == 'email_domain':
                    domain = value or 'example.com'
                    lines += [f"        email = cleaned_data.get('{field}','')",
                              f"        if email and not email.endswith('@{domain}'):",
                              "            self.add_error('" + field + "', _('Email doit appartenir à @" + domain + ".'))"]
                elif action == 'numeric_only':
                    lines += [f"        v = cleaned_data.get('{field}','')",
                              f"        if v and not v.isdigit():",
                              f"            self.add_error('{field}', _('{field} doit être numérique.'))"]
                elif action == 'positive':
                    lines += [f"        v = cleaned_data.get('{field}')",
                              f"        if v is not None and v <= 0:",
                              f"            self.add_error('{field}', _('{field} doit être positif.'))"]
            lines.append("        return cleaned_data")
        return '\n'.join(lines)

    @staticmethod
    def admin(model, list_display, list_filter, search_fields, readonly_fields, logic, actions):
        cls = model.replace('_',' ').title().replace(' ','')
        lines = [
            "from django.contrib import admin",
            f"from .models import {cls}",
            "from django.utils.translation import gettext_lazy as _",
            "",
            f"@admin.register({cls})",
            f"class {cls}Admin(admin.ModelAdmin):",
        ]
        if list_display:
            lines.append(f"    list_display = {list_display}")
        if list_filter:
            lines.append(f"    list_filter = {list_filter}")
        if search_fields:
            lines.append(f"    search_fields = {search_fields}")
        if readonly_fields:
            lines.append(f"    readonly_fields = {readonly_fields}")
        lines.append("    ordering = ['-id']")
        lines.append("    list_per_page = 25")
        lines.append("    save_on_top = True")
        # Actions admin
        if actions:
            for action in actions:
                fn = action.get('fn','mon_action')
                desc = action.get('desc','Action personnalisée')
                lines += [
                    "",
                    f"    @admin.action(description=_('{desc}'))",
                    f"    def {fn}(self, request, queryset):",
                ]
                act = action.get('type','message')
                if act == 'activate':
                    lines += ["        queryset.update(actif=True)",
                              f"        self.message_user(request, _('Éléments activés.'))"]
                elif act == 'deactivate':
                    lines += ["        queryset.update(actif=False)",
                              f"        self.message_user(request, _('Éléments désactivés.'))"]
                elif act == 'export_csv':
                    lines += [
                        "        import csv",
                        "        from django.http import HttpResponse",
                        "        response = HttpResponse(content_type='text/csv')",
                        "        response['Content-Disposition'] = 'attachment; filename=\"export.csv\"'",
                        "        writer = csv.writer(response)",
                        "        for obj in queryset:",
                        "            writer.writerow([str(obj)])",
                        "        return response",
                    ]
                else:
                    lines.append(f"        self.message_user(request, _('{desc} exécutée.'))")
            actions_list = "[" + ", ".join("'" + a.get('fn','action') + "'" for a in actions) + "]"
            lines.append(f"    actions = {actions_list}")
        if logic:
            lines += [
                "",
                "    def save_model(self, request, obj, form, change):",
            ]
            for b in logic:
                if b.get('action') == 'set_user':
                    field = b.get('field','created_by')
                    lines.append(f"        if not obj.{field}_id: obj.{field} = request.user")
                elif b.get('action') == 'log_save':
                    lines += ["        import logging",
                              "        logging.getLogger(__name__).info('Objet sauvegardé: %s', obj)"]
            lines.append("        super().save_model(request, obj, form, change)")
        return '\n'.join(lines)

    @staticmethod
    def settings(data):
        lines = [
            "import os",
            "from pathlib import Path",
            "",
            "# ── Chemins ────────────────────────────────────────────",
            "BASE_DIR = Path(__file__).resolve().parent.parent",
            "",
            "# ── Sécurité ────────────────────────────────────────────",
            f"SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '{data['secret_key']}')",
            f"DEBUG = {data['debug']}",
            "ALLOWED_HOSTS = [" + ", ".join(f"'{h}'" for h in data['allowed_hosts']) + "]",
            "",
            "# ── Applications ────────────────────────────────────────",
            "INSTALLED_APPS = [",
        ]
        for app in data['installed_apps']:
            lines.append(f"    '{app}',")
        lines += [
            "]",
            "",
            "# ── Middleware ──────────────────────────────────────────",
            "MIDDLEWARE = [",
        ]
        for mid in data['middleware']:
            lines.append(f"    '{mid}',")
        lines += [
            "]",
            "",
            f"ROOT_URLCONF = '{data['root_urlconf']}'",
            "",
            "# ── Templates ───────────────────────────────────────────",
            "TEMPLATES = [{",
            "    'BACKEND': 'django.template.backends.django.DjangoTemplates',",
            f"    'DIRS': [BASE_DIR / '{data['templates_dir']}'],",
            "    'APP_DIRS': True,",
            "    'OPTIONS': {",
            "        'context_processors': [",
            "            'django.template.context_processors.debug',",
            "            'django.template.context_processors.request',",
            "            'django.contrib.auth.context_processors.auth',",
            "            'django.contrib.messages.context_processors.messages',",
            "        ],",
            "    },",
            "}]",
            "",
            f"WSGI_APPLICATION = '{data['root_urlconf'].replace('urls','wsgi')}.application'",
            "",
            "# ── Base de données ─────────────────────────────────────",
            "DATABASES = {",
            "    'default': {",
        ]
        db = data['database']
        engine_map = {
            'sqlite3':    'django.db.backends.sqlite3',
            'postgresql': 'django.db.backends.postgresql',
            'mysql':      'django.db.backends.mysql',
        }
        lines.append(f"        'ENGINE': '{engine_map.get(db['engine'], db['engine'])}',")
        lines.append(f"        'NAME': BASE_DIR / '{db['name']}'" if db['engine']=='sqlite3' else f"        'NAME': '{db['name']}',")
        if db['engine'] != 'sqlite3':
            for k in ('USER','PASSWORD','HOST','PORT'):
                v = db.get(k.lower())
                if v: lines.append(f"        '{k}': '{v}',")
        lines += [
            "    }",
            "}",
            "",
            "# ── Authentification ────────────────────────────────────",
            "AUTH_PASSWORD_VALIDATORS = [",
            "    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},",
            "    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},",
            "    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},",
            "    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},",
            "]",
            "",
            "# ── Internationalisation ─────────────────────────────────",
            f"LANGUAGE_CODE = '{data['language_code']}'",
            f"TIME_ZONE = '{data['time_zone']}'",
            "USE_I18N = True",
            "USE_TZ = True",
            "",
            "# ── Fichiers statiques & médias ──────────────────────────",
            "STATIC_URL = '/static/'",
            "STATICFILES_DIRS = [",
        ]
        for s in data['static_dirs']:
            lines.append(f"    BASE_DIR / '{s}',")
        lines += [
            "]",
            "STATIC_ROOT = BASE_DIR / 'staticfiles'",
            f"MEDIA_URL = '{data['media_url']}'",
            f"MEDIA_ROOT = BASE_DIR / '{data['media_root']}'",
            "",
            "# ── Auto ─────────────────────────────────────────────────",
            "DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'",
        ]
        if data.get('login_url'):
            lines.append(f"LOGIN_URL = '{data['login_url']}'")
        lines.append(f"LOGIN_REDIRECT_URL = '{data.get('login_redirect','/')}' ")
        if data.get('email_backend'):
            lines += [
                "",
                "# ── Email ────────────────────────────────────────────",
                f"EMAIL_BACKEND = '{data['email_backend']}'",
            ]
        if data.get('csrf'):
            lines.append("CSRF_COOKIE_SECURE = False  # True en production HTTPS")
        if data.get('xss'):
            lines.append("SECURE_BROWSER_XSS_FILTER = True")
            lines.append("X_FRAME_OPTIONS = 'DENY'")
        if data.get('secure_cookies'):
            lines += ["SESSION_COOKIE_SECURE = True", "CSRF_COOKIE_SECURE = True"]
        if data.get('http_only'):
            lines.append("SESSION_COOKIE_HTTPONLY = True")
        if data.get('session_age'):
            lines.append(f"SESSION_COOKIE_AGE = {data['session_age']}")
        return '\n'.join(lines)

    @staticmethod
    def urls(entries, app_name=""):
        lines = [
            "from django.urls import path, include",
            "from . import views",
            "",
        ]
        if app_name:
            lines.append(f"app_name = '{app_name}'")
        lines.append("")
        lines.append("urlpatterns = [")
        for e in entries:
            path_str = e.get('path','')
            view_str = e.get('view','')
            name_str = e.get('name','')
            comment  = e.get('comment','')
            if comment: lines.append(f"    # {comment}")
            if view_str:
                lines.append(f"    path('{path_str}', views.{view_str}, name='{name_str}'),")
        lines.append("]")
        return '\n'.join(lines)

    @staticmethod
    def base_html(title, theme_color="#0d3b6e", include_chart=False):
        chart_js = '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>' if include_chart else ''
        # Utilisation de format() pour éviter les conflits d'accolades avec f-strings
        template = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{% block title %}}{title}{{% endblock %}}</title>
{{% load static %}}
<style>
:root {{
--primary: {theme_color};
--primary-light: #1a5c9e;
--accent: #4a90d9;
--bg: #f4f6fa;
--text: #1a1a2a;
--card-bg: #ffffff;
--border: #dde2ee;
--danger: #c0392b;
--success: #27ae60;
--warning: #e67e22;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Segoe UI', Arial, sans-serif; background: var(--bg); color: var(--text); }}
/* ── Navbar ── */
.navbar {{
background: var(--primary);
color: #fff;
padding: 0 24px;
display: flex;
align-items: center;
justify-content: space-between;
height: 60px;
position: sticky;
top: 0;
z-index: 100;
box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}}
.navbar .brand {{ font-size: 1.3rem; font-weight: 700; color: #fff; text-decoration: none; }}
.navbar nav a {{
color: rgba(255,255,255,0.85);
text-decoration: none;
margin-left: 20px;
font-size: 0.9rem;
transition: color 0.2s;
}}
.navbar nav a:hover {{ color: #fff; }}
/* ── Layout ── */
.container {{ max-width: 1280px; margin: 0 auto; padding: 24px 16px; }}
.page-header {{
background: var(--card-bg);
border-bottom: 3px solid var(--primary);
padding: 20px 24px;
margin-bottom: 24px;
border-radius: 6px;
}}
.page-header h1 {{ font-size: 1.6rem; color: var(--primary); }}
.page-header p {{ color: #666; margin-top: 4px; }}
/* ── Cards ── */
.card {{
background: var(--card-bg);
border: 1px solid var(--border);
border-radius: 8px;
padding: 20px;
margin-bottom: 16px;
box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}}
.card-title {{ font-size: 1.1rem; font-weight: 600; color: var(--primary); margin-bottom: 12px; }}
/* ── Tableau ── */
.table-container {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
thead tr {{ background: var(--primary); color: #fff; }}
th, td {{ padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--border); }}
tbody tr:hover {{ background: #f0f4ff; }}
/* ── Formulaires ── */
.form-group {{ margin-bottom: 16px; }}
.form-group label {{ display: block; font-size: 0.85rem; font-weight: 600; color: #444; margin-bottom: 4px; }}
.form-group input, .form-group select, .form-group textarea {{
width: 100%; padding: 9px 12px;
border: 1px solid var(--border); border-radius: 5px;
font-size: 0.9rem; transition: border-color 0.2s;
}}
.form-group input:focus, .form-group select:focus {{ outline: none; border-color: var(--accent); }}
/* ── Boutons ── */
.btn {{
display: inline-block; padding: 9px 20px; border-radius: 5px;
font-size: 0.9rem; font-weight: 600; cursor: pointer; text-decoration: none;
border: none; transition: all 0.2s;
}}
.btn-primary {{ background: var(--primary); color: #fff; }}
.btn-primary:hover {{ background: var(--primary-light); }}
.btn-success {{ background: var(--success); color: #fff; }}
.btn-danger  {{ background: var(--danger); color: #fff; }}
.btn-outline {{ background: transparent; border: 2px solid var(--primary); color: var(--primary); }}
/* ── Messages Django ── */
.messages {{ list-style: none; margin-bottom: 16px; }}
.messages li {{
padding: 10px 16px; border-radius: 5px; margin-bottom: 8px;
font-size: 0.9rem; border-left: 4px solid;
}}
.messages .success {{ background: #eafaf1; border-color: var(--success); color: #1e7e34; }}
.messages .error   {{ background: #fdf2f2; border-color: var(--danger);  color: #8b1a1a; }}
.messages .warning {{ background: #fef9e7; border-color: var(--warning); color: #8a5a00; }}
.messages .info    {{ background: #eaf4ff; border-color: var(--accent);  color: #0c4a8a; }}
/* ── Stats (dashboard) ── */
.stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px,1fr)); gap: 16px; }}
.stat-card {{
background: var(--card-bg); border: 1px solid var(--border);
border-left: 5px solid var(--primary);
padding: 18px; border-radius: 8px; text-align: center;
}}
.stat-card .stat-value {{ font-size: 2rem; font-weight: 700; color: var(--primary); }}
.stat-card .stat-label {{ font-size: 0.85rem; color: #888; margin-top: 4px; }}
/* ── Footer ── */
footer {{
background: var(--primary); color: rgba(255,255,255,0.7);
text-align: center; padding: 16px;
margin-top: 40px; font-size: 0.85rem;
}}
{{% block extra_css %}}
{{% endblock %}}
</style>
{chart_js}
{{% block head_extra %}}{{% endblock %}}
</head>
<body>
<header class="navbar">
<a class="brand" href="{{% url 'home' %}}">{title}</a>
<nav>
{{% block navbar_links %}}
<a href="{{% url 'home' %}}">Accueil</a>
{{% if user.is_authenticated %}}
<a href="{{% url 'dashboard' %}}">Tableau de bord</a>
<a href="{{% url 'logout' %}}">Déconnexion ({{{{ request.user.username }}}})</a>
{{% else %}}
<a href="{{% url 'login' %}}">Connexion</a>
{{% endif %}}
{{% endblock %}}
</nav>
</header>
<div class="container">
{{% if messages %}}
<ul class="messages">
{{% for msg in messages %}}
<li class="{{{{ msg.tags }}}}">{{{{ msg }}}}</li>
{{% endfor %}}
</ul>
{{% endif %}}
{{% block content %}}
{{% endblock %}}
</div>
<footer>
<p>&copy; {{% now "Y" %}} {title} — Propulsé par GCI / Gykhamine OS</p>
</footer>
{{% block extra_js %}}
{{% endblock %}}
</body>
</html>"""
        return template.format(title=title, theme_color=theme_color, chart_js=chart_js)

    @staticmethod
    def child_template(name, base, template_type, model_var="objet"):
        """Génère les 3 templates standards : entrer, liste, dashboard"""
        if template_type == "entrer":
            return """{{% extends '{base}' %}}
{{% load static %}}
{{% block title %}}Nouveau — {name}{{% endblock %}}
{{% block content %}}
<div class="page-header">
<h1>➕ Nouveau {name}</h1>
<p>Remplissez le formulaire ci-dessous.</p>
</div>
<div class="card">
<form method="post" enctype="multipart/form-data">
{{% csrf_token %}}
{{{{ form.as_p }}}}
<div style="margin-top: 20px; display:flex; gap: 12px;">
<button type="submit" class="btn btn-primary">💾 Enregistrer</button>
<a href="{{% url '{name}_liste' %}}" class="btn btn-outline">← Annuler</a>
</div>
</form>
</div>
{{% endblock %}}""".format(base=base, name=name)
        elif template_type == "liste":
            return """{{% extends '{base}' %}}
{{% load static %}}
{{% block title %}}Liste {name}s{{% endblock %}}
{{% block content %}}
<div class="page-header">
<h1>📋 Liste des {name}s</h1>
<p>{{{{ object_list|length }}}} enregistrement(s) trouvé(s).</p>
</div>
<div class="card">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
<input type="text" id="live-search" placeholder="🔍 Rechercher..." style="max-width:300px;" class="form-group input">
<a href="{{% url '{name}_entrer' %}}" class="btn btn-primary">➕ Ajouter</a>
</div>
<div class="table-container">
<table data-sortable>
<thead>
<tr>
<th>#</th>
<th>Objet</th>
<th>Actions</th>
</tr>
</thead>
<tbody>
{{% for obj in object_list %}}
<tr data-searchable>
<td>{{{{ forloop.counter }}}}</td>
<td>{{{{ obj }}}}</td>
<td>
<a href="{{% url '{name}_detail' obj.pk %}}" class="btn btn-outline">👁️ Voir</a>
<a href="{{% url '{name}_modifier' obj.pk %}}" class="btn btn-success">✏️ Modifier</a>
<a href="{{% url '{name}_supprimer' obj.pk %}}" class="btn btn-danger" onclick="return confirm('Confirmer ?')">🗑️ Supprimer</a>
</td>
</tr>
{{% empty %}}
<tr><td colspan="3" style="text-align:center;color:#888;padding:30px;">Aucun enregistrement.</td></tr>
{{% endfor %}}
</tbody>
</table>
</div>
{{% if is_paginated %}}
<div style="display:flex;gap:8px;margin-top:16px;">
{{% if page_obj.has_previous %}}<a href="?page={{{{ page_obj.previous_page_number }}}}" class="btn btn-outline">←</a>{{% endif %}}
<span style="padding:9px 16px;background:#f0f4ff;border-radius:5px;">Page {{{{ page_obj.number }}}} / {{{{ page_obj.paginator.num_pages }}}}</span>
{{% if page_obj.has_next %}}<a href="?page={{{{ page_obj.next_page_number }}}}" class="btn btn-outline">→</a>{{% endif %}}
</div>
{{% endif %}}
</div>
{{% endblock %}}
{{% block extra_js %}}
<script>
const s=document.querySelector('#live-search');
if(s)s.addEventListener('input',()=>{{
const q=s.value.toLowerCase();
document.querySelectorAll('[data-searchable]').forEach(r=>{{r.style.display=r.textContent.toLowerCase().includes(q)?'':'none';}});
}});
</script>
{{% endblock %}}""".format(base=base, name=name)
        elif template_type == "dashboard":
            return """{{% extends '{base}' %}}
{{% load static %}}
{{% block title %}}Tableau de Bord — {name}{{% endblock %}}
{{% block content %}}
<div class="page-header">
<h1>📊 Tableau de Bord {name}</h1>
<p>Vue d'ensemble de toutes les données.</p>
</div>
<div class="stats-grid">
<div class="stat-card">
<div class="stat-value">{{{{ total }}}}</div>
<div class="stat-label">Total {name}s</div>
</div>
<div class="stat-card">
<div class="stat-value">{{{{ actifs }}}}</div>
<div class="stat-label">Actifs</div>
</div>
<div class="stat-card">
<div class="stat-value">{{{{ recents }}}}</div>
<div class="stat-label">Ce mois</div>
</div>
</div>
<div class="card" style="margin-top:24px;">
<div class="card-title">📈 Évolution</div>
<canvas id="mainChart" height="120"></canvas>
</div>
<div class="card">
<div class="card-title">🕐 Derniers enregistrements</div>
<div class="table-container">
<table>
<thead><tr><th>#</th><th>Objet</th><th>Lien</th></tr></thead>
<tbody>
{{% for obj in derniers %}}
<tr>
<td>{{{{ forloop.counter }}}}</td>
<td>{{{{ obj }}}}</td>
<td><a href="{{% url '{name}_detail' obj.pk %}}" class="btn btn-outline">Voir</a></td>
</tr>
{{% empty %}}
<tr><td colspan="3" style="text-align:center;color:#888;">Aucune donnée.</td></tr>
{{% endfor %}}
</tbody>
</table>
</div>
</div>
{{% endblock %}}
{{% block extra_js %}}
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
const ctx = document.getElementById('mainChart')?.getContext('2d');
if (ctx) {{
new Chart(ctx, {{
type: 'bar',
data: {{
labels: {{{{ labels|safe }}}},
datasets: [{{ label: '{name}s', data: {{{{ values|safe }}}}, backgroundColor: '#4a90d9' }}]
}},
options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
}});
}}
</script>
{{% endblock %}}""".format(base=base, name=name)
        return """{{% extends '{base}' %}}
{{% block content %}}
<!-- {template_type} -->
{{% endblock %}}""".format(base=base, template_type=template_type)
