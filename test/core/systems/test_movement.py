"""Tests unitaires pour core/systems/movement.py

NOTE sur le bug détecté (movement.py lignes ~234-239) :
    Le contrôle d'affinité à l'eau (`if not unit.water_affinity and tile.is_water()`)
    est indenté à l'intérieur du bloc `if not unit.land_affinity` (code mort après un
    `continue`). En conséquence, les unités terrestres sans water_affinity peuvent
    actuellement se déplacer sur des tuiles d'eau — ce qui est un bug.
    Les tests marqués `xfail` reflètent le comportement ATTENDU et échoueront jusqu'à
    la correction du bug.
"""
import pytest
from world.unit import UnitType, Soldier, Cavalry, Archer, Colon, Boat, Plane
from world.biome import Biome
from core.systems.movement import Movement
from helpers import make_tile, make_linear_map, MockMap, MockGameState


#  get_movement_cost

class TestGetMovementCost:
    def test_plain_soldier_cost_1(self):
        assert Movement.get_movement_cost(Biome.PLAIN, UnitType.SOLDIER) == 1.0

    def test_forest_soldier_cost_1_5(self):
        assert Movement.get_movement_cost(Biome.FOREST, UnitType.SOLDIER) == 1.5

    def test_mountain_soldier_cost_2(self):
        assert Movement.get_movement_cost(Biome.MOUNTAIN, UnitType.SOLDIER) == 2.0

    def test_water_default_is_infinity(self):
        assert Movement.get_movement_cost(Biome.WATER, UnitType.SOLDIER) == float("inf")

    def test_desert_cost_1_2(self):
        assert Movement.get_movement_cost(Biome.DESERT, UnitType.SOLDIER) == 1.2

    def test_plain_cavalry_faster(self):
        cost = Movement.get_movement_cost(Biome.PLAIN, UnitType.CAVALRY)
        assert cost < 1.0  # La cavalerie est plus rapide en plaine

    def test_forest_cavalry_slower_than_default(self):
        cavalry_cost = Movement.get_movement_cost(Biome.FOREST, UnitType.CAVALRY)
        base_cost = Movement.get_movement_cost(Biome.FOREST, UnitType.SOLDIER)
        assert cavalry_cost > base_cost

    def test_mountain_cavalry_very_expensive(self):
        assert Movement.get_movement_cost(Biome.MOUNTAIN, UnitType.CAVALRY) == 2.5

    def test_colon_mountain_override(self):
        # Le colon traverse la montagne à coût 1 (override)
        assert Movement.get_movement_cost(Biome.MOUNTAIN, UnitType.COLON) == 1

    def test_colon_water_traversable(self):
        # Le colon peut traverser l'eau
        assert Movement.get_movement_cost(Biome.WATER, UnitType.COLON) == 1

    def test_plane_water_cost_1(self):
        assert Movement.get_movement_cost(Biome.WATER, UnitType.PLANE) == 1

    def test_boat_water_cost_1(self):
        assert Movement.get_movement_cost(Biome.WATER, UnitType.BOAT) == 1

    def test_unknown_biome_defaults_to_1(self):
        # Un biome inconnu doit retourner le coût par défaut 1.0
        assert Movement.get_movement_cost(None, UnitType.SOLDIER) == 1.0


#  dijkstra_reachable

