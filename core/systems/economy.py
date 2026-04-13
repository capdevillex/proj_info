from core.game_state import GameState


class Economy:
    def update(self, game_state: GameState):
        """Met à jour les ressources du joueur en fonction des unités et des villes."""

        # Calculer les ressources générées par les villes
        self.process_city_production(game_state)

        # Calculer les coûts d'entretien des unités
        for unit in game_state.units:
            if unit.owner == game_state.current_player:
                game_state.player_resources[unit.owner]["gold"] -= unit.upkeep_cost

    def process_city_production(self, game_state: GameState):
        """
        Traite la production de toutes les villes pour le tour actuel.

        Calcule la production de chaque ville et l'ajoute aux ressources du joueur.
        """
        for city in game_state.cities:
            # Calculer la production de la ville
            city.calculate_production(game_state.map)

            # Ajouter la production aux ressources du joueur
            if city.owner not in game_state.player_resources:
                game_state.player_resources[city.owner] = {
                    "food": 0,
                    "wood": 0,
                    "stone": 0,
                    "iron": 0,
                    "gold": 0,
                }

            for resource_type, amount in city.production.items():
                game_state.player_resources[city.owner][resource_type] += amount
