"""
Module de persistance : sauvegarde et chargement d'une partie au format JSON.

Choix du format
---------------
Nous utilisons le JSON (et non `pickle`), pour trois raisons :
    1. lisibilité : un fichier de sauvegarde est inspectable et éditable à la main ;
    2. portabilité : indépendant de la version de Python et des classes internes ;
    3. sûreté : `pickle` exécute du code arbitraire à la lecture, pas le JSON.

Astuce de conception
---------------------
La génération de la carte est purement déterministe (pilotée par une seed).
Une sauvegarde n'a donc PAS besoin de stocker les ~110 000 cellules de la carte :
il suffit de stocker les paramètres de génération (seed, dimensions, taille de
tuile). Au chargement, on régénère la carte à l'identique, puis on y replace
l'état dynamique (unités, villes, ressources, tour, brouillard de guerre).
Le fichier de sauvegarde reste ainsi très léger (quelques Ko).

Author : Victor
"""

import json

from core.game_state import GameState, TurnPhase
from world.kingdom import Kingdom
from world.unit import Unit, UnitType, UNIT_CLASS_MAP
from world.city import City
from world.construction import Farm, Mine, Road, Scierie

# Version du format : permet de rejeter (ou migrer) une sauvegarde incompatible.
SAVE_FORMAT_VERSION = 1

# Reconstruction des bâtiments à partir de leur nom (même table que GameEngine).
_CONSTRUCTION_CLASSES = {"Ferme": Farm, "Mine": Mine, "Route": Road, "Scierie": Scierie}


def save_game(state: GameState, path: str) -> dict:
    """Écrit l'état complet d'une partie dans un fichier JSON.

    Args:
        state: l'état de jeu courant à sauvegarder.
        path:  chemin du fichier de sauvegarde (ex. "saves/partie1.json").

    Returns:
        dict: le dictionnaire effectivement sérialisé (utile pour les tests).
    """
    data = {
        "version": SAVE_FORMAT_VERSION,
        # Carte : uniquement les paramètres de génération (déterministe)
        "map": state.map.serialize(),
        # État global du tour
        "turn": state.turn,
        "current_player": state.current_player,
        "current_kingdom_idx": state.current_kingdom_idx,
        "phase": state.phase.name,
        "turn_order": list(state.turn_order),
        # Brouillard de guerre / terra incognita
        "use_ti": state.use_ti,
        "use_fow": state.use_fow,
        "discovered": state.discovered,
        "visibility": state.visibility,
        # Royaumes (joueur + IA)
        "kingdoms": [
            {
                "kingdom_id": k.kingdom_id,
                "name": k.name,
                "color": list(k.color),
                "is_ai": k.is_ai,
                "cities": list(k.cities),
                "ai_params": k.ai_params,
            }
            for k in state.kingdoms
        ],
        # Ressources (clés int -> str pour le JSON)
        "resources": {str(kid): res for kid, res in state.player_resources.items()},
        # Unités
        "units": [
            {
                "id": u.id,
                "type": u.unit_type.name,
                "tile_id": u.tile_id,
                "owner": u.owner,
                "x": u.x,
                "y": u.y,
                "hp": u.hp,
                "has_moved": u.has_moved,
                "has_attacked": u.has_attacked,
            }
            for u in state.units
        ],
        # Villes
        "cities": [
            {
                "id": c.id,
                "name": c.name,
                "owner": c.owner,
                "center_tile_id": c.center_tile_id,
                "tile_ids": sorted(c.tile_ids),
                "population": c.population,
                "age": c.age,
                "production": c.production,
            }
            for c in state.cities
        ],
        # Constructions, indexées par tuile (uniquement les tuiles bâties)
        "constructions": {
            str(tid): [cons.name for cons in tile.constructions]
            for tid, tile in state.map.tiles.items()
            if tile.constructions
        },
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


def load_game(path: str) -> GameState:
    """Recharge une partie depuis un fichier JSON et reconstruit un GameState.

    La carte est régénérée à l'identique depuis la seed, puis l'état dynamique
    (unités, villes, constructions, ressources, tour) est restauré par-dessus.

    Args:
        path: chemin du fichier de sauvegarde.

    Returns:
        GameState: un état de jeu prêt à être repris.

    Raises:
        ValueError: si la version du format de sauvegarde est incompatible.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    version = data.get("version")
    if version != SAVE_FORMAT_VERSION:
        raise ValueError(
            f"Format de sauvegarde v{version} incompatible (attendu v{SAVE_FORMAT_VERSION})."
        )

    # Régénération déterministe de la carte depuis la seed.
    m = data["map"]
    state = GameState(
        m["width"], m["height"], m["seed"],
        tile_area=m["avg_cells_per_tile"], log=m.get("log", False),
    )

    # État global du tour.
    state.turn = data["turn"]
    state.current_player = data["current_player"]
    state.current_kingdom_idx = data["current_kingdom_idx"]
    state.phase = TurnPhase[data["phase"]]
    state.turn_order = list(data["turn_order"])
    state.use_ti = data["use_ti"]
    state.use_fow = data["use_fow"]
    state.discovered = data["discovered"]
    state.visibility = data["visibility"]

    # Royaumes (on remplace le royaume joueur créé par défaut).
    state.kingdoms = [
        Kingdom(
            kingdom_id=k["kingdom_id"],
            name=k["name"],
            color=tuple(k["color"]),
            is_ai=k["is_ai"],
            cities=list(k["cities"]),
            ai_params=k["ai_params"],
        )
        for k in data["kingdoms"]
    ]

    # Ressources (str -> int sur les clés).
    state.player_resources = {int(kid): res for kid, res in data["resources"].items()}

    # Unités : on les recrée via la factory, en restaurant leur id exact.
    state.units = []
    for tile in state.map.tiles.values():
        tile.clear_units()
    max_uid = 0
    for ud in data["units"]:
        cls = UNIT_CLASS_MAP[UnitType[ud["type"]]]
        u = cls(ud["tile_id"], owner=ud["owner"], x=ud["x"], y=ud["y"])
        u.id = ud["id"]
        u.hp = ud["hp"]
        u.has_moved = ud["has_moved"]
        u.has_attacked = ud["has_attacked"]
        u.unit_type = UnitType[ud["type"]]
        state.units.append(u)
        if ud["tile_id"] in state.map.tiles:
            state.map.tiles[ud["tile_id"]].add_unit(u)
        max_uid = max(max_uid, u.id)

    # Villes : on restaure l'id exact (référencé par kingdom.cities).
    state.cities = []
    max_cid = -1
    for cd in data["cities"]:
        c = City(cd["name"], cd["owner"], cd["center_tile_id"], state)
        c.id = cd["id"]
        c.tile_ids = set(cd["tile_ids"])
        c.population = cd["population"]
        c.age = cd["age"]
        c.production = cd["production"]
        state.cities.append(c)
        max_cid = max(max_cid, c.id)

    # Constructions, replacées sur leurs tuiles.
    for tid_str, names in data["constructions"].items():
        tid = int(tid_str)
        if tid not in state.map.tiles:
            continue
        tile = state.map.tiles[tid]
        tile.constructions = [_CONSTRUCTION_CLASSES[name](tile) for name in names]

    # On réaligne les compteurs globaux pour éviter toute collision d'id
    #    sur les unités/villes créées APRÈS le chargement.
    Unit._unit_counter = max(Unit._unit_counter, max_uid)
    City._next_id = max_cid + 1

    return state
