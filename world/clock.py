class TurnManager:
    def __init__(self):
        self.current_turn = 1

    def next_turn(self, game_map):
        self.current_turn += 1
        print(f"\nET attention pour le changement de tour !\nTour N°{self.current_turn} !")

        for tile in game_map.tiles.values():
            for unit in tile.units:
                unit.reset_movement()
        
        # C'est ici (plus tard) qu''on pourras dire :
        # - Redonner des points de mouvement aux unités
        # - Récolter l'or des villes
        # - Soigner les unités, etc.