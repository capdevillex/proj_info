"""
UIManager - Design stratégique sombre, style 4X.

Layout :
  - Sidebar gauche rétractable, ressources du joueur
  - Barre de statut bas gauche, infos tuile survolée
  - Boutons action haut gauche, placement, etc.
  - Bouton "Fin du tour" bas droite (grand, bien visible)
  - Indicateur tour / joueur , coin haut droit
"""

import math
from pathlib import Path

import pygame

from ui.button import Button
from config import GameConfig as gc
from core.game_engine import GameEngine


#  Palette UI
C_PANEL_BG = (12, 16, 24)  # fond principal
C_PANEL_BG2 = (18, 24, 36)  # fond secondaire
C_BORDER = (40, 60, 90)  # bordure froide
C_BORDER_LIT = (70, 110, 160)  # bordure éclairée
C_TEXT_DIM = (110, 130, 155)  # texte discret
C_TEXT = (185, 205, 225)  # texte normal
C_TEXT_BRIGHT = (225, 240, 255)  # texte important
C_GOLD = (210, 175, 90)  # or / accent
C_RED = (200, 80, 70)
C_GREEN = (90, 190, 110)
C_BLUE_ACC = (80, 150, 220)

# Icônes textuelles pour chaque ressource (emoji visibles sur la plupart des OS)
RESOURCE_ICONS = {
    "food": "🌾",
    "wood": "🪵",
    "stone": "🪨",
    "iron": "⛓️",
    "gold": "💰",
}

RESOURCE_COLORS = {
    "food": (120, 200, 90),
    "wood": (160, 120, 60),
    "stone": (160, 160, 170),
    "iron": (180, 180, 200),
    "gold": (210, 175, 90),
}


