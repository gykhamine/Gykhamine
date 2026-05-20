import os
import sys
import re

# ======================
# CONFIGURATION
# ======================

# Chemin vers ton projet Django
ENV_PATH = "/run/media/gykhamine/GY/Gykhamine/gy/.env"

if not os.path.exists(ENV_PATH):
    print(f"Erreur : Le fichier .env est introuvable à l'emplacement : {ENV_PATH}", file=sys.stderr)
    sys.exit(1)

# Variables figées sur Localhost (plus de détection dynamique)
IP_FIXE = "127.0.0.1"
PORT = "6379"
DATA_DIR = "/home/gykhamine/redis_data"

print("== Chargement de la configuration ==")

# On s'assure d'extraire REDIS_USE_PERSISTENCE du .env si présent
USE_PERSISTENCE = True
with open(ENV_PATH, 'r') as f:
    for line in f:
        if line.strip().startswith('REDIS_USE_PERSISTENCE='):
            USE_PERSISTENCE = line.strip().split('=')[1].split('#')[0].strip() == 'True'

# Mettre à jour de manière stricte le REDIS_URL dans le .env
redis_url = f"redis://{IP_FIXE}:{PORT}/1"

with open(ENV_PATH, 'r') as f:
    content = f.read()

# Remplacement propre de l'URL
content = re.sub(r'^REDIS_URL=.*$', f'REDIS_URL={redis_url}', content, flags=re.MULTILINE)

with open(ENV_PATH, 'w') as f:
    f.write(content)

print(f"REDIS_URL synchronisé dans le .env : {redis_url}")

# ======================
# LANCEMENT DE REDIS
# ======================

print("== Démarrage de Redis Server ==")

if USE_PERSISTENCE:
    os.makedirs(DATA_DIR, exist_ok=True)
    # Exécution avec persistance locale
    cmd = f"redis-server --bind {IP_FIXE} --port {PORT} --dir {DATA_DIR} --appendonly yes --daemonize yes"
else:
    # Exécution simple en mémoire
    cmd = f"redis-server --bind {IP_FIXE} --port {PORT} --daemonize yes"

status = os.system(cmd)

if status == 0:
    print("== READY ==")
    print(f"Redis tourne localement et de manière sécurisée sur : {IP_FIXE}:{PORT}")
else:
    print("Erreur : Impossible de démarrer le serveur Redis.", file=sys.stderr)
    sys.exit(1)
