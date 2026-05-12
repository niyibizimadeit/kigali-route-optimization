"""
rl_bridge.py — Simulates delivery outcomes as RL reward signals.

Mirrors the reward signal construction in GiraXpress:
    ml-service/app/bandits/linucb.py
    ml-service/app/constants.py

If reward constants change in GiraXpress, update here too.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Reward constants — must match GiraXpress ml-service/app/constants.py
# ---------------------------------------------------------------------------

CLICK_REWARD:            float = 1.0
CART_REWARD:             float = 5.0
PURCHASE_REWARD:         float = 20.0
DELIVERY_SUCCESS_REWARD: float = 3.0
DELIVERY_FAILURE_REWARD: float = -10.0
LAMBDA_DEFAULT:          float = 0.5


# ---------------------------------------------------------------------------
# Return types
# ---------------------------------------------------------------------------


@dataclass
class DeliveryEvent:
    product_id:    int
    customer_node: int
    was_delivered: bool
    reward:        float


@dataclass
class RegretResult:
    cumulative_regret: np.ndarray   # shape (T,)
    final_regret:      float
    convergence_step:  int          # first step where 100-step avg growth < threshold


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

    Each stop in each route is one delivery. Each delivery fails independently
    with probability failure_rate.

    Args:
        solution: CVRPSolution — each stop in each route is one delivery.
        failure_rate: Probability (0.0–1.0) that any delivery fails.
        n_days: Number of days to simulate (solution repeated each day).
        seed: Optional random seed.

    Returns:
        List of DeliveryEvent objects, length = n_days × total_stops.
    """
    rng = np.random.default_rng(seed)

    # Flatten all stops across all routes into a single delivery list
    all_stops = []
    for route in solution.routes:
        for node_idx in route:
            all_stops.append(node_idx)

    events = []
    for day in range(n_days):
        for product_id, node_idx in enumerate(all_stops):
            failed = rng.random() < failure_rate
            reward = DELIVERY_FAILURE_REWARD if failed else DELIVERY_SUCCESS_REWARD
            events.append(DeliveryEvent(
                product_id=product_id % max(len(all_stops), 1),
                customer_node=node_idx,
                was_delivered=not failed,
                reward=reward,
            ))

    return events


def compute_linucb_regret(
    reward_events: list[DeliveryEvent],
    n_products: int = 50,
    alpha: float = 1.0,
    lam: float = LAMBDA_DEFAULT,
    T: int = 5000,
    seed: Optional[int] = None,
) -> RegretResult:
    """
    Simulate a LinUCB agent and compute cumulative regret.

    Adjusted reward:
        r_adj = r_click + lam × r_delivery

    The optimal arm at each step is the one with the highest true mean
    adjusted reward (computed from reward_events). Regret is the gap
    between optimal and chosen arm reward, cumulated over T steps.

    Context vectors are random unit vectors — we measure how delivery
    failure rate affects regret, not reproduce the exact GiraXpress model.

    Args:
        reward_events: Output of simulate_delivery_outcomes.
        n_products: Number of arms (products) in the bandit.
        alpha: LinUCB exploration parameter.
        lam: Delivery reward weight in r_adj formula.
        T: Number of interaction steps.
        seed: Optional random seed.

    Returns:
        RegretResult with cumulative_regret array and summary stats.
    """
    rng = np.random.default_rng(seed)
    d = 10   # context vector dimension

    # Build per-product mean adjusted reward from delivery events
    # Products without delivery events get a neutral reward
    product_delivery_rewards = {}
    for evt in reward_events:
        pid = evt.product_id % n_products
        product_delivery_rewards.setdefault(pid, []).append(evt.reward)

    # True mean adjusted reward per product
    # Click reward is simulated as uniform [0, CLICK_REWARD]
    true_click = rng.uniform(0, CLICK_REWARD, n_products)
    true_delivery_mean = np.array([
        np.mean(product_delivery_rewards[p]) if p in product_delivery_rewards
        else 0.0
        for p in range(n_products)
    ])
    true_reward = true_click + lam * true_delivery_mean
    optimal_reward = true_reward.max()

    # LinUCB parameters: one (A, b) pair per arm
    A = [np.eye(d) for _ in range(n_products)]
    b = [np.zeros(d) for _ in range(n_products)]

    cumulative_regret = np.zeros(T)
    convergence_step  = T   # default: never converged

    WINDOW = 100
    regret_so_far = 0.0

    for t in range(T):
        x = rng.standard_normal(d)
        x /= (np.linalg.norm(x) + 1e-12)

        # UCB score for each arm
        ucb = np.array([
            float(x @ np.linalg.solve(A[a], b[a]))
            + alpha * float(np.sqrt(x @ np.linalg.solve(A[a], x)))
            for a in range(n_products)
        ])
        chosen = int(np.argmax(ucb))

        # Observe reward — click reward + delivery component
        click_r = rng.uniform(0, CLICK_REWARD)
        delivery_r = (
            product_delivery_rewards[chosen][t % len(product_delivery_rewards[chosen])]
            if chosen in product_delivery_rewards and product_delivery_rewards[chosen]
            else 0.0
        )
        observed = click_r + lam * delivery_r

        # Update LinUCB matrices
        A[chosen] += np.outer(x, x)
        b[chosen] += observed * x

        # Regret = optimal - observed (using true means)
        step_regret = max(0.0, optimal_reward - true_reward[chosen])
        regret_so_far += step_regret
        cumulative_regret[t] = regret_so_far

        # Check convergence: 100-step average growth < 0.1
        if t >= WINDOW and convergence_step == T:
            recent_growth = (cumulative_regret[t] - cumulative_regret[t - WINDOW]) / WINDOW
            if recent_growth < 0.1:
                convergence_step = t

    return RegretResult(
        cumulative_regret=cumulative_regret,
        final_regret=float(cumulative_regret[-1]),
        convergence_step=convergence_step,
    )