from core.game_state import GameState


class Visibility:
    def __init__(self, state: GameState) -> None:
        self.state = state

    def update(self, state: GameState):
        """Met à jour les cellules visibles pour le joueur actuel en fonction de ses unités."""
        state.update_fow()

    def calculate_visible_tiles(self, unit, map_):
        """
        Calcule les cellules visibles pour une unité donnée.
        La visibilité de base est la province de l'unité plus les provinces adjacentes.
        Des bonus de visibilité peuvent être ajoutés en fonction du terrain ou d'autres facteurs.
        Args:
            unit (Unit): L'unité pour laquelle calculer la visibilité
            map_ (Map): La carte du jeu, nécessaire pour accéder aux provinces et à leurs voisins
        Returns:
            Set[int]: Un ensemble d'identifiants de cellules visibles
        """
        visible = {unit.tile_id}  # Commencer par les cellules de la province

        # Ajouter les provinces adjacentes
        for neighbor_id in map_.tiles[unit.tile_id].neighbors:
            neighbor_tile = map_.tiles[neighbor_id]
            visible.update(neighbor_tile.cells)
            # ajouter bonus de visibilité terrain ici plus tard

        return visible
