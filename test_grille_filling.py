import random

import pygame  # type: ignore

from world.map import Map


# -------------------------
# 🎨 CONFIG
# -------------------------
TILE_SIZE = 12
HEIGHT = 80
WIDTH = (HEIGHT * 16) // 9

SCREEN_WIDTH = WIDTH * TILE_SIZE
SCREEN_HEIGHT = HEIGHT * TILE_SIZE

LOG_MAP_GENERATION = True


BIOME_COLORS = {
    "water": (50, 80, 200),
    "plain": (120, 200, 100),
    "forest": (30, 120, 30),
    "mountain": (120, 120, 120),
}


def darken(color, factor=0.7):
    return tuple(int(c * factor) for c in color)


def lighten(color, amount=40):
    """Augmente la luminosité d'une couleur pour l'effet de survol"""
    return tuple(min(255, c + amount) for c in color)


def compute_tile_size(window_w, window_h):
    return min(window_w // WIDTH, window_h // HEIGHT)


# -------------------------
# 🖼️ RENDER (CELL-BASED)
# -------------------------


def draw_map(screen, game_map: Map, tile_size, hovered_tile=None):
    """Dessine les provinces cellule par cellule"""
    for tile in game_map.tiles.values():
        color = BIOME_COLORS[tile.biome]  # type: ignore

        if tile == hovered_tile:
            color = lighten(color, 70)

        if LOG_MAP_GENERATION and hovered_tile and tile.id in hovered_tile.neighbors:
            color = lighten(color, 35)

        for x, y in tile.cells:
            rect = pygame.Rect(
                x * tile_size,
                y * tile_size,
                tile_size,
                tile_size,
            )
            pygame.draw.rect(screen, color, rect)


def draw_borders(screen, game_map: Map, tile_size):
    """Dessine les frontières entre provinces"""
    border_color = (20, 20, 20)

    for y in range(game_map.height):
        for x in range(game_map.width):
            tile = game_map.grid[y][x]
            if tile is None:
                continue

            # vérifier voisins
            for dx, dy in [(1, 0), (0, 1)]:
                nx, ny = x + dx, y + dy

                if 0 <= nx < game_map.width and 0 <= ny < game_map.height:
                    neighbor = game_map.grid[ny][nx]

                    if neighbor != tile:
                        x1 = x * tile_size
                        y1 = y * tile_size

                        if dx == 1:
                            pygame.draw.line(
                                screen,
                                border_color,
                                (x1 + tile_size, y1),
                                (x1 + tile_size, y1 + tile_size),
                                1,
                            )
                        if dy == 1:
                            pygame.draw.line(
                                screen,
                                border_color,
                                (x1, y1 + tile_size),
                                (x1 + tile_size, y1 + tile_size),
                                1,
                            )


def draw_centers(screen, game_map: Map, tile_size):
    for tile in game_map.tiles.values():
        x, y = tile.center

        pygame.draw.circle(
            screen,
            (255, 255, 255),
            (int(x * tile_size), int(y * tile_size)),
            3,
        )
        # render number of cells
        font = pygame.font.SysFont(None, 20)
        text = font.render(str(len(tile.cells)), True, (255, 255, 255))
        screen.blit(text, (int(x * tile_size) - 10, int(y * tile_size) - 15))


# -------------------------
# 🚀 MAIN
# -------------------------


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("4X Map Generator")

    clock = pygame.time.Clock()

    seed = random.randint(0, 1000)
    game_map = Map(WIDTH, HEIGHT, seed, log=LOG_MAP_GENERATION)

    running = True
    show_centers = False

    while running:
        window_w, window_h = screen.get_size()
        tile_size = compute_tile_size(window_w, window_h)

        mouse_x, mouse_y = pygame.mouse.get_pos()
        # Convertir pixel -> index grille
        grid_x = mouse_x // tile_size
        grid_y = mouse_y // tile_size

        hovered_tile = None
        if 0 <= grid_x < game_map.width and 0 <= grid_y < game_map.height:
            # On récupère la province (Tile) à cette position via la grille interne
            tile_id = game_map.grid[grid_y][grid_x]
            hovered_tile = game_map.tiles.get(tile_id)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    print("\n--- REGEN MAP ---")
                    seed = random.randint(0, 1000)
                    game_map = Map(WIDTH, HEIGHT, seed, log=LOG_MAP_GENERATION)

                if event.key == pygame.K_c:
                    show_centers = not show_centers

        screen.fill((0, 0, 0))

        draw_map(screen, game_map, tile_size, hovered_tile)
        draw_borders(screen, game_map, tile_size)

        if show_centers:
            draw_centers(screen, game_map, tile_size)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
