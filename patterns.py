"""
Patterns regex partagés pour l'extraction des numéros de tome/chapitre.
"""

# Patterns pour extraire le numéro de tome d'un nom de fichier
# Chaque entrée : (pattern, prefix) où prefix est "T" pour tome ou "C" pour chapitre
TOME_EXTRACT_PATTERNS = [
    (r"T(\d+)", "T"),
    (r"C(\d+)", "C"),
    (r"Chapitre\s*(\d+)", "C"),
    (r"Tome\s*(\d+)", "T"),
    (r"Vol\.?\s*(\d+)", "T"),
    (r"Volume\.?\s*(\d+)", "T"),
    (r"#(\d+)", "T"),
]


def get_tome_match_patterns(tome_num):
    """
    Génère les patterns regex pour matcher un numéro de tome spécifique.

    Args:
        tome_num: Le numéro de tome à matcher

    Returns:
        Liste de patterns regex compilés
    """
    return [
        rf"T0*{tome_num}(?!\d)",
        rf"C0*{tome_num}(?!\d)",
        rf"Chapitre\s*0*{tome_num}(?!\d)",
        rf"Tome\s*0*{tome_num}(?!\d)",
        rf"Vol\.?\s*0*{tome_num}(?!\d)",
        rf"Volume\.?\s*0*{tome_num}(?!\d)",
        rf"#{tome_num}(?!\d)",
    ]
