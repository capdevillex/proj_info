"""
Benchmark — gain du calcul vectoriel pour l'assignation Voronoï des cellules.

Contexte
--------
Dans `world/map.py`, l'étape de partition de Voronoï assigne chacune des ~110 000
cellules de la grille à la capitale (centre de province) la plus proche. C'est
exactement l'opération réalisée par `Map._assign_cells` :

        _, indices = self.kdtree.query(coords)   # vectorisé (scipy + numpy)

Ce script compare deux implémentations de cette même opération :
  * NAÏVE   : double boucle Python pure (pour chaque cellule, on parcourt toutes
              les capitales et on garde la plus proche) — complexité O(N*K) ;
  * VECTORISÉE : une seule requête `scipy.spatial.KDTree.query(coords)`, qui
              travaille sur des tableaux NumPy et exploite une structure d'arbre
              k-dimensionnel — complexité O(N log K).

On mesure le temps des deux et on en déduit le facteur d'accélération. On vérifie
aussi que les deux méthodes renvoient bien le même résultat.

Usage :
    python3 benchmark_vectorisation.py            # tailles par défaut
    python3 benchmark_vectorisation.py 110000 3000  # N cellules, K capitales

Author : Victor et Xavier
"""

import sys
import time
import math
import random

import numpy as np
from scipy.spatial import KDTree


def assign_naive(coords, capitals):
    """Assignation au plus proche voisin, double boucle Python pure. O(N*K)."""
    result = []
    for (cx, cy) in coords:
        best_idx = -1
        best_d2 = math.inf
        for i, (kx, ky) in enumerate(capitals):
            dx = cx - kx
            dy = cy - ky
            d2 = dx * dx + dy * dy
            if d2 < best_d2:
                best_d2 = d2
                best_idx = i
        result.append(best_idx)
    return result


def assign_vectorized(coords, capitals):
    """Assignation au plus proche voisin via KDTree (scipy + numpy). O(N log K)."""
    tree = KDTree(capitals)
    _, indices = tree.query(coords)
    return indices


def main():
    # Tailles : par défaut, un échantillon représentatif mais qui laisse la
    # version naïve terminer en quelques secondes. La carte réelle fait
    # ~110 000 cellules pour ~3 000 pts attracteurs.
    n_cells = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    n_caps = int(sys.argv[2]) if len(sys.argv) > 2 else 3_000
    n_runs = 20

    width = height = 1000

    print(f"Assignation de {n_cells:,} cellules à {n_caps:,} pts attracteurs")
    print(f"Moyenne sur {n_runs} générations de carte\n")

    times_vec = []
    times_naive = []
    all_same = True

    for i in range(n_runs):
        rng = random.Random(i)
        coords = [(rng.uniform(0, width), rng.uniform(0, height)) for _ in range(n_cells)]
        capitals = [(rng.uniform(0, width), rng.uniform(0, height)) for _ in range(n_caps)]

        t0 = time.perf_counter()
        idx_vec = assign_vectorized(coords, capitals)
        times_vec.append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        idx_naive = assign_naive(coords, capitals)
        times_naive.append(time.perf_counter() - t0)

        if not np.array_equal(np.asarray(idx_naive), np.asarray(idx_vec)):
            all_same = False

        print(f"  Run {i + 1:2d}/{n_runs} — vec: {times_vec[-1]:.4f} s, naïf: {times_naive[-1]:.4f} s")

    t_vec = sum(times_vec) / n_runs
    t_naive = sum(times_naive) / n_runs

    print(f"\n  === Moyennes sur {n_runs} runs ===")
    print(f"  Vectorisée (KDTree)     : {t_vec:8.4f} s")
    print(f"  Naïve (boucles Python)  : {t_naive:8.4f} s")
    print(f"\n  Résultats toujours identiques : {all_same}")
    if t_vec > 0:
        print(f"  Facteur d'accélération       : x{t_naive / t_vec:,.0f}")


if __name__ == "__main__":
    main()
