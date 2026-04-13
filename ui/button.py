"""
Module de gestion des boutons UI.

Contient une classe Button générique pour créer n'importe quel bouton
avec configuration flexible (position, taille, couleurs, texte, etc.)
"""

import pygame
import math


class Button:
    """
    Classe générique pour tous les boutons de l'interface.

    Permet de créer des boutons avec configuration complète :
    - Position et taille
    - Texte et police
    - Couleurs (normal, hover, active)
    - État (actif/inactif)
    - Comportement (toggle ou simple clic)

    Supporte les états normal / hover / actif avec transitions douces.
    """

    # Palette centralisée
    C_BG = (18, 22, 30)
    C_BORDER = (70, 90, 120)
    C_HOVER_BG = (30, 40, 58)
    C_HOVER_BD = (120, 160, 210)
    C_ACTIVE_BG = (28, 55, 90)
    C_ACTIVE_BD = (100, 180, 255)
    C_TEXT = (200, 215, 230)
    C_TEXT_ACT = (255, 255, 255)

    def __init__(
        self,
        x,
        y,
        width,
        height,
        text="Button",
        font=None,
        # Les arguments legacy ci-dessous sont acceptés mais ignorés
        # (on garde la signature pour compatibilité avec l'existant)
        color=None,
        hover_color=None,
        active_color=None,
        border_color=None,
        text_color=None,
        is_toggleable=False,
    ):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font or pygame.font.SysFont(None, 18)
        self.is_toggleable = is_toggleable

        self.is_active = False
        self.is_hovered = False

        # Animation : interpolation de l'alpha de surbrillance
        self._hover_t = 0.0  # 0..1
        self._active_t = 0.0

    # État
    def update(self, mouse_pos, dt=0.016):
        target_h = 1.0 if self.rect.collidepoint(mouse_pos) else 0.0
        speed = 8.0
        self._hover_t += (target_h - self._hover_t) * speed * dt
        self.is_hovered = self.rect.collidepoint(mouse_pos)

        target_a = 1.0 if self.is_active else 0.0
        self._active_t += (target_a - self._active_t) * speed * dt

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

    # Rendu
    def draw(self, screen):
        """
        Dessine le bouton à l'écran.

        Args:
            screen: Surface pygame où dessiner
        """
        t_h = self._hover_t
        t_a = self._active_t

        # Fond
        bg = self._lerp_color(self.C_BG, self.C_HOVER_BG, t_h)
        bg = self._lerp_color(bg, self.C_ACTIVE_BG, t_a)

        # Bordure
        bd = self._lerp_color(self.C_BORDER, self.C_HOVER_BD, t_h)
        bd = self._lerp_color(bd, self.C_ACTIVE_BD, t_a)

        # Texte
        tc = self._lerp_color(self.C_TEXT, self.C_TEXT_ACT, max(t_h, t_a))

        # Fond avec léger arrondi simulé (pas de border_radius < pygame 2.0)
        pygame.draw.rect(screen, bg, self.rect)
        pygame.draw.rect(screen, bd, self.rect, 1)

        # Ligne de surbrillance en haut (highlight)
        if t_h > 0.05 or t_a > 0.05:
            alpha = int(60 * max(t_h, t_a))
            hl_surf = pygame.Surface((self.rect.width, 1), pygame.SRCALPHA)
            hl_surf.fill((*bd, alpha))
            screen.blit(hl_surf, (self.rect.x, self.rect.y))

        # Indicateur actif : petite barre à gauche
        if t_a > 0.05:
            bar_h = int(self.rect.height * 0.5 * t_a)
            bar_y = self.rect.centery - bar_h // 2
            pygame.draw.rect(screen, self.C_ACTIVE_BD, (self.rect.x, bar_y, 2, bar_h))

        # Texte
        surf = self.font.render(self.text, True, tc)
        r = surf.get_rect(center=self.rect.center)
        screen.blit(surf, r)

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------

    @staticmethod
    def _lerp_color(a, b, t):
        t = max(0.0, min(1.0, t))
        return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

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

    # Rétro-compat
    def set_colors(self, *args):
        pass

    def __repr__(self):
        """Représentation textuelle du bouton"""
        return f"Button(text='{self.text}', active={self.is_active}, pos=({self.rect.x}, {self.rect.y}))"
