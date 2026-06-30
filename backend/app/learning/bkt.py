"""Bayesian Knowledge Tracing (BKT).

Standard 4-parameter model per concept:
  p_init    P(known) before any practice
  p_transit P(learn the skill on an attempt where it wasn't known)
  p_slip    P(answer wrong even though known)
  p_guess   P(answer right even though not known)

`update` applies the evidence (correct/incorrect) via Bayes to get the posterior
P(known), then applies the learning-transition to get the new prior for next time.
Pure functions — no I/O — so they're trivially unit-testable.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BKTParams:
    p_init: float = 0.2
    p_transit: float = 0.15
    p_slip: float = 0.1
    p_guess: float = 0.25


DEFAULT = BKTParams()


def update(p_known: float, correct: bool, params: BKTParams = DEFAULT) -> float:
    """Return the new P(known) after observing one correct/incorrect attempt."""
    p = min(max(p_known, 0.0), 1.0)
    if correct:
        num = p * (1 - params.p_slip)
        den = num + (1 - p) * params.p_guess
    else:
        num = p * params.p_slip
        den = num + (1 - p) * (1 - params.p_guess)
    posterior = num / den if den > 0 else p
    # Learning transition: chance of acquiring the skill this step.
    return posterior + (1 - posterior) * params.p_transit


def p_correct_next(p_known: float, params: BKTParams = DEFAULT) -> float:
    """Predicted probability the learner answers the next item correctly."""
    p = min(max(p_known, 0.0), 1.0)
    return p * (1 - params.p_slip) + (1 - p) * params.p_guess
