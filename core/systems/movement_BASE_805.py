"""
Module de gestion du mouvement des unités - AMÉLIORÉ AVEC DIJKSTRA.

Gère :
- Calcul des chemins optimaux avec coûts de déplacement variables (Dijkstra)
- Pénalités de mouvement basées sur le biome (montagne, forêt, etc.)
- Détermination des zones accessibles pour une unité
- Validation et exécution des mouvements
"""

import heapq
from collections import deque
from world.unit import Unit, UnitType
from world.map import Map
from world.tile import Tile
from world.biome import Biome


class Movement:
    """
    Système centralisé de gestion des mouvements d'unités.

    Utilise l'algorithme de Dijkstra pour respecter les coûts de déplacement variables.
    Supporte les pénalités de terrain (montagne coûte plus cher que plaine, etc.)
    """

    # Dictionnaire des coûts de mouvement par biome
    # Un coût de 1.0 = 1 point de mouvement normal
    # Un coût de 2.0 = terrain difficile (coûte 2 points)
    TERRAIN_COSTS = {
        Biome.BLANK: 1.0,  # Plaine vide = normal
        Biome.PLAIN: 1.0,  # Plaine = normal
        Biome.FOREST: 1.5,  # Forêt = un peu difficile
        Biome.MOUNTAIN: 2.0,  # Montagne = très difficile (coûte 2x)
        Biome.DESERT: 1.2,  # Désert = légèrement difficile
        Biome.WATER: float("inf"),  # Eau = non traversable par défaut
    }

    # Modifiants de coût spécifiques à chaque type d'unité
    # La cavalerie est rapide, les colons sont lents en montagne
    UNIT_TERRAIN_MODIFIERS = {
        UnitType.SOLDIER: {},  # Pas de modifiant spécial
        UnitType.CAVALRY: {  # La cavalerie adore les plaines
            Biome.PLAIN: 0.8,  # Plus rapide en plaine
            Biome.FOREST: 1.8,  # Très lente en forêt
            Biome.MOUNTAIN: 2.5,  # Très difficile en montagne
        },
        UnitType.ARCHER: {},  # Pareil que soldat
        UnitType.COLON: {  # Le colon traverse tout mais lentement
            Biome.MOUNTAIN: 1,
            Biome.FOREST: 1,
            Biome.WATER: 1,
            Biome.DESERT: 1,
        },
        UnitType.COLONIE: {},  # N'a pas de max_distance
        UnitType.BABY: {Biome.WATER: 2},  # Pareil que soldat
    }

    @staticmethod
    def get_movement_cost(biome: Biome, unit_type: UnitType) -> float:
        """
        Calcule le coût de mouvement pour une tuile donnée et un type d'unité.

        Args:
            biome: Type de biome de la tuile
            unit_type: Type d'unité se déplaçant

        Returns:
            float: Coût en points de mouvement (1.0 = normal, 2.0 = 2x plus cher)
        """
        # Coût de base du biome
        base_cost = Movement.TERRAIN_COSTS.get(biome, 1.0)

        # Appliquer le modifiant de l'unité si disponible
        modifiers = Movement.UNIT_TERRAIN_MODIFIERS.get(unit_type, {})
        if biome in modifiers:
            return modifiers[biome]

        return base_cost

    @staticmethod
    def dijkstra_reachable(
        map_: Map, start_tile_id: int, max_movement: float, unit_type: UnitType
    ) -> dict:
        """
        Utilise Dijkstra pour calculer toutes les tuiles accessibles avec des coûts variables.

        Retourne aussi la distance de mouvement consommée pour atteindre chaque tuile.

        Args:
            map_: L'objet Map
            start_tile_id: ID de la tuile de départ
            max_movement: Points de mouvement disponibles
            unit_type: Type d'unité pour calculer les coûts

        Returns:
            dict: {tile_id: mouvement_consommé}
        """
        # heap = [(coût_total, tile_id)]
        heap = [(0, start_tile_id)]
        distances = {start_tile_id: 0}
        visited = set()

        while heap:
            current_cost, current_tile_id = heapq.heappop(heap)

            # Si déjà visité, skip
            if current_tile_id in visited:
                continue
            visited.add(current_tile_id)

            # Si on dépasse le mouvement max, on arrête cette branche
            if current_cost > max_movement:
                continue

            # Vérifier les voisins
            current_tile = map_.tiles[current_tile_id]
            for neighbor_tile_id in current_tile.neighbors:
                if neighbor_tile_id in visited:
                    continue

                neighbor_tile = map_.tiles[neighbor_tile_id]

                # Calcul du coût pour se déplacer vers ce voisin
                terrain_cost = Movement.get_movement_cost(neighbor_tile.biome, unit_type)

                # Si le terrain est intraversable, skip
                if terrain_cost == float("inf"):
                    continue

                new_cost = current_cost + terrain_cost

                # Si on a trouvé un chemin meilleur, on l'ajoute
                if neighbor_tile_id not in distances or new_cost < distances[neighbor_tile_id]:
                    distances[neighbor_tile_id] = new_cost
                    heapq.heappush(heap, (new_cost, neighbor_tile_id))

        return distances

    @staticmethod
    def get_reachable_tiles(map_: Map, unit: Unit) -> set:
        """
        Récupère toutes les tuiles accessibles pour une unité donnée.

        Utilise maintenant Dijkstra pour respecter les coûts de terrain !

        Args:
            map_: L'objet Map
            unit: L'unité à vérifier

        Returns:
            set: IDs des tuiles accessibles
        """
        if not unit.can_move():
            return set()

        # Utiliser Dijkstra au lieu du BFS simple
        distances = Movement.dijkstra_reachable(
            map_, unit.tile_id, unit.max_distance, unit.unit_type
        )

        # Retourner toutes les tuiles accessibles
        reachable = set()
        for tile_id, movement_cost in distances.items():
            # On exclut la tuile de départ (distance > 0)
            if movement_cost == 0:
                continue

            # On ne dépasse pas le mouvement max
            if movement_cost > unit.max_distance:
                continue

            tile = map_.tiles[tile_id]

            # On ne peut pas aller sur une tuile avec une unité
            if tile.has_units():
                continue

            # On respecte l'affinité avec l'eau
            if not unit.water_affinity and tile.is_water():
                continue

            reachable.add(tile_id)

        return reachable

    @staticmethod
    def get_path_to_tile(map_: Map, unit: Unit, target_tile_id: int) -> list:
        """
        Calcule le chemin optimal (plus court) pour aller d'une unité à une tuile cible.

        Args:
            map_: L'objet Map
            unit: L'unité qui se déplace
            target_tile_id: ID de la tuile cible

        Returns:
            list: Liste des IDs des tuiles du chemin [start, ..., target]
                  ou liste vide si pas de chemin
        """
        if not unit.can_move():
            return []

        # BFS simple pour trouver le chemin
        queue = deque([(unit.tile_id, [unit.tile_id])])
        visited = {unit.tile_id}

        while queue:
            current_tile_id, path = queue.popleft()

            if current_tile_id == target_tile_id:
                return path

            # Vérifier les voisins
            current_tile = map_.tiles[current_tile_id]
            for neighbor_tile_id in current_tile.neighbors:
                if neighbor_tile_id not in visited:
                    visited.add(neighbor_tile_id)
                    new_path = path + [neighbor_tile_id]
                    queue.append((neighbor_tile_id, new_path))

        return []  # Pas de chemin trouvé

    @staticmethod
    def calculate_movement_cost_to_tile(map_: Map, unit: Unit, target_tile_id: int) -> float:
        """
        Calcule le coût total en points de mouvement pour atteindre une tuile cible.

        Utilise le chemin optimal.

        Args:
            map_: L'objet Map
            unit: L'unité
            target_tile_id: ID de la tuile cible

        Returns:
            float: Coût en points de mouvement, ou -1 si pas accessible
        """
        distances = Movement.dijkstra_reachable(
            map_, unit.tile_id, unit.max_distance, unit.unit_type
        )

        if target_tile_id in distances:
            return distances[target_tile_id]
        return -1

   
    @staticmethod
    def get_attackable_tiles(map_: Map, unit: Unit) -> set:
        if unit.attack_range == 0:
            return set()

        attackable = set()

        # BFS par nombre de cases (hops), pas par coût de terrain
        visited = {unit.tile_id}
        frontier = {unit.tile_id}

        for _ in range(unit.attack_range):
            next_frontier = set()
            for tile_id in frontier:
                tile = map_.tiles[tile_id]
                for neighbor_id in tile.neighbors:
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        next_frontier.add(neighbor_id)
            frontier = next_frontier

        # Parmi toutes les cases à portée, garder celles avec une unité ennemie
        for tile_id in visited:
            if tile_id == unit.tile_id:
                continue
            tile = map_.tiles[tile_id]
            if tile.has_units():
                for enemy in tile.units:
                    if enemy.owner != unit.owner:
                        attackable.add(tile_id)
                        break

        return attackable

    @staticmethod
    def get_tiles_in_range(map_: Map, tile_id: int, range_: int) -> set:
        """
        Récupère toutes les tuiles dans un certain rayon autour d'une tuile.
        Utile pour calculer les zones d'effet ou les portées d'attaque.

        Args:
            map_: L'objet Map
            tile_id: ID de la tuile centrale
            range_: Portée (distance max)

        Returns:
            set: IDs des tuiles dans le rayon
        """
        tiles_in_range = set()
        queue = deque([(tile_id, 0)])
        visited = {tile_id}

        while queue:
            current_tile_id, current_distance = queue.popleft()

            if current_distance > 0:  # Exclure la tuile de départ
                tiles_in_range.add(current_tile_id)

            if current_distance < range_:
                current_tile = map_.tiles[current_tile_id]
                for neighbor_tile_id in current_tile.neighbors:
                    if neighbor_tile_id not in visited:
                        visited.add(neighbor_tile_id)
                        queue.append((neighbor_tile_id, current_distance + 1))

        return tiles_in_range

    @staticmethod
    def execute_move(map_: Map, unit: Unit, target_tile_id):
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

        # Vérifier que la nouvelle tuile est accessible
        if target_tile_id not in Movement.get_reachable_tiles(map_, unit):
            print(f"❌ La tuile {target_tile_id} n'est pas accessible pour l'unité {unit.id}")
            return False

        # Retirer de l'ancienne tuile
        old_tile = map_.tiles[unit.tile_id]
        old_tile.remove_unit(unit)

        # Ajouter à la nouvelle tuile
        new_tile = map_.tiles[target_tile_id]
        new_tile.add_unit(unit)

        # Marquer comme ayant bougé
        unit.move_to_tile(target_tile_id)

        return True
