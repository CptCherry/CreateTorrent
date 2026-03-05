#!/usr/bin/env python3
"""
Script générique pour créer des fichiers torrent pour des livres CBZ/PDF.
Voir README.md pour la documentation complète.
"""

import os
import json
import re
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv
from torf import Torrent
from patterns import TOME_EXTRACT_PATTERNS

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
DEFAULT_SOURCE = os.getenv("SOURCE_DIR", "")
DEFAULT_TRACKER = os.getenv("TRACKER_URL", "")
DEFAULT_BOOK_JSON = os.getenv("BOOK_JSON", "")
CREATED_BY = os.getenv("CREATED_BY", "CreateTorrent by CaptainCherry")


def get_team_for_tome(tome_num, team_rules, default_team):
    """Retourne la team correspondant au numéro de tome."""
    if team_rules:
        for start, end, team in team_rules:
            if start <= tome_num <= end:
                return team
    return default_team


def get_date_for_tome(tome_num, tome_dates, default_date):
    """Retourne la date de sortie correspondant au numéro de tome."""
    if tome_dates:
        return tome_dates.get(str(tome_num), default_date)
    return default_date


def extract_tome_number(filename):
    """Extrait le numéro de tome/chapitre du nom de fichier.

    Retourne (numero, prefix) où prefix est "T" pour tome ou "C" pour chapitre,
    ou (None, None) si aucun match.
    """
    for pattern, prefix in TOME_EXTRACT_PATTERNS:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            return int(match.group(1)), prefix
    return None, None


def create_torrent(file_path, output_path, tracker_url=""):
    """Crée un fichier torrent en utilisant torf."""
    file_path = Path(file_path)
    output_path = Path(output_path)

    try:
        t = Torrent(
            path=file_path,
            trackers=[tracker_url] if tracker_url else None,
            source="TOS",
            comment=CREATED_BY,
            private=True,
        )
        # piece_size = 2^20 = 1 Mo (équivalent à -l 20 de mktorrent)
        t.piece_size = 2**20
        t.generate()
        t.write(output_path)
        return True
    except Exception as e:
        logger.error(f"Erreur création torrent: {e}")
        return False


def format_title(metadata):
    """Formate le titre au format AUTEUR.DATE.TITRE.LANGUE.FORMAT-TEAM (DATE optionnel)."""

    def clean(s):
        # Remplacer les caractères accentués
        accents = {
            "à": "a",
            "â": "a",
            "ä": "a",
            "á": "a",
            "è": "e",
            "ê": "e",
            "ë": "e",
            "é": "e",
            "ì": "i",
            "î": "i",
            "ï": "i",
            "í": "i",
            "ò": "o",
            "ô": "o",
            "ö": "o",
            "ó": "o",
            "ù": "u",
            "û": "u",
            "ü": "u",
            "ú": "u",
            "ç": "c",
            "ñ": "n",
            "À": "A",
            "Â": "A",
            "Ä": "A",
            "Á": "A",
            "È": "E",
            "Ê": "E",
            "Ë": "E",
            "É": "E",
            "Ì": "I",
            "Î": "I",
            "Ï": "I",
            "Í": "I",
            "Ò": "O",
            "Ô": "O",
            "Ö": "O",
            "Ó": "O",
            "Ù": "U",
            "Û": "U",
            "Ü": "U",
            "Ú": "U",
            "Ç": "C",
            "Ñ": "N",
        }
        for accent, replacement in accents.items():
            s = s.replace(accent, replacement)

        # Supprimer les caractères non autorisés (garder lettres, chiffres, points, tirets)
        result = ""
        for c in s:
            if c.isalnum() or c in ".-_":
                result += c
            elif c in " '":
                result += "."
            # Autres caractères ignorés

        # Nettoyer les points multiples
        while ".." in result:
            result = result.replace("..", ".")

        return result

    titre = clean(metadata["titre"])
    langue = clean(metadata["langue"])
    format_ = clean(metadata["format"])
    team = clean(metadata["team"])
    auteur = clean(metadata.get("auteur", ""))
    date = clean(metadata.get("date", ""))

    # Construire le titre avec les parties optionnelles
    parts = []
    if auteur:
        parts.append(auteur)
    if date:
        parts.append(date)
    parts.extend([titre, langue, format_])

    return ".".join(parts) + f"-{team}"


