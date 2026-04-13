import random
import pygame
from pathlib import Path


from config import GameConfig as gc
from core.game_state import GameState
from world.map import Map
from world.clock import TurnManager
from ui.camera import Camera, world_to_screen
from ui.renderer import RenderPipeline
from ui.ui_manager import UIManager
from ui.ui_utils import get_hovered_tile, compute_tile_size
from ui.button import Button
from world.unit import Unit, UnitType
from world.biome import Biome
from world.selector import UnitSelector
from world.movement import get_reachable_tiles


pygame.init()

font = pygame.font.SysFont(None, 20)
button_font = pygame.font.SysFont(None, 18)

img_path = Path(".") / "img"


# -------------------------
# 🚀 MAIN
# -------------------------
def main():
    screen = pygame.display.set_mode((gc.SCREEN_WIDTH, gc.SCREEN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("4X Map Generator, en fait c'est un début de jeu mais voila quoi")

    icone = pygame.image.load(img_path / "Logo.png")
    pygame.display.set_icon(icone)

    clock = pygame.time.Clock()

    seed = random.randint(0, 1000)
    gs = GameState(gc.WIDTH, gc.HEIGHT, seed, log=gc.LOG_MAP_GENERATION, tile_size=gc.TILE_SIZE)

    camera = Camera()
    renderer = RenderPipeline(font, gc.BIOME_COLORS)

    ui_manager = UIManager(button_font)

    unit_selector = UnitSelector()

    # Type d'unité à placer par défaut
    selected_unit_type = UnitType.SOLDIER
    selected_unit_water_affinity = False

    running = True
    turn_manager = TurnManager()

    game_map = gs.map

    while running:
        dt = clock.tick(gc.FPS) / 1000
        window_w, window_h = screen.get_size()
        tile_size = compute_tile_size(window_w, window_h)

        # -------- INPUT --------

        for event in pygame.event.get():

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    print(" --- Regenerating map --- ")
                    renderer.map_dirty = True
                    renderer.border_dirty = True
                    seed = random.randint(0, 1000)
                    gs = GameState(
                        gc.WIDTH, gc.HEIGHT, seed, log=gc.LOG_MAP_GENERATION, tile_size=gc.TILE_SIZE
                    )
                    game_map = gs.map
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
                    selected_unit_type = UnitType.COLON
                    selected_unit_water_affinity = True
                    print("Type sélectionné : COLON")
                if event.key == pygame.K_ESCAPE:
                    unit_selector.deselect_unit()
                    print("Unité désélectionnée")

            if event.type == pygame.MOUSEWHEEL:
                camera.apply_zoom(pygame.mouse.get_pos(), event.y)

            # ICI: Gestion unifiée des clics
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Clic gauche
                    mouse_pos = pygame.mouse.get_pos()

                    # Vérifier les boutons UI
                    action = ui_manager.handle_click(
                        mouse_pos, gs.map, selected_unit_type, selected_unit_water_affinity
                    )

                    # Gérer l'action retournée
                    if action == "next_turn":
                        turn_manager.next_turn(game_map)
                    elif action == "quit":
                        running = False

                    # Ici gestion du mouvement des unités
                    elif not unit_selector.is_unit_selected():
                        # Si aucune unité sélectionnée, chercher une unité cliquée
                        hovered_tile = get_hovered_tile(game_map, camera, tile_size)

                        if hovered_tile and hovered_tile.has_units():
                            unit = hovered_tile.units[0]

                            # Sélectionner l'unité si elle peut bouger
                            if unit.can_move():
                                unit_selector.select_unit(unit, game_map)
                                print(
                                    f"✅ Unité {unit.id} sélectionnée - Distance max: {unit.max_distance}"
                                )
                            else:
                                print(f"❌ Unité {unit.id} a déjà bougé ce tour !")

                    else:
                        # Une unité est sélectionnée, essayer de la déplacer
                        hovered_tile = get_hovered_tile(game_map, camera, tile_size)

                        if hovered_tile:
                            # Vérifier si on clique sur la même tuile (désélection)
                            if hovered_tile.id == unit_selector.selected_unit.tile_id:
                                unit_selector.deselect_unit()
                                print("Unité désélectionnée")
                            else:
                                # Essayer de déplacer l'unité
                                if unit_selector.try_move(game_map, hovered_tile.id):
                                    print(f"✅ Unité déplacée vers tuile {hovered_tile.id}")
                                else:
                                    print(f"❌ Déplacement impossible vers tuile {hovered_tile.id}")

                    # ✨ NOUVEAU : Si en mode placement, placer une unité
                    if (
                        ui_manager.placement_button.is_active
                        and not unit_selector.is_unit_selected()
                    ):
                        hovered_tile = get_hovered_tile(game_map, camera, tile_size)
                        turn_manager.next_turn(gs.map)

                    # Si en mode placement, essayer de placer une unité
                    elif ui_manager.placement_button.is_active:
                        hovered_tile = get_hovered_tile(gs.map, camera, tile_size)
                        if hovered_tile:
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
                                unit = Unit(
                                    tile_id=hovered_tile.id,
                                    unit_type=selected_unit_type,
                                    owner=0,
                                    water_affinity=selected_unit_water_affinity,
                                )
                                hovered_tile.add_unit(unit)
                                print(f"✅ Unité placée sur tuile {hovered_tile.id} : {unit}")

        # -------- UPDATE --------
        camera.update(dt, gs.map, tile_size, window_w, window_h)
        hovered_tile = get_hovered_tile(gs.map, camera, tile_size)

        # Mettre à jour les positions des boutons en fonction de la taille de l'écran
        ui_manager.update_positions(window_w, window_h)

        # Mettre à jour tous les boutons et la sidebar
        mouse_pos = pygame.mouse.get_pos()
        ui_manager.update(mouse_pos, dt)

        # -------- RENDER --------
        screen.fill((0, 0, 0))
        renderer.render(screen, gs.map, camera, tile_size, hovered_tile, dt)

        # Une seule ligne pour dessiner tous les boutons
        ui_manager.draw(screen)

        if unit_selector.is_unit_selected():
            # Afficher les zones accessibles en bleu transparent
            reachable = unit_selector.get_reachable_tiles()
            for tile_id in reachable:
                tile = game_map.tiles[tile_id]
                tile_x, tile_y = tile.center
                world_x = tile_x * tile_size
                world_y = tile_y * tile_size
                screen_x, screen_y = world_to_screen(
                    world_x, world_y, camera.x, camera.y, camera.zoom
                )

                # Dessiner un petit overlay bleu
                pygame.draw.circle(
                    screen,
                    (100, 150, 255, 100),
                    (int(screen_x), int(screen_y)),
                    int(3 * camera.zoom),
                    1,
                )

        # Afficher le type d'unité sélectionné (positionné en bas à droite)
        unit_type_text = button_font.render(
            f"Type: {selected_unit_type.name} (1-4)",
            True,
            (200, 200, 200),
        )
        text_rect = unit_type_text.get_rect()
        text_rect.bottomright = (window_w - 10, window_h - 10)
        screen.blit(unit_type_text, text_rect)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
