#!/usr/bin/env python3
"""
Script pour retirer la première page d'un fichier CBZ.
Usage: python remove_first_page.py fichier.cbz [fichier2.cbz ...]
"""

import argparse
import zipfile
import tempfile
import shutil
from pathlib import Path


def get_sorted_images(zip_file):
    """Retourne la liste des images triées par nom."""
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
    images = [
        name for name in zip_file.namelist()
        if Path(name).suffix.lower() in image_extensions
    ]
    return sorted(images)


def remove_first_page(cbz_path, dry_run=False):
    """Retire la première page d'un CBZ."""
    cbz_path = Path(cbz_path)

    if not cbz_path.exists():
        print(f"Fichier non trouvé: {cbz_path}")
        return False

    if cbz_path.suffix.lower() != ".cbz":
        print(f"Ce n'est pas un fichier CBZ: {cbz_path}")
        return False

    try:
        with zipfile.ZipFile(cbz_path, 'r') as zf:
            images = get_sorted_images(zf)

            if len(images) < 2:
                print(f"Pas assez de pages dans {cbz_path.name} ({len(images)} image(s))")
                return False

            first_page = images[0]
            print(f"{cbz_path.name}: suppression de '{first_page}' ({len(images)} pages -> {len(images)-1})")

            if dry_run:
                return True

            # Créer un nouveau CBZ sans la première page
            with tempfile.NamedTemporaryFile(delete=False, suffix='.cbz') as tmp:
                tmp_path = Path(tmp.name)

            with zipfile.ZipFile(cbz_path, 'r') as zf_in:
                with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as zf_out:
                    for item in zf_in.namelist():
                        if item != first_page:
                            data = zf_in.read(item)
                            zf_out.writestr(item, data)

            # Remplacer l'original
            shutil.move(tmp_path, cbz_path)
            print(f"  OK")
            return True

    except zipfile.BadZipFile:
        print(f"Fichier ZIP invalide: {cbz_path}")
        return False
    except Exception as e:
        print(f"Erreur avec {cbz_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Retire la première page d'un ou plusieurs fichiers CBZ"
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="Fichier(s) CBZ à traiter"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Affiche ce qui serait fait sans modifier les fichiers"
    )
    args = parser.parse_args()

    success = 0
    for file_path in args.files:
        path = Path(file_path)

        # Si c'est un dossier, traiter tous les CBZ dedans
        if path.is_dir():
            files = sorted(path.glob("*.cbz"))
            if not files:
                print(f"Aucun fichier CBZ trouvé dans: {path}")
        # Support des wildcards sur Windows
        elif "*" in file_path:
            files = sorted(path.parent.glob(path.name)) if path.parent.exists() else []
        else:
            files = [path]

        for f in files:
            if remove_first_page(f, dry_run=args.dry_run):
                success += 1

    print(f"\n{success} fichier(s) traité(s)")


if __name__ == "__main__":
    main()
