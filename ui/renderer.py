from pathlib import Path

import pygame

from ui.camera import world_to_screen
from world.unit import UnitType


img_path = Path(".") / "img"


class RenderPipeline:
    def __init__(self, font, biome_colors):
        self.show_centers = False

        self.map_surface = None
        self.border_surface = None
        self.tile_highlights = {}
        self.map_dirty = True
        self.border_dirty = True
        self.font = font
        self.biome_colors = biome_colors

        self.fps = 60

        """dico avec les chemins des images des unités"""
        self.unit_images = {
            UnitType.SOLDIER: pygame.image.load(img_path / "soldat.png").convert_alpha(),
            UnitType.ARCHER: pygame.image.load(img_path / "archer.png").convert_alpha(),
            UnitType.CAVALRY: pygame.image.load(img_path / "cavalier.png").convert_alpha(),
            UnitType.COLON: pygame.image.load(img_path / "colon.png").convert_alpha(),
        }
        self.default_image = pygame.image.load(img_path / "soldat.png").convert_alpha()

    def clear_cache(self):
        """Vide les surfaces mises en cache pour forcer un recalcul total."""
        self.tile_highlights = {}
        self.map_dirty = True
        self.border_dirty = True
        self.map_surface = None
        self.border_surface = None

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

    def build_tile_highlight(self, tile, tile_size):
        """Crée une surface unique pour la mise en évidence d'une tuile spécifique."""
        min_x = min(c[0] for c in tile.cells)
        max_x = max(c[0] for c in tile.cells)
        min_y = min(c[1] for c in tile.cells)
        max_y = max(c[1] for c in tile.cells)

        width = (max_x - min_x + 1) * tile_size
        height = (max_y - min_y + 1) * tile_size

        surface = pygame.Surface((width, height), pygame.SRCALPHA)

        highlight_color = (255, 255, 255, 100)

        for x, y in tile.cells:
            rect = ((x - min_x) * tile_size, (y - min_y) * tile_size, tile_size, tile_size)
            surface.fill(highlight_color, rect)

        return surface, (min_x * tile_size, min_y * tile_size)

    # NOUVEAU : Méthode pour dessiner les unités
    def render_units(self, screen, game_map, cam, tile_size):
        """
        Dessine toutes les unités de la carte.
        """
        for tile in game_map.tiles.values():
            if not tile.has_units():
                continue

            # Position du centre de la tuile
            tile_center_x, tile_center_y = tile.center
            world_x = tile_center_x * tile_size
            world_y = tile_center_y * tile_size

            # Convertir en coordonnées écran
            screen_x, screen_y = world_to_screen(world_x, world_y, cam.x, cam.y, cam.zoom)

            # MODIFIÉ : Arrondir pour mieux centrer
            screen_x = round(screen_x)
            screen_y = round(screen_y)

            # Dessiner chaque unité
            """
            for unit in tile.units:
                color = unit.get_color()
                size = max(1, int(unit.get_size() * cam.zoom))

                # Dessiner le cercle
                pygame.draw.circle(screen, color, (screen_x, screen_y), size)

                # Bordure blanche
                pygame.draw.circle(screen, (255, 255, 255), (screen_x, screen_y), size, 1)
                """

            # Dessiner chaque unité
            for unit in tile.units:
                # 1. Récupérer l'image associée au type de cette unité
                # La méthode .get() renvoie self.default_image si unit.unit_type n'est pas trouvé
                base_image = self.unit_images.get(unit.unit_type, self.default_image)

                # 2. Calculer la taille souhaitée
                base_diameter = unit.get_size() * 2
                scaled_size = max(1, int(base_diameter * cam.zoom))

                # 3. Redimensionner LA bonne image
                scaled_img = pygame.transform.scale(base_image, (scaled_size, scaled_size))

                # 4. Centrer et afficher
                img_rect = scaled_img.get_rect(center=(screen_x, screen_y))

                # Pas de numéro ici, gestion de l'opacité
                opacity = unit.get_opacity()  # Retourne 1.0 ou 0.5
                alpha = int(255 * opacity)
                scaled_img.set_alpha(alpha)
                screen.blit(scaled_img, img_rect)

    def render(self, screen, game_state, cam, tile_size, hovered_tile, dt):
        self.render_world(screen, game_state.map, cam, tile_size)
        self.render_overlay(screen, game_state.map, cam, tile_size, hovered_tile)
        self.render_units(screen, game_state.map, cam, tile_size)
        self.render_ui(screen, game_state.map, hovered_tile, dt)

    def render_world(self, screen, game_map, cam, tile_size):
        if self.map_surface is None or self.map_dirty:
            self.map_surface = self.build_map_surface(game_map, tile_size)
            self.map_dirty = False

        if self.border_surface is None or self.border_dirty:
            self.border_surface = self.build_border_surface(game_map, tile_size)
            self.border_dirty = False

        window_w, window_h = pygame.display.get_window_size()
        view_rect = pygame.Rect(
            int(cam.x),
            int(cam.y),
            int(window_w / cam.zoom),
            int(window_h / cam.zoom),
        )
        map_rect = self.map_surface.get_rect()

        clipped = view_rect.clip(map_rect)
        if clipped.width <= 0 or clipped.height <= 0:
            return

        offset_x = (clipped.x - view_rect.x) * cam.zoom
        offset_y = (clipped.y - view_rect.y) * cam.zoom

        sub = self.map_surface.subsurface(clipped)

        scaled = pygame.transform.scale(
            sub,
            (
                int(clipped.width * cam.zoom),
                int(clipped.height * cam.zoom),
            ),
        )

        screen.blit(scaled, (offset_x, offset_y))

        self.last_view_rect = view_rect
        self.last_clipped = clipped
        self.last_offset = (offset_x, offset_y)

        if cam.zoom > 1.2:
            sub_b = self.border_surface.subsurface(clipped)
            scaled_b = pygame.transform.scale(
                sub_b,
                (
                    int(clipped.width * cam.zoom),
                    int(clipped.height * cam.zoom),
                ),
            )
            screen.blit(scaled_b, (offset_x, offset_y))

    def render_overlay(self, screen, game_map, cam, tile_size, hovered_tile):
        if not hovered_tile:
            return

        if hovered_tile.id not in self.tile_highlights:
            self.tile_highlights[hovered_tile.id] = self.build_tile_highlight(
                hovered_tile, tile_size
            )

        highlight_surf, (world_x, world_y) = self.tile_highlights[hovered_tile.id]
        view_rect = self.last_view_rect
        offset_x, offset_y = self.last_offset

        rel_x = world_x - view_rect.x
        rel_y = world_y - view_rect.y

        screen_x = rel_x * cam.zoom + offset_x
        screen_y = rel_y * cam.zoom + offset_y

        new_size = (
            int(highlight_surf.get_width() * cam.zoom),
            int(highlight_surf.get_height() * cam.zoom),
        )

        scaled_surf = pygame.transform.scale(highlight_surf, new_size)
        screen.blit(scaled_surf, (screen_x, screen_y))

    def render_ui(self, screen, game_map, hovered_tile, dt):
        if hovered_tile:
            text_info = self.font.render(
                f"Tile {hovered_tile.id:>5} | {hovered_tile.biome:>7} | {hovered_tile.area}",
                True,
                (255, 255, 255),
            )
            screen.blit(text_info, (10, 70))

        self.fps = (self.fps * 0.85) + (1 / dt * (1 - 0.85))
        text_FPS = self.font.render(
            f"FPS : {self.fps:.1f} | seed {game_map.seed}",
            True,
            (255, 255, 255),
        )
        screen.blit(text_FPS, (10, 90))
