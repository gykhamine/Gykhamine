import subprocess
import os
def connexion_depuis_fichier(nom_fichier="/run/media/gykhamine/GY/Gykhamine/conf/txt/wifi.txt"):
    # Vérifie si le fichier existe
    if not os.path.exists(nom_fichier):
        print(f"❌ Erreur : Créez un fichier '{nom_fichier}' avec SSID et MDP.")
        return

    # Lecture des lignes
    with open(nom_fichier, "r") as f:
        lignes = [l.strip() for l in f.readlines() if l.strip()]

    if len(lignes) < 2:
        print("❌ Erreur : Le fichier doit avoir le SSID sur la ligne 1 et le MDP sur la ligne 2.")
        return

    ssid = lignes[0]
    mdp  = lignes[1]

    print(f"📡 Connexion à {ssid}...")

    # Commande système pour Linux
    commande = ["nmcli", "dev", "wifi", "connect", ssid, "password", mdp]
    
    try:
        subprocess.run(commande, check=True)
        print(f"✅ Connecté à {ssid} avec succès !")
        return 1
    except subprocess.CalledProcessError:
        print(f"❌ Échec de la connexion. Vérifiez le signal ou le mot de passe.")
        return 0
if __name__ == "__main__":
    connexion_depuis_fichier()
