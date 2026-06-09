"""Tests unitaires pour utils/noise.py"""
import pytest
import math
from utils.noise import lerp, grad2, perlin_noise, _noise, PERM


class TestLerp:
    def test_at_t0_returns_a(self):
        assert lerp(0.0, 3.0, 7.0) == pytest.approx(3.0)

    def test_at_t1_returns_b(self):
        assert lerp(1.0, 3.0, 7.0) == pytest.approx(7.0)

    def test_midpoint(self):
        assert lerp(0.5, 0.0, 10.0) == pytest.approx(5.0)

    def test_negative_values(self):
        assert lerp(0.5, -10.0, 10.0) == pytest.approx(0.0)

    def test_same_values(self):
        assert lerp(0.3, 5.0, 5.0) == pytest.approx(5.0)

    def test_monotonic(self):
        values = [lerp(t / 10, 0.0, 1.0) for t in range(11)]
        assert values == sorted(values)


class TestGrad2:
    def test_returns_a_number(self):
        result = grad2(PERM[0], 0.5, 0.5)
        assert isinstance(result, (int, float))

    def test_symmetric_hash_range(self):
        """Pour les 8 directions possibles (h=0..7), aucune exception."""
        for h in range(8):
            result = grad2(h, 0.3, 0.7)
            assert isinstance(result, (int, float))

    def test_zero_input(self):
        result = grad2(0, 0.0, 0.0)
        assert result == pytest.approx(0.0)


class TestNoiseInternal:
    def test_range_is_bounded(self):
        """_noise doit retourner des valeurs dans [-1, 1] environ."""
        for x in [0.1, 0.5, 1.0, 2.3, 5.7]:
            for y in [0.1, 0.5, 1.0, 2.3, 5.7]:
                val = _noise(x, y)
                assert -2.0 <= val <= 2.0, f"_noise({x}, {y}) = {val} hors bornes"

    def test_deterministic(self):
        """Le même appel doit donner le même résultat."""
        v1 = _noise(1.23, 4.56)
        v2 = _noise(1.23, 4.56)
        assert v1 == pytest.approx(v2)

    def test_different_positions_differ(self):
        """Des positions différentes doivent (presque toujours) donner des valeurs différentes."""
        v1 = _noise(0.1, 0.1)
        v2 = _noise(0.9, 0.9)
        assert v1 != pytest.approx(v2)


class TestPerlinNoise:
    def test_single_octave_range(self):
        """Bruit à 1 octave doit rester dans une plage raisonnable."""
        for i in range(20):
            x, y = i * 0.13, i * 0.17
            val = perlin_noise(x, y, octaves=1)
            assert -2.0 <= val <= 2.0, f"perlin_noise({x}, {y}) = {val} hors bornes"

    def test_multi_octave_range(self):
        """Bruit multi-octaves normalisé doit rester borné."""
        for i in range(10):
            val = perlin_noise(i * 0.1, i * 0.2, octaves=4, persistence=0.5)
            assert -2.0 <= val <= 2.0

    def test_deterministic_single_octave(self):
        v1 = perlin_noise(1.5, 2.5, octaves=1)
        v2 = perlin_noise(1.5, 2.5, octaves=1)
        assert v1 == pytest.approx(v2)

    def test_deterministic_multi_octave(self):
        v1 = perlin_noise(3.14, 2.71, octaves=6, persistence=0.5, lacunarity=2.0)
        v2 = perlin_noise(3.14, 2.71, octaves=6, persistence=0.5, lacunarity=2.0)
        assert v1 == pytest.approx(v2)

    def test_zero_octaves_raises(self):
        with pytest.raises(ValueError):
            perlin_noise(0.5, 0.5, octaves=0)

    def test_negative_octaves_raises(self):
        with pytest.raises(ValueError):
            perlin_noise(0.5, 0.5, octaves=-1)

    def test_single_octave_delegates_to_noise(self):
        """octaves=1 doit retourner exactement le même résultat que _noise."""
        x, y = 0.77, 1.33
        assert perlin_noise(x, y, octaves=1) == pytest.approx(_noise(x, y))

    def test_more_octaves_different_than_one(self):
        """Plus d'octaves ne doit pas donner le même résultat que 1 octave."""
        x, y = 0.5, 0.5
        v1 = perlin_noise(x, y, octaves=1)
        v4 = perlin_noise(x, y, octaves=4)
        assert v1 != pytest.approx(v4)

    def test_spatial_continuity(self):
        """Deux points très proches doivent avoir des valeurs proches (continuité)."""
        v1 = perlin_noise(1.0000, 1.0000)
        v2 = perlin_noise(1.0001, 1.0000)
        assert abs(v1 - v2) < 0.1

    def test_base_changes_output(self):
        """Changer la graine `base` doit changer le résultat."""
        v0 = perlin_noise(0.5, 0.5, base=0)
        v1 = perlin_noise(0.5, 0.5, base=42)
        assert v0 != pytest.approx(v1)

    def test_persistence_effect(self):
        """Une persistence plus haute doit amplifier les octaves hautes."""
        x, y = 2.5, 3.5
        vlow  = perlin_noise(x, y, octaves=4, persistence=0.1)
        vhigh = perlin_noise(x, y, octaves=4, persistence=0.9)
        # Ils ne doivent pas être identiques
        assert vlow != pytest.approx(vhigh)


class TestPermutationTable:
    def test_perm_length(self):
        assert len(PERM) == 512

    def test_perm_values_in_range(self):
        assert all(0 <= v <= 255 for v in PERM[:256])

    def test_perm_is_permutation(self):
        """Les 256 premières valeurs doivent être une permutation de 0..255."""
        assert sorted(PERM[:256]) == list(range(256))

    def test_perm_doubled(self):
        """La deuxième moitié est une copie de la première."""
        assert PERM[:256] == PERM[256:]