def _lerp_color(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _draw_panel(surface, rect, bg=C_PANEL_BG, border=C_BORDER, alpha=None):
    """Dessine un panneau rectangulaire avec fond et bordure."""
    if alpha is not None:
        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        s.fill((*bg, alpha))
        surface.blit(s, rect.topleft)
    else:
        pygame.draw.rect(surface, bg, rect)
    pygame.draw.rect(surface, border, rect, 1)


def _draw_separator(surface, x1, y, x2, color=C_BORDER):
    pygame.draw.line(surface, color, (x1, y), (x2, y), 1)


class UIManager:
    """
    Gestionnaire centralisé de tous les boutons UI.

    Permet de gérer facilement plusieurs boutons sans dupliquer du code.
    """

    def __init__(self, game_engine: GameEngine, font):
        """Crée tous les boutons UI"""
        self.game_engine = game_engine
        self.font = font
        self.screen_width = gc.SCREEN_WIDTH
        self.screen_height = gc.SCREEN_HEIGHT

        self.resource_images = {}

        #  Fonts
        pygame.font.init()
        self._fnt_tiny = pygame.font.SysFont("consolas,monospace", 13)
        self._fnt_small = pygame.font.SysFont("consolas,monospace", 15)
        self._fnt_normal = pygame.font.SysFont("consolas,monospace", 17)
        self._fnt_big = pygame.font.SysFont("consolas,monospace", 20, bold=True)
        self._fnt_title = pygame.font.SysFont("consolas,monospace", 22, bold=True)

        #  Sidebar state
        self._sidebar_cur_w = float(gc.SIDEBAR_WIDTH)

        #  Boutons de la sidebar
        btn_w, btn_h = 170, 30

        self.placement_button = Button(
            x=0,
            y=0,
            width=btn_w,
            height=btn_h,
            text="▸ Placer unité (allié)",
            font=self._fnt_small,
            is_toggleable=True,
        )
        self.placement_button_enn = Button(
            x=0,
            y=0,
            width=btn_w,
            height=btn_h,
            text="▸ Placer unité (ennemi)",
            font=self._fnt_small,
            is_toggleable=True,
        )

        #  Bouton Fin du tour
        self.next_turn_button = Button(
            x=0,
            y=0,
            width=160,
            height=42,
            text="Fin du tour  ▶",
            font=self._fnt_big,
            is_toggleable=False,
        )

        #  Bouton Quitter
        self.quit_button = Button(
            x=0,
            y=0,
            width=90,
            height=26,
            text="✕  Quitter",
            font=self._fnt_small,
            is_toggleable=False,
        )

        #  Cache animation barre ressource
        self._res_anim = {}  # resource_name -> float (valeur affichée, lissée)

        #  Pulse animation fin de tour
        self._pulse_t = 0.0

        # Hovered tile info (set depuis main)
        self.hovered_tile = None
        self.hovered_unit = None
        self.fps_value = 60.0

    def load_resource_images(self):
        """Charge les images depuis le dossier img/ basé sur les noms des ressources."""
        img_path = Path(".") / "img"
        for res_name in ["food", "wood", "stone", "iron", "gold"]:
            try:
                img = pygame.image.load(img_path / f"{res_name}1.png").convert_alpha()
                self.resource_images[res_name] = pygame.transform.scale(img, (20, 20))
            except:
                self.resource_images[res_name] = None

    # Mise à jour

    def update_positions(self, screen_width, screen_height):
        """Met à jour les positions des boutons en fonction de la taille de l'écran"""
        self.screen_width = screen_width
        self.screen_height = screen_height

        sw, sh = screen_width, screen_height

        # Boutons dans la sidebar
        btn_x = 20
        self.placement_button.set_position(btn_x, self._sidebar_action_y(0))
        self.placement_button_enn.set_position(btn_x, self._sidebar_action_y(1))

        # Fin du tour, bas droite
        self.next_turn_button.set_position(
            sw - self.next_turn_button.rect.width - 16,
            sh - self.next_turn_button.rect.height - 16,
        )

        # Quitter, bas droite, au-dessus
        self.quit_button.set_position(
            sw - self.quit_button.rect.width - 16,
            sh - self.next_turn_button.rect.height - self.quit_button.rect.height - 24,
        )

    def _sidebar_action_y(self, index):
        """Y pour les boutons d'action dans la sidebar."""
        base_y = self._resource_section_end() + 16
        return base_y + index * 38

    def _resource_section_end(self):
        """Y de fin de la section ressources (pour positionner les boutons en dessous)."""
        n = len(self._get_resources())
        return 60 + n * 36 + 8

    def _get_resources(self):
        """Retourne le dict des ressources du joueur courant."""
        return self.game_engine.state.player_resources.get(
            self.game_engine.state.current_player, {}
        )

    def update(self, mouse_pos, dt):
        # Mettre à jour les positions
        self.update_positions(self.screen_width, self.screen_height)

        # Mettre à jour les boutons
        self.placement_button.update(mouse_pos, dt)
        self.placement_button_enn.update(mouse_pos, dt)
        self.next_turn_button.update(mouse_pos, dt)
        self.quit_button.update(mouse_pos, dt)

        # Lissage des ressources (animation de compteur)
        resources = self._get_resources()
        for name, val in resources.items():
            cur = self._res_anim.get(name, float(val))
            self._res_anim[name] = cur + (val - cur) * min(1.0, 8 * dt)

        # Pulse bouton fin de tour
        self._pulse_t += dt * 2.0

    # Dessin
    def draw(self, screen, selected_unit_type):
        cw = int(self._sidebar_cur_w)
        sw, sh = self.screen_width, self.screen_height

        #  Sidebar
        self._draw_sidebar(screen, cw, sh)

        #  Barre de statut bas
        self._draw_status_bar(screen, cw, sw, sh, selected_unit_type)

        #  Panneau infos tuile (bas gauche après sidebar)
        if self.hovered_tile:
            self._draw_tile_info(screen, cw, sh)

        #  Indicateur tour (haut droite)
        self._draw_turn_indicator(screen, sw)

        #  Boutons principaux
        self.next_turn_button.draw(screen)
        self.quit_button.draw(screen)

    #  Sidebar
    def _draw_sidebar(self, screen, cw, sh):
        # Fond principal
        sidebar_rect = pygame.Rect(0, 0, cw, sh)
        _draw_panel(screen, sidebar_rect, bg=C_PANEL_BG, border=C_BORDER)

        # Ligne de bordure droite plus visible
        pygame.draw.line(screen, C_BORDER_LIT, (cw, 0), (cw, sh), 1)

        alpha_content = 255

        #  Titre / joueur
        self._draw_player_header(screen, cw, alpha_content)

        #  Section ressources
        self._draw_resource_section(screen, cw, alpha_content)

        #  Boutons d'action
        self.placement_button.draw(screen)
        self.placement_button_enn.draw(screen)

    def _draw_player_header(self, screen, cw, alpha):
        state = self.game_engine.state
        player = state.current_player
        turn = state.turn

        # Bande colorée joueur
        player_colors = [
            (60, 110, 190),
            (190, 70, 60),
            (60, 170, 90),
            (190, 160, 50),
            (150, 60, 180),
        ]
        pc = player_colors[player % len(player_colors)]
        band = pygame.Surface((4, 44), pygame.SRCALPHA)
        band.fill((*pc, alpha))
        screen.blit(band, (0, 8))
        title = self._fnt_title.render(
            f"JOUEUR  {player + 1}", True, (*C_TEXT_BRIGHT, alpha) if False else C_TEXT_BRIGHT
        )
        screen.blit(title, (14, 12))
        sub = self._fnt_tiny.render(f"Tour {turn}", True, C_TEXT_DIM)
        screen.blit(sub, (14, 36))
        _draw_separator(screen, 0, 54, cw)

    def _draw_resource_section(self, screen, cw, alpha):
        resources = self._get_resources()
        y = 62
        label = self._fnt_tiny.render("RESSOURCES", True, C_TEXT_DIM)
        screen.blit(label, (14, y))
        y += 18
        for name, amount in resources.items():
            disp_val = self._res_anim.get(name, float(amount))
            self._draw_resource_row(screen, cw, name, int(disp_val), amount, y)
            y += 36

        # Séparateur après ressources
        _draw_separator(screen, 0, y, cw)

    def _draw_resource_row(self, screen, panel_w, name, disp, real, y):
        icon = RESOURCE_ICONS.get(name, "-")
        color = RESOURCE_COLORS.get(name, C_TEXT)

        # Fond de la rangée
        row_rect = pygame.Rect(4, y, panel_w - 8, 30)
        bg_surf = pygame.Surface((row_rect.width, row_rect.height), pygame.SRCALPHA)
        bg_surf.fill((*C_PANEL_BG2, 180))
        screen.blit(bg_surf, row_rect.topleft)
        pygame.draw.rect(screen, C_BORDER, row_rect, 1)

        # Icône
        icon_surf = self._fnt_normal.render(icon, True, color)
        screen.blit(icon_surf, (12, y + 7))

        # Nom ressource
        name_surf = self._fnt_small.render(name.upper(), True, C_TEXT_DIM)
        screen.blit(name_surf, (30, y + 9))

        # Valeur (droite alignée)
        val_text = f"+{real}" if real >= 0 else str(real)
        val_color = C_GREEN if real > 0 else (C_TEXT_DIM if real == 0 else C_RED)
        val_surf = self._fnt_big.render(val_text, True, val_color)
        screen.blit(val_surf, (panel_w - val_surf.get_width() - 12, y + 6))

    #  Barre de statut
    def _draw_status_bar(self, screen, cw, sw, sh, selected_unit_type):
        bar_rect = pygame.Rect(0, sh - gc.STATUS_H, sw, gc.STATUS_H)
        _draw_panel(screen, bar_rect, bg=C_PANEL_BG, border=C_BORDER)
        pygame.draw.line(screen, C_BORDER_LIT, (0, sh - gc.STATUS_H), (sw, sh - gc.STATUS_H), 1)

        x_cur = cw + 12

        # FPS
        fps_s = self._fnt_tiny.render(f"FPS {self.fps_value:.0f}", True, C_TEXT_DIM)
        screen.blit(fps_s, (x_cur, sh - gc.STATUS_H + 6))
        x_cur += fps_s.get_width() + 20

        # Seed
        seed_s = self._fnt_tiny.render(f"seed {self.game_engine.state.map.seed}", True, C_TEXT_DIM)
        screen.blit(seed_s, (x_cur, sh - gc.STATUS_H + 6))
        x_cur += seed_s.get_width() + 24

        # Infos tuile survolée
        if self.hovered_tile:
            tile = self.hovered_tile
            parts = [
                (f"Tile #{tile.id}", C_TEXT),
                (f"  {tile.biome.name}", C_BLUE_ACC),
                (f"  {tile.resource.name}", C_GOLD if tile.resource.name != "NONE" else C_TEXT_DIM),
                (f"  aire {tile.area}", C_TEXT_DIM),
            ]
            for text, color in parts:
                s = self._fnt_small.render(text, True, color)
                screen.blit(s, (x_cur, sh - gc.STATUS_H + 16))
                x_cur += s.get_width()

            # Unités sur la tuile
            if tile.has_units():
                u = tile.units[0]
                u_s = self._fnt_small.render(
                    f"  ◆ {u.unit_type.name} (j{u.owner+1})", True, C_GREEN
                )
                screen.blit(u_s, (x_cur, sh - gc.STATUS_H + 16))

        # Raccourcis clavier (droite)
        hint = self._fnt_tiny.render(
            f"1-4 : type unité  | Unité courante : {selected_unit_type.name} | Esc : déselect  |  R : nouvelle carte  |  clic droit : fonder ville",
            True,
            C_TEXT_DIM,
        )
        screen.blit(hint, (sw - hint.get_width() - 16, sh - gc.STATUS_H + 34))

    #  Panneau infos tuile
    def _draw_tile_info(self, screen, cw, sh):
        pass  # Intégré dans la status bar

    #  Indicateur tour
    def _draw_turn_indicator(self, screen, sw):
        state = self.game_engine.state
        turn = state.turn
        player = state.current_player

        panel_w, panel_h = 170, 42
        panel_x = sw - panel_w - 16
        panel_y = 12

        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        _draw_panel(screen, panel_rect, bg=C_PANEL_BG, border=C_BORDER_LIT)

        # Pulse border pour "ton tour"
        pulse = (math.sin(self._pulse_t) + 1) / 2
        pb = _lerp_color(C_BORDER, C_BLUE_ACC, pulse * 0.5)
        pygame.draw.rect(screen, pb, panel_rect, 1)

        t1 = self._fnt_big.render(f"Tour  {turn}", True, C_TEXT_BRIGHT)
        screen.blit(t1, (panel_x + 12, panel_y + 6))

        player_colors = [(80, 130, 210), (210, 80, 70), (70, 190, 100)]
        pc_text = _lerp_color(C_TEXT_DIM, player_colors[player % 3], 1.0)
        t2 = self._fnt_tiny.render(f"Joueur {player + 1}", True, pc_text)
        screen.blit(t2, (panel_x + 12, panel_y + 26))

    # Gestion des clics
    def handle_click(self, mouse_pos, game_map, selected_unit_type, selected_unit_water_affinity):
        # Languette toggle sidebar
        cw = int(self._sidebar_cur_w)
        sh = self.screen_height

        # Bouton placer unité allié
        if self.placement_button.is_clicked(mouse_pos):
            self.placement_button.toggle()
            if self.placement_button.is_active:
                self.placement_button_enn.set_active(False)
            return None

        # Bouton placer unité ennemi
        if self.placement_button_enn.is_clicked(mouse_pos):
            self.placement_button_enn.toggle()
            if self.placement_button_enn.is_active:
                self.placement_button.set_active(False)
            return None

        # Fin du tour
        if self.next_turn_button.is_clicked(mouse_pos):
            return "next_turn"

        # Quitter
        if self.quit_button.is_clicked(mouse_pos):
            return "quit"

        return None

    def is_mouse_over_ui(self, mouse_pos):
        """Retourne True si la souris est sur un élément d'interface."""
        cw = int(self._sidebar_cur_w)
        sh = self.screen_height

        # Sidebar
        if mouse_pos[0] < cw:
            return True

        # Languette
        tab_rect = pygame.Rect(cw, sh // 2 - 24, 14, 48)
        if tab_rect.collidepoint(mouse_pos):
            return True

        # Barre de statut bas
        if mouse_pos[1] > sh - gc.STATUS_H:
            return True

        # Boutons droite
        if self.next_turn_button.rect.collidepoint(mouse_pos):
            return True
        if self.quit_button.rect.collidepoint(mouse_pos):
            return True

        return False

    # Compat legacy (main.py utilise ces attributs directement)

    # Exposer toggle_sidebar_button comme no-op pour éviter les AttributeError
    class _NoOpButton:
        rect = pygame.Rect(0, 0, 0, 0)
        is_active = False

        def is_clicked(self, _):
            return False

        def draw(self, _):
            pass

        def update(self, *_):
            pass

    toggle_sidebar_button = _NoOpButton()
