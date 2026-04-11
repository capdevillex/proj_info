import random
import pygame

from world.map import Map
from world.biome import Biome
from world.unit import Unit, UnitType  # NOUVEAU : imports pour les unités
from ui.camera import Camera, world_to_screen, screen_to_world
from ui.renderer import RenderPipeline

# -------------------------
# 🎨 CONFIG
# -------------------------
TILE_SIZE = 2  # Divisé par 2 pour passer de 2132px à 1066px de large
HEIGHT = 300
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

# NOUVEAU : Configuration du bouton
BUTTON_WIDTH = 150
BUTTON_HEIGHT = 40
BUTTON_X = 10
BUTTON_Y = 50
BUTTON_COLOR = (100, 100, 200)
BUTTON_HOVER_COLOR = (150, 150, 255)
BUTTON_ACTIVE_COLOR = (255, 100, 100)

pygame.init()
font = pygame.font.SysFont(None, 20)
button_font = pygame.font.SysFont(None, 18)  # NOUVEAU : police pour le bouton


# -------------------------
# 🧰 UTILS
# -------------------------
def lighten(color, amount=40):
    return tuple(min(255, c + amount) for c in color)


def compute_tile_size(window_w, window_h):
    return min(window_w // WIDTH, window_h // HEIGHT)


def draw_centers(screen, game_map, tile_size, cam):
    for tile in game_map.tiles.values():
        x, y = tile.center
        wx = x * tile_size
        wy = y * tile_size
        sx, sy = world_to_screen(wx, wy, cam.x, cam.y, cam.zoom)

        pygame.draw.circle(screen, (255, 255, 255), (sx, sy), 3)

        text = font.render(f"{tile.area}:{tile.id}", True, (255, 255, 255))
        screen.blit(text, (sx - 10, sy - 15))


def get_hovered_tile(game_map, cam, tile_size):
    mouse_x, mouse_y = pygame.mouse.get_pos()

    world_x, world_y = screen_to_world(mouse_x, mouse_y, cam.x, cam.y, cam.zoom)

    grid_x = int(world_x // tile_size)
    grid_y = int(world_y // tile_size)

    if 0 <= grid_x < game_map.width and 0 <= grid_y < game_map.height:
        tile_id = game_map.grid[grid_y][grid_x]
        return game_map.tiles.get(tile_id)

    return None


# NOUVEAU : Classe pour le bouton de placement d'unités
class UnitPlacementButton:
    """
    Bouton UI pour activer/désactiver le mode placement d'unités.

    Le bouton affiche :
    - "Place Unit" en bleu normal quand le mode est désactivé
    - "Place Unit (ON)" en rouge quand le mode est activé
    """

    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.is_active = False
        self.is_hovered = False

    def update(self, mouse_pos):
        """Met à jour l'état du bouton (survol)"""
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, mouse_pos):
        """Retourne True si le bouton est cliqué"""
        return self.rect.collidepoint(mouse_pos)

    def toggle(self):
        """Active/désactive le mode placement"""
        self.is_active = not self.is_active

    def draw(self, screen):
        """Dessine le bouton à l'écran"""
        # Couleur du bouton selon l'état
        if self.is_active:
            color = BUTTON_ACTIVE_COLOR  # Rouge si actif
        elif self.is_hovered:
            color = BUTTON_HOVER_COLOR  # Bleu clair si survolé
        else:
            color = BUTTON_COLOR  # Bleu normal

        # Dessiner le rectangle du bouton
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (200, 200, 200), self.rect, 2)  # Bordure

        # Texte du bouton
        text_str = "Placer Unité (ON)" if self.is_active else "Placer Unité (OFF)"
        text_surface = button_font.render(text_str, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)


# -------------------------
# 🚀 MAIN
# -------------------------
def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("4X Map Generator")

    clock = pygame.time.Clock()

    seed = random.randint(0, 1000)
    game_map = Map(WIDTH, HEIGHT, seed, log=LOG_MAP_GENERATION)

    camera = Camera()
    renderer = RenderPipeline(font, BIOME_COLORS)

    # NOUVEAU : Créer le bouton de placement
    placement_button = UnitPlacementButton(BUTTON_X, BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT)

    # NOUVEAU : Type d'unité à placer par défaut
    selected_unit_type = UnitType.SOLDIER
    selected_unit_water_affinity = False

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
                    game_map = Map(WIDTH, HEIGHT, seed, log=LOG_MAP_GENERATION)

                if event.key == pygame.K_c:
                    renderer.show_centers = not renderer.show_centers

                # NOUVEAU : Touches pour changer le type d'unité avec clavier et numpad
                if event.key in (pygame.K_1, pygame.K_KP1):
                    selected_unit_type = UnitType.SOLDIER
                    selected_unit_water_affinity = False
                    print("Type sélectionné : SOLDAT")
                if event.key in (pygame.K_2, pygame.K_KP2):
                    selected_unit_type = UnitType.CAVALRY
                    selected_unit_water_affinity = False
                    print("Type sélectionné : CAVALIER")
                if event.key in (pygame.K_3, pygame.K_KP3):
                    selected_unit_type = UnitType.ARCHER
                    selected_unit_water_affinity = False
                    print("Type sélectionné : ARCHER")
                if event.key in (pygame.K_4, pygame.K_KP4):
                    selected_unit_type = UnitType.SETTLEMENT
                    selected_unit_water_affinity = True
                    print("Type sélectionné : COLON")

            if event.type == pygame.MOUSEWHEEL:
                camera.apply_zoom(pygame.mouse.get_pos(), event.y)

            # NOUVEAU : Détection du clic sur le bouton
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Clic gauche
                    mouse_pos = pygame.mouse.get_pos()

                    # Vérifier si le bouton est cliqué
                    if placement_button.is_clicked(mouse_pos):
                        placement_button.toggle()
                        status = "ACTIVÉ" if placement_button.is_active else "DÉSACTIVÉ"
                        print(f"Mode placement {status}")

                    # NOUVEAU : Si en mode placement et clic sur une tuile
                    elif placement_button.is_active:
                        hovered_tile = get_hovered_tile(game_map, camera, tile_size)
                        if hovered_tile:
                            # MODIFIÉ : Vérifier qu'il n'y a pas déjà une unité
                            if hovered_tile.has_units():
                                print(f"❌La tuile {hovered_tile.id} a déjà une unité !")
                            elif (
                                hovered_tile.biome == Biome.WATER
                                and not selected_unit_water_affinity
                            ):
                                print(
                                    f"❌La tuile {hovered_tile.id} est pleine de flotte l'unité va se noyer!"
                                )
                            else:
                                # Créer et ajouter une unité
                                unit = Unit(
                                    tile_id=hovered_tile.id,
                                    unit_type=selected_unit_type,
                                    owner=0,
                                    water_affinity=selected_unit_water_affinity,
                                )

                                hovered_tile.add_unit(unit)
                                print(f"✅ Unité placée sur tuile {hovered_tile.id} : {unit}")

        # -------- UPDATE --------
        camera.update(dt, game_map, tile_size, window_w, window_h)
        hovered_tile = get_hovered_tile(game_map, camera, tile_size)

        # NOUVEAU : Mettre à jour l'état du bouton (survol)
        mouse_pos = pygame.mouse.get_pos()
        placement_button.update(mouse_pos)

        # -------- RENDER --------
        screen.fill((0, 0, 0))
        renderer.render(screen, game_map, camera, tile_size, hovered_tile, dt)

        # NOUVEAU : Dessiner le bouton
        placement_button.draw(screen)

        # NOUVEAU : Afficher le type d'unité sélectionné
        unit_type_text = button_font.render(
            f"Type: {selected_unit_type.name} (1-4 pour changer)", True, (200, 200, 200)
        )
        screen.blit(unit_type_text, (BUTTON_X, BUTTON_Y + BUTTON_HEIGHT + 10))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
