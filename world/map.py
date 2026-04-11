"""
Module de Génération Procédurale de Monde (Grid-Based Voronoi Map)

Ce module orchestre la création d'un monde structuré en provinces (Tiles) à partir d'une grille 2D.
La génération suit une approche hybride mêlant partitionnement spatial (Voronoï), échantillonnage de
Blue Noise (Ebeida/Poisson) et bruit cohérent (Perlin).

---

### Pipeline de Génération :

1.  **Placement des points d'attraction (Blue Noise) :**
    * Initialisation de points d'attraction via l'algorithme d'Ebeida (Poisson-disk sampling simplifié).
    * Cette méthode garantit une distribution homogène des centres de provinces, évitant
        les clusters inesthétiques tout en conservant un aspect organique.
    * *Optionnel :* Relaxation de Lloyd pour stabiliser les centroïdes.

2.  **Cartographie des Biomes (Bruit Cohérent) :**
    * Génération d'une carte de bruit de Perlin multi-octave.
    * Segmentation de la valeur du bruit en seuils discrets pour définir les biomes
        (Eau, Plaine, Forêt, Montagne).
    * Assure une continuité spatiale (les forêts bordent les plaines, etc.).

3.  **Partitionnement de Voronoï Discret :**
    * Chaque cellule de la grille est assignée à la capitale la plus proche via une
        recherche accélérée par KD-Tree.
    * Unification des biomes : La province adopte le biome majoritaire de ses cellules
        constituantes, et réécrase ensuite le biome de chaque cellule pour garantir
        l'homogénéité interne.

4.  **Optimisation Topologique et Nettoyage :**
    * **BFS :** Détection et réassignation des fragments isolés (îles de pixels)
        vers la province voisine la plus dominante.
    * **Contraintes morphologiques :** Stabilisation des formes pour éviter les
        provinces en "U" ou excessivement morcelées.
    * **Filtrage de taille :** Fusion systématique des micro-provinces sous un seuil
        de surface critique.

5.  **Instanciation et Topologie (Graphe) :**
    * Calcul des propriétés finales de chaque objet `Tile` (Centroïde, Surface, Biome).
    * **Graphe d'Adjacence :** Analyse des frontières de cellules pour identifier les
        provinces voisines. Ce graphe sert de base au calcul de pathfinding et aux
        algorithmes de diffusion.

---

### Mécaniques de Jeu et Déplacement :
* **Coût de mouvement :** Le temps de trajet entre deux provinces est calculé par la
    distance euclidienne entre les centres, pondérée par un coefficient de friction
    propre au biome de destination.
* **Déterminisme :** La génération est entièrement pilotée par une graine (seed),
    permettant une reproductibilité parfaite de la géographie et des biomes.
"""

import heapq
import random, math, time
from typing import List, Tuple, Optional, Dict
from collections import defaultdict, Counter, deque

from scipy.spatial import KDTree

from utils.noise import perlin_noise
from world.biome import Biome

from world.unit import Unit

VORONOI_AREA_CORRECTION = 1.556  # facteur de correction empirique

# Taille minimale d'un cluster d'eau (en nombre de tuiles) pour être conservé. Les groupes connexes
# de tuiles d'eau dont la taille est <= à cette valeur seront convertis en biome terrestre.
MIN_WATER_CLUSTER_SIZE = 2

# Taille minimale d'une masse d'eau pour tenter de la relier à une voisine.
WATER_CONNECT_MIN_SIZE = 8

# Distance maximale (en sauts de tuile) entre deux masses d'eau pour les relier.
WATER_BRIDGE_MAX_HOPS = 3


def ratio_area_perimeter(cells: List):
    """
    Calcule le ratio area/perimeter d'un groupe de cellules, utilisé pour favoriser les fusions avec des groupes plus compacts.

    Args:
        cells (List[Tuple[int, int]]): Liste des coordonnées des cellules formant le groupe.
    Returns:
        float: Le ratio area/perimeter (plus élevé pour les formes compactes).
    """
    area = len(cells)
    perimeter = 0
    cell_set = set(cells)
    for x, y in cells:
        for nx, ny in [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]:
            if (nx, ny) not in cell_set:
                perimeter += 1
    return area / (perimeter + 10**-12)


