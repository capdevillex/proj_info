class Economy:
    def update(self, game_state):
        """Met à jour les ressources du joueur en fonction des unités et des villes."""

        # Calculer les ressources générées par les villes
        for city in game_state.cities:
            if city.owner == game_state.current_player:
                game_state.resources["gold"] += city.gold_output
                game_state.resources["food"] += city.food_output
                game_state.resources["production"] += city.production_output

        # Calculer les coûts d'entretien des unités
        for unit in game_state.units:
            if unit.owner == game_state.current_player:
                game_state.resources["gold"] -= unit.upkeep_cost
