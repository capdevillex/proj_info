class CombatSystem:
    def resolve(self, state, attacker_id, defender_id):
        attacker = state.units[attacker_id]
        defender = state.units[defender_id]

        damage = self.compute_damage(attacker, defender)

        defender.hp -= damage

        if defender.hp <= 0:
            state.units.remove(defender)

    def compute_damage(self, attacker, defender):
        """Calcule les dégâts infligés par l'attaquant au défenseur."""
        # Implémenter la logique de calcul des dégâts
        return 10  # Placeholder pour les dégâts infligés
