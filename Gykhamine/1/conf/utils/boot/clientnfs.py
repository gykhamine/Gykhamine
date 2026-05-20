import os

# ======================
# CONFIG
# ======================

SERVER_IP = "192.168.1.10"   # IP du serveur NFS
EXPORT_DIR = "/srv/nfs"
MOUNT_POINT = "/home/ton_user/nfs"

print("== NFS CLIENT START ==")

# 1. créer point de montage local
os.system(f"mkdir -p {MOUNT_POINT}")

# 2. tester si serveur accessible
ping = os.system(f"ping -c 1 {SERVER_IP} > /dev/null 2>&1")

if ping != 0:
    print("Server not reachable, fallback local mode")
    exit()

print(f"Server reachable: {SERVER_IP}")

# 3. monter le partage NFS
os.system(f"mount -t nfs {SERVER_IP}:{EXPORT_DIR} {MOUNT_POINT}")

print("== NFS MOUNTED ==")
print(f"Mounted at: {MOUNT_POINT}")