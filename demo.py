#!/usr/bin/env python3
"""Elevator Simulator demo.

Generates a reproducible batch of random rider requests and runs the same
workload through both dispatch strategies, reporting a genuine before/after
comparison of average/max wait and travel time.

Usage:
    python demo.py
    python demo.py --floors 20 --elevators 4 --riders 60 --seed 7
"""
from __future__ import annotations

import argparse
import copy

from elevator_simulator.building import Building
from elevator_simulator.dispatch import NearestElevatorDispatch, ScanDispatch
from elevator_simulator.generator import generate_riders
from elevator_simulator.simulation import Simulation, SimulationResult


def run_strategy(strategy_cls, num_floors, num_elevators, capacity, riders) -> SimulationResult:
    building = Building(num_floors=num_floors, num_elevators=num_elevators, capacity=capacity)
    strategy = strategy_cls()
    sim = Simulation(building, strategy)
    # Each strategy gets its own copies of the riders, since the simulation
    # mutates them in place (pickup_time / dropoff_time).
    riders_copy = copy.deepcopy(riders)
    return sim.run(riders_copy)


def main() -> None:
    parser = argparse.ArgumentParser(description="Elevator dispatch strategy comparison")
    parser.add_argument("--floors", type=int, default=15)
    parser.add_argument("--elevators", type=int, default=3)
    parser.add_argument("--capacity", type=int, default=6)
    parser.add_argument("--riders", type=int, default=40)
    parser.add_argument("--window", type=int, default=100, help="time window requests arrive over")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    riders = generate_riders(
        num_riders=args.riders,
        min_floor=0,
        max_floor=args.floors - 1,
        time_window=args.window,
        seed=args.seed,
    )

    print(
        f"Elevator Simulator demo: {args.floors} floors, {args.elevators} elevators, "
        f"capacity {args.capacity}, {args.riders} riders (seed={args.seed})\n"
    )

    results = {}
    for name, cls in [("Nearest-elevator", NearestElevatorDispatch), ("SCAN", ScanDispatch)]:
        result = run_strategy(cls, args.floors, args.elevators, args.capacity, riders)
        results[name] = result
        print(f"--- {name} dispatch ---")
        print(f"  ticks to complete:  {result.ticks}")
        print(f"  riders served:      {result.completed_count()} / {len(result.riders)}")
        print(f"  avg wait time:      {result.average_wait_time():.2f}")
        print(f"  max wait time:      {result.max_wait_time()}")
        print(f"  avg travel time:    {result.average_travel_time():.2f}")
        print(f"  max travel time:    {result.max_travel_time()}")
        print()

    best = min(results.items(), key=lambda kv: kv[1].average_wait_time())
    print(f"Winner on average wait time: {best[0]} ({best[1].average_wait_time():.2f} ticks)")


if __name__ == "__main__":
    main()
