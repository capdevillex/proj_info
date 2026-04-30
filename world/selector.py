"""
Module de gestion de la sélection d'unités.

Gère :
- Sélection/désélection d'une unité
- Affichage des zones accessibles (mouvement en bleu)
- Affichage des zones attaquables (combat en rouge)
- Déplacement ou attaque quand on clique sur une zone
"""

from core.systems.movement import Movement


class UnitSelector:
    """
    Gestionnaire de la sélection d'unités et des zones de mouvement/combat.

    Permet de :
    - Sélectionner une unité
    - Afficher les zones accessibles en bleu transparent (mouvement)
    - Afficher les zones attaquables en rouge transparent (combat)
    - Déplacer l'unité si on clique sur une zone accessible
    - Attaquer si on clique sur une zone attaquable
    """

    def __init__(self):
        self.selected_unit = None
        self.reachable_tiles = set()      # Tuiles accessibles pour le mouvement (BLEU)
        self.attackable_tiles = set()     # Tuiles avec unités ennemies attaquables (ROUGE)

    def select_unit(self, unit, state):
        """
        Sélectionne une unité et calcule ses zones accessibles et attaquables.

        Args:
            unit: L'unité à sélectionner
            state: L'objet GameState pour accéder à la carte et aux autres informations nécessaires
        """
        map_ = state.map
        self.selected_unit = unit

        # Si l'unité peut bouger, calculer les zones accessibles
        if unit.can_move():
            self.reachable_tiles = Movement.get_reachable_tiles(state, unit)
        else:
            self.reachable_tiles = set()

        # Calculer les zones attaquables (indépendamment de can_move)
        if unit.attack_range > 0:
            self.attackable_tiles = Movement.get_attackable_tiles(map_, unit)
        else:
            self.attackable_tiles = set()

    def deselect_unit(self):
        """Désélectionne l'unité actuelle."""
        self.selected_unit = None
        self.reachable_tiles = set()
        self.attackable_tiles = set()

    def try_move(self, map_, target_tile_id):
        """
        Essaie de déplacer l'unité sélectionnée vers une tuile cible.

        Args:
            map_: L'objet Map
            target_tile_id: ID de la tuile cible

        Returns:
            bool: True si le déplacement a réussi
        """
        if not self.selected_unit:
            return False

        # Vérifier que la cible est accessible
        if target_tile_id not in self.reachable_tiles:
            return False

        # Déplacer l'unité
        old_tile_id = self.selected_unit.tile_id
        new_tile_id = target_tile_id

        # Retirer de l'ancienne tuile
        old_tile = map_.tiles[old_tile_id]
        old_tile.remove_unit(self.selected_unit)

        # Ajouter à la nouvelle tuile
        new_tile = map_.tiles[new_tile_id]
        self.selected_unit.move_to_tile(new_tile_id)
        new_tile.add_unit(self.selected_unit)

        # Désélectionner après le mouvement
        self.deselect_unit()

        return True

    def is_unit_selected(self):
        """Retourne True si une unité est sélectionnée."""
        return self.selected_unit is not None

    def get_selected_unit(self):
        """Retourne l'unité sélectionnée (ou None)."""
        return self.selected_unit

    def get_reachable_tiles(self):
        """Retourne l'ensemble des tuiles accessibles (mouvement)."""
        return self.reachable_tiles

    def get_attackable_tiles(self):
        """Retourne l'ensemble des tuiles attaquables (combat)."""
        return self.attackable_tiles

    def is_tile_attackable(self, tile_id):
        """Vérifie si une tuile contient une unité ennemie attaquable."""
        return tile_id in self.attackable_tiles

    def is_tile_reachable(self, tile_id):
        """Vérifie si une tuile est accessible pour le mouvement."""
        return tile_id in self.reachable_tiles