class Tile:
    """
    Représente une unité territoriale (province) cohérente sur la carte.

    Une province regroupe un ensemble de cellules (pixels/coordonnées) issues d'une
    segmentation de Voronoï. Elle porte des propriétés physiques et topologiques
    utilisées pour le gameplay et le rendu.

    Attributes:
        id (int): Identifiant unique de la tuile.
        cells (List[Tuple[int, int]]): Liste des coordonnées (x, y) composant la tuile.
        center (Tuple[float, float]): Point central (centroïde) géométrique de la tuile.
        area (int): Nombre total de cellules (surface).
        neighbors (Set[int]): Ensemble des IDs des tuiles adjacentes.
        biome (Biome): Type de terrain dominant assigné à la tuile.

        units (List[Unit]): NOUVEAU - Liste des unités présentes sur cette tuile
    """

    def __init__(self, id_, cells):
        self.id = id_
        self.cells = cells
        self.center = self._compute_center()
        self.area = len(cells)
        self.neighbors = set()
        self.biome = Biome.BLANK

        # NOUVEAU : initialiser la liste d'unités vide
        self.units = []

    def _compute_center(self):
        """
        Calcule le centre de masse moyen de la tuile.

        Returns:
            Tuple[float, float]: Coordonnées (x, y) du centre géométrique.
        """
        x = sum(c[0] + 0.5 for c in self.cells) / len(self.cells)
        y = sum(c[1] + 0.5 for c in self.cells) / len(self.cells)
        return (x, y)

    # ========== NOUVELLES MÉTHODES POUR GÉRER LES UNITÉS ==========

    def add_unit(self, unit):
        """
        Ajoute une unité à cette tuile.

        Args:
            unit (Unit): L'unité à ajouter

        Exemple :
            tile = game_map.tiles[5]
            unit = Unit(tile_id=5, unit_type=UnitType.SOLDIER)
            tile.add_unit(unit)
        """
        if unit not in self.units:
            self.units.append(unit)
            unit.tile_id = self.id  # S'assurer que l'unité sait sur quelle tuile elle est

    def remove_unit(self, unit):
        """
        Retire une unité de cette tuile.

        Args:
            unit (Unit): L'unité à retirer

        Retour :
            bool : True si l'unité a été trouvée et retirée, False sinon

        Exemple :
            if tile.remove_unit(unit):
                print("Unité retirée")
        """
        if unit in self.units:
            self.units.remove(unit)
            return True
        return False

    def remove_unit_by_id(self, unit_id):
        """
        Retire une unité par son ID.

        Args:
            unit_id (int): L'ID de l'unité à retirer

        Retour :
            Unit : L'unité retirée, ou None si non trouvée

        Exemple :
            removed = tile.remove_unit_by_id(5)
            if removed:
                print(f"Unité {removed.id} retirée")
        """
        for unit in self.units[:]:  # Copie pour éviter les problèmes lors de la modification
            if unit.id == unit_id:
                self.units.remove(unit)
                return unit
        return None

    def get_units(self):
        """
        Retourne la liste des unités sur cette tuile.

        Retour :
            List[Unit] : Liste des unités

        Exemple :
            units = tile.get_units()
            for unit in units:
                print(unit)
        """
        return self.units.copy()  # Retourner une copie pour éviter les modifications externes

    def get_unit_by_id(self, unit_id):
        """
        Trouve une unité par son ID sur cette tuile.

        Args:
            unit_id (int): L'ID de l'unité à chercher

        Retour :
            Unit : L'unité trouvée, ou None si non trouvée

        Exemple :
            unit = tile.get_unit_by_id(5)
            if unit:
                print(f"Trouvée : {unit}")
        """
        for unit in self.units:
            if unit.id == unit_id:
                return unit
        return None

    def has_units(self):
        """
<<<<<<< HEAD
        bool qui vérifie si la tuile a des unités
=======
        Vérifie si la tuile a des unités.

        Retour :
            bool : True si au moins une unité est présente

        Exemple :
            if tile.has_units():
                print(f"Cette tuile a {len(tile.units)} unité(s)")
>>>>>>> 2d403f6 (style(map): Clean up whitespace and formatting in Tile class)
        """

        return len(self.units) > 0

    def get_units_by_owner(self, owner):
        #utile si mind bender/priest
        """
        Récupère toutes les unités d'un propriétaire sur cette tuile.

        Args:
            owner (int): L'ID du propriétaire

        Retour :
            List[Unit] : Les unités du propriétaire

        Exemple :
            units_joueur_0 = tile.get_units_by_owner(0)
        """
        return [unit for unit in self.units if unit.owner == owner]

    def clear_units(self):
        """
        Retire toutes les unités de cette tuile.

        """
        removed = self.units.copy()
        self.units.clear()
        return removed

    def __repr__(self):
        """Représentation textuelle de la tuile"""
        units_str = f", {len(self.units)} unit(s)" if self.units else ""
        return f"Tile(id={self.id}, biome={self.biome.name}, area={self.area}{units_str})"


