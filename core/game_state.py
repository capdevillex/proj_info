from typing import List

from world.map import Map
from world.unit import Unit


class GameState:
    def __init__(self, width, height, seed, tile_area, log):
        self.map = Map(width, height, seed, tile_area, log)
        self.units: List[Unit] = []
        self.cities = []

        self.current_player = 0
        self.turn = 0

        self.resources = {"gold": 0, "food": 0, "production": 0}

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
