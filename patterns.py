"""
Patterns regex partagés pour l'extraction des numéros de tome/chapitre.
"""

# Patterns pour extraire le numéro de tome d'un nom de fichier
TOME_EXTRACT_PATTERNS = [
    r"T(\d+)",
    r"Chapitre\s*(\d+)",
    r"Tome\s*(\d+)",
    r"Vol\.?\s*(\d+)",
    r"Volume\.?\s*(\d+)",
    r"#(\d+)",
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
        rf"Chapitre\s*0*{tome_num}(?!\d)",
        rf"Tome\s*0*{tome_num}(?!\d)",
        rf"Vol\.?\s*0*{tome_num}(?!\d)",
        rf"Volume\.?\s*0*{tome_num}(?!\d)",
        rf"#{tome_num}(?!\d)",
    ]
