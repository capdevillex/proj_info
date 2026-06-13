"""
Module de gestion des unités dans le jeu.

Les unités sont des entités placées sur les provinces de la carte.
Elles représentent des éléments du gameplay (soldats, villes, etc.)

Author : Xavier (whole file)
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
    BABY    = 5
    PLANE   = 6
    BOAT    = 7


class Unit:
    """Classe de base — ne pas instancier directement."""

    #Attention à bein le redéfinir dans chaque type d'unités
    UNIT_TYPE:      UnitType
    MAX_DISTANCE:   int
    ATTACK_RANGE:   int
    BASE_ATTACK:    int
    BASE_DEFENSE:   int
    BASE_HP:        int
    WATER_AFFINITY: bool = False
    SIZE:           int
    BASE_COST :     int
    UPKEEP_COST:    int
    DASH:           bool = False
    FLY :           bool = False
    CARRY:          bool = False
    ESCAPE:         bool = False
    SCOUT:          bool = False
    PERSIST:        bool = False
    LAND_AFFINITY:  bool = True



    _unit_counter = 0

    def __init__(self, tile_id, owner=0, x=0.0, y=0.0):
        Unit._unit_counter += 1
        self.id             = Unit._unit_counter
        self.tile_id        = tile_id
        self.owner          = owner
        self.x              = x
        self.y              = y
        self.hp             = self.BASE_HP
        self.unit_type      = self.UNIT_TYPE
        self.has_moved      = False
        self.has_attacked   = False
        self.unit_type      = self.UNIT_TYPE
        self.max_distance   = self.MAX_DISTANCE
        self.attack_range   = self.ATTACK_RANGE
        self.water_affinity = self.WATER_AFFINITY
        self.land_affinity  = self.LAND_AFFINITY
        self.upkeep_cost    = self.UPKEEP_COST
        self.can_dash       = self.DASH
        self.base_cost      = self.BASE_COST


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
        if self.has_attacked and not self.has_moved and self.ESCAPE:
            return True
        else:
            return not self.has_moved

    def unit_can_attack(self):
        """Vérifie si l'unité peut encore se déplacer ce tour."""
        return not self.has_attacked


    def move_to_tile(self, new_tile_id):
        """Déplace simplement l'unité vers une nouvelle tuile."""
        self.tile_id = new_tile_id
        self.has_moved = True

    def reset_turn(self):
        """Appelé au début de chaque nouveau tour."""
        self.has_moved = False
        self.has_attacked = False




    def get_visibility_mask(self, map_):
        """Calcule le bitmask de visibilité pour cette unité."""
        visible_tiles = set()
        visible_tiles.add(self.tile_id)
        if self.SCOUT:
                print("Je suis un scout")
                for neighbor_id in map_.tiles[self.tile_id].neighbors:
                    visible_tiles.add(neighbor_id)
                    for neigh_of_neigh in map_.tiles[neighbor_id].neighbors:
                        visible_tiles.add(neigh_of_neigh)

        else:
            for neighbor_id in map_.tiles[self.tile_id].neighbors:
                visible_tiles.add(neighbor_id)

        mask = 0
        for tile_id in visible_tiles:
            mask |= 1 << tile_id
        return mask



#  Sous-classes

class Soldier(Unit):
    UNIT_TYPE    = UnitType.SOLDIER
    MAX_DISTANCE = 3
    ATTACK_RANGE = 1
    BASE_ATTACK  = 9999
    BASE_DEFENSE = 8
    BASE_HP      = 100
    SIZE         = 4
    BASE_COST    = 8
    UPKEEP_COST  = 1

class Cavalry(Unit):
    UNIT_TYPE    = UnitType.CAVALRY
    MAX_DISTANCE = 5
    ATTACK_RANGE = 1
    BASE_ATTACK  = 12
    BASE_DEFENSE = 6
    BASE_HP      = 90
    SIZE         = 4
    UPKEEP_COST  = 1
    BASE_COST    = 150
    DASH         = True
    ESCAPE       = True

class Archer(Unit):
    UNIT_TYPE    = UnitType.ARCHER
    MAX_DISTANCE = 2
    ATTACK_RANGE = 2
    BASE_ATTACK  = 8
    BASE_DEFENSE = 5
    BASE_HP      = 70
    SIZE         = 4
    UPKEEP_COST  = 1
    BASE_COST    = 10
    SCOUT        = True

class Colon(Unit):
    UNIT_TYPE      = UnitType.COLON
    MAX_DISTANCE   = 1
    ATTACK_RANGE   = 0
    BASE_ATTACK    = 2
    BASE_DEFENSE   = 3
    BASE_HP        = 50
    WATER_AFFINITY = True
    SIZE           = 4
    BASE_COST      = 15
    UPKEEP_COST    = 10

class Plane(Unit):
    UNIT_TYPE      = UnitType.PLANE
    MAX_DISTANCE   = 10
    ATTACK_RANGE   = MAX_DISTANCE
    BASE_ATTACK    = 20
    BASE_DEFENSE   = 5
    BASE_HP        = 50
    WATER_AFFINITY = True
    SIZE           = 4
    BASE_COST      = 500
    UPKEEP_COST    = 10
    FLY            = True
    SCOUT          = True


class Baby(Unit):
    UNIT_TYPE      = UnitType.BABY
    MAX_DISTANCE   = 3
    ATTACK_RANGE   = 1
    BASE_ATTACK    = 5
    BASE_DEFENSE   = 3
    BASE_HP        = 50
    SIZE           = 4
    UPKEEP_COST    = 1
    BASE_COST      = 50

class Boat(Unit):
    UNIT_TYPE      = UnitType.BOAT
    MAX_DISTANCE   = 3
    ATTACK_RANGE   = 1
    BASE_ATTACK    = 5
    BASE_DEFENSE   = 3
    BASE_HP        = 50
    SIZE           = 4
    UPKEEP_COST    = 1
    BASE_COST      = 100
    WATER_AFFINITY = True
    LAND_AFFINITY  = False


#  Factory

UNIT_CLASS_MAP = {
    UnitType.SOLDIER: Soldier,
    UnitType.CAVALRY: Cavalry,
    UnitType.ARCHER:  Archer,
    UnitType.COLON:   Colon,
    UnitType.BABY:    Baby,
    UnitType.PLANE:   Plane,
    UnitType.BOAT:    Boat,
}
