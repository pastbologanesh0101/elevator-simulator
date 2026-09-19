"""Dispatch strategies: nearest-elevator and SCAN-style (disk-scheduling-style)
scheduling applied to elevators.

Each strategy answers two questions:
  1. ``assign``          -- which elevator should answer a new hall call?
  2. ``next_direction``  -- which way should a given elevator move next,
                            given the stops (pickups + dropoffs) it still owes?
"""
from __future__ import annotations

from typing import List, Optional

from .models import Direction, Elevator, Rider


class DispatchStrategy:
    """Interface implemented by concrete dispatch strategies."""

    name = "base"

    def assign(self, elevators: List[Elevator], rider: Rider) -> Optional[Elevator]:
        raise NotImplementedError

    def next_direction(self, elevator: Elevator, min_floor: int, max_floor: int) -> Direction:
        raise NotImplementedError


def _eta(elevator: Elevator, floor: int) -> float:
    """Estimate how many time-steps it will take ``elevator`` to reach ``floor``.

    An elevator already heading toward the floor gets a plain distance
    estimate. One heading away pays a penalty: it must first finish its
    current sweep (to its farthest stop) and then travel all the way back.
    """
    distance = abs(elevator.current_floor - floor)
    if elevator.direction == Direction.IDLE:
        return distance

    moving_up = elevator.direction == Direction.UP
    heading_toward = (moving_up and floor >= elevator.current_floor) or (
        not moving_up and floor <= elevator.current_floor
    )
    if heading_toward:
        return distance

    stops = elevator.all_stop_floors()
    if stops:
        farthest = max(stops) if moving_up else min(stops)
        return abs(farthest - elevator.current_floor) + abs(farthest - floor)
    return distance + 1


def _actionable_stops(elevator: Elevator) -> set:
    """Stops worth planning a route around right now.

    Dropoffs are always actionable (someone's already onboard). A pickup is
    only actionable if the elevator currently has a free seat -- otherwise
    treating a capacity-blocked pickup as a legitimate "nearest stop" makes
    a greedy strategy reverse toward a floor it cannot actually do anything
    at, oscillating forever instead of going to drop someone off first.
    """
    stops = elevator.dropoff_floors()
    if elevator.has_capacity():
        stops |= elevator.pickup_floors()
    return stops


def _sweeping_toward(elevator: Elevator, floor: int) -> bool:
    """Is this elevator's current sweep compatible with picking up at ``floor``?"""
    if elevator.direction == Direction.UP:
        return floor >= elevator.current_floor
    if elevator.direction == Direction.DOWN:
        return floor <= elevator.current_floor
    return True  # an idle elevator is compatible with anything


def _scan_style_direction(elevator: Elevator) -> Direction:
    """The SCAN ("elevator algorithm") movement rule, shared by both
    dispatch strategies: keep sweeping in the current direction as long as
    there is an actionable stop ahead, and only reverse once there is
    nothing left ahead.

    This is what real elevators do physically, regardless of which
    dispatcher decided who gets to ride -- an elevator does not helicopter
    back and forth chasing whichever raw floor number happens to be
    numerically closest; it commits to a sweep. Without this hysteresis, a
    "nearest absolute distance" rule oscillates forever whenever the
    nearest stop keeps flipping sides as the car moves (e.g. a rider
    waiting one floor "behind" while a dropoff is one floor "ahead").
    """
    stops = _actionable_stops(elevator)
    if not stops:
        return Direction.IDLE

    ahead_up = any(f > elevator.current_floor for f in stops)
    ahead_down = any(f < elevator.current_floor for f in stops)

    if elevator.direction == Direction.UP:
        if ahead_up:
            return Direction.UP
        if ahead_down:
            return Direction.DOWN
        return Direction.IDLE

    if elevator.direction == Direction.DOWN:
        if ahead_down:
            return Direction.DOWN
        if ahead_up:
            return Direction.UP
        return Direction.IDLE

    # Currently idle: pick a direction toward the nearest outstanding stop.
    if ahead_up and not ahead_down:
        return Direction.UP
    if ahead_down and not ahead_up:
        return Direction.DOWN
    if ahead_up and ahead_down:
        nearest = min(stops, key=lambda f: abs(f - elevator.current_floor))
        return Direction.UP if nearest > elevator.current_floor else Direction.DOWN
    return Direction.IDLE


class NearestElevatorDispatch(DispatchStrategy):
    """Assign each hall call to whichever available elevator can reach it
    soonest (by estimated arrival time, factoring in current direction and
    load).

    Once a car is moving, it still has to move like a physical elevator --
    it sweeps in its current direction until nothing is left there, then
    reverses (see ``_scan_style_direction``). What distinguishes this
    strategy from ``ScanDispatch`` is purely *which elevator answers a new
    call*, not the physics of how a car moves once it's underway.
    """

    name = "nearest"

    def assign(self, elevators: List[Elevator], rider: Rider) -> Optional[Elevator]:
        candidates = [e for e in elevators if e.has_capacity()]
        if not candidates:
            return None
        return min(candidates, key=lambda e: _eta(e, rider.origin_floor))

    def next_direction(self, elevator: Elevator, min_floor: int, max_floor: int) -> Direction:
        return _scan_style_direction(elevator)


class ScanDispatch(DispatchStrategy):
    """Classic SCAN ("elevator algorithm"): keep sweeping in the current
    direction, servicing every compatible stop along the way, and only
    reverse once nothing is left ahead in that direction. Hall calls are
    preferentially handed to whichever elevator is already sweeping toward
    them.
    """

    name = "scan"

    def assign(self, elevators: List[Elevator], rider: Rider) -> Optional[Elevator]:
        candidates = [e for e in elevators if e.has_capacity()]
        if not candidates:
            return None

        def score(e: Elevator):
            compatible = 0 if _sweeping_toward(e, rider.origin_floor) else 1
            return (compatible, _eta(e, rider.origin_floor))

        return min(candidates, key=score)

    def next_direction(self, elevator: Elevator, min_floor: int, max_floor: int) -> Direction:
        return _scan_style_direction(elevator)
