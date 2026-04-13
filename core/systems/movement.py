class Movement:
    """Système de gestion des mouvements des unités."""

    def move(self, state, unit_id, target_tile):
        unit = state.units[unit_id]

        if not self.is_valid_move(state, unit, target_tile):
            return False

        unit.position = target_tile
        unit.movement_points -= 1

        return True

    def is_valid_move(self, game_state, unit, target_tile):
        """Vérifie si le mouvement est valide."""
        # Implémenter la logique de validation du mouvement (ex: distance maximale)
        return True  # Placeholder pour la validation du mouvement
