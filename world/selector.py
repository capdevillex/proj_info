"""
Module de gestion de la sélection d'unités.

Gère :
- Sélection/désélection d'une unité
- Affichage des zones accessibles
- Déplacement quand on clique sur une zone
"""

from world.movement import get_reachable_tiles, is_tile_reachable


class UnitSelector:
    """
    Gestionnaire de la sélection d'unités et des zones de mouvement.
    
    Permet de :
    - Sélectionner une unité
    - Afficher les zones accessibles en bleu transparent
    - Déplacer l'unité si on clique sur une zone accessible
    """
    
    def __init__(self):
        self.selected_unit = None
        self.reachable_tiles = set()
    
    def select_unit(self, unit, map_):
        """
        Sélectionne une unité et calcule ses zones accessibles.
        
        Args:
            unit: L'unité à sélectionner
            map_: L'objet Map
        """
        self.selected_unit = unit
        
        # Si l'unité peut bouger, calculer les zones accessibles
        if unit.can_move():
            self.reachable_tiles = get_reachable_tiles(map_, unit)
        else:
            self.reachable_tiles = set()
    
    def deselect_unit(self):
        """Désélectionne l'unité actuelle."""
        self.selected_unit = None
        self.reachable_tiles = set()
    
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
        if not is_tile_reachable(map_, self.selected_unit, target_tile_id):
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
        """Retourne l'ensemble des tuiles accessibles."""
        return self.reachable_tiles
