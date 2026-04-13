"""
Module de gestion des unités dans le jeu.

Les unités sont des entités placées sur les provinces de la carte.
Elles représentent des éléments du gameplay (soldats, villes, etc.)
"""

import pygame
from enum import Enum

from config import GameConfig as gc


pygame.init()

font = pygame.font.SysFont(None, 20)
button_font = pygame.font.SysFont(None, 18)


class UnitType(Enum):
    """Types d'unités disponibles"""

    SOLDIER = 1
    CAVALRY = 2
    ARCHER = 3
    COLON = 4
    COLONIE = 5


class Unit:
    """
    Représente une unité sur la carte.

    Une unité est placée sur une tuile spécifique et a une position
    relative au centre de la tuile.
    """

    # Compteur global pour générer des IDs uniques
    _unit_counter = 0

    # Distance maximale pour chaque type d'unité
    MAX_DISTANCE = {
        UnitType.SOLDIER: 3,
        UnitType.CAVALRY: 5,
        UnitType.ARCHER: 2,
        UnitType.COLON: 2,  # Immobile
        UnitType.COLONIE: 0,
    }

    def __init__(self, tile_id, water_affinity, unit_type=UnitType.SOLDIER, owner=0, x=0.0, y=0.0):
        """Crée une nouvelle unité."""
        Unit._unit_counter += 1
        self.id = Unit._unit_counter
        self.tile_id = tile_id
        self.water_affinity = water_affinity
        self.unit_type = unit_type
        self.owner = owner
        self.x = x
        self.y = y
        self.max_distance = self.MAX_DISTANCE[unit_type]
        self.has_moved = False

    def __repr__(self):
        """Représentation textuelle de l'unité"""
        return f"Unit(id={self.id}, tile_id={self.tile_id}, type={self.unit_type.name}, owner={self.owner})"

    def get_color(self):
        """Retourne la couleur pour dessiner l'unité."""
        colors = {
            UnitType.SOLDIER: (255, 100, 100),  # Rouge
            UnitType.CAVALRY: (100, 200, 255),  # Bleu
            UnitType.ARCHER: (255, 200, 100),  # Orange
            UnitType.COLON: (255, 255, 100),  # Jaune
        }
        return colors.get(self.unit_type, (200, 200, 200))

    def get_size(self):
        """Retourne la taille (rayon) pour dessiner l'unité."""
        sizes = {
            UnitType.SOLDIER: 1,
            UnitType.CAVALRY: 2,
            UnitType.ARCHER: 3,
            UnitType.COLON: 4,
        }
        return sizes.get(self.unit_type, 2)

    def get_opacity(self):
        """
        Retourne l'opacité de l'unité.

        Returns:
            float: 1.0 si n'a pas bougé, 0.5 si a bougé
        """
        return 0.5 if self.has_moved else 1.0

    def can_move(self):
        """Vérifie si l'unité peut encore se déplacer ce tour."""
        return not self.has_moved and self.max_distance > 0

    def move_to_tile(self, new_tile_id):
        """
        Déplace l'unité vers une nouvelle tuile.

        Args:
            new_tile_id (int): ID de la nouvelle tuile
        """
        self.tile_id = new_tile_id
        self.has_moved = True

    def reset_movement(self):
        """Réinitialise le mouvement (appelé au début d'un nouveau tour)."""
        self.has_moved = False

    def get_visibility_mask(self, map_):
        """Calcule le bitmask de visibilité pour cette unité."""
        visible_tiles = set()
        visible_tiles.add(self.tile_id)
        for neighbor_id in map_.tiles[self.tile_id].neighbors:
            visible_tiles.add(neighbor_id)
        mask = 0
        for tile_id in visible_tiles:
            mask |= 1 << tile_id
        return mask
