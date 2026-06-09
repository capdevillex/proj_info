"""Tests unitaires pour world/tile.py"""
import pytest
from world.biome import Biome
from world.resources import Resource
from world.tile import Tile
from world.unit import Soldier, Cavalry

from helpers import make_tile


class TestTileInit:
    def test_id_is_set(self):
        t = make_tile(7)
        assert t.id == 7

    def test_cells_stored(self):
        cells = [(0, 0), (1, 0), (2, 0)]
        t = Tile(0, cells)
        assert t.cells == cells

    def test_area_equals_cell_count(self):
        cells = [(0, 0), (1, 0), (2, 0)]
        t = Tile(0, cells)
        assert t.area == 3

    def test_neighbors_empty_on_creation(self):
        t = make_tile(0)
        assert t.neighbors == set()

    def test_units_empty_on_creation(self):
        t = make_tile(0)
        assert t.units == []

    def test_constructions_empty_on_creation(self):
        t = make_tile(0)
        assert t.constructions == []

    def test_default_biome_is_blank(self):
        cells = [(0, 0)]
        t = Tile(0, cells)
        assert t.biome == Biome.BLANK

    def test_custom_biome_stored(self):
        t = make_tile(0, biome=Biome.FOREST)
        assert t.biome == Biome.FOREST

    def test_default_resource_is_none(self):
        cells = [(0, 0)]
        t = Tile(0, cells)
        assert t.resource == Resource.NONE

    def test_custom_resource_stored(self):
        t = make_tile(0, resource=Resource.GOLD1)
        assert t.resource == Resource.GOLD1


class TestTileCenter:
    def test_center_single_cell(self):
        t = Tile(0, [(4, 6)])
        assert t.center == (4.5, 6.5)

    def test_center_two_cells(self):
        # cells (0,0) et (2,0) → centres (0.5,0.5) et (2.5,0.5) → moyenne (1.5, 0.5)
        t = Tile(0, [(0, 0), (2, 0)])
        assert t.center == (1.5, 0.5)

    def test_center_three_cells_symmetrical(self):
        t = Tile(0, [(0, 0), (2, 0), (4, 0)])
        # (0.5 + 2.5 + 4.5) / 3 = 2.5
        assert t.center[0] == pytest.approx(2.5)


class TestTileIsWater:
    def test_water_biome_is_water(self):
        t = make_tile(0, biome=Biome.WATER)
        assert t.is_water() is True

    def test_plain_is_not_water(self):
        t = make_tile(0, biome=Biome.PLAIN)
        assert t.is_water() is False

    def test_forest_is_not_water(self):
        t = make_tile(0, biome=Biome.FOREST)
        assert t.is_water() is False

    def test_mountain_is_not_water(self):
        t = make_tile(0, biome=Biome.MOUNTAIN)
        assert t.is_water() is False

    def test_desert_is_not_water(self):
        t = make_tile(0, biome=Biome.DESERT)
        assert t.is_water() is False

    def test_blank_is_not_water(self):
        t = make_tile(0, biome=Biome.BLANK)
        assert t.is_water() is False


class TestTileAddUnit:
    def test_add_unit_appears_in_units(self, plain_tile):
        u = Soldier(tile_id=plain_tile.id, owner=0)
        plain_tile.add_unit(u)
        assert u in plain_tile.units

    def test_add_unit_updates_unit_tile_id(self, plain_tile):
        u = Soldier(tile_id=99, owner=0)
        plain_tile.add_unit(u)
        assert u.tile_id == plain_tile.id

    def test_add_same_unit_twice_no_duplicate(self, plain_tile):
        u = Soldier(tile_id=plain_tile.id, owner=0)
        plain_tile.add_unit(u)
        plain_tile.add_unit(u)
        assert plain_tile.units.count(u) == 1

    def test_add_multiple_different_units(self, plain_tile):
        u1 = Soldier(tile_id=plain_tile.id, owner=0)
        u2 = Cavalry(tile_id=plain_tile.id, owner=0)
        plain_tile.add_unit(u1)
        plain_tile.add_unit(u2)
        assert len(plain_tile.units) == 2


class TestTileRemoveUnit:
    def test_remove_unit_returns_true(self, plain_tile, soldier):
        plain_tile.units.append(soldier)
        assert plain_tile.remove_unit(soldier) is True

    def test_remove_unit_is_removed(self, plain_tile, soldier):
        plain_tile.units.append(soldier)
        plain_tile.remove_unit(soldier)
        assert soldier not in plain_tile.units

    def test_remove_absent_unit_returns_false(self, plain_tile, soldier):
        assert plain_tile.remove_unit(soldier) is False

    def test_remove_unit_by_id_returns_unit(self, plain_tile, soldier):
        plain_tile.units.append(soldier)
        removed = plain_tile.remove_unit_by_id(soldier.id)
        assert removed is soldier

    def test_remove_unit_by_id_unit_gone(self, plain_tile, soldier):
        plain_tile.units.append(soldier)
        plain_tile.remove_unit_by_id(soldier.id)
        assert soldier not in plain_tile.units

    def test_remove_unit_by_id_not_found_returns_none(self, plain_tile):
        assert plain_tile.remove_unit_by_id(999) is None


class TestTileGetUnits:
    def test_get_units_returns_copy(self, plain_tile, soldier):
        plain_tile.units.append(soldier)
        copy = plain_tile.get_units()
        copy.clear()
        assert len(plain_tile.units) == 1

    def test_get_unit_by_id_found(self, plain_tile, soldier):
        plain_tile.units.append(soldier)
        assert plain_tile.get_unit_by_id(soldier.id) is soldier

    def test_get_unit_by_id_not_found(self, plain_tile):
        assert plain_tile.get_unit_by_id(999) is None


class TestTileHasUnits:
    def test_empty_tile_has_no_units(self, plain_tile):
        assert plain_tile.has_units() is False

    def test_tile_with_unit_has_units(self, plain_tile, soldier):
        plain_tile.units.append(soldier)
        assert plain_tile.has_units() is True


class TestTileGetUnitsByOwner:
    def test_returns_only_owner_units(self, plain_tile):
        u0 = Soldier(tile_id=0, owner=0)
        u1 = Soldier(tile_id=0, owner=1)
        plain_tile.units.extend([u0, u1])
        result = plain_tile.get_units_by_owner(0)
        assert result == [u0]
        assert u1 not in result

    def test_no_units_for_owner(self, plain_tile, soldier):
        plain_tile.units.append(soldier)
        assert plain_tile.get_units_by_owner(99) == []


class TestTileClearUnits:
    def test_clear_empties_units(self, plain_tile, soldier):
        plain_tile.units.append(soldier)
        plain_tile.clear_units()
        assert plain_tile.units == []

    def test_clear_returns_removed_units(self, plain_tile, soldier, cavalry):
        plain_tile.units.extend([soldier, cavalry])
        removed = plain_tile.clear_units()
        assert soldier in removed
        assert cavalry in removed


class TestTileRepr:
    def test_repr_contains_id(self):
        t = make_tile(42)
        assert "42" in repr(t)

    def test_repr_contains_biome_name(self):
        t = make_tile(0, biome=Biome.FOREST)
        assert "FOREST" in repr(t)

    def test_repr_no_units_no_unit_string(self, plain_tile):
        assert "unit" not in repr(plain_tile)

    def test_repr_with_units_mentions_count(self, plain_tile, soldier):
        plain_tile.units.append(soldier)
        assert "unit" in repr(plain_tile)
