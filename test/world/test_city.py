"""Tests unitaires pour world/city.py"""
import pytest
from unittest.mock import MagicMock
from world.biome import Biome
from world.resources import Resource
from world.city import City
from world.construction import Farm, Mine
from helpers import make_tile, MockMap


def make_mock_state(tiles=None):
    """Crée un état minimal pour City."""
    state = MagicMock()
    state.cities = []
    if tiles:
        state.map = MockMap(tiles)
    else:
        state.map = MockMap()
    return state


class TestCityInit:
    def test_auto_id_starts_at_0(self):
        state = make_mock_state()
        c = City("Paris", owner=0, center_tile_id=0, state=state)
        assert c.id == 0

    def test_auto_id_increments(self):
        state = make_mock_state()
        c1 = City("A", owner=0, center_tile_id=0, state=state)
        c2 = City("B", owner=0, center_tile_id=1, state=state)
        assert c2.id == c1.id + 1

    def test_name_stored(self):
        state = make_mock_state()
        c = City("Rome", owner=0, center_tile_id=0, state=state)
        assert c.name == "Rome"

    def test_owner_stored(self):
        state = make_mock_state()
        c = City("X", owner=2, center_tile_id=0, state=state)
        assert c.owner == 2

    def test_center_tile_in_tile_ids(self):
        state = make_mock_state()
        c = City("X", owner=0, center_tile_id=5, state=state)
        assert 5 in c.tile_ids

    def test_initial_population_is_1(self):
        state = make_mock_state()
        c = City("X", owner=0, center_tile_id=0, state=state)
        assert c.population == 1

    def test_initial_age_is_0(self):
        state = make_mock_state()
        c = City("X", owner=0, center_tile_id=0, state=state)
        assert c.age == 0

    def test_initial_production(self):
        state = make_mock_state()
        c = City("X", owner=0, center_tile_id=0, state=state)
        assert c.production["food"] == 1
        assert c.production["gold"] == 1
        assert c.production["wood"] == 0
        assert c.production["stone"] == 0
        assert c.production["iron"] == 0

    def test_initial_constructions_empty(self):
        state = make_mock_state()
        c = City("X", owner=0, center_tile_id=0, state=state)
        assert len(c.constructions) == 0


class TestCityRemoveTile:
    def test_remove_non_center_tile(self):
        state = make_mock_state()
        c = City("X", owner=0, center_tile_id=0, state=state)
        c.tile_ids.add(1)
        assert c.remove_tile(1) is True
        assert 1 not in c.tile_ids

    def test_cannot_remove_center_tile(self):
        state = make_mock_state()
        c = City("X", owner=0, center_tile_id=0, state=state)
        assert c.remove_tile(0) is False
        assert 0 in c.tile_ids

    def test_remove_tile_not_in_territory(self):
        state = make_mock_state()
        c = City("X", owner=0, center_tile_id=0, state=state)
        assert c.remove_tile(99) is False


