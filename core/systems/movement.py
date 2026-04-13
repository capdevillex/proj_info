from world.movement import get_reachable_tiles
from world.biome import Biome


class Movement:
    """Système de gestion des mouvements des unités."""

    def move(self, state, unit, target_tile_id):
        """
        Déplace une unité vers une tuile cible.

        Args:
            state: L'état du jeu
            unit: L'unité à déplacer
            target_tile_id: ID de la tuile de destination

        Returns:
            True si le mouvement a réussi, False sinon
        """
        # Vérifier que la tuile cible existe
        target_tile = state.map.tiles.get(target_tile_id)
        if not target_tile:
            print(f"❌ Tuile {target_tile_id} inexistante")
            return False

        # Vérifier si le mouvement est valide
        if not self.is_valid_move(state, unit, target_tile_id):
            return False

        # Retirer l'unité de l'ancienne tuile
        old_tile = state.map.tiles.get(unit.tile_id)
        if old_tile:
            old_tile.remove_unit(unit)

        # Déplacer l'unité
        unit.move_to_tile(target_tile_id)

        # Ajouter l'unité à la nouvelle tuile
        target_tile.add_unit(unit)

        return True

    def is_valid_move(self, game_state, unit, target_tile_id):
        """
        Vérifie si le mouvement est valide.

        Args:
            game_state: L'état du jeu
            unit: L'unité qui veut se déplacer
            target_tile_id: ID de la tuile de destination

        Returns:
            True si le mouvement est valide, False sinon
        """
        # Vérifier que l'unité peut bouger
        if not unit.can_move():
            print(f"❌ L'unité {unit.id} a déjà bougé ce tour")
            return False

        # Vérifier que la tuile cible existe
        target_tile = game_state.map.tiles.get(target_tile_id)
        if not target_tile:
            return False

        # Vérifier que la tuile n'est pas déjà occupée
        if target_tile.has_units():
            print(f"❌ La tuile {target_tile_id} est déjà occupée")
            return False

        # Vérifier que l'unité peut aller sur l'eau si nécessaire
        if target_tile.biome == Biome.WATER and not unit.water_affinity:
            print(f"❌ L'unité ne peut pas aller sur l'eau")
            return False

        # Vérifier que la tuile est accessible (distance)
        reachable = get_reachable_tiles(game_state.map, unit)
        if target_tile_id not in reachable:
            print(f"❌ La tuile {target_tile_id} est trop loin (max: {unit.max_distance})")
            return False

        return True
