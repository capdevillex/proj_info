"""
map_generator.py
Module autonome qui génère un pavage (tilemap) sous forme de surface Pygame.
Importez generate_map() depuis votre script principal.
"""

import pygame
import random

# ── Palette de tuiles ────────────────────────────────────────────────────────
TILE_COLORS = {
    0: (34,  139,  34),   # herbe
    1: (194, 178, 128),   # sable
    2: (70,  130, 180),   # eau
    3: (139,  90,  43),   # terre
    4: (200, 200, 200),   # roche
}

TILE_SIZE = 32  # pixels par tuile


def _generate_grid(cols: int, rows: int, seed: int | None = None) -> list[list[int]]:
    """Génère une grille 2‑D de types de tuiles (bruit simplifié)."""
    rng = random.Random(seed)
    grid = []
    for r in range(rows):
        row = []
        for c in range(cols):
            # Bord = eau, intérieur = aléatoire pondéré
            if r == 0 or r == rows - 1 or c == 0 or c == cols - 1:
                row.append(2)
            else:
                row.append(rng.choices([0, 1, 3, 4], weights=[50, 20, 20, 10])[0])
        grid.append(row)
    return grid


def generate_map(
    cols: int = 20,
    rows: int = 15,
    tile_size: int = TILE_SIZE,
    seed: int | None = 42,
) -> pygame.Surface:
    """
    Retourne une pygame.Surface représentant le pavage.

    Paramètres
    ----------
    cols, rows  : dimensions de la grille en tuiles
    tile_size   : taille d'une tuile en pixels
    seed        : graine pour la reproductibilité (None = aléatoire)
    """
    grid = _generate_grid(cols, rows, seed)
    width  = cols * tile_size
    height = rows * tile_size
    surface = pygame.Surface((width, height))

    for r, row in enumerate(grid):
        for c, tile_id in enumerate(row):
            color = TILE_COLORS.get(tile_id, (0, 0, 0))
            rect  = pygame.Rect(c * tile_size, r * tile_size, tile_size, tile_size)
            pygame.draw.rect(surface, color, rect)
            # Grille fine
            pygame.draw.rect(surface, (0, 0, 0, 60), rect, 1)

    return surface
