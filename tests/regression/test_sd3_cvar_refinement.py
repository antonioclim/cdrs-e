"""Separate post-primary-lock refinement; never folded into the frozen 422."""
from fractions import Fraction
import math
from cdrse.economics import empirical_cvar


def test_tail_mass_just_above_an_order_statistic_boundary():
    values = (1.0, 3.0)
    alpha = math.nextafter(0.5, 0.0)
    a = Fraction.from_float(alpha)
    exact_values = tuple(Fraction.from_float(x) for x in values)
    # S4's variational expression, not the implementation's tail-sweep loop.
    exact = min(z + sum(max(x - z, Fraction(0)) for x in exact_values)
                / (len(values) * (1 - a)) for z in exact_values)
    assert float(exact) == 3.0
    assert empirical_cvar(values, alpha) == float(exact)
