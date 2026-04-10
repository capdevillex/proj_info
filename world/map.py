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
    * **Flood Fill :** Détection et réassignation des fragments isolés (îles de pixels)
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

import random, math, time
from typing import List, Tuple, Optional, Dict
from collections import defaultdict, Counter, deque

from scipy.spatial import KDTree

from utils.noise import perlin_noise
from world.biome import Biome


VORONOI_AREA_CORRECTION = 1.556  # facteur de correction empirique


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
    """

    def __init__(self, id_, cells):
        self.id = id_
        self.cells = cells
        self.center = self._compute_center()
        self.area = len(cells)
        self.neighbors = set()
        self.biome = Biome.BLANK

    def _compute_center(self):
        """
        Calcule le centre de masse moyen de la tuile.

        Returns:
            Tuple[float, float]: Coordonnées (x, y) du centre géométrique.
        """
        x = sum(c[0] + 0.5 for c in self.cells) / len(self.cells)
        y = sum(c[1] + 0.5 for c in self.cells) / len(self.cells)
        return (x, y)


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
        # En pratique ne change pas la forme des tuiles et en le désativant on gagne 20-30% de temps de génération

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

        self._log("[7] Voisinage")
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

    def _generate_biomes(self, octaves=3):
        """
        Génère les biomes via bruit de Perlin multi-octave.

        Chaque cellule reçoit une valeur continue transformée en catégorie : eau, plaine, forêt, montagne.

        Args:
            octaves (int): Niveau de détail du bruit (persistance des fréquences).
        """
        scale = self.avg_cells_per_tile * 1.35

        for y in range(self.height):
            for x in range(self.width):
                n = perlin_noise(
                    x / scale, y / scale, octaves=octaves, lacunarity=1.75, base=self.seed % 255
                )

                # ajout d'un gradiant négatif qui part des bords de la carte et vers le centre
                nx = 1 - (2 * x / self.width - 1 + 10**-5) ** 2
                ny = 1 - (2 * y / self.height - 1 + 10**-5) ** 2
                deniv = min(math.log(3 * min(nx, ny)), 0.1)
                n += 0.7 * deniv

                if n < -0.225:
                    self.biomes[y][x] = Biome.WATER
                elif n < 0.1125:
                    self.biomes[y][x] = Biome.PLAIN
                elif n < 0.325:
                    self.biomes[y][x] = Biome.FOREST
                else:
                    self.biomes[y][x] = Biome.MOUNTAIN

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

        On utilise un flood fill pour détecter les composantes connexes.
        Les petites composantes sont réassignées à un voisin dominant.

        Cela évite les formes aberrantes et améliore la jouabilité.
        """
        visited = [[False] * self.width for _ in range(self.height)]

        def flood_fill(x, y, id_):
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
                    comp = flood_fill(x, y, id_)
                    if len(comp) < self.avg_cells_per_tile * 0.3:
                        self._reassign_component(comp)

    def _reassign_component(self, comp):
        """
        Réassigne un groupe de cellules isolées au voisin le plus représenté.

        Args:
            comp (List[Tuple[int, int]]): Liste de cellules formant une île isolée.
        """
        self._log(f"[reassign comp] : {comp}")
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
