import os

db_name = "ma_base"
db_user = "mon_user"
db_password = "mot_de_passe".replace("'", "''")

print("=== Vérifier utilisateur ===")

check_user = os.popen(
    f"sudo -u postgres psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='{db_user}'\""
).read().strip()

if check_user != "1":
    print("Création utilisateur")
    os.system(
        f"sudo -u postgres psql -c "
        f"\"CREATE USER {db_user} WITH PASSWORD '{db_password}';\""
    )
else:
    print("Utilisateur déjà existant")

print("=== Vérifier base ===")

check_db = os.popen(
    f"sudo -u postgres psql -tAc \"SELECT 1 FROM pg_database WHERE datname='{db_name}'\""
).read().strip()

if check_db != "1":
    print("Création base")
    os.system(
        f"sudo -u postgres createdb -O {db_user} {db_name}"
    )
else:
    print("Base déjà existante")

print("=== Donner les privilèges ===")

os.system(
    f"sudo -u postgres psql -c "
    f"\"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};\""
)

print("== Fix schema public ==")

os.system(
    f'sudo -u postgres psql -d {db_name} -c '
    f'"GRANT USAGE, CREATE ON SCHEMA public TO {db_user};"'
)

os.system(
    f'sudo -u postgres psql -d {db_name} -c '
    f'"ALTER SCHEMA public OWNER TO {db_user};"'
)

print("=== OK ===")
