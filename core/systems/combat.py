from world.unit import UnitType, Soldier, Cavalry, Colon, Baby, Archer
from world.biome import Biome


class Combat:
    """Système de gestion des combats entre unités."""

    # Triangle d'acier : efficacité des unités les unes contre les autres
    EFFECTIVENESS = {
        UnitType.SOLDIER: {UnitType.CAVALRY: 1.5, UnitType.ARCHER: 0.7},  # Soldat > Cavalerie
        UnitType.ARCHER: {UnitType.SOLDIER: 1.5, UnitType.CAVALRY: 0.7},  # Archer > Soldat
        UnitType.CAVALRY: {UnitType.ARCHER: 1.5, UnitType.SOLDIER: 0.7},  # Cavalerie > Archer
        UnitType.BABY: {UnitType.ARCHER: 1.5, UnitType.SOLDIER: 1},
    }

    # Stats de base des unités
    BASE_STATS = {
                    UnitType.SOLDIER: {"attack": Soldier.BASE_ATTACK, "defense": Soldier.BASE_DEFENSE, "hp": Soldier.BASE_HP},
                    UnitType.CAVALRY: {"attack": Cavalry.BASE_ATTACK, "defense": Cavalry.BASE_DEFENSE, "hp": Cavalry.BASE_HP},
                    UnitType.ARCHER: {"attack": Archer.BASE_ATTACK, "defense": Archer.BASE_DEFENSE, "hp": Archer.BASE_HP},
                    UnitType.COLON: {"attack": Colon.BASE_ATTACK, "defense": Colon.BASE_DEFENSE, "hp": Colon.BASE_HP},
                    UnitType.BABY: {"attack": Baby.BASE_ATTACK, "defense": Baby.BASE_DEFENSE, "hp": Baby.BASE_HP}
                }

    # Modificateurs de terrain pour la défense
    TERRAIN_DEFENSE_MODIFIER = {
        Biome.FOREST: 1.3,  # +30% défense en forêt
        Biome.MOUNTAIN: 1.5,  # +50% défense en montagne
        Biome.PLAIN: 1.0,  # Neutre
        Biome.WATER: 0.8,  # -20% défense sur l'eau
        Biome.DESERT: 0.9,  # -10% défense dans le désert
    }

    def resolve(self, state, attacker, defender):
        """
        Résout un combat entre deux unités.

        Formule : damage = base_damage * attack / (attack + defense) * terrain_modifier * (HP / MaxHP)

        Args:
            state: L'état du jeu
            attacker: L'unité attaquante
            defender: L'unité défenseur

        Returns:
            Dictionnaire avec les résultats du combat
        """
        # Calculer les dégâts
        damage = self.compute_damage(state, attacker, defender)

        # Appliquer les dégâts (TODO: ajouter HP aux unités)
        defender.hp -= damage

        print(f"⚔️ Combat : {attacker.unit_type.name} attaque {defender.unit_type.name}")
        print(f"   Dégâts infligés : {damage:.1f}")

        result = {"damage": damage, "defender_killed": defender.hp <= 0}  # TODO: vérifier si defender.hp <= 0

        if defender.hp <= 0:
            print(f"   💀 {defender.unit_type.name} est détruit !")

        return result

    def compute_damage(self, state, attacker, defender):

        # Stats directement depuis les classes d'unités
        attack  = attacker.BASE_ATTACK
        defense = defender.BASE_DEFENSE

        # Modificateur de type (triangle d'or (non))
        type_modifier = self.EFFECTIVENESS.get(attacker.unit_type, {}).get(defender.unit_type, 1.0)

        # Modificateur de terrain (défenseur)
        defender_tile = state.map.tiles.get(defender.tile_id)
        terrain_modifier = self.TERRAIN_DEFENSE_MODIFIER.get(defender_tile.biome, 1.0) if defender_tile else 1.0

        # Modificateur de santé
        hp_ratio = attacker.hp / attacker.BASE_HP

        # Formule finale
        damage =(attack - defense * terrain_modifier) * type_modifier * hp_ratio

        return damage

    def can_attack(self, state, attacker, defender):
        """
        Vérifie si une unité peut attaquer une autre.

        Args:
            state: L'état du jeu
            attacker: L'unité attaquante
            defender: L'unité défenseur

        Returns:
            bool: True si l'attaque est possible
        """
        # Vérifier que les unités sont ennemies
        if attacker.owner == defender.owner:
            print(f"❌ Impossible d'attaquer une unité alliée")
            return False

        # Vérifier que l'attaquant peut bouger (pas encore implémenté pour l'attaque)
        # if not attacker.can_move():
        #     print(f"❌ L'unité {attacker.id} a déjà agi ce tour")
        #     return False

        # Vérifier que les unités sont adjacentes (TODO: implémenter portée d'attaque)
        attacker_tile = state.map.tiles.get(attacker.tile_id)
        if attacker_tile and defender.tile_id not in attacker_tile.neighbors:
            print(f"❌ La cible est trop loin")
            return False

        return True


    DAMAGE_THRESHOLD_FOR_DEATH = 15  # Constante à mettre ici, pas dans game_engine
    #mzethode de merde pour la vie du truc

    def execute_attack(self, state, attacker, target_tile_id):
        """
        Point d'entrée principal du combat.
        Trouve la cible, vérifie les conditions, calcule les dégâts,
        détermine si le défenseur est tué.

        Returns:
            dict avec :
                - "success": bool (l'attaque a eu lieu)
                - "defender": Unit | None
                - "defender_killed": bool
                - "damage": float
        """
        # Trouver le défenseur sur la tuile
        target_tile = state.map.tiles.get(target_tile_id)
        if not target_tile or not target_tile.has_units():
            print(f"❌ Aucune unité sur la tuile {target_tile_id}")
            return {"success": False, "defender": None, "defender_killed": False, "damage": 0}

        defender = target_tile.units[0]

        # Vérifier la portée via Movement (import local pour éviter le circulaire)
        from core.systems.movement import Movement
        attackable_tiles = Movement.get_attackable_tiles(state.map, attacker)
        if target_tile_id not in attackable_tiles:
            print(f"❌ La cible n'est pas à portée d'attaque")
            return {"success": False, "defender": None, "defender_killed": False, "damage": 0}

        # Vérifier les conditions d'attaque
        if not self.can_attack(state, attacker, defender):
            return {"success": False, "defender": None, "defender_killed": False, "damage": 0}

        # Résoudre le combat
        result = self.resolve(state, attacker, defender)
        damage = result.get("damage", 0)

        # Décider du sort du défenseur
        defender_killed = result.get("defender_killed", False)
        if defender_killed:
            print(f"💀 L'unité ennemie {defender.unit_type.name} est détruite !")
        else:
            print(f"⚔️ L'unité ennemie {defender.unit_type.name} résiste à l'attaque !")

        return {
            "success": True,
            "defender": defender,
            "defender_killed": defender_killed,
            "damage": damage,
        }
