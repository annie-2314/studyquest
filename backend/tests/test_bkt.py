"""Unit tests for the Bayesian Knowledge Tracing update logic."""
from app.learning import bkt


def test_correct_increases_and_wrong_decreases_mastery():
    p = bkt.DEFAULT.p_init
    after_correct = bkt.update(p, True)
    after_wrong = bkt.update(p, False)
    assert after_correct > p
    assert after_wrong < after_correct
    # Wrong from a low prior still shouldn't increase mastery much.
    assert after_wrong <= p + bkt.DEFAULT.p_transit


def test_mastery_converges_upward_with_repeated_correct():
    p = 0.2
    for _ in range(8):
        p = bkt.update(p, True)
    assert p > 0.9
    assert p <= 1.0


def test_update_is_bounded_0_1():
    for start in (0.0, 0.5, 1.0):
        for correct in (True, False):
            out = bkt.update(start, correct)
            assert 0.0 <= out <= 1.0


def test_p_correct_next_monotonic_in_mastery():
    assert bkt.p_correct_next(0.9) > bkt.p_correct_next(0.1)
