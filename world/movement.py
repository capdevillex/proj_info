"""
Module de gestion du mouvement des unités.

Gère :
- Calcul des distances entre tuiles (Tchebychev)
- Détermination des zones accessibles pour une unité
- Validation et exécution des mouvements
- Toute la logique de mouvement est ici !
"""

from collections import deque
from world.unit import Unit
from world.map import Map
from world.tile import Tile


class MovementSystem:
    """
    Système centralisé de gestion des mouvements d'unités.
    
    Encapsule TOUTE la logique de mouvement :
    - Calcul des distances
    - Zones accessibles
    - Validation des mouvements
    - Exécution des mouvements
    """
    
    @staticmethod
    def chebyshev_distance_grid(map_: Map, start_tile_id: int, max_distance: int) -> dict:
        """
        Calcule la distance de Tchebychev de chaque tuile par rapport à start_tile_id.

        Distance de Tchebychev = max(|x1-x2|, |y1-y2|)
        C'est parfait pour les grilles avec mouvements diagonaux !

        Args:
            map_: L'objet Map
            start_tile_id: ID de la tuile de départ
            max_distance: Distance maximale à calculer

        Returns:
            dict: {tile_id: distance}
        """
        distances = {}
        start_tile = map_.tiles[start_tile_id]
        distances[start_tile_id] = 0
        queue = deque([start_tile_id])

        while queue:
            current_tile_id = queue.popleft()
            current_distance = distances[current_tile_id]

            # Si on a atteint la distance max, on arrête pour cette branche
            if current_distance >= max_distance:
                continue

            # Vérifier les tuiles voisines
            current_tile = map_.tiles[current_tile_id]
            for neighbor_tile_id in current_tile.neighbors:
                if neighbor_tile_id not in distances:
                    distances[neighbor_tile_id] = current_distance + 1
                    queue.append(neighbor_tile_id)

        return distances

    @staticmethod
    def get_reachable_tiles(map_: Map, unit: Unit) -> set:
        """
        Récupère toutes les tuiles accessibles pour une unité donnée.

        Args:
            map_: L'objet Map
            unit: L'unité à vérifier

        Returns:
            set: IDs des tuiles accessibles
        """
        if not unit.can_move():
            return set()

        distances = MovementSystem.chebyshev_distance_grid(map_, unit.tile_id, unit.max_distance)

        # Retourner toutes les tuiles à distance <= max_distance
        # on fait le tri des cases où on ne peut pas aller (eau/unité déjà présente)
        reachable = {
            tile_id
            for tile_id, distance in distances.items()
            if distance <= unit.max_distance
            and distance > 0
            and not map_.tiles[tile_id].has_units()
            and (unit.water_affinity or not map_.tiles[tile_id].is_water())
        }
        
        return reachable

    @staticmethod
    def execute_move(map_: Map, unit: Unit, target_tile_id: int) -> bool:
        """
        EXÉCUTE le mouvement d'une unité.
        
        Étapes :
        1. Vérifier que l'unité peut bouger
        2. Vérifier que la tuile cible est accessible
        3. Retirer l'unité de son ancienne tuile
        4. Ajouter l'unité à la nouvelle tuile
        5. Marquer l'unité comme ayant bougé
        
        Args:
            map_: L'objet Map
            unit: L'unité à déplacer
            target_tile_id: ID de la tuile de destination

        Returns:
            bool: True si le mouvement a réussi, False sinon
        """
        
        # Vérifier que l'unité peut bouger
        if not unit.can_move():
            print(f"❌ L'unité {unit.id} ne peut pas bouger ce tour")
            return False

        #  Retirer de l'ancienne tuile
        old_tile = map_.tiles[unit.tile_id]
        old_tile.remove_unit(unit)

        #Ajouter à la nouvelle tuile
        new_tile = map_.tiles[target_tile_id]
        new_tile.add_unit(unit)

        # Marquer comme ayant bougé
        unit.move_to_tile(target_tile_id)

        print(f"✅ Unité {unit.id} déplacée vers tuile {target_tile_id}")
        return True


# ============ RACCOURCIS POUR COMPATIBILITÉ =============
# Ces fonctions libres permettent d'appeler le système directement

def get_reachable_tiles(map_: Map, unit: Unit) -> set:
    """Raccourci pour MovementSystem.get_reachable_tiles()"""
    return MovementSystem.get_reachable_tiles(map_, unit)


def move_unit(map_: Map, unit: Unit, target_tile_id: int) -> bool:
    """Raccourci pour MovementSystem.execute_move()"""
    return MovementSystem.execute_move(map_, unit, target_tile_id)