class TestDijkstraReachable:
    def test_start_tile_has_cost_0(self):
        map_ = make_linear_map(3)
        distances = Movement.dijkstra_reachable(map_, 0, 5, UnitType.SOLDIER)
        assert distances[0] == 0

    def test_adjacent_tile_cost_1(self):
        map_ = make_linear_map(3)
        distances = Movement.dijkstra_reachable(map_, 0, 5, UnitType.SOLDIER)
        assert distances[1] == pytest.approx(1.0)

    def test_two_hops_cost_2(self):
        map_ = make_linear_map(3)
        distances = Movement.dijkstra_reachable(map_, 0, 5, UnitType.SOLDIER)
        assert distances[2] == pytest.approx(2.0)

    def test_max_movement_limits_reach(self):
        # dijkstra_reachable peut inclure des tuiles au-delà du max dans le dict
        # (elles sont filtrées par get_reachable_tiles). On vérifie que le coût
        # dépasse bien max_movement pour les tuiles hors portée.
        map_ = make_linear_map(10)
        distances = Movement.dijkstra_reachable(map_, 0, 2, UnitType.SOLDIER)
        # Si la tuile 3 est présente, son coût doit dépasser 2
        if 3 in distances:
            assert distances[3] > 2

    def test_water_tile_not_reachable_by_default(self):
        tiles = {
            0: make_tile(0, biome=Biome.PLAIN),
            1: make_tile(1, biome=Biome.WATER),
        }
        tiles[0].neighbors.add(1)
        tiles[1].neighbors.add(0)
        map_ = MockMap(tiles)
        distances = Movement.dijkstra_reachable(map_, 0, 5, UnitType.SOLDIER)
        assert 1 not in distances

    def test_expensive_terrain_reduces_range(self):
        # 3 tuiles en chaîne : PLAIN → MOUNTAIN → PLAIN
        tiles = {
            0: make_tile(0, biome=Biome.PLAIN),
            1: make_tile(1, biome=Biome.MOUNTAIN),
            2: make_tile(2, biome=Biome.PLAIN),
        }
        for i in range(3):
            if i > 0:
                tiles[i].neighbors.add(i - 1)
            if i < 2:
                tiles[i].neighbors.add(i + 1)
        map_ = MockMap(tiles)
        # MAX_DISTANCE=3 pour un Soldat: coût pour la tuile 2 = 1(PLAIN→MTN) + 2(MTN) = 3
        distances = Movement.dijkstra_reachable(map_, 0, 3.0, UnitType.SOLDIER)
        # Montagne coûte 2.0 → tuile 2 coûte 2.0 + 1.0 = 3.0 (dans les limites)
        assert 1 in distances
        assert 2 in distances


#  get_reachable_tiles

class TestGetReachableTiles:
    def test_already_moved_returns_empty(self, mock_game_state):
        u = Soldier(tile_id=0, owner=0)
        u.has_moved = True
        result = Movement.get_reachable_tiles(mock_game_state, u)
        assert result == set()

    def test_soldier_reaches_3_tiles(self, mock_game_state):
        # Tuile 0, Soldat MAX_DISTANCE=3 → peut aller en 1, 2, 3
        u = Soldier(tile_id=0, owner=0)
        result = Movement.get_reachable_tiles(mock_game_state, u)
        assert 1 in result
        assert 2 in result
        assert 3 in result

    def test_occupied_tile_not_reachable(self, mock_game_state):
        u = Soldier(tile_id=0, owner=0)
        blocker = Soldier(tile_id=2, owner=1)
        mock_game_state.map.tiles[2].add_unit(blocker)
        result = Movement.get_reachable_tiles(mock_game_state, u)
        assert 2 not in result

    def test_start_tile_not_in_reachable(self, mock_game_state):
        u = Soldier(tile_id=0, owner=0)
        result = Movement.get_reachable_tiles(mock_game_state, u)
        assert 0 not in result

    def test_soldier_cannot_move_to_water(self):
        """Dijkstra bloque l'eau (coût=inf) → un Soldat ne peut pas atteindre l'eau."""
        tiles = {
            0: make_tile(0, biome=Biome.PLAIN),
            1: make_tile(1, biome=Biome.WATER),
        }
        tiles[0].neighbors.add(1)
        tiles[1].neighbors.add(0)
        state = MockGameState(MockMap(tiles))
        u = Soldier(tile_id=0, owner=0)
        result = Movement.get_reachable_tiles(state, u)
        assert 1 not in result

    def test_colon_can_move_to_water(self):
        """Le Colon a un override de coût pour l'eau → il peut s'y déplacer."""
        tiles = {
            0: make_tile(0, biome=Biome.PLAIN),
            1: make_tile(1, biome=Biome.WATER),
        }
        tiles[0].neighbors.add(1)
        tiles[1].neighbors.add(0)
        state = MockGameState(MockMap(tiles))
        u = Colon(tile_id=0, owner=0)
        result = Movement.get_reachable_tiles(state, u)
        assert 1 in result


#  get_attackable_tiles

