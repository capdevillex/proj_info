import random
import pygame

from pathlib import Path

from config import GameConfig as gc
from core.game_state import GameState
from core.game_engine import GameEngine
from ui.camera import Camera
from ui.renderer import RenderPipeline
from ui.ui_manager import UIManager
from ui.ui_utils import get_hovered_tile, compute_tile_size
from world.unit import Unit, UnitType, UNIT_CLASS_MAP
from world.selector import UnitSelector


pygame.init()

font = pygame.font.SysFont("consolas,monospace", 15)
button_font = pygame.font.SysFont("consolas,monospace", 15)

img_path = Path(".") / "img"


def _setup_game(seed: int) -> tuple[GameState, GameEngine]:
    """Crée un GameState et un GameEngine frais avec les royaumes configurés.

    C'est ici qu'on enregistre les royaumes ennemis (et leurs IA quand elles
    seront implémentées). Modifier cette fonction pour ajouter / retirer des IA.
    """
    gs = GameState(gc.WIDTH, gc.HEIGHT, seed, tile_area=gc.TILE_AVG_AREA, log=gc.LOG_MAP_GENERATION)

    # Royaumes ennemis
    # Décommenter et dupliquer pour ajouter des royaumes supplémentaires.
    # Les paramètres ai_params calibreront l'arbre de décision pondéré.
    # Ne pas oublier d'ajouter : from world.kingdom import Kingdom
    #
    # Exemple royaume agressif :
    # gs.add_kingdom(Kingdom(
    #     kingdom_id=1, name="Barbares", color=(190, 70, 60), is_ai=True,
    #     ai_params={"aggression": 0.8, "exploration": 0.5, "expansion": 0.3, "defense": 0.2},
    # ))
    #
    # Exemple royaume expansionniste :
    # gs.add_kingdom(Kingdom(
    #     kingdom_id=2, name="Marchands", color=(60, 170, 90), is_ai=True,
    #     ai_params={"aggression": 0.2, "exploration": 0.7, "expansion": 0.9, "defense": 0.5},
    # ))

    engine = GameEngine(gs)

    # Enregistrement des contrôleurs IA (quand implémentés)
    # from core.ai.my_ai import MyAI
    # engine.register_ai(MyAI(kingdom_id=1, params=gs.get_kingdom(1).ai_params))

    engine.setup_start_units()
    return gs, engine


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
    gs, game_engine = _setup_game(seed)

    camera = Camera()
    renderer = RenderPipeline(font, gc.BIOME_COLORS)
    ui_manager = UIManager(game_engine, renderer, button_font, camera)
    unit_selector = UnitSelector()

    # Type d'unité à placer par défaut
    selected_unit_type = UnitType.SOLDIER
    selected_enn_unit_type = UnitType.BABY
    running = True
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

            # Touches non-verrouillées (toujours actives)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    print(" --- Regenerating map --- ")
                    renderer.map_dirty = True
                    renderer.border_dirty = True
                    seed = random.randint(0, 1000)
                    gs, game_engine = _setup_game(seed)
                    game_map = gs.map
                    ui_manager.game_engine = game_engine
                    ui_manager.mark_dirty()
                    renderer.clear_cache()

                if event.key == pygame.K_c:
                    renderer.show_centers = not renderer.show_centers

            if event.type == pygame.MOUSEWHEEL:
                camera.apply_zoom(pygame.mouse.get_pos(), event.y)

            # Entrées joueur verrouillées pendant le tour IA
            if game_engine.input_locked:
                continue  # ignorer tous les inputs joueur pendant le tour IA

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_1, pygame.K_KP1):
                    selected_unit_type = UnitType.SOLDIER
                if event.key in (pygame.K_2, pygame.K_KP2):
                    selected_unit_type = UnitType.CAVALRY
                if event.key in (pygame.K_3, pygame.K_KP3):
                    selected_unit_type = UnitType.ARCHER
                if event.key in (pygame.K_4, pygame.K_KP4):
                    selected_unit_type = UnitType.COLON
                if event.key == pygame.K_ESCAPE:
                    unit_selector.deselect_unit()
                    ui_manager.close_construction_menu()

                if event.key == pygame.K_SPACE:
                    game_engine.end_turn()
                    unit_selector.deselect_unit()
                    ui_manager.mark_dirty()

            # --- GESTION DES CLICS ---
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Clic gauche
                    mouse_pos = event.pos

                    # 1. Vérifier si on touche l'un des boutons de l'UI
                    action = ui_manager.handle_click(mouse_pos, gs.map, selected_unit_type)

                    clic_sur_ui = action is not None or ui_manager.is_mouse_over_ui(mouse_pos)

                    if clic_sur_ui:
                        if action == "next_turn":
                            game_engine.end_turn()
                            unit_selector.deselect_unit()
                            ui_manager.mark_dirty()
                        elif action == "quit":
                            running = False
                        elif isinstance(action, tuple) and action[0] == "build":
                            _, name, tile = action
                            if game_engine.build_construction(tile, name, gs.current_player):
                                renderer.clear_cache()
                                ui_manager.mark_dirty()
                        elif isinstance(action, tuple) and action[0] == "buy_unit":
                            _, unit_type, tile, cost = action
                            if tile is not None:
                                player = gs.current_player
                                res = game_engine.state.player_resources.get(player, {})
                                if all(res.get(r, 0) >= a for r, a in cost.items()):
                                    for r, a in cost.items():
                                        res[r] -= a
                                    game_engine.spawn_unit(unit_type, tile.id, player)
                                    renderer.clear_cache()
                        elif isinstance(action, tuple) and action[0] == "buy_tile":
                            _, tile_id, city, cost = action
                            player = gs.current_player
                            res = game_engine.state.player_resources.get(player, {})
                            if all(res.get(r, 0) >= a for r, a in cost.items()):
                                for r, a in cost.items():
                                    res[r] -= a
                                city.tile_ids.add(tile_id)
                                renderer.clear_cache()
                                ui_manager.mark_dirty()
                        # On arrête le traitement ici pour ne pas cliquer "à travers" le bouton
                        continue

                    hovered_tile = get_hovered_tile(game_map, camera, tile_size)

                    if hovered_tile:

                        if ui_manager.placement_button.is_active:
                            game_engine.spawn_unit(
                                unit_type=selected_unit_type,
                                tile_id=hovered_tile.id,
                                owner=gs.current_player,
                            )
                        elif ui_manager.placement_button_enn.is_active:
                            game_engine.spawn_unit(
                                unit_type=selected_enn_unit_type,
                                tile_id=hovered_tile.id,
                                owner=1,
                            )

                        # Priorité B : Sélection d'unité
                        elif not unit_selector.is_unit_selected():
                            if hovered_tile.has_units():
                                unit = hovered_tile.units[0]
                                if unit.can_move():
                                    unit_selector.select_unit(unit, game_engine.state)

                        # Priorité C : Mouvement ou attaque d'unité déjà sélectionnée
                        else:
                            # Vérifier si c'est la tuile de l'unité sélectionnée (désélectionner)
                            if hovered_tile.id == unit_selector.selected_unit.tile_id:
                                unit_selector.deselect_unit()
                            # Vérifier si on attaque une unité ennemie (tuile rouge)
                            elif unit_selector.is_tile_attackable(hovered_tile.id):
                                atk_result = game_engine.attack_unit(
                                    unit_selector.selected_unit, hovered_tile.id
                                )
                                if atk_result["success"] and atk_result["damage"] > 0:
                                    renderer.add_damage_number(
                                        hovered_tile.id, atk_result["damage"],
                                        gs.map, tile_size, camera.zoom
                                    )
                                if atk_result["defender_killed"]:
                                    unit_selector.deselect_unit()
                            # Sinon, essayer de se déplacer (tuile bleue)
                            else:
                                if game_engine.move_unit(
                                    unit_selector.selected_unit, hovered_tile.id
                                ):
                                    unit_selector.deselect_unit()

                        renderer.clear_cache()  # Clear cache to update FoW/TI changes

                elif event.button == 3:  # Clic droit
                    mouse_pos = event.pos
                    ui_manager.close_construction_menu()
                    hovered_tile = get_hovered_tile(game_map, camera, tile_size)

                    # clic droit sur une tuile ayant une unité
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
                    # si n'a pas d'unité sur la case, ouverture du menu de construction
                    elif hovered_tile:
                        ui_manager.open_construction_menu(hovered_tile)

        # -------- UPDATE --------
        camera.update(dt, gs.map, tile_size, window_w, window_h)
        hovered_tile = get_hovered_tile(gs.map, camera, tile_size)
        ui_manager.update_positions(window_w, window_h)
        # Invalider le rendu si la fenêtre a été redimensionnée
        if (window_w, window_h) != getattr(
            ui_manager, "_last_window_size", None
        ) or game_engine.needs_ui_update:
            renderer.map_dirty = True
            renderer.border_dirty = True
            renderer.city_dirty = True
            ui_manager.mark_dirty()
            renderer.clear_cache()
            ui_manager._last_window_size = (window_w, window_h)
            game_engine.needs_ui_update = False  # reset du flag

        mouse_pos = pygame.mouse.get_pos()
        ui_manager.update(mouse_pos, dt)

        # Transmettre l'état courant à l'UIManager
        ui_manager.hovered_tile = hovered_tile
        fps_smooth = fps_smooth * 0.9 + (1.0 / max(dt, 0.001)) * 0.1
        ui_manager.fps_value = fps_smooth

        # RENDER
        screen.fill((6, 8, 14))
        renderer.render(screen, gs, camera, tile_size, hovered_tile, dt)

        ui_manager.draw(screen, selected_unit_type, mouse_pos)

        # Afficher les zones de mouvement et de combat pour l'unité sélectionnée
        if unit_selector.is_unit_selected():
            reachable = unit_selector.get_reachable_tiles()
            attackable = unit_selector.get_attackable_tiles()

            # Afficher les tuiles attaquables en ROUGE (avant les tuiles accessibles pour la visibilité)
            renderer.render_attackable_tiles(screen, game_map, camera, tile_size, attackable)

            # Afficher les tuiles accessibles en BLEU
            renderer.render_reachable_tiles(screen, game_map, camera, tile_size, reachable)

        ui_manager.draw(screen, selected_unit_type, mouse_pos)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
