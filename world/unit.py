"""
Module de gestion des unités dans le jeu.

Les unités sont des entités placées sur les tuiles de la carte.
Elles représentent des éléments du gameplay (soldats, villes, etc.)
"""

from enum import Enum


class UnitType(Enum):
    """Types d'unités disponibles"""
    SOLDIER = 1
    CAVALRY = 2
    ARCHER = 3
    SETTLEMENT = 4


class Unit:
    """
    Représente une unité sur la carte.
    
    Une unité est placée sur une tuile spécifique et a une position 
    relative au centre de la tuile.
    """
    
    # Compteur global pour générer des IDs uniques
    _unit_counter = 0
    
    def __init__(self, tile_id,water_affinity, unit_type=UnitType.SOLDIER, owner=0, x=0.0, y=0.0):
        """Crée une nouvelle unité."""
        Unit._unit_counter += 1
        self.id = Unit._unit_counter
        self.tile_id = tile_id
        self.water_affinity = water_affinity
        self.unit_type = unit_type
        self.owner = owner
        self.x = x
        self.y = y
        
    
    def __repr__(self):
        """Représentation textuelle de l'unité"""
        return f"Unit(id={self.id}, tile_id={self.tile_id}, type={self.unit_type.name}, owner={self.owner})"
    
    def get_color(self):
        """Retourne la couleur pour dessiner l'unité."""
        colors = {
            UnitType.SOLDIER: (255, 100, 100),      # Rouge
            UnitType.CAVALRY: (100, 200, 255),      # Bleu
            UnitType.ARCHER: (255, 200, 100),       # Orange
            UnitType.SETTLEMENT: (255, 255, 100),   # Jaune
        }
        return colors.get(self.unit_type, (200, 200, 200))
    
    def get_size(self):
        """Retourne la taille (rayon) pour dessiner l'unité."""
        # MODIFIÉ : Tailles réduites pour mieux voir le détail
        sizes = {
            UnitType.SOLDIER: 1,
            UnitType.CAVALRY: 2,
            UnitType.ARCHER: 3,
            UnitType.SETTLEMENT: 4,
        }
        return sizes.get(self.unit_type, 2)
