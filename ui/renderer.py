from pathlib import Path
from typing import Optional

import pygame
from pygame import base

from core.game_state import GameState
from ui.camera import world_to_screen
from world.map import Map
from world.resources import Resource
from world.tile import Tile
from world.unit import UnitType
from config import GameConfig as gc


img_path = Path(".") / "img"

resource_scaling = {
    "gold": 1.7,
    "iron": 1.7,
    "stone": 2.3,
    "wood": 2.2,
    "food": 2,
    "default": 1.0,
}


def crop_alpha(surface):
    """Recadre une surface SRCALPHA à son contenu non-transparent."""
    rect = surface.get_bounding_rect()
    return surface.subsurface(rect).copy()


class RenderPipeline:
    def __init__(self, font, biome_colors):
        self.show_centers = False

        self._overlay_sf = None
        self.map_sf = None
        self.border_sf = None
        self.resource_sf = None
        self.city_overlay_sf = None
        self.city_border_sf = None
        self.tile_highlights = {}
        self.map_dirty = True
        self.resource_dirty = True
        self.border_dirty = True
        self.city_dirty = True
        self.font = font
        self.biome_colors = biome_colors

        self.fps = 60

        # dico avec les chemins des images des unités
        self.unit_images = {
            UnitType.SOLDIER: pygame.image.load(img_path / "soldat.png").convert_alpha(),
            UnitType.ARCHER: pygame.image.load(img_path / "archer.png").convert_alpha(),
            UnitType.CAVALRY: pygame.image.load(img_path / "cavalier.png").convert_alpha(),
            UnitType.COLON: pygame.image.load(img_path / "colon.png").convert_alpha(),
            UnitType.BABY: pygame.image.load(img_path / "baby.png").convert_alpha(),
        }
        self.default_image = pygame.image.load(img_path / "soldat.png").convert_alpha()
        self.unit_cache = {}

        # dico avec les images des ressources
        self.rsrc_img = {
            r: crop_alpha(pygame.image.load(img_path / (r.value + ".png")).convert_alpha())
            for r in Resource
            if r != Resource.NONE
        }

        self._scaled_cache = {}

        # Couleurs pour les différents propriétaires de villes
        self.owner_colors = [
            (100, 150, 255),  # Bleu pour joueur 0
            (255, 100, 100),  # Rouge pour joueur 1
            (100, 255, 100),  # Vert pour joueur 2
            (255, 255, 100),  # Jaune pour joueur 3
            (255, 100, 255),  # Magenta pour joueur 4
            (100, 255, 255),  # Cyan pour joueur 5
        ]

    def clear_cache(self):
        """Vide les surfaces mises en cache pour forcer un recalcul total."""
        self.tile_highlights = {}
        self._scaled_cache = {}
        self.map_dirty = True
        self.border_dirty = True
        self.city_dirty = True
        self.resource_dirty = True
        self.map_sf = None
        self.resource_sf = None
        self.border_sf = None
        self.city_overlay_sf = None
        self.city_border_sf = None

    def get_owner_color(self, owner_id):
        """Retourne la couleur associée à un propriétaire."""
        return self.owner_colors[owner_id % len(self.owner_colors)]

    def get_unit_image(self, unit, size):
        """Retourne l'image redimensionnée pour une unité donnée."""
        key = (unit.unit_type, size)
        if key not in self.unit_cache:
            base_image = self.unit_images.get(unit.unit_type, self.default_image)
            scaled_img = pygame.transform.scale(base_image, (size, size))
            self.unit_cache[key] = scaled_img
        return self.unit_cache[key]

    def build_map_sf(self, game_state: GameState, game_map: Map, tile_size):
        """Méthode de pré-render, prépare la surface Pygame sur laquelle rendre la carte"""
        width_px = game_map.width * tile_size
        height_px = game_map.height * tile_size
        surface = pygame.Surface((width_px, height_px))

        for tile in game_map.tiles.values():
            color = self.biome_colors[tile.biome]
            if game_state.use_fow and not (game_state.visibility & (1 << tile.id)):
                # assombrir les tuiles non visibles
                color = tuple(c // 2 for c in color)
            if game_state.use_ti and not (game_state.discovered & (1 << tile.id)):
                # rendre les tuiles non découvertes en gris foncé
                color = (30, 30, 30)
            for x, y in tile.cells:
                surface.fill(
                    color,
                    (x * tile_size, y * tile_size, tile_size, tile_size),
                )
        return surface

    def build_resource_sf(self, game_state, game_map, tile_size):
        """Méthode de pré-render, prépare la surface Pygame sur laquelle rendre les ressources des provinces"""
        scale = gc.RESOURCE_BASE_SCALE
        width_px = game_map.width * tile_size * scale
        height_px = game_map.height * tile_size * scale
        surface = pygame.Surface((width_px, height_px), pygame.SRCALPHA)

        for tile in game_map.tiles.values():
            if not tile.resource or tile.resource == Resource.NONE:
                continue
            if game_state.use_ti and not (game_state.discovered & (1 << tile.id)):
                continue  # Ne pas afficher les ressources des tuiles non découvertes
            try:
                scale_factor = resource_scaling.get(
                    tile.resource.value[:-1], resource_scaling["default"]
                )
                target_size = int(
                    tile_size * scale_factor * scale * int(tile.resource.value[-1]) ** 0.5
                )
                base_img = self.rsrc_img[tile.resource]
                img = pygame.transform.scale(
                    base_img,
                    (target_size, target_size * base_img.get_height() // base_img.get_width()),
                )
                world_x = tile.center[0] * tile_size * scale
                world_y = tile.center[1] * tile_size * scale
                surface.blit(
                    img,
                    (
                        int(world_x - target_size // 2),
                        int(
                            world_y
                            - target_size * base_img.get_height() // base_img.get_width() // 2
                        ),
                    ),
                )
            except Exception as e:
                print(f"Erreur ressource {tile.resource.value}: {e}")
        return surface

    def build_city_overlay_sf(self, game_map, game_state, tile_size):
        """Construit une surface avec les teintes de couleur pour les villes."""
        width_px = game_map.width * tile_size
        height_px = game_map.height * tile_size

        surface = pygame.Surface((width_px, height_px), pygame.SRCALPHA)

        # Pour chaque ville, teinter ses tuiles
        for city in game_state.cities:
            owner_color = self.get_owner_color(city.owner)

            # Créer une couleur semi-transparente pour la teinte
            tint_color = (*owner_color, 60)  # Alpha à 60 pour une teinte légère

            # Teinter toutes les tuiles de la ville
            for tile_id in city.tile_ids:
                if tile_id not in game_map.tiles:
                    continue

                tile = game_map.tiles[tile_id]

                # Dessiner chaque cellule de la tuile avec la teinte
                for x, y in tile.cells:
                    pygame.draw.rect(
                        surface, tint_color, (x * tile_size, y * tile_size, tile_size, tile_size)
                    )

        return surface

    def build_city_border_sf(self, game_map, game_state, tile_size):
        """Construit une surface avec les contours colorés des villes."""
        width_px = game_map.width * tile_size
        height_px = game_map.height * tile_size

        surface = pygame.Surface((width_px, height_px), pygame.SRCALPHA)

        # Pour chaque ville, dessiner les contours de ses tuiles
        for city in game_state.cities:
            owner_color = self.get_owner_color(city.owner)

            # Créer un set des tuiles de la ville pour vérification rapide
            city_tile_ids = city.tile_ids

            # Parcourir toutes les cellules de toutes les tuiles de la ville
            for tile_id in city_tile_ids:
                if tile_id not in game_map.tiles:
                    continue

                tile = game_map.tiles[tile_id]

                for x, y in tile.cells:
                    # Vérifier les 4 directions pour dessiner les bordures
                    for dx, dy in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
                        nx, ny = x + dx, y + dy

                        # Si on sort de la carte ou si la cellule voisine n'appartient pas à la ville
                        if 0 <= nx < game_map.width and 0 <= ny < game_map.height:
                            neighbor_tile_id = game_map.grid[ny][nx]

                            # Dessiner une bordure si le voisin n'est pas dans la ville
                            if neighbor_tile_id not in city_tile_ids:
                                px = x * tile_size
                                py = y * tile_size

                                if dx == 1:  # Bordure droite
                                    pygame.draw.line(
                                        surface,
                                        owner_color,
                                        (px + tile_size, py),
                                        (px + tile_size, py + tile_size),
                                        2,
                                    )
                                elif dx == -1:  # Bordure gauche
                                    pygame.draw.line(
                                        surface, owner_color, (px, py), (px, py + tile_size), 2
                                    )
                                elif dy == 1:  # Bordure bas
                                    pygame.draw.line(
                                        surface,
                                        owner_color,
                                        (px, py + tile_size),
                                        (px + tile_size, py + tile_size),
                                        2,
                                    )
                                elif dy == -1:  # Bordure haut
                                    pygame.draw.line(
                                        surface, owner_color, (px, py), (px + tile_size, py), 2
                                    )
                        else:
                            # Bordure de la carte
                            px = x * tile_size
                            py = y * tile_size

                            if dx == 1 and nx >= game_map.width:
                                pygame.draw.line(
                                    surface,
                                    owner_color,
                                    (px + tile_size, py),
                                    (px + tile_size, py + tile_size),
                                    2,
                                )
                            elif dx == -1 and nx < 0:
                                pygame.draw.line(
                                    surface, owner_color, (px, py), (px, py + tile_size), 2
                                )
                            elif dy == 1 and ny >= game_map.height:
                                pygame.draw.line(
                                    surface,
                                    owner_color,
                                    (px, py + tile_size),
                                    (px + tile_size, py + tile_size),
                                    2,
                                )
                            elif dy == -1 and ny < 0:
                                pygame.draw.line(
                                    surface, owner_color, (px, py), (px + tile_size, py), 2
                                )

        return surface

    def build_border_sf(self, game_map, tile_size):
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

    # Méthode pour dessiner les unités
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

            # Arrondir pour mieux centrer
            screen_x = int(screen_x)
            screen_y = int(screen_y)

            # Dessiner chaque unité
            for unit in tile.units:
                # 1. Récupérer l'image associée au type de cette unité
                base_image = self.unit_images.get(unit.unit_type, self.default_image)

                # 2. Calculer la taille souhaitée
                base_diameter = unit.SIZE * 2
                # quantization pour améliorer les performances du cache et éviter les tailles d'image trop petites
                scaled_size = (base_diameter * cam.zoom // 4) * 4
                scaled_size = max(1, scaled_size)

                # 3. Redimensionner LA bonne image
                scaled_img = self.get_unit_image(unit, scaled_size)

                # 4. Centrer et afficher
                img_rect = scaled_img.get_rect(center=(screen_x, screen_y))

                # Pas de numéro ici, gestion de l'opacité
                opacity = unit.get_opacity()  # Retourne 1.0 ou 0.5
                alpha = int(255 * opacity)
                scaled_img.set_alpha(alpha)
                screen.blit(scaled_img, img_rect)

    def render_cities(self, screen, game_state, cam, tile_size):
        """
        Dessine les noms des villes sur la carte.
        """
        for city in game_state.cities:
            # Récupérer la tuile centrale de la ville
            tile = game_state.map.tiles.get(city.center_tile_id)
            if not tile:
                continue

            # Position du centre de la tuile
            tile_center_x, tile_center_y = tile.center
            world_x = tile_center_x * tile_size
            world_y = tile_center_y * tile_size

            # Convertir en coordonnées écran
            screen_x, screen_y = world_to_screen(world_x, world_y, cam.x, cam.y, cam.zoom)
            screen_x = int(screen_x)
            screen_y = int(screen_y)

            # Afficher le nom de la ville si le zoom est suffisant
            if cam.zoom > 0.6:
                city_name_sf = self.font.render(city.name, True, (255, 255, 255))
                name_rect = city_name_sf.get_rect(center=(screen_x, screen_y))

                # Fond semi-transparent pour le texte
                bg_rect = name_rect.inflate(6, 4)
                bg_sf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
                bg_sf.fill((0, 0, 0, 200))
                screen.blit(bg_sf, bg_rect)
                screen.blit(city_name_sf, name_rect)

    def render(self, screen, game_state, cam, tile_size, hovered_tile, dt):
        self.render_world(screen, game_state.map, game_state, cam, tile_size)
        self.render_overlay(screen, game_state.map, cam, tile_size, hovered_tile)
        self.render_units(screen, game_state.map, cam, tile_size)
        self.render_cities(screen, game_state, cam, tile_size)
        # self.render_ui(screen, game_state.map, hovered_tile, dt)

    def render_world(self, screen, game_map, game_state, cam, tile_size):
        if self.map_sf is None or self.map_dirty:
            self.map_sf = self.build_map_sf(game_state, game_map, tile_size)
            self.map_dirty = False

        if self.resource_sf is None or self.resource_dirty:
            self.resource_sf = self.build_resource_sf(game_state, game_map, tile_size)
            self.resource_dirty = False

        if self.border_sf is None or self.border_dirty:
            self.border_sf = self.build_border_sf(game_map, tile_size)
            self.border_dirty = False

        # Construire les surfaces de villes si nécessaire
        if self.city_overlay_sf is None or self.city_dirty:
            self.city_overlay_sf = self.build_city_overlay_sf(game_map, game_state, tile_size)
            self.city_border_sf = self.build_city_border_sf(game_map, game_state, tile_size)
            self.city_dirty = False

        window_w, window_h = pygame.display.get_window_size()
        view_w = window_w - gc.SIDEBAR_WIDTH
        view_h = window_h - gc.STATUS_H
        view_rect = pygame.Rect(
            int(cam.x),
            int(cam.y),
            int(view_w / cam.zoom),
            int(view_h / cam.zoom),
        )
        map_rect = self.map_sf.get_rect()

        clipped = view_rect.clip(map_rect)
        if clipped.width <= 0 or clipped.height <= 0:
            return

        offset_x = (clipped.x - view_rect.x) * cam.zoom + gc.SIDEBAR_WIDTH
        offset_y = (clipped.y - view_rect.y) * cam.zoom

        sub = self.map_sf.subsurface(clipped)
        cache_key = (round(cam.zoom, 3), clipped.topleft, clipped.size)
        target_size = (int(clipped.width * cam.zoom), int(clipped.height * cam.zoom))
        if cache_key not in self._scaled_cache:
            self._scaled_cache[cache_key] = pygame.transform.scale(sub, target_size)
        scaled = self._scaled_cache[cache_key]
        screen.blit(scaled, (offset_x, offset_y))

        # Rendu des ressources (pré-render)
        scale = gc.RESOURCE_BASE_SCALE

        # convertir le clipped en coordonnées haute résolution
        clipped_scaled = pygame.Rect(
            clipped.x * scale,
            clipped.y * scale,
            clipped.width * scale,
            clipped.height * scale,
        )
        sub_res = self.resource_sf.subsurface(clipped_scaled)
        scaled_res = pygame.transform.scale(
            sub_res,
            (
                int(clipped.width * cam.zoom),
                int(clipped.height * cam.zoom),
            ),
        )
        screen.blit(scaled_res, (offset_x, offset_y))

        # Dessiner la teinte des villes
        if self.city_overlay_sf:
            sub_city = self.city_overlay_sf.subsurface(clipped)
            scaled_city = pygame.transform.scale(
                sub_city,
                (
                    int(clipped.width * cam.zoom),
                    int(clipped.height * cam.zoom),
                ),
            )
            screen.blit(scaled_city, (offset_x, offset_y))

        self.last_view_rect = view_rect
        self.last_clipped = clipped
        self.last_offset = (offset_x, offset_y)

        # Dessiner les bordures de tuiles normales
        if cam.zoom > 1.2:
            sub_b = self.border_sf.subsurface(clipped)
            scaled_b = pygame.transform.scale(
                sub_b,
                (
                    int(clipped.width * cam.zoom),
                    int(clipped.height * cam.zoom),
                ),
            )
            screen.blit(scaled_b, (offset_x, offset_y))

        # Dessiner les bordures de villes (toujours visibles)
        if self.city_border_sf:
            sub_city_border = self.city_border_sf.subsurface(clipped)
            scaled_city_border = pygame.transform.scale(
                sub_city_border,
                (
                    int(clipped.width * cam.zoom),
                    int(clipped.height * cam.zoom),
                ),
            )
            screen.blit(scaled_city_border, (offset_x, offset_y))

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

    def render_reachable_tiles(self, screen, game_map, cam, tile_size, reachable_tile_ids):
        """Affiche un overlay bleu transparent sur les tuiles accessibles (mouvement)."""
        if not reachable_tile_ids:
            return

        view_rect = self.last_view_rect
        offset_x, offset_y = self.last_offset

        # Créer UNE surface overlay
        if self._overlay_sf is None or self._overlay_sf.get_size() != screen.get_size():
            self._overlay_sf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        self._overlay_sf.fill((0, 0, 0, 0))

        for tile_id in reachable_tile_ids:
            tile = game_map.tiles[tile_id]

            # Pour CHAQUE cellule de la tuile
            for cell_x, cell_y in tile.cells:
                # Convertir en coordonnées monde
                world_x = cell_x * tile_size
                world_y = cell_y * tile_size

                # Convertir en coordonnées écran
                rel_x = world_x - view_rect.x
                rel_y = world_y - view_rect.y
                screen_x = rel_x * cam.zoom + offset_x
                screen_y = rel_y * cam.zoom + offset_y

                # Taille du rectangle
                rect_width = int(tile_size * cam.zoom)
                rect_height = int(tile_size * cam.zoom)

                # Dessiner LE RECTANGLE BLEU directement
                pygame.draw.rect(
                    self._overlay_sf,
                    (100, 150, 255, 80),
                    (int(screen_x), int(screen_y), rect_width, rect_height),
                )

        # Blitter l'overlay sur l'écran UNE SEULE FOIS
        screen.blit(self._overlay_sf, (0, 0))

    def render_attackable_tiles(self, screen, game_map, cam, tile_size, attackable_tile_ids):
        """Affiche un overlay rouge transparent sur les tuiles attaquables (combat avec unités ennemies)."""
        if not attackable_tile_ids:
            return

        view_rect = self.last_view_rect
        offset_x, offset_y = self.last_offset

        # Créer UNE surface overlay
        overlay_sf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

        for tile_id in attackable_tile_ids:
            tile = game_map.tiles[tile_id]

            # Pour CHAQUE cellule de la tuile
            for cell_x, cell_y in tile.cells:
                # Convertir en coordonnées monde
                world_x = cell_x * tile_size
                world_y = cell_y * tile_size

                # Convertir en coordonnées écran
                rel_x = world_x - view_rect.x
                rel_y = world_y - view_rect.y
                screen_x = rel_x * cam.zoom + offset_x
                screen_y = rel_y * cam.zoom + offset_y

                # Taille du rectangle
                rect_width = int(tile_size * cam.zoom)
                rect_height = int(tile_size * cam.zoom)

                # Dessiner LE RECTANGLE ROUGE directement (avec même opacité que le bleu)
                pygame.draw.rect(
                    overlay_sf,
                    (255, 100, 100, 80),  # RGBA: Rouge avec opacité 80
                    (int(screen_x), int(screen_y), rect_width, rect_height),
                )

        # Blitter l'overlay sur l'écran UNE SEULE FOIS
        screen.blit(overlay_sf, (0, 0))

    def render_ui(self, screen, game_map, hovered_tile: Tile, dt):
        if hovered_tile:
            text_info = self.font.render(
                f"Tile {hovered_tile.id:>5} | {hovered_tile.biome.name:>8} | {hovered_tile.resource.name:>7}| {hovered_tile.area}",
                True,
                (255, 255, 255),
            )
            screen.blit(text_info, (gc.SIDEBAR_WIDTH + 10, 70))

        self.fps = (self.fps * 0.85) + (1 / dt * (1 - 0.85))
        text_FPS = self.font.render(
            f"FPS : {self.fps:.1f} | seed {game_map.seed}",
            True,
            (255, 255, 255),
        )
        screen.blit(text_FPS, (gc.SIDEBAR_WIDTH + 10, 90))
