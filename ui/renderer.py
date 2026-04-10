import pygame

from ui.camera import world_to_screen


class RenderPipeline:
    def __init__(self, font, biome_colors):
        self.show_centers = False

        self.map_surface = None
        self.border_surface = None
        self.map_dirty = True
        self.border_dirty = True
        self.font = font
        self.biome_colors = biome_colors

        self.fps = 60  # Valeur de départ arbitraire

    def build_map_surface(self, game_map, tile_size):
        """Méthode de pré-render, prépare la surface Pygame sur laquelle rendre la carte"""
        width_px = game_map.width * tile_size
        height_px = game_map.height * tile_size

        surface = pygame.Surface((width_px, height_px))

        for tile in game_map.tiles.values():
            color = self.biome_colors[tile.biome]

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

            pygame.draw.rect(screen, color, (sx + 5, sy + 5, size, size), 1)

    def render_ui(self, screen, hovered_tile, dt):
        if hovered_tile:
            text_info = self.font.render(
                f"Tile {hovered_tile.id:>5} | {hovered_tile.biome:>7} | {hovered_tile.area}",
                True,
                (255, 255, 255),
            )
            screen.blit(text_info, (10, 10))
            self.fps = (self.fps * 0.85) + (1 / dt * (1 - 0.85))
            text_FPS = self.font.render(
                f"FPS : {self.fps:.1f}",
                True,
                (255, 255, 255),
            )
            screen.blit(text_FPS, (10, 30))
