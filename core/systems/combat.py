from world.unit import UnitType
from world.biome import Biome


class Combat:
    """Système de gestion des combats entre unités."""

    # Triangle d'acier : efficacité des unités les unes contre les autres
    EFFECTIVENESS = {
        UnitType.SOLDIER: {UnitType.CAVALRY: 1.5, UnitType.ARCHER: 0.7},  # Soldat > Cavalerie
        UnitType.ARCHER: {UnitType.SOLDIER: 1.5, UnitType.CAVALRY: 0.7},  # Archer > Soldat
        UnitType.CAVALRY: {UnitType.ARCHER: 1.5, UnitType.SOLDIER: 0.7},  # Cavalerie > Archer
        UnitType.BABY: {UnitType.ARCHER: 1.5, UnitType.SOLDIER: 0.7},
    }

    # Stats de base des unités
    BASE_STATS = {
        UnitType.SOLDIER: {"attack": 10, "defense": 8, "hp": 100},
        UnitType.CAVALRY: {"attack": 12, "defense": 6, "hp": 90},
        UnitType.ARCHER: {"attack": 8, "defense": 5, "hp": 70},
        UnitType.COLON: {"attack": 2, "defense": 3, "hp": 50},
        UnitType.BABY: {"attack": 5, "defense": 3, "hp": 50}
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
        # defender.hp -= damage

        print(f"⚔️ Combat : {attacker.unit_type.name} attaque {defender.unit_type.name}")
        print(f"   Dégâts infligés : {damage:.1f}")

        result = {"damage": damage, "defender_killed": False}  # TODO: vérifier si defender.hp <= 0

        # if defender.hp <= 0:
        #     result["defender_killed"] = True
        #     print(f"   💀 {defender.unit_type.name} est détruit !")

        return result

    def compute_damage(self, state, attacker, defender):
        """
        Calcule les dégâts infligés par l'attaquant au défenseur.

        Formule : damage = base_damage * attack / (attack + defense) * terrain_modifier * (HP / MaxHP)

        Args:
            state: L'état du jeu
            attacker: L'unité attaquante
            defender: L'unité défenseur

        Returns:
            float: Les dégâts infligés
        """
        # Récupérer les stats de base
        attacker_stats = self.BASE_STATS.get(
            attacker.unit_type, {"attack": 5, "defense": 5, "hp": 50}
        )
        defender_stats = self.BASE_STATS.get(
            defender.unit_type, {"attack": 5, "defense": 5, "hp": 50}
        )

        base_damage = 20  # Dégâts de base
        attack = attacker_stats["attack"]
        defense = defender_stats["defense"]

        # Modificateur de type (triangle d'acier)
        type_modifier = self.EFFECTIVENESS.get(attacker.unit_type, {}).get(defender.unit_type, 1.0)

        # Modificateur de terrain (défenseur)
        defender_tile = state.map.tiles.get(defender.tile_id)
        terrain_modifier = 1.0
        if defender_tile:
            terrain_modifier = self.TERRAIN_DEFENSE_MODIFIER.get(defender_tile.biome, 1.0)

        # Modificateur de santé (TODO: implémenter HP sur les unités)
        # Pour l'instant, on suppose que les unités sont à pleine santé
        hp_ratio = 1.0  # attacker.hp / attacker_stats["hp"]

        # Formule finale
        damage = (
            base_damage
            * (attack / (attack + defense * terrain_modifier))
            * type_modifier
            * hp_ratio
        )

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
