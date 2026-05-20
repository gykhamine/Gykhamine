import subprocess
import re
import os

ENV_PATH = "/run/media/gykhamine/GY/gy/.env"

def get_local_ip_address():
    try:
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, check=True)
        ip_addresses = result.stdout.strip().split()
        if ip_addresses:
            return ip_addresses[0]
        return None
    except Exception as e:
        print("Erreur récupération IP :", e)
        return None


def update_settings_ip(file_path, new_ip):

    if not os.path.exists(file_path):
        print("Fichier introuvable :", file_path)
        return False

    try:
        with open(file_path) as f:
            content = f.read()

        # DJANGO_ALLOWED_HOSTS — ajouter l'IP si absente
        m = re.search(r'^DJANGO_ALLOWED_HOSTS=(.*)$', content, re.MULTILINE)
        if m:
            hosts = m.group(1)
            if new_ip not in hosts.split(','):
                hosts += ',' + new_ip
            content = re.sub(r'^DJANGO_ALLOWED_HOSTS=.*$', f'DJANGO_ALLOWED_HOSTS={hosts}', content, flags=re.MULTILINE)
            print("ALLOWED_HOSTS mis à jour avec :", new_ip)

        # DB_HOST
        content = re.sub(r'^DB_HOST=.*$', f'DB_HOST={new_ip}', content, flags=re.MULTILINE)
        print("DB_HOST mis à jour avec :", new_ip)

        # REDIS_URL
        content = re.sub(r'(REDIS_URL=redis://)[\d.]+', rf'\g<1>{new_ip}', content)
        print("REDIS_URL mis à jour avec :", new_ip)

        with open(file_path, 'w') as f:
            f.write(content)

        print(".env mis à jour.")
        return True

    except Exception as e:
        print("Erreur modification fichier :", e)
        return False


if __name__ == "__main__":

    current_ip = get_local_ip_address()

    if current_ip:
        print("IP détectée :", current_ip)
        update_settings_ip(ENV_PATH, current_ip)
    else:
        print("Impossible de récupérer l'IP.")