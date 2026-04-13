"""
Module de gestion du mouvement des unités.

Gère :
- Calcul des distances entre tuiles (Tchebychev)
- Détermination des zones accessibles pour une unité
- Validation des mouvements
"""

from world.map import Map
from world.unit import Unit


def chebyshev_distance_grid(map_, start_tile_id, max_distance):
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

    # On va utiliser une approche BFS (parcours en largeur)
    # pour calculer les distances correctement
    from collections import deque

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


def get_reachable_tiles(map_: Map, unit: Unit):
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

    distances = chebyshev_distance_grid(map_, unit.tile_id, unit.max_distance)

    # Retourner toutes les tuiles à distance <= max_distance
    reachable = {
        tile_id
        for tile_id, distance in distances.items()
        if distance <= unit.max_distance
        and distance > 0
        and not map_.tiles[tile_id].has_units()
        and (unit.water_affinity or not map_.tiles[tile_id].is_water())
    }

    return reachable


def is_tile_reachable(map_, unit, target_tile_id):
    """
    Vérifie si une tuile est accessible pour une unité.

    Args:
        map_: L'objet Map
        unit: L'unité
        target_tile_id: ID de la tuile cible

    Returns:
        bool: True si accessible
    """
    if not unit.can_move():
        return False

    distances = chebyshev_distance_grid(map_, unit.tile_id, unit.max_distance)
    distance = distances.get(target_tile_id, float("inf"))

    return 0 < distance <= unit.max_distance
