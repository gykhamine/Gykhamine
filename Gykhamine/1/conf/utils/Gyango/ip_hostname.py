import subprocess
import os
import re
import shutil # Pour la sauvegarde du fichier

def get_local_ip_address():
    """
    Exécute 'hostname -I' pour obtenir la ou les adresses IP locales et retourne la première.
    Retourne None si aucune adresse IP n'est trouvée ou si une erreur survient.
    """
    try:
        # Exécute la commande 'hostname -I'
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, check=True)
        ip_addresses = result.stdout.strip().split()

        if ip_addresses:
            # Retourne la première adresse IP trouvée
            return ip_addresses[0]
        else:
            print("Aucune adresse IP trouvée par 'hostname -I'.")
            return None
    except FileNotFoundError:
        print("Erreur: La commande 'hostname' est introuvable. Assurez-vous qu'elle est installée et dans votre PATH.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'exécution de 'hostname -I': {e.stderr.strip()}")
        return None
    except Exception as e:
        print(f"Une erreur inattendue est survenue lors de la récupération de l'IP: {e}")
        return None

def update_or_add_etc_hosts(target_hostname, new_ip):
    """
    Lit /etc/hosts, met à jour la ligne contenant target_hostname avec new_ip si elle existe,
    sinon ajoute une nouvelle ligne à la fin.
    Ceci est adapté au format 'IP Gykhamine.cg' sans alias supplémentaires sur la même ligne.
    """
    hosts_file_path = '/etc/hosts'
    backup_file_path = '/etc/hosts.bak' # Chemin pour la sauvegarde
    updated_lines = []
    line_found_and_modified = False # Indique si la ligne a été trouvée ET modifiée
    # La ligne à ajouter si non trouvée, utilisant une tabulation pour correspondre au format courant
    line_to_add = f"{new_ip}\t{target_hostname}\n"

    if not new_ip:
        print("Erreur: Nouvelle adresse IP non fournie. Impossible de mettre à jour /etc/hosts.")
        return False

    # Vérification des permissions root
    if os.geteuid() != 0:
        print(f"Erreur: Permissions insuffisantes. Ce script doit être exécuté avec 'sudo' pour modifier '{hosts_file_path}'.")
        return False

    try:
        # 1. Sauvegarde du fichier /etc/hosts avant modification
        if os.path.exists(hosts_file_path):
            shutil.copyfile(hosts_file_path, backup_file_path)
            print(f"Sauvegarde de '{hosts_file_path}' effectuée vers '{backup_file_path}'.")
        else:
            print(f"Avertissement: Le fichier '{hosts_file_path}' n'existe pas. Il sera créé si une entrée est ajoutée.")
            # If the file doesn't exist, 'lines' will be empty, and the new line will be added.

        # 2. Lire le fichier et préparer les modifications
        lines = []
        if os.path.exists(hosts_file_path):
            with open(hosts_file_path, 'r') as f:
                lines = f.readlines()

        # Build a more specific regex for "IP_ADDRESS TARGET_HOSTNAME" pattern
        # This regex looks for:
        # ^                 - start of the line
        # \s* - optional whitespace at the beginning
        # (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) - captures the IP address (group 1)
        # \s+               - one or more spaces/tabs
        # (?:[a-zA-Z0-9\-\.]+\s+)*? - non-capturing group for potential other hostnames before target (non-greedy)
        # ({target_hostname_escaped}) - captures our target hostname
        # (\s+.*)?           - captures any optional aliases/comments after the target hostname
        # $                 - end of the line (or before newline character)
        
        # Use re.IGNORECASE to match "Gykhamine.cg", "gykhamine.cg", etc.
        # If you want case-sensitive match, remove re.IGNORECASE flag.
        target_hostname_escaped = re.escape(target_hostname)
        # This regex is specifically tuned for lines like "IP Gykhamine.cg"
        # It allows for potential other hostnames/aliases *before* Gykhamine.cg,
        # but assumes Gykhamine.cg is the primary one we're interested in on that line.
        # It also captures anything AFTER Gykhamine.cg (e.g., comments or other aliases).
        # We'll use a slightly simpler one if we just expect "IP Gykhamine.cg"
        
        # More specific regex for exact "IP Gykhamine.cg" or "IP Gykhamine.cg # comment"
        # This matches the IP, then one or more whitespace chars, then target_hostname, then optional suffix
        pattern = re.compile(r"^\s*\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s+" + target_hostname_escaped + r"(\s+.*)?$", re.IGNORECASE)


        for i, line in enumerate(lines):
            match = pattern.match(line)

            if match:
                # We found the line to modify.
                # Capture any suffix (like comments or trailing aliases)
                suffix = match.group(1) if match.group(1) else ""
                
                new_formatted_line = f"{new_ip}\t{target_hostname}{suffix}\n" # Use tab, keep original suffix
                updated_lines.append(new_formatted_line)
                line_found_and_modified = True
                print(f"Ligne trouvée et modifiée pour '{target_hostname}': '{line.strip()}' -> '{new_formatted_line.strip()}'")
            else:
                updated_lines.append(line) # Conserver les autres lignes intactes

        # 3. Si la ligne n'a pas été trouvée, l'ajouter
        if not line_found_and_modified:
            # Add a newline character before the new entry if the file is not empty and doesn't end with one
            if lines and not lines[-1].endswith('\n'):
                updated_lines.append('\n')
            updated_lines.append(line_to_add)
            print(f"La ligne pour '{target_hostname}' n'a pas été trouvée. Ajout de la nouvelle ligne: '{line_to_add.strip()}'")
            line_found_and_modified = True # La ligne est maintenant "traitée" (ajoutée)

        # 4. Écrire le contenu mis à jour dans /etc/hosts
        with open(hosts_file_path, 'w') as f:
            f.writelines(updated_lines)
        
        print(f"Le fichier '{hosts_file_path}' a été mis à jour avec succès.")
        return True

    except IOError as e:
        print(f"Erreur d'accès au fichier '{hosts_file_path}': {e}")
        print(f"Vérifiez les permissions. Le fichier de sauvegarde peut être restauré manuellement depuis '{backup_file_path}'.")
        return False
    except Exception as e:
        print(f"Une erreur inattendue est survenue lors de la mise à jour de /etc/hosts: {e}")
        print(f"Vérifiez le fichier de sauvegarde '{backup_file_path}' en cas de problème.")
        return False

if __name__ == "__main__":
    # Assurez-vous que le nom d'hôte cible correspond EXACTEMENT (sensible à la casse si vous retirez re.IGNORECASE)
    # ou utilisez le nom d'hôte tel qu'il doit apparaître dans le fichier hosts si on l'ajoute.
    target_hostname_to_find = "Gykhamine.cg" # Using "Gykhamine.cg" as provided in your example

    # 1. Obtenir l'adresse IP locale actuelle
    current_ip = get_local_ip_address()

    if current_ip:
        print(f"Adresse IP locale actuelle détectée: {current_ip}")
        # 2. Mettre à jour ou ajouter l'entrée dans le fichier /etc/hosts
        success = update_or_add_etc_hosts(target_hostname_to_find, current_ip)
        if success:
            print("Opération terminée.")
        else:
            print("L'opération de mise à jour/ajout de /etc/hosts n'a pas été entièrement réussie.")
    else:
        print("Impossible de récupérer l'adresse IP locale. La mise à jour de /etc/hosts est annulée.")