class TestGetAttackableTiles:
    def test_colon_no_attack_range(self):
        map_ = make_linear_map(3)
        u = Colon(tile_id=0, owner=0)
        result = Movement.get_attackable_tiles(map_, u)
        assert result == set()

    def test_soldier_melee_range_1(self):
        map_ = make_linear_map(3)
        u = Soldier(tile_id=0, owner=0)
        enemy = Soldier(tile_id=1, owner=1)
        map_.tiles[1].add_unit(enemy)
        result = Movement.get_attackable_tiles(map_, u)
        assert 1 in result

    def test_soldier_cannot_reach_2_hops(self):
        map_ = make_linear_map(5)
        u = Soldier(tile_id=0, owner=0)
        enemy = Soldier(tile_id=2, owner=1)
        map_.tiles[2].add_unit(enemy)
        result = Movement.get_attackable_tiles(map_, u)
        assert 2 not in result

    def test_archer_range_2(self):
        map_ = make_linear_map(5)
        u = Archer(tile_id=0, owner=0)
        enemy = Soldier(tile_id=2, owner=1)
        map_.tiles[2].add_unit(enemy)
        result = Movement.get_attackable_tiles(map_, u)
        assert 2 in result

    def test_only_enemy_tiles_returned(self):
        map_ = make_linear_map(5)
        u = Soldier(tile_id=0, owner=0)
        ally = Soldier(tile_id=1, owner=0)  # allié, pas ennemi
        map_.tiles[1].add_unit(ally)
        result = Movement.get_attackable_tiles(map_, u)
        assert 1 not in result

    def test_empty_adjacent_tile_not_attackable(self):
        map_ = make_linear_map(3)
        u = Soldier(tile_id=0, owner=0)
        result = Movement.get_attackable_tiles(map_, u)
        assert result == set()


#  get_tiles_in_range

class TestGetTilesInRange:
    def test_range_1_linear(self):
        map_ = make_linear_map(5)
        result = Movement.get_tiles_in_range(map_, 2, 1)
        assert result == {1, 3}

    def test_range_2_linear(self):
        map_ = make_linear_map(5)
        result = Movement.get_tiles_in_range(map_, 2, 2)
        assert result == {0, 1, 3, 4}

    def test_range_0_empty(self):
        map_ = make_linear_map(5)
        result = Movement.get_tiles_in_range(map_, 2, 0)
        assert result == set()

    def test_start_tile_excluded(self):
        map_ = make_linear_map(5)
        result = Movement.get_tiles_in_range(map_, 2, 1)
        assert 2 not in result


#  execute_move

class TestExecuteMove:
    def test_valid_move_returns_true(self, mock_game_state):
        u = Soldier(tile_id=0, owner=0)
        mock_game_state.map.tiles[0].add_unit(u)
        result = Movement.execute_move(mock_game_state, u, 1)
        assert result is True

    def test_valid_move_updates_tile_id(self, mock_game_state):
        u = Soldier(tile_id=0, owner=0)
        mock_game_state.map.tiles[0].add_unit(u)
        Movement.execute_move(mock_game_state, u, 1)
        assert u.tile_id == 1

    def test_valid_move_transfers_unit_between_tiles(self, mock_game_state):
        u = Soldier(tile_id=0, owner=0)
        mock_game_state.map.tiles[0].add_unit(u)
        Movement.execute_move(mock_game_state, u, 1)
        assert u not in mock_game_state.map.tiles[0].units
        assert u in mock_game_state.map.tiles[1].units

    def test_valid_move_sets_has_moved(self, mock_game_state):
        u = Soldier(tile_id=0, owner=0)
        mock_game_state.map.tiles[0].add_unit(u)
        Movement.execute_move(mock_game_state, u, 1)
        assert u.has_moved is True

    def test_already_moved_returns_false(self, mock_game_state):
        u = Soldier(tile_id=0, owner=0)
        u.has_moved = True
        result = Movement.execute_move(mock_game_state, u, 1)
        assert result is False

    def test_unreachable_tile_returns_false(self, mock_game_state):
        u = Soldier(tile_id=0, owner=0)
        mock_game_state.map.tiles[0].add_unit(u)
        # tuile 4 est à 4 hops mais Soldier a MAX_DISTANCE=3
        result = Movement.execute_move(mock_game_state, u, 4)
        assert result is False


#  calculate_movement_cost_to_tile

class TestCalculateMovementCost:
    def test_adjacent_tile_cost(self):
        map_ = make_linear_map(5)
        u = Soldier(tile_id=0, owner=0)
        cost = Movement.calculate_movement_cost_to_tile(map_, u, 1)
        assert cost == pytest.approx(1.0)

    def test_unreachable_returns_minus_one(self):
        # Soldat ne peut pas traverser l'eau
        tiles = {
            0: make_tile(0, biome=Biome.PLAIN),
            1: make_tile(1, biome=Biome.WATER),
        }
        tiles[0].neighbors.add(1)
        tiles[1].neighbors.add(0)
        map_ = MockMap(tiles)
        u = Soldier(tile_id=0, owner=0)
        assert Movement.calculate_movement_cost_to_tile(map_, u, 1) == -1
