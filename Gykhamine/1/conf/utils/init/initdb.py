import os

device = "/dev/sda3"
mount_point = "/var/lib/pgsql/data"

print("=== Vérifier point de montage ===")
os.system(f"mkdir -p {mount_point}")

print("=== Vérifier si déjà monté ===")
mounts = os.popen("mount").read()
if mount_point not in mounts:
    os.system(f"mount {device} {mount_point}")
else:
    print("Déjà monté")

print("=== Vérification initdb ===")
if not os.path.exists(f"{mount_point}/PG_VERSION"):
    print("Initialisation PostgreSQL")
    os.system(f"sudo chown -R postgres:postgres {mount_point}")
    os.system(f"sudo chmod 700 {mount_point}")
    os.system(f"sudo -u postgres initdb -D {mount_point}")
else:
    print("Base déjà existante")

print("=== Démarrage PostgreSQL ===")
status = os.system(f"sudo -u postgres pg_ctl -D {mount_point} status")

if status != 0:
    os.system(f"sudo -u postgres pg_ctl -D {mount_point} start")
else:
    print("PostgreSQL déjà démarré")

print("=== OK ===")