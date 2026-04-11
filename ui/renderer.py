import pygame

from ui.camera import world_to_screen


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

    def build_tile_highlight(self, tile, tile_size):
        """Crée une surface unique pour la mise en évidence d'une tuile spécifique."""
        # On calcule la bounding box de la tuile pour ne pas créer une surface de la taille de toute la map
        min_x = min(c[0] for c in tile.cells)
        max_x = max(c[0] for c in tile.cells)
        min_y = min(c[1] for c in tile.cells)
        max_y = max(c[1] for c in tile.cells)

        width = (max_x - min_x + 1) * tile_size
        height = (max_y - min_y + 1) * tile_size

        surface = pygame.Surface((width, height), pygame.SRCALPHA)

        highlight_color = (255, 255, 255, 100)  # Couleur blanche avec une opacité de 100/255

        for x, y in tile.cells:
            rect = ((x - min_x) * tile_size, (y - min_y) * tile_size, tile_size, tile_size)
            surface.fill(highlight_color, rect)

        return surface, (min_x * tile_size, min_y * tile_size)

    # ========== NOUVEAU : Méthode pour dessiner les unités ==========
    def render_units(self, screen, game_map, cam, tile_size):
        """
        Dessine toutes les unités de la carte.
        
        Pour chaque tuile, dessine les unités comme des cercles colorés
        au-dessus du centre de la tuile.
        
        Args:
            screen: Surface pygame du rendu
            game_map: La carte avec toutes les tuiles
            cam: Caméra (pour les transformations de coordonnées)
            tile_size: Taille d'une tuile en pixels
        """
        for tile in game_map.tiles.values():
            # Si la tuile n'a pas d'unités, on saute
            if not tile.has_units():
                continue
            
            # Position du centre de la tuile en coordonnées monde
            tile_center_x, tile_center_y = tile.center
            world_x = tile_center_x * tile_size
            world_y = tile_center_y * tile_size
            
            # Convertir en coordonnées écran
            screen_x, screen_y = world_to_screen(world_x, world_y, cam.x, cam.y, cam.zoom)
            
            # Dessiner chaque unité sur cette tuile
            for i, unit in enumerate(tile.units):
                # Décaler légèrement chaque unité si plusieurs sur la même tuile
                offset = (i - len(tile.units) / 2) * 12 * cam.zoom
                unit_screen_x = screen_x + offset
                unit_screen_y = screen_y
                
                # Récupérer la couleur et la taille de l'unité
                color = unit.get_color()
                size = int(unit.get_size() * cam.zoom)
                
                # Dessiner l'unité comme un cercle
                pygame.draw.circle(screen, color, (int(unit_screen_x), int(unit_screen_y)), max(2, size))
                
                # Ajouter une bordure blanche pour mieux voir
                pygame.draw.circle(screen, (255, 255, 255), (int(unit_screen_x), int(unit_screen_y)), max(2, size), 1)

    def render(self, screen, game_map, cam, tile_size, hovered_tile, dt):
        self.render_world(screen, game_map, cam, tile_size)
        self.render_overlay(screen, game_map, cam, tile_size, hovered_tile)
        
        # NOUVEAU : Dessiner les unités
        self.render_units(screen, game_map, cam, tile_size)
        
        self.render_ui(screen, hovered_tile, dt)

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

        # OFFSET écran
        offset_x = (clipped.x - view_rect.x) * cam.zoom
        offset_y = (clipped.y - view_rect.y) * cam.zoom

        # extraire zone valide
        sub = self.map_surface.subsurface(clipped)

        # scale seulement la partie visible
        scaled = pygame.transform.scale(
            sub,
            (
                int(clipped.width * cam.zoom),
                int(clipped.height * cam.zoom),
            ),
        )

        # dessiner au bon endroit
        screen.blit(scaled, (offset_x, offset_y))

        # stockage des paramètres pour le rendu de l'overlay
        self.last_view_rect = view_rect
        self.last_clipped = clipped
        self.last_offset = (offset_x, offset_y)

        if cam.zoom > 1.2:  # BORDERS (LOD)
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

        # On scale la surface de highlight
        scaled_surf = pygame.transform.scale(highlight_surf, new_size)
        screen.blit(scaled_surf, (screen_x, screen_y))

    def render_ui(self, screen, hovered_tile, dt):
        if hovered_tile:
            # Afficher les infos de la tuile
            text_info = self.font.render(
                f"Tile {hovered_tile.id:>5} | {hovered_tile.biome:>7} | {hovered_tile.area}",
                True,
                (255, 255, 255),
            )
            screen.blit(text_info, (10, 10))
            
            # NOUVEAU : Afficher le nombre d'unités
            units_count = len(hovered_tile.units)
            if units_count > 0:
                units_text = self.font.render(
                    f"Units: {units_count}",
                    True,
                    (200, 255, 200),
                )
                screen.blit(units_text, (10, 50))
            
            self.fps = (self.fps * 0.85) + (1 / dt * (1 - 0.85))
            text_FPS = self.font.render(
                f"FPS : {self.fps:.1f}",
                True,
                (255, 255, 255),
            )
            screen.blit(text_FPS, (10, 30))
