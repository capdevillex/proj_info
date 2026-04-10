import random, math
import pygame  # type: ignore

from world.map import Map
from world.biome import Biome
from ui.camera import Camera, world_to_screen, screen_to_world


# -------------------------
# 🎨 CONFIG
# -------------------------
TILE_SIZE = 6
HEIGHT = 200
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
def draw_map(screen, game_map: Map, tile_size, cam, hovered_tile, camera_x, camera_y, zoom):
    min_x = camera_x - TILE_SIZE
    max_x = camera_x + WIDTH * TILE_SIZE / zoom + TILE_SIZE

    min_y = camera_y - TILE_SIZE
    max_y = camera_y + HEIGHT * TILE_SIZE / zoom + TILE_SIZE

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

            if wx1 < min_x or wx2 > max_x or wy1 < min_y or wy2 > max_y:  # Culling
                continue

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

        self.map_surface = None
        self.border_surface = None
        self.map_dirty = True
        self.border_dirty = True

    def build_map_surface(self, game_map, tile_size):
        """Méthode de pré-render, prépare la surface Pygame sur laquelle rendre la carte"""
        width_px = game_map.width * tile_size
        height_px = game_map.height * tile_size

        surface = pygame.Surface((width_px, height_px))

        for tile in game_map.tiles.values():
            color = BIOME_COLORS[tile.biome]

            for x, y in tile.cells:
                surface.fill(
                    color,
                    (x * tile_size, y * tile_size, tile_size, tile_size),
                )

        return surface

    def build_border_surface(self, game_map, tile_size):
        """Méthode de pré-render, prépare la surface Pygame sur laquelle rendre les frontières des provinces"""
        width_px = game_map.width * tile_size
        height_px = game_map.height * tile_size

        surface = pygame.Surface((width_px, height_px), pygame.SRCALPHA)

        color = (20, 20, 20)

        for y in range(game_map.height):
            for x in range(game_map.width):
                tile = game_map.grid[y][x]

                for dx, dy in [(1, 0), (0, 1)]:
                    nx, ny = x + dx, y + dy

                    if 0 <= nx < game_map.width and 0 <= ny < game_map.height:
                        if game_map.grid[ny][nx] != tile:
                            px = x * tile_size
                            py = y * tile_size

                            if dx == 1:
                                pygame.draw.line(
                                    surface,
                                    color,
                                    (px + tile_size, py),
                                    (px + tile_size, py + tile_size),
                                    1,
                                )
                            if dy == 1:
                                pygame.draw.line(
                                    surface,
                                    color,
                                    (px, py + tile_size),
                                    (px + tile_size, py + tile_size),
                                    1,
                                )

        return surface

    def render(self, screen, game_map, cam, tile_size, hovered_tile, dt):
        self.render_world(screen, game_map, cam, tile_size)
        self.render_overlay(screen, game_map, cam, tile_size, hovered_tile)
        self.render_ui(screen, hovered_tile, dt)

    def render_world(self, screen, game_map, cam, tile_size):
        if self.map_surface is None or self.map_dirty:
            self.map_surface = self.build_map_surface(game_map, tile_size)
            self.map_dirty = False

        if self.border_surface is None or self.border_dirty:
            self.border_surface = self.build_border_surface(game_map, tile_size)
            self.border_dirty = False

        view_rect = pygame.Rect(
            int(cam.x),
            int(cam.y),
            int(screen.get_width() / cam.zoom),
            int(screen.get_height() / cam.zoom),
        )

        sub = self.map_surface.subsurface(view_rect)
        scaled = pygame.transform.scale(sub, screen.get_size())
        screen.blit(scaled, (0, 0))

        if cam.zoom > 1.2:  # BORDERS (LOD)
            sub_b = self.border_surface.subsurface(view_rect)
            scaled_b = pygame.transform.scale(sub_b, screen.get_size())
            screen.blit(scaled_b, (0, 0))

    def render_overlay(self, screen, game_map, cam, tile_size, hovered_tile):
        if not hovered_tile:
            return

        color = (255, 255, 255)

        for x, y in hovered_tile.cells:
            wx = x * tile_size
            wy = y * tile_size

            sx, sy = world_to_screen(wx, wy, cam.x, cam.y, cam.zoom)
            size = int(tile_size * cam.zoom)

            pygame.draw.rect(screen, color, (sx, sy, size, size), 1)

    def render_ui(self, screen, hovered_tile, dt):
        if hovered_tile:
            text_info = font.render(
                f"Tile {hovered_tile.id:>5} | {hovered_tile.biome:>7} | {hovered_tile.area}",
                True,
                (255, 255, 255),
            )
            screen.blit(text_info, (10, 10))
            text_FPS = font.render(
                f"FPS : {1/dt:.3f}",
                True,
                (255, 255, 255),
            )
            screen.blit(text_FPS, (10, 30))


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
        dt = clock.tick(350) / 1000
        window_w, window_h = screen.get_size()
        tile_size = compute_tile_size(window_w, window_h)

        # -------- INPUT --------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    print(" --- Regenerating map --- ")
                    renderer.map_dirty = True
                    renderer.border_dirty = True
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
        renderer.render(screen, game_map, camera, tile_size, hovered_tile, dt)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
