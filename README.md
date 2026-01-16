# CreateTorrent v1.0

Scripts Python pour créer et uploader des fichiers torrent de mangas/ebooks sur TheOldSchool.cc.

Aucune dépendance externe requise pour la création de torrents (utilise la bibliothèque Python `torf`).

## Installation

```bash
# Linux/Mac
pip install python-dotenv requests pymupdf rarfile torf

# Windows
py -m pip install python-dotenv requests pymupdf rarfile torf
```

## Configuration

Créer un fichier `.env` à la racine du projet :

```env
# Dossier source par défaut (contenant les CBZ/PDF)
SOURCE_DIR=

# Chemin vers book.json (laisser vide pour chercher dans SOURCE_DIR)
BOOK_JSON=

# Tracker URL
TRACKER_URL=https://theoldschool.cc/announce/VOTRE_PASSKEY

# API TheOldSchool.cc
API_TOKEN=VOTRE_API_TOKEN

# Délai entre uploads (en secondes)
UPLOAD_DELAY=10

# Créateur du torrent (champ "created by")
CREATED_BY=MonPseudo

# Type ID pour l'upload
# Ebook => 19
# Ebook/Audio => 20
# Ebook/Comics=> 19
# Ebook/Mangas=> 19
# Ebook/Presse=> 19
TYPE_ID=19

# API imgbb pour upload des covers (optionnel)
IMGBB_API_KEY=
```

## Scripts disponibles

### create_torrents.py

Crée des fichiers `.torrent` pour des CBZ/PDF.

### pdf_to_cbz.py

Convertit des fichiers PDF en CBZ (Comic Book Zip).

## Paramètres du torrent

Les fichiers `.torrent` générés incluent :

| Champ          | Valeur                                  |
| -------------- | --------------------------------------- |
| `piece length` | 1 Mo (2^20 bytes)                       |
| `private`      | 1 (torrent privé)                       |
| `source`       | TOS                                     |
| `created by`   | Configurable via `CREATED_BY` dans .env |

## Utilisation

### 1. Convertir des PDF en CBZ (optionnel)

```bash
# Avec le chemin en argument
python pdf_to_cbz.py "Y:\books\MonManga"

# Avec le chemin par défaut du .env (SOURCE_DIR)
python pdf_to_cbz.py

# Options
python pdf_to_cbz.py "Y:\books\MonManga" --dpi 300 --quality 100
python pdf_to_cbz.py "Y:\books\MonManga" --output "C:\cbz"
```

Options disponibles :

- `--dpi`, `-d` : Résolution des images (défaut: 300)
- `--quality`, `-q` : Qualité JPEG 1-100 (défaut: 100)
- `--output`, `-o` : Dossier de sortie (défaut: même que source)

### 2. Préparer le dossier du manga

Structure attendue :

```
Y:\books\MonManga\
├── book.json          # Métadonnées
├── MonManga T01.cbz
├── MonManga T02.cbz
└── ...
```

### 3. Créer le fichier book.json

Exemple minimal avec date globale :

```json
{
  "titre": "Mon Manga",
  "auteur": "Nom Auteur",
  "date": "2024",
  "langue": "FRENCH",
  "format": "CBZ"
}
```

Exemple avec dates par tome (sans date globale) :

```json
{
  "titre": "Mon Manga",
  "auteur": "Nom Auteur",
  "langue": "FRENCH",
  "format": "CBZ",
  "tome_dates": {
    "1": "2021",
    "2": "2021",
    "3": "2022",
    "4": "2022"
  }
}
```

Exemple complet avec teams et dates par tome :

```json
{
  "titre": "Mon Manga",
  "auteur": "Nom Auteur",
  "date": "2024",
  "langue": "FRENCH",
  "format": "CBZ",
  "team": "NOTAG",
  "team_rules": [
    [1, 10, "TeamA"],
    [11, 20, "TeamB"],
    [21, 99, "NOTAG"]
  ],
  "tome_dates": {
    "1": "2021",
    "2": "2021",
    "3": "2022",
    "4": "2022"
  }
}
```

