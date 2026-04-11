import random
import pygame

from config import GameConfig as gc
from world.map import Map
from world.biome import Biome
from world.unit import Unit, UnitType, UnitPlacementButton  # NOUVEAU : imports pour les unités
from world.clock import TurnManager
from ui.camera import Camera, world_to_screen, screen_to_world
from ui.renderer import RenderPipeline



pygame.init()

font = pygame.font.SysFont(None, 20)
button_font = pygame.font.SysFont(None, 18)  #police pour le bouton

# -------------------------
# 🧰 UTILS
# -------------------------
def lighten(color, amount=40):
    return tuple(min(255, c + amount) for c in color)


def compute_tile_size(window_w, window_h):
    return min(window_w // gc.WIDTH, window_h // gc.HEIGHT)


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


# -------------------------
# 🚀 MAIN
# -------------------------
def main():
    screen = pygame.display.set_mode((gc.SCREEN_WIDTH, gc.SCREEN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("4X Map Generator")

    clock = pygame.time.Clock()

    seed = random.randint(0, 1000)
    game_map = Map(gc.WIDTH, gc.HEIGHT, seed, log=gc.LOG_MAP_GENERATION)

    camera = Camera()
    renderer = RenderPipeline(font, gc.BIOME_COLORS)

    # NOUVEAU : Créer le bouton de placement
    placement_button = UnitPlacementButton(
        gc.BUTTON_X, gc.BUTTON_Y, gc.BUTTON_WIDTH, gc.BUTTON_HEIGHT
    )

    # NOUVEAU : Type d'unité à placer par défaut
    selected_unit_type = UnitType.SOLDIER
    selected_unit_water_affinity = False

    running = True

    turn_manager = TurnManager()

    #bouton pour le tour suivant
    next_turn_rect = pygame.Rect(gc.SCREEN_WIDTH - 160, 10, 150, 40)
    while running:
        dt = clock.tick(gc.FPS) / 1000
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
                    game_map = Map(gc.WIDTH, gc.HEIGHT, seed, log=gc.LOG_MAP_GENERATION)
                    renderer.clear_cache()  # vider le cache du renderer pour forcer un recalcul total

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
                            print(f"2. Tuile survolée trouvée : {hovered_tile.id}")
                            if hovered_tile.has_units():
                                print(f"❌La tuile {hovered_tile.id} a déjà une unité !")
                            elif (hovered_tile.biome == Biome.WATER
                                and not selected_unit_water_affinity):
                                print(f"❌La tuile {hovered_tile.id} est pleine de flotte l'unité va se noyer!")
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

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Clic gauche
                    mouse_pos = pygame.mouse.get_pos()
                    
                    # Si on clique DANS le rectangle du bouton "Tour Suivant"
                    if next_turn_rect.collidepoint(mouse_pos):
                        turn_manager.next_turn(game_map)

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
        unit_type_text = button_font.render(f"Type d'unité sélectionnée: {selected_unit_type.name} (1-4 pour changer)", True, (200, 200, 200))
        screen.blit(unit_type_text, (gc.BUTTON_X, gc.BUTTON_Y + gc.BUTTON_HEIGHT + 10))

        #bouton tour suivant crazzyyyyyyyy
        pygame.draw.rect(screen, (60, 60, 60), next_turn_rect)
        pygame.draw.rect(screen, (255, 255, 255), next_turn_rect, 2)
        ui_font = pygame.font.SysFont(None, 24)
        turn_text = ui_font.render(f"Fin du tour {turn_manager.current_turn}", True, (255, 255, 255))
        text_rect = turn_text.get_rect(center=next_turn_rect.center)
        screen.blit(turn_text, text_rect)



        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
