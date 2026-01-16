# Changelog

## [1.0.0] - 2025-01-18

Première version stable.

### create_torrents.py
- Création de fichiers `.torrent` pour CBZ/PDF avec la bibliothèque Python `torf`
- Aucun outil externe requis (plus besoin de mktorrent ou WSL)
- Métadonnées via `book.json` (titre, auteur, date, langue, format, team)
- Support des dates par tome (`tome_dates`)
- Support des teams par plage de tomes (`team_rules`)
- Formatage des noms de release : `AUTEUR.DATE.TITRE.LANGUE.FORMAT-TEAM`
- Nettoyage automatique des caractères spéciaux et accents
- Configuration via `.env` (SOURCE_DIR, TRACKER_URL, BOOK_JSON, CREATED_BY)
- Paramètres torrent : piece length 1MB, private, source TOS
- Les champs `auteur` et `date` sont optionnels dans book.json

### pdf_to_cbz.py
- Conversion de fichiers PDF en CBZ (Comic Book Zip)
- Extraction parallèle des pages (8 threads max)
- DPI configurable (défaut: 200)
- Qualité JPEG configurable (défaut: 90)
- Progression affichée toutes les 20 pages
- Configuration via `.env` (SOURCE_DIR)

### upload_torrents.py
- Upload des torrents via API UNIT3D
- Délai configurable entre uploads
- Option pour exclure certains tomes (`--skip`)
- Support de `description.txt` pour ajouter une description personnalisée
- Téléchargement automatique du fichier .torrent après upload réussi
- Support des covers : upload automatique sur imgbb si `IMGBB_API_KEY` configuré
- Cover manuelle (`cover.jpg/png/jpeg`) ou extraction automatique depuis la première page de chaque tome
- Support des fichiers CBZ, CBR (via `rarfile`) et PDF (via `pymupdf`)
