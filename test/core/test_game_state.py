"""Tests unitaires pour core/game_state.py"""
import pytest
from unittest.mock import patch, MagicMock
from world.kingdom import Kingdom
from world.unit import Soldier
from core.game_state import GameState, TurnPhase
from helpers import make_tile, MockMap, MockGameState


@pytest.fixture
def game_state(five_tile_map):
    """GameState avec la génération de Map patchée."""
    with patch("core.game_state.Map", return_value=five_tile_map):
        state = GameState(10, 10, 42, 5, False)
    return state


class TestGameStateInit:
    def test_current_player_is_0(self, game_state):
        assert game_state.current_player == 0

    def test_initial_turn_is_0(self, game_state):
        assert game_state.turn == 0

    def test_player_kingdom_created(self, game_state):
        assert len(game_state.kingdoms) == 1
        assert game_state.kingdoms[0].kingdom_id == 0
        assert game_state.kingdoms[0].is_ai is False

    def test_turn_order_starts_with_player(self, game_state):
        assert game_state.turn_order[0] == 0

    def test_phase_is_player_turn(self, game_state):
        assert game_state.phase == TurnPhase.PLAYER_TURN

    def test_player_resources_initialized(self, game_state):
        res = game_state.player_resources[0]
        assert set(res.keys()) == {"food", "wood", "stone", "iron", "gold"}

    def test_units_empty(self, game_state):
        assert game_state.units == []

    def test_cities_empty(self, game_state):
        assert game_state.cities == []

    def test_visibility_false_by_default(self, game_state):
        assert game_state.use_ti is False
        assert game_state.use_fow is False


class TestGameStateProperties:
    def test_active_kingdom_id_is_player(self, game_state):
        assert game_state.active_kingdom_id == 0

    def test_is_player_turn_true_initially(self, game_state):
        assert game_state.is_player_turn is True

    def test_is_player_turn_false_during_ai(self, game_state):
        game_state.phase = TurnPhase.AI_TURN
        assert game_state.is_player_turn is False

    def test_active_kingdom_id_changes_with_index(self, game_state):
        k2 = Kingdom(kingdom_id=2, name="AI", color=(0, 0, 0), is_ai=True)
        game_state.add_kingdom(k2)
        game_state.current_kingdom_idx = 1
        assert game_state.active_kingdom_id == 2


class TestAddKingdom:
    def test_add_kingdom_increases_count(self, game_state):
        k = Kingdom(kingdom_id=1, name="AI1", color=(0, 0, 0), is_ai=True)
        game_state.add_kingdom(k)
        assert len(game_state.kingdoms) == 2

    def test_add_kingdom_added_to_turn_order(self, game_state):
        k = Kingdom(kingdom_id=5, name="X", color=(0, 0, 0))
        game_state.add_kingdom(k)
        assert 5 in game_state.turn_order

    def test_add_kingdom_creates_resources(self, game_state):
        k = Kingdom(kingdom_id=3, name="X", color=(0, 0, 0))
        game_state.add_kingdom(k)
        assert 3 in game_state.player_resources

    def test_add_duplicate_raises(self, game_state):
        with pytest.raises(ValueError):
            game_state.add_kingdom(Kingdom(kingdom_id=0, name="Dup", color=(0, 0, 0)))

    def test_get_kingdom_found(self, game_state):
        k = game_state.get_kingdom(0)
        assert k is not None
        assert k.kingdom_id == 0

    def test_get_kingdom_not_found(self, game_state):
        assert game_state.get_kingdom(999) is None


class TestCityManagement:
    def _make_city(self, game_state, name="Test", owner=0, tile_id=0):
        from world.city import City
        city = City(name, owner=owner, center_tile_id=tile_id, state=game_state)
        return city

    def test_add_city(self, game_state):
        city = self._make_city(game_state)
        game_state.add_city(city)
        assert city in game_state.cities

    def test_get_city_by_id(self, game_state):
        city = self._make_city(game_state)
        game_state.add_city(city)
        found = game_state.get_city_by_id(city.id)
        assert found is city

    def test_get_city_by_id_not_found(self, game_state):
        assert game_state.get_city_by_id(999) is None

    def test_get_city_at_tile(self, game_state):
        city = self._make_city(game_state, tile_id=2)
        game_state.add_city(city)
        assert game_state.get_city_at_tile(2) is city

    def test_get_city_at_tile_no_city(self, game_state):
        assert game_state.get_city_at_tile(99) is None

    def test_get_cities_by_owner(self, game_state):
        c1 = self._make_city(game_state, name="A", owner=0, tile_id=0)
        c2 = self._make_city(game_state, name="B", owner=1, tile_id=1)
        game_state.add_city(c1)
        game_state.add_city(c2)
        result = game_state.get_cities_by_owner(0)
        assert c1 in result
        assert c2 not in result

    def test_add_city_creates_resources_for_new_owner(self, game_state):
        from world.city import City
        city = City("Z", owner=7, center_tile_id=0, state=game_state)
        game_state.add_city(city)
        assert 7 in game_state.player_resources


class TestVisibilityUpdate:
    def test_update_discovered_accumulates(self, game_state):
        game_state.visibility = 0b1010
        game_state.discovered = 0b0101
        game_state.update_discovered()
        assert game_state.discovered == 0b1111

    def test_update_fow_resets_visibility(self, game_state, five_tile_map):
        # Avec aucune unité ni ville, la visibilité doit rester 0
        game_state.visibility = 999
        game_state.map = five_tile_map
        game_state.update_fow()
        assert game_state.visibility == 0

    def test_update_fow_with_unit(self, game_state, five_tile_map):
        game_state.map = five_tile_map
        u = Soldier(tile_id=2, owner=0)
        game_state.units.append(u)
        # Placer l'unité sur la tuile pour que get_visibility_mask fonctionne
        game_state.update_fow()
        assert game_state.visibility != 0
