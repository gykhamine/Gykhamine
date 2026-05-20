import os

EXPORT_DIR = "/run/media/gykhamine/GY/gy/media"
LAN_NETWORK = "192.168.1.0/24"

print("== NFS SERVER START ==")

# 1. détecter IP locale (info uniquement)
ip = os.popen("hostname -I | awk '{print $1}'").read().strip()

if not ip:
    ip = "127.0.0.1"

print(f"Server IP detected: {ip}")

# 2. créer dossier d'export si absent
os.system(f"mkdir -p {EXPORT_DIR}")
os.system(f"chmod 777 {EXPORT_DIR}")

# 3. écrire configuration NFS (exports)
export_config = f"{EXPORT_DIR} {LAN_NETWORK}(rw,sync,no_subtree_check,no_root_squash)\n"

with open("/tmp/exports", "w") as f:
    f.write(export_config)

os.system("sudo mv /tmp/exports /etc/exports")

# 4. appliquer configuration
os.system("sudo exportfs -ra")

# 5. redémarrer service NFS (déjà installé)
os.system("sudo systemctl restart nfs-server.service")

print("== NFS SERVER READY ==")
print(f"Export: {EXPORT_DIR}")
print(f"Network: {LAN_NETWORK}")