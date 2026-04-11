import random, math

import pygame

from world.map import Map
from world.biome import Biome


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
    Biome.BLANK: (0, 0, 0),
    Biome.WATER: (50, 80, 200),
    Biome.PLAIN: (120, 200, 100),
    Biome.FOREST: (30, 120, 30),
    Biome.MOUNTAIN: (120, 120, 120),
    Biome.DESERT: (194, 178, 128),
}

pygame.init()

font = pygame.font.SysFont(None, 20)


def darken(color, factor=0.7):
    return tuple(int(c * factor) for c in color)


def lighten(color, amount=40):
    """Augmente la luminosité d'une couleur pour l'effet de survol"""
    return tuple(min(255, c + amount) for c in color)


def compute_tile_size(window_w, window_h):
    return min(window_w // WIDTH, window_h // HEIGHT)


def world_to_screen(x, y, camera_x, camera_y, zoom):
    return int((x - camera_x) * zoom), int((y - camera_y) * zoom)


def screen_to_world(x, y, camera_x, camera_y, zoom):
    return (x / zoom + camera_x), (y / zoom + camera_y)


def speed_coeff(zoom):
    return max(1, 1 / (math.atan((zoom - 1.2) * math.pi) / math.pi + 0.4))


# 🖼️ RENDER (CELL-BASED)
def draw_map(screen, game_map: Map, tile_size, camera_x, camera_y, zoom, hovered_tile=None):
    """Dessine les provinces cellule par cellule"""
    for tile in game_map.tiles.values():
        color = BIOME_COLORS[tile.biome]

        if tile == hovered_tile:
            color = lighten(color, 70)

        if LOG_MAP_GENERATION and hovered_tile and tile.id in hovered_tile.neighbors:
            color = lighten(color, 35)

        for x, y in tile.cells:
            # sorcellerie pour éviter un grille fantôme à certaine valeur de zoom
            wx1 = x * tile_size
            wy1 = y * tile_size
            wx2 = (x + 1) * tile_size
            wy2 = (y + 1) * tile_size

            sx1, sy1 = world_to_screen(wx1, wy1, camera_x, camera_y, zoom)
            sx2, sy2 = world_to_screen(wx2, wy2, camera_x, camera_y, zoom)

            rect = pygame.Rect(
                sx1,
                sy1,
                sx2 - sx1,
                sy2 - sy1,
            )
            pygame.draw.rect(screen, color, rect)


def draw_borders(screen, game_map: Map, tile_size, camera_x, camera_y, zoom):
    """Dessine les frontières entre provinces"""
    border_color = (20, 20, 20)

    for y in range(game_map.height):
        for x in range(game_map.width):
            tile = game_map.grid[y][x]
            if tile is None:
                continue
            for dx, dy in [(1, 0), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < game_map.width and 0 <= ny < game_map.height:
                    neighbor = game_map.grid[ny][nx]
                    if neighbor != tile:
                        wx = x * tile_size
                        wy = y * tile_size
                        sx, sy = world_to_screen(wx, wy, camera_x, camera_y, zoom)
                        size = int(tile_size * zoom)
                        if dx == 1:
                            pygame.draw.line(
                                screen, border_color, (sx + size, sy), (sx + size, sy + size), 1
                            )
                        if dy == 1:
                            pygame.draw.line(
                                screen, border_color, (sx, sy + size), (sx + size, sy + size), 1
                            )


def draw_centers(screen, game_map: Map, tile_size, camera_x, camera_y, zoom):
    for tile in game_map.tiles.values():
        x, y = tile.center

        wx = x * tile_size
        wy = y * tile_size

        sx, sy = world_to_screen(wx, wy, camera_x, camera_y, zoom)

        pygame.draw.circle(screen, (255, 255, 255), (sx, sy), 3)
        # render number of cells
        text = font.render(f"{tile.area}:{tile.id}", True, (255, 255, 255))
        screen.blit(text, (sx - 10, sy - 15))


def main():
    camera_x = 0
    camera_y = 0
    zoom = 1.0

    move_speed = 1000  # pixels/sec
    zoom_speed = 0.1

    dx, dy = 0, 0

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

        dt = clock.get_time() / 1000

        keys = pygame.key.get_pressed()

        dx, dy = dx / (1.65 + 20 * dt), dy / (1.65 + 20 * dt)
        if keys[pygame.K_z]:
            dy -= move_speed * dt / zoom
        if keys[pygame.K_s]:
            dy += move_speed * dt / zoom
        if keys[pygame.K_q]:
            dx -= move_speed * dt / zoom
        if keys[pygame.K_d]:
            dx += move_speed * dt / zoom

        if abs(dx) > 0.05 or abs(dy) > 0.05:
            camera_x += dx / (dx**2 + dy**2) ** 0.5 * speed_coeff(zoom)
            camera_y += dy / (dx**2 + dy**2) ** 0.5 * speed_coeff(zoom)

        camera_x = min(game_map.width * tile_size - window_w / zoom, max(0, camera_x))
        camera_y = min(game_map.height * tile_size - window_h / zoom, max(0, camera_y))

        mouse_x, mouse_y = pygame.mouse.get_pos()
        # Convertir pixel -> index grille
        world_x, world_y = screen_to_world(mouse_x, mouse_y, camera_x, camera_y, zoom)
        grid_x = int(world_x // tile_size)
        grid_y = int(world_y // tile_size)

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
                    # seed = random.randint(0, 1000)
                    game_map = Map(WIDTH, HEIGHT, seed, log=LOG_MAP_GENERATION)

                if event.key == pygame.K_c:
                    show_centers = not show_centers

            if event.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                before = screen_to_world(  # position monde AVANT zoom
                    mx, my, camera_x, camera_y, zoom
                )

                zoom *= 1 + event.y * 0.1
                zoom = max(1, min(zoom, 5))
                # print(f"{zoom=:.2f}, {speed_coeff(zoom)=:.2f}")
                after = screen_to_world(  # position monde APRÈS zoom
                    mx, my, camera_x, camera_y, zoom
                )

                # compensation pour zoom centré souris
                camera_x += before[0] - after[0]
                camera_y += before[1] - after[1]

        screen.fill((0, 0, 0))

        draw_map(screen, game_map, tile_size, camera_x, camera_y, zoom, hovered_tile)
        draw_borders(screen, game_map, tile_size, camera_x, camera_y, zoom)

        if show_centers:
            draw_centers(screen, game_map, tile_size, camera_x, camera_y, zoom)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
