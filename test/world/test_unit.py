"""Tests unitaires pour world/unit.py"""
import pytest
from world.unit import (
    Unit, UnitType, UNIT_CLASS_MAP,
    Soldier, Cavalry, Archer, Colon, Baby, Plane, Boat,
)
from helpers import make_tile, make_linear_map, MockMap


#  Stats de référence

class TestSoldierStats:
    def test_unit_type(self, soldier):
        assert soldier.unit_type == UnitType.SOLDIER

    def test_max_distance(self, soldier):
        assert soldier.max_distance == 3

    def test_attack_range(self, soldier):
        assert soldier.attack_range == 1

    def test_base_attack(self):
        assert Soldier.BASE_ATTACK == 9999

    def test_base_defense(self):
        assert Soldier.BASE_DEFENSE == 8

    def test_base_hp(self):
        assert Soldier.BASE_HP == 100

    def test_upkeep(self):
        assert Soldier.UPKEEP_COST == 1

    def test_no_dash(self):
        assert Soldier.DASH is False

    def test_no_fly(self):
        assert Soldier.FLY is False

    def test_no_escape(self):
        assert Soldier.ESCAPE is False

    def test_no_scout(self):
        assert Soldier.SCOUT is False

    def test_land_affinity(self):
        assert Soldier.LAND_AFFINITY is True

    def test_no_water_affinity(self):
        assert Soldier.WATER_AFFINITY is False


class TestCavalryStats:
    def test_unit_type(self, cavalry):
        assert cavalry.unit_type == UnitType.CAVALRY

    def test_max_distance(self, cavalry):
        assert cavalry.max_distance == 5

    def test_has_dash(self):
        assert Cavalry.DASH is True

    def test_has_escape(self):
        assert Cavalry.ESCAPE is True

    def test_no_fly(self):
        assert Cavalry.FLY is False

    def test_hp(self):
        assert Cavalry.BASE_HP == 90


class TestArcherStats:
    def test_unit_type(self, archer):
        assert archer.unit_type == UnitType.ARCHER

    def test_attack_range_2(self):
        assert Archer.ATTACK_RANGE == 2

    def test_is_scout(self):
        assert Archer.SCOUT is True

    def test_max_distance(self):
        assert Archer.MAX_DISTANCE == 2

    def test_hp(self):
        assert Archer.BASE_HP == 70


class TestColonStats:
    def test_unit_type(self, colon):
        assert colon.unit_type == UnitType.COLON

    def test_attack_range_0(self):
        assert Colon.ATTACK_RANGE == 0

    def test_max_distance_1(self):
        assert Colon.MAX_DISTANCE == 1

    def test_water_affinity(self):
        assert Colon.WATER_AFFINITY is True

    def test_high_upkeep(self):
        assert Colon.UPKEEP_COST == 10


class TestPlaneStats:
    def test_unit_type(self):
        p = Plane(tile_id=0, owner=0)
        assert p.unit_type == UnitType.PLANE

    def test_can_fly(self):
        assert Plane.FLY is True

    def test_is_scout(self):
        assert Plane.SCOUT is True

    def test_water_affinity(self):
        assert Plane.WATER_AFFINITY is True

    def test_max_distance_10(self):
        assert Plane.MAX_DISTANCE == 10


class TestBoatStats:
    def test_unit_type(self, boat):
        assert boat.unit_type == UnitType.BOAT

    def test_water_affinity(self):
        assert Boat.WATER_AFFINITY is True

    def test_no_land_affinity(self):
        assert Boat.LAND_AFFINITY is False


#  Initialisation & compteur

class TestUnitInit:
    def test_id_starts_at_1_after_reset(self):
        u = Soldier(tile_id=0, owner=0)
        assert u.id == 1

    def test_ids_are_unique(self):
        u1 = Soldier(tile_id=0, owner=0)
        u2 = Soldier(tile_id=0, owner=0)
        assert u1.id != u2.id

    def test_counter_increments(self):
        u1 = Soldier(tile_id=0, owner=0)
        u2 = Cavalry(tile_id=0, owner=0)
        assert u2.id == u1.id + 1

    def test_tile_id_set(self):
        u = Soldier(tile_id=42, owner=0)
        assert u.tile_id == 42

    def test_owner_set(self):
        u = Soldier(tile_id=0, owner=3)
        assert u.owner == 3

    def test_hp_equals_base_hp(self, soldier):
        assert soldier.hp == Soldier.BASE_HP

    def test_has_not_moved_initially(self, soldier):
        assert soldier.has_moved is False

    def test_has_not_attacked_initially(self, soldier):
        assert soldier.has_attacked is False

    def test_can_dash_set_from_class(self, cavalry):
        assert cavalry.can_dash is True

    def test_upkeep_cost_set(self, soldier):
        assert soldier.upkeep_cost == Soldier.UPKEEP_COST

    def test_base_cost_set(self, soldier):
        assert soldier.base_cost == Soldier.BASE_COST


