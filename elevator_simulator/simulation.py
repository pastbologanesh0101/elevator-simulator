"""The discrete-event simulation loop.

Time advances in fixed integer ticks. Each tick:
  1. any requests whose request_time has arrived become pending hall calls
  2. pending hall calls are assigned to an elevator by the dispatch strategy
  3. every elevator picks up / drops off riders at its current floor
  4. every elevator moves at most one floor toward its next stop

The loop terminates once every valid rider has been dropped off (or the
optional safety cap ``max_ticks`` is hit, which should never happen in
practice for a bounded, connected building).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List

from .building import Building
from .dispatch import DispatchStrategy, _actionable_stops
from .models import Direction, Elevator, Rider, can_drop_off, can_pick_up


@dataclass
class SimulationResult:
    riders: List[Rider]
    rejected: List[Rider]
    ticks: int
    strategy_name: str

    def _completed(self) -> List[Rider]:
        return [r for r in self.riders if r.dropoff_time is not None]

    def completed_count(self) -> int:
        return len(self._completed())

    def average_wait_time(self) -> float:
        completed = self._completed()
        if not completed:
            return 0.0
        return sum(r.wait_time for r in completed) / len(completed)

    def max_wait_time(self) -> int:
        completed = self._completed()
        return max((r.wait_time for r in completed), default=0)

    def average_travel_time(self) -> float:
        completed = self._completed()
        if not completed:
            return 0.0
        return sum(r.travel_time for r in completed) / len(completed)

    def max_travel_time(self) -> int:
        completed = self._completed()
        return max((r.travel_time for r in completed), default=0)


class Simulation:
    """Runs a batch of rider requests through a building under a dispatch strategy."""

    def __init__(self, building: Building, strategy: DispatchStrategy, max_ticks: int = 100_000):
        self.building = building
        self.strategy = strategy
        self.max_ticks = max_ticks

    def run(self, riders: Iterable[Rider]) -> SimulationResult:
        valid: List[Rider] = []
        rejected: List[Rider] = []
        for rider in riders:
            if self.building.is_valid_request(rider.origin_floor, rider.destination_floor):
                valid.append(rider)
            else:
                rejected.append(rider)

        pending: List[Rider] = sorted(valid, key=lambda r: r.request_time)
        all_riders: List[Rider] = list(pending)
        unassigned: List[Rider] = []
        t = 0

        while True:
            # 1. Release requests whose arrival time has come.
            while pending and pending[0].request_time <= t:
                unassigned.append(pending.pop(0))

            # 2. Assign outstanding hall calls to elevators.
            still_unassigned = []
            for rider in unassigned:
                elevator = self.strategy.assign(self.building.elevators, rider)
                if elevator is not None:
                    elevator.assigned_pickups.append(rider)
                else:
                    still_unassigned.append(rider)
            unassigned = still_unassigned

            # 3. Turnaround detection. If an elevator has nothing actionable
            #    left ahead of it in the direction it arrived from -- either
            #    because it's at the building's physical top/bottom, or
            #    simply because its remaining stops are all behind it --
            #    treat it as momentarily idle for servicing purposes. That
            #    lets a rider waiting right here board regardless of which
            #    way *they* want to go next, exactly like a real elevator
            #    opening its doors and flipping its direction light before
            #    setting off again. Crucially this does NOT force a specific
            #    opposite direction (that caused an earlier oscillation bug
            #    where an elevator with two stops on opposite sides kept
            #    reversing right past each one without ever being allowed to
            #    stop): it just goes neutral and lets step 4b below work out
            #    the real next direction from the updated stop list.
            for elevator in self.building.elevators:
                stops = _actionable_stops(elevator)
                if elevator.direction == Direction.UP:
                    ahead = any(f > elevator.current_floor for f in stops)
                elif elevator.direction == Direction.DOWN:
                    ahead = any(f < elevator.current_floor for f in stops)
                else:
                    ahead = True  # already idle/neutral
                if not ahead:
                    elevator.direction = Direction.IDLE

            # 4. Service the floor each elevator currently sits on, boarding
            #    and alighting riders using the direction it arrived with
            #    (or the boundary-corrected direction above).
            for elevator in self.building.elevators:
                self._handle_stop(elevator, t)

            # 4b. Now that this floor has been serviced, let the strategy
            #     decide which way to actually move from here.
            for elevator in self.building.elevators:
                elevator.direction = self.strategy.next_direction(
                    elevator, self.building.min_floor, self.building.max_floor
                )

            # 5. Are we done?
            all_done = all(r.dropoff_time is not None for r in all_riders)
            nothing_pending = not pending and not unassigned
            elevators_idle = all(e.is_idle_and_empty() for e in self.building.elevators)
            if all_done and nothing_pending and elevators_idle:
                break
            if t >= self.max_ticks:
                break

            # 6. Move every elevator one floor toward its next stop.
            for elevator in self.building.elevators:
                self._move(elevator)

            t += 1

        return SimulationResult(
            riders=all_riders, rejected=rejected, ticks=t, strategy_name=self.strategy.name
        )

    @staticmethod
    def _handle_stop(elevator: Elevator, t: int) -> None:
        # Drop off first, freeing capacity for anyone picked up at this floor.
        remaining = []
        for rider in elevator.riders:
            if can_drop_off(elevator, rider):
                rider.dropoff_time = t
            else:
                remaining.append(rider)
        elevator.riders = remaining

        still_waiting = []
        for rider in elevator.assigned_pickups:
            if can_pick_up(elevator, rider):
                rider.pickup_time = t
                elevator.riders.append(rider)
            else:
                still_waiting.append(rider)
        elevator.assigned_pickups = still_waiting

    def _move(self, elevator: Elevator) -> None:
        """Move ``elevator`` one floor in the direction already decided for
        it this tick (see step 4b of ``run``).
        """
        if elevator.direction == Direction.UP:
            elevator.current_floor = min(elevator.current_floor + 1, self.building.max_floor)
        elif elevator.direction == Direction.DOWN:
            elevator.current_floor = max(elevator.current_floor - 1, self.building.min_floor)
