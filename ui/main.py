import random
import pygame

from config import GameConfig as gc
from world.map import Map
from world.clock import TurnManager
from ui.camera import Camera
from ui.renderer import RenderPipeline
from ui.ui_manager import UIManager
from ui.ui_utils import get_hovered_tile, compute_tile_size
from ui.button import Button
from world.unit import Unit, UnitType
from world.biome import Biome 


pygame.init()

font = pygame.font.SysFont(None, 20)
button_font = pygame.font.SysFont(None, 18)



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

    # ✨ NOUVEAU : Utiliser UIManager au lieu de créer les boutons manuellement
    ui_manager = UIManager(button_font)

    # Type d'unité à placer par défaut
    selected_unit_type = UnitType.SOLDIER
    selected_unit_water_affinity = False

    running = True
    turn_manager = TurnManager()

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
                    renderer.clear_cache()

                if event.key == pygame.K_c:
                    renderer.show_centers = not renderer.show_centers

                # Touches pour changer le type d'unité
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

            # ✨ NOUVEAU : Gestion unifiée des clics
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Clic gauche
                    mouse_pos = pygame.mouse.get_pos()

                    # Vérifier les boutons
                    action = ui_manager.handle_click(
                        mouse_pos, game_map,
                        selected_unit_type, selected_unit_water_affinity
                    )

                    # Gérer l'action retournée
                    if action == "next_turn":
                        turn_manager.next_turn(game_map)
                    
                    # Si en mode placement, essayer de placer une unité
                    elif ui_manager.placement_button.is_active:
                        hovered_tile = get_hovered_tile(game_map, camera, tile_size)
                        if hovered_tile:
                            if hovered_tile.has_units():
                                print(f"❌La tuile {hovered_tile.id} a déjà une unité !")
                            elif (hovered_tile.biome == Biome.WATER
                                and not selected_unit_water_affinity):
                                print(f"❌La tuile {hovered_tile.id} est pleine de flotte l'unité va se noyer!")
                            else:
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

        # ✨ NOUVEAU : Une seule ligne pour mettre à jour tous les boutons
        mouse_pos = pygame.mouse.get_pos()
        ui_manager.update(mouse_pos)

        # -------- RENDER --------
        screen.fill((0, 0, 0))
        renderer.render(screen, game_map, camera, tile_size, hovered_tile, dt)

        # ✨ NOUVEAU : Une seule ligne pour dessiner tous les boutons
        ui_manager.draw(screen)

        # Afficher le type d'unité sélectionné
        unit_type_text = button_font.render(
            f"Type d'unité sélectionnée: {selected_unit_type.name} (1-4 pour changer)",
            True,
            (200, 200, 200)
        )
        screen.blit(unit_type_text, (gc.BUTTON_X, gc.BUTTON_Y + gc.BUTTON_HEIGHT + 10))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
