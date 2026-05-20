import os
import re

ENV_PATH = "/run/media/gykhamine/GY/gy/.env"

with open(ENV_PATH) as f:
    for line in f:
        m = re.match(r'^([A-Z_]+)=(.*)$', line.strip())
        if m:
            os.environ.setdefault(m.group(1), m.group(2))

PGDATA = os.environ.get('PG_DATA', '/var/lib/pgsql/data')
DEVICE = os.environ.get('PG_DEVICE', '/dev/sda3')

print("== Mount ==")
os.system(f"mountpoint -q {PGDATA} || mount {DEVICE} {PGDATA}")

print("== Start PostgreSQL ==")
os.system(f"sudo -u postgres pg_ctl -D {PGDATA} status || sudo -u postgres pg_ctl -D {PGDATA} start")

print("== Detect IP safely ==")

ip = os.popen("hostname -I | awk '{print $1}'").read().strip() or "127.0.0.1"

with open(ENV_PATH) as f:
    content = f.read()
content = re.sub(r'^DB_HOST=.*$', f'DB_HOST={ip}', content, flags=re.MULTILINE)
with open(ENV_PATH, 'w') as f:
    f.write(content)
print(f"DB_HOST mis à jour dans .env : {ip}")

os.system(f"sudo -u postgres psql -c \"ALTER SYSTEM SET listen_addresses = '{ip},localhost';\"")


os.system("sudo -u postgres psql -c 'SELECT pg_reload_conf();'")

print("== READY ==")