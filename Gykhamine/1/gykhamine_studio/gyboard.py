"""Format de distribution .gyboard : un livrable auto-contenu pour les ERP Django Gykhamine.

Inspiré des .pbix de Power BI, qui sont en réalité des archives ZIP (format Open
Packaging Conventions) renommées et contenant le modèle de données, la mise en page,
etc. Un fichier .gyboard suit le même principe : c'est un ZIP standard qui contient
l'intégralité d'un projet (code Django + base SQLite + médias + statiques).

Cycle de vie :
  1. pack_project()       : compresse un dossier de projet en un seul fichier .gyboard
  2. unpack_to_memory()   : décompresse dans un dossier de travail temporaire — en RAM
                            via /dev/shm sous Linux quand c'est possible — pour une
                            exécution et une édition RÉELLES (le serveur Django tourne
                            sur ce dossier, la base SQLite y est modifiée pour de vrai)
  3. repack_from_memory() : recompresse ce dossier de travail (code + données modifiés)
                            dans le même fichier .gyboard, qui reste l'unique livrable

Plus besoin de distribuer un dossier entier : un seul fichier .gyboard voyage, se lance,
se modifie, et se sauvegarde — exactement comme on ouvre/modifie/enregistre un .pbix.
"""
import zipfile, tempfile, shutil, uuid, json
from pathlib import Path
from datetime import datetime

GYBOARD_EXT = ".gyboard"
GYBOARD_META_FILE = ".gyboard_meta.json"

# Dossiers/fichiers qu'on ne distribue jamais dans le livrable (cache, VCS, venv...)
IGNORED_FOR_GYBOARD = {"__pycache__", ".git", "venv", "env", ".venv", "node_modules", ".idea", ".vscode"}


def _is_ignored(rel_path: Path) -> bool:
    return any(part in IGNORED_FOR_GYBOARD or part.endswith(".egg-info") for part in rel_path.parts)


def get_memory_workdir_root() -> Path:
    """Retourne un dossier racine en mémoire (tmpfs) si disponible et inscriptible,
    sinon le dossier temporaire système classique. Sous Linux, /dev/shm est un tmpfs
    monté en RAM : c'est exactement l'esprit 'décompresse en mémoire'."""
    shm = Path("/dev/shm")
    if shm.exists() and shm.is_dir():
        try:
            probe = shm / f".gyboard_write_test_{uuid.uuid4().hex}"
            probe.touch(); probe.unlink()
            return shm
        except Exception:
            pass
    return Path(tempfile.gettempdir())


def pack_project(source_dir: Path, gyboard_path: Path) -> None:
    """Compresse un dossier de projet en un fichier .gyboard (ZIP standard)."""
    source_dir = Path(source_dir)
    gyboard_path = Path(gyboard_path)
    meta = {
        "format": "gyboard",
        "version": 1,
        "project_name": source_dir.name,
        "packed_at": datetime.now().isoformat(),
    }
    tmp_target = gyboard_path.with_suffix(gyboard_path.suffix + ".tmp")
    with zipfile.ZipFile(tmp_target, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(GYBOARD_META_FILE, json.dumps(meta, indent=2, ensure_ascii=False))
        for file_path in source_dir.rglob("*"):
            if file_path.is_dir():
                continue
            rel = file_path.relative_to(source_dir)
            if _is_ignored(rel):
                continue
            zf.write(file_path, str(rel))
    tmp_target.replace(gyboard_path)  # remplacement atomique : jamais de .gyboard à moitié écrit


def unpack_to_memory(gyboard_path: Path) -> Path:
    """Décompresse un .gyboard dans un dossier de travail temporaire (RAM si possible).
    Retourne le chemin du dossier extrait, prêt pour exécution/édition réelle."""
    gyboard_path = Path(gyboard_path)
    if not zipfile.is_zipfile(gyboard_path):
        raise ValueError(f"« {gyboard_path.name} » n'est pas un .gyboard valide (ZIP attendu).")

    root = get_memory_workdir_root()
    workdir = root / f"gyboard_{gyboard_path.stem}_{uuid.uuid4().hex[:8]}"
    workdir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(gyboard_path, "r") as zf:
        zf.extractall(workdir)

    meta_file = workdir / GYBOARD_META_FILE
    if meta_file.exists():
        meta_file.unlink()  # métadonnée interne au format, pas un fichier du projet

    return workdir


def repack_from_memory(workdir: Path, gyboard_path: Path) -> None:
    """Recompresse le dossier de travail (code ET base SQLite potentiellement modifiés
    par une exécution réelle) dans le même fichier .gyboard, en l'écrasant."""
    pack_project(Path(workdir), Path(gyboard_path))


def cleanup_workdir(workdir: Path) -> None:
    """Supprime le dossier de travail temporaire (à fermer/remplacer le projet)."""
    try:
        shutil.rmtree(Path(workdir), ignore_errors=True)
    except Exception:
        pass