**Note :** `date` ou `tome_dates` doit être présent (ou les deux). Si `tome_dates` est défini, il a priorité sur `date` pour les tomes concernés.

### 4. Générer les torrents

```bash
# Avec le chemin en argument
python create_torrents.py "Y:\books\MonManga"

# Avec le chemin par défaut du .env
python create_torrents.py

# Options
python create_torrents.py "Y:\books\MonManga" --tracker "https://autre-tracker.com/announce"
python create_torrents.py "Y:\books\MonManga" --output "C:\torrents"
```

Les fichiers `.torrent` sont créés dans `<source>/output/`.

**Note :** La création des torrents utilise la bibliothèque Python `torf`, aucun outil externe n'est requis.

### 5. Uploader les torrents

```bash
# Uploader tous les torrents du dossier output
python upload_torrents.py "Y:\books\MonManga\output"

# Exclure certains tomes (déjà uploadés)
python upload_torrents.py "Y:\books\MonManga\output" --skip T01 T02 T03

# Modifier le délai entre uploads
python upload_torrents.py "Y:\books\MonManga\output" --delay 15
```

Après chaque upload réussi, le fichier `.torrent` du tracker est téléchargé dans un dossier `downloaded/` :

```
MonManga/
├── output/
│   └── *.torrent           # Torrents créés par mktorrent
└── downloaded/
    └── *.torrent           # Torrents téléchargés depuis le tracker
```

## Format des noms de release

Les torrents sont nommés selon le format :

```
AUTEUR.DATE.TITRE.LANGUE.FORMAT-TEAM
```

Exemple :

```
Muneyuki.Kaneshiro.2021.Blue.Lock.T01.FRENCH.CBZ-PapriKa+.torrent
```

## Extraction du numéro de tome

Le script reconnaît plusieurs formats de nommage :

- `T01`, `T1`
- `Tome 01`, `Tome01`
- `Vol.1`, `Vol 1`
- `#1`

## API Upload (UNIT3D)

L'upload utilise l'API UNIT3D avec les paramètres suivants :

**Requis :**

- `torrent` (file) : Fichier .torrent
- `name` (string) : Nom du torrent
- `description` (string) : Description BBCode
- `category_id` (int) : ID catégorie (3 = Ebooks)
- `type_id` (int) : ID type (22 = Ebook)

**Optionnels :**

- `resolution_id` (int) : ID résolution
- `tmdb`, `imdb`, `tvdb`, `mal`, `igdb` (int) : IDs bases de données
- `anonymous` (bool) : Cacher le pseudo
- `personal_release` (bool) : Release personnelle

Documentation complète : https://hdinnovations.github.io/UNIT3D/torrent_api.html

### Description personnalisée

Créer un fichier `description.txt` à la racine du projet (à côté des scripts) pour ajouter une description à tous les uploads :

```
CreateTorrent/
├── description.txt    # Description BBCode commune à tous les uploads
├── cover.jpg          # Cover optionnelle (jpg/jpeg/png)
├── upload_torrents.py
└── ...
```

La description finale sera : `[center][b]{nom_release}[/b][/center]` suivi du contenu de `description.txt`.

### Cover automatique

Si `IMGBB_API_KEY` est configuré, la cover est gérée automatiquement :

1. **Cover manuelle** : Si un fichier `cover.jpg`, `cover.jpeg` ou `cover.png` existe à côté du script, il est utilisé pour **tous les tomes**
2. **Extraction automatique** : Sinon, la **première page de chaque fichier CBZ/CBR/PDF** est extraite comme cover individuelle pour chaque tome

L'image est uploadée sur imgbb et l'URL est ajoutée en haut de la description :

```bbcode
[center][img=350]https://i.ibb.co/xxx/cover.jpg[/img][/center]
[center][b]{nom_release}[/b][/center]

{contenu de description.txt}
```

**Dépendances pour l'extraction automatique :**
- CBZ : aucune (zipfile natif Python)
- CBR : `rarfile` (`pip install rarfile`)
- PDF : `pymupdf` (`pip install pymupdf`)
