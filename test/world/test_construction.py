"""Tests unitaires pour world/construction.py"""
import pytest
from world.biome import Biome
from world.resources import Resource
from world.construction import Farm, Mine, Scierie, Road
from helpers import make_tile


class TestFarm:
    def test_name(self):
        t = make_tile(0)
        assert Farm(t).name == "Ferme"

    def test_cost(self):
        t = make_tile(0)
        assert Farm.COST == {"wood": 5}

    def test_boost_food1(self):
        t = make_tile(0, resource=Resource.FOOD1)
        f = Farm(t)
        assert f.boost["food"] == 1

    def test_boost_food2(self):
        t = make_tile(0, resource=Resource.FOOD2)
        f = Farm(t)
        assert f.boost["food"] == 2

    def test_boost_food3(self):
        t = make_tile(0, resource=Resource.FOOD3)
        f = Farm(t)
        assert f.boost["food"] == 3

    def test_boost_no_food_resource_defaults_to_1(self):
        t = make_tile(0, resource=Resource.NONE)
        f = Farm(t)
        assert f.boost["food"] == 1

    def test_boost_non_food_resource_defaults_to_1(self):
        t = make_tile(0, resource=Resource.WOOD1)
        f = Farm(t)
        assert f.boost["food"] == 1

    def test_repr(self):
        t = make_tile(0)
        assert "Ferme" in repr(Farm(t))


class TestMine:
    def test_name(self):
        t = make_tile(0)
        assert Mine(t).name == "Mine"

    def test_cost(self):
        assert Mine.COST == {"stone": 2, "wood": 3}

    def test_boost_iron1(self):
        t = make_tile(0, resource=Resource.IRON1)
        m = Mine(t)
        assert m.boost["iron"] == 1
        assert m.boost["stone"] == 1

    def test_boost_iron3(self):
        t = make_tile(0, resource=Resource.IRON3)
        m = Mine(t)
        assert m.boost["iron"] == 3

    def test_boost_gold1(self):
        t = make_tile(0, resource=Resource.GOLD1)
        m = Mine(t)
        assert m.boost["gold"] == 1
        assert m.boost["stone"] == 1

    def test_boost_gold2(self):
        t = make_tile(0, resource=Resource.GOLD2)
        m = Mine(t)
        assert m.boost["gold"] == 2

    def test_boost_stone2(self):
        t = make_tile(0, resource=Resource.STONE2)
        m = Mine(t)
        assert m.boost["stone"] == 2

    def test_boost_default_no_resource(self):
        t = make_tile(0, resource=Resource.NONE)
        m = Mine(t)
        assert m.boost["iron"] == 1
        assert m.boost["stone"] == 1
        assert m.boost["gold"] == 0

    def test_boost_default_food_resource(self):
        t = make_tile(0, resource=Resource.FOOD1)
        m = Mine(t)
        assert m.boost["iron"] == 1
        assert m.boost["stone"] == 1


class TestScierie:
    def test_name(self):
        t = make_tile(0)
        assert Scierie(t).name == "Scierie"

    def test_cost(self):
        assert Scierie.COST == {"wood": 5}

    def test_boost_wood1(self):
        t = make_tile(0, resource=Resource.WOOD1)
        s = Scierie(t)
        assert s.boost["wood"] == 1

    def test_boost_wood3(self):
        t = make_tile(0, resource=Resource.WOOD3)
        s = Scierie(t)
        assert s.boost["wood"] == 3

    def test_boost_no_wood_defaults_to_1(self):
        t = make_tile(0, resource=Resource.NONE)
        s = Scierie(t)
        assert s.boost["wood"] == 1

    def test_boost_non_wood_resource_defaults_to_1(self):
        t = make_tile(0, resource=Resource.IRON2)
        s = Scierie(t)
        assert s.boost["wood"] == 1


class TestRoad:
    def test_name(self):
        t = make_tile(0)
        assert Road(t).name == "Route"

    def test_cost(self):
        assert Road.COST == {"stone": 1, "wood": 1}

    def test_boost_movement(self):
        t = make_tile(0)
        r = Road(t)
        assert r.boost["movement"] == 1

    def test_no_resource_boost(self):
        t = make_tile(0)
        r = Road(t)
        assert "food" not in r.boost
        assert "gold" not in r.boost
