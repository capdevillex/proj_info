import random, math
import pygame  # type: ignore

from world.map import Map
from ui.camera import Camera, world_to_screen, screen_to_world


# -------------------------
# 🎨 CONFIG
# -------------------------
TILE_SIZE = 10
HEIGHT = 100
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

pygame.init()
font = pygame.font.SysFont(None, 20)


# -------------------------
# 🧰 UTILS
# -------------------------
def lighten(color, amount=40):
    return tuple(min(255, c + amount) for c in color)


def compute_tile_size(window_w, window_h):
    return min(window_w // WIDTH, window_h // HEIGHT)


# -------------------------
# 🖼️ RENDER WORLD
# -------------------------
def draw_map(screen, game_map, tile_size, cam, hovered_tile):
    for tile in game_map.tiles.values():
        color = BIOME_COLORS[tile.biome]

        if tile == hovered_tile:
            color = lighten(color, 70)

        if LOG_MAP_GENERATION and hovered_tile and tile.id in hovered_tile.neighbors:
            color = lighten(color, 35)

        for x, y in tile.cells:
            wx1 = x * tile_size
            wy1 = y * tile_size
            wx2 = (x + 1) * tile_size
            wy2 = (y + 1) * tile_size

            sx1, sy1 = world_to_screen(wx1, wy1, cam.x, cam.y, cam.zoom)
            sx2, sy2 = world_to_screen(wx2, wy2, cam.x, cam.y, cam.zoom)

            rect = pygame.Rect(sx1, sy1, sx2 - sx1, sy2 - sy1)
            pygame.draw.rect(screen, color, rect)


def draw_borders(screen, game_map, tile_size, cam):
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
                        sx, sy = world_to_screen(wx, wy, cam.x, cam.y, cam.zoom)
                        size = int(tile_size * cam.zoom)

                        if dx == 1:
                            pygame.draw.line(
                                screen, border_color, (sx + size, sy), (sx + size, sy + size), 1
                            )
                        if dy == 1:
                            pygame.draw.line(
                                screen, border_color, (sx, sy + size), (sx + size, sy + size), 1
                            )


def draw_centers(screen, game_map, tile_size, cam):
    for tile in game_map.tiles.values():
        x, y = tile.center
        wx = x * tile_size
        wy = y * tile_size
        sx, sy = world_to_screen(wx, wy, cam.x, cam.y, cam.zoom)

        pygame.draw.circle(screen, (255, 255, 255), (sx, sy), 3)

        text = font.render(f"{tile.area}:{tile.id}", True, (255, 255, 255))
        screen.blit(text, (sx - 10, sy - 15))


# -------------------------
# 🧠 HOVER
# -------------------------
def get_hovered_tile(game_map, cam, tile_size):
    mouse_x, mouse_y = pygame.mouse.get_pos()

    world_x, world_y = screen_to_world(mouse_x, mouse_y, cam.x, cam.y, cam.zoom)

    grid_x = int(world_x // tile_size)
    grid_y = int(world_y // tile_size)

    if 0 <= grid_x < game_map.width and 0 <= grid_y < game_map.height:
        tile_id = game_map.grid[grid_y][grid_x]
        return game_map.tiles.get(tile_id)

    return None


# -------------------------
# 🎛️ RENDER PIPELINE
# -------------------------
class RenderPipeline:
    def __init__(self):
        self.show_centers = False

    def render(self, screen, game_map, cam, tile_size, hovered_tile):
        self.render_world(screen, game_map, cam, tile_size, hovered_tile)
        self.render_overlay(screen, game_map, cam, tile_size, hovered_tile)
        self.render_ui(screen, hovered_tile)

    def render_world(self, screen, game_map, cam, tile_size, hovered_tile):
        draw_map(screen, game_map, tile_size, cam, hovered_tile)
        draw_borders(screen, game_map, tile_size, cam)

    def render_overlay(self, screen, game_map, cam, tile_size, hovered_tile):
        if self.show_centers:
            draw_centers(screen, game_map, tile_size, cam)

    def render_ui(self, screen, hovered_tile):
        if hovered_tile:
            text = font.render(
                f"Tile {hovered_tile.id} | {hovered_tile.biome} | {hovered_tile.area}",
                True,
                (255, 255, 255),
            )
            screen.blit(text, (10, 10))


# -------------------------
# 🚀 MAIN
# -------------------------
def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("4X Map Generator")

    clock = pygame.time.Clock()

    seed = random.randint(0, 1000)
    game_map = Map(WIDTH, HEIGHT, seed, avg_pts_per_tile=30, log=LOG_MAP_GENERATION)

    camera = Camera()
    renderer = RenderPipeline()

    running = True

    while running:
        dt = clock.tick(60) / 1000
        window_w, window_h = screen.get_size()
        tile_size = compute_tile_size(window_w, window_h)

        # -------- INPUT --------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    print(" --- Regenerating map --- ")
                    seed = random.randint(0, 1000)
                    game_map = Map(WIDTH, HEIGHT, seed, avg_pts_per_tile=30, log=LOG_MAP_GENERATION)

                if event.key == pygame.K_c:
                    renderer.show_centers = not renderer.show_centers

            if event.type == pygame.MOUSEWHEEL:
                camera.apply_zoom(pygame.mouse.get_pos(), event.y)

        # -------- UPDATE --------
        camera.update(dt, game_map, tile_size, window_w, window_h)
        hovered_tile = get_hovered_tile(game_map, camera, tile_size)

        # -------- RENDER --------
        screen.fill((0, 0, 0))
        renderer.render(screen, game_map, camera, tile_size, hovered_tile)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
