"""
main.py
Fenêtre Pygame qui affiche la map générée par map_generator.py, centrée à l'écran.
Lancez : python main.py
"""

import pygame
import sys

# ── Import du module générateur ──────────────────────────────────────────────
from map_generator import generate_map

# ── Constantes de la fenêtre ─────────────────────────────────────────────────
WIN_W, WIN_H = 900, 700
BG_COLOR     = (30, 30, 30)   # fond sombre autour de la map
FPS          = 60

# ── Paramètres de la map (modifiables) ───────────────────────────────────────
MAP_COLS      = 24
MAP_ROWS      = 18
MAP_TILE_SIZE = 32
MAP_SEED      = 42            # None → régénération aléatoire à chaque lancement


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Pavage centré – map_generator")
    clock = pygame.time.Clock()

    # ── Génération de la map via le module externe ────────────────────────────
    map_surface = generate_map(
        cols=MAP_COLS,
        rows=MAP_ROWS,
        tile_size=MAP_TILE_SIZE,
        seed=MAP_SEED,
    )

    # Position pour centrer la map dans la fenêtre
    map_rect = map_surface.get_rect(center=(WIN_W // 2, WIN_H // 2))

    # ── Boucle principale ─────────────────────────────────────────────────────
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                # R → régénère avec une graine aléatoire
                if event.key == pygame.K_r:
                    map_surface = generate_map(
                        cols=MAP_COLS,
                        rows=MAP_ROWS,
                        tile_size=MAP_TILE_SIZE,
                        seed=None,
                    )
                    map_rect = map_surface.get_rect(center=(WIN_W // 2, WIN_H // 2))

        screen.fill(BG_COLOR)
        screen.blit(map_surface, map_rect)

        # Légende
        font = pygame.font.SysFont("monospace", 14)
        hint = font.render("R : régénérer  |  Échap : quitter", True, (180, 180, 180))
        screen.blit(hint, (10, 10))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
