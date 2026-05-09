"""
rl_bridge.py — Simulates delivery outcomes as RL reward signals.

Mirrors the reward signal construction in GiraXpress:
    ml-service/app/bandits/linucb.py
    ml-service/app/constants.py

If reward constants change in GiraXpress, they must be updated here too.
These two files must stay in sync — they define the same feedback loop.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Reward constants — must match GiraXpress ml-service/app/constants.py exactly
# ---------------------------------------------------------------------------

CLICK_REWARD: float = 1.0
CART_REWARD: float = 5.0
PURCHASE_REWARD: float = 20.0
DELIVERY_SUCCESS_REWARD: float = 3.0
DELIVERY_FAILURE_REWARD: float = -10.0

# Lambda: weight applied to delivery reward in the adjusted reward formula.
# r_adj = r_click + LAMBDA * r_delivery
# The ablation study in notebook 07 varies this from 0.0 to 1.0.
LAMBDA_DEFAULT: float = 0.5


# ---------------------------------------------------------------------------
# Return types
# ---------------------------------------------------------------------------


@dataclass
class DeliveryEvent:
    """A single simulated delivery outcome."""
    product_id: int
    customer_node: int
    was_delivered: bool           # True = success, False = failure
    reward: float                 # DELIVERY_SUCCESS_REWARD or DELIVERY_FAILURE_REWARD


@dataclass
class RegretResult:
    """Output of compute_linucb_regret."""
    cumulative_regret: np.ndarray   # shape (T,)
    final_regret: float
    convergence_step: int           # first step where regret growth rate < threshold


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def simulate_delivery_outcomes(
    solution,
    failure_rate: float,
    n_days: int = 30,
    seed: Optional[int] = None,
) -> list[DeliveryEvent]:
    """
    Simulate delivery outcomes for a CVRPSolution over n_days.

    For each delivery in the solution, randomly marks it as failed with
    probability failure_rate. Uses the reward constants above.

    Args:
        solution: CVRPSolution from any solver. Each stop in each route
                  is treated as one delivery.
        failure_rate: Probability (0.0 – 1.0) that any given delivery fails.
        n_days: Number of days to simulate (solution is repeated each day).
        seed: Optional random seed for reproducibility.

    Returns:
        List of DeliveryEvent objects, length = n_days × total_stops_in_solution.
    """
    pass


def compute_linucb_regret(
    reward_events: list[DeliveryEvent],
    n_products: int = 50,
    alpha: float = 1.0,
    lam: float = LAMBDA_DEFAULT,
    T: int = 5000,
    seed: Optional[int] = None,
) -> RegretResult:
    """
    Simulate a simplified LinUCB agent and compute cumulative regret.

    The agent uses the adjusted reward formula:
        r_adj = r_click + lam × r_delivery

    The 'optimal' arm at each step is defined as the one with the highest
    true mean adjusted reward (computed from reward_events). Regret is the
    gap between optimal and chosen arm reward, cumulated over T steps.

    This mirrors the LinUCB formulation in GiraXpress but is simplified
    for simulation: context vectors are random unit vectors (no real user
    features). The point is to measure how delivery failure rate affects
    regret, not to reproduce the exact GiraXpress model.

    Args:
        reward_events: Output of simulate_delivery_outcomes.
        n_products: Number of arms (products) in the bandit.
        alpha: LinUCB exploration parameter.
        lam: Weight for delivery reward in r_adj formula.
        T: Number of interaction steps to simulate.
        seed: Optional random seed.

    Returns:
        RegretResult with cumulative_regret array and summary stats.
    """
    pass