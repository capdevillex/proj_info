"""Tests unitaires pour core/systems/combat.py

NOTE sur le bug détecté (execute_attack, ligne ~194) :
    `defender_killed = damage >= defender.hp < 0`
    est une chaîne de comparaison Python signifiant :
        damage >= defender.hp ET defender.hp < 0
    Cela ne retourne True que si les HP sont négatifs ET que les dégâts >= HP,
    ce qui est presque toujours faux. La valeur correcte est `defender.hp <= 0`.
    Le test `test_execute_attack_killed_flag_bug` documente ce comportement incorrect.
"""
import pytest
from world.unit import UnitType, Soldier, Cavalry, Archer, Colon, Baby
from world.biome import Biome
from core.systems.combat import Combat
from helpers import make_tile, make_linear_map, MockMap, MockGameState


@pytest.fixture
def combat():
    return Combat()


def make_state_with_units(attacker, defender):
    """Crée un MockGameState avec deux tuiles : attaquant en 0, défenseur en 1."""
    tiles = {
        0: make_tile(0, biome=Biome.PLAIN),
        1: make_tile(1, biome=Biome.PLAIN),
    }
    tiles[0].neighbors.add(1)
    tiles[1].neighbors.add(0)
    map_ = MockMap(tiles)
    tiles[0].add_unit(attacker)
    tiles[1].add_unit(defender)
    state = MockGameState(map_)
    return state


#  Triangle d'efficacité

class TestEffectivenessTable:
    def test_soldier_vs_cavalry_advantage(self):
        eff = Combat.EFFECTIVENESS
        assert eff[UnitType.SOLDIER][UnitType.CAVALRY] == 1.5

    def test_soldier_vs_archer_disadvantage(self):
        assert Combat.EFFECTIVENESS[UnitType.SOLDIER][UnitType.ARCHER] == 0.7

    def test_cavalry_vs_archer_advantage(self):
        assert Combat.EFFECTIVENESS[UnitType.CAVALRY][UnitType.ARCHER] == 1.5

    def test_cavalry_vs_soldier_disadvantage(self):
        assert Combat.EFFECTIVENESS[UnitType.CAVALRY][UnitType.SOLDIER] == 0.7

    def test_archer_vs_soldier_advantage(self):
        assert Combat.EFFECTIVENESS[UnitType.ARCHER][UnitType.SOLDIER] == 1.5

    def test_archer_vs_cavalry_disadvantage(self):
        assert Combat.EFFECTIVENESS[UnitType.ARCHER][UnitType.CAVALRY] == 0.7


#  compute_damage

