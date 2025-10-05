import numpy as np

from ml.drift import psi


def test_psi_identical_distributions_near_zero():
    a = np.random.normal(0, 1, size=1000)
    b = a.copy()
    v = psi(a, b, bins=10)
    assert abs(v) < 1e-3


def test_psi_shifted_distribution_positive():
    a = np.random.normal(0, 1, size=1000)
    b = np.random.normal(1.0, 1, size=1000)
    v = psi(a, b, bins=10)
    assert v > 0.05


def test_psi_small_samples_finite():
    a = np.array([0.0, 0.0, 1.0])
    b = np.array([0.0, 1.0])
    v = psi(a, b, bins=5)
    assert np.isfinite(v)
