"""Tests unitaires pour core/systems/economy.py"""
import pytest
from unittest.mock import MagicMock, patch
from world.unit import Soldier, Colon
from world.resources import Resource
from core.systems.economy import Economy
from helpers import make_tile, MockMap, MockGameState


def make_state_with_cities(cities=None, units=None, player=0):
    """Crée un MockGameState enrichi avec villes et unités."""
    state = MockGameState(MockMap())
    state.cities = cities or []
    state.units = units or []
    state.current_player = player
    return state


def make_city_mock(owner=0, production=None):
    """Crée un mock de City avec une production connue."""
    city = MagicMock()
    city.owner = owner
    city.production = production or {"food": 1, "wood": 0, "stone": 0, "iron": 0, "gold": 1}
    city.calculate_production = MagicMock()
    return city


class TestProcessCityProduction:
    def test_city_production_added_to_resources(self):
        econ = Economy()
        city = make_city_mock(owner=0, production={"food": 3, "wood": 2, "stone": 0, "iron": 0, "gold": 5})
        state = make_state_with_cities(cities=[city])
        econ.process_city_production(state)
        assert state.player_resources[0]["food"] == 3
        assert state.player_resources[0]["wood"] == 2
        assert state.player_resources[0]["gold"] == 5

    def test_calculate_production_called(self):
        econ = Economy()
        city = make_city_mock(owner=0)
        state = make_state_with_cities(cities=[city])
        econ.process_city_production(state)
        city.calculate_production.assert_called_once_with(state.map)

    def test_multiple_cities_same_owner_accumulate(self):
        econ = Economy()
        c1 = make_city_mock(owner=0, production={"food": 2, "wood": 0, "stone": 0, "iron": 0, "gold": 0})
        c2 = make_city_mock(owner=0, production={"food": 3, "wood": 1, "stone": 0, "iron": 0, "gold": 0})
        state = make_state_with_cities(cities=[c1, c2])
        econ.process_city_production(state)
        assert state.player_resources[0]["food"] == 5
        assert state.player_resources[0]["wood"] == 1

    def test_creates_resources_for_new_owner(self):
        econ = Economy()
        city = make_city_mock(owner=7, production={"food": 1, "wood": 0, "stone": 0, "iron": 0, "gold": 0})
        state = make_state_with_cities(cities=[city])
        econ.process_city_production(state)
        assert 7 in state.player_resources
        assert state.player_resources[7]["food"] == 1

    def test_different_owners_separate_resources(self):
        econ = Economy()
        c0 = make_city_mock(owner=0, production={"food": 10, "wood": 0, "stone": 0, "iron": 0, "gold": 0})
        c1 = make_city_mock(owner=1, production={"food": 5, "wood": 0, "stone": 0, "iron": 0, "gold": 0})
        state = make_state_with_cities(cities=[c0, c1])
        econ.process_city_production(state)
        assert state.player_resources[0]["food"] == 10
        assert state.player_resources[1]["food"] == 5

    def test_no_cities_no_change(self):
        econ = Economy()
        state = make_state_with_cities(cities=[])
        econ.process_city_production(state)
        assert state.player_resources[0]["food"] == 0


class TestEconomyUpdate:
    def test_unit_upkeep_deducted_from_current_player(self):
        econ = Economy()
        u = Soldier(tile_id=0, owner=0)
        state = make_state_with_cities(units=[u], player=0)
        state.player_resources[0]["gold"] = 10
        econ.update(state)
        # Upkeep du Soldier = 1
        assert state.player_resources[0]["gold"] == 10 - Soldier.UPKEEP_COST

    def test_other_player_units_not_deducted(self):
        econ = Economy()
        u = Soldier(tile_id=0, owner=1)  # propriétaire 1
        state = make_state_with_cities(units=[u], player=0)
        state.player_resources[0]["gold"] = 10
        econ.update(state)
        # L'unité appartient au joueur 1, pas 0 → aucune déduction sur joueur 0
        assert state.player_resources[0]["gold"] == 10

    def test_multiple_units_cumulative_upkeep(self):
        econ = Economy()
        u1 = Soldier(tile_id=0, owner=0)
        u2 = Colon(tile_id=1, owner=0)
        state = make_state_with_cities(units=[u1, u2], player=0)
        state.player_resources[0]["gold"] = 50
        econ.update(state)
        # Soldier upkeep=1, Colon upkeep=10
        expected = 50 - Soldier.UPKEEP_COST - Colon.UPKEEP_COST
        assert state.player_resources[0]["gold"] == expected

    def test_update_calls_process_city_production(self):
        econ = Economy()
        city = make_city_mock(owner=0, production={"food": 2, "wood": 0, "stone": 0, "iron": 0, "gold": 0})
        state = make_state_with_cities(cities=[city], player=0)
        econ.update(state)
        # La production de la ville doit avoir été traitée
        city.calculate_production.assert_called_once()

    def test_gold_can_go_negative(self):
        """L'entretien peut mettre les ressources en négatif (pas de plancher)."""
        econ = Economy()
        u = Colon(tile_id=0, owner=0)  # upkeep=10
        state = make_state_with_cities(units=[u], player=0)
        state.player_resources[0]["gold"] = 5
        econ.update(state)
        assert state.player_resources[0]["gold"] == 5 - Colon.UPKEEP_COST
