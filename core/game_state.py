from typing import List

from world.map import Map
from world.unit import Unit
from world.city import City


class GameState:
    def __init__(self, width, height, seed, tile_area, log):
        self.map = Map(width, height, seed, tile_area, log)
        self.units: List[Unit] = []
        self.cities: List[City] = []

        self.current_player = 0
        self.turn = 0

        # Ressources par joueur
        self.player_resources = {0: {"food": 0, "wood": 0, "stone": 0, "iron": 0, "gold": 0}}

        # Bitmasks pour la gestion de visibilité des tuiles
        self.discovered = 0  # Terra Incognita
        self.visibility = 0  # Fog of war

        # sélection actuelle
        self.selected_unit_id = None
        self.selected_city_id = None

    def update_fow(self):
        """Met à jour les bitmasks de découverte et de visibilité en fonction des unités et des villes du joueur."""
        self.visibility = 0

        for unit in self.units:
            if unit.owner == self.current_player:
                self.visibility |= unit.get_visibility_mask(self.map)

        for city in self.cities:
            if city.owner == self.current_player:
                self.visibility |= city.get_visibility_mask(self.map)

    def add_city(self, city: City):
        """
        Ajoute une ville au jeu.

        Args:
            city (City): La ville à ajouter
        """
        self.cities.append(city)

        # Initialiser les ressources du joueur si nécessaire
        if city.owner not in self.player_resources:
            self.player_resources[city.owner] = {
                "food": 0,
                "wood": 0,
                "stone": 0,
                "iron": 0,
                "gold": 0,
            }

    def get_city_by_id(self, city_id: int):
        """
        Trouve une ville par son ID.

        Args:
            city_id (int): ID de la ville

        Returns:
            City: La ville trouvée, ou None
        """
        for city in self.cities:
            if city.id == city_id:
                return city
        return None

    def get_city_at_tile(self, tile_id: int):
        """
        Trouve la ville située sur une tuile donnée (tuile centrale).

        Args:
            tile_id (int): ID de la tuile

        Returns:
            City: La ville trouvée, ou None
        """
        for city in self.cities:
            if city.center_tile_id == tile_id:
                return city
        return None

    def get_cities_by_owner(self, owner: int):
        """
        Récupère toutes les villes d'un joueur.

        Args:
            owner (int): ID du joueur

        Returns:
            List[City]: Liste des villes du joueur
        """
        return [city for city in self.cities if city.owner == owner]
