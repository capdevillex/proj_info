import random
from typing import Optional, Set, Dict

from click import Option
from cv2 import add
from regex import T
from torch import ne

from world.biome import Biome
from world.map import Map
from world.resources import Resource
from config import GameConfig as gc
from world.tile import Tile


class City:
    """
    Représente une ville sur la carte.

    Une ville possède un ensemble de tuiles adjacentes et produit des ressources
    chaque tour en fonction des tuiles qu'elle contrôle.

    Attributes:
        id (int): Identifiant unique de la ville.
        name (str): Nom de la ville.
        owner (int): ID du joueur propriétaire de la ville.
        tile_ids (Set[int]): Ensemble des IDs des tuiles contrôlées par la ville.
        center_tile_id (int): ID de la tuile centrale où se trouve la ville.
        production (Dict[str, float]): Production de ressources au tour courant.
    """

    _next_id = 0

    def __init__(self, name: str, owner: int, center_tile_id: int):
        self.id = City._next_id
        City._next_id += 1

        self.name = name
        self.owner = owner
        self.center_tile_id = center_tile_id
        self.tile_ids: Set[int] = {center_tile_id}
        self.population = 1  # population initiale de la ville
        self.constructions = (
            set()
        )  # constructions présentes dans la ville (ex: "farm", "mine", etc.)
        self.age = 0  # nombre de tours depuis la fondation de la ville

        # Production de ressources par tour
        self.production: Dict[str, int] = {
            "food": 1,
            "wood": 0,
            "stone": 0,
            "iron": 0,
            "gold": 1,
        }

    def _add_tile(self, tile_id: int):
        """
        Ajoute une tuile au territoire de la ville.

        Args:
            tile_id (int): ID de la tuile à ajouter
        """
        self.tile_ids.add(tile_id)

    def expend_territory(self, game_state) -> Optional[int]:
        """
        Étend le territoire de la ville en ajoutant une tuile voisine au hasard.

        Args:
            game_map (Map): La carte du jeu pour accéder aux tuiles
        """
        # les tuiles candidates sont les tuiles voisines des tuiles déjà contrôlées
        candidate_tiles = set()
        # bfs depuis la tuile centrale en stockant les disances pour ne pas dépasser le rayon d'extension
        visited = set()
        queue = [(self.center_tile_id, 0)]
        while queue:
            current_tile_id, distance = queue.pop(0)
            if distance > gc.CITY_EXTENSION_RADIUS:
                continue
            visited.add(current_tile_id)
            current_tile = game_state.map.tiles[current_tile_id]
            for neighbor_id in current_tile.neighbors:
                if (
                    (neighbor_id not in visited)
                    and (current_tile_id in self.tile_ids)
                    and (game_state.map.tiles[neighbor_id].biome != Biome.WATER)
                ):
                    print("tuile candidate", neighbor_id)
                    queue.append((neighbor_id, distance + 1))
                    if neighbor_id not in self.tile_ids:
                        candidate_tiles.add((neighbor_id, distance + 1))
        print(
            f"Ville '{self.name}' - tuiles candidates pour extension : {[t[0] for t in candidate_tiles]}"
        )
        # les tuiles ont une probabilité d'être choisies en fonction de leur éloignement à la tuile centrale (plus c'est proche, plus c'est probable)
        if not candidate_tiles:
            return  # pas de tuiles candidates, on ne peut pas étendre
        # on choisit une tuile aléatoire parmi les tuiles selon une loi de probabilité décroissante avec la distance
        total_weight = sum(1 / (distance + 1) for _, distance in candidate_tiles)
        pick = random.uniform(0, total_weight)
        current = 0
        for tile_id, distance in candidate_tiles:
            weight = 1 / (distance + 1)
            current += weight
            if current > pick:
                self._add_tile(tile_id)
                print("extension réussie : ajout de la tuile", tile_id)
                return tile_id

    def remove_tile(self, tile_id: int) -> bool:
        """
        Retire une tuile du territoire de la ville.

        Args:
            tile_id (int): ID de la tuile à retirer

        Returns:
            bool: True si la tuile a été retirée, False si elle n'était pas dans le territoire
        """
        if tile_id in self.tile_ids and tile_id != self.center_tile_id:
            self.tile_ids.discard(tile_id)
            return True
        return False

    def calculate_production(self, game_map):
        """
        Calcule la production de ressources de la ville en fonction des tuiles qu'elle contrôle.

        La production dépend des ressources présentes sur chaque tuile.

        Args:
            game_map (Map): La carte du jeu pour accéder aux tuiles
        """
        # Réinitialiser la production
        self.production = {
            "food": 1,
            "wood": 0,
            "stone": 0,
            "iron": 0,
            "gold": 1,
        }

        # Calculer la production pour chaque tuile
        for tile_id in self.tile_ids:
            if tile_id not in game_map.tiles:
                continue

            tile = game_map.tiles[tile_id]
            resource = tile.resource

            # Mapping des ressources vers les catégories de production
            if resource == Resource.NONE:
                continue
            elif resource.name.startswith("FOOD"):
                level = int(resource.name[-1])
                self.production["food"] += level
            elif resource.name.startswith("WOOD"):
                level = int(resource.name[-1])
                self.production["wood"] += level
            elif resource.name.startswith("STONE"):
                level = int(resource.name[-1])
                self.production["stone"] += level
            elif resource.name.startswith("IRON"):
                level = int(resource.name[-1])
                self.production["iron"] += level
            elif resource.name.startswith("GOLD"):
                level = int(resource.name[-1])
                self.production["gold"] += level

    def get_visibility_mask(self, game_map) -> int:
        """
        Calcule le masque de visibilité de la ville (tuiles visibles).

        Une ville voit toutes ses tuiles et leurs voisines immédiates.

        Args:
            game_map (Map): La carte du jeu

        Returns:
            int: Masque de bits représentant les tuiles visibles
        """
        mask = 0

        for tile_id in self.tile_ids:
            if tile_id not in game_map.tiles:
                continue

            # La ville voit sa propre tuile
            mask |= 1 << tile_id

            # Et les tuiles voisines
            tile = game_map.tiles[tile_id]
            for neighbor_id in tile.neighbors:
                mask |= 1 << neighbor_id

        return mask

    def __repr__(self):
        """Représentation textuelle de la ville"""
        return f"City(id={self.id}, name='{self.name}', owner={self.owner}, tiles={len(self.tile_ids)}, production={self.production})"
