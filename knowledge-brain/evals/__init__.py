"""Knowledge Brain Evaluations and Benchmarks (Role 4)."""

from evals.compare_baselines import run_baseline_comparison
from evals.run_5_strategies import evaluate_5_strategies
from evals.run_benchmarks import run_benchmark_suite
from evals.run_mvs_eval import run_mvs_eval
from evals.seed_30_sessions import generate_dataset, seed_live_shards

__all__ = [
    "generate_dataset",
    "seed_live_shards",
    "run_benchmark_suite",
    "run_mvs_eval",
    "evaluate_5_strategies",
    "run_baseline_comparison",
]
