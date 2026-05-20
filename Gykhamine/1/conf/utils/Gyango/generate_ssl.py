import subprocess
import os

def generer_certificat():
    # --- CONFIGURATION DES CHEMINS ---
    # Change ces chemins selon tes besoins
    dossier_ssl = "/etc/pki/nginx"
    cle_privee = os.path.join(dossier_ssl, "private/server.key")
    certificat = os.path.join(dossier_ssl, "server.crt")
    
    # Détails du certificat (Subject)
    # C=Pays, ST=État, L=Ville, O=Organisation, CN=Nom de domaine ou IP
    sujet = "/C=FR/ST=Paris/L=Paris/O=MonProjet/CN=localhost"
    jours_validite = 365

    # --- CRÉATION DES DOSSIERS ---
    try:
        os.makedirs(os.path.dirname(cle_privee), exist_ok=True)
        os.makedirs(os.path.dirname(certificat), exist_ok=True)
    except PermissionError:
        print("❌ Erreur : Vous devez lancer ce script avec 'sudo'.")
        return

    # --- COMMANDE OPENSSL ---
    # req: gestion des requêtes de certificat
    # -x509: génère un certificat auto-signé
    # -nodes: ne pas chiffrer la clé privée (indispensable pour Nginx sans prompt)
    cmd = [
        "openssl", "req", "-x509", "-nodes",
        "-days", str(jours_validite),
        "-newkey", "rsa:2048",
        "-keyout", cle_privee,
        "-out", certificat,
        "-subj", sujet
    ]

    print(f"🛠  Génération de la clé et du certificat...")
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Sécuriser les permissions de la clé privée (lecture seule pour root)
        os.chmod(cle_privee, 0o600)
        
        print(f"✅ Certificat généré avec succès !")
        print(f"🔑 Clé : {cle_privee}")
        print(f"📜 Cert : {certificat}")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'exécution d'OpenSSL :")
        print(e.stderr)

if __name__ == "__main__":
    generer_certificat()