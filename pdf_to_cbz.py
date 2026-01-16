#!/usr/bin/env python3
"""
Convertit des fichiers PDF en CBZ (Comic Book Zip).
Extrait chaque page du PDF en image JPEG puis crée une archive ZIP renommée en .cbz
"""

import argparse
import logging
import os
import shutil
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF requis: pip install pymupdf")
    exit(1)

# Charger le fichier .env
load_dotenv(Path(__file__).parent / ".env")

# Configuration depuis .env
DEFAULT_SOURCE = os.getenv("SOURCE_DIR", "")

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def extract_page(args):
    """Extrait une page du PDF en image JPEG (pour parallélisation)."""
    pdf_path, page_num, output_path, dpi, quality = args
    doc = fitz.open(pdf_path)
    page = doc[page_num]

    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix)
    pix.save(output_path, output="jpeg", jpg_quality=quality)

    doc.close()
    return page_num


def pdf_to_cbz(pdf_path, output_path, dpi=200, quality=90, workers=None):
    """Convertit un PDF en CBZ avec extraction parallèle."""
    pdf_path = Path(pdf_path)
    output_path = Path(output_path)

    if workers is None:
        workers = min(8, os.cpu_count() or 4)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Compter les pages
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()

        logger.info(f"  {total_pages} pages à extraire ({workers} threads)")

        # Préparer les tâches
        tasks = [
            (str(pdf_path), i, str(temp_path / f"{i + 1:04d}.jpg"), dpi, quality)
            for i in range(total_pages)
        ]

        # Extraction parallèle avec ProcessPoolExecutor (plus rapide que threads pour PyMuPDF)
        completed = 0
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(extract_page, task) for task in tasks]
            for future in as_completed(futures):
                future.result()
                completed += 1
                if completed % 20 == 0 or completed == total_pages:
                    logger.info(f"  {completed}/{total_pages} pages")

        # Créer l'archive CBZ (ZIP renommé)
        cbz_path = output_path.with_suffix("")
        shutil.make_archive(str(cbz_path), "zip", temp_path)

        # Renommer .zip en .cbz
        zip_path = Path(str(cbz_path) + ".zip")
        zip_path.rename(output_path)

    return True


def process_folder(source_dir, output_dir=None, dpi=200, quality=90):
    """Convertit tous les PDF d'un dossier en CBZ."""
    source_dir = Path(source_dir)
    output_dir = Path(output_dir) if output_dir else source_dir

    if not source_dir.exists():
        logger.error(f"Dossier source introuvable: {source_dir}")
        return

    # Créer le dossier de sortie si nécessaire
    output_dir.mkdir(parents=True, exist_ok=True)

    # Trouver tous les PDF
    pdf_files = list(source_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning("Aucun fichier PDF trouvé")
        return

    logger.info(f"Trouvé {len(pdf_files)} fichier(s) PDF")
    logger.info(f"DPI: {dpi}, Qualité JPEG: {quality}")

    for i, pdf_file in enumerate(sorted(pdf_files), 1):
        logger.info(f"[{i}/{len(pdf_files)}] Conversion de: {pdf_file.name}")

        cbz_path = output_dir / f"{pdf_file.stem}.cbz"

        if cbz_path.exists():
            logger.warning(f"  Fichier existant, ignoré: {cbz_path.name}")
            continue

        try:
            pdf_to_cbz(pdf_file, cbz_path, dpi=dpi, quality=quality)
            logger.info(f"  Créé: {cbz_path.name}")
        except Exception as e:
            logger.error(f"  Erreur: {e}")

    logger.info(f"Terminé! {len(pdf_files)} fichier(s) traité(s)")


def main():
    parser = argparse.ArgumentParser(
        description="Convertit des fichiers PDF en CBZ",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python pdf_to_cbz.py "C:\\books\\manga"
  python pdf_to_cbz.py "C:\\books\\manga" --output "C:\\books\\cbz"
  python pdf_to_cbz.py "C:\\books\\manga" --dpi 200 --quality 90
        """,
    )
    parser.add_argument(
        "source",
        nargs="?",
        default=DEFAULT_SOURCE,
        help="Dossier contenant les fichiers PDF",
    )
    parser.add_argument(
        "--output", "-o", help="Dossier de sortie (défaut: même que source)"
    )
    parser.add_argument(
        "--dpi", "-d", type=int, default=200, help="Résolution des images (défaut: 200)"
    )
    parser.add_argument(
        "--quality", "-q", type=int, default=90, help="Qualité JPEG 1-100 (défaut: 90)"
    )

    args = parser.parse_args()

    process_folder(args.source, output_dir=args.output, dpi=args.dpi, quality=args.quality)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()  # Requis pour Windows
    main()
