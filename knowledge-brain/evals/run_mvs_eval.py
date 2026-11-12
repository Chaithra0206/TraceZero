"""Minimum Viable System (MVS) evaluation wrapper delegating to run_benchmarks."""

from __future__ import annotations

from evals.run_benchmarks import main, run_benchmark_suite

__all__ = ["run_benchmark_suite", "main"]

if __name__ == "__main__":
    main()
