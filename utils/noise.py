"""
Utilitaires de base pour le bruit de Perlin

Pris de la bibliothèques `noise` mais plus mise à jour depuis 8 ans, d'où le choix de ne prendre que les bouts utiles.
"""

import math
import json

# Table de permutation standard de Ken Perlin (doublée à 512 pour éviter les débordements d'index)
with open("utils/perm.json") as f:
    _PERM = json.load(f)
PERM = _PERM * 2


def lerp(t, a, b):
    return a + t * (b - a)


def grad2(hash_val, x, y):
    """Calcule le produit scalaire entre un vecteur de gradient et le vecteur (x, y)."""
    # Utilise les 4 bits de poids faible du hash pour choisir parmi 8 directions
    h = hash_val & 7
    u = x if h < 4 else y
    v = y if h < 4 else x
    return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -2.0 * v if (h & 2) else -v)


def _noise(x, y, repeatx=1024, repeaty=1024, base=0):
    # Gestion de la répétition (périodicité)
    i = int(math.floor(x % repeatx))
    j = int(math.floor(y % repeaty))
    ii = int((i + 1) % repeatx)
    jj = int((j + 1) % repeaty)

    # Application du base et masquage pour la table de permutation
    i = (i & 255) + base
    j = (j & 255) + base
    ii = (ii & 255) + base
    jj = (jj & 255) + base

    # Coordonnées relatives dans la cellule (0.0 à 1.0)
    x -= math.floor(x)
    y -= math.floor(y)

    # Courbe d'atténuation (Quintic curve: 6t^5 - 15t^4 + 10t^3)
    fx = x * x * x * (x * (x * 6 - 15) + 10)
    fy = y * y * y * (y * (y * 6 - 15) + 10)

    # Récupération des indices de hashage
    A = PERM[i]
    AA = PERM[(A + j) % 512]
    AB = PERM[(A + jj) % 512]
    B = PERM[ii]
    BA = PERM[(B + j) % 512]
    BB = PERM[(B + jj) % 512]

    # Interpolation finale
    res = lerp(
        fy,
        lerp(fx, grad2(PERM[AA], x, y), grad2(PERM[BA], x - 1, y)),
        lerp(fx, grad2(PERM[AB], x, y - 1), grad2(PERM[BB], x - 1, y - 1)),
    )
    return res


def perlin_noise(
    x, y, octaves=1, persistence=0.5, lacunarity=2.0, repeatx=1024, repeaty=1024, base=0
):
    """
    Fonction principale pour générer du bruit de Perlin fractal.
    """
    if octaves <= 0:
        raise ValueError("Expected octaves value > 0")

    if octaves == 1:
        return _noise(x, y, repeatx, repeaty, base)

    freq = 1.0
    amp = 1.0
    max_amp = 0.0
    total = 0.0

    for _ in range(octaves):
        total += (
            _noise(x * freq, y * freq, int(repeatx * freq), int(repeaty * freq), base % 254) * amp
        )
        max_amp += amp
        freq *= lacunarity
        amp *= persistence

    return total / max_amp
