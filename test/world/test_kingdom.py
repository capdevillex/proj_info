"""Tests unitaires pour world/kingdom.py"""
import pytest
from world.kingdom import Kingdom


class TestKingdomInit:
    def test_kingdom_id_stored(self):
        k = Kingdom(kingdom_id=1, name="France", color=(255, 0, 0))
        assert k.kingdom_id == 1

    def test_name_stored(self):
        k = Kingdom(kingdom_id=0, name="Rome", color=(200, 200, 0))
        assert k.name == "Rome"

    def test_color_stored(self):
        color = (80, 130, 210)
        k = Kingdom(kingdom_id=0, name="Test", color=color)
        assert k.color == color

    def test_default_not_ai(self):
        k = Kingdom(kingdom_id=0, name="X", color=(0, 0, 0))
        assert k.is_ai is False

    def test_ai_kingdom(self):
        k = Kingdom(kingdom_id=1, name="Bot", color=(0, 0, 0), is_ai=True)
        assert k.is_ai is True

    def test_default_cities_empty(self):
        k = Kingdom(kingdom_id=0, name="X", color=(0, 0, 0))
        assert k.cities == []

    def test_default_ai_params_empty(self):
        k = Kingdom(kingdom_id=0, name="X", color=(0, 0, 0))
        assert k.ai_params == {}

    def test_cities_not_shared_between_instances(self):
        k1 = Kingdom(kingdom_id=0, name="A", color=(0, 0, 0))
        k2 = Kingdom(kingdom_id=1, name="B", color=(0, 0, 0))
        k1.cities.append(99)
        assert 99 not in k2.cities

    def test_ai_params_not_shared(self):
        k1 = Kingdom(kingdom_id=0, name="A", color=(0, 0, 0))
        k2 = Kingdom(kingdom_id=1, name="B", color=(0, 0, 0))
        k1.ai_params["aggression"] = 0.9
        assert "aggression" not in k2.ai_params


class TestKingdomRepr:
    def test_repr_human(self):
        k = Kingdom(kingdom_id=0, name="Joueur", color=(0, 0, 0), is_ai=False)
        r = repr(k)
        assert "Humain" in r
        assert "Joueur" in r

    def test_repr_ai(self):
        k = Kingdom(kingdom_id=1, name="Bot", color=(0, 0, 0), is_ai=True)
        assert "IA" in repr(k)

    def test_repr_contains_id(self):
        k = Kingdom(kingdom_id=42, name="X", color=(0, 0, 0))
        assert "42" in repr(k)
