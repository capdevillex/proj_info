"""
Module de gestion des unités dans le jeu.

Les unités sont des entités placées sur les tuiles de la carte.
Elles représentent des éléments du gameplay (soldats, villes, etc.)
"""

import pygame
from enum import Enum
from config import GameConfig as gc


pygame.init()

font = pygame.font.SysFont(None, 20)
button_font = pygame.font.SysFont(None, 18)  #police pour le bouton



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

class UnitPlacementButton:
    """
    Bouton UI pour activer/désactiver le mode placement d'unités.

    Le bouton affiche :
    - "Place Unit" en bleu normal quand le mode est désactivé
    - "Place Unit (ON)" en rouge quand le mode est activé
    """

    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.is_active = False
        self.is_hovered = False

    def update(self, mouse_pos):
        """Met à jour l'état du bouton (survol)"""
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, mouse_pos):
        """Retourne True si le bouton est cliqué"""
        return self.rect.collidepoint(mouse_pos)

    def toggle(self):
        """Active/désactive le mode placement"""
        self.is_active = not self.is_active

    def draw(self, screen):
        """Dessine le bouton à l'écran"""
        # Couleur du bouton selon l'état
        if self.is_active:
            color = gc.BUTTON_ACTIVE_COLOR  # Rouge si actif
        elif self.is_hovered:
            color = gc.BUTTON_HOVER_COLOR  # Bleu clair si survolé
        else:
            color = gc.BUTTON_COLOR  # Bleu normal

        # Dessiner le rectangle du bouton
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (200, 200, 200), self.rect, 2)  # Bordure

        # Texte du bouton
        text_str = "Placer Unité (ON)" if self.is_active else "Placer Unité (OFF)"
        text_surface = button_font.render(text_str, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
