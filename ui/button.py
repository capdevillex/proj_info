"""
Module de gestion des boutons UI.

Contient une classe Button générique pour créer n'importe quel bouton
avec configuration flexible (position, taille, couleurs, texte, etc.)
"""

import pygame


class Button:
    """
    Classe générique pour tous les boutons de l'interface.
    
    Permet de créer des boutons avec configuration complète :
    - Position et taille
    - Texte et police
    - Couleurs (normal, hover, active)
    - État (actif/inactif)
    - Comportement (toggle ou simple clic)
    
    Exemple d'utilisation :
        button = Button(
            x=10, y=10,
            width=150, height=40,
            text="Placer Unité",
            font=font,
            color=(100, 100, 200),
            hover_color=(150, 150, 255),
            active_color=(255, 100, 100)
        )
    """
    
    def __init__(
        self,
        x, y,
        width, height,
        text="Button",
        font=None,
        color=(100, 100, 200),
        hover_color=(150, 150, 255),
        active_color=(255, 100, 100),
        border_color=(200, 200, 200),
        text_color=(255, 255, 255),
        is_toggleable=False  # True = toggle on/off, False = juste clic
    ):
        """
        Crée un nouveau bouton.
        
        Args:
            x, y: Position du bouton
            width, height: Dimensions du bouton
            text: Texte affiché sur le bouton
            font: Police pygame pour le texte
            color: Couleur normale (RGB tuple)
            hover_color: Couleur au survol
            active_color: Couleur quand actif
            border_color: Couleur de la bordure
            text_color: Couleur du texte
            is_toggleable: Si True, le bouton bascule on/off à chaque clic
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font or pygame.font.SysFont(None, 18)
        self.color = color
        self.hover_color = hover_color
        self.active_color = active_color
        self.border_color = border_color
        self.text_color = text_color
        self.is_toggleable = is_toggleable
        
        # État du bouton
        self.is_active = False
        self.is_hovered = False
    
    # ========== MÉTHODES DE GESTION D'ÉTAT ==========
    
    def update(self, mouse_pos):
        """
        Met à jour l'état du bouton (survol).
        À appeler chaque frame avant le rendu.
        
        Args:
            mouse_pos: Position de la souris (x, y)
        """
        self.is_hovered = self.rect.collidepoint(mouse_pos)
    
    def is_clicked(self, mouse_pos):
        """
        Vérifie si le bouton est cliqué.
        
        Args:
            mouse_pos: Position de la souris au moment du clic
            
        Returns:
            bool: True si le bouton est cliqué
        """
        return self.rect.collidepoint(mouse_pos)
    
    def toggle(self):
        """Active/désactive le bouton (si toggleable)."""
        if self.is_toggleable:
            self.is_active = not self.is_active
    
    def set_active(self, state):
        """
        Force l'état du bouton.
        
        Args:
            state: True pour activer, False pour désactiver
        """
        self.is_active = state
    
    def reset(self):
        """Réinitialise le bouton à l'état inactif."""
        self.is_active = False
    
    # ========== RENDU ==========
    
    def draw(self, screen):
        """
        Dessine le bouton à l'écran.
        
        Args:
            screen: Surface pygame où dessiner
        """
        # Déterminer la couleur du bouton
        if self.is_active:
            button_color = self.active_color
        elif self.is_hovered:
            button_color = self.hover_color
        else:
            button_color = self.color
        
        # Dessiner le fond du bouton
        pygame.draw.rect(screen, button_color, self.rect)
        
        # Dessiner la bordure
        pygame.draw.rect(screen, self.border_color, self.rect, 2)
        
        # Préparer le texte
        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        
        # Afficher le texte
        screen.blit(text_surface, text_rect)
    
    # ========== UTILITAIRES ==========
    
    def set_position(self, x, y):
        """
        Change la position du bouton.
        
        Args:
            x, y: Nouvelles coordonnées
        """
        self.rect.x = x
        self.rect.y = y
    
    def set_size(self, width, height):
        """
        Change la taille du bouton.
        
        Args:
            width, height: Nouvelles dimensions
        """
        self.rect.width = width
        self.rect.height = height
    
    def set_text(self, text):
        """
        Change le texte du bouton.
        
        Args:
            text: Nouveau texte
        """
        self.text = text
    
    def set_colors(self, color, hover_color, active_color):
        """
        Change toutes les couleurs du bouton.
        
        Args:
            color: Couleur normale
            hover_color: Couleur au survol
            active_color: Couleur active
        """
        self.color = color
        self.hover_color = hover_color
        self.active_color = active_color
    
    def __repr__(self):
        """Représentation textuelle du bouton"""
        return f"Button(text='{self.text}', active={self.is_active}, pos=({self.rect.x}, {self.rect.y}))"
