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
    ARCHER  = 3
    COLON   = 4
    COLONIE = 5
    BABY    = 6


class Unit:
    """Classe de base — ne pas instancier directement."""

    #Attention à bein le redéfinir dans chaque type d'unités
    UNIT_TYPE:     UnitType
    MAX_DISTANCE:   int
    ATTACK_RANGE:   int
    BASE_ATTACK:    int
    BASE_DEFENSE:   int
    BASE_HP:        int
    WATER_AFFINITY: bool = False
    SIZE:           int
    UPKEEP_COST:    int
    DASH:           bool = False

    _unit_counter = 0

    def __init__(self, tile_id, owner=0, x=0.0, y=0.0):
        Unit._unit_counter += 1
        self.id            = Unit._unit_counter
        self.tile_id       = tile_id
        self.owner         = owner
        self.x             = x
        self.y             = y
        self.unit_type     = self.UNIT_TYPE
        self.has_moved     = False
        self.unit_type      = self.UNIT_TYPE
        self.max_distance   = self.MAX_DISTANCE
        self.attack_range   = self.ATTACK_RANGE
        self.water_affinity = self.WATER_AFFINITY
        self.upkeep_cost    = self.UPKEEP_COST
        self.can_dash       = self.DASH
            

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, tile={self.tile_id}, owner={self.owner})"

    def get_size(self):
        """Retourne la taille pour dessiner l'unité."""
        return self.SIZE

    def get_opacity(self):
        """Retourne l'opacité : 0.5 si a bougé, 1.0 sinon."""
        return 0.5 if self.has_moved else 1.0

    def can_move(self):
        """Vérifie si l'unité peut encore se déplacer ce tour."""
        return not self.has_moved and self.max_distance > 0

    def move_to_tile(self, new_tile_id):
        """Déplace l'unité vers une nouvelle tuile."""
        self.tile_id   = new_tile_id
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

    

# ── Sous-classes ────────────────────────────────────────────────

class Soldier(Unit):
    UNIT_TYPE    = UnitType.SOLDIER
    MAX_DISTANCE = 3
    ATTACK_RANGE = 1
    BASE_ATTACK  = 10
    BASE_DEFENSE = 8
    BASE_HP      = 100
    SIZE         = 4
    UPKEEP_COST  = 10 

class Cavalry(Unit):
    UNIT_TYPE    = UnitType.CAVALRY
    MAX_DISTANCE = 5
    ATTACK_RANGE = 1
    BASE_ATTACK  = 12
    BASE_DEFENSE = 6
    BASE_HP      = 90
    SIZE         = 4
    UPKEEP_COST  = 10 


class Archer(Unit):
    UNIT_TYPE    = UnitType.ARCHER
    MAX_DISTANCE = 2
    ATTACK_RANGE = 2
    BASE_ATTACK  = 8
    BASE_DEFENSE = 5
    BASE_HP      = 70
    SIZE         = 4
    UPKEEP_COST  = 10 

class Colon(Unit):
    UNIT_TYPE      = UnitType.COLON
    MAX_DISTANCE   = 1
    ATTACK_RANGE   = 0
    BASE_ATTACK    = 2
    BASE_DEFENSE   = 3
    BASE_HP        = 50
    WATER_AFFINITY = True
    SIZE = 4
    UPKEEP_COST  = 10 


class Colonie(Unit):
    UNIT_TYPE    = UnitType.COLONIE
    MAX_DISTANCE = 0
    ATTACK_RANGE = 0
    BASE_ATTACK  = 0
    BASE_DEFENSE = 0
    BASE_HP      = 0
    SIZE         = 15


class Baby(Unit):
    UNIT_TYPE      = UnitType.BABY
    MAX_DISTANCE   = 3
    ATTACK_RANGE   = 1
    BASE_ATTACK    = 5
    BASE_DEFENSE   = 3
    BASE_HP        = 50
    SIZE           = 4
    UPKEEP_COST  = 10 


# ── Factory ─────────────────────────────────────────────────────

UNIT_CLASS_MAP = {
    UnitType.SOLDIER: Soldier,
    UnitType.CAVALRY: Cavalry,
    UnitType.ARCHER:  Archer,
    UnitType.COLON:   Colon,
    UnitType.COLONIE: Colonie,
    UnitType.BABY:    Baby,
}