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
    
    Attributes:
        id (int): Identifiant unique de l'unité
        tile_id (int): ID de la tuile sur laquelle l'unité est placée
        unit_type (UnitType): Type d'unité
        x (float): Position X relative au centre de la tuile
        y (float): Position Y relative au centre de la tuile
        owner (int): ID du propriétaire (joueur) de l'unité
    """
    
    # Compteur global pour générer des IDs uniques
    _unit_counter = 0
    
    def __init__(self, tile_id, unit_type=UnitType.SOLDIER, owner=0, x=0.0, y=0.0):
        """
        Crée une nouvelle unité.
        
        Args:
            tile_id (int): ID de la tuile sur laquelle placer l'unité
            unit_type (UnitType): Type d'unité (par défaut: SOLDIER)
            owner (int): ID du propriétaire (par défaut: 0)
            x (float): Position X relative (par défaut: 0, soit le centre)
            y (float): Position Y relative (par défaut: 0, soit le centre)
        """
        Unit._unit_counter += 1
        self.id = Unit._unit_counter
        self.tile_id = tile_id
        self.unit_type = unit_type
        self.owner = owner
        self.x = x  # Position relative au centre de la tuile
        self.y = y  # Position relative au centre de la tuile
    
    def __repr__(self):
        """Représentation textuelle de l'unité"""
        return f"Unit(id={self.id}, tile_id={self.tile_id}, type={self.unit_type.name}, owner={self.owner})"
    
    def get_color(self):

        #Retourne la couleur à utiliser pour dessiner l'unité.

        colors = {
            UnitType.SOLDIER: (255, 100, 100),      # Rouge
            UnitType.CAVALRY: (100, 200, 255),      # Bleu
            UnitType.ARCHER: (255, 200, 100),       # Orange
            UnitType.SETTLEMENT: (255, 255, 100),   # Jaune
        }
        return colors.get(self.unit_type, (200, 200, 200))  # Gris par défaut
    
    def get_size(self):

        #Retourne la taille (rayon) à utiliser pour dessiner l'unité.

        sizes = {
            UnitType.SOLDIER: 4,
            UnitType.CAVALRY: 6,
            UnitType.ARCHER: 4,
            UnitType.SETTLEMENT: 8,
        }
        return sizes.get(self.unit_type, 5)