#  can_move

class TestCanMove:
    def test_fresh_unit_can_move(self, soldier):
        assert soldier.can_move() is True

    def test_cannot_move_after_has_moved(self, soldier):
        soldier.has_moved = True
        assert soldier.can_move() is False

    def test_can_still_move_after_attacking_without_escape(self, soldier):
        # Comportement réel : has_attacked seul ne bloque pas le mouvement.
        # Seul has_moved bloque. ESCAPE n'est utile que pour permettre de bouger
        # APRES une attaque ET un déplacement (cas non-standard).
        soldier.has_attacked = True
        assert soldier.can_move() is True

    def test_escape_can_move_after_attacking(self, cavalry):
        # Cavalry a ESCAPE=True : peut fuir même après avoir attaqué
        cavalry.has_attacked = True
        cavalry.has_moved = False
        assert cavalry.can_move() is True

    def test_escape_cannot_move_after_moving_and_attacking(self, cavalry):
        cavalry.has_moved = True
        cavalry.has_attacked = True
        assert cavalry.can_move() is False


#  unit_can_attack

class TestUnitCanAttack:
    def test_fresh_unit_can_attack(self, soldier):
        assert soldier.unit_can_attack() is True

    def test_cannot_attack_after_has_attacked(self, soldier):
        soldier.has_attacked = True
        assert soldier.unit_can_attack() is False


#  move_to_tile

class TestMoveToTile:
    def test_updates_tile_id(self, soldier):
        soldier.move_to_tile(5)
        assert soldier.tile_id == 5

    def test_sets_has_moved(self, soldier):
        soldier.move_to_tile(5)
        assert soldier.has_moved is True


#  reset_turn

class TestResetTurn:
    def test_clears_has_moved(self, soldier):
        soldier.has_moved = True
        soldier.reset_turn()
        assert soldier.has_moved is False

    def test_clears_has_attacked(self, soldier):
        soldier.has_attacked = True
        soldier.reset_turn()
        assert soldier.has_attacked is False

    def test_reset_allows_move_again(self, soldier):
        soldier.has_moved = True
        soldier.reset_turn()
        assert soldier.can_move() is True


#  get_opacity

class TestGetOpacity:
    def test_full_opacity_when_not_moved(self, soldier):
        assert soldier.get_opacity() == 1.0

    def test_half_opacity_when_moved(self, soldier):
        soldier.has_moved = True
        assert soldier.get_opacity() == 0.5


#  get_visibility_mask

class TestGetVisibilityMask:
    def test_non_scout_sees_own_tile(self, soldier):
        """Un soldat doit voir sa propre tuile."""
        map_ = make_linear_map(3)
        soldier.tile_id = 1
        mask = soldier.get_visibility_mask(map_)
        assert mask & (1 << 1)

    def test_non_scout_sees_neighbors(self, soldier):
        """Un soldat (non-scout) voit ses voisins immédiats."""
        map_ = make_linear_map(3)
        soldier.tile_id = 1
        mask = soldier.get_visibility_mask(map_)
        # tuiles 0 et 2 sont voisines de 1
        assert mask & (1 << 0)
        assert mask & (1 << 2)

    def test_scout_sees_two_hops(self, archer):
        """Un archer (SCOUT=True) voit jusqu'à 2 niveaux de voisins."""
        map_ = make_linear_map(5)
        archer.tile_id = 2
        mask = archer.get_visibility_mask(map_)
        # Avec 5 tuiles (0-4) et archer en 2, doit voir 0,1,2,3,4
        for i in range(5):
            assert mask & (1 << i), f"tuile {i} non visible par le scout"

    def test_mask_uses_bitmask(self, soldier):
        """Le masque de visibilité utilise bien des bits."""
        map_ = make_linear_map(3)
        soldier.tile_id = 0
        mask = soldier.get_visibility_mask(map_)
        assert isinstance(mask, int)
        assert mask > 0


#  UNIT_CLASS_MAP

class TestUnitClassMap:
    def test_all_types_present(self):
        for unit_type in UnitType:
            assert unit_type in UNIT_CLASS_MAP

    def test_factory_creates_correct_type(self):
        for unit_type, cls in UNIT_CLASS_MAP.items():
            u = cls(tile_id=0, owner=0)
            assert u.unit_type == unit_type


#  __repr__

class TestUnitRepr:
    def test_repr_contains_class_name(self, soldier):
        assert "Soldier" in repr(soldier)

    def test_repr_contains_id(self, soldier):
        assert str(soldier.id) in repr(soldier)

    def test_repr_contains_owner(self, soldier):
        assert "owner=0" in repr(soldier)