class TestComputeDamage:
    def test_damage_is_positive_soldier_vs_colon(self, combat):
        atk = Soldier(tile_id=0, owner=0)
        dfn = Colon(tile_id=1, owner=1)
        state = make_state_with_units(atk, dfn)
        dmg = combat.compute_damage(state, atk, dfn)
        # Soldier BASE_ATTACK=9999, Colon BASE_DEFENSE=3, terrain=1.0, hp_ratio=1.0
        # damage = (9999 - 3*1.0) * 1.0 * 1.0 = 9996
        assert dmg == pytest.approx(9996.0)

    def test_type_advantage_increases_damage(self, combat):
        """Soldat vs Cavalerie : modificateur 1.5 doit augmenter les dégâts."""
        atk = Soldier(tile_id=0, owner=0)
        atk_type = atk.unit_type  # SOLDIER
        dfn = Cavalry(tile_id=1, owner=1)

        state = make_state_with_units(atk, dfn)
        base_dmg = combat.compute_damage(state, atk, dfn)

        # Vérifie que le modificateur de type est appliqué
        expected_modifier = Combat.EFFECTIVENESS[atk_type].get(dfn.unit_type, 1.0)
        assert expected_modifier == 1.5
        # Les dégâts doivent être supérieurs à ceux sans modificateur
        no_mod_dmg = (Soldier.BASE_ATTACK - Cavalry.BASE_DEFENSE * 1.0) * 1.0 * 1.0
        assert base_dmg == pytest.approx(no_mod_dmg * 1.5)

    def test_type_disadvantage_reduces_damage(self, combat):
        """Soldat vs Archer : modificateur 0.7 doit réduire les dégâts."""
        atk = Soldier(tile_id=0, owner=0)
        dfn = Archer(tile_id=1, owner=1)
        state = make_state_with_units(atk, dfn)
        dmg = combat.compute_damage(state, atk, dfn)
        no_mod_dmg = (Soldier.BASE_ATTACK - Archer.BASE_DEFENSE * 1.0) * 1.0 * 1.0
        assert dmg == pytest.approx(no_mod_dmg * 0.7)

    def test_forest_defense_modifier(self, combat):
        """La forêt donne +30% de défense au défenseur."""
        atk = Cavalry(tile_id=0, owner=0)
        dfn = Soldier(tile_id=1, owner=1)
        tiles = {
            0: make_tile(0, biome=Biome.PLAIN),
            1: make_tile(1, biome=Biome.FOREST),
        }
        tiles[0].neighbors.add(1)
        tiles[1].neighbors.add(0)
        state = MockGameState(MockMap(tiles))
        tiles[0].add_unit(atk)
        tiles[1].add_unit(dfn)

        plain_dmg_formula = Cavalry.BASE_ATTACK - Soldier.BASE_DEFENSE * 1.0
        forest_dmg_formula = Cavalry.BASE_ATTACK - Soldier.BASE_DEFENSE * 1.3
        dmg = combat.compute_damage(state, atk, dfn)
        # modificateur Cavalry vs Soldier = 0.7, hp=1.0
        assert dmg == pytest.approx(forest_dmg_formula * 0.7)

    def test_mountain_defense_modifier(self, combat):
        """La montagne donne +50% de défense."""
        atk = Cavalry(tile_id=0, owner=0)
        dfn = Archer(tile_id=1, owner=1)
        tiles = {
            0: make_tile(0, biome=Biome.PLAIN),
            1: make_tile(1, biome=Biome.MOUNTAIN),
        }
        tiles[0].neighbors.add(1)
        tiles[1].neighbors.add(0)
        state = MockGameState(MockMap(tiles))
        tiles[0].add_unit(atk)
        tiles[1].add_unit(dfn)

        dmg = combat.compute_damage(state, atk, dfn)
        expected = (Cavalry.BASE_ATTACK - Archer.BASE_DEFENSE * 1.5) * 1.5 * 1.0
        assert dmg == pytest.approx(expected)

    def test_low_hp_reduces_damage(self, combat):
        """Un attaquant à 50% HP fait moins de dégâts."""
        atk = Baby(tile_id=0, owner=0)
        dfn = Colon(tile_id=1, owner=1)
        atk.hp = atk.BASE_HP // 2  # 50% HP
        state = make_state_with_units(atk, dfn)
        dmg = combat.compute_damage(state, atk, dfn)
        full_dmg_formula = (Baby.BASE_ATTACK - Colon.BASE_DEFENSE * 1.0) * 1.0 * 1.0
        assert dmg == pytest.approx(full_dmg_formula * 0.5)

    def test_full_hp_ratio_is_1(self, combat):
        atk = Baby(tile_id=0, owner=0)
        dfn = Colon(tile_id=1, owner=1)
        state = make_state_with_units(atk, dfn)
        dmg = combat.compute_damage(state, atk, dfn)
        expected = (Baby.BASE_ATTACK - Colon.BASE_DEFENSE * 1.0) * 1.0
        assert dmg == pytest.approx(expected)

    def test_neutral_matchup_modifier_is_1(self, combat):
        """Baby vs Colon : aucun modificateur de type (défaut 1.0)."""
        atk = Baby(tile_id=0, owner=0)
        dfn = Colon(tile_id=1, owner=1)
        state = make_state_with_units(atk, dfn)
        dmg = combat.compute_damage(state, atk, dfn)
        expected = (Baby.BASE_ATTACK - Colon.BASE_DEFENSE) * 1.0 * 1.0
        assert dmg == pytest.approx(expected)


#  can_attack

class TestCanAttack:
    def test_allied_cannot_attack(self, combat):
        atk = Soldier(tile_id=0, owner=0)
        dfn = Soldier(tile_id=1, owner=0)  # même propriétaire
        state = make_state_with_units(atk, dfn)
        assert combat.can_attack(state, atk, dfn) is False

    def test_already_attacked_cannot_attack(self, combat):
        atk = Soldier(tile_id=0, owner=0)
        dfn = Soldier(tile_id=1, owner=1)
        atk.has_attacked = True
        state = make_state_with_units(atk, dfn)
        assert combat.can_attack(state, atk, dfn) is False

    def test_target_out_of_range_returns_false(self, combat):
        # Soldat a portée 1 ; défenseur à 2 hops
        tiles = {i: make_tile(i) for i in range(4)}
        for i in range(3):
            tiles[i].neighbors.add(i + 1)
            tiles[i + 1].neighbors.add(i)
        map_ = MockMap(tiles)
        atk = Soldier(tile_id=0, owner=0)
        dfn = Soldier(tile_id=2, owner=1)
        tiles[0].add_unit(atk)
        tiles[2].add_unit(dfn)
        state = MockGameState(map_)
        assert combat.can_attack(state, atk, dfn) is False

    def test_valid_attack_returns_true(self, combat):
        atk = Soldier(tile_id=0, owner=0)
        dfn = Soldier(tile_id=1, owner=1)
        state = make_state_with_units(atk, dfn)
        assert combat.can_attack(state, atk, dfn) is True

    def test_cavalry_after_move_can_attack(self, combat):
        """La cavalerie avec DASH peut attaquer même après s'être déplacée."""
        atk = Cavalry(tile_id=0, owner=0)
        dfn = Soldier(tile_id=1, owner=1)
        atk.has_moved = True  # a déjà bougé
        state = make_state_with_units(atk, dfn)
        assert combat.can_attack(state, atk, dfn) is True


#  resolve

