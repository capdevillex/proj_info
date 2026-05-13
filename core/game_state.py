from enum import Enum, auto
from typing import List, Optional

from world.map import Map
from world.unit import Unit
from world.city import City
from world.kingdom import Kingdom


class TurnPhase(Enum):
    """Phase active dans le cycle de tour."""
    PLAYER_TURN = auto()  # le joueur humain peut interagir
    AI_TURN = auto()      # une IA est en train de jouer, input verrouillé


class GameState:
    def __init__(self, width, height, seed, tile_area, log):
        self.map = Map(width, height, seed, avg_cells_per_tile=tile_area, log=log)
        self.units: List[Unit] = []
        self.cities: List[City] = []

        # Joueur humain toujours 0
        self.current_player = 0

        self.turn = 0

        # Royaumes
        # Créer le royaume joueur par défaut
        player_kingdom = Kingdom(
            kingdom_id=0,
            name="Joueur 1",
            color=(80, 130, 210),
            is_ai=False,
        )
        self.kingdoms: List[Kingdom] = [player_kingdom]

        # Ordre de jeu : liste d'IDs de royaumes, dans l'ordre du tour.
        # Le joueur (0) joue en premier, puis les IA dans l'ordre d'ajout.
        self.turn_order: List[int] = [0]

        # Index courant dans turn_order (utilisé pendant la phase IA)
        self.current_kingdom_idx: int = 0

        # Phase du tour en cours
        self.phase: TurnPhase = TurnPhase.PLAYER_TURN

        # Ressources par royaume (clé = kingdom_id)
        self.player_resources = {
            0: {"food": 0, "wood": 0, "stone": 0, "iron": 0, "gold": 0}
        }

        # Bitmasks pour la gestion de visibilité des tuiles
        self.discovered = 0  # Terra Incognita
        self.visibility = 0  # Fog of war
        self.use_ti = False
        self.use_fow = False

        # Sélection actuelle (joueur humain)
        self.selected_unit_id = None
        self.selected_city_id = None

    # Propriétés de tour
    @property
    def active_kingdom_id(self) -> int:
        """ID du royaume dont c'est le tour (joueur ou IA)."""
        if not self.turn_order:
            return self.current_player
        return self.turn_order[self.current_kingdom_idx]

    @property
    def is_player_turn(self) -> bool:
        """True si le joueur humain peut interagir."""
        return self.phase == TurnPhase.PLAYER_TURN

    # Gestion des royaumes
    def add_kingdom(self, kingdom: Kingdom) -> None:
        """Enregistre un nouveau royaume et initialise ses ressources."""
        if any(k.kingdom_id == kingdom.kingdom_id for k in self.kingdoms):
            raise ValueError(f"Le royaume {kingdom.kingdom_id} est déjà enregistré")
        self.kingdoms.append(kingdom)
        if kingdom.kingdom_id not in self.turn_order:
            self.turn_order.append(kingdom.kingdom_id)
        if kingdom.kingdom_id not in self.player_resources:
            self.player_resources[kingdom.kingdom_id] = {
                "food": 0, "wood": 0, "stone": 0, "iron": 0, "gold": 0
            }

    def get_kingdom(self, kingdom_id: int) -> Optional[Kingdom]:
        """Retourne le Kingdom correspondant à l'ID, ou None."""
        for k in self.kingdoms:
            if k.kingdom_id == kingdom_id:
                return k
        return None

    # Visibilité
    def update_fow(self):
        """Met à jour les bitmasks de visibilité pour le joueur humain (current_player)."""
        self.visibility = 0
        for unit in self.units:
            if unit.owner == self.current_player:
                self.visibility |= unit.get_visibility_mask(self.map)
        for city in self.cities:
            if city.owner == self.current_player:
                self.visibility |= city.get_visibility_mask(self.map)
        self.update_discovered()

    def update_discovered(self):
        """Met à jour le bitmask de découverte en ajoutant les tuiles actuellement visibles."""
        self.discovered |= self.visibility

    def get_kingdom_visibility(self, kingdom_id: int) -> int:
        """Calcule le bitmask de visibilité d'un royaume quelconque (lecture seule).

        Utile pour les IA qui ont besoin de savoir ce qu'elles voient
        sans affecter la visibilité affichée au joueur humain.
        """
        vis = 0
        for unit in self.units:
            if unit.owner == kingdom_id:
                vis |= unit.get_visibility_mask(self.map)
        for city in self.cities:
            if city.owner == kingdom_id:
                vis |= city.get_visibility_mask(self.map)
        return vis

    # Villes

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
                "food": 0, "wood": 0, "stone": 0, "iron": 0, "gold": 0,
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
