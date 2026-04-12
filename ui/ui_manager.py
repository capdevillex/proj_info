import pygame

from ui.button import Button
from config import GameConfig as gc


class UIManager:
    """
    Gestionnaire centralisé de tous les boutons UI.
    
    Permet de gérer facilement plusieurs boutons sans dupliquer du code.
    """
    
    def __init__(self, font):
        """Crée tous les boutons UI"""
        
        # Bouton "Placer Unité" - TOGGLEABLE
        self.placement_button = Button(
            x=gc.BUTTON_X,
            y=gc.BUTTON_Y,
            width=gc.BUTTON_WIDTH,
            height=gc.BUTTON_HEIGHT,
            text="Placer Unité",
            font=font,
            color=gc.BUTTON_COLOR,
            hover_color=gc.BUTTON_HOVER_COLOR,
            active_color=gc.BUTTON_ACTIVE_COLOR,
            is_toggleable=True  # ← Toggle on/off avec clic
        )
        
        # Bouton "Tour Suivant" - NON TOGGLEABLE
        self.next_turn_button = Button(
            x=gc.SCREEN_WIDTH - 160,
            y=10,
            width=150,
            height=40,
            text="Fin du tour",
            font=font,
            color=(60, 60, 60),
            hover_color=(100, 100, 100),
            active_color=(100, 100, 100),
            is_toggleable=False  # ← Juste clic, pas de toggle
        )
        
        self.quit_button = Button(
        	x = 10,
        	y = gc.SCREEN_HEIGHT-50,
        	height = 40,
        	width = 150,
        	text = "Quitter",
        	font = font,
        	color=(60, 60, 60),
            hover_color=(100, 100, 100),
            active_color=(100, 100, 100),
            is_toggleable=False
        )
        # Tu peux ajouter d'autres boutons aussi facilement :
        # self.save_button = Button(...)
        # self.load_button = Button(...)
        # etc.
    
    def update(self, mouse_pos):
        """Met à jour tous les boutons"""
        self.placement_button.update(mouse_pos)
        self.next_turn_button.update(mouse_pos)
    
    def draw(self, screen):
        """Dessine tous les boutons"""
        self.placement_button.draw(screen)
        self.next_turn_button.draw(screen)
        self.quit_button.draw(screen)
    
    def handle_click(self,
    	mouse_pos, game_map,
    	selected_unit_type,
    	selected_unit_water_affinity):
        """
        Gère les clics sur les boutons.
        
        Args:
            mouse_pos: Position du clic
            game_map: La carte du jeu
            selected_unit_type: Type d'unité sélectionné
            selected_unit_water_affinity: Affinité eau de l'unité
        
        Returns:
            str: Action à effectuer ("place_unit", "next_turn", None)
        """
        
        # Bouton Placer Unité
        if self.placement_button.is_clicked(mouse_pos):
            self.placement_button.toggle()
            status = "ACTIVÉ" if self.placement_button.is_active else "DÉSACTIVÉ"
            print(f"Mode placement {status}")
            return None  # Pas d'action immédiate, juste toggle
        
        # Bouton Tour Suivant
        if self.next_turn_button.is_clicked(mouse_pos):
            return "next_turn"

        # Boutin pour fermer le jeu
        if self.quit_button.is_clicked(mouse_pos):
        	return "quit"
        
        return None
