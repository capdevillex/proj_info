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
        self.font = font
        self.screen_width = gc.SCREEN_WIDTH
        self.screen_height = gc.SCREEN_HEIGHT

        # Sidebar rétractable pour les ressources
        self.sidebar_expanded = False
        self.sidebar_height = 60
        self.sidebar_collapsed_height = 25
        self.sidebar_animation_speed = 300  # pixels par seconde
        self.sidebar_current_height = self.sidebar_collapsed_height

        # Ressources (pas encore implémentées dans le jeu)
        self.resources = {"Nourriture": 100, "Or": 50, "Bois": 75, "Pierre": 30, "Fer": 20}

        # Bouton "Placer Unité" - TOGGLEABLE (en haut à gauche)
        self.placement_button = Button(
            x=10,
            y=10,
            width=gc.BUTTON_WIDTH,
            height=gc.BUTTON_HEIGHT,
            text="Placer Unité",
            font=font,
            color=gc.BUTTON_COLOR,
            hover_color=gc.BUTTON_HOVER_COLOR,
            active_color=gc.BUTTON_ACTIVE_COLOR,
            is_toggleable=True,
        )

        # Bouton "Tour Suivant" - NON TOGGLEABLE (en haut à droite)
        self.next_turn_button = Button(
            x=0,  # Sera mis à jour dans update_positions
            y=10,
            width=150,
            height=40,
            text="Fin du tour",
            font=font,
            color=(60, 60, 60),
            hover_color=(100, 100, 100),
            active_color=(100, 100, 100),
            is_toggleable=False,
        )

        # Bouton "Quitter" (en bas à gauche)
        self.quit_button = Button(
            x=10,
            y=0,  # Sera mis à jour dans update_positions
            height=40,
            width=150,
            text="Quitter",
            font=font,
            color=(60, 60, 60),
            hover_color=(100, 100, 100),
            active_color=(100, 100, 100),
            is_toggleable=False,
        )

        # Bouton pour toggle la sidebar (en haut au centre)
        self.toggle_sidebar_button = Button(
            x=0,  # Sera mis à jour dans update_positions
            y=0,
            width=120,
            height=self.sidebar_collapsed_height,
            text="▼ Ressources",
            font=font,
            color=(40, 40, 40),
            hover_color=(70, 70, 70),
            active_color=(70, 70, 70),
            is_toggleable=False,
        )

    def update_positions(self, screen_width, screen_height):
        """Met à jour les positions des boutons en fonction de la taille de l'écran"""
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Bouton "Tour Suivant" - en haut à droite
        self.next_turn_button.set_position(screen_width - 160, 10)

        # Bouton "Quitter" - en bas à gauche
        self.quit_button.set_position(10, screen_height - 50)

        # Bouton toggle sidebar - en haut au centre
        self.toggle_sidebar_button.set_position(
            (screen_width - self.toggle_sidebar_button.rect.width) // 2, 0
        )

    def update(self, mouse_pos, dt):
        """Met à jour tous les boutons et la sidebar"""
        self.placement_button.update(mouse_pos)
        self.next_turn_button.update(mouse_pos)
        self.quit_button.update(mouse_pos)
        self.toggle_sidebar_button.update(mouse_pos)

        # Animation de la sidebar
        target_height = (
            self.sidebar_height if self.sidebar_expanded else self.sidebar_collapsed_height
        )
        if self.sidebar_current_height < target_height:
            self.sidebar_current_height = min(
                self.sidebar_current_height + self.sidebar_animation_speed * dt, target_height
            )
        elif self.sidebar_current_height > target_height:
            self.sidebar_current_height = max(
                self.sidebar_current_height - self.sidebar_animation_speed * dt, target_height
            )

    def draw(self, screen):
        """Dessine tous les boutons et la sidebar"""
        # Dessiner la sidebar
        self._draw_sidebar(screen)

        # Dessiner les boutons
        self.placement_button.draw(screen)
        self.next_turn_button.draw(screen)
        self.quit_button.draw(screen)
        self.toggle_sidebar_button.draw(screen)

    def _draw_sidebar(self, screen):
        """Dessine la sidebar des ressources"""
        # Fond de la sidebar
        sidebar_rect = pygame.Rect(0, 0, self.screen_width, int(self.sidebar_current_height))
        pygame.draw.rect(screen, (30, 30, 30), sidebar_rect)
        pygame.draw.line(
            screen,
            (100, 100, 100),
            (0, int(self.sidebar_current_height)),
            (self.screen_width, int(self.sidebar_current_height)),
            2,
        )

        # Si la sidebar est suffisamment ouverte, afficher les ressources
        if self.sidebar_current_height > self.sidebar_collapsed_height + 10:
            # Calculer l'espacement entre les ressources
            num_resources = len(self.resources)
            spacing = self.screen_width // (num_resources + 1)

            # Afficher chaque ressource
            for i, (resource_name, amount) in enumerate(self.resources.items()):
                x_pos = spacing * (i + 1)
                y_pos = self.sidebar_collapsed_height + 10

                # Nom de la ressource
                name_surface = self.font.render(resource_name, True, (200, 200, 200))
                name_rect = name_surface.get_rect(center=(x_pos, y_pos))
                screen.blit(name_surface, name_rect)

                # Quantité
                amount_surface = self.font.render(str(amount), True, (255, 215, 0))
                amount_rect = amount_surface.get_rect(center=(x_pos, y_pos + 15))
                screen.blit(amount_surface, amount_rect)

    def handle_click(self, mouse_pos, game_map, selected_unit_type, selected_unit_water_affinity):
        """
        Gère les clics sur les boutons.

        Args:
            mouse_pos: Position du clic
            game_map: La carte du jeu
            selected_unit_type: Type d'unité sélectionné
            selected_unit_water_affinity: Affinité eau de l'unité

        Returns:
            str: Action à effectuer ("place_unit", "next_turn", "quit", None)
        """

        # Bouton toggle sidebar
        if self.toggle_sidebar_button.is_clicked(mouse_pos):
            self.sidebar_expanded = not self.sidebar_expanded
            # Changer le texte du bouton
            if self.sidebar_expanded:
                self.toggle_sidebar_button.set_text("▲ Ressources")
            else:
                self.toggle_sidebar_button.set_text("▼ Ressources")
            return None

        # Bouton Placer Unité
        if self.placement_button.is_clicked(mouse_pos):
            self.placement_button.toggle()
            status = "ACTIVÉ" if self.placement_button.is_active else "DÉSACTIVÉ"
            print(f"Mode placement {status}")
            return None

        # Bouton Tour Suivant
        if self.next_turn_button.is_clicked(mouse_pos):
            return "next_turn"

        # Bouton pour fermer le jeu
        if self.quit_button.is_clicked(mouse_pos):
            return "quit"

        return None