class Map:
    """
    Gestionnaire principal de la génération procédurale du monde.

    Cette classe orchestre un pipeline allant de la distribution de points  stochastiques (Poisson
    Disk Sampling) à la construction d'un graphe de voisinage,  en passant par la génération de
    bruit cohérent (Perlin) pour les biomes.

    Attributes:
        width (int): Largeur de la carte en cellules.
        height (int): Hauteur de la carte en cellules.
        seed (int): Graine de génération garantissant le déterminisme.
        tiles (Dict[int, Tile]): Répertoire des objets Tile générés.
        grid (List[List[Optional[int]]]): Grille 2D stockant l'ID de la tuile pour chaque coordonnée.
        biomes (List[List[Biome]]): Grille 2D des types de terrain.
    """

    def __init__(self, width, height, seed, avg_cells_per_tile=35, log=False):
        self.width = width
        self.height = height
        self.avg_cells_per_tile = avg_cells_per_tile
        _corrected_avg_cells_per_tile = avg_cells_per_tile / VORONOI_AREA_CORRECTION
        self.n_points = int(width * height / _corrected_avg_cells_per_tile)
        self.seed = seed
        random.seed(self.seed)
        self.log = log

        self.grid: List[List[Optional[int]]] = [[None] * width for _ in range(height)]
        self.biomes = [[Biome.BLANK] * width for _ in range(height)]

        self.capitals: List[Tuple[float, float]] = []
        self.kdtree = None
        self.tiles: Dict[int, Tile] = {}

        self._generate()

    def serialize(self):
        """
        Sérialise la carte, la génération est purement déterministe en se basant sur la seed, on peut
        donc se contenter de stocker les paramètres de génération pour recréer la même carte à l'identique.

        Returns:
            Dict: Paramètres nécessaires pour reconstruire la carte via la même seed.
        """
        return {
            "width": self.width,
            "height": self.height,
            "avg_cells_per_tile": self.avg_cells_per_tile,
            "seed": self.seed,
            "log": self.log,
        }

    # PIPELINE GLOBAL
    def _generate(self):
        """ "
        Exécute le pipeline de génération complet (Séquence chronologique).

        Séquence :
            Points Poisson -> Bruit Biomes -> Voronoï -> Nettoyage -> Topologie.
        """
        tic = time.perf_counter()
        self._log("[1] Génération des points d'attraction (Poisson)")
        self.capitals = self._ebeida_poisson_phase1(self.n_points)
        self.kdtree = KDTree(self.capitals)
        self._log(f"    {len(self.capitals)} points d'attraction générés")

        # self._log("[2] Relaxation de Lloyd")
        # self._lloyd_relaxation(iterations=1)
        # En pratique ne change pas la forme des tuiles et en le désactivant on gagne 20-30% de temps de génération

        self._log("[3] Génération des biomes")
        self._generate_biomes()

        self._log("[4] Assignation Voronoï")
        self._assign_cells()

        self._log("[5] Nettoyage & contraintes")
        self._cleanup()

        self._log("[6] Construction des provinces")
        self._build_tiles()
        self._log(f"    {len(self.tiles)} provinces générés")
        self._log(f"    mean area : {sum((t.area for t in self.tiles.values()))/len(self.tiles)}")

        self._log("[7] Post-traitement hydrographique")
        self._fix_water_connectivity()

        self._log("[8] Fusion des tuiles d'eau (super-tuiles)")
        self._merge_water_tiles()

        self._log("[9] Voisinage")
        self._build_neighbors()

        self._log(f"[perf] generation time : {time.perf_counter() - tic}s")

    def _log(self, msg):
        """Affiche un message de log si l'option est activée"""
        if self.log:
            print(msg)

    def _poisson_disk_sampling(self, n_points: int) -> List[Tuple[float, float]]:
        """
        Génère des points espacés de manière homogène (Poisson disk sampling simplifié).

        On place aléatoirement des points dans la carte tout en imposant une distance minimale
        entre eux. Cela évite les clusters et garantit une distribution plus naturelle.

        Ici, on utilise une version naïve (rejet) plutôt que Bridson pour rester simple.
        Cela suffit pour des tailles modestes.

        Le but est d'obtenir des points d'attraction bien répartis qui serviront de centres Voronoï.

        ---

        (Non appelé, gardé juste à des fins de documentation)
        """
        points = []
        min_dist = math.sqrt((self.width * self.height) / n_points) * 0.7

        attempts = 0
        while len(points) < n_points and attempts < n_points * 50:
            x = random.uniform(0, self.width)
            y = random.uniform(0, self.height)

            if all((px - x) ** 2 + (py - y) ** 2 >= min_dist**2 for px, py in points):
                points.append((x, y))

            attempts += 1

        return points

    def _ebeida_poisson_phase1(self, n_points: int):
        """
        Implémentation de la Phase I de l'algorithme d'Ebeida et al. (2011) (https://dl.acm.org/doi/10.1145/1964921.1964944).

        On utilise une grille d'accélération où chaque cellule peut contenir au plus un point (taille = r / sqrt(2)).

        On parcourt les cellules dans un ordre aléatoire et on tente de placer un point uniformément à l'intérieur.

        La validation se fait uniquement sur un voisinage local (5x5), garantissant une complexité quasi-linéaire.

        Cette méthode remplace efficacement le Poisson disk sampling naïf avec de bien meilleures performances pour un grand nombre de points.
        """

        width, height = self.width, self.height

        # distance cible entre points
        r = math.sqrt((width * height) / n_points) * 0.9

        cell_size = r / math.sqrt(2)

        grid_w = int(width / cell_size) + 1
        grid_h = int(height / cell_size) + 1

        # grille : stocke index du point
        grid = [[-1 for _ in range(grid_w)] for _ in range(grid_h)]

        points = []

        # liste des cellules mélangée (important pour uniformité)
        cells = [(x, y) for y in range(grid_h) for x in range(grid_w)]
        random.shuffle(cells)

        def fits(px, py, gx, gy):
            """Vérifie localement si un point respecte la distance minimale."""
            for ny in range(max(0, gy - 2), min(grid_h, gy + 3)):
                for nx in range(max(0, gx - 2), min(grid_w, gx + 3)):
                    idx = grid[ny][nx]
                    if idx != -1:
                        qx, qy = points[idx]
                        if (qx - px) ** 2 + (qy - py) ** 2 < r * r:
                            return False
            return True

        # Phase I : un seul essai par cellule
        for gx, gy in cells:
            px = (gx + random.random()) * cell_size
            py = (gy + random.random()) * cell_size

            if not (0 <= px < width and 0 <= py < height):
                continue

            if fits(px, py, gx, gy):
                grid[gy][gx] = len(points)
                points.append((px, py))

        if len(points) < width * height / self.avg_cells_per_tile * 0.7:
            raise RuntimeError(
                f"Poisson sampling failed to generate enough points: {len(points)} / {n_points}"
            )
        return points

    def _lloyd_relaxation(self, iterations=2):
        """
        Applique une relaxation de Lloyd sur les capitales.

        Chaque point est déplacé vers le centre de masse des cellules qui lui sont
        les plus proches (Voronoï discret sur la grille).

        Cela permet de rendre la distribution plus régulière et organique, en évitant les zones trop denses ou trop vides.

        Transforme un Voronoï irrégulier en un pavage de Centroïdal Voronoï (CVT) plus esthétique et équilibré.

        ---

        (Non appelé, gardé juste à des fins de documentation)
        """
        for _ in range(iterations):
            regions = defaultdict(list)

            for y in range(self.height):
                for x in range(self.width):
                    i = self._nearest_capital((x, y))
                    regions[i].append((x, y))

            new_capitals = []
            for i, cells in regions.items():
                if not cells:
                    continue
                cx = sum(c[0] + 0.5 for c in cells) / len(cells)
                cy = sum(c[1] + 0.5 for c in cells) / len(cells)
                new_capitals.append((cx, cy))

            self.capitals = new_capitals

    def _generate_biomes(self, octaves=4):
        """
        Génère les biomes via bruit de Perlin multi-octave.

        Chaque cellule reçoit une valeur continue transformée en catégorie : eau, plaine, forêt,
        montagne ou désert.

        Le désert est déterminé par un second bruit de Perlin indépendant ("heat map") appliqué
        uniquement dans les zones de plaine.

        Args:
            octaves (int): Niveau de détail du bruit (persistance des fréquences).
        """
        scale = self.avg_cells_per_tile * 1.35
        # Échelle plus large pour le bruit de chaleur : les zones désertiques sont plus étendues et moins fragmentées que la topographie de base.
        heat_scale = self.avg_cells_per_tile * 3.5
        heat_seed = (
            self.seed + 7919
        ) % 255  # Décalage de seed pour que la heat map soit indépendante du bruit de terrain.

        # Seuil au-dessus duquel une cellule de plaine devient désert.
        # ~0.15 donne environ 9% de déserts, ce qui est rare mais visible.
        DESERT_HEAT_THRESHOLD = 0.15

        # stats pour les biomes
        water_ct = 0
        plain_ct = 0
        forest_ct = 0
        mountain_ct = 0
        desert_ct = 0

        for y in range(self.height):
            for x in range(self.width):
                n = perlin_noise(
                    x / scale, y / scale, octaves=octaves, lacunarity=1.75, base=self.seed % 255
                )

                # ajout d'un gradient négatif qui part des bords de la carte et vers le centre
                nx = 1 - (2 * x / self.width - 1 + 10**-5) ** 2
                ny = 1 - (2 * y / self.height - 1 + 10**-5) ** 2
                deniv = min(math.log(2.25 * min(nx, ny)), 0.1)
                n += 0.7 * deniv

                if n < -0.225:
                    self.biomes[y][x] = Biome.WATER
                    water_ct += 1
                elif n < 0.325:
                    heat = perlin_noise(
                        x / heat_scale, y / heat_scale, octaves=2, lacunarity=2.0, base=heat_seed
                    )
                    if n < 0.14:
                        # Zone de plaine : on applique la heat map pour détecter le désert.
                        if heat > DESERT_HEAT_THRESHOLD:
                            self.biomes[y][x] = Biome.DESERT
                            desert_ct += 1
                        else:
                            self.biomes[y][x] = Biome.PLAIN
                            plain_ct += 1
                    else:
                        self.biomes[y][x] = (
                            Biome.FOREST if heat < DESERT_HEAT_THRESHOLD else Biome.PLAIN
                        )
                        forest_ct += 1
                else:
                    self.biomes[y][x] = Biome.MOUNTAIN
                    mountain_ct += 1
        total = self.width * self.height
        self._log(
            f"    Biome distribution: WATER={water_ct/total:.2%}, PLAIN={plain_ct/total:.2%}, DESERT={desert_ct/total:.2%}, FOREST={forest_ct/total:.2%}, MOUNTAIN={mountain_ct/total:.2%}"
        )

    def _assign_cells(self):
        """
        Assigne chaque cellule au point d'attraction le plus proche (Voronoï discret).

        Utilise un KD-Tree pour optimiser la recherche du point d'attraction le plus proche pour chaque cellule (x, y).

        Cette étape garantit que toute la carte est couverte et sans trous.
        """
        coords = [(x, y) for y in range(self.height) for x in range(self.width)]
        _, indices = self.kdtree.query(coords)
        for i, (x, y) in enumerate(coords):
            self.grid[y][x] = int(indices[i])

    def _nearest_capital(self, pos):
        """
        Trouve l'index du point d'attraction le plus proche d'une coordonnée donnée.

        Args:
            pos (Tuple[int, int]): Position cible.
        Returns:
            int: Index (ID) de la capitale la plus proche.

        ---

        (Non appelé, gardé juste à des fins de documentation)
        """
        if self.kdtree is None:
            raise RuntimeError("This should not happen")
        _, index = self.kdtree.query(pos)
        return int(index)

    def _cleanup(self):
        """
        Post-traitement morphologique pour garantir l'intégrité de la carte, nettoie les artefacts du Voronoï discret.

        - Supprime les petites régions isolées
        - Fusionne les provinces trop petites avec leurs voisines
        - Assure la connexité des provinces

        On utilise un BFS pour détecter les composantes connexes.
        Les petites composantes sont réassignées à un voisin dominant.

        Cela évite les formes aberrantes et améliore la jouabilité.
        """
        visited = [[False] * self.width for _ in range(self.height)]

        def bfs(x, y, id_):
            q = deque([(x, y)])
            comp = []
            visited[y][x] = True

            while q:
                cx, cy = q.popleft()
                comp.append((cx, cy))
                for nx, ny in self._neighbors(cx, cy):
                    if not visited[ny][nx] and self.grid[ny][nx] == id_:
                        visited[ny][nx] = True
                        q.append((nx, ny))
            return comp

        for y in range(self.height):
            for x in range(self.width):
                if not visited[y][x]:
                    id_ = self.grid[y][x]
                    comp = bfs(x, y, id_)
                    if len(comp) < self.avg_cells_per_tile * 0.3:
                        self._reassign_component(comp)

    def _reassign_component(self, comp):
        """
        Réassigne un groupe de cellules isolées au voisin le plus représenté.

        Args:
            comp (List[Tuple[int, int]]): Liste de cellules formant une île isolée.
        """
        # self._log(f"[reassign comp] : {comp}")
        neighbor_ids = Counter()
        for x, y in comp:
            for nx, ny in self._neighbors(x, y):
                neighbor_ids[self.grid[ny][nx]] += 1
        if neighbor_ids:
            new_id = neighbor_ids.most_common(1)[0][0]
            for x, y in comp:
                self.grid[y][x] = new_id

    def _build_tiles(self):
        """
        Instancie les objets Tile et harmonise les biomes.

        Chaque province récupère :
        - ses cellules
        - son centre géométrique
        - son biome majoritaire

        Le biome est ensuite uniformisé sur toute la province.

        Cela finalise les entités de jeu manipulables.
        """
        cells_by_id = defaultdict(list)

        for y in range(self.height):
            for x in range(self.width):
                cells_by_id[self.grid[y][x]].append((x, y))

        for id_, cells in cells_by_id.items():
            tile = Tile(id_, cells)
            biome = Counter(self.biomes[y][x] for x, y in cells).most_common(1)[0][0]
            tile.biome = biome
            for x, y in cells:
                self.biomes[y][x] = biome
            self.tiles[id_] = tile

    def _fix_water_connectivity(self):
        """
        Assure la cohérence hydrographique de la carte en deux passes.

        **Passe 1 — Suppression des micro-points d'eau :**
            Les composantes connexes de tuiles d'eau de taille <= MIN_WATER_CLUSTER_SIZE
            sont converties en biome terrestre. Cela élimine les points d'eau ponctuels
            (1-2 provinces) incohérents.

        **Passe 2 — Connexion des masses d'eau proches :**
            Pour chaque paire de masses d'eau significatives (>= WATER_CONNECT_MIN_SIZE),
            on cherche un chemin de tuiles intermédiaires de longueur <= WATER_BRIDGE_MAX_HOPS
            qui ne traverse pas de montagne. Si un tel chemin existe, les tuiles terrestres
            sur le chemin le plus court sont converties en eau, créant un détroit naturel.

        Note : cette méthode doit être appelée après `_build_tiles` et avant `_build_neighbors`.
        """

        # tile.neighbors est vide à ce stade, on construit le graphe complet à la volée.
        tile_adjacency: Dict[int, set] = defaultdict(set)
        for y in range(self.height):
            for x in range(self.width):
                tid = self.grid[y][x]
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        nid = self.grid[ny][nx]
                        if nid != tid and nid is not None and tid is not None:
                            tile_adjacency[tid].add(nid)

        water_tile_ids = {tid for tid, t in self.tiles.items() if t.biome == Biome.WATER}

        if not water_tile_ids:
            return

        # --- BFS pour identifier les composantes connexes d'eau ---
        def water_components(wids):
            visited: set = set()
            comps: List[List[int]] = []
            for start in wids:
                if start in visited:
                    continue
                comp = []
                q = deque([start])
                visited.add(start)
                while q:
                    cur = q.popleft()
                    comp.append(cur)
                    for nb in tile_adjacency[cur]:
                        if nb not in visited and nb in wids:
                            visited.add(nb)
                            q.append(nb)
                comps.append(comp)
            return comps

        components = water_components(water_tile_ids)

        # Passe 1 : supprimer les micro-clusters d'eau
        small_ids: set = set()
        large_components: List[List[int]] = []
        for comp in components:
            if len(comp) <= MIN_WATER_CLUSTER_SIZE:
                small_ids.update(comp)
                self._log(f"[water] micro-cluster supprimé ({len(comp)} tuile(s))")
            else:
                large_components.append(comp)

        for tid in small_ids:
            self._convert_water_tile_to_land(tid, tile_adjacency)

        # Passe 2 : relier les masses d'eau significatives proches
        # On ne tente de relier que les composantes >= WATER_CONNECT_MIN_SIZE.
        significant = [c for c in large_components if len(c) >= WATER_CONNECT_MIN_SIZE]

        if len(significant) < 2:
            self._log(
                f"[water] {len(significant)} masse(s) d'eau significative(s), pas de connexion à établir."
            )
            return

        # Pour chaque paire de composantes significatives distinctes, on cherche
        # le chemin le plus court entre leurs tuiles via un BFS sur le graphe de tuiles.
        # On bloque les tuiles de montagne pour ne pas percer les reliefs.
        # Si le chemin (hors les tuiles d'eau de départ/arrivée) a <= WATER_BRIDGE_MAX_HOPS
        # tuiles terrestres, on les convertit en eau.
        comp_sets = [set(c) for c in significant]
        bridges_built = 0

        for i in range(len(significant)):
            for j in range(i + 1, len(significant)):
                set_i, set_j = comp_sets[i], comp_sets[j]

                # BFS depuis toutes les tuiles de la composante i vers la composante j.
                # On s'arrête dès qu'on atteint une tuile de j ou qu'on dépasse la distance max.
                # `prev` stocke le prédécesseur pour reconstruire le chemin.
                prev: Dict[int, Optional[int]] = {tid: None for tid in set_i}
                frontier = deque(set_i)
                found: Optional[int] = None
                land_hops: Dict[int, int] = {tid: 0 for tid in set_i}  # nb de sauts terrestres

                while frontier and found is None:
                    cur = frontier.popleft()
                    cur_hops = land_hops[cur]
                    if cur_hops > WATER_BRIDGE_MAX_HOPS:
                        continue
                    for nb in tile_adjacency[cur]:
                        if nb in prev:
                            continue
                        nb_biome = self.tiles[nb].biome
                        # Bloquer les montagnes
                        if nb_biome == Biome.MOUNTAIN:
                            continue
                        prev[nb] = cur
                        if nb in set_j:
                            found = nb
                            break
                        # Compter les sauts terrestres (hors eau)
                        nb_hops = cur_hops if nb_biome == Biome.WATER else cur_hops + 1
                        land_hops[nb] = nb_hops
                        frontier.append(nb)

                if found is None:
                    continue  # pas de chemin court trouvé, on laisse les masses séparées

                # Reconstruction du chemin et conversion des tuiles terrestres en eau.
                path = []
                cur = found
                while cur is not None:
                    path.append(cur)
                    cur = prev[cur]
                path.reverse()

                converted = 0
                for tid in path:
                    if self.tiles[tid].biome != Biome.WATER:
                        self._convert_land_tile_to_water(tid)
                        water_tile_ids.add(tid)
                        set_i.add(tid)
                        set_j.add(tid)
                        converted += 1

                if converted > 0:
                    bridges_built += 1
                    self._log(
                        f"[water] pont créé entre comp {i} et comp {j} ({converted} tuile(s) converties)"
                    )

                # Fusionner les deux composantes dans comp_sets pour les prochaines paires.
                comp_sets[i] = set_i | set_j
                comp_sets[j] = comp_sets[i]

        self._log(f"[water] {bridges_built} pont(s) hydrographique(s) établi(s).")

        # Passe 3 : élargissement des corridors trop fins
        self._widen_water_corridors(water_tile_ids, tile_adjacency)

    def _widen_water_corridors(self, water_tile_ids: set, tile_adjacency: Dict[int, set]):
        """
        Épaissit les corridors d'eau trop fins après la création des ponts.

        Algorithme :
          1. On constitue l'ensemble des tuiles d'eau qui ont strictement moins de 4 voisines
             eau (au sens de tile_adjacency). Ce sont les tuiles "en bordure étroite".
          2. Pour chaque tuile T de cet ensemble, on itère sur ses voisines eau W.
             On compte les pixels de frontière 4-connexe entre T et W.
             Si ce contact est < 4 (la connexion entre T et W est trop fine) :
               - On prend l'intersection des voisines de T et de W (hors eau, hors montagne).
               - Parmi ces candidates, on convertit en eau celle dont la somme de pixels de
                 frontière avec T et W est maximale.
          3. Les tuiles nouvellement converties sont ajoutées à water_tile_ids et
             tile_adjacency pour que les passes suivantes les voient.

        Args:
            water_tile_ids: Ensemble des IDs de tuiles d'eau (modifié en place).
            tile_adjacency: Graphe d'adjacence inter-tuiles complet (modifié en place).
        """
        # Calcul du cache des frontières pixel entre tuiles voisines.
        # On ne calcule que les paires (a, b) avec a < b pour éviter les doublons.
        border_cache: Dict[tuple, int] = {}

        def pixel_border(a: int, b: int) -> int:
            key = (min(a, b), max(a, b))
            if key not in border_cache:
                cells_b = set(self.tiles[b].cells)
                count = 0
                for x, y in self.tiles[a].cells:
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        if (x + dx, y + dy) in cells_b:
                            count += 1
                border_cache[key] = count
            return border_cache[key]

        # On itère jusqu'à convergence : une conversion peut créer de nouvelles paires trop fines.
        # En pratique 2-3 passes suffisent largement.
        MAX_PASSES = 3
        for pass_num in range(MAX_PASSES):
            widened = 0

            # Étape 1 : tuiles d'eau avec < 5 voisines eau.
            thin_water = {
                tid
                for tid in water_tile_ids
                if sum(1 for nb in tile_adjacency[tid] if nb in water_tile_ids) < 4
            }

            for tid in thin_water:
                water_neighbors = [nb for nb in tile_adjacency[tid] if nb in water_tile_ids]

                for w_nb in water_neighbors:
                    if pixel_border(tid, w_nb) >= 5:
                        continue  # connexion déjà suffisamment large

                    # Intersection des voisines terrestres non-montagne de tid et w_nb.
                    candidates = (tile_adjacency[tid] - water_tile_ids) & (
                        tile_adjacency[w_nb] - water_tile_ids
                    )
                    candidates = {c for c in candidates if self.tiles[c].biome != Biome.MOUNTAIN}

                    if not candidates:
                        continue

                    # On choisit le candidat qui maximise la frontière totale avec tid + w_nb.
                    best = max(
                        candidates, key=lambda c: pixel_border(c, tid) + pixel_border(c, w_nb)
                    )

                    self._convert_land_tile_to_water(best)
                    water_tile_ids.add(best)

                    # Mise à jour de tile_adjacency pour les passes suivantes.
                    for nb in tile_adjacency[best]:
                        tile_adjacency[nb].add(best)

                    # Invalider le cache pour les paires impliquant best.
                    keys_to_drop = [k for k in border_cache if best in k]
                    for k in keys_to_drop:
                        del border_cache[k]

                    widened += 1
                    self._log(f"[water] élargissement : tuile {best} convertie en eau")

            self._log(
                f"[water] passe d'élargissement {pass_num + 1} : {widened} tuile(s) ajoutée(s)"
            )
            if widened == 0:
                break

    def _convert_water_tile_to_land(self, tile_id: int, tile_adjacency: Dict[int, set]):
        """
        Convertit une tuile d'eau en biome terrestre (PLAIN ou DESERT).

        Le biome est choisi selon le voisinage dominant (hors eau) dans tile_adjacency.

        Args:
            tile_id (int): Identifiant de la tuile à convertir.
            tile_adjacency (Dict[int, set]): Graphe d'adjacence inter-tuiles pré-calculé.
        """
        tile = self.tiles[tile_id]

        land_neighbor_biomes = [
            self.tiles[nid].biome
            for nid in tile_adjacency.get(tile_id, set())
            if nid in self.tiles and self.tiles[nid].biome != Biome.WATER
        ]

        if land_neighbor_biomes:
            dominant = Counter(land_neighbor_biomes).most_common(1)[0][0]
            new_biome = dominant if dominant in (Biome.DESERT, Biome.PLAIN) else Biome.PLAIN
        else:
            new_biome = Biome.PLAIN

        tile.biome = new_biome
        for x, y in tile.cells:
            self.biomes[y][x] = new_biome

        # self._log(f"[water->land] tuile {tile_id} convertie en {new_biome.name}")

    def _convert_land_tile_to_water(self, tile_id: int, biome=Biome.WATER):
        """
        Convertit une tuile terrestre en eau pour créer un détroit entre deux masses d'eau.

        Args:
            tile_id (int): Identifiant de la tuile à convertir.
        """
        tile = self.tiles[tile_id]
        tile.biome = biome
        for x, y in tile.cells:
            self.biomes[y][x] = biome

        # self._log(f"[land->water] tuile {tile_id} convertie en eau (détroit)")

    def _pixel_contact_with_water(self, tile_id: int, water_tile_ids: set) -> int:
        """
        Compte le nombre de pixels (4-connexité) par lesquels une tuile touche
        l'ensemble des tuiles d'eau indiquées.

        Chaque paire (cellule de tile_id, cellule voisine d'une tuile d'eau) comptant
        comme un contact, le maximum théorique est le périmètre complet de la tuile.

        Args:
            tile_id: Tuile dont on mesure le contact avec l'eau.
            water_tile_ids: Ensemble des IDs de tuiles considérées comme eau.

        Returns:
            int: Nombre de contacts pixel 4-connexes avec des tuiles d'eau.
        """
        contact = 0
        for x, y in self.tiles[tile_id].cells:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    nid = self.grid[ny][nx]
                    if nid != tile_id and nid in water_tile_ids:
                        contact += 1
        return contact

    def _shared_pixel_border(self, tile_a: int, tile_b: int) -> int:
        """
        Compte le nombre de pixels de frontière 4-connexe partagés entre deux tuiles.

        Utile pour choisir la tuile voisine qui est "la plus proche" d'un pont d'eau
        existant, dans le but d'élargir un détroit trop fin.

        Args:
            tile_a: ID de la première tuile.
            tile_b: ID de la seconde tuile.

        Returns:
            int: Nombre de paires de cellules adjacentes (4-connexité) entre les deux tuiles.
        """
        # On construit un set des cellules de tile_b pour les lookups O(1).
        cells_b = set(self.tiles[tile_b].cells)
        count = 0
        for x, y in self.tiles[tile_a].cells:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                if (x + dx, y + dy) in cells_b:
                    count += 1
        return count

    def _merge_water_tiles(self, target_size: int = 12):
        """
        Fusionne les tuiles d'eau proches en super-tuiles plus grandes pour améliorer la jouabilité.
        Algorithme :
            1. On collecte les cellules d'eau et on prépare une Distance Transform pour mesurer la distance à la terre la plus proche.
            2. On applique un Poisson Disk Sampling adaptatif (inspiré d'Ebeida) sur les cellules d'eau, où le rayon de rejet varie en fonction de la distance à la côte : plus on est proche de la terre, plus les points d'attraction sont denses, créant des tuiles d'eau plus petites et détaillées près des côtes, et plus espacés au large pour éviter les micro-tuiles d'eau.
            3. On effectue une relaxation de Lloyd sur les points d'attraction pour améliorer la régularité des tuiles d'eau, en introduisant une répulsion supplémentaire près des côtes pour éviter que les tuiles d'eau ne deviennent trop grandes et irrégulières à proximité de la terre.
            4. Enfin, on réassigne les cellules d'eau aux nouveaux points d'attraction via un Voronoï discret, ce qui fusionne efficacement les tuiles d'eau proches en de plus grandes entités cohérentes, tout en préservant les détails côtiers essentiels pour la jouabilité et l'esthétique de la carte.
            5. On reconstruit les tuiles d'eau fusionnées et on met à jour les biomes en conséquence.
        """
        # 1. Collecte des cellules d'eau et préparation de la Distance Transform
        water_cells_set = set()
        land_cells = set()
        land_tiles = []

        for tid, tile in self.tiles.items():
            if tile.biome == Biome.WATER:
                water_cells_set.update(tile.cells)
            else:
                land_tiles.append(tile)
                land_cells.update(tile.cells)

        if not water_cells_set:
            return

        # ÉTAPE A : DISTANCE TRANSFORM (Manhattan simplifiée pour la performance)
        # Calcule la distance de chaque cellule d'eau à la terre la plus proche
        distance_map = {pos: float("inf") for pos in water_cells_set}
        dist_queue = deque()

        # Initialisation avec les cellules d'eau adjacentes à la terre
        for cx, cy in water_cells_set:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                if (cx + dx, cy + dy) in land_cells:
                    distance_map[(cx, cy)] = 1
                    dist_queue.append((cx, cy))
                    break

        while dist_queue:
            curr = dist_queue.popleft()
            d = distance_map[curr]
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor = (curr[0] + dx, curr[1] + dy)
                if neighbor in distance_map and distance_map[neighbor] == float("inf"):
                    distance_map[neighbor] = d + 1
                    dist_queue.append(neighbor)

        # ÉTAPE B : POISSON DISK SAMPLING ADAPTATIF (Ebeida encore)
        # Rayon de base pour la densité cible (target_size)
        r_base = math.sqrt(
            len(water_cells_set)
            / (max(1, len(water_cells_set) / (self.avg_cells_per_tile * target_size)))
        )

        # Paramètres de densité : 1.5x plus dense à la côte -> r_coast = r_base / sqrt(1.5)
        r_min = r_base * 0.85  # Près des côtes
        r_max = r_base * 1.75  # Large (3x moins dense environ)

        seeds = []
        # Grille d'accélération basée sur r_max pour la sécurité
        cell_size = r_max / 1.414
        grid_w, grid_h = int(self.width / cell_size) + 1, int(self.height / cell_size) + 1
        accel_grid = [[-1 for _ in range(grid_w)] for _ in range(grid_h)]

        def get_local_r(pos):
            d = distance_map.get(pos, 0)
            # Interpolation douce du rayon : sature à 50 pixels de la côte
            t = min(d / 50.0, 1.0)
            return r_min + (r_max - r_min) * t

        water_candidates = list(water_cells_set)
        random.shuffle(water_candidates)

        for cx, cy in water_candidates:
            px, py = cx + 0.5, cy + 0.5
            local_r = get_local_r((cx, cy))

            # Vérification du voisinage
            gx, gy = int(px / cell_size), int(py / cell_size)
            too_close = False
            for ny in range(max(0, gy - 2), min(grid_h, gy + 3)):
                for nx in range(max(0, gx - 2), min(grid_w, gx + 3)):
                    idx = accel_grid[ny][nx]
                    if idx != -1:
                        sx, sy = seeds[idx]
                        dist_sq = (sx - px) ** 2 + (sy - py) ** 2
                        # Rayon effectif : moyenne ou max pour assurer la transition
                        combined_r = max(local_r, get_local_r((int(sx), int(sy))))
                        if dist_sq < combined_r**2:
                            too_close = True
                            break
                if too_close:
                    break

            if not too_close:
                accel_grid[gy][gx] = len(seeds)
                seeds.append((px, py))

        # ÉTAPE C : RELAXATION DE LLOYD AVEC RÉPULSION CÔTIÈRE
        for _ in range(3):  # 2 itérations suffisent
            groups = defaultdict(list)
            # BFS temporaire pour assigner les cellules aux seeds actuelles
            temp_assignment = {
                (int(s[0]), int(s[1])): i
                for i, s in enumerate(seeds)
                if (int(s[0]), int(s[1])) in water_cells_set
            }
            q = deque(temp_assignment.keys())

            while q:
                curr = q.popleft()
                idx = temp_assignment[curr]
                groups[idx].append(curr)
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb = (curr[0] + dx, curr[1] + dy)
                    if nb in water_cells_set and nb not in temp_assignment:
                        temp_assignment[nb] = idx
                        q.append(nb)

            new_seeds = []
            for i, old_seed in enumerate(seeds):
                cells = groups[i]
                if not cells:
                    new_seeds.append(old_seed)
                    continue

                # Centroïde
                tx = sum(c[0] for c in cells) / len(cells)
                ty = sum(c[1] for c in cells) / len(cells)

                # Répulsion : on pousse vers le gradient positif de distance
                d_center = distance_map.get((int(tx), int(ty)), 20)
                if d_center < 15:
                    push_x, push_y = 0, 0
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        if distance_map.get((int(tx) + dx, int(ty) + dy), 0) > d_center:
                            push_x += dx
                            push_y += dy

                    factor = (15 - d_center) / 15 * 1.5
                    tx += push_x * factor
                    ty += push_y * factor

                # Validation : rester dans l'eau
                if (int(tx), int(ty)) in water_cells_set:
                    new_seeds.append((tx, ty))
                else:
                    new_seeds.append(old_seed)
            seeds = new_seeds

        # ÉTAPE 4 : PROPAGATION PAR FLOOD FILL SIMULTANÉ (BFS)
        grid_assignment = {}
        priority_queue = []  # (cost, x, y, seed_index, x_seed, y_seed)

        for i, seed in enumerate(seeds):
            pos = (int(seed[0]), int(seed[1]))
            if pos in water_cells_set:
                grid_assignment[pos] = i
                heapq.heappush(priority_queue, (0, pos[0], pos[1], i, pos[0], pos[1]))

        while priority_queue:
            _, x, y, s_idx, sx, sy = heapq.heappop(priority_queue)

            curr = (x, y)
            if grid_assignment.get(curr) != s_idx and curr in grid_assignment:
                continue

            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor = (x + dx, y + dy)
                if neighbor in water_cells_set and neighbor not in grid_assignment:
                    new_cost = (neighbor[0] - sx) ** 2 + (neighbor[1] - sy) ** 2
                    grid_assignment[neighbor] = s_idx
                    heapq.heappush(
                        priority_queue, (new_cost, neighbor[0], neighbor[1], s_idx, sx, sy)
                    )

        # ÉTAPE E : NETTOYAGE ET FUSION
        water_groups = defaultdict(list)
        for pos, s_idx in grid_assignment.items():
            water_groups[s_idx].append(pos)

        min_area = (self.avg_cells_per_tile * target_size) * 0.4
        remap = {idx: idx for idx in range(len(seeds))}

        # Fusion des orphelins (identique à ton code mais sécurisé)
        sorted_indices = sorted(water_groups.keys(), key=lambda i: len(water_groups[i]))
        for s_idx in sorted_indices:
            cells = water_groups[s_idx]
            if 0 < len(cells) < min_area:
                neighbor_indices = set()
                for cx, cy in cells:
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nb = (cx + dx, cy + dy)
                        if nb in grid_assignment:
                            nb_idx = remap[grid_assignment[nb]]
                            if nb_idx != s_idx:
                                neighbor_indices.add(nb_idx)

                if neighbor_indices:
                    target_idx = min(
                        neighbor_indices,
                        key=lambda idx: (
                            len(water_groups[idx] + water_groups[s_idx])
                            / (self._shared_pixel_border(s_idx, idx) + 1)
                            / (1 + ratio_area_perimeter(water_groups[idx] + water_groups[s_idx]))
                            ** 2
                        ),
                    )
                    water_groups[target_idx].extend(cells)
                    for c in cells:
                        grid_assignment[c] = target_idx  # Mise à jour pour fusions suivantes
                    remap[s_idx] = target_idx
                    water_groups[s_idx] = []

        # ÉTAPE F : RECONSTRUCTION
        new_tiles = {}
        next_id = 0

        # Terres (on garde tes objets Tile existants)
        for tile in sorted(land_tiles, key=lambda t: t.id):
            tile.id = next_id
            for x, y in tile.cells:
                self.grid[y][x] = next_id
            new_tiles[next_id] = tile
            next_id += 1

        # Mers
        for s_idx, cells in water_groups.items():
            if not cells:
                continue
            w_tile = Tile(next_id, cells)
            w_tile.biome = Biome.WATER
            for x, y in cells:
                self.grid[y][x] = next_id
                self.biomes[y][x] = Biome.WATER
            new_tiles[next_id] = w_tile
            next_id += 1

        self.tiles = new_tiles

    def _build_neighbors(self):
        """
        Construit le graphe de voisinage entre provinces.

        Deux provinces sont voisines si au moins une de leurs cellules est adjacente latéralement ou diagonalement.

        Ce graphe est essentiel pour :
        - pathfinding
        - gameplay stratégique
        - diffusion (culture, ressources, etc.)
        """
        for y in range(self.height):
            for x in range(self.width):
                id_ = self.grid[y][x]

                if id_ is None:
                    print(f"   ({x,y}) cell is None, check the assignation step")
                    continue

                for nx, ny in self._neighbors(x, y):
                    nid = self.grid[ny][nx]
                    if nid != id_:
                        self.tiles[id_].neighbors.add(nid)

    def _neighbors(self, x, y):
        """
        Générateur des 8 coordonnées adjacentes à un point. On considère aussi comme adjacente deux
        provinces ne partageant qu'un sommet commun.

        Args:
            x (int): Coordonnée X d'origine.
            y (int): Coordonnée Y d'origine.
        Yields:
            Tuple[int, int]: Coordonnées valides à l'intérieur des limites de la carte.
        """
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (1, 1), (1, -1), (-1, 1), (-1, -1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                yield nx, ny
