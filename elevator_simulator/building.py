"""The building: floor bounds plus the fleet of elevators that serve them."""
from __future__ import annotations

from typing import List

from .models import Elevator


class InvalidFloorError(ValueError):
    """Raised when a rider requests a floor outside the building's range."""


class Building:
    """A building with a fixed floor range and a fleet of elevators."""

    def __init__(
        self,
        num_floors: int,
        num_elevators: int,
        capacity: int = 8,
        ground_floor: int = 0,
    ):
        if num_floors < 2:
            raise ValueError("A building needs at least 2 floors")
        if num_elevators < 1:
            raise ValueError("A building needs at least 1 elevator")

        self.min_floor = ground_floor
        self.max_floor = ground_floor + num_floors - 1
        self.elevators: List[Elevator] = [
            Elevator(elevator_id=i, current_floor=ground_floor, capacity=capacity)
            for i in range(num_elevators)
        ]

    def validate_floor(self, floor: int) -> None:
        """Raise InvalidFloorError if ``floor`` is outside the building."""
        if floor < self.min_floor or floor > self.max_floor:
            raise InvalidFloorError(
                f"Floor {floor} is outside the building's range "
                f"[{self.min_floor}, {self.max_floor}]"
            )

    def is_valid_request(self, origin: int, destination: int) -> bool:
        """Return True if a rider request between these two floors is servable."""
        try:
            self.validate_floor(origin)
            self.validate_floor(destination)
        except InvalidFloorError:
            return False
        return origin != destination
