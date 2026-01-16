#!/usr/bin/env python3
"""
Script pour uploader les fichiers torrent sur TheOldSchool.cc via API.

Usage:
    python upload_torrents.py <dossier_torrents>
    python upload_torrents.py "Y:\\books\\MonManga\\output"
"""

import os
import base64
import logging
import time
import argparse
import tempfile
import zipfile
import shutil
import requests
from pathlib import Path
from dotenv import load_dotenv
from patterns import get_tome_match_patterns

# Charger le fichier .env
load_dotenv(Path(__file__).parent / ".env")

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Configuration depuis .env
API_URL = "https://theoldschool.cc/api/torrents/upload"
API_TOKEN = os.getenv("API_TOKEN")
DEFAULT_SOURCE = os.getenv("SOURCE_DIR")
UPLOAD_DELAY = int(os.getenv("UPLOAD_DELAY"))
TYPE_ID = int(os.getenv("TYPE_ID"))
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "")

# Configuration pour Ebooks/Manga
# Voir: https://hdinnovations.github.io/UNIT3D/torrent_api.html
DEFAULT_PARAMS = {
    # Requis
    "category_id": 3,  # Ebooks
    "type_id": TYPE_ID,
    "stream": 0,
    "sd": 0,
    # Optionnels
    "resolution_id": 10,  # Autre
    "tmdb": 0,
    "imdb": 0,
    "tvdb": 0,
    "mal": 0,
    "igdb": 0,
    "anonymous": 0,
    "personal_release": 0,
}


def find_cover():
    """Trouve le fichier cover à côté du script."""
    script_dir = Path(__file__).parent
    extensions = [".jpg", ".jpeg", ".png"]

    for ext in extensions:
        cover_path = script_dir / f"cover{ext}"
        if cover_path.exists():
            return cover_path

    return None


def get_first_image_from_sorted(file_list):
    """Retourne le premier fichier image d'une liste triée."""
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    sorted_files = sorted([f for f in file_list if not f.startswith("__MACOSX")])
    for filename in sorted_files:
        ext = Path(filename).suffix.lower()
        if ext in image_extensions:
            return filename
    return None


def extract_cover_from_cbz(cbz_path):
    """Extrait la première page d'un fichier CBZ (archive ZIP)."""
    try:
        with zipfile.ZipFile(cbz_path, "r") as zf:
            first_image = get_first_image_from_sorted(zf.namelist())
            if first_image:
                # Extraire dans un fichier temporaire
                ext = Path(first_image).suffix
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                temp_file.write(zf.read(first_image))
                temp_file.close()
                return Path(temp_file.name)
    except zipfile.BadZipFile:
        logger.warning(f"Fichier CBZ invalide: {cbz_path}")
    except Exception as e:
        logger.warning(f"Erreur extraction CBZ: {e}")
    return None


def extract_cover_from_cbr(cbr_path):
    """Extrait la première page d'un fichier CBR (archive RAR) via rarfile."""
    try:
        import rarfile

        with rarfile.RarFile(cbr_path, "r") as rf:
            first_image = get_first_image_from_sorted(rf.namelist())
            if first_image:
                ext = Path(first_image).suffix
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                temp_file.write(rf.read(first_image))
                temp_file.close()
                return Path(temp_file.name)
    except ImportError:
        logger.warning("rarfile non installé (pip install rarfile)")
    except Exception as e:
        logger.warning(f"Erreur extraction CBR: {e}")
    return None


def extract_cover_from_pdf(pdf_path):
    """Extrait la première page d'un fichier PDF en image via pymupdf."""
    try:
        import fitz  # pymupdf

        doc = fitz.open(pdf_path)
        if len(doc) > 0:
            page = doc[0]
            # Render à 150 DPI pour une bonne qualité
            pix = page.get_pixmap(dpi=150)
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            temp_file.close()
            pix.save(temp_file.name)
            doc.close()
            return Path(temp_file.name)
        doc.close()
    except ImportError:
        logger.warning("pymupdf non installé (pip install pymupdf)")
    except Exception as e:
        logger.warning(f"Erreur extraction PDF: {e}")
    return None


def extract_cover_from_book(book_path):
    """Extrait la couverture du premier fichier CBZ/CBR/PDF trouvé."""
    book_path = Path(book_path)
    ext = book_path.suffix.lower()

    if ext == ".cbz":
        return extract_cover_from_cbz(book_path)
    elif ext == ".cbr":
        return extract_cover_from_cbr(book_path)
    elif ext == ".pdf":
        return extract_cover_from_pdf(book_path)
    return None


