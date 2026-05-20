import subprocess
import os
import re
import sys

ENV_PATH = "/run/media/gykhamine/GY/gy/.env"
with open(ENV_PATH) as f:
    for line in f:
        m = re.match(r'^([A-Z_0-9]+)=(.*)$', line.strip())
        if m:
            os.environ.setdefault(m.group(1), m.group(2))

PORTS_FIXES = [
    ("22",  "tcp"),   # SSH
    ("80",  "tcp"),   # HTTP
    ("443", "tcp"),   # HTTPS
    ("5432","tcp"),   # PostgreSQL
    ("6379","tcp"),   # Redis
    ("8000","tcp"),   # Django dev
]

PORTS_CONFIGURABLES = [
    (os.environ.get("FIREWALL_EXTRA_PORT_1", "8080"), "tcp"),
    (os.environ.get("FIREWALL_EXTRA_PORT_2", "3000"), "tcp"),
    (os.environ.get("FIREWALL_EXTRA_PORT_3", "3306"), "tcp"),
    (os.environ.get("FIREWALL_EXTRA_PORT_4", "27017"),"tcp"),
    (os.environ.get("FIREWALL_EXTRA_PORT_5", "9200"), "tcp"),
    (os.environ.get("FIREWALL_EXTRA_PORT_6", "5601"), "tcp"),
    (os.environ.get("FIREWALL_EXTRA_PORT_7", "4000"), "tcp"),
]

def configurer_firewall_fedora(port="443", protocole="tcp"):
    # 1. Vérification des privilèges
    if os.geteuid() != 0:
        print("❌ Erreur : Vous devez exécuter ce script avec 'sudo'.")
        sys.exit(1)

    print(f"🛠️  Configuration de Firewalld pour le port {port}/{protocole}...")

    try:
        # Ajout de la règle permanente (--permanent)
        # Cela écrit la configuration dans le fichier XML de la zone
        subprocess.run(
            ["firewall-cmd", "--permanent", f"--add-port={port}/{protocole}"],
            check=True, capture_output=True, text=True
        )

        # Rechargement pour appliquer la règle immédiatement sans couper les connexions
        subprocess.run(["firewall-cmd", "--reload"], check=True, capture_output=True, text=True)

        print(f"✅ Port {port}/{protocole} ouvert avec succès et persistant au redémarrage.")

    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de la modification du firewall : {e.stderr}")
    except FileNotFoundError:
        print("❌ Erreur : 'firewall-cmd' n'est pas installé. Est-ce bien une Fedora ?")

if __name__ == "__main__":
    for port, proto in PORTS_FIXES + PORTS_CONFIGURABLES:
        configurer_firewall_fedora(port, proto)