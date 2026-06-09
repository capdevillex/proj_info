"""Tests unitaires pour world/resources.py"""
import pytest
from world.resources import Resource


class TestResourceEnum:
    def test_none_exists(self):
        assert Resource.NONE is not None

    def test_gold_levels(self):
        assert Resource.GOLD1
        assert Resource.GOLD2
        assert Resource.GOLD3

    def test_food_levels(self):
        assert Resource.FOOD1
        assert Resource.FOOD2
        assert Resource.FOOD3

    def test_wood_levels(self):
        assert Resource.WOOD1
        assert Resource.WOOD2
        assert Resource.WOOD3

    def test_iron_levels(self):
        assert Resource.IRON1
        assert Resource.IRON2
        assert Resource.IRON3

    def test_stone_levels(self):
        assert Resource.STONE1
        assert Resource.STONE2
        assert Resource.STONE3

    def test_total_count(self):
        # 1 NONE + 5 types × 3 niveaux = 16
        assert len(Resource) == 16

    def test_names_start_with_category(self):
        for r in Resource:
            if r == Resource.NONE:
                continue
            assert r.name[:-1] in ("GOLD", "FOOD", "WOOD", "IRON", "STONE")

    def test_levels_end_with_digit(self):
        for r in Resource:
            if r == Resource.NONE:
                continue
            assert r.name[-1].isdigit()

    def test_level_digit_range(self):
        for r in Resource:
            if r == Resource.NONE:
                continue
            assert int(r.name[-1]) in (1, 2, 3)