def find_first_book(source_dir):
    """Trouve le premier fichier CBZ/CBR/PDF dans le dossier source."""
    source_dir = Path(source_dir)
    extensions = ["*.cbz", "*.cbr", "*.pdf"]

    for ext in extensions:
        books = sorted(source_dir.glob(ext))
        if books:
            return books[0]
    return None


def find_book_for_torrent(torrent_name, source_dir):
    """Trouve le fichier CBZ/CBR/PDF correspondant au torrent via le numéro de tome."""
    import re

    source_dir = Path(source_dir)

    # Extraire le numéro de tome du nom du torrent (T01, T02, etc.)
    match = re.search(r"\.T(\d+)\.", torrent_name)
    if not match:
        return None

    tome_num = int(match.group(1))
    tome_patterns = get_tome_match_patterns(tome_num)

    # Chercher dans tous les fichiers CBZ/CBR/PDF
    for ext in ["*.cbz", "*.cbr", "*.pdf"]:
        for book in source_dir.glob(ext):
            for pattern in tome_patterns:
                if re.search(pattern, book.name, re.IGNORECASE):
                    return book
    return None


def upload_image_to_imgbb(image_path):
    """Upload une image sur imgbb et retourne l'URL."""
    if not IMGBB_API_KEY:
        logger.warning("IMGBB_API_KEY non défini, cover ignorée")
        return None

    image_path = Path(image_path)
    if not image_path.exists():
        logger.warning(f"Image non trouvée: {image_path}")
        return None

    try:
        # Lire et encoder l'image en base64
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        url = "https://api.imgbb.com/1/upload"
        payload = {
            "key": IMGBB_API_KEY,
            "image": image_data,
            "name": image_path.stem,
        }

        response = requests.post(url, data=payload)

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                image_url = result["data"]["url"]
                logger.info(f"  Cover uploadée: {image_url}")
                return image_url
            else:
                logger.error(
                    f"  Erreur imgbb: {result.get('error', {}).get('message', 'Unknown')}"
                )
                return None
        else:
            logger.error(f"  Erreur imgbb HTTP {response.status_code}: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"  Erreur upload cover: {e}")
        return None


def download_torrent(url, output_dir, filename):
    """Télécharge le fichier .torrent depuis le tracker."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            download_dir = Path(output_dir) / "downloaded"
            download_dir.mkdir(exist_ok=True)
            output_path = download_dir / filename
            output_path.write_bytes(response.content)
            logger.info(f"  Torrent téléchargé: {output_path}")
            return True
        else:
            logger.error(
                f"  Erreur téléchargement torrent: HTTP {response.status_code}"
            )
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"  Erreur téléchargement: {e}")
        return False


def upload_torrent(torrent_path, name, description="", cover_url=""):
    """Upload un fichier torrent sur TheOldSchool.cc."""
    torrent_path = Path(torrent_path)

    if not torrent_path.exists():
        logger.error(f"Fichier torrent non trouvé: {torrent_path}")
        return False

    if not API_TOKEN:
        logger.error("API_TOKEN non défini dans .env")
        return False

    # Préparer les fichiers
    files = {
        "torrent": (
            torrent_path.name,
            open(torrent_path, "rb"),
            "application/x-bittorrent",
        ),
    }

    # Construire la description avec cover si disponible
    desc_parts = []
    if cover_url:
        desc_parts.append(f"[center][img=350]{cover_url}[/img][/center]")
    desc_parts.append(f"[center][b]{name}[/b][/center]")
    if description:
        desc_parts.append(f"\n{description}")

    # Préparer les données
    data = DEFAULT_PARAMS.copy()
    data["name"] = name
    data["description"] = "\n".join(desc_parts)

    # URL avec token
    url = f"{API_URL}?api_token={API_TOKEN}"

    logger.info(f"Upload de: {name}")
    logger.debug(f"  Fichier: {torrent_path.name}")

    try:
        response = requests.post(url, files=files, data=data)

        if response.status_code == 200:
            logger.info(f"  Upload réussi!")
            result = response.json()
            # Télécharger le .torrent depuis le tracker
            download_url = result.get("data")
            if download_url and isinstance(download_url, str):
                download_torrent(
                    download_url, torrent_path.parent.parent, torrent_path.name
                )
            return True
        else:
            logger.error(f"  Erreur HTTP {response.status_code}")
            logger.error(f"  Réponse: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"  Erreur de connexion: {e}")
        return False
    finally:
        files["torrent"][1].close()


def get_description_from_project():
    """Récupère la description depuis description.txt à côté du script."""
    txt_path = Path(__file__).parent / "description.txt"
    if txt_path.exists():
        try:
            description = txt_path.read_text(encoding="utf-8").strip()
            if description:
                logger.info(f"Description chargée depuis: {txt_path}")
                return description
        except Exception as e:
            logger.warning(f"Erreur lecture {txt_path}: {e}")
    return ""


def upload_all_torrents(torrent_dir, skip_patterns=None):
    """Upload tous les fichiers .torrent d'un dossier."""
    torrent_dir = Path(torrent_dir)
    skip_patterns = skip_patterns or []

    if not torrent_dir.exists():
        logger.error(f"Dossier non trouvé: {torrent_dir}")
        return

    torrent_files = sorted(torrent_dir.glob("*.torrent"))

    # Filtrer les fichiers à ignorer
    if skip_patterns:
        torrent_files = [
            f for f in torrent_files if not any(p in f.name for p in skip_patterns)
        ]

    if not torrent_files:
        logger.warning("Aucun fichier .torrent trouvé")
        return

    logger.info(f"Trouvé {len(torrent_files)} fichier(s) .torrent")

    # Charger la description une seule fois pour tous les torrents
    description = get_description_from_project()

    # Vérifier si une cover manuelle existe (utilisée pour tous les tomes)
    manual_cover_url = ""
    if IMGBB_API_KEY:
        cover_path = find_cover()
        if cover_path:
            logger.info(f"Cover manuelle trouvée: {cover_path.name}")
            manual_cover_url = upload_image_to_imgbb(cover_path)

    source_dir = torrent_dir.parent  # Le dossier source est le parent de output/

    success_count = 0
    fail_count = 0

    for i, torrent_file in enumerate(torrent_files, 1):
        logger.info(f"\n[{i}/{len(torrent_files)}] {torrent_file.name}")

        # Le nom de la release = nom du fichier sans extension
        release_name = torrent_file.stem

        # Déterminer la cover pour ce tome
        cover_url = manual_cover_url
        extracted_cover = None

        if not cover_url and IMGBB_API_KEY:
            # Pas de cover manuelle, extraire depuis le fichier correspondant
            book_file = find_book_for_torrent(torrent_file.name, source_dir)
            if book_file:
                logger.info(f"  Extraction cover depuis: {book_file.name}")
                extracted_cover = extract_cover_from_book(book_file)
                if extracted_cover:
                    cover_url = upload_image_to_imgbb(extracted_cover)
                    # Nettoyer le fichier temporaire
                    try:
                        extracted_cover.unlink()
                        if "tmp" in str(extracted_cover.parent).lower():
                            shutil.rmtree(extracted_cover.parent, ignore_errors=True)
                    except Exception:
                        pass
                else:
                    logger.warning("  Impossible d'extraire la cover")
            else:
                logger.info("  Pas de fichier source trouvé pour la cover")

        if upload_torrent(torrent_file, release_name, description, cover_url):
            success_count += 1
        else:
            fail_count += 1

        # Pause entre les uploads pour éviter le flood
        if i < len(torrent_files):
            logger.info(f"  Pause de {UPLOAD_DELAY} secondes...")
            time.sleep(UPLOAD_DELAY)

    logger.info(f"\nTerminé! {success_count} réussi(s), {fail_count} échoué(s)")


def main():
    parser = argparse.ArgumentParser(
        description="Upload des fichiers torrent sur TheOldSchool.cc",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python upload_torrents.py "Y:\\books\\MonManga\\output"
  python upload_torrents.py "Y:\\books\\MonManga\\output" --skip T01 T02
  python upload_torrents.py "Y:\\books\\MonManga\\output" --delay 15

Configuration dans .env:
  API_TOKEN, API_URL, SOURCE_DIR, UPLOAD_DELAY, IMGBB_API_KEY

Note: Si un fichier cover.jpg/png/jpeg existe dans le dossier parent, il sera uploadé sur imgbb.
        """,
    )

    default_dir = Path(DEFAULT_SOURCE) / "output" if DEFAULT_SOURCE else ""
    parser.add_argument(
        "source",
        nargs="?",
        default=str(default_dir),
        help="Dossier contenant les fichiers .torrent",
    )
    parser.add_argument(
        "--skip", "-s", nargs="*", default=[], help="Patterns à ignorer (ex: T01 T02)"
    )
    parser.add_argument(
        "--delay",
        "-d",
        type=int,
        default=UPLOAD_DELAY,
        help=f"Délai entre uploads en secondes (défaut: {UPLOAD_DELAY})",
    )
    args = parser.parse_args()

    upload_all_torrents(args.source, skip_patterns=args.skip)


if __name__ == "__main__":
    main()
