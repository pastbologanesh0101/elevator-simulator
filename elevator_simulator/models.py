"""Core data models for the elevator simulation: riders and elevator cars."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set


class Direction(Enum):
    UP = 1
    IDLE = 0
    DOWN = -1


@dataclass
class Rider:
    """A rider entity travelling from an origin floor to a destination floor.

    ``request_time`` is when the hall call was made. ``pickup_time`` and
    ``dropoff_time`` are filled in by the simulation as the rider is served.
    """

    origin_floor: int
    destination_floor: int
    request_time: int
    rider_id: int = 0
    pickup_time: Optional[int] = None
    dropoff_time: Optional[int] = None

    @property
    def direction(self) -> Direction:
        """The direction this rider wants to travel (their hall-call direction)."""
        if self.destination_floor > self.origin_floor:
            return Direction.UP
        if self.destination_floor < self.origin_floor:
            return Direction.DOWN
        return Direction.IDLE

    @property
    def wait_time(self) -> Optional[int]:
        """Time from request to pickup, or None if not yet picked up."""
        if self.pickup_time is None:
            return None
        return self.pickup_time - self.request_time

    @property
    def travel_time(self) -> Optional[int]:
        """Time from pickup to dropoff, or None if not yet dropped off."""
        if self.dropoff_time is None or self.pickup_time is None:
            return None
        return self.dropoff_time - self.pickup_time

    @property
    def total_time(self) -> Optional[int]:
        """Time from request to dropoff (wait_time + travel_time)."""
        if self.dropoff_time is None:
            return None
        return self.dropoff_time - self.request_time


@dataclass
class Elevator:
    """A single elevator car within a building."""

    elevator_id: int
    current_floor: int = 0
    capacity: int = 8
    direction: Direction = Direction.IDLE
    riders: List[Rider] = field(default_factory=list)           # onboard, awaiting dropoff
    assigned_pickups: List[Rider] = field(default_factory=list)  # waiting riders assigned here

    @property
    def load(self) -> int:
        return len(self.riders)

    def has_capacity(self) -> bool:
        return self.load < self.capacity

    def dropoff_floors(self) -> Set[int]:
        return {r.destination_floor for r in self.riders}

    def pickup_floors(self) -> Set[int]:
        return {r.origin_floor for r in self.assigned_pickups}

    def all_stop_floors(self) -> Set[int]:
        return self.dropoff_floors() | self.pickup_floors()

    def is_idle_and_empty(self) -> bool:
        return not self.riders and not self.assigned_pickups


def can_pick_up(elevator: Elevator, rider: Rider) -> bool:
    """Can ``elevator`` pick up ``rider`` right now?

    Requires the elevator to be at the rider's floor, to have spare capacity,
    and to be travelling in a direction compatible with the rider's request
    (an idle elevator that has just arrived is always compatible).
    """
    if elevator.current_floor != rider.origin_floor:
        return False
    if not elevator.has_capacity():
        return False
    if elevator.direction == Direction.IDLE:
        return True
    return elevator.direction == rider.direction


def can_drop_off(elevator: Elevator, rider: Rider) -> bool:
    """Can ``elevator`` drop off ``rider`` right now?"""
    return elevator.current_floor == rider.destination_floor
