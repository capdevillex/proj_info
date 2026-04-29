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
from ui.camera import Camera, world_to_screen
from ui.renderer import RenderPipeline
from ui.ui_utils import compute_tile_size
from world.biome import Biome
from world.construction import Farm, Mine, Road, Scierie
from world.resources import Resource
from world.tile import Tile

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
    """Dessine un panneau rectangulaire avec fond et bordure.
    Le paramètre alpha est conservé pour compatibilité mais ignoré :
    les panels UI sont tous opaques, pas de SRCALPHA."""
    pygame.draw.rect(surface, bg, rect)
    pygame.draw.rect(surface, border, rect, 1)


def _draw_separator(surface, x1, y, x2, color=C_BORDER):
    pygame.draw.line(surface, color, (x1, y), (x2, y), 1)


class UIManager:
    """
    Gestionnaire centralisé de tous les boutons UI.

    Permet de gérer facilement plusieurs boutons sans dupliquer du code.
    """

    def __init__(self, game_engine: GameEngine, renderer: RenderPipeline, font, camera: Camera):
        """Crée tous les boutons UI"""
        self.game_engine = game_engine
        self.renderer = renderer
        self.font = font
        self.screen_width = gc.SCREEN_WIDTH
        self.screen_height = gc.SCREEN_HEIGHT
        self.camera = camera

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
            text="Placer unité (allié)",
            font=self._fnt_small,
            is_toggleable=True,
        )
        self.placement_button_enn = Button(
            x=0,
            y=0,
            width=btn_w,
            height=btn_h,
            text="Placer unité (ennemi)",
            font=self._fnt_small,
            is_toggleable=True,
        )
        self.toogle_fow_button = Button(
            x=0,
            y=0,
            width=btn_w,
            height=btn_h,
            text="Use FoW",
            font=self._fnt_small,
            is_toggleable=True,
        )
        self.toogle_TI_button = Button(
            x=0,
            y=0,
            width=btn_w,
            height=btn_h,
            text="Use TI",
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

        # --- Surface de fond de la sidebar (statique entre fin de tour et resize) ---
        # Les boutons et éléments dynamiques (hover, pulse) sont dessinés
        # directement sur l'écran par-dessus cette surface.
        self._sidebar_bg_sf: pygame.Surface | None = None
        self._sidebar_dirty = True
        # Dimensions ayant servi au dernier build (pour détecter un resize)
        self._sidebar_built_size: tuple[int, int] = (0, 0)

        # Surface pour le menu de construction
        self._construction_sf: pygame.Surface | None = None
        self._construction_menu_options = []
        self._construction_menu_visible = False
        self._construction_menu_pos = (0, 0)
        self._construction_menu_tile = None
        self._construction_buttons = []
        self._construction_anchor_world: tuple[float, float] | None = None

    def load_resource_images(self):
        """Charge les images depuis le dossier img/ basé sur les noms des ressources."""
        img_path = Path(".") / "img"
        for res_name in ["food", "wood", "stone", "iron", "gold"]:
            try:
                img = pygame.image.load(img_path / f"{res_name}1.png").convert_alpha()
                self.resource_images[res_name] = pygame.transform.scale(img, (20, 20))
            except:
                self.resource_images[res_name] = None

    def mark_dirty(self):
        """Invalide la surface cachée de la sidebar. À appeler après un changement
        d'état (fin de tour, resize fenêtre) pour forcer un rebuild au prochain draw."""
        self._sidebar_dirty = True

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
        self.toogle_fow_button.set_position(btn_x, self._sidebar_action_y(2))
        self.toogle_TI_button.set_position(btn_x, self._sidebar_action_y(3))

        # Fin du tour, bas droite
        self.next_turn_button.set_position(
            sw - self.next_turn_button.rect.width - 16,
            sh - self.next_turn_button.rect.height - 16 - gc.STATUS_H,
        )

        # Quitter, bas droite, au-dessus
        self.quit_button.set_position(
            sw - self.quit_button.rect.width - 16,
            sh
            - self.next_turn_button.rect.height
            - self.quit_button.rect.height
            - 24
            - gc.STATUS_H,
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
        self.toogle_fow_button.update(mouse_pos, dt)
        self.toogle_TI_button.update(mouse_pos, dt)
        self.next_turn_button.update(mouse_pos, dt)
        self.quit_button.update(mouse_pos, dt)

        # Mettre à jour les boutons du menu de construction
        if self._construction_menu_visible:
            if self._construction_anchor_world is not None:
                self._update_construction_buttons_pos()
            for btn, _, _ in self._construction_buttons:
                btn.update(mouse_pos, dt)

        # Lissage des ressources (animation de compteur)
        resources = self._get_resources()
        for name, val in resources.items():
            cur = self._res_anim.get(name, float(val))
            self._res_anim[name] = cur + (val - cur) * min(1.0, 8 * dt)

        # Pulse bouton fin de tour
        self._pulse_t += dt * 2.0

    # Dessin
    def draw(self, screen, selected_unit_type, mouse_pos):
        cw = int(self._sidebar_cur_w)
        sw, sh = self.screen_width, self.screen_height

        # --- Sidebar : rebuild uniquement si dirty ou resize ---
        if self._sidebar_dirty or self._sidebar_built_size != (cw, sh):
            self._rebuild_sidebar_bg(cw, sh)
        screen.blit(self._sidebar_bg_sf, (0, 0))

        # --- Status bar : toujours redessinée (contient fps, tuile survolée) ---
        # Aucune allocation SRCALPHA dedans, le coût est négligeable.
        self._draw_status_bar(screen, cw, sw, sh, selected_unit_type)

        # --- Éléments dynamiques dessinés par-dessus ---
        # Indicateur de tour (pulse animé)
        self._draw_turn_indicator(screen, sw)

        # --- Menus de construction ---
        self._draw_construction_menu(screen)

        # Boutons : hover + active state changent à chaque frame
        self.placement_button.draw(screen)
        self.placement_button_enn.draw(screen)
        self.toogle_fow_button.draw(screen)
        self.toogle_TI_button.draw(screen)
        self.next_turn_button.draw(screen)
        self.quit_button.draw(screen)

    # --- Builders de surfaces cachées ---

    def _rebuild_sidebar_bg(self, cw: int, sh: int):
        """Reconstruit la surface de fond de la sidebar (sans les boutons)."""
        sf = pygame.Surface((cw, sh))
        self._draw_sidebar(sf, cw, sh)
        self._sidebar_bg_sf = sf
        self._sidebar_dirty = False
        self._sidebar_built_size = (cw, sh)

    def _rebuild_construction_menu(self, tile: Tile, pos: tuple):
        """Construit le menu de construction pour une tuile donnée."""

        # Déterminer les options disponibles selon le biome
        options = []
        if tile and tile.biome != Biome.WATER:
            has_road = any(c.name == "Route" for c in tile.constructions)
            has_building = any(c.name != "Route" for c in tile.constructions)

            if not has_road:
                options.append(("Route", Road.COST))

            if not has_building:
                if tile.biome in [Biome.PLAIN, Biome.FOREST]:
                    options.append(("Ferme", Farm.COST))
                if tile.biome == Biome.FOREST:
                    options.append(("Scierie", Scierie.COST))
                if tile.biome == Biome.MOUNTAIN:
                    options.append(("Mine", Mine.COST))
                if tile.resource in [
                    Resource.STONE1,
                    Resource.STONE2,
                    Resource.STONE3,
                    Resource.IRON1,
                    Resource.IRON2,
                    Resource.IRON3,
                    Resource.GOLD1,
                    Resource.GOLD2,
                    Resource.GOLD3,
                ]:
                    options.append(("Mine", Mine.COST))

        self._construction_menu_options = options
        self._construction_menu_tile = tile
        self._construction_menu_pos = pos

        # Créer les boutons pour chaque option
        self._construction_buttons = []
        y_offset = gc.CONSTRUCTION_MENU_PADDING

        for i, (name, cost) in enumerate(options):
            btn = Button(
                x=pos[0] + gc.CONSTRUCTION_MENU_PADDING,
                y=pos[1] + y_offset,
                width=gc.CONSTRUCTION_MENU_WIDTH - 2 * gc.CONSTRUCTION_MENU_PADDING,
                height=gc.CONSTRUCTION_MENU_ITEM_H,
                text=name,
                font=self._fnt_normal,
                is_toggleable=False,
            )
            self._construction_buttons.append((btn, name, cost))
            y_offset += gc.CONSTRUCTION_MENU_ITEM_H + gc.CONSTRUCTION_MENU_PADDING

    def _get_construction_menu_rect(self):
        if not self._construction_menu_options:
            return None
        pos = self._construction_menu_pos
        menu_height = (
            len(self._construction_menu_options)
            * (gc.CONSTRUCTION_MENU_ITEM_H + gc.CONSTRUCTION_MENU_PADDING)
            + gc.CONSTRUCTION_MENU_PADDING
        )
        return pygame.Rect(pos[0], pos[1], gc.CONSTRUCTION_MENU_WIDTH, menu_height)

    def _compute_menu_screen_pos(self) -> tuple[int, int]:
        """Convertit l'ancre monde (centre tuile) en position écran, avec clamping."""
        assert self._construction_anchor_world is not None
        wx, wy = self._construction_anchor_world
        sx, sy = world_to_screen(wx, wy, self.camera.x, self.camera.y, self.camera.zoom)
        sx += 12
        sy += 12
        menu_height = (
            len(self._construction_menu_options)
            * (gc.CONSTRUCTION_MENU_ITEM_H + gc.CONSTRUCTION_MENU_PADDING)
            + gc.CONSTRUCTION_MENU_PADDING
        )
        sx = max(gc.SIDEBAR_WIDTH + 4, min(sx, self.screen_width - gc.CONSTRUCTION_MENU_WIDTH - 4))
        sy = max(4, min(sy, self.screen_height - gc.STATUS_H - menu_height - 4))
        return (sx, sy)

    def _update_construction_buttons_pos(self) -> None:
        """Repositionne les boutons du menu d'après la position écran courante."""
        pos = self._compute_menu_screen_pos()
        self._construction_menu_pos = pos
        y_offset = gc.CONSTRUCTION_MENU_PADDING
        for btn, _, _ in self._construction_buttons:
            btn.set_position(pos[0] + gc.CONSTRUCTION_MENU_PADDING, pos[1] + y_offset)
            y_offset += gc.CONSTRUCTION_MENU_ITEM_H + gc.CONSTRUCTION_MENU_PADDING

    def close_construction_menu(self):
        self._construction_menu_visible = False
        self._construction_anchor_world = None

    #  Sidebar (dessine sur la surface passée en argument — écran ou cache)
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

        # Note : les boutons (placement_button, placement_button_enn) sont dessinés
        # directement sur l'écran dans draw() — pas dans le cache.

    def _draw_construction_menu(self, screen):
        """Dessine le menu de construction à l'écran."""
        if not self._construction_menu_visible or not self._construction_menu_options:
            return

        pos = self._construction_menu_pos
        menu_height = (
            len(self._construction_menu_options)
            * (gc.CONSTRUCTION_MENU_ITEM_H + gc.CONSTRUCTION_MENU_PADDING)
            + gc.CONSTRUCTION_MENU_PADDING
        )

        # Fond du menu
        menu_rect = pygame.Rect(pos[0], pos[1], gc.CONSTRUCTION_MENU_WIDTH, menu_height)
        _draw_panel(screen, menu_rect, bg=C_PANEL_BG2, border=C_BORDER_LIT)

        # Dessiner chaque bouton avec son coût
        for btn, name, cost in self._construction_buttons:
            btn.draw(screen)

            # Afficher le coût à côté du nom
            cost_text = ", ".join([f"{amount} {res}" for res, amount in cost.items()])
            cost_surf = self._fnt_tiny.render(cost_text, True, C_TEXT_DIM)
            screen.blit(cost_surf, (btn.rect.x + 10, btn.rect.y + btn.rect.height - 16))

    def _draw_player_header(self, screen, cw, alpha):
        state = self.game_engine.state
        player = state.current_player
        turn = state.turn

        # Bande colorée joueur — opaque, pas besoin de SRCALPHA
        player_colors = [
            (60, 110, 190),
            (190, 70, 60),
            (60, 170, 90),
            (190, 160, 50),
            (150, 60, 180),
        ]
        pc = player_colors[player % len(player_colors)]
        pygame.draw.rect(screen, pc, (0, 8, 4, 44))
        title = self._fnt_title.render(f"JOUEUR  {player + 1}", True, C_TEXT_BRIGHT)
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

        # Fond de la rangée : opaque, pas besoin de SRCALPHA
        row_rect = pygame.Rect(4, y, panel_w - 8, 30)
        pygame.draw.rect(screen, C_PANEL_BG2, row_rect)
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
        """Dessine la barre de statut directement sur l'écran (coordonnées absolues)."""
        y_offset = sh - gc.STATUS_H
        bar_rect = pygame.Rect(0, y_offset, sw, gc.STATUS_H)
        _draw_panel(screen, bar_rect, bg=C_PANEL_BG, border=C_BORDER)
        pygame.draw.line(screen, C_BORDER_LIT, (0, y_offset), (sw, y_offset), 1)

        x_cur = cw + 12
        text_y = y_offset + 6

        # FPS
        fps_s = self._fnt_tiny.render(f"FPS {self.fps_value:.1f}", True, C_TEXT_DIM)
        screen.blit(fps_s, (x_cur, text_y))
        x_cur += fps_s.get_width() + 20

        # Zoom
        fps_s = self._fnt_tiny.render(f"Zoom {self.camera.zoom:.5f}", True, C_TEXT_DIM)
        screen.blit(fps_s, (x_cur, text_y))
        x_cur += fps_s.get_width() + 20

        # Seed
        seed_s = self._fnt_tiny.render(f"seed {self.game_engine.state.map.seed}", True, C_TEXT_DIM)
        screen.blit(seed_s, (x_cur, text_y))
        x_cur += seed_s.get_width() + 24

        # Infos tuile survolée
        if self.hovered_tile:
            tile: Tile = self.hovered_tile
            parts = [
                (f"Tile #{tile.id}", C_TEXT),
                (f"  {tile.biome.name}", C_BLUE_ACC),
                (f"  {tile.resource.name}", C_GOLD if tile.resource.name != "NONE" else C_TEXT_DIM),
                (f"  aire {tile.area}", C_TEXT_DIM),
            ]
            if tile.constructions:
                names = ", ".join(c.name for c in tile.constructions)
                parts.append((f"  [{names}]", C_GOLD))
            for text, color in parts:
                s = self._fnt_small.render(text, True, color)
                screen.blit(s, (x_cur, y_offset + 16))
                x_cur += s.get_width()

            if tile.has_units():
                u = tile.units[0]
                u_s = self._fnt_small.render(
                    f"  ◆ {u.unit_type.name} (j{u.owner+1})", True, C_GREEN
                )
                screen.blit(u_s, (x_cur, y_offset + 16))

        # Raccourcis clavier (droite)
        hint = self._fnt_tiny.render(
            f"1-4 : type unité  | Unité courante : {selected_unit_type.name} | Esc : déselect  |  R : nouvelle carte  |  clic droit : fonder ville",
            True,
            C_TEXT_DIM,
        )
        screen.blit(hint, (sw - hint.get_width() - 16, y_offset + 34))

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
    def handle_click(self, mouse_pos, game_map, selected_unit_type):
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

        # Bouton toggle FoW
        if self.toogle_fow_button.is_clicked(mouse_pos):
            self.toogle_fow_button.toggle()
            self.game_engine.state.use_fow = self.toogle_fow_button.is_active
            self.renderer.clear_cache()
            self.game_engine.state.update_fow()
            return None

        # Bouton toggle TI
        if self.toogle_TI_button.is_clicked(mouse_pos):
            self.toogle_TI_button.toggle()
            self.game_engine.state.use_ti = self.toogle_TI_button.is_active
            self.renderer.clear_cache()
            return None

        # Fin du tour
        if self.next_turn_button.is_clicked(mouse_pos):
            return "next_turn"

        # Quitter
        if self.quit_button.is_clicked(mouse_pos):
            return "quit"

        # Menu de construction
        if self._construction_menu_visible:
            menu_rect = self._get_construction_menu_rect()
            if menu_rect and menu_rect.collidepoint(mouse_pos):
                for btn, name, _ in self._construction_buttons:
                    if btn.is_clicked(mouse_pos):
                        self._construction_menu_visible = False
                        return ("build", name, self._construction_menu_tile)
                return None  # clic sur le fond du menu, consommer sans action
            else:
                self._construction_menu_visible = False

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

    def open_construction_menu(self, hovered_tile: Tile):
        """Ouvre le menu de construction ancré sur le centre de la tuile."""
        ts = compute_tile_size(self.screen_width, self.screen_height)
        self._construction_anchor_world = (
            hovered_tile.center[0] * ts,
            hovered_tile.center[1] * ts,
        )

        # Construit les options/boutons (pos provisoire, corrigée juste après)
        self._rebuild_construction_menu(hovered_tile, (0, 0))

        if not self._construction_menu_options:
            self._construction_menu_visible = False
            self._construction_anchor_world = None
            return

        self._update_construction_buttons_pos()
        self._construction_menu_visible = True

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
