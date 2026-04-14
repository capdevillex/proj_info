from typing import List, Dict, Optional, Any

from core.game_state import GameState
from core.systems import Movement, Combat, Economy, Visibility
from world.unit import Unit, UnitType
from world.city import City
from world.map import Map
from world.biome import Biome
from core.systems.movement import Movement  # Importer le système centralisé


class GameEngine:
    """
    Moteur de jeu central pour le 4X.

    Gère toutes les interactions entre les systèmes (mouvement, combat, économie, visibilité)
    et maintient la cohérence de l'état du jeu.
    """

    def __init__(self, game_state: GameState):
        self.state = game_state

        # Systèmes de jeu
        self.movement = Movement  # Utiliser le système centralisé
        self.combat = Combat()
        self.economy = Economy()
        self.visibility = Visibility()

    # ========== GESTION DES UNITÉS ==========

    def spawn_unit(
        self, unit_type: UnitType, tile_id: int, owner: int = 0, water_affinity: bool = False
    ) -> Optional[Unit]:
        """
        Place une nouvelle unité du type spécifié sur la tuile donnée.

        Args:
            unit_type: Type d'unité à créer
            tile_id: ID de la tuile où placer l'unité
            owner: Propriétaire de l'unité (joueur)
            water_affinity: Si l'unité peut se déplacer sur l'eau

        Returns:
            L'unité créée, ou None si le placement est impossible
        """
        tile = self.state.map.tiles.get(tile_id)

        if not tile:
            print(f"❌ Tuile {tile_id} inexistante")
            return None

        # Vérifier si la tuile est occupée
        if tile.has_units():
            print(f"❌ La tuile {tile_id} a déjà une unité")
            return None

        # Vérifier si l'unité peut être placée sur l'eau
        if tile.biome == Biome.WATER and not water_affinity:
            print(f"❌ Impossible de placer une unité terrestre sur l'eau (tuile {tile_id})")
            return None

        # Créer l'unité
        new_unit = Unit(
            tile_id=tile_id, unit_type=unit_type, owner=owner, water_affinity=water_affinity
        )

        # Ajouter l'unité à la tuile et à l'état du jeu
        tile.add_unit(new_unit)
        self.state.units.append(new_unit)

        # Mettre à jour la visibilité
        self.visibility.update(self.state)

        print(f"✅ Unité {unit_type.name} numéro {new_unit.id} créée sur tuile {tile_id}")
        return new_unit

    def move_unit(self, unit: Unit, target_tile_id: int) -> bool:
        """
        Déplace une unité vers une tuile cible.

        MAINTENANT : Juste un wrapper qui appelle MovementSystem !

        Args:
            unit: L'unité à déplacer
            target_tile_id: ID de la tuile de destination

        Returns:
            True si le mouvement a réussi, False sinon
        """
        # Utiliser le système centralisé
        success = self.movement.execute_move(self.state.map, unit, target_tile_id)

        if success:
            # Mettre à jour la visibilité après le mouvement
            self.visibility.update(self.state)

        return success

    def remove_unit(self, unit: Unit) -> bool:
        """
        Retire une unité du jeu (mort, destruction, etc.).

        Args:
            unit: L'unité à retirer

        Returns:
            True si l'unité a été retirée, False sinon
        """
        # Retirer de la tuile
        tile = self.state.map.tiles.get(unit.tile_id)
        if tile:
            tile.remove_unit(unit)

        # Retirer de la liste des unités
        if unit in self.state.units:
            self.state.units.remove(unit)
            self.visibility.update(self.state)
            print(f"✅ Unité {unit.id} retirée du jeu")
            return True

        return False

    # ========== GESTION DU COMBAT ==========

    def attack(self, attacker: Unit, defender: Unit) -> bool:
        """
        Résout un combat entre deux unités.

        Détruit le défenseur si ses dégâts dépassent un certain seuil.

        Args:
            attacker: L'unité attaquante
            defender: L'unité défenseur

        Returns:
            True si le défenseur est détruit, False sinon
        """
        # Vérifier que l'attaque est possible
        if not self.combat.can_attack(self.state, attacker, defender):
            print(f"❌ L'attaque n'est pas possible")
            return False

        result = self.combat.resolve(self.state, attacker, defender)
        damage = result.get("damage", 0)

        # Logique simple : si les dégâts dépassent un seuil, le défenseur meurt
        # On peut améliorer cela avec un système de HP réel
        DAMAGE_THRESHOLD_FOR_DEATH = 15  # À ajuster selon le game balance

        if damage >= DAMAGE_THRESHOLD_FOR_DEATH:
            print(f"💀 L'unité ennemie {defender.unit_type.name} est détruite !")
            self.remove_unit(defender)
            return True
        else:
            print(f"⚔️ L'unité ennemie {defender.unit_type.name} résiste à l'attaque !")
            return False

    def attack_unit(self, attacker: Unit, target_tile_id: int) -> bool:
        """
        Attaque une unité ennemie sur une tuile cible.

        À utiliser quand on clique sur une tuile rouge (attaquable).

        Args:
            attacker: L'unité attaquante
            target_tile_id: ID de la tuile contenant l'ennemie à attaquer

        Returns:
            True si l'attaque a réussi et l'ennemi est détruit, False sinon
        """
        # Vérifier que la tuile cible existe et a des unités
        target_tile = self.state.map.tiles.get(target_tile_id)
        if not target_tile or not target_tile.has_units():
            print(f"❌ Aucune unité sur la tuile {target_tile_id}")
            return False

        # Récupérer l'unité ennemie
        defender = target_tile.units[0]  # On attaque la première unité

        # Vérifier que c'est une unité ennemie
        if defender.owner == attacker.owner:
            print(f"❌ Impossible d'attaquer une unité alliée")
            return False

        # Vérifier que l'unité attaquante peut attaquer (portée correcte)
        from core.systems.movement import Movement

        attackable_tiles = Movement.get_attackable_tiles(self.state.map, attacker)
        if target_tile_id not in attackable_tiles:
            print(f"❌ La cible n'est pas à portée d'attaque")
            return False

        # Effectuer l'attaque
        return self.attack(attacker, defender)

    # ========== GESTION DES TOURS ==========

    def end_turn(self):
        """
        Termine le tour actuel et prépare le suivant.

        Actions effectuées :
        - Mise à jour de l'économie (ressources, entretien)
        - Réinitialisation des mouvements des unités
        - Incrémentation du compteur de tours
        - Mise à jour de la visibilité
        """
        print(f"\n{'='*50}")
        print(f"Fin du tour {self.state.turn}")
        print(f"{'='*50}")

        # Mettre à jour l'économie
        self.economy.update(self.state)

        # Réinitialiser le mouvement de toutes les unités
        for unit in self.state.units:
            unit.reset_movement()

        # Incrémenter le tour
        self.state.turn += 1

        # Mettre à jour la visibilité
        self.visibility.update(self.state)

        print(f"\n{'='*50}")
        print(f"Début du tour {self.state.turn}")
        print(f"{'='*50}\n")

    # ========== GESTION DES VILLES ==========

    def found_city(self, colon_unit: Unit, city_name: Optional[str] = None) -> bool:
        """
        Fonde une ville à l'emplacement d'un colon.

        Args:
            colon_unit: L'unité colon qui fonde la ville
            city_name: Nom de la ville (optionnel, généré automatiquement si None)

        Returns:
            True si la ville a été fondée, False sinon
        """
        # Vérifier que c'est bien un colon
        if colon_unit.unit_type != UnitType.COLON:
            print(f"❌ Seul un colon peut fonder une ville")
            return False

        # Vérifier que la tuile existe
        tile = self.state.map.tiles.get(colon_unit.tile_id)
        if not tile:
            print(f"❌ Tuile {colon_unit.tile_id} inexistante")
            return False

        # Vérifier qu'il n'y a pas déjà une ville sur cette tuile
        if self.state.get_city_at_tile(colon_unit.tile_id):
            print(f"❌ Il y a déjà une ville sur cette tuile")
            return False

        # Vérifier que la tuile n'est pas de l'eau
        if tile.is_water():
            print(f"❌ Impossible de fonder une ville sur l'eau")
            return False

        # Générer un nom de ville si non fourni
        if city_name is None:
            city_name = self._generate_city_name(colon_unit.owner)

        # Créer la ville
        new_city = City(name=city_name, owner=colon_unit.owner, center_tile_id=colon_unit.tile_id)

        # Ajouter la ville à l'état du jeu
        self.state.add_city(new_city)

        # Calculer la production initiale
        new_city.calculate_production(self.state.map)

        # Retirer le colon du jeu
        self.remove_unit(colon_unit)

        print(
            f"✅ Ville '{city_name}' fondée sur la tuile {colon_unit.tile_id} par le joueur {colon_unit.owner}"
        )

        return True

    def _generate_city_name(self, owner: int) -> str:
        """
        Génère un nom de ville automatiquement.

        Args:
            owner: ID du joueur propriétaire

        Returns:
            Nom de la ville
        """
        # Listes de noms de villes, je dois avouer avoir une inspiration limitée
        city_names = [
            "Nova",
            "Bourg Palette",
            "Arcadia",
            "Zenith",
            "Aurora",
            "Elysium",
            "Olympus",
            "Volucité",
            "Atlantis",
            "Avalon",
            "Carmin-sur-mer",
            "Camelot",
            "Eden",
            "Relifac-le-Haut",
            "Utopia",
            "Paradis",
            "Lavanville",
            "Harmonie",
            "Prospérité",
            "Liberté",
            "Féli-Cité",
            "Espoir",
            "Lumière",
            "Auffrac-les-Congères",
            "Victoire",
            "Gloire",
            "Honneur",
        ]

        # Récupérer les noms déjà utilisés
        used_names = {city.name for city in self.state.cities if city.owner == owner}

        # Trouver un nom disponible
        for name in city_names:
            if name not in used_names:
                return name

        # Si tous les noms sont pris, ajouter un numéro
        base_name = city_names[0]
        counter = 1
        while f"{base_name} {counter}" in used_names:
            counter += 1

        return f"{base_name} {counter}"