class TestResolve:
    def test_damage_applied_to_defender(self, combat):
        atk = Baby(tile_id=0, owner=0)
        dfn = Colon(tile_id=1, owner=1)
        state = make_state_with_units(atk, dfn)
        initial_hp = dfn.hp
        combat.resolve(state, atk, dfn)
        assert dfn.hp < initial_hp

    def test_has_attacked_set_after_resolve(self, combat):
        atk = Soldier(tile_id=0, owner=0)
        dfn = Colon(tile_id=1, owner=1)
        state = make_state_with_units(atk, dfn)
        combat.resolve(state, atk, dfn)
        assert atk.has_attacked is True

    def test_has_moved_set_for_non_escape_unit(self, combat):
        """Un soldat (pas ESCAPE) doit aussi être marqué has_moved après une attaque."""
        atk = Soldier(tile_id=0, owner=0)
        dfn = Colon(tile_id=1, owner=1)
        state = make_state_with_units(atk, dfn)
        combat.resolve(state, atk, dfn)
        assert atk.has_moved is True

    def test_escape_unit_move_not_consumed(self, combat):
        """Une unité avec ESCAPE ne doit pas avoir has_moved après avoir attaqué."""
        atk = Cavalry(tile_id=0, owner=0)
        dfn = Colon(tile_id=1, owner=1)
        state = make_state_with_units(atk, dfn)
        combat.resolve(state, atk, dfn)
        assert atk.has_moved is False

    def test_defender_killed_flag_when_lethal(self, combat):
        """Si les dégâts tuent le défenseur, defender_killed doit être True."""
        atk = Soldier(tile_id=0, owner=0)
        dfn = Colon(tile_id=1, owner=1)
        dfn.hp = 1  # presque mort
        state = make_state_with_units(atk, dfn)
        result = combat.resolve(state, atk, dfn)
        assert result["defender_killed"] is True

    def test_defender_not_killed_flag(self, combat):
        """Défenseur avec beaucoup de HP ne doit pas être marqué tué."""
        atk = Baby(tile_id=0, owner=0)
        dfn = Soldier(tile_id=1, owner=1)
        dfn.hp = 9999
        state = make_state_with_units(atk, dfn)
        result = combat.resolve(state, atk, dfn)
        assert result["defender_killed"] is False

    def test_result_contains_damage_key(self, combat):
        atk = Baby(tile_id=0, owner=0)
        dfn = Colon(tile_id=1, owner=1)
        state = make_state_with_units(atk, dfn)
        result = combat.resolve(state, atk, dfn)
        assert "damage" in result
        assert result["damage"] > 0


#  execute_attack

class TestExecuteAttack:
    def test_no_unit_on_target_tile(self, combat):
        tiles = {
            0: make_tile(0),
            1: make_tile(1),
        }
        tiles[0].neighbors.add(1)
        tiles[1].neighbors.add(0)
        map_ = MockMap(tiles)
        atk = Soldier(tile_id=0, owner=0)
        tiles[0].add_unit(atk)
        state = MockGameState(map_)
        result = combat.execute_attack(state, atk, 1)
        assert result["success"] is False

    def test_target_out_of_range(self, combat):
        map_ = make_linear_map(4)
        atk = Soldier(tile_id=0, owner=0)
        dfn = Soldier(tile_id=3, owner=1)
        map_.tiles[0].add_unit(atk)
        map_.tiles[3].add_unit(dfn)
        state = MockGameState(map_)
        result = combat.execute_attack(state, atk, 3)
        assert result["success"] is False

    def test_valid_attack_success(self, combat):
        atk = Soldier(tile_id=0, owner=0)
        dfn = Colon(tile_id=1, owner=1)
        state = make_state_with_units(atk, dfn)
        result = combat.execute_attack(state, atk, 1)
        assert result["success"] is True
        assert result["damage"] > 0

    def test_execute_attack_killed_flag_bug(self, combat):
        """
        Documente le bug dans execute_attack ligne ~194 :
            defender_killed = damage >= defender.hp < 0
        C'est une chaîne Python : (damage >= defender.hp) AND (defender.hp < 0).
        Le bug se manifeste quand les HP tombent EXACTEMENT à 0 après resolve() :
            damage=2, defender.hp avant=2 → hp après=0
            → 2 >= 0 = True, mais 0 < 0 = False → defender_killed = False  (BUG)
        La valeur correcte serait True (defender.hp <= 0).
        """
        # Baby vs Colon sur terrain neutre : damage = (5 - 3) * 1.0 = 2.0
        atk = Baby(tile_id=0, owner=0)
        dfn = Colon(tile_id=1, owner=1)
        dfn.hp = 2  # exactement la valeur des dégâts → hp tombera à 0
        state = make_state_with_units(atk, dfn)
        result = combat.execute_attack(state, atk, 1)
        # Après le combat, dfn.hp == 0 → le défenseur devrait être mort
        assert dfn.hp == 0
        # Le bug : defender_killed est False alors que hp == 0
        assert result["defender_killed"] is False, (
            "Bug confirmé : `damage >= defender.hp < 0` retourne False "
            "quand hp == 0 exactement au lieu de True. "
            "Corriger en : defender_killed = defender.hp <= 0"
        )
