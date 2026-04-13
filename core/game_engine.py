from typing import List, Dict, Optional, Any

from core.game_state import GameState
from core.systems import Movement, Combat, Economy, Visibility
from world.unit import Unit, UnitType
from world.map import Map
from world.biome import Biome
from core.systems.movement import Movement  # ✨ Importer le système centralisé


class GameEngine:
    """
    Moteur de jeu central pour le 4X.

    Gère toutes les interactions entre les systèmes (mouvement, combat, économie, visibilité)
    et maintient la cohérence de l'état du jeu.
    """

    def __init__(self, game_state: GameState):
        self.state = game_state

        # Systèmes de jeu
        self.movement = Movement  # ✨ Utiliser le système centralisé
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

        ✨ MAINTENANT : Juste un wrapper qui appelle MovementSystem !

        Args:
            unit: L'unité à déplacer
            target_tile_id: ID de la tuile de destination

        Returns:
            True si le mouvement a réussi, False sinon
        """
        # ✨ Utiliser le système centralisé
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

        Args:
            attacker: L'unité attaquante
            defender: L'unité défenseur

        Returns:
            True si le défenseur est détruit, False sinon
        """
        result = self.combat.resolve(self.state, attacker, defender)

        # Si le défenseur est mort, le retirer du jeu
        if result.get("defender_killed", False):
            self.remove_unit(defender)
            return True

        return False

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

        # Afficher les ressources
        print(
            f"Ressources : Or={self.state.resources['gold']}, "
            f"Nourriture={self.state.resources['food']}, "
            f"Production={self.state.resources['production']}"
        )

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

    # ========== GESTION DES VILLES (PHASE 1) ==========

    def found_city(self, colon_unit: Unit, city_name: str) -> bool:
        """
        Fonde une ville à l'emplacement d'un colon.

        Args:
            colon_unit: L'unité colon qui fonde la ville
            city_name: Nom de la ville (optionnel)

        Returns:
            True si la ville a été fondée, False sinon
        """
        # Vérifier que c'est bien un colon
        if colon_unit.unit_type != UnitType.COLON:
            print(f"❌ Seul un colon peut fonder une ville")
            return False

        # TODO: Implémenter la création de ville (Phase 1)
        # - Créer l'objet City
        # - Retirer le colon
        # - Ajouter la ville à l'état du jeu

        print(f"⚠️ Fondation de ville pas encore implémentée (Phase 1)")
        return False

    # ========== UTILITAIRES ==========

    def get_unit_by_id(self, unit_id: int) -> Optional[Unit]:
        """
        Trouve une unité par son ID.

        Args:
            unit_id: ID de l'unité recherchée

        Returns:
            L'unité trouvée, ou None
        """
        for unit in self.state.units:
            if unit.id == unit_id:
                return unit
        return None

    def get_units_on_tile(self, tile_id: int) -> List[Unit]:
        """
        Récupère toutes les unités sur une tuile.

        Args:
            tile_id: ID de la tuile

        Returns:
            Liste des unités sur la tuile
        """
        tile = self.state.map.tiles.get(tile_id)
        if tile:
            return tile.get_units()
        return []

    def get_player_units(self, player_id: int) -> List[Unit]:
        """
        Récupère toutes les unités d'un joueur.

        Args:
            player_id: ID du joueur

        Returns:
            Liste des unités du joueur
        """
        return [unit for unit in self.state.units if unit.owner == player_id]

    def get_game_stats(self) -> Dict[str, Any]:
        """
        Retourne des statistiques sur l'état actuel du jeu.

        Returns:
            Dictionnaire avec les statistiques
        """
        stats = {
            "turn": self.state.turn,
            "total_units": len(self.state.units),
            "total_cities": len(self.state.cities),
            "resources": self.state.resources.copy(),
            "units_by_player": {},
            "units_by_type": {},
        }

        # Compter les unités par joueur
        for unit in self.state.units:
            stats["units_by_player"][unit.owner] = stats["units_by_player"].get(unit.owner, 0) + 1
            stats["units_by_type"][unit.unit_type.name] = (
                stats["units_by_type"].get(unit.unit_type.name, 0) + 1
            )

        return stats