def process_books(source_dir, output_dir=None, tracker_url="", json_path=None):
    """Traite tous les fichiers CBZ/PDF du dossier source."""
    source_dir = Path(source_dir)
    output_dir = Path(output_dir) if output_dir else source_dir / "output"

    logger.info(f"Dossier source: {source_dir}")
    logger.info(f"Dossier sortie: {output_dir}")

    # Lire le fichier book.json (depuis .env ou dossier source)
    if json_path:
        json_path = Path(json_path)
    else:
        json_path = source_dir / "book.json"

    logger.info(f"Fichier JSON: {json_path}")

    if not json_path.exists():
        logger.error(f"Fichier non trouvé: {json_path}")
        logger.error("Créez un fichier book.json ou définissez BOOK_JSON dans .env")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    logger.info(f"Métadonnées chargées: {metadata.get('titre', 'N/A')}")

    # Vérifier les champs requis (titre, langue, format obligatoires / auteur, date optionnels)
    required_fields = ["titre", "langue", "format"]
    missing = [f for f in required_fields if not metadata.get(f)]
    if missing:
        logger.error(f"Champs manquants dans book.json: {', '.join(missing)}")
        return

    # Extraire les configurations optionnelles
    default_team = metadata.get("team", "NOTAG")
    team_rules = metadata.get("team_rules", [])
    tome_dates = metadata.get("tome_dates", {})

    # Créer le dossier de sortie si nécessaire
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Dossier de sortie créé/vérifié: {output_dir}")

    # Trouver tous les fichiers CBZ et PDF
    book_files = (
        list(source_dir.glob("*.cbz"))
        + list(source_dir.glob("*.pdf"))
        + list(source_dir.glob("*.cbr"))
    )
    if not book_files:
        logger.warning("Aucun fichier CBR/CBZ ou PDF trouvé")
        return

    logger.info(f"Trouvé {len(book_files)} fichier(s)")

    for i, book_file in enumerate(sorted(book_files), 1):
        logger.info(f"[{i}/{len(book_files)}] Traitement de: {book_file.name}")

        # Extraire le numéro de tome/chapitre
        tome_num, tome_prefix = extract_tome_number(book_file.name)

        # Déterminer la team et la date
        default_date = metadata.get("date", "")
        if tome_num:
            team = get_team_for_tome(tome_num, team_rules, default_team)
            date = get_date_for_tome(tome_num, tome_dates, default_date)
            titre = f"{metadata['titre']} {tome_prefix}{tome_num:02d}"
        else:
            team = default_team
            date = default_date
            titre = metadata["titre"]

        # Créer une copie des métadonnées pour ce fichier
        file_metadata = metadata.copy()
        file_metadata["team"] = team
        file_metadata["date"] = date
        file_metadata["titre"] = titre

        # Formater le titre
        formatted_title = format_title(file_metadata)
        logger.info(f"  Team: {team} | Date: {date} | Titre: {formatted_title}")

        # Créer le fichier torrent
        torrent_path = output_dir / f"{formatted_title}.torrent"
        logger.info(f"  Création torrent: {torrent_path.name}")
        if create_torrent(book_file, torrent_path, tracker_url):
            logger.info(f"  Torrent créé OK")
        else:
            logger.error(f"  Échec création torrent")

    logger.info(f"Terminé! {len(book_files)} fichier(s) traité(s)")


def main():
    parser = argparse.ArgumentParser(
        description="Crée des fichiers torrent pour des mangas/ebooks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python create_torrents.py "Y:\\books\\Mon Manga"
  python create_torrents.py "Y:\\books\\Mon Manga" --tracker "https://tracker.example.com/announce"
  python create_torrents.py "Y:\\books\\Mon Manga" --output "C:\\torrents"

Le fichier book.json doit être présent dans le dossier source.
        """,
    )
    parser.add_argument(
        "source",
        nargs="?",
        default=DEFAULT_SOURCE,
        help="Dossier contenant les fichiers CBZ/PDF",
    )
    parser.add_argument(
        "--tracker", "-t", default=DEFAULT_TRACKER, help="URL du tracker"
    )
    parser.add_argument(
        "--output", "-o", help="Dossier de sortie (défaut: source/output)"
    )
    parser.add_argument(
        "--json", "-j", default=DEFAULT_BOOK_JSON, help="Chemin vers book.json"
    )

    args = parser.parse_args()

    process_books(
        args.source,
        output_dir=args.output,
        tracker_url=args.tracker,
        json_path=args.json,
    )


if __name__ == "__main__":
    main()