class TestCityCalculateProduction:
    def _make_state_with_tiles(self, tile_map):
        state = make_mock_state(tile_map)
        return state

    def test_no_resources_gives_base_production(self):
        t = make_tile(0, resource=Resource.NONE)
        state = self._make_state_with_tiles({0: t})
        c = City("X", owner=0, center_tile_id=0, state=state)
        c.calculate_production(state.map)
        assert c.production["food"] == 1
        assert c.production["gold"] == 1
        assert c.production["wood"] == 0

    def test_food1_tile_adds_1_food(self):
        t = make_tile(0, resource=Resource.FOOD1)
        state = self._make_state_with_tiles({0: t})
        c = City("X", owner=0, center_tile_id=0, state=state)
        c.calculate_production(state.map)
        assert c.production["food"] == 2  # base 1 + FOOD1 level 1

    def test_food3_tile_adds_3_food(self):
        t = make_tile(0, resource=Resource.FOOD3)
        state = self._make_state_with_tiles({0: t})
        c = City("X", owner=0, center_tile_id=0, state=state)
        c.calculate_production(state.map)
        assert c.production["food"] == 4  # base 1 + FOOD3 level 3

    def test_wood2_tile_adds_wood(self):
        t = make_tile(0, resource=Resource.WOOD2)
        state = self._make_state_with_tiles({0: t})
        c = City("X", owner=0, center_tile_id=0, state=state)
        c.calculate_production(state.map)
        assert c.production["wood"] == 2

    def test_gold2_tile_adds_gold(self):
        t = make_tile(0, resource=Resource.GOLD2)
        state = self._make_state_with_tiles({0: t})
        c = City("X", owner=0, center_tile_id=0, state=state)
        c.calculate_production(state.map)
        assert c.production["gold"] == 3  # base 1 + GOLD2 level 2

    def test_iron3_tile_adds_iron(self):
        t = make_tile(0, resource=Resource.IRON3)
        state = self._make_state_with_tiles({0: t})
        c = City("X", owner=0, center_tile_id=0, state=state)
        c.calculate_production(state.map)
        assert c.production["iron"] == 3

    def test_stone1_tile_adds_stone(self):
        t = make_tile(0, resource=Resource.STONE1)
        state = self._make_state_with_tiles({0: t})
        c = City("X", owner=0, center_tile_id=0, state=state)
        c.calculate_production(state.map)
        assert c.production["stone"] == 1

    def test_multiple_tiles_accumulate(self):
        t0 = make_tile(0, resource=Resource.FOOD1)
        t1 = make_tile(1, resource=Resource.FOOD2)
        state = self._make_state_with_tiles({0: t0, 1: t1})
        c = City("X", owner=0, center_tile_id=0, state=state)
        c.tile_ids.add(1)
        c.calculate_production(state.map)
        assert c.production["food"] == 4  # base 1 + 1 + 2

    def test_farm_construction_adds_boost(self):
        t = make_tile(0, resource=Resource.FOOD2)
        farm = Farm(t)
        t.constructions.append(farm)
        state = self._make_state_with_tiles({0: t})
        c = City("X", owner=0, center_tile_id=0, state=state)
        c.calculate_production(state.map)
        # base 1 + FOOD2 (2) + Farm boost (2) = 5
        assert c.production["food"] == 5

    def test_production_resets_each_call(self):
        t = make_tile(0, resource=Resource.GOLD1)
        state = self._make_state_with_tiles({0: t})
        c = City("X", owner=0, center_tile_id=0, state=state)
        c.calculate_production(state.map)
        c.calculate_production(state.map)
        assert c.production["gold"] == 2  # pas d'accumulation double


class TestCityVisibilityMask:
    def test_sees_own_tile(self):
        t = make_tile(0)
        state = make_mock_state({0: t})
        c = City("X", owner=0, center_tile_id=0, state=state)
        mask = c.get_visibility_mask(state.map)
        assert mask & (1 << 0)

    def test_sees_neighboring_tiles(self):
        t0 = make_tile(0)
        t1 = make_tile(1)
        t0.neighbors.add(1)
        t1.neighbors.add(0)
        state = make_mock_state({0: t0, 1: t1})
        c = City("X", owner=0, center_tile_id=0, state=state)
        mask = c.get_visibility_mask(state.map)
        assert mask & (1 << 1)

    def test_sees_all_controlled_tiles(self):
        t0 = make_tile(0)
        t1 = make_tile(1)
        t2 = make_tile(2)
        state = make_mock_state({0: t0, 1: t1, 2: t2})
        c = City("X", owner=0, center_tile_id=0, state=state)
        c.tile_ids.add(2)
        mask = c.get_visibility_mask(state.map)
        assert mask & (1 << 0)
        assert mask & (1 << 2)

    def test_missing_tile_id_skipped(self):
        t0 = make_tile(0)
        state = make_mock_state({0: t0})
        c = City("X", owner=0, center_tile_id=0, state=state)
        c.tile_ids.add(999)  # tuile inexistante
        # Ne doit pas lever d'exception
        mask = c.get_visibility_mask(state.map)
        assert mask & (1 << 0)


class TestCityRepr:
    def test_repr_contains_name(self):
        state = make_mock_state()
        c = City("Carthage", owner=0, center_tile_id=0, state=state)
        assert "Carthage" in repr(c)

    def test_repr_contains_owner(self):
        state = make_mock_state()
        c = City("X", owner=3, center_tile_id=0, state=state)
        assert "owner=3" in repr(c)
