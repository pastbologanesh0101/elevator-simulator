# Elevator Simulator

[![tests](https://github.com/pastbologanesh0101/elevator-simulator/actions/workflows/tests.yml/badge.svg)](https://github.com/pastbologanesh0101/elevator-simulator/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A discrete-event simulation of a multi-elevator building, built to answer the
classic systems-design interview question "design an elevator system" with
actual running code instead of a whiteboard diagram.

Two real dispatch algorithms are implemented and compared head-to-head on the
same generated workload:

- **Nearest-elevator dispatch** -- each hall call is answered by whichever
  available car has the shortest estimated time to reach it.
- **SCAN dispatch** -- the "elevator algorithm" from disk scheduling, applied
  to elevators: hall calls preferentially go to a car that's already sweeping
  toward them, and every car keeps moving in its current direction, picking
  up compatible requests, until nothing is left ahead -- only then does it
  reverse.

Pure Python standard library. No dependencies.

## How it works

### The model

- **`Building`** -- a fixed floor range (`min_floor`..`max_floor`) and a
  fleet of `Elevator` cars.
- **`Elevator`** -- has a `current_floor`, a `direction` (`UP` / `IDLE` /
  `DOWN`), a `capacity`, the riders currently onboard, and the riders
  assigned to it that are still waiting to be picked up.
- **`Rider`** -- an `(origin_floor, destination_floor, request_time)` entity.
  A rider's desired travel `direction` is derived from origin vs.
  destination. As the simulation runs, `pickup_time` and `dropoff_time` get
  filled in, which is what `wait_time` (`pickup - request`) and
  `travel_time` (`dropoff - pickup`) are computed from.

A **hall call** is a rider showing up at `origin_floor` wanting to go up or
down; a **car call** is the destination floor they press once inside. Both
are represented directly on the `Rider` object -- `origin_floor` is the hall
call, `destination_floor` is the car call.

### Discrete-event simulation loop

Time advances in fixed integer ticks (`elevator_simulator/simulation.py`).
Each tick:

1. Any rider requests whose `request_time` has arrived become pending hall
   calls.
2. Pending hall calls are assigned to a car by the active dispatch strategy.
3. **Turnaround handling**: if a car has nothing left to do ahead of it in
   the direction it arrived from (including simply being at the building's
   top or bottom floor), it's treated as momentarily idle -- like a real
   elevator opening its doors and flipping its direction indicator -- so a
   rider waiting right there can board regardless of which way *they* want
   to go next.
4. Each car boards/alights riders at its current floor: dropoffs always
   happen when a car reaches a rider's destination; pickups happen only when
   the car's current direction matches the waiting rider's desired direction
   (or the car is idle), and only if it has spare capacity.
5. Each car decides which way to move next (its dispatch strategy's
   `next_direction`), and moves at most one floor toward it.

The loop ends once every valid rider has been dropped off.

### Dispatch strategies

Both strategies implement `assign()` (who answers a new hall call) and
`next_direction()` (which way a car moves next). They intentionally share
the same underlying physical movement rule -- a real elevator doesn't
teleport toward whichever floor number happens to be closest right now, it
commits to a sweep -- so the actual, meaningful difference between them is
in `assign()`:

- `NearestElevatorDispatch.assign` scores every elevator with capacity by
  estimated time-to-arrival (`_eta`): a car already heading toward the call
  gets a plain distance estimate, one heading away is penalized for having to
  finish its sweep and come back. The minimum-ETA car wins.
- `ScanDispatch.assign` prefers a car that's already sweeping toward the
  call (same logic, but ties are broken in favor of "already compatible with
  my current direction" before "just closest").

### Capacity, invalid floors

- `Elevator.has_capacity()` gates every pickup -- a full car will not board
  anyone else until it drops someone off.
- `Building.is_valid_request()` rejects any request whose origin or
  destination is outside `[min_floor, max_floor]`. `Simulation.run()` filters
  these out up front (`SimulationResult.rejected`) instead of crashing.

## Running it

```bash
python demo.py
```

Optional flags: `--floors`, `--elevators`, `--capacity`, `--riders`,
`--window` (the time window requests arrive over), `--seed`.

```bash
python demo.py --floors 20 --elevators 4 --riders 60 --seed 7
```

### Example output

```
$ python demo.py
Elevator Simulator demo: 15 floors, 3 elevators, capacity 6, 40 riders (seed=42)

--- Nearest-elevator dispatch ---
  ticks to complete:  112
  riders served:      40 / 40
  avg wait time:      5.05
  max wait time:      15
  avg travel time:    5.67
  max travel time:    13

--- SCAN dispatch ---
  ticks to complete:  106
  riders served:      40 / 40
  avg wait time:      5.00
  max wait time:      18
  avg travel time:    5.58
  max travel time:    13

Winner on average wait time: SCAN (5.00 ticks)
```

Same seed, same 40 riders, both strategies serve everyone -- but SCAN
finishes the whole batch in fewer ticks and edges out a slightly better
average wait time, because it avoids the extra back-and-forth "chase the
literal nearest ETA" reversals that nearest-elevator dispatch occasionally
makes; nearest-elevator dispatch does not clearly come out ahead on any of
these metrics for this workload, which is itself a realistic finding --
optimizing dispatch purely for a new call's ETA does not always beat a
simpler global sweep.

## Running the tests

```bash
python -m unittest discover -v tests
# or
python -m pytest tests/ -v
```

33 unit and integration tests cover, among other things:

- an elevator picks up a rider only when it reaches their floor **and** its
  direction matches what the rider wants (with a matching test for the
  inverse: no pickup on direction mismatch);
- an elevator drops a rider off exactly when it reaches their destination;
- nearest-elevator dispatch assigns a hall call to the genuinely closest
  available car in a crafted three-elevator scenario, and correctly skips
  a closer car that's already full;
- SCAN dispatch does not reverse direction while a compatible request is
  still ahead of it, and does reverse once nothing is left ahead (asserted
  directly against `next_direction`);
- elevator capacity is respected -- a full car won't board anyone else until
  it has space;
- wait time and travel time are computed correctly against a hand-worked
  single-rider scenario (elevator starts at floor 0, rider requests floor
  3 -> 8 at t=0: pickup at t=3, dropoff at t=8, wait=3, travel=5);
- a request above the top floor or below the ground floor is rejected
  gracefully instead of crashing the simulation;
- running the full simulation with a seeded random rider batch is
  deterministic -- the same seed reproduces the exact same aggregate
  numbers, which the tests assert on directly.

All tests run in CI on Python 3.11 and 3.12 via
[`.github/workflows/tests.yml`](.github/workflows/tests.yml).

## Project layout

```
elevator_simulator/
  models.py      Rider, Elevator, Direction, can_pick_up / can_drop_off
  building.py     Building: floor bounds + fleet, floor validation
  dispatch.py     NearestElevatorDispatch, ScanDispatch
  simulation.py   the discrete-event loop + SimulationResult
  generator.py    seeded random rider batch generation
demo.py           CLI: generate riders, run both strategies, compare
tests/            33 unit + integration tests
```
