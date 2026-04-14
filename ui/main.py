import random
import pygame
from pathlib import Path

from config import GameConfig as gc
from core.game_state import GameState
from core.game_engine import GameEngine
from world.clock import TurnManager
from ui.camera import Camera, world_to_screen
from ui.renderer import RenderPipeline
from ui.ui_manager import UIManager
from ui.ui_utils import get_hovered_tile, compute_tile_size
from world.unit import Unit, UnitType
from world.biome import Biome
from world.selector import UnitSelector
from core.systems.movement import Movement

pygame.init()

font = pygame.font.SysFont("consolas,monospace", 15)
button_font = pygame.font.SysFont("consolas,monospace", 15)

img_path = Path(".") / "img"


def main():
    screen = pygame.display.set_mode((gc.SCREEN_WIDTH, gc.SCREEN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Novum Imperium(4X Prototype)")

    try:
        icone = pygame.image.load(img_path / "Logo.png")
        pygame.display.set_icon(icone)
    except Exception:
        pass

    clock = pygame.time.Clock()

    seed = random.randint(0, 1000)
    gs = GameState(gc.WIDTH, gc.HEIGHT, seed, tile_area=gc.TILE_AVG_AREA, log=gc.LOG_MAP_GENERATION)

    game_engine = GameEngine(gs)
    camera = Camera()
    renderer = RenderPipeline(font, gc.BIOME_COLORS)
    ui_manager = UIManager(game_engine, button_font)
    unit_selector = UnitSelector()

    # Type d'unité à placer par défaut
    selected_unit_type = UnitType.SOLDIER
    selected_unit_water_affinity = False
    selected_enn_unit_type = UnitType.BABY
    selected_enn_unit_water_affinity = False

    running = True
    turn_manager = TurnManager()
    game_map = gs.map

    fps_smooth = 60.0

    while running:
        dt = clock.tick(gc.FPS) / 1000.0
        dt = min(dt, 0.05)  # cap pour éviter les sauts d'animation

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
                    gs = GameState(
                        gc.WIDTH,
                        gc.HEIGHT,
                        seed,
                        log=gc.LOG_MAP_GENERATION,
                        tile_area=gc.TILE_AVG_AREA,
                    )
                    game_map = gs.map
                    game_engine = GameEngine(gs)
                    ui_manager.game_engine = game_engine
                    renderer.clear_cache()

                if event.key == pygame.K_c:
                    renderer.show_centers = not renderer.show_centers

                if event.key in (pygame.K_1, pygame.K_KP1):
                    selected_unit_type = UnitType.SOLDIER
                    selected_unit_water_affinity = False
                if event.key in (pygame.K_2, pygame.K_KP2):
                    selected_unit_type = UnitType.CAVALRY
                    selected_unit_water_affinity = False
                if event.key in (pygame.K_3, pygame.K_KP3):
                    selected_unit_type = UnitType.ARCHER
                    selected_unit_water_affinity = False
                if event.key in (pygame.K_4, pygame.K_KP4):
                    selected_unit_type = UnitType.COLON
                    selected_unit_water_affinity = True
                if event.key == pygame.K_ESCAPE:
                    unit_selector.deselect_unit()

            if event.type == pygame.MOUSEWHEEL:
                camera.apply_zoom(pygame.mouse.get_pos(), event.y)

            # --- GESTION DES CLICS ---
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Clic gauche
                    mouse_pos = event.pos

                    # 1. Vérifier si on touche l'un des boutons de l'UI
                    action = ui_manager.handle_click(
                        mouse_pos, gs.map, selected_unit_type, selected_unit_water_affinity
                    )

                    clic_sur_ui = action is not None or ui_manager.is_mouse_over_ui(mouse_pos)

                    if clic_sur_ui:
                        if action == "next_turn":
                            game_engine.end_turn()
                            unit_selector.deselect_unit()
                        elif action == "quit":
                            running = False
                        # On arrête le traitement ici pour ne pas cliquer "à travers" le bouton
                        continue

                    hovered_tile = get_hovered_tile(game_map, camera, tile_size)

                    if hovered_tile:
                        if ui_manager.placement_button.is_active:
                            game_engine.spawn_unit(
                                unit_type=selected_unit_type,
                                tile_id=hovered_tile.id,
                                owner=gs.current_player,
                                water_affinity=selected_unit_water_affinity,
                            )
                        elif ui_manager.placement_button_enn.is_active:
                            game_engine.spawn_unit(
                                unit_type=selected_enn_unit_type,
                                tile_id=hovered_tile.id,
                                owner=1,
                                water_affinity=selected_enn_unit_water_affinity,
                            )

                        # Priorité B : Sélection d'unité
                        elif not unit_selector.is_unit_selected():
                            if hovered_tile.has_units():
                                unit = hovered_tile.units[0]
                                if unit.can_move():
                                    unit_selector.select_unit(unit, game_map)

                        # Priorité C : Mouvement ou attaque d'unité déjà sélectionnée
                        else:
                            # Vérifier si c'est la tuile de l'unité sélectionnée (désélectionner)
                            if hovered_tile.id == unit_selector.selected_unit.tile_id:
                                unit_selector.deselect_unit()
                            # Vérifier si on attaque une unité ennemie (tuile rouge)
                            elif unit_selector.is_tile_attackable(hovered_tile.id):
                                if game_engine.attack_unit(
                                    unit_selector.selected_unit, hovered_tile.id
                                ):
                                    # Attaque réussie, désélectionner
                                    unit_selector.deselect_unit()
                                else:
                                    # Attaque échouée mais pas grave, on laisse sélectionné
                                    pass
                            # Sinon, essayer de se déplacer (tuile bleue)
                            else:
                                if game_engine.move_unit(
                                    unit_selector.selected_unit, hovered_tile.id
                                ):
                                    unit_selector.deselect_unit()

                elif event.button == 3:  # Clic droit
                    mouse_pos = event.pos
                    hovered_tile = get_hovered_tile(game_map, camera, tile_size)

                    if hovered_tile and hovered_tile.has_units():
                        # Récupérer l'unité sur la tuile
                        unit = hovered_tile.units[0]

                        # Si c'est un colon, fonder une ville
                        if unit.unit_type == UnitType.COLON and unit.owner == gs.current_player:
                            if game_engine.found_city(unit):
                                # Désélectionner l'unité si elle était sélectionnée
                                if (
                                    unit_selector.is_unit_selected()
                                    and unit_selector.selected_unit.id == unit.id
                                ):
                                    unit_selector.deselect_unit()
                                # Marquer le rendu comme sale pour rafraîchir l'affichage
                                renderer.city_dirty = True

        # -------- UPDATE --------
        camera.update(dt, gs.map, tile_size, window_w, window_h)
        hovered_tile = get_hovered_tile(gs.map, camera, tile_size)
        ui_manager.update_positions(window_w, window_h)

        mouse_pos = pygame.mouse.get_pos()
        ui_manager.update(mouse_pos, dt)

        # Transmettre l'état courant à l'UIManager
        ui_manager.hovered_tile = hovered_tile
        fps_smooth = fps_smooth * 0.9 + (1.0 / max(dt, 0.001)) * 0.1
        ui_manager.fps_value = fps_smooth

        # RENDER
        screen.fill((6, 8, 14))
        renderer.render(screen, gs, camera, tile_size, hovered_tile, dt)

        ui_manager.draw(screen, selected_unit_type)

        # Afficher les zones de mouvement et de combat pour l'unité sélectionnée
        if unit_selector.is_unit_selected():
            reachable = unit_selector.get_reachable_tiles()
            attackable = unit_selector.get_attackable_tiles()

            # Afficher les tuiles attaquables en ROUGE (avant les tuiles accessibles pour la visibilité)
            renderer.render_attackable_tiles(screen, game_map, camera, tile_size, attackable)

            # Afficher les tuiles accessibles en BLEU
            renderer.render_reachable_tiles(screen, game_map, camera, tile_size, reachable)

        ui_manager.draw(screen, selected_unit_type)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